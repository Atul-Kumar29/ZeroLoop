# ZeroLoop Two-Layer Upgrade - Implementation Summary

## Quick Overview

**Goal**: Replace hardcoded conflict rules with AI-powered interpretation using IBM watsonx.ai Granite.

**Approach**: Two-layer architecture
- **Layer 1** ([`analyze.py`](scanner/analyze.py)): Collect raw findings only
- **Layer 2** ([`granite_interpreter.py`](scanner/granite_interpreter.py)): AI interpretation with Granite

---

## Layer 1: Changes to analyze.py

### Functions to REMOVE
```python
# These hardcoded conflict checkers will be replaced by npm audit
_check_express_bodyparser_conflict()
_check_mongoose_mongodb_conflict()
_check_multiple_logging_libraries()
```

### Functions to ADD
```python
def check_npm_audit(project_path: str) -> Dict[str, Any]:
    """Run npm audit and return raw vulnerability data."""
    # Execute: npm audit --json
    # Return raw findings (no bobclues)

def check_depcheck(project_path: str) -> Dict[str, Any]:
    """Run depcheck to find unused and missing dependencies."""
    # Execute: npx depcheck --json
    # Return raw findings (no bobclues)
```

### Functions to MODIFY

#### 1. `check_dependency_conflicts()` → DELETE
Replace with `check_npm_audit()` and `check_depcheck()`

#### 2. `check_circular_dependencies()` → MODIFY
**Before**: Returns issues with bobclues and explanations
```python
{
    "type": "error",
    "category": "circular-deps",
    "title": "Circular dependency detected",
    "detail": "Circular dependency chain: A → B → A",
    "bobclue": "DO NOT add more imports...",
    "fix": "Break the circular dependency..."
}
```

**After**: Returns raw findings only
```python
{
    "finding_type": "circular_deps",
    "raw_data": {
        "circular": [["A.js", "B.js"]],
        "method": "madge"
    },
    "metadata": {
        "tool": "madge",
        "timestamp": "...",
        "project_path": "..."
    }
}
```

#### 3. `check_node_version()` → MODIFY
**Before**: Returns issues with bobclues
```python
{
    "type": "incompatibility",
    "category": "node-version",
    "title": "Node version mismatch",
    "detail": "Current: 20.10.0, Required: >=18.0.0",
    "bobclue": "DO NOT commit code...",
    "fix": "Update .nvmrc..."
}
```

**After**: Returns raw findings only
```python
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
    "metadata": {...}
}
```

#### 4. `run_analysis()` → MODIFY
**Before**: Returns status, summary, and interpreted issues
```python
{
    "status": "BLOCKED|CAUTION|CLEARED",
    "status_message": "...",
    "timestamp": "...",
    "summary": {
        "total_issues": 5,
        "by_type": {...},
        "by_category": {...}
    },
    "issues": [...]  # With bobclues
}
```

**After**: Returns only raw findings
```python
{
    "timestamp": "...",
    "project_path": "...",
    "raw_findings": [
        {...},  # npm_audit
        {...},  # depcheck
        {...},  # circular_deps
        {...}   # node_version
    ],
    "errors": []
}
```

### Helper Functions to KEEP
```python
_normalize_node_version()
_parse_version()
_versions_compatible()
_compare_node_versions()
_check_current_vs_required()
_check_current_vs_nvmrc()
_find_cycles_dfs()
_check_circular_with_madge()
_check_circular_manual()
```

---

## Layer 2: New File granite_interpreter.py

