# ZeroLoop Two-Layer Architecture Upgrade Plan

## Overview
Upgrade the ZeroLoop scanner from hardcoded conflict rules to a two-layer system:
- **Layer 1**: Raw findings collection (analyze.py)
- **Layer 2**: AI interpretation via IBM watsonx.ai Granite (granite_interpreter.py)

---

## Current Architecture Analysis

### Existing Functions in analyze.py
1. **`check_dependency_conflicts()`** - Hardcoded conflict detection
   - `_check_express_bodyparser_conflict()` - Express/body-parser redundancy
   - `_check_mongoose_mongodb_conflict()` - Mongoose/MongoDB version collision
   - `_check_multiple_logging_libraries()` - Multiple logger detection

2. **`check_node_version()`** - Node version mismatch detection
   - Compares package.json engines.node, .nvmrc, and current Node version
   - Uses helper functions: `_compare_node_versions()`, `_versions_compatible()`, etc.

3. **`check_circular_dependencies()`** - Circular dependency detection
   - Uses madge (npm tool) as primary method
   - Falls back to manual analysis if madge unavailable

4. **`run_analysis()`** - Aggregates all checks
   - Returns structured JSON with status, issues, and bobclues

### Current Issue Format
```json
{
  "type": "error|incompatibility|conflict|redundancy|warning|info",
  "category": "dependencies|logging|circular-deps|setup",
  "title": "Short description",
  "detail": "Detailed explanation",
  "bobclue": "DO NOT... guidance",
  "fix": "Recommended fix steps"
}
```

---

## Layer 1: analyze.py Changes

### New Raw Findings Format
All functions return **raw findings only** - NO bobclues, NO explanations:

```json
{
  "finding_type": "npm_audit|depcheck|circular_deps|node_version",
  "raw_data": {
    // Tool-specific raw output
  },
  "metadata": {
    "tool": "npm|depcheck|madge|node",
    "timestamp": "ISO-8601",
    "project_path": "string"
  }
}
```

### Function Changes

#### 1. Replace `check_dependency_conflicts()` with `check_npm_audit()`
```python
def check_npm_audit(project_path: str) -> Dict[str, Any]:
    """
    Run npm audit and return raw vulnerability data.
    
    Returns:
        {
            "finding_type": "npm_audit",
            "raw_data": {
                "vulnerabilities": {...},  # npm audit JSON output
                "metadata": {...}
            },
            "metadata": {...}
        }
    """
```

**Implementation:**
- Execute: `npm audit --json`
- Parse JSON output
- Return raw vulnerability data (no interpretation)
- Handle errors gracefully (offline, no npm, etc.)

#### 2. Add `check_depcheck()`
```python
def check_depcheck(project_path: str) -> Dict[str, Any]:
    """
    Run depcheck to find unused and missing dependencies.
    
    Returns:
        {
            "finding_type": "depcheck",
            "raw_data": {
                "dependencies": [...],      # unused deps
                "devDependencies": [...],   # unused devDeps
                "missing": {...},           # missing deps
                "using": {...}              # where deps are used
            },
            "metadata": {...}
        }
    """
```

**Implementation:**
- Execute: `npx depcheck --json`
- Parse JSON output
- Return raw unused/missing dependency data
- Handle errors gracefully

#### 3. Update `check_circular_dependencies()`
```python
def check_circular_dependencies(project_path: str) -> Dict[str, Any]:
    """
    Detect circular dependencies using madge.
    
    Returns:
        {
            "finding_type": "circular_deps",
            "raw_data": {
                "circular": [[...], [...]],  # madge JSON output
                "method": "madge|manual"
            },
            "metadata": {...}
        }
    """
```

**Changes:**
- Keep madge integration
- Remove hardcoded bobclues and explanations
- Return only raw circular dependency chains
- Keep manual fallback

#### 4. Update `check_node_version()`
```python
def check_node_version(project_path: str) -> Dict[str, Any]:
    """
    Check Node version compatibility.
    
    Returns:
        {
            "finding_type": "node_version",
            "raw_data": {
                "package_json_engines": ">=18.0.0",
                "nvmrc_version": "18.16.0",
                "current_version": "20.10.0",
                "mismatches": [
                    {
                        "type": "current_vs_required|current_vs_nvmrc|nvmrc_vs_required",
                        "expected": "string",
                        "actual": "string"
                    }
                ]
            },
            "metadata": {...}
        }
    """
```

**Changes:**
- Keep version comparison logic
- Remove hardcoded bobclues
- Return only raw version data and mismatches

