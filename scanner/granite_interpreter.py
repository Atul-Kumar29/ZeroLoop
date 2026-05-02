"""
ZeroLoop Granite AI Interpreter - Layer 2

Interprets raw findings from analyze.py using IBM watsonx.ai Granite models.
Provides bobclues, explanations, and coordinated fix plans.
"""

import json
import os
from typing import Dict, Any, List, Optional
import requests


# Granite API Configuration
GRANITE_API_BASE = "https://{region}.ml.cloud.ibm.com/ml/v1"
GRANITE_MODEL_ID = "ibm/granite-13b-chat-v2"
GRANITE_API_VERSION = "2023-05-29"


class GraniteAPIError(Exception):
    """Raised when Granite API call fails."""
    pass


class GraniteResponseError(Exception):
    """Raised when Granite response is malformed."""
    pass


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
    
    Raises:
        GraniteAPIError: If API call fails
        GraniteResponseError: If response is malformed
    """
    # Build prompt for Granite
    prompt = _build_granite_prompt(raw_findings)
    
    # Call Granite API
    response_text = _call_granite_api(prompt, api_key, project_id, region)
    
    # Parse and validate response
    interpretation = _parse_granite_response(response_text)
    
    # Validate schema
    if not _validate_interpretation_schema(interpretation):
        raise GraniteResponseError("Response does not match expected schema")
    
    return interpretation


def template_interpret(raw_findings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback interpreter when no Granite credentials provided.
    Generates basic bobclues using template logic.
    
    Args:
        raw_findings: Output from analyze.py run_analysis()
    
    Returns:
        Same schema as interpret_findings() but with template-based content
    """
    interpreted_issues = []
    circular_constraint_pairs = []
    install_packages = []
    uninstall_packages = []
    
    # Process each raw finding
    for finding in raw_findings.get("raw_findings", []):
        finding_type = finding.get("finding_type")
        raw_data = finding.get("raw_data", {})
        
        if finding_type == "npm_audit":
            # Process npm audit vulnerabilities
            vulnerabilities = raw_data.get("vulnerabilities", {})
            if vulnerabilities and not raw_data.get("error"):
                for pkg_name, vuln_data in vulnerabilities.items():
                    if isinstance(vuln_data, dict):
                        severity = vuln_data.get("severity", "medium")
                        # Map npm severity to our severity levels
                        if severity in ["critical", "high"]:
                            our_severity = severity
                        else:
                            our_severity = "medium"
                        
                        interpreted_issues.append({
                            "title": f"Security vulnerability in {pkg_name}",
                            "explanation": f"Package {pkg_name} has a {severity} severity vulnerability. This could expose your application to security risks.",
                            "bobclue": f"DO NOT use {pkg_name} in production until updated. DO NOT ignore security vulnerabilities. DO NOT downgrade to avoid the issue.",
                            "severity": our_severity,
                            "fix": f"Update {pkg_name} to the latest secure version: npm install {pkg_name}@latest"
                        })
                        
                        if vuln_data.get("fixAvailable"):
                            install_packages.append(f"{pkg_name}@latest")
        
        elif finding_type == "depcheck":
            # Process unused dependencies
            unused_deps = raw_data.get("dependencies", [])
            unused_dev_deps = raw_data.get("devDependencies", [])
            missing_deps = raw_data.get("missing", {})
            
            if unused_deps:
                interpreted_issues.append({
                    "title": f"Unused dependencies detected ({len(unused_deps)} packages)",
                    "explanation": f"The following packages are installed but not used: {', '.join(unused_deps[:5])}{'...' if len(unused_deps) > 5 else ''}. This increases bundle size and maintenance overhead.",
                    "bobclue": f"DO NOT add imports for these packages just to 'use' them. DO NOT keep unused dependencies 'just in case'. DO NOT remove packages that are used indirectly by other tools.",
                    "severity": "medium",
                    "fix": f"Remove unused packages: npm uninstall {' '.join(unused_deps)}"
                })
                uninstall_packages.extend(unused_deps)
            
            if unused_dev_deps:
                interpreted_issues.append({
                    "title": f"Unused devDependencies detected ({len(unused_dev_deps)} packages)",
                    "explanation": f"The following dev packages are not used: {', '.join(unused_dev_deps[:5])}{'...' if len(unused_dev_deps) > 5 else ''}.",
                    "bobclue": "DO NOT remove devDependencies that are used by npm scripts or CI/CD pipelines.",
                    "severity": "medium",
                    "fix": f"Remove unused dev packages: npm uninstall --save-dev {' '.join(unused_dev_deps)}"
                })
            
            if missing_deps:
                missing_list = list(missing_deps.keys())
                interpreted_issues.append({
                    "title": f"Missing dependencies detected ({len(missing_list)} packages)",
                    "explanation": f"The following packages are used but not in package.json: {', '.join(missing_list[:5])}{'...' if len(missing_list) > 5 else ''}. This will cause runtime errors.",
                    "bobclue": "DO NOT assume these packages are available. DO NOT rely on globally installed packages. DO NOT commit code with missing dependencies.",
                    "severity": "critical",
                    "fix": f"Install missing packages: npm install {' '.join(missing_list)}"
                })
                install_packages.extend(missing_list)
        
        elif finding_type == "circular_deps":
            # Process circular dependencies
            circular = raw_data.get("circular", [])
            if circular:
                for cycle in circular:
                    if isinstance(cycle, list) and len(cycle) >= 2:
                        cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
                        
                        interpreted_issues.append({
                            "title": f"Circular dependency: {len(cycle)} files in cycle",
                            "explanation": f"Circular dependency chain detected: {cycle_str}. This can cause initialization issues and makes code harder to maintain.",
                            "bobclue": "DO NOT add more imports between these files. DO NOT ignore circular dependencies. DO NOT try to fix by adding a third file that imports both.",
                            "severity": "high",
                            "fix": f"Break the cycle by: 1) Extract shared code to a new module, 2) Use dependency injection, 3) Move imports to function scope (lazy load), or 4) Refactor to remove the dependency"
                        })
                        
                        # Add constraint pairs for first two files in cycle
                        if len(cycle) >= 2:
                            circular_constraint_pairs.append({
                                "package_a": cycle[0],
                                "package_b": cycle[1],
                                "reason": "Part of circular dependency chain"
                            })
        
        elif finding_type == "node_version":
            # Process Node version mismatches
            mismatches = raw_data.get("mismatches", [])
            for mismatch in mismatches:
                mismatch_type = mismatch.get("type")
                expected = mismatch.get("expected")
                actual = mismatch.get("actual")
                
                if mismatch_type == "current_vs_required":
                    interpreted_issues.append({
                        "title": "Node version incompatible with package.json",
                        "explanation": f"Currently running Node {actual} but package.json requires {expected}. This may cause runtime errors or unexpected behavior.",
                        "bobclue": "DO NOT run npm install or scripts until Node version is correct. DO NOT modify package.json to match current version without testing. DO NOT ignore this warning.",
                        "severity": "critical",
                        "fix": f"Switch to compatible Node version: nvm install {expected} && nvm use {expected}"
                    })
                
                elif mismatch_type == "current_vs_nvmrc":
                    interpreted_issues.append({
                        "title": "Node version differs from .nvmrc",
                        "explanation": f"Currently running Node {actual} but .nvmrc specifies {expected}. Team members using .nvmrc will have a different environment.",
                        "bobclue": "DO NOT commit code that only works on your Node version. DO NOT update .nvmrc without team consensus.",
                        "severity": "medium",
                        "fix": "Switch to .nvmrc version: nvm use"
                    })
                
                elif mismatch_type == "nvmrc_vs_required":
                    interpreted_issues.append({
                        "title": "Node version mismatch between package.json and .nvmrc",
                        "explanation": f"package.json requires {expected} but .nvmrc specifies {actual}. This creates confusion about which version to use.",
                        "bobclue": "DO NOT modify either file without checking CI/CD configuration. DO NOT assume .nvmrc takes precedence.",
                        "severity": "high",
                        "fix": f"Align versions: Update .nvmrc to match package.json or vice versa"
                    })
    
    # Build coordinated fix plan
    install_command = None
    uninstall_command = None
    warning = "Review all changes before applying. Test thoroughly after updates."
    
    if install_packages:
        # Remove duplicates
        install_packages = list(set(install_packages))
        install_command = f"npm install {' '.join(install_packages)}"
    
    if uninstall_packages:
        # Remove duplicates
        uninstall_packages = list(set(uninstall_packages))
        uninstall_command = f"npm uninstall {' '.join(uninstall_packages)}"
    
    if not install_command and not uninstall_command:
        install_command = "npm install"
        warning = "No package changes needed. Focus on fixing circular dependencies and Node version issues."
    
    return {
        "interpreted_issues": interpreted_issues,
        "circular_constraint_pairs": circular_constraint_pairs,
        "coordinated_fix_plan": {
            "install_command": install_command,
            "uninstall_command": uninstall_command,
            "warning": warning
        }
    }


