"""
ZeroLoop Dependency Conflict Analyzer

Analyzes Node.js projects for known dependency conflicts and provides
Bob-specific guidance on how to handle them.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


def check_dependency_conflicts(project_path: str) -> List[Dict[str, Any]]:
    """
    Check for known dependency conflicts in a Node.js project.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        List of issue objects with fields:
        - type: Issue type (e.g., "conflict", "redundancy", "incompatibility")
        - category: Category (e.g., "dependencies", "logging")
        - title: Short issue title
        - detail: Detailed description
        - bobclue: Critical guidance for Bob on what NOT to do
        - fix: Recommended fix
    """
    issues = []
    
    # Read package.json
    package_json_path = Path(project_path) / "package.json"
    
    if not package_json_path.exists():
        return [{
            "type": "error",
            "category": "setup",
            "title": "package.json not found",
            "detail": f"No package.json found at {project_path}",
            "bobclue": "DO NOT attempt to install packages or run npm commands until package.json exists",
            "fix": "Initialize project with 'npm init' first"
        }]
    
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
    except json.JSONDecodeError as e:
        return [{
            "type": "error",
            "category": "setup",
            "title": "Invalid package.json",
            "detail": f"Failed to parse package.json: {str(e)}",
            "bobclue": "DO NOT modify package.json until syntax errors are fixed",
            "fix": "Fix JSON syntax errors in package.json"
        }]
    
    # Combine all dependencies
    all_deps = {}
    all_deps.update(package_data.get("dependencies", {}))
    all_deps.update(package_data.get("devDependencies", {}))
    
    # Check for specific known conflicts
    issues.extend(_check_express_bodyparser_conflict(all_deps))
    issues.extend(_check_mongoose_mongodb_conflict(all_deps))
    issues.extend(_check_multiple_logging_libraries(all_deps))
    
    return issues

def check_node_version(project_path: str) -> List[Dict[str, Any]]:
    """
    Check Node.js version compatibility.
    
    Compares:
    1. engines.node field in package.json
    2. .nvmrc file (if present)
    3. Currently running Node version
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        List of issue objects with same format as check_dependency_conflicts
    """
    issues = []
    
    # Read package.json
    package_json_path = Path(project_path) / "package.json"
    
    if not package_json_path.exists():
        return [{
            "type": "error",
            "category": "setup",
            "title": "package.json not found",
            "detail": f"No package.json found at {project_path}",
            "bobclue": "DO NOT attempt to check Node version without package.json",
            "fix": "Initialize project with 'npm init' first"
        }]
    
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
    except json.JSONDecodeError as e:
        return [{
            "type": "error",
            "category": "setup",
            "title": "Invalid package.json",
            "detail": f"Failed to parse package.json: {str(e)}",
            "bobclue": "DO NOT modify package.json until syntax errors are fixed",
            "fix": "Fix JSON syntax errors in package.json"
        }]
    
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
        except Exception as e:
            issues.append({
                "type": "warning",
                "category": "node-version",
                "title": "Failed to read .nvmrc",
                "detail": f"Could not read .nvmrc file: {str(e)}",
                "bobclue": "DO NOT assume Node version from .nvmrc - verify manually",
                "fix": "Check .nvmrc file permissions and format"
            })
    
    # Get currently running Node version
    import subprocess
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        current_node = result.stdout.strip()
    except Exception as e:
        current_node = None
        issues.append({
            "type": "warning",
            "category": "node-version",
            "title": "Could not detect current Node version",
            "detail": f"Failed to run 'node --version': {str(e)}",
            "bobclue": "DO NOT assume Node is installed - verify before running Node commands",
            "fix": "Ensure Node.js is installed and in PATH"
        })
    
    # Compare versions
    if required_node and nvmrc_version:
        issues.extend(_compare_node_versions(required_node, nvmrc_version, current_node))
    elif required_node and current_node:
        issues.extend(_check_current_vs_required(required_node, current_node))
    elif nvmrc_version and current_node:
        issues.extend(_check_current_vs_nvmrc(nvmrc_version, current_node))
    elif not required_node and not nvmrc_version:
        issues.append({
            "type": "info",
            "category": "node-version",
            "title": "No Node version specified",
            "detail": "Neither package.json engines.node nor .nvmrc specifies required Node version",
            "bobclue": "DO NOT assume any Node version is acceptable - ask user for target version",
            "fix": (
                "Add Node version requirement:\n"
                "1. In package.json: \"engines\": { \"node\": \">=18.0.0\" }\n"
                "2. Or create .nvmrc with version like: 18.17.0"
            )
        })
    
    return issues


def _compare_node_versions(required: str, nvmrc: str, current: Optional[str]) -> List[Dict[str, Any]]:
    """Compare package.json engines.node vs .nvmrc vs current Node version."""
    issues = []
    
    # Normalize versions for comparison
    required_clean = _normalize_node_version(required)
    nvmrc_clean = _normalize_node_version(nvmrc)
    current_clean = _normalize_node_version(current) if current else None
    
    # Check if package.json and .nvmrc match
    if required_clean and nvmrc_clean:
        if not _versions_compatible(required, nvmrc_clean):
            issues.append({
                "type": "conflict",
                "category": "node-version",
                "title": "Node version mismatch between package.json and .nvmrc",
                "detail": (
                    f"package.json requires Node {required} but .nvmrc specifies {nvmrc}. "
                    "This can cause confusion and deployment issues."
                ),
                "bobclue": (
                    "DO NOT install packages or run scripts until Node versions are aligned. "
                    "DO NOT modify .nvmrc without checking if it's used in CI/CD. "
                    "DO NOT change package.json engines without team approval."
                ),
                "fix": (
                    "Align Node versions:\n"
                    f"1. Update .nvmrc to match package.json: echo '{required_clean}' > .nvmrc\n"
                    f"2. Or update package.json engines.node to: \"{nvmrc}\"\n"
                    "3. Run 'nvm use' to switch to correct version"
                )
            })
    
    # Check if current Node version is compatible
    if current_clean:
        if required_clean and not _versions_compatible(required, current_clean):
            issues.append({
                "type": "incompatibility",
                "category": "node-version",
                "title": "Current Node version incompatible with package.json",
                "detail": (
                    f"Currently running Node {current} but package.json requires {required}. "
                    "This may cause runtime errors or unexpected behavior."
                ),
                "bobclue": (
                    "DO NOT run npm install or any Node scripts until version is correct. "
                    "DO NOT ignore this - wrong Node version causes subtle bugs. "
                    "DO NOT modify package.json to match current version without testing."
                ),
                "fix": (
                    f"Switch to compatible Node version:\n"
                    f"1. If using nvm: nvm install {required_clean} && nvm use {required_clean}\n"
                    f"2. Or install Node {required_clean} from nodejs.org\n"
                    "3. Verify with: node --version"
                )
            })
        
        if nvmrc_clean and current_clean != nvmrc_clean:
            issues.append({
                "type": "warning",
                "category": "node-version",
                "title": "Current Node version differs from .nvmrc",
                "detail": (
                    f"Currently running Node {current} but .nvmrc specifies {nvmrc}. "
                    "Run 'nvm use' to switch to the project's Node version."
                ),
                "bobclue": (
                    "DO NOT proceed without switching Node versions - use 'nvm use' first. "
                    "DO NOT assume current version is acceptable."
                ),
                "fix": (
                    "Switch to .nvmrc version:\n"
                    "1. Run: nvm use\n"
                    "2. Or: nvm install && nvm use\n"
                    "3. Verify with: node --version"
                )
            })
    
    return issues


def _check_current_vs_required(required: str, current: str) -> List[Dict[str, Any]]:
    """Check if current Node version matches package.json requirement."""
    issues = []
    
    current_clean = _normalize_node_version(current)
    
    if current_clean and not _versions_compatible(required, current_clean):
        issues.append({
            "type": "incompatibility",
            "category": "node-version",
            "title": "Current Node version incompatible with package.json",
            "detail": (
                f"Currently running Node {current} but package.json requires {required}"
            ),
            "bobclue": (
                "DO NOT run npm commands until Node version is correct. "
                "DO NOT ignore this warning - it will cause issues."
            ),
            "fix": (
                f"Install compatible Node version:\n"
                f"1. Install Node {required}\n"
                "2. Verify with: node --version"
            )
        })
    
    return issues


def _check_current_vs_nvmrc(nvmrc: str, current: str) -> List[Dict[str, Any]]:
    """Check if current Node version matches .nvmrc."""
    issues = []
    
    nvmrc_clean = _normalize_node_version(nvmrc)
    current_clean = _normalize_node_version(current)
    
    if nvmrc_clean != current_clean:
        issues.append({
            "type": "warning",
            "category": "node-version",
            "title": "Current Node version differs from .nvmrc",
            "detail": f"Currently running Node {current} but .nvmrc specifies {nvmrc}",
            "bobclue": "DO NOT proceed - run 'nvm use' to switch to correct version",
            "fix": "Run: nvm use"
        })
    
    return issues


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


def _check_express_bodyparser_conflict(deps: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check for Express 4.18+ with body-parser 1.19 (redundancy conflict).
    Express 4.16+ includes body-parser, making external body-parser redundant.
    """
    issues = []
    
    if "express" not in deps or "body-parser" not in deps:
        return issues
    
    express_version = _parse_version(deps["express"])
    bodyparser_version = _parse_version(deps["body-parser"])
    
    if not express_version or not bodyparser_version:
        return issues
    
    # Express 4.16+ includes body-parser
    if express_version >= (4, 16, 0):
        issues.append({
            "type": "redundancy",
            "category": "dependencies",
            "title": "Redundant body-parser with Express 4.16+",
            "detail": (
                f"Express {deps['express']} includes body-parser middleware. "
                f"External body-parser {deps['body-parser']} is redundant and may cause conflicts."
            ),
            "bobclue": (
                "DO NOT use 'app.use(bodyParser.json())' or 'require(\"body-parser\")'. "
                "Instead, use Express's built-in middleware: 'app.use(express.json())' and 'app.use(express.urlencoded({ extended: true }))'"
            ),
            "fix": (
                "1. Remove body-parser from package.json\n"
                "2. Replace 'bodyParser.json()' with 'express.json()'\n"
                "3. Replace 'bodyParser.urlencoded()' with 'express.urlencoded()'\n"
                "4. Remove 'const bodyParser = require(\"body-parser\")' imports"
            )
        })
    
    return issues