#### 5. Update `run_analysis()`
```python
def run_analysis(project_path: str) -> Dict[str, Any]:
    """
    Run all analyzers and aggregate raw findings.
    
    Returns:
        {
            "timestamp": "ISO-8601",
            "project_path": "string",
            "raw_findings": [
                {...},  # npm_audit finding
                {...},  # depcheck finding
                {...},  # circular_deps finding
                {...}   # node_version finding
            ],
            "errors": [...]  # Any analyzer errors
        }
    """
```

**Changes:**
- Remove status calculation (BLOCKED/CAUTION/CLEARED)
- Remove issue counting
- Return only aggregated raw findings
- Keep error handling for failed analyzers

### Helper Functions to Remove
- `_check_express_bodyparser_conflict()` - Replaced by npm audit
- `_check_mongoose_mongodb_conflict()` - Replaced by npm audit
- `_check_multiple_logging_libraries()` - Replaced by depcheck
- All hardcoded conflict detection logic

### Helper Functions to Keep
- `_normalize_node_version()`
- `_parse_version()`
- `_versions_compatible()`
- `_find_cycles_dfs()`
- `_check_circular_with_madge()`
- `_check_circular_manual()`

---

## Layer 2: granite_interpreter.py

### New File Structure

```python
"""
ZeroLoop Granite AI Interpreter
Interprets raw findings using IBM watsonx.ai Granite models.
"""

import json
import requests
from typing import Dict, Any, List, Optional

# Granite API Configuration
GRANITE_API_ENDPOINT = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation"
GRANITE_MODEL_ID = "ibm/granite-13b-chat-v2"

def interpret_findings(
    raw_findings: Dict[str, Any],
    api_key: str,
    project_id: str,
    region: str = "us-south"
) -> Dict[str, Any]:
    """
    Interpret raw findings using IBM watsonx.ai Granite API.
    
    Args:
        raw_findings: Output from analyze.py run_analysis()
        api_key: IBM Cloud API key
        project_id: watsonx.ai project ID
        region: IBM Cloud region (default: us-south)
    
    Returns:
        {
            "interpreted_issues": [
                {
                    "title": "string",
                    "explanation": "string",
                    "bobclue": "DO NOT...",
                    "severity": "critical|high|medium",
                    "fix": "string"
                }
            ],
            "circular_constraint_pairs": [
                {
                    "package_a": "string",
                    "package_b": "string",
                    "reason": "string"
                }
            ],
            "coordinated_fix_plan": {
                "install_command": "npm install ...",
                "uninstall_command": "npm uninstall ...|null",
                "warning": "string"
            }
        }
    """
```

### Granite Prompt Template

```python
GRANITE_PROMPT_TEMPLATE = """You are a Node.js dependency expert analyzing project issues.

Given these raw findings from automated tools:
{raw_findings_json}

Analyze and provide:
1. Interpreted issues with Bob-specific guidance (bobclues starting with "DO NOT")
2. Circular dependency constraint pairs
3. A coordinated fix plan with npm commands

Return ONLY valid JSON in this exact schema:
{{
  "interpreted_issues": [
    {{
      "title": "string",
      "explanation": "string",
      "bobclue": "DO NOT...",
      "severity": "critical|high|medium",
      "fix": "string"
    }}
  ],
  "circular_constraint_pairs": [
    {{
      "package_a": "string",
      "package_b": "string",
      "reason": "string"
    }}
  ],
  "coordinated_fix_plan": {{
    "install_command": "npm install ...",
    "uninstall_command": "npm uninstall ...|null",
    "warning": "string"
  }}
}}

Rules:
- All bobclues MUST start with "DO NOT"
- Severity must be: critical, high, or medium
- Coordinated fix plan must consider all issues together
- If no circular deps, return empty array for circular_constraint_pairs
"""
```

### Implementation Functions

```python
def _call_granite_api(
    prompt: str,
    api_key: str,
    project_id: str,
    region: str
) -> str:
    """Call IBM watsonx.ai Granite API."""
    # Implementation details...

def _parse_granite_response(response_text: str) -> Dict[str, Any]:
    """Parse and validate Granite JSON response."""
    # Handle malformed responses
    # Validate schema
    # Return parsed JSON

def _validate_interpretation_schema(data: Dict[str, Any]) -> bool:
    """Validate Granite response matches expected schema."""
    # Check required fields
    # Validate severity values
    # Ensure bobclues start with "DO NOT"

def template_interpret(raw_findings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback interpreter when no Granite credentials provided.
    Generates basic bobclues using template logic.
    
    Args:
        raw_findings: Output from analyze.py run_analysis()
    
    Returns:
        Same schema as interpret_findings() but with template-based content
    """
    # Basic rule-based interpretation
    # Generate simple bobclues
    # Create basic fix plans
```

### Error Handling