def interpret_findings_safe(
    raw_findings: Dict[str, Any],
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
    region: str = "us-south"
) -> Dict[str, Any]:
    """
    Safe wrapper that falls back to template_interpret on errors.
    
    Args:
        raw_findings: Output from analyze.py run_analysis()
        api_key: IBM Cloud API key (optional)
        project_id: watsonx.ai project ID (optional)
        region: IBM Cloud region (default: us-south)
    
    Returns:
        Interpreted findings (from Granite or template fallback)
    """
    # If no credentials, use template
    if not api_key or not project_id:
        return template_interpret(raw_findings)
    
    try:
        return interpret_findings(raw_findings, api_key, project_id, region)
    except (GraniteAPIError, GraniteResponseError, Exception) as e:
        # Log error (in production, use proper logging)
        print(f"Warning: Granite API failed ({str(e)}), using template fallback")
        return template_interpret(raw_findings)


def _build_granite_prompt(raw_findings: Dict[str, Any]) -> str:
    """Build prompt for Granite API."""
    
    raw_findings_json = json.dumps(raw_findings, indent=2)
    
    prompt = f"""You are a Node.js dependency expert analyzing project issues.

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
- Be specific and actionable in explanations and fixes
- Consider security, performance, and maintainability

Return ONLY the JSON, no other text."""

    return prompt