### File Structure
```python
"""
ZeroLoop Granite AI Interpreter
Interprets raw findings using IBM watsonx.ai Granite models.
"""

import json
import requests
from typing import Dict, Any, List, Optional

# Configuration
GRANITE_API_ENDPOINT = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation"
GRANITE_MODEL_ID = "ibm/granite-13b-chat-v2"

# Main Functions
def interpret_findings(raw_findings, api_key, project_id, region) -> Dict:
    """Call Granite API to interpret raw findings."""
    
def template_interpret(raw_findings) -> Dict:
    """Fallback interpreter without Granite."""
    
def interpret_findings_safe(raw_findings, api_key, project_id, region) -> Dict:
    """Safe wrapper with automatic fallback."""

# Helper Functions
def _call_granite_api(prompt, api_key, project_id, region) -> str:
    """Make HTTP request to Granite API."""
    
def _parse_granite_response(response_text) -> Dict:
    """Parse and validate Granite JSON response."""
    
def _validate_interpretation_schema(data) -> bool:
    """Ensure response matches expected schema."""
    
def _build_granite_prompt(raw_findings) -> str:
    """Build prompt for Granite API."""

# Error Classes
class GraniteAPIError(Exception):
    """Raised when Granite API call fails."""
    
class GraniteResponseError(Exception):
    """Raised when Granite response is malformed."""
```

### Key Implementation Details

#### Granite Prompt Template
```python
GRANITE_PROMPT_TEMPLATE = """You are a Node.js dependency expert analyzing project issues.

Given these raw findings from automated tools:
{raw_findings_json}

Analyze and provide:
1. Interpreted issues with Bob-specific guidance (bobclues starting with "DO NOT")
2. Circular dependency constraint pairs
3. A coordinated fix plan with npm commands

Return ONLY valid JSON in this exact schema:
{
  "interpreted_issues": [...],
  "circular_constraint_pairs": [...],
  "coordinated_fix_plan": {...}
}

Rules:
- All bobclues MUST start with "DO NOT"
- Severity must be: critical, high, or medium
- Coordinated fix plan must consider all issues together
"""
```

#### API Call Implementation
```python
def _call_granite_api(prompt, api_key, project_id, region):
    url = f"https://{region}.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    body = {
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 2000,
            "temperature": 0.7
        },
        "model_id": GRANITE_MODEL_ID,
        "project_id": project_id
    }
    
    response = requests.post(url, headers=headers, json=body, timeout=30)
    
    if response.status_code != 200:
        raise GraniteAPIError(f"API returned {response.status_code}")
    
    return response.json()["results"][0]["generated_text"]
```

#### Template Fallback
```python
def template_interpret(raw_findings):
    """Generate basic interpretation without Granite."""
    interpreted_issues = []
    
    # Process npm_audit findings
    for finding in raw_findings.get("raw_findings", []):
        if finding["finding_type"] == "npm_audit":
            vulnerabilities = finding["raw_data"]["vulnerabilities"]
            for pkg, vuln in vulnerabilities.items():
                interpreted_issues.append({
                    "title": f"Vulnerability in {pkg}",
                    "explanation": f"Security issue: {vuln.get('severity', 'unknown')} severity",
                    "bobclue": f"DO NOT use {pkg} until updated",
                    "severity": vuln.get("severity", "medium"),
                    "fix": f"Run: npm install {pkg}@latest"
                })
    
    # Process depcheck findings
    # Process circular_deps findings
    # Process node_version findings
    
    return {
        "interpreted_issues": interpreted_issues,
        "circular_constraint_pairs": [],
        "coordinated_fix_plan": {
            "install_command": "npm install",
            "uninstall_command": None,
            "warning": "Review all changes before applying"
        }
    }
```

---

## Exact JSON Schemas

### Layer 1 Output Schema
```typescript
interface RawFindingsOutput {
  timestamp: string;           // ISO-8601
  project_path: string;
  raw_findings: RawFinding[];
  errors: ErrorFinding[];
}

interface RawFinding {
  finding_type: "npm_audit" | "depcheck" | "circular_deps" | "node_version";
  raw_data: any;              // Tool-specific data
  metadata: {
    tool: string;
    timestamp: string;
    project_path: string;
  };
}
```

### Layer 2 Output Schema
```typescript
interface InterpretedOutput {
  interpreted_issues: InterpretedIssue[];
  circular_constraint_pairs: CircularConstraint[];
  coordinated_fix_plan: FixPlan;
}

interface InterpretedIssue {
  title: string;
  explanation: string;
  bobclue: string;            // Must start with "DO NOT"
  severity: "critical" | "high" | "medium";
  fix: string;
}

interface CircularConstraint {
  package_a: string;
  package_b: string;
  reason: string;
}

interface FixPlan {
  install_command: string;
  uninstall_command: string | null;
  warning: string;
}
```