```python
class GraniteAPIError(Exception):
    """Raised when Granite API call fails."""

class GraniteResponseError(Exception):
    """Raised when Granite response is malformed."""

def interpret_findings_safe(
    raw_findings: Dict[str, Any],
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
    region: str = "us-south"
) -> Dict[str, Any]:
    """
    Safe wrapper that falls back to template_interpret on errors.
    """
    if not api_key or not project_id:
        return template_interpret(raw_findings)
    
    try:
        return interpret_findings(raw_findings, api_key, project_id, region)
    except (GraniteAPIError, GraniteResponseError) as e:
        # Log error
        # Fall back to template
        return template_interpret(raw_findings)
```

---

## Exact JSON Schemas

### Layer 1 Output (analyze.py)

```json
{
  "timestamp": "2026-05-02T07:00:00.000Z",
  "project_path": "/path/to/project",
  "raw_findings": [
    {
      "finding_type": "npm_audit",
      "raw_data": {
        "vulnerabilities": {
          "express": {
            "name": "express",
            "severity": "high",
            "via": ["body-parser"],
            "effects": [],
            "range": "4.0.0 - 4.17.0",
            "nodes": ["node_modules/express"],
            "fixAvailable": true
          }
        },
        "metadata": {
          "vulnerabilities": {
            "info": 0,
            "low": 2,
            "moderate": 5,
            "high": 3,
            "critical": 1,
            "total": 11
          }
        }
      },
      "metadata": {
        "tool": "npm",
        "timestamp": "2026-05-02T07:00:00.000Z",
        "project_path": "/path/to/project"
      }
    },
    {
      "finding_type": "depcheck",
      "raw_data": {
        "dependencies": ["body-parser", "lodash"],
        "devDependencies": ["eslint-plugin-unused"],
        "missing": {
          "axios": ["src/api/client.js"]
        },
        "using": {
          "express": ["src/app.js", "src/routes/index.js"]
        }
      },
      "metadata": {
        "tool": "depcheck",
        "timestamp": "2026-05-02T07:00:01.000Z",
        "project_path": "/path/to/project"
      }
    },
    {
      "finding_type": "circular_deps",
      "raw_data": {
        "circular": [
          ["src/services/ProductService.js", "src/services/OrderService.js"],
          ["src/utils/logger.js", "src/config/index.js", "src/utils/logger.js"]
        ],
        "method": "madge"
      },
      "metadata": {
        "tool": "madge",
        "timestamp": "2026-05-02T07:00:02.000Z",
        "project_path": "/path/to/project"
      }
    },
    {
      "finding_type": "node_version",
      "raw_data": {
        "package_json_engines": ">=18.0.0",
        "nvmrc_version": "18.16.0",
        "current_version": "20.10.0",
        "mismatches": [
          {
            "type": "current_vs_nvmrc",
            "expected": "18.16.0",
            "actual": "20.10.0"
          }
        ]
      },
      "metadata": {
        "tool": "node",
        "timestamp": "2026-05-02T07:00:03.000Z",
        "project_path": "/path/to/project"
      }
    }
  ],
  "errors": []
}
```

### Layer 2 Output (granite_interpreter.py)

```json
{
  "interpreted_issues": [
    {
      "title": "Critical: Express vulnerable to prototype pollution",
      "explanation": "Express 4.17.0 has a high-severity vulnerability (CVE-2022-24999) that allows prototype pollution attacks through body-parser. This can lead to remote code execution.",
      "bobclue": "DO NOT use req.body without validating and sanitizing input. DO NOT upgrade Express alone - also check body-parser compatibility. DO NOT ignore this vulnerability in production environments.",
      "severity": "critical",
      "fix": "Run: npm install express@latest\nVerify: npm audit\nTest all routes that use req.body after upgrade"
    },
    {
      "title": "Unused dependency: body-parser",
      "explanation": "body-parser is installed but not used anywhere in the codebase. Express 4.16+ includes body-parser middleware built-in, making this package redundant.",
      "bobclue": "DO NOT add new imports of body-parser. DO NOT use require('body-parser') - use express.json() and express.urlencoded() instead.",
      "severity": "medium",
      "fix": "Remove from package.json: npm uninstall body-parser\nReplace any bodyParser.json() with express.json()\nReplace any bodyParser.urlencoded() with express.urlencoded()"
    },
    {
      "title": "Circular dependency: ProductService ↔ OrderService",
      "explanation": "ProductService and OrderService import each other, creating a circular dependency. This can cause initialization issues and makes the code harder to maintain.",
      "bobclue": "DO NOT add more imports between these services. DO NOT try to fix by adding a third service that imports both - this creates more coupling. DO NOT ignore this - it will cause runtime errors.",
      "severity": "high",
      "fix": "Option 1: Extract shared logic to a new InventoryService\nOption 2: Use dependency injection\nOption 3: Move one import to function scope (lazy load)\nVerify fix: npx madge --circular ."
    },
    {
      "title": "Node version mismatch: .nvmrc vs current",
      "explanation": ".nvmrc specifies Node 18.16.0 but you're running 20.10.0. While package.json allows >=18.0.0, team members using .nvmrc will have a different environment.",
      "bobclue": "DO NOT commit code that only works on Node 20. DO NOT update .nvmrc without team consensus. DO NOT assume all Node 18 features work the same in Node 20.",
      "severity": "medium",
      "fix": "Option 1: Update .nvmrc to match current: echo '20.10.0' > .nvmrc\nOption 2: Switch to .nvmrc version: nvm use\nOption 3: Update package.json engines to be more specific"
    }
  ],
  "circular_constraint_pairs": [
    {
      "package_a": "ProductService",
      "package_b": "OrderService",
      "reason": "Mutual imports create initialization deadlock"
    }
  ],
  "coordinated_fix_plan": {
    "install_command": "npm install express@latest",
    "uninstall_command": "npm uninstall body-parser lodash eslint-plugin-unused",
    "warning": "After running these commands: 1) Replace all body-parser usage with express built-ins, 2) Refactor ProductService/OrderService circular dependency, 3) Run npm audit to verify security fixes, 4) Test all API endpoints"
  }
}
```