def _call_granite_api(
    prompt: str,
    api_key: str,
    project_id: str,
    region: str
) -> str:
    """
    Call IBM watsonx.ai Granite API.
    
    Args:
        prompt: The prompt to send
        api_key: IBM Cloud API key
        project_id: watsonx.ai project ID
        region: IBM Cloud region
    
    Returns:
        Generated text from Granite
    
    Raises:
        GraniteAPIError: If API call fails
    """
    url = f"{GRANITE_API_BASE.format(region=region)}/text/generation?version={GRANITE_API_VERSION}"
    
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
            "min_new_tokens": 100,
            "temperature": 0.7,
            "top_p": 1,
            "top_k": 50,
            "repetition_penalty": 1.0
        },
        "model_id": GRANITE_MODEL_ID,
        "project_id": project_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=60)
        
        if response.status_code == 401:
            raise GraniteAPIError("Authentication failed - check API key")
        elif response.status_code == 403:
            raise GraniteAPIError("Access forbidden - check project ID and permissions")
        elif response.status_code == 404:
            raise GraniteAPIError("Model or endpoint not found - check region and model ID")
        elif response.status_code != 200:
            raise GraniteAPIError(f"API returned status {response.status_code}: {response.text}")
        
        response_data = response.json()
        
        if "results" not in response_data or not response_data["results"]:
            raise GraniteAPIError("No results in API response")
        
        generated_text = response_data["results"][0].get("generated_text", "")
        
        if not generated_text:
            raise GraniteAPIError("Empty generated text from API")
        
        return generated_text
        
    except requests.exceptions.Timeout:
        raise GraniteAPIError("API request timed out (>60s)")
    except requests.exceptions.ConnectionError:
        raise GraniteAPIError("Failed to connect to API - check network connection")
    except requests.exceptions.RequestException as e:
        raise GraniteAPIError(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        raise GraniteAPIError("Failed to parse API response as JSON")


def _parse_granite_response(response_text: str) -> Dict[str, Any]:
    """
    Parse and validate Granite JSON response.
    
    Args:
        response_text: Raw text from Granite API
    
    Returns:
        Parsed JSON object
    
    Raises:
        GraniteResponseError: If response is malformed
    """
    # Try to extract JSON from response (in case there's extra text)
    response_text = response_text.strip()
    
    # Find JSON object boundaries
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}')
    
    if start_idx == -1 or end_idx == -1:
        raise GraniteResponseError("No JSON object found in response")
    
    json_text = response_text[start_idx:end_idx + 1]
    
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise GraniteResponseError(f"Failed to parse JSON: {str(e)}")
    
    return data


