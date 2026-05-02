import { exec } from 'child_process';
import { promisify } from 'util';
import { existsSync, writeFileSync, unlinkSync } from 'fs';
import { resolve, join } from 'path';
import { tmpdir } from 'os';
import { NextResponse } from 'next/server';

const execAsync = promisify(exec);

/**
 * Detects which Python command works on the current system.
 * Tries python3, python, and py in order.
 * Returns the working command or null if none work.
 */
let cachedPythonCommand = null;

async function detectPythonCommand() {
  // Return cached result if available
  if (cachedPythonCommand !== null) {
    return cachedPythonCommand;
  }

  // On Windows, prefer 'python' and 'py' over 'python3' since python3
  // might be from msys64/cygwin without proper package installation
  const isWindows = process.platform === 'win32';
  const commands = isWindows
    ? ['python', 'py', 'python3']
    : ['python3', 'python', 'py'];
  
  for (const cmd of commands) {
    try {
      await execAsync(`${cmd} --version`, { timeout: 5000 });
      cachedPythonCommand = cmd;
      console.log(`Detected Python command: ${cmd}`);
      return cmd;
    } catch (error) {
      // Command not found, try next one
      continue;
    }
  }
  
  // No Python command found
  cachedPythonCommand = false;
  return null;
}

/**
 * POST /api/analyze
 * 
 * Analyzes a Node.js project using ZeroLoop's three-layer architecture:
 * - Layer 1: Raw findings (analyze.py)
 * - Layer 2: AI interpretation (granite_interpreter.py with Granite or template fallback)
 * - Layer 3: Bob context generation (bob_context_generator.py)
 * 
 * Request body:
 * {
 *   "projectPath": "/path/to/project",
 *   "apiKey": "optional-ibm-cloud-api-key",
 *   "projectId": "optional-watsonx-project-id",
 *   "region": "optional-region-default-us-south"
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "clearance": "BLOCKED|CAUTION|CLEARED",
 *   "clearance_message": "...",
 *   "summary": { ... },
 *   "issues": [ ... ],
 *   "bob_context": "...",
 *   "reset_context": "...",
 *   "savings": { ... },
 *   "coordinated_fix_plan": { ... },
 *   "timestamp": "..."
 * }
 */