---

## Implementation Strategy

### Phase 1: Layer 1 Refactoring
1. Create backup of current analyze.py
2. Add npm audit integration
3. Add depcheck integration
4. Refactor existing functions to return raw findings
5. Update run_analysis() to aggregate raw findings
6. Test with existing test_project

### Phase 2: Layer 2 Implementation
1. Create granite_interpreter.py
2. Implement Granite API integration
3. Implement template_interpret fallback
4. Add error handling and validation
5. Test with sample raw findings

### Phase 3: Integration
1. Update API route to use both layers
2. Add configuration for Granite credentials
3. Test end-to-end flow
4. Update documentation

---

## Error Handling Strategy

### Layer 1 Errors
- **npm not installed**: Return error finding, continue with other checks
- **npm audit fails**: Return error finding with details
- **depcheck not available**: Try to install, fallback to warning
- **madge fails**: Use manual circular detection fallback
- **Node version check fails**: Return error finding

### Layer 2 Errors
- **No Granite credentials**: Automatically use template_interpret
- **Granite API timeout**: Retry once, then fallback to template_interpret
- **Malformed Granite response**: Log error, use template_interpret
- **Invalid JSON from Granite**: Parse what's possible, fill gaps with templates

---

## Testing Plan

### Layer 1 Tests
- Test npm audit with vulnerable packages
- Test depcheck with unused dependencies
- Test circular dependency detection
- Test Node version mismatches
- Test error handling for missing tools

### Layer 2 Tests
- Test Granite API integration with valid credentials
- Test template_interpret fallback
- Test malformed response handling
- Test schema validation
- Test coordinated fix plan generation

### Integration Tests
- Test full flow: analyze.py → granite_interpreter.py
- Test with real project (scanner/test_project)
- Test error scenarios end-to-end

---

## Migration Notes

### Breaking Changes
- `run_analysis()` output format completely changed
- No more hardcoded bobclues in analyze.py
- API consumers must update to handle new format

### Backward Compatibility
- Keep old analyze.py as analyze_legacy.py for reference
- Provide migration guide for API consumers
- Consider versioned API endpoints (/api/v1/analyze vs /api/v2/analyze)

---

## Dependencies to Add

```json
{
  "dependencies": {
    "requests": "for Granite API calls (Python)",
    "ibm-watson-machine-learning": "optional IBM SDK"
  }
}
```

### npm tools (must be available)
- `npm` (for npm audit)
- `npx depcheck` (for unused deps)
- `npx madge` (for circular deps - already used)

---

## Configuration

### Environment Variables
```bash
GRANITE_API_KEY=your_ibm_cloud_api_key
GRANITE_PROJECT_ID=your_watsonx_project_id
GRANITE_REGION=us-south  # or eu-de, jp-tok, etc.
GRANITE_MODEL_ID=ibm/granite-13b-chat-v2  # optional override
```

### Fallback Behavior
- If no credentials: Use template_interpret automatically
- If API fails: Log error, use template_interpret
- If response malformed: Parse what's possible, fill gaps

---

## Success Criteria

✅ Layer 1 returns only raw findings (no bobclues)
✅ npm audit integration working
✅ depcheck integration working
✅ Circular deps and Node version checks preserved
✅ Layer 2 calls Granite API successfully
✅ Layer 2 returns exact JSON schema
✅ template_interpret fallback works
✅ Error handling graceful at all levels
✅ All tests passing
✅ Documentation updated