def _validate_interpretation_schema(data: Dict[str, Any]) -> bool:
    """
    Validate Granite response matches expected schema.
    
    Args:
        data: Parsed JSON from Granite
    
    Returns:
        True if valid, False otherwise
    """
    # Check required top-level keys
    if not isinstance(data, dict):
        return False
    
    required_keys = ["interpreted_issues", "circular_constraint_pairs", "coordinated_fix_plan"]
    for key in required_keys:
        if key not in data:
            return False
    
    # Validate interpreted_issues
    if not isinstance(data["interpreted_issues"], list):
        return False
    
    for issue in data["interpreted_issues"]:
        if not isinstance(issue, dict):
            return False
        
        required_issue_keys = ["title", "explanation", "bobclue", "severity", "fix"]
        for key in required_issue_keys:
            if key not in issue:
                return False
        
        # Check bobclue starts with "DO NOT"
        if not issue["bobclue"].startswith("DO NOT"):
            return False
        
        # Check severity is valid
        if issue["severity"] not in ["critical", "high", "medium"]:
            return False
    
    # Validate circular_constraint_pairs
    if not isinstance(data["circular_constraint_pairs"], list):
        return False
    
    for pair in data["circular_constraint_pairs"]:
        if not isinstance(pair, dict):
            return False
        
        required_pair_keys = ["package_a", "package_b", "reason"]
        for key in required_pair_keys:
            if key not in pair:
                return False
    
    # Validate coordinated_fix_plan
    if not isinstance(data["coordinated_fix_plan"], dict):
        return False
    
    required_plan_keys = ["install_command", "uninstall_command", "warning"]
    for key in required_plan_keys:
        if key not in data["coordinated_fix_plan"]:
            return False
    
    return True


# For testing
if __name__ == "__main__":
    import sys
    from analyze import run_analysis
    
    # Get raw findings
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "scanner/test_project"
    
    print("Running Layer 1 analysis...")
    raw_findings = run_analysis(project_path)
    
    print("\nRunning Layer 2 interpretation (template fallback)...")
    interpretation = template_interpret(raw_findings)
    
    print("\n=== INTERPRETED RESULTS ===")
    print(json.dumps(interpretation, indent=2))
    
    # Try with Granite if credentials available
    api_key = os.getenv("GRANITE_API_KEY")
    project_id = os.getenv("GRANITE_PROJECT_ID")
    
    if api_key and project_id:
        print("\n\nTrying with Granite API...")
        try:
            granite_interpretation = interpret_findings(raw_findings, api_key, project_id)
            print("\n=== GRANITE INTERPRETATION ===")
            print(json.dumps(granite_interpretation, indent=2))
        except Exception as e:
            print(f"Granite API failed: {str(e)}")

# Made with Bob