export async function POST(request) {
  try {
    // Parse request body
    const body = await request.json();
    const { projectPath, apiKey, projectId, region = 'us-south' } = body;

    // Validate required fields
    if (!projectPath) {
      return NextResponse.json(
        {
          success: false,
          error: 'Missing required field',
          message: 'Please provide a projectPath in the request body.',
          hint: 'The projectPath should be the full path to your Node.js project directory.'
        },
        { status: 400 }
      );
    }

    // Validate credential pairing
    if ((apiKey && !projectId) || (!apiKey && projectId)) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid credentials',
          message: 'Both apiKey and projectId must be provided together, or neither.',
          hint: 'To use Granite AI interpretation, provide both IBM Cloud API key and watsonx.ai project ID.'
        },
        { status: 400 }
      );
    }

    // Detect Python command before proceeding
    const pythonCmd = await detectPythonCommand();
    if (!pythonCmd) {
      return NextResponse.json(
        {
          success: false,
          error: 'Python not found',
          message: 'Python not found. Please ensure Python is installed and accessible from the command line.',
          hint: 'Install Python 3.7+ from python.org and ensure it is added to your system PATH. On Windows, you may need to restart your terminal or IDE after installation.'
        },
        { status: 500 }
      );
    }

    // Normalize path for Windows compatibility (handles backslashes)
    const normalizedPath = resolve(projectPath);
    
    // Sanitize path to prevent command injection
    const sanitizedPath = normalizedPath.replace(/[;&|`$()]/g, '');
    
    if (sanitizedPath !== normalizedPath) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid project path',
          message: 'Project path contains invalid characters.',
          hint: 'Avoid special characters like ; & | ` $ ( ) in the path.'
        },
        { status: 400 }
      );
    }

    // Check if project path exists
    if (!existsSync(sanitizedPath)) {
      return NextResponse.json(
        {
          success: false,
          error: 'Project not found',
          message: `The project path "${projectPath}" does not exist.`,
          hint: 'Please verify the path and try again. Make sure you provide the full path to your Node.js project directory.'
        },
        { status: 404 }
      );
    }

    const warnings = [];
    const timestamp = new Date().toISOString();

    // ============================================================
    // LAYER 1: Run analyze.py for raw findings
    // ============================================================
    let rawFindings;
    try {
      const { stdout: analysisOutput, stderr: analysisError } = await execAsync(
        `${pythonCmd} scanner/analyze.py "${sanitizedPath}"`,
        {
          timeout: 120000, // 120 second timeout (increased for npm audit on first run)
          maxBuffer: 10 * 1024 * 1024 // 10MB buffer
        }
      );

      if (analysisError) {
        console.warn('Analysis stderr:', analysisError);
      }

      // Parse JSON output
      rawFindings = JSON.parse(analysisOutput);
    } catch (error) {
      console.error('Layer 1 (analyze.py) error:', error);
      
      // Check for specific error types
      if (error.killed && error.signal === 'SIGTERM') {
        return NextResponse.json(
          {
            success: false,
            error: 'Analysis timeout',
            message: 'The analysis took too long to complete (>120 seconds).',
            hint: 'This might happen with very large projects or slow npm audit on first run. Try analyzing a smaller directory or check for performance issues.'
          },
          { status: 500 }
        );
      }
      
      return NextResponse.json(
        {
          success: false,
          error: 'Analysis failed',
          message: 'Failed to run the dependency analyzer.',
          hint: error.message || 'An unexpected error occurred during analysis.',
          details: {
            stderr: error.stderr,
            code: error.code
          }
        },
        { status: 500 }
      );
    }

    // ============================================================
    // LAYER 2: Run granite_interpreter.py for AI interpretation
    // ============================================================
    let interpretation;
    let interpretationMethod = 'template'; // Default to template
    
    try {
      let interpreterCmd;
      const env = { ...process.env };
      
      // Use temporary file to avoid Windows command line length limits
      const tempFile = join(tmpdir(), `zeroloop-layer2-${Date.now()}.json`);
      writeFileSync(tempFile, JSON.stringify(rawFindings), 'utf-8');
      
      try {
        if (apiKey && projectId) {
          // Use Granite API - pass credentials via environment variables for security
          env.GRANITE_API_KEY = apiKey;
          env.GRANITE_PROJECT_ID = projectId;
          env.GRANITE_REGION = region;
          interpreterCmd = `${pythonCmd} -W ignore -c "import sys; import json; import os; from scanner.granite_interpreter import interpret_findings_safe; raw = json.load(open('${tempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); result = interpret_findings_safe(raw, os.getenv('GRANITE_API_KEY'), os.getenv('GRANITE_PROJECT_ID'), os.getenv('GRANITE_REGION', 'us-south')); print(json.dumps(result))"`;
          interpretationMethod = 'granite';
        } else {
          // Use template fallback
          interpreterCmd = `${pythonCmd} -W ignore -c "import sys; import json; from scanner.granite_interpreter import template_interpret; raw = json.load(open('${tempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); result = template_interpret(raw); print(json.dumps(result))"`;
        }
        
        const { stdout: interpretOutput, stderr: interpretError } = await execAsync(
          interpreterCmd,
          {
            timeout: 90000, // 90 second timeout for Granite API
            maxBuffer: 10 * 1024 * 1024,
            env: env
          }
        );

        if (interpretError) {
          console.warn('Interpretation stderr:', interpretError);
        }

        interpretation = JSON.parse(interpretOutput);
      } finally {
        // Clean up temp file
        try {
          unlinkSync(tempFile);
        } catch (e) {
          // Ignore cleanup errors
        }
      }
      
      // If we tried Granite but got template fallback, add warning
      if (apiKey && projectId && interpretError && interpretError.includes('template fallback')) {
        warnings.push('Granite API unavailable - using template-based interpretation');
        interpretationMethod = 'template';
      }
      
    } catch (error) {
      console.error('Layer 2 (granite_interpreter.py) error:', error);
      
      // Fall back to template interpretation on any error
      warnings.push('AI interpretation failed - using template-based interpretation');
      interpretationMethod = 'template';
      
      try {
        const fallbackTempFile = join(tmpdir(), `zeroloop-fallback-${Date.now()}.json`);
        writeFileSync(fallbackTempFile, JSON.stringify(rawFindings), 'utf-8');
        
        try {
          const fallbackCmd = `${pythonCmd} -W ignore -c "import sys; import json; from scanner.granite_interpreter import template_interpret; raw = json.load(open('${fallbackTempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); result = template_interpret(raw); print(json.dumps(result))"`;
          const { stdout: fallbackOutput } = await execAsync(
            fallbackCmd,
            {
              timeout: 30000,
              maxBuffer: 10 * 1024 * 1024
            }
          );
          interpretation = JSON.parse(fallbackOutput);
        } finally {
          try {
            unlinkSync(fallbackTempFile);
          } catch (e) {
            // Ignore cleanup errors
          }
        }
      } catch (fallbackError) {
        console.error('Template fallback also failed:', fallbackError);
        return NextResponse.json(
          {
            success: false,
            error: 'Interpretation failed',
            message: 'Failed to interpret the analysis results.',
            hint: 'Both Granite API and template fallback failed. Please check your Python environment.'
          },
          { status: 500 }
        );
      }
    }

    // ============================================================
    // LAYER 3: Run bob_context_generator.py for Bob context
    // ============================================================
    
    // Combine raw findings and interpretation for context generation
    const combinedResult = {
      ...rawFindings,
      granite_interpretation: interpretation,
      status: 'CLEARED', // Will be calculated below
      status_message: '',
      summary: {
        total_issues: interpretation.interpreted_issues?.length || 0,
        by_type: {}
      },
      issues: interpretation.interpreted_issues || []
    };
    
    // Calculate clearance status based on severity
    const criticalCount = interpretation.interpreted_issues?.filter(
      i => i.severity === 'critical'
    ).length || 0;
    const highCount = interpretation.interpreted_issues?.filter(
      i => i.severity === 'high'
    ).length || 0;
    
    if (criticalCount > 0) {
      combinedResult.status = 'BLOCKED';
      combinedResult.status_message = `Found ${criticalCount} critical issue(s) that must be resolved before proceeding.`;
    } else if (highCount > 0) {
      combinedResult.status = 'CAUTION';
      combinedResult.status_message = `Found ${highCount} high-priority issue(s). Review carefully before proceeding.`;
    } else {
      combinedResult.status = 'CLEARED';
      combinedResult.status_message = 'No critical issues detected. Safe to proceed.';
    }
    
    // Calculate summary by type
    const byType = {
      error: 0,
      incompatibility: 0,
      conflict: 0,
      redundancy: 0,
      warning: 0,
      info: 0
    };
    
    interpretation.interpreted_issues?.forEach(issue => {
      const severity = issue.severity;
      if (severity === 'critical') {
        byType.error++;
      } else if (severity === 'high') {
        byType.conflict++;
      } else {
        byType.warning++;
      }
    });
    
    combinedResult.summary.by_type = byType;
    
    let bobContext = null;
    let resetContext = null;
    let savings = null;
    
    try {
      // Use temporary file to avoid Windows command line length limits
      const tempFile = join(tmpdir(), `zeroloop-${Date.now()}.json`);
      writeFileSync(tempFile, JSON.stringify(combinedResult), 'utf-8');
      
      try {
        // Generate full Bob context - set UTF-8 encoding for Windows
        const contextCmd = `${pythonCmd} -W ignore -c "import sys; import json; import io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'); from scanner.bob_context_generator import generate_bob_context; data = json.load(open('${tempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); print(generate_bob_context(data))"`;
        const { stdout: contextOutput } = await execAsync(
          contextCmd,
          {
            timeout: 30000,
            maxBuffer: 10 * 1024 * 1024,
            encoding: 'utf8'
          }
        );
        bobContext = contextOutput.trim();
        
        // Generate reset context
        const resetCmd = `${pythonCmd} -W ignore -c "import sys; import json; import io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'); from scanner.bob_context_generator import generate_reset_context; data = json.load(open('${tempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); print(generate_reset_context(data))"`;
        const { stdout: resetOutput } = await execAsync(
          resetCmd,
          {
            timeout: 30000,
            maxBuffer: 10 * 1024 * 1024,
            encoding: 'utf8'
          }
        );
        resetContext = resetOutput.trim();
        
        // Estimate Bobcoin savings
        const savingsCmd = `${pythonCmd} -W ignore -c "import sys; import json; from scanner.bob_context_generator import estimate_bobcoin_savings; data = json.load(open('${tempFile.replace(/\\/g, '\\\\')}', 'r', encoding='utf-8')); print(json.dumps(estimate_bobcoin_savings(data)))"`;
        const { stdout: savingsOutput } = await execAsync(
          savingsCmd,
          {
            timeout: 30000,
            maxBuffer: 10 * 1024 * 1024,
            encoding: 'utf8'
          }
        );
        savings = JSON.parse(savingsOutput);
      } finally {
        // Clean up temp file
        try {
          unlinkSync(tempFile);
        } catch (e) {
          // Ignore cleanup errors
        }
      }
      
    } catch (error) {
      console.error('Layer 3 (bob_context_generator.py) error:', error);
      warnings.push('Bob context generation partially failed - some outputs may be missing');
      
      // Context generation failure is not critical - continue with available data
      bobContext = bobContext || 'Context generation failed';
      resetContext = resetContext || 'Reset context unavailable';
      savings = savings || {
        total_saved: 0,
        breakdown: [],
        summary: {},
        granite_cost: 0.0001,
        net_roi: 'Unable to calculate',
        explanation: 'Savings estimation failed'
      };
    }

    // ============================================================
    // Return combined result
    // ============================================================
    return NextResponse.json({
      success: true,
      analysis: {
        status: combinedResult.status,
        status_message: combinedResult.status_message,
        summary: combinedResult.summary,
        issues: interpretation.interpreted_issues || []
      },
      clearance: combinedResult.status,
      clearance_message: combinedResult.status_message,
      summary: combinedResult.summary,
      issues: interpretation.interpreted_issues || [],
      bob_context: bobContext,
      bobContext: bobContext, // Legacy support
      reset_context: resetContext,
      savings: savings,
      coordinated_fix_plan: interpretation.coordinated_fix_plan || {
        install_command: null,
        uninstall_command: null,
        warning: 'No coordinated fix plan available'
      },
      interpretation_method: interpretationMethod,
      warnings: warnings.length > 0 ? warnings : undefined,
      timestamp: timestamp
    });

  } catch (error) {
    console.error('API route error:', error);
    
    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        message: 'An unexpected error occurred while processing your request.',
        hint: error.message || 'Please try again or contact support if the issue persists.',
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/analyze
 * 
 * Returns API documentation
 */
export async function GET() {
  return NextResponse.json({
    name: 'ZeroLoop Analysis API',
    version: '2.0.0',
    description: 'Analyzes Node.js projects using three-layer AI-powered architecture',
    architecture: {
      layer1: 'Raw findings collection (analyze.py)',
      layer2: 'AI interpretation (Granite or template)',
      layer3: 'Bob context generation'
    },
    endpoints: {
      POST: {
        description: 'Analyze a project with optional Granite AI interpretation',
        body: {
          projectPath: 'string (required) - Path to the Node.js project',
          apiKey: 'string (optional) - IBM Cloud API key for Granite',
          projectId: 'string (optional) - watsonx.ai project ID',
          region: 'string (optional) - IBM Cloud region (default: us-south)'
        },
        response: {
          success: 'boolean',
          clearance: 'string - BLOCKED|CAUTION|CLEARED',
          clearance_message: 'string',
          summary: 'object - Issue statistics',
          issues: 'array - Interpreted issues with bobclues',
          bob_context: 'string - Full markdown context for Bob IDE',
          reset_context: 'string - Short reset prompt',
          savings: 'object - Bobcoin savings estimate',
          coordinated_fix_plan: 'object - npm commands to fix issues',
          interpretation_method: 'string - granite|template',
          warnings: 'array (optional) - Non-fatal warnings',
          timestamp: 'string - ISO timestamp'
        }
      }
    },
    example: {
      request: {
        method: 'POST',
        body: {
          projectPath: './my-project',
          apiKey: 'your-ibm-cloud-api-key',
          projectId: 'your-watsonx-project-id',
          region: 'us-south'
        }
      }
    },
    notes: [
      'If apiKey and projectId are not provided, template-based interpretation is used',
      'Granite API errors automatically fall back to template interpretation',
      'All errors return user-friendly messages without stack traces'
    ]
  });
}

// Made with Bob