---

## Integration Example

### Before (Current)
```python
# In API route
from scanner.analyze import run_analysis

result = run_analysis(project_path)
# result already has bobclues and interpretations
return result
```

### After (Two-Layer)
```python
# In API route
from scanner.analyze import run_analysis
from scanner.granite_interpreter import interpret_findings_safe

# Layer 1: Get raw findings
raw_findings = run_analysis(project_path)

# Layer 2: Interpret with Granite (or fallback)
interpreted = interpret_findings_safe(
    raw_findings,
    api_key=os.getenv("GRANITE_API_KEY"),
    project_id=os.getenv("GRANITE_PROJECT_ID"),
    region=os.getenv("GRANITE_REGION", "us-south")
)

# Combine for response
result = {
    "raw_findings": raw_findings,
    "interpretation": interpreted,
    "timestamp": raw_findings["timestamp"]
}

return result
```

---

## Testing Strategy

### Layer 1 Tests
```bash
# Test npm audit integration
cd scanner/test_project
npm audit --json  # Verify output format

# Test depcheck integration
npx depcheck --json  # Verify output format

# Test with Python
python -c "
from scanner.analyze import run_analysis
result = run_analysis('scanner/test_project')
print(result)
"
```

### Layer 2 Tests
```bash
# Test template fallback (no credentials)
python -c "
from scanner.granite_interpreter import template_interpret
result = template_interpret({'raw_findings': []})
print(result)
"

# Test with Granite (requires credentials)
python -c "
from scanner.granite_interpreter import interpret_findings_safe
result = interpret_findings_safe(
    raw_findings,
    api_key='your_key',
    project_id='your_project'
)
print(result)
"
```

---

## Migration Checklist

- [ ] Backup current [`analyze.py`](scanner/analyze.py) as `analyze_legacy.py`
- [ ] Remove hardcoded conflict functions from [`analyze.py`](scanner/analyze.py)
- [ ] Add `check_npm_audit()` to [`analyze.py`](scanner/analyze.py)
- [ ] Add `check_depcheck()` to [`analyze.py`](scanner/analyze.py)
- [ ] Modify `check_circular_dependencies()` to return raw findings
- [ ] Modify `check_node_version()` to return raw findings
- [ ] Modify `run_analysis()` to aggregate raw findings only
- [ ] Create [`granite_interpreter.py`](scanner/granite_interpreter.py)
- [ ] Implement `interpret_findings()` with Granite API
- [ ] Implement `template_interpret()` fallback
- [ ] Implement error handling and validation
- [ ] Update API route to use both layers
- [ ] Add environment variables for Granite credentials
- [ ] Test with [`scanner/test_project`](scanner/test_project)
- [ ] Update documentation

---

## Environment Setup

### Required Environment Variables
```bash
# .env file
GRANITE_API_KEY=your_ibm_cloud_api_key_here
GRANITE_PROJECT_ID=your_watsonx_project_id_here
GRANITE_REGION=us-south
GRANITE_MODEL_ID=ibm/granite-13b-chat-v2  # optional
```

### Required npm Tools
```bash
# npm audit - built into npm (no install needed)
npm audit --version

# depcheck - will be auto-installed via npx
npx depcheck --version

# madge - already in use
npx madge --version
```

---

## Success Criteria

✅ **Layer 1 Complete**
- `check_npm_audit()` returns raw vulnerability data
- `check_depcheck()` returns raw unused/missing deps
- `check_circular_dependencies()` returns raw circular chains
- `check_node_version()` returns raw version mismatches
- `run_analysis()` aggregates all raw findings
- NO bobclues or interpretations in Layer 1

✅ **Layer 2 Complete**
- `interpret_findings()` calls Granite API successfully
- Returns exact JSON schema with interpreted_issues
- `template_interpret()` works as fallback
- Error handling graceful at all levels
- Malformed responses handled properly

✅ **Integration Complete**
- API route uses both layers
- Environment variables configured
- Tests passing
- Documentation updated