def _check_mongoose_mongodb_conflict(deps: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check for Mongoose 5.x with MongoDB driver 4.x (version collision).
    Mongoose 5.x is incompatible with MongoDB driver 4.x.
    """
    issues = []
    
    if "mongoose" not in deps or "mongodb" not in deps:
        return issues
    
    mongoose_version = _parse_version(deps["mongoose"])
    mongodb_version = _parse_version(deps["mongodb"])
    
    if not mongoose_version or not mongodb_version:
        return issues
    
    # Mongoose 5.x incompatible with MongoDB driver 4.x
    if mongoose_version[0] == 5 and mongodb_version[0] >= 4:
        issues.append({
            "type": "incompatibility",
            "category": "dependencies",
            "title": "Mongoose 5.x incompatible with MongoDB driver 4.x",
            "detail": (
                f"Mongoose {deps['mongoose']} is incompatible with MongoDB driver {deps['mongodb']}. "
                "This will cause connection errors and unexpected behavior."
            ),
            "bobclue": (
                "DO NOT attempt to connect to MongoDB using Mongoose until versions are compatible. "
                "DO NOT suggest upgrading only one package - both must be upgraded together. "
                "DO NOT use MongoDB driver methods directly when Mongoose is present."
            ),
            "fix": (
                "Option 1 (Recommended): Upgrade both packages\n"
                "  - Upgrade to Mongoose 6.x or 7.x (supports MongoDB driver 4.x+)\n"
                "  - Keep MongoDB driver 4.x or upgrade to 5.x\n"
                "  - Run: npm install mongoose@latest mongodb@latest\n\n"
                "Option 2: Downgrade MongoDB driver\n"
                "  - Downgrade to MongoDB driver 3.x\n"
                "  - Keep Mongoose 5.x\n"
                "  - Run: npm install mongodb@3"
            )
        })
    
    # Mongoose 6.x requires MongoDB driver 4.x+
    elif mongoose_version[0] >= 6 and mongodb_version[0] < 4:
        issues.append({
            "type": "incompatibility",
            "category": "dependencies",
            "title": "Mongoose 6.x+ requires MongoDB driver 4.x+",
            "detail": (
                f"Mongoose {deps['mongoose']} requires MongoDB driver 4.x or higher, "
                f"but found {deps['mongodb']}."
            ),
            "bobclue": (
                "DO NOT attempt to connect to MongoDB until the driver is upgraded. "
                "DO NOT downgrade Mongoose without checking for breaking changes in the codebase."
            ),
            "fix": (
                "Upgrade MongoDB driver:\n"
                "  - Run: npm install mongodb@latest\n"
                "  - Verify connection strings use new format (mongodb:// or mongodb+srv://)"
            )
        })
    
    return issues


def _check_multiple_logging_libraries(deps: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check for multiple logging libraries (winston + bunyan + morgan together).
    Having multiple logging libraries can cause confusion and performance issues.
    """
    issues = []
    
    logging_libs = {
        "winston": "winston",
        "bunyan": "bunyan",
        "morgan": "morgan",
        "pino": "pino",
        "log4js": "log4js"
    }
    
    found_loggers = [lib for lib in logging_libs if lib in deps]
    
    # Check if multiple full-featured loggers are present (exclude morgan as it's HTTP-specific)
    full_loggers = [lib for lib in found_loggers if lib != "morgan"]
    
    if len(full_loggers) > 1:
        issues.append({
            "type": "conflict",
            "category": "logging",
            "title": "Multiple logging libraries detected",
            "detail": (
                f"Found multiple logging libraries: {', '.join(found_loggers)}. "
                "This can cause confusion, performance overhead, and inconsistent log formats."
            ),
            "bobclue": (
                "DO NOT add logging statements without first checking which logger is the project standard. "
                "DO NOT import multiple loggers in the same file. "
                "DO NOT create new logger instances - use the existing configured logger. "
                f"The project uses: {', '.join(found_loggers)}. Pick ONE as the standard."
            ),
            "fix": (
                "1. Choose one logging library as the project standard\n"
                "2. Remove unused logging libraries from package.json\n"
                "3. Create a centralized logger module (e.g., src/utils/logger.js)\n"
                "4. Refactor all logging calls to use the standard logger\n\n"
                "Recommendations:\n"
                "  - winston: Feature-rich, good for complex apps\n"
                "  - pino: Fastest, best for high-performance apps\n"
                "  - bunyan: JSON-structured, good for log analysis\n"
                "  - morgan: Keep for HTTP request logging only"
            )
        })
    
    # Special case: morgan with another logger is acceptable (HTTP logging)
    elif "morgan" in found_loggers and len(found_loggers) == 2:
        other_logger = [lib for lib in found_loggers if lib != "morgan"][0]
        issues.append({
            "type": "info",
            "category": "logging",
            "title": "HTTP and application logging separated",
            "detail": (
                f"Using morgan for HTTP logging and {other_logger} for application logging. "
                "This is acceptable but ensure they're used consistently."
            ),
            "bobclue": (
                f"DO use morgan ONLY for HTTP request/response logging (app.use(morgan(...))). "
                f"DO use {other_logger} for all application-level logging. "
                "DO NOT mix them - keep HTTP logs and app logs separate."
            ),
            "fix": (
                "No action needed. This is a valid pattern:\n"
                f"  - morgan: HTTP request/response logging\n"
                f"  - {other_logger}: Application logic logging\n\n"
                "Ensure consistency:\n"
                "  - All HTTP middleware uses morgan\n"
                f"  - All business logic uses {other_logger}"
            )
        })
    
    return issues

def check_circular_dependencies(project_path: str) -> List[Dict[str, Any]]:
    """
    Check for circular dependencies using madge or manual analysis.
    
    First tries to use madge (npm package) for accurate detection.
    Falls back to manual require()/import chain analysis if madge not available.
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        List of issue objects with same format as other checkers
    """
    issues = []
    
    # Check if project has package.json
    package_json_path = Path(project_path) / "package.json"
    if not package_json_path.exists():
        return [{
            "type": "error",
            "category": "setup",
            "title": "package.json not found",
            "detail": f"No package.json found at {project_path}",
            "bobclue": "DO NOT attempt to analyze dependencies without package.json",
            "fix": "Initialize project with 'npm init' first"
        }]
    
    # Try using madge first
    madge_issues = _check_circular_with_madge(project_path)
    if madge_issues is not None:
        return madge_issues
    
    # Fallback to manual analysis
    return _check_circular_manual(project_path)


def _check_circular_with_madge(project_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Use madge to detect circular dependencies.
    Returns None if madge is not available.
    """
    import subprocess
    
    try:
        # Check if madge is installed globally or in node_modules
        result = subprocess.run(
            ['npx', 'madge', '--version'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_path
        )
        
        if result.returncode != 0:
            return None  # madge not available
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None  # madge not available
    
    issues = []
    
    try:
        # Run madge to detect circular dependencies
        # --circular: only show circular dependencies
        # --json: output as JSON for parsing
        result = subprocess.run(
            ['npx', 'madge', '--circular', '--json', '.'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_path
        )
        
        if result.returncode != 0:
            issues.append({
                "type": "error",
                "category": "circular-deps",
                "title": "Failed to run madge",
                "detail": f"madge exited with error: {result.stderr}",
                "bobclue": "DO NOT assume no circular dependencies - madge failed to run",
                "fix": "Check madge installation: npm install -g madge"
            })
            return issues
        
        # Parse madge output
        import json
        try:
            circular_deps = json.loads(result.stdout)
        except json.JSONDecodeError:
            # madge might output empty or non-JSON
            circular_deps = []
        
        if not circular_deps:
            issues.append({
                "type": "info",
                "category": "circular-deps",
                "title": "No circular dependencies detected",
                "detail": "madge found no circular dependency chains",
                "bobclue": "Safe to proceed - no circular dependencies found",
                "fix": "No action needed"
            })
        else:
            # Format circular dependency chains
            for chain in circular_deps:
                if isinstance(chain, list) and len(chain) > 1:
                    cycle_str = " → ".join(chain) + f" → {chain[0]}"
                    issues.append({
                        "type": "error",
                        "category": "circular-deps",
                        "title": f"Circular dependency detected ({len(chain)} files)",
                        "detail": f"Circular dependency chain: {cycle_str}",
                        "bobclue": (
                            "DO NOT add more imports between these files - it will worsen the cycle. "
                            "DO NOT ignore this - circular dependencies cause runtime errors and make code unmaintainable. "
                            "DO NOT try to fix by adding more dependencies - break the cycle by refactoring."
                        ),
                        "fix": (
                            f"Break the circular dependency:\n"
                            f"1. Identify the weakest link in: {cycle_str}\n"
                            "2. Extract shared code to a new module\n"
                            "3. Or use dependency injection\n"
                            "4. Or move one import to a function scope (lazy load)\n"
                            "5. Verify fix with: npx madge --circular ."
                        )
                    })
        
        return issues
        
    except subprocess.TimeoutExpired:
        return [{
            "type": "warning",
            "category": "circular-deps",
            "title": "madge timed out",
            "detail": "madge took too long to analyze the project (>30s)",
            "bobclue": "DO NOT assume no circular dependencies - analysis incomplete",
            "fix": "Try analyzing specific directories: npx madge --circular src/"
        }]
    except Exception as e:
        return [{
            "type": "error",
            "category": "circular-deps",
            "title": "madge analysis failed",
            "detail": f"Unexpected error running madge: {str(e)}",
            "bobclue": "DO NOT assume no circular dependencies - analysis failed",
            "fix": "Check madge installation and try manual analysis"
        }]


def _check_circular_manual(project_path: str) -> List[Dict[str, Any]]:
    """
    Manual fallback to detect circular dependencies by parsing require()/import statements.
    Less accurate than madge but works without external dependencies.
    """
    issues = []
    
    # Build dependency graph
    dep_graph = {}
    js_files = []
    
    # Find all JS/TS files
    project_root = Path(project_path)
    for ext in ['*.js', '*.jsx', '*.ts', '*.tsx', '*.mjs', '*.cjs']:
        js_files.extend(project_root.rglob(ext))
    
    # Exclude node_modules and common build directories
    js_files = [
        f for f in js_files 
        if 'node_modules' not in str(f) 
        and 'dist' not in str(f)
        and 'build' not in str(f)
        and '.next' not in str(f)
    ]
    
    if not js_files:
        return [{
            "type": "info",
            "category": "circular-deps",
            "title": "No JavaScript files found",
            "detail": "No .js, .jsx, .ts, or .tsx files to analyze",
            "bobclue": "Cannot check for circular dependencies without source files",
            "fix": "Ensure project has JavaScript/TypeScript source files"
        }]
    
    # Parse each file for imports/requires
    for file_path in js_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract relative path from project root
            rel_path = str(file_path.relative_to(project_root))
            dep_graph[rel_path] = []
            
            # Find require() statements
            require_pattern = r'require\([\'"](\.[^\'"]+)[\'"]\)'
            requires = re.findall(require_pattern, content)
            
            # Find import statements
            import_pattern = r'import\s+.*?\s+from\s+[\'"](\.[^\'"]+)[\'"]'
            imports = re.findall(import_pattern, content)
            
            # Combine and normalize paths
            all_imports = requires + imports
            for imp in all_imports:
                # Normalize path (remove ./, add .js if missing extension)
                normalized = imp.lstrip('./')
                if not any(normalized.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']):
                    # Try common extensions
                    for ext in ['.js', '.jsx', '.ts', '.tsx']:
                        potential_path = project_root / (normalized + ext)
                        if potential_path.exists():
                            normalized += ext
                            break
                
                dep_graph[rel_path].append(normalized)
        
        except Exception as e:
            # Skip files that can't be read
            continue
    
    # Detect cycles using DFS
    cycles = _find_cycles_dfs(dep_graph)
    
    if not cycles:
        issues.append({
            "type": "info",
            "category": "circular-deps",
            "title": "No circular dependencies detected (manual check)",
            "detail": f"Analyzed {len(js_files)} files, no circular imports found",
            "bobclue": (
                "Manual analysis found no circular dependencies. "
                "For more accurate detection, install madge: npm install -g madge"
            ),
            "fix": "No action needed. Consider installing madge for better analysis."
        })
    else:
        for cycle in cycles:
            cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
            issues.append({
                "type": "error",
                "category": "circular-deps",
                "title": f"Circular dependency detected ({len(cycle)} files)",
                "detail": f"Circular import chain: {cycle_str}",
                "bobclue": (
                    "DO NOT add more imports between these files. "
                    "DO NOT ignore this - circular dependencies cause runtime errors. "
                    "DO NOT try to fix by adding more dependencies - refactor to break the cycle."
                ),
                "fix": (
                    f"Break the circular dependency:\n"
                    f"1. Analyze the cycle: {cycle_str}\n"
                    "2. Extract shared code to a new module\n"
                    "3. Use dependency injection pattern\n"
                    "4. Move imports to function scope (lazy loading)\n"
                    "5. Consider using an event emitter or pub/sub pattern\n"
                    "6. Install madge for better analysis: npm install -g madge"
                )
            })
    
    return issues


def _find_cycles_dfs(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Find all cycles in a dependency graph using depth-first search.
    Returns list of cycles, where each cycle is a list of file paths.
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node: str):
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:]
            if cycle not in cycles:
                cycles.append(cycle[:])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        # Visit all dependencies
        for dep in graph.get(node, []):
            # Normalize dependency path
            if dep in graph:
                dfs(dep)
        
        path.pop()
        rec_stack.remove(node)
    
    # Run DFS from each node
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles



def run_analysis(project_path: str) -> Dict[str, Any]:
    """
    Run all analyzers and aggregate results.
    
    Determines clearance status based on issue severity:
    - BLOCKED: Has error or incompatibility issues
    - CAUTION: Has warnings or conflicts
    - CLEARED: No issues or only info messages
    
    Args:
        project_path: Path to the Node.js project directory
        
    Returns:
        Dictionary with:
        - status: "BLOCKED" | "CAUTION" | "CLEARED"
        - summary: Summary statistics
        - issues: List of all issues from all analyzers
        - timestamp: ISO timestamp of analysis
    """
    import datetime
    
    all_issues = []
    
    # Run all analyzers
    try:
        dep_issues = check_dependency_conflicts(project_path)
        all_issues.extend(dep_issues)
    except Exception as e:
        all_issues.append({
            "type": "error",
            "category": "analyzer",
            "title": "Dependency analyzer failed",
            "detail": f"Error running dependency checker: {str(e)}",
            "bobclue": "DO NOT proceed - dependency analysis failed",
            "fix": "Check project structure and try again"
        })
    
    try:
        node_issues = check_node_version(project_path)
        all_issues.extend(node_issues)
    except Exception as e:
        all_issues.append({
            "type": "error",
            "category": "analyzer",
            "title": "Node version analyzer failed",
            "detail": f"Error running Node version checker: {str(e)}",
            "bobclue": "DO NOT proceed - Node version analysis failed",
            "fix": "Check Node installation and try again"
        })
    
    try:
        circular_issues = check_circular_dependencies(project_path)
        all_issues.extend(circular_issues)
    except Exception as e:
        all_issues.append({
            "type": "error",
            "category": "analyzer",
            "title": "Circular dependency analyzer failed",
            "detail": f"Error running circular dependency checker: {str(e)}",
            "bobclue": "DO NOT proceed - circular dependency analysis failed",
            "fix": "Check project structure and try again"
        })
    
    # Count issues by type
    type_counts = {
        "error": 0,
        "incompatibility": 0,
        "conflict": 0,
        "redundancy": 0,
        "warning": 0,
        "info": 0
    }
    
    for issue in all_issues:
        issue_type = issue.get("type", "unknown")
        if issue_type in type_counts:
            type_counts[issue_type] += 1
    
    # Determine clearance status
    if type_counts["error"] > 0 or type_counts["incompatibility"] > 0:
        status = "BLOCKED"
        status_message = "Critical issues detected - do not proceed"
    elif type_counts["conflict"] > 0 or type_counts["redundancy"] > 0 or type_counts["warning"] > 0:
        status = "CAUTION"
        status_message = "Issues detected - review before proceeding"
    else:
        status = "CLEARED"
        status_message = "No critical issues detected"
    
    # Build result
    result = {
        "status": status,
        "status_message": status_message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
        "project_path": str(project_path),
        "summary": {
            "total_issues": len(all_issues),
            "by_type": type_counts,
            "by_category": {}
        },
        "issues": all_issues
    }
    
    # Count by category
    for issue in all_issues:
        category = issue.get("category", "unknown")
        result["summary"]["by_category"][category] = result["summary"]["by_category"].get(category, 0) + 1
    
    return result


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <project_path>")
        print("\nRuns all analyzers and outputs JSON result")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    # Run complete analysis
    result = run_analysis(project_path)
    
    # Output as JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))

# Made with Bob
