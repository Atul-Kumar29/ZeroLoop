import pytest
import json


@pytest.fixture
def sample_raw_findings():
    return {
        "timestamp": "2026-05-02T10:00:00Z",
        "project_path": "/test/galaxy-store-api",
        "raw_findings": [
            {
                "finding_type": "npm_audit",
                "raw_data": {
                    "vulnerabilities": {
                        "mongoose": {
                            "severity": "critical",
                            "name": "mongoose",
                            "fixAvailable": True
                        },
                        "body-parser": {
                            "severity": "high",
                            "name": "body-parser",
                            "fixAvailable": True
                        }
                    }
                },
                "metadata": {
                    "tool": "npm",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/galaxy-store-api",
                    "success": True,
                    "exit_code": 1
                }
            },
            {
                "finding_type": "depcheck",
                "raw_data": {
                    "dependencies": ["bunyan", "morgan"],
                    "devDependencies": [],
                    "missing": {
                        "lodash": ["services/auth.js"]
                    },
                    "using": {}
                },
                "metadata": {
                    "tool": "depcheck",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/galaxy-store-api",
                    "success": True
                }
            },
            {
                "finding_type": "circular_deps",
                "raw_data": {
                    "circular": [
                        ["services/auth.js", "services/token.js"],
                        ["services/token.js", "services/auth.js"]
                    ],
                    "method": "madge"
                },
                "metadata": {
                    "tool": "madge",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/galaxy-store-api",
                    "success": True
                }
            },
            {
                "finding_type": "node_version",
                "raw_data": {
                    "package_json_engines": ">=18.0.0",
                    "nvmrc_version": "14.17.0",
                    "current_version": "v14.17.0",
                    "mismatches": [
                        {
                            "type": "nvmrc_vs_required",
                            "expected": ">=18.0.0",
                            "actual": "14.17.0"
                        },
                        {
                            "type": "current_vs_required",
                            "expected": ">=18.0.0",
                            "actual": "v14.17.0"
                        }
                    ]
                },
                "metadata": {
                    "tool": "node",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/galaxy-store-api",
                    "success": True
                }
            }
        ],
        "errors": []
    }


@pytest.fixture
def sample_interpreted_analysis():
    return {
        "status": "BLOCKED",
        "status_message": "Critical issues detected. Bob should NOT start.",
        "project_path": "/test/galaxy-store-api",
        "timestamp": "2026-05-02T10:00:00Z",
        "summary": {
            "total_issues": 3,
            "by_type": {
                "error": 1,
                "incompatibility": 1,
                "conflict": 1,
                "redundancy": 0,
                "warning": 0,
                "info": 0
            }
        },
        "issues": [
            {
                "type": "incompatibility",
                "category": "dependencies",
                "title": "Mongoose 5.x / MongoDB Driver 4.x Version Collision",
                "detail": "Mongoose 5.x uses MongoDB driver 3.x internally.",
                "bobclue": "DO NOT attempt MongoDB connection fixes through code changes.",
                "fix": "Upgrade to Mongoose 6.x or remove mongodb from dependencies."
            },
            {
                "type": "error",
                "category": "dependencies",
                "title": "Critical Security Vulnerability in body-parser",
                "detail": "body-parser has a critical vulnerability.",
                "bobclue": "DO NOT use body-parser in production until updated.",
                "fix": "Run: npm install body-parser@latest"
            },
            {
                "type": "conflict",
                "category": "dependencies",
                "title": "Multiple Logging Libraries",
                "detail": "Three logging libraries competing.",
                "bobclue": "DO NOT add logging configuration until one library is chosen.",
                "fix": "Choose one logging library and remove the others."
            }
        ],
        "granite_interpretation": {
            "interpreted_issues": [
                {
                    "title": "Mongoose 5.x / MongoDB Driver 4.x",
                    "explanation": "Incompatible versions.",
                    "bobclue": "DO NOT attempt MongoDB connection fixes.",
                    "severity": "critical",
                    "fix": "Upgrade Mongoose to 6.x"
                }
            ],
            "circular_constraint_pairs": [
                {
                    "package_a": "mongoose",
                    "package_b": "mongodb",
                    "reason": "Mongoose 5.x requires MongoDB driver 3.x internally"
                }
            ],
            "coordinated_fix_plan": {
                "install_command": "npm install mongoose@6.0.0",
                "uninstall_command": "npm uninstall body-parser mongodb",
                "warning": "DO NOT run any other npm install commands before these complete"
            }
        }
    }


@pytest.fixture
def sample_package_json():
    return {
        "name": "galaxy-store-api",
        "version": "1.0.0",
        "engines": {
            "node": ">=18.0.0"
        },
        "dependencies": {
            "express": "4.18.2",
            "body-parser": "1.19.0",
            "mongoose": "5.13.15",
            "mongodb": "4.0.0",
            "winston": "3.8.2",
            "bunyan": "1.8.15",
            "morgan": "1.10.0"
        }
    }


@pytest.fixture
def empty_raw_findings():
    return {
        "timestamp": "2026-05-02T10:00:00Z",
        "project_path": "/test/clean-project",
        "raw_findings": [
            {
                "finding_type": "npm_audit",
                "raw_data": {
                    "vulnerabilities": {}
                },
                "metadata": {
                    "tool": "npm",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/clean-project",
                    "success": True,
                    "exit_code": 0
                }
            },
            {
                "finding_type": "depcheck",
                "raw_data": {
                    "dependencies": [],
                    "devDependencies": [],
                    "missing": {},
                    "using": {}
                },
                "metadata": {
                    "tool": "depcheck",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/clean-project",
                    "success": True
                }
            },
            {
                "finding_type": "circular_deps",
                "raw_data": {
                    "circular": [],
                    "method": "madge"
                },
                "metadata": {
                    "tool": "madge",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/clean-project",
                    "success": True
                }
            },
            {
                "finding_type": "node_version",
                "raw_data": {
                    "package_json_engines": ">=18.0.0",
                    "nvmrc_version": "18.0.0",
                    "current_version": "v18.0.0",
                    "mismatches": []
                },
                "metadata": {
                    "tool": "node",
                    "timestamp": "2026-05-02T10:00:00Z",
                    "project_path": "/test/clean-project",
                    "success": True
                }
            }
        ],
        "errors": []
    }