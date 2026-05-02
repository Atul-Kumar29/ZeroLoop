"""
ZeroLoop Dependency Analyzer - Layer 1 (Raw Findings)

Collects raw findings from various tools without interpretation.
All bobclues and explanations are handled by Layer 2 (granite_interpreter.py).
"""

import json
import os
import subprocess
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


def check_npm_audit(project_path: str) -> Dict[str, Any]:
    """
    Run npm audit and return raw vulnerability data.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Raw finding object with npm audit results
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Check if package.json exists
    package_json_path = Path(project_path) / "package.json"
    if not package_json_path.exists():
        return {
            "finding_type": "npm_audit",
            "raw_data": {
                "error": "package.json not found",
                "vulnerabilities": {}
            },
            "metadata": {
                "tool": "npm",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    
    try:
        # Run npm audit --json
        result = subprocess.run(
            ['npm', 'audit', '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_path
        )
        
        # npm audit returns non-zero exit code if vulnerabilities found
        # This is expected, so we parse the output regardless
        try:
            audit_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            audit_data = {
                "error": "Failed to parse npm audit output",
                "raw_output": result.stdout,
                "vulnerabilities": {}
            }
        
        return {
            "finding_type": "npm_audit",
            "raw_data": audit_data,
            "metadata": {
                "tool": "npm",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": True,
                "exit_code": result.returncode
            }
        }
        
    except subprocess.TimeoutExpired:
        return {
            "finding_type": "npm_audit",
            "raw_data": {
                "error": "npm audit timed out (>30s)",
                "vulnerabilities": {}
            },
            "metadata": {
                "tool": "npm",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    except FileNotFoundError:
        return {
            "finding_type": "npm_audit",
            "raw_data": {
                "error": "npm not found - ensure Node.js and npm are installed",
                "vulnerabilities": {}
            },
            "metadata": {
                "tool": "npm",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    except Exception as e:
        return {
            "finding_type": "npm_audit",
            "raw_data": {
                "error": f"Unexpected error running npm audit: {str(e)}",
                "vulnerabilities": {}
            },
            "metadata": {
                "tool": "npm",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }


def check_depcheck(project_path: str) -> Dict[str, Any]:
    """
    Run depcheck to find unused and missing dependencies.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Raw finding object with depcheck results
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Check if package.json exists
    package_json_path = Path(project_path) / "package.json"
    if not package_json_path.exists():
        return {
            "finding_type": "depcheck",
            "raw_data": {
                "error": "package.json not found",
                "dependencies": [],
                "devDependencies": [],
                "missing": {},
                "using": {}
            },
            "metadata": {
                "tool": "depcheck",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    
    try:
        # Run depcheck --json
        result = subprocess.run(
            ['npx', 'depcheck', '--json'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_path
        )
        
        if result.returncode != 0:
            return {
                "finding_type": "depcheck",
                "raw_data": {
                    "error": f"depcheck failed: {result.stderr}",
                    "dependencies": [],
                    "devDependencies": [],
                    "missing": {},
                    "using": {}
                },
                "metadata": {
                    "tool": "depcheck",
                    "timestamp": timestamp,
                    "project_path": str(project_path),
                    "success": False
                }
            }
        
        try:
            depcheck_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            depcheck_data = {
                "error": "Failed to parse depcheck output",
                "raw_output": result.stdout,
                "dependencies": [],
                "devDependencies": [],
                "missing": {},
                "using": {}
            }
        
        return {
            "finding_type": "depcheck",
            "raw_data": depcheck_data,
            "metadata": {
                "tool": "depcheck",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": True
            }
        }
        
    except subprocess.TimeoutExpired:
        return {
            "finding_type": "depcheck",
            "raw_data": {
                "error": "depcheck timed out (>60s)",
                "dependencies": [],
                "devDependencies": [],
                "missing": {},
                "using": {}
            },
            "metadata": {
                "tool": "depcheck",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    except FileNotFoundError:
        return {
            "finding_type": "depcheck",
            "raw_data": {
                "error": "npx not found - ensure Node.js and npm are installed",
                "dependencies": [],
                "devDependencies": [],
                "missing": {},
                "using": {}
            },
            "metadata": {
                "tool": "depcheck",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    except Exception as e:
        return {
            "finding_type": "depcheck",
            "raw_data": {
                "error": f"Unexpected error running depcheck: {str(e)}",
                "dependencies": [],
                "devDependencies": [],
                "missing": {},
                "using": {}
            },
            "metadata": {
                "tool": "depcheck",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }


def check_circular_dependencies(project_path: str) -> Dict[str, Any]:
    """
    Check for circular dependencies using madge.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Raw finding object with circular dependency data
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Check if package.json exists
    package_json_path = Path(project_path) / "package.json"
    if not package_json_path.exists():
        return {
            "finding_type": "circular_deps",
            "raw_data": {
                "error": "package.json not found",
                "circular": [],
                "method": "none"
            },
            "metadata": {
                "tool": "madge",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    
    # Try using madge
    madge_result = _check_circular_with_madge(project_path)
    if madge_result:
        madge_result["metadata"]["timestamp"] = timestamp
        return madge_result
    
    # Fallback to manual analysis
    manual_result = _check_circular_manual(project_path)
    manual_result["metadata"]["timestamp"] = timestamp
    return manual_result


def _check_circular_with_madge(project_path: str) -> Optional[Dict[str, Any]]:
    """
    Use madge to detect circular dependencies.
    Returns None if madge is not available.
    """
    try:
        # Check if madge is available
        result = subprocess.run(
            ['npx', 'madge', '--version'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_path
        )
        
        if result.returncode != 0:
            return None
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None
    
    try:
        # Run madge to detect circular dependencies
        result = subprocess.run(
            ['npx', 'madge', '--circular', '--json', '.'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_path
        )
        
        if result.returncode != 0:
            return {
                "finding_type": "circular_deps",
                "raw_data": {
                    "error": f"madge failed: {result.stderr}",
                    "circular": [],
                    "method": "madge"
                },
                "metadata": {
                    "tool": "madge",
                    "timestamp": "",
                    "project_path": str(project_path),
                    "success": False
                }
            }
        
        # Parse madge output
        try:
            circular_deps = json.loads(result.stdout)
        except json.JSONDecodeError:
            circular_deps = []
        
        return {
            "finding_type": "circular_deps",
            "raw_data": {
                "circular": circular_deps if circular_deps else [],
                "method": "madge"
            },
            "metadata": {
                "tool": "madge",
                "timestamp": "",
                "project_path": str(project_path),
                "success": True
            }
        }
        
    except subprocess.TimeoutExpired:
        return {
            "finding_type": "circular_deps",
            "raw_data": {
                "error": "madge timed out (>30s)",
                "circular": [],
                "method": "madge"
            },
            "metadata": {
                "tool": "madge",
                "timestamp": "",
                "project_path": str(project_path),
                "success": False
            }
        }
    except Exception as e:
        return {
            "finding_type": "circular_deps",
            "raw_data": {
                "error": f"Unexpected error running madge: {str(e)}",
                "circular": [],
                "method": "madge"
            },
            "metadata": {
                "tool": "madge",
                "timestamp": "",
                "project_path": str(project_path),
                "success": False
            }
        }


def _check_circular_manual(project_path: str) -> Dict[str, Any]:
    """
    Manual circular dependency detection as fallback.
    Analyzes require() and import statements.
    """
    dep_graph = {}
    js_files = []
    
    # Find all JS files
    project_root = Path(project_path)
    for ext in ['*.js', '*.jsx', '*.ts', '*.tsx']:
        js_files.extend(project_root.rglob(ext))
    
    # Build dependency graph
    for file_path in js_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            rel_path = str(file_path.relative_to(project_root))
            
            # Find require() statements
            require_pattern = r'require\([\'"](.+?)[\'"]\)'
            requires = re.findall(require_pattern, content)
            
            # Find import statements
            import_pattern = r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]'
            imports = re.findall(import_pattern, content)
            
            all_imports = requires + imports
            normalized = []
            for imp in all_imports:
                # Only track relative imports (circular deps are within project)
                if imp.startswith('.'):
                    # Normalize path
                    potential_path = (file_path.parent / imp).resolve()
                    try:
                        normalized.append(str(potential_path.relative_to(project_root)))
                    except ValueError:
                        pass
            
            dep_graph[rel_path] = normalized
            
        except Exception:
            continue
    
    # Find cycles using DFS
    cycles = _find_cycles_dfs(dep_graph)
    
    return {
        "finding_type": "circular_deps",
        "raw_data": {
            "circular": cycles,
            "method": "manual"
        },
        "metadata": {
            "tool": "manual",
            "timestamp": "",
            "project_path": str(project_path),
            "success": True
        }
    }


def _find_cycles_dfs(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Find all cycles in a dependency graph using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node):
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for dep in graph.get(node, []):
            dfs(dep)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles


def check_node_version(project_path: str) -> Dict[str, Any]:
    """
    Check Node.js version compatibility.
    
    Compares:
    1. engines.node field in package.json
    2. .nvmrc file (if present)
    3. Currently running Node version
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Raw finding object with Node version data
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Read package.json
    package_json_path = Path(project_path) / "package.json"
    
    if not package_json_path.exists():
        return {
            "finding_type": "node_version",
            "raw_data": {
                "error": "package.json not found",
                "package_json_engines": None,
                "nvmrc_version": None,
                "current_version": None,
                "mismatches": []
            },
            "metadata": {
                "tool": "node",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "finding_type": "node_version",
            "raw_data": {
                "error": f"Invalid package.json: {str(e)}",
                "package_json_engines": None,
                "nvmrc_version": None,
                "current_version": None,
                "mismatches": []
            },
            "metadata": {
                "tool": "node",
                "timestamp": timestamp,
                "project_path": str(project_path),
                "success": False
            }
        }
    
    # Get Node version from package.json engines field
    engines = package_data.get("engines", {})
    required_node = engines.get("node")
    
    # Get Node version from .nvmrc
    nvmrc_path = Path(project_path) / ".nvmrc"
    nvmrc_version = None
    if nvmrc_path.exists():
        try:
            with open(nvmrc_path, 'r', encoding='utf-8') as f:
                nvmrc_version = f.read().strip()
        except Exception:
            pass
    
    # Get currently running Node version
    current_node = None
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        current_node = result.stdout.strip()
    except Exception:
        pass
    
    # Compare versions and identify mismatches
    mismatches = []
    
    if required_node and nvmrc_version:
        required_clean = _normalize_node_version(required_node)
        nvmrc_clean = _normalize_node_version(nvmrc_version)
        if required_clean and nvmrc_clean and not _versions_compatible(required_node, nvmrc_clean):
            mismatches.append({
                "type": "nvmrc_vs_required",
                "expected": required_node,
                "actual": nvmrc_version
            })
    
    if required_node and current_node:
        current_clean = _normalize_node_version(current_node)
        if current_clean and not _versions_compatible(required_node, current_clean):
            mismatches.append({
                "type": "current_vs_required",
                "expected": required_node,
                "actual": current_node
            })
    
    if nvmrc_version and current_node:
        nvmrc_clean = _normalize_node_version(nvmrc_version)
        current_clean = _normalize_node_version(current_node)
        if nvmrc_clean and current_clean and nvmrc_clean != current_clean:
            mismatches.append({
                "type": "current_vs_nvmrc",
                "expected": nvmrc_version,
                "actual": current_node
            })
    
    return {
        "finding_type": "node_version",
        "raw_data": {
            "package_json_engines": required_node,
            "nvmrc_version": nvmrc_version,
            "current_version": current_node,
            "mismatches": mismatches
        },
        "metadata": {
            "tool": "node",
            "timestamp": timestamp,
            "project_path": str(project_path),
            "success": True
        }
    }


def _normalize_node_version(version: str) -> Optional[str]:
    """
    Normalize Node version string to major.minor.patch format.
    Handles: v18.17.0, 18.17.0, >=18.0.0, ^18.0.0, ~18.0.0, 18, 18.17
    """
    if not version:
        return None
    
    version = version.strip()
    
    # Remove 'v' prefix
    version = version.lstrip('v')
    
    # Remove range operators for comparison
    version = re.sub(r'^[>=<^~]+', '', version)
    
    # Extract version numbers
    match = re.match(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?', version)
    if match:
        major = match.group(1)
        minor = match.group(2) or '0'
        patch = match.group(3) or '0'
        return f"{major}.{minor}.{patch}"
    
    return None


def _versions_compatible(requirement: str, version: str) -> bool:
    """
    Check if a version satisfies a requirement.
    Handles: >=18.0.0, ^18.0.0, ~18.0.0, 18.17.0, 18.x, *
    """
    requirement = requirement.strip()
    
    # Handle wildcards
    if requirement == '*' or requirement == 'x':
        return True
    
    # Parse version
    version_tuple = _parse_version(version)
    if not version_tuple:
        return False
    
    # Handle >= operator
    if requirement.startswith('>='):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        return version_tuple >= req_tuple if req_tuple else False
    
    # Handle > operator
    if requirement.startswith('>') and not requirement.startswith('>='):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        return version_tuple > req_tuple if req_tuple else False
    
    # Handle <= operator
    if requirement.startswith('<='):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        return version_tuple <= req_tuple if req_tuple else False
    
    # Handle < operator
    if requirement.startswith('<') and not requirement.startswith('<='):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        return version_tuple < req_tuple if req_tuple else False
    
    # Handle ^ (caret) - compatible with version (same major)
    if requirement.startswith('^'):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        if not req_tuple:
            return False
        # Same major version, minor and patch can be higher
        return version_tuple[0] == req_tuple[0] and version_tuple >= req_tuple
    
    # Handle ~ (tilde) - approximately equivalent (same major.minor)
    if requirement.startswith('~'):
        req_version = _normalize_node_version(requirement)
        if not req_version:
            return False
        req_tuple = _parse_version(req_version)
        if not req_tuple:
            return False
        # Same major.minor, patch can be higher
        return (version_tuple[0] == req_tuple[0] and
                version_tuple[1] == req_tuple[1] and
                version_tuple[2] >= req_tuple[2])
    
    # Handle x ranges (18.x, 18.17.x)
    if 'x' in requirement.lower():
        req_parts = requirement.lower().split('.')
        ver_parts = version.split('.')
        for i, req_part in enumerate(req_parts):
            if req_part == 'x':
                return True
            if i >= len(ver_parts) or req_part != ver_parts[i]:
                return False
        return True
    
    # Exact match or range
    req_version = _normalize_node_version(requirement)
    return version == req_version


def _parse_version(version_string: str) -> Optional[tuple]:
    """
    Parse a semver version string into comparable tuple.
    Handles ^, ~, >=, >, <, <=, and exact versions.
    
    Returns: (major, minor, patch) or None if unparseable
    """
    # Remove common prefixes
    version_string = version_string.strip()
    version_string = re.sub(r'^[\^~>=<]+', '', version_string)
    
    # Extract version numbers
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    
    # Try major.minor format
    match = re.match(r'(\d+)\.(\d+)', version_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), 0)
    
    # Try major only
    match = re.match(r'(\d+)', version_string)
    if match:
        return (int(match.group(1)), 0, 0)
    
    return None


def run_analysis(project_path: str) -> Dict[str, Any]:
    """
    Run all analyzers and aggregate raw findings.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Dictionary with:
        - timestamp: ISO timestamp of analysis
        - project_path: Path analyzed
        - raw_findings: List of all raw findings from all analyzers
        - errors: List of any analyzer errors
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    
    raw_findings = []
    errors = []
    
    # Run npm audit
    try:
        npm_finding = check_npm_audit(project_path)
        raw_findings.append(npm_finding)
        if not npm_finding["metadata"]["success"]:
            errors.append({
                "analyzer": "npm_audit",
                "error": npm_finding["raw_data"].get("error", "Unknown error")
            })
    except Exception as e:
        errors.append({
            "analyzer": "npm_audit",
            "error": f"Unexpected error: {str(e)}"
        })
    
    # Run depcheck
    try:
        depcheck_finding = check_depcheck(project_path)
        raw_findings.append(depcheck_finding)
        if not depcheck_finding["metadata"]["success"]:
            errors.append({
                "analyzer": "depcheck",
                "error": depcheck_finding["raw_data"].get("error", "Unknown error")
            })
    except Exception as e:
        errors.append({
            "analyzer": "depcheck",
            "error": f"Unexpected error: {str(e)}"
        })
    
    # Run circular dependency check
    try:
        circular_finding = check_circular_dependencies(project_path)
        raw_findings.append(circular_finding)
        if not circular_finding["metadata"]["success"]:
            errors.append({
                "analyzer": "circular_deps",
                "error": circular_finding["raw_data"].get("error", "Unknown error")
            })
    except Exception as e:
        errors.append({
            "analyzer": "circular_deps",
            "error": f"Unexpected error: {str(e)}"
        })
    
    # Run Node version check
    try:
        node_finding = check_node_version(project_path)
        raw_findings.append(node_finding)
        if not node_finding["metadata"]["success"]:
            errors.append({
                "analyzer": "node_version",
                "error": node_finding["raw_data"].get("error", "Unknown error")
            })
    except Exception as e:
        errors.append({
            "analyzer": "node_version",
            "error": f"Unexpected error: {str(e)}"
        })
    
    return {
        "timestamp": timestamp,
        "project_path": str(project_path),
        "raw_findings": raw_findings,
        "errors": errors
    }


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "scanner/test_project"
    
    result = run_analysis(project_path)
    print(json.dumps(result, indent=2))

# Made with Bob
