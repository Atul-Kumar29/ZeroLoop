#!/usr/bin/env python3
"""
ZeroLoop Context Injector

A CLI tool that runs complete ZeroLoop analysis and outputs Bob context to stdout.
Designed for easy copy-paste into IBM Bob IDE.

Usage:
    python3 zeroloop-inject.py ./my-project              # Full Bob context
    python3 zeroloop-inject.py ./my-project --reset      # Reset context only
    python3 zeroloop-inject.py ./my-project --no-ai      # Skip Granite, use template

Environment Variables:
    GRANITE_API_KEY      IBM Cloud API key for Granite
    GRANITE_PROJECT_ID   watsonx.ai project ID
    GRANITE_REGION       IBM Cloud region (default: us-south)
"""

import sys
import os
import json
import argparse
from pathlib import Path


def main():
    """Main entry point for ZeroLoop context injection."""
    
    # Set UTF-8 encoding for stdout on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    """Main entry point for ZeroLoop context injection."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='ZeroLoop - Generate Bob context for dependency analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 zeroloop-inject.py ./my-project
  python3 zeroloop-inject.py ./my-project --reset
  python3 zeroloop-inject.py ./my-project --no-ai
  
Environment Variables:
  GRANITE_API_KEY      IBM Cloud API key
  GRANITE_PROJECT_ID   watsonx.ai project ID
  GRANITE_REGION       IBM Cloud region (default: us-south)
'''
    )
    
    parser.add_argument(
        'project_path',
        help='Path to Node.js project directory'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Output reset context only (short circuit breaker reminder)'
    )
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Skip Granite AI, use template fallback'
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.project_path).resolve()
    
    if not project_path.exists():
        print(f"Error: Project path does not exist: {args.project_path}", file=sys.stderr)
        print("Please provide a valid path to your Node.js project directory.", file=sys.stderr)
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {args.project_path}", file=sys.stderr)
        sys.exit(1)
    
    # Check for package.json (warning only, not fatal)
    package_json = project_path / "package.json"
    if not package_json.exists():
        print("Warning: package.json not found in project directory", file=sys.stderr)
        print("Analysis will be limited without package.json", file=sys.stderr)
        print("", file=sys.stderr)
    
    # Import ZeroLoop modules
    try:
        from scanner.analyze import run_analysis
        from scanner.granite_interpreter import interpret_findings_safe, template_interpret
        from scanner.bob_context_generator import generate_bob_context, generate_reset_context
    except ImportError as e:
        print(f"Error: Failed to import ZeroLoop modules: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Make sure you're running this script from the ZeroLoop project root.", file=sys.stderr)
        print("Required modules: scanner/analyze.py, scanner/granite_interpreter.py, scanner/bob_context_generator.py", file=sys.stderr)
        sys.exit(1)
    
    # Get Granite credentials from environment
    api_key = None
    project_id = None
    region = 'us-south'
    
    if not args.no_ai:
        api_key = os.getenv('GRANITE_API_KEY')
        project_id = os.getenv('GRANITE_PROJECT_ID')
        region = os.getenv('GRANITE_REGION', 'us-south')
        
        if api_key and project_id:
            print(f"Using Granite AI interpretation (region: {region})", file=sys.stderr)
        else:
            print("Using template-based interpretation", file=sys.stderr)
    else:
        print("Using template-based interpretation (--no-ai flag)", file=sys.stderr)
    
    print("", file=sys.stderr)
    
    # ============================================================
    # LAYER 1: Run analyze.py for raw findings
    # ============================================================
    print("Running Layer 1: Raw findings analysis...", file=sys.stderr)
    
    try:
        raw_findings = run_analysis(str(project_path))
    except Exception as e:
        print(f"Error: Layer 1 analysis failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ Found {len(raw_findings.get('raw_findings', []))} raw findings", file=sys.stderr)
    print("", file=sys.stderr)
    
    # ============================================================
    # LAYER 2: Run granite_interpreter.py for AI interpretation
    # ============================================================
    print("Running Layer 2: AI interpretation...", file=sys.stderr)
    
    try:
        if args.no_ai or not api_key or not project_id:
            # Use template fallback
            interpretation = template_interpret(raw_findings)
            print("✓ Template-based interpretation complete", file=sys.stderr)
        else:
            # Try Granite API with automatic fallback
            interpretation = interpret_findings_safe(
                raw_findings,
                api_key=api_key,
                project_id=project_id,
                region=region
            )
            print("✓ AI interpretation complete", file=sys.stderr)
    except Exception as e:
        print(f"Error: Layer 2 interpretation failed: {e}", file=sys.stderr)
        print("Attempting template fallback...", file=sys.stderr)
        try:
            interpretation = template_interpret(raw_findings)
            print("✓ Template fallback successful", file=sys.stderr)
        except Exception as fallback_error:
            print(f"Error: Template fallback also failed: {fallback_error}", file=sys.stderr)
            sys.exit(1)
    
    print("", file=sys.stderr)
    
    # ============================================================
    # LAYER 3: Combine and generate Bob context
    # ============================================================
    print("Running Layer 3: Bob context generation...", file=sys.stderr)
    
    # Combine raw findings and interpretation
    combined_result = {
        **raw_findings,
        'granite_interpretation': interpretation,
        'status': 'CLEARED',
        'status_message': '',
        'summary': {
            'total_issues': len(interpretation.get('interpreted_issues', [])),
            'by_type': {}
        },
        'issues': interpretation.get('interpreted_issues', [])
    }
    
    # Calculate clearance status
    interpreted_issues = interpretation.get('interpreted_issues', [])
    critical_count = sum(1 for i in interpreted_issues if i.get('severity') == 'critical')
    high_count = sum(1 for i in interpreted_issues if i.get('severity') == 'high')
    
    if critical_count > 0:
        combined_result['status'] = 'BLOCKED'
        combined_result['status_message'] = f"Found {critical_count} critical issue(s) that must be resolved before proceeding."
    elif high_count > 0:
        combined_result['status'] = 'CAUTION'
        combined_result['status_message'] = f"Found {high_count} high-priority issue(s). Review carefully before proceeding."
    else:
        combined_result['status'] = 'CLEARED'
        combined_result['status_message'] = 'No critical issues detected. Safe to proceed.'
    
    # Calculate summary by type
    by_type = {
        'error': 0,
        'incompatibility': 0,
        'conflict': 0,
        'redundancy': 0,
        'warning': 0,
        'info': 0
    }
    
    for issue in interpreted_issues:
        severity = issue.get('severity', 'medium')
        if severity == 'critical':
            by_type['error'] += 1
        elif severity == 'high':
            by_type['conflict'] += 1
        else:
            by_type['warning'] += 1
    
    combined_result['summary']['by_type'] = by_type
    
    # Generate appropriate context
    try:
        if args.reset:
            # Generate reset context only
            context = generate_reset_context(combined_result)
            print("✓ Reset context generated", file=sys.stderr)
        else:
            # Generate full Bob context
            context = generate_bob_context(combined_result)
            print("✓ Full Bob context generated", file=sys.stderr)
    except Exception as e:
        print(f"Error: Layer 3 context generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    # ============================================================
    # Output context to stdout (clean, no extra messages)
    # ============================================================
    print(context)
    
    # Print completion message to stderr
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("✓ Context generation complete!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Exit successfully
    sys.exit(0)


if __name__ == '__main__':
    main()

# Made with Bob