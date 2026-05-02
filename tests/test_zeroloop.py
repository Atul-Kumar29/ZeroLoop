import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scanner.analyze import (
    check_npm_audit,
    check_depcheck,
    check_circular_dependencies,
    check_node_version,
    run_analysis
)
from scanner.bob_context_generator import (
    generate_bob_context,
    generate_reset_context,
    estimate_bobcoin_savings
)
from scanner.granite_interpreter import (
    template_interpret,
    interpret_findings_safe,
    _validate_interpretation_schema,
    _parse_granite_response
)


# ─────────────────────────────────────────────
# 1. NPM AUDIT
# ─────────────────────────────────────────────

class TestNpmAudit:

    @patch('scanner.analyze.subprocess.run')
    def test_identifies_critical_vulnerabilities(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "vulnerabilities": {
                    "mongoose": {
                        "severity": "critical",
                        "name": "mongoose",
                        "fixAvailable": True
                    }
                }
            }),
            stderr="",
            returncode=1
        )
        result = check_npm_audit(str(tmp_path))
        assert result["finding_type"] == "npm_audit"
        vulns = result["raw_data"].get("vulnerabilities", {})
        assert "mongoose" in vulns
        assert vulns["mongoose"]["severity"] == "critical"

    @patch('scanner.analyze.subprocess.run')
    def test_identifies_high_vulnerabilities(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "vulnerabilities": {
                    "body-parser": {
                        "severity": "high",
                        "name": "body-parser",
                        "fixAvailable": True
                    }
                }
            }),
            stderr="",
            returncode=1
        )
        result = check_npm_audit(str(tmp_path))
        vulns = result["raw_data"].get("vulnerabilities", {})
        assert "body-parser" in vulns
        assert vulns["body-parser"]["severity"] == "high"

    @patch('scanner.analyze.subprocess.run')
    def test_returns_empty_vulnerabilities_when_clean(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"vulnerabilities": {}}),
            stderr="",
            returncode=0
        )
        result = check_npm_audit(str(tmp_path))
        assert result["raw_data"]["vulnerabilities"] == {}

    @patch('scanner.analyze.subprocess.run')
    def test_handles_malformed_json_gracefully(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout="not valid json at all",
            stderr="",
            returncode=1
        )
        result = check_npm_audit(str(tmp_path))
        assert result["finding_type"] == "npm_audit"
        assert "error" in result["raw_data"]

    def test_returns_error_when_no_package_json(
        self, tmp_path
    ):
        result = check_npm_audit(str(tmp_path))
        assert result["metadata"]["success"] is False
        assert "error" in result["raw_data"]

    @patch('scanner.analyze.subprocess.run')
    def test_handles_timeout_gracefully(
        self, mock_run, tmp_path, sample_package_json
    ):
        import subprocess
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="npm audit", timeout=30
        )
        result = check_npm_audit(str(tmp_path))
        assert "timed out" in result["raw_data"]["error"].lower()
        assert result["metadata"]["success"] is False


# ─────────────────────────────────────────────
# 2. DEPCHECK
# ─────────────────────────────────────────────

class TestDepcheck:

    @patch('scanner.analyze.subprocess.run')
    def test_identifies_unused_dependencies(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "dependencies": ["bunyan", "morgan"],
                "devDependencies": [],
                "missing": {},
                "using": {}
            }),
            stderr="",
            returncode=0
        )
        result = check_depcheck(str(tmp_path))
        assert result["finding_type"] == "depcheck"
        assert "bunyan" in result["raw_data"]["dependencies"]

    @patch('scanner.analyze.subprocess.run')
    def test_identifies_missing_dependencies(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                "dependencies": [],
                "devDependencies": [],
                "missing": {"lodash": ["services/auth.js"]},
                "using": {}
            }),
            stderr="",
            returncode=0
        )
        result = check_depcheck(str(tmp_path))
        assert "lodash" in result["raw_data"]["missing"]

    def test_returns_error_when_no_package_json(
        self, tmp_path
    ):
        result = check_depcheck(str(tmp_path))
        assert result["metadata"]["success"] is False

    @patch('scanner.analyze.subprocess.run')
    def test_handles_timeout_gracefully(
        self, mock_run, tmp_path, sample_package_json
    ):
        import subprocess
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="npx depcheck", timeout=60
        )
        result = check_depcheck(str(tmp_path))
        assert "timed out" in result["raw_data"]["error"].lower()


# ─────────────────────────────────────────────
# 3. CIRCULAR DEPENDENCY DETECTION
# ─────────────────────────────────────────────

class TestCircularDependencies:

    @patch('scanner.analyze.subprocess.run')
    def test_detects_circular_dependencies_with_madge(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        circular = [
            ["services/auth.js", "services/token.js"]
        ]
        mock_run.return_value = MagicMock(
            stdout=json.dumps(circular),
            stderr="",
            returncode=0
        )
        result = check_circular_dependencies(str(tmp_path))
        assert result["finding_type"] == "circular_deps"
        assert len(result["raw_data"]["circular"]) >= 1

    @patch('scanner.analyze.subprocess.run')
    def test_returns_empty_when_no_circular_deps(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps([]),
            stderr="",
            returncode=0
        )
        result = check_circular_dependencies(str(tmp_path))
        assert result["raw_data"]["circular"] == []

    def test_returns_error_when_no_package_json(
        self, tmp_path
    ):
        result = check_circular_dependencies(str(tmp_path))
        assert result["metadata"]["success"] is False


# ─────────────────────────────────────────────
# 4. NODE VERSION CHECK
# ─────────────────────────────────────────────

class TestNodeVersionCheck:

    def test_detects_nvmrc_vs_required_mismatch(
        self, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        (tmp_path / ".nvmrc").write_text("14.17.0")

        with patch('scanner.analyze.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="v18.0.0\n",
                stderr=""
            )
            result = check_node_version(str(tmp_path))

        mismatches = result["raw_data"]["mismatches"]
        mismatch_types = [m["type"] for m in mismatches]
        assert "nvmrc_vs_required" in mismatch_types

    def test_no_mismatch_when_versions_compatible(
        self, tmp_path
    ):
        pkg = {"engines": {"node": ">=18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        (tmp_path / ".nvmrc").write_text("18.17.0")

        with patch('scanner.analyze.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="v18.17.0\n",
                stderr=""
            )
            result = check_node_version(str(tmp_path))

        assert result["raw_data"]["mismatches"] == []

    def test_handles_missing_nvmrc_gracefully(
        self, tmp_path
    ):
        pkg = {"engines": {"node": ">=18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        with patch('scanner.analyze.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="v18.0.0\n",
                stderr=""
            )
            result = check_node_version(str(tmp_path))

        assert result["finding_type"] == "node_version"
        assert result["raw_data"]["nvmrc_version"] is None

    def test_returns_error_when_no_package_json(
        self, tmp_path
    ):
        result = check_node_version(str(tmp_path))
        assert result["metadata"]["success"] is False

    def test_detects_current_vs_required_mismatch(
        self, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )

        with patch('scanner.analyze.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="v14.17.0\n",
                stderr=""
            )
            result = check_node_version(str(tmp_path))

        mismatch_types = [
            m["type"] for m in result["raw_data"]["mismatches"]
        ]
        assert "current_vs_required" in mismatch_types


# ─────────────────────────────────────────────
# 5. RUN ANALYSIS
# ─────────────────────────────────────────────

class TestRunAnalysis:

    @patch('scanner.analyze.subprocess.run')
    def test_returns_all_four_finding_types(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        (tmp_path / ".nvmrc").write_text("18.0.0")
        mock_run.return_value = MagicMock(
            stdout=json.dumps({}),
            stderr="",
            returncode=0
        )
        result = run_analysis(str(tmp_path))
        finding_types = [
            f["finding_type"] 
            for f in result["raw_findings"]
        ]
        assert "npm_audit" in finding_types
        assert "depcheck" in finding_types
        assert "circular_deps" in finding_types
        assert "node_version" in finding_types

    @patch('scanner.analyze.subprocess.run')
    def test_includes_timestamp_and_project_path(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({}),
            stderr="",
            returncode=0
        )
        result = run_analysis(str(tmp_path))
        assert "timestamp" in result
        assert "project_path" in result

    @patch('scanner.analyze.subprocess.run')
    def test_returns_errors_list(
        self, mock_run, tmp_path, sample_package_json
    ):
        (tmp_path / "package.json").write_text(
            json.dumps(sample_package_json)
        )
        mock_run.return_value = MagicMock(
            stdout=json.dumps({}),
            stderr="",
            returncode=0
        )
        result = run_analysis(str(tmp_path))
        assert "errors" in result
        assert isinstance(result["errors"], list)


# ─────────────────────────────────────────────
# 6. BOB CONTEXT GENERATION
# ─────────────────────────────────────────────

class TestBobContextGeneration:

    def test_circuit_breaker_always_present(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert "CIRCUIT BREAKER" in context.upper()

    def test_clearance_status_in_context(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert "BLOCKED" in context

    def test_circular_constraint_pairs_listed(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        pairs = sample_interpreted_analysis[
            "granite_interpretation"
        ]["circular_constraint_pairs"]
        for pair in pairs:
            assert pair["package_a"] in context

    def test_coordinated_fix_plan_in_context(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        fix_cmd = sample_interpreted_analysis[
            "granite_interpretation"
        ]["coordinated_fix_plan"]["install_command"]
        assert fix_cmd in context

    def test_bobclues_present_in_context(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert "BOBCLUE" in context.upper()

    def test_do_not_instructions_present(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert "DO NOT" in context

    def test_retry_loop_prevention_present(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert "retry" in context.lower() or \
               "loop" in context.lower()

    def test_returns_string(
        self, sample_interpreted_analysis
    ):
        context = generate_bob_context(
            sample_interpreted_analysis
        )
        assert isinstance(context, str)
        assert len(context) > 0


# ─────────────────────────────────────────────
# 7. RESET CONTEXT GENERATION
# ─────────────────────────────────────────────

class TestResetContextGeneration:

    def test_reset_context_under_200_words(
        self, sample_interpreted_analysis
    ):
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        word_count = len(reset.split())
        assert word_count <= 200, (
            f"Reset context is {word_count} words, "
            f"must be under 200"
        )

    def test_reset_context_starts_with_stop(
        self, sample_interpreted_analysis
    ):
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        assert "STOP" in reset[:50].upper()

    def test_reset_context_contains_constraint_pairs(
        self, sample_interpreted_analysis
    ):
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        pairs = sample_interpreted_analysis[
            "granite_interpretation"
        ]["circular_constraint_pairs"]
        for pair in pairs:
            assert pair["package_a"] in reset

    def test_reset_context_contains_fix_command(
        self, sample_interpreted_analysis
    ):
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        fix = sample_interpreted_analysis[
            "granite_interpretation"
        ]["coordinated_fix_plan"]["install_command"]
        assert fix in reset

    def test_reset_context_shorter_than_full(
        self, sample_interpreted_analysis
    ):
        full = generate_bob_context(
            sample_interpreted_analysis
        )
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        assert len(reset) < len(full)

    def test_reset_context_returns_string(
        self, sample_interpreted_analysis
    ):
        reset = generate_reset_context(
            sample_interpreted_analysis
        )
        assert isinstance(reset, str)
        assert len(reset) > 0

    def test_reset_context_no_circular_pairs(
        self, sample_interpreted_analysis
    ):
        analysis = dict(sample_interpreted_analysis)
        analysis["granite_interpretation"] = {
            "circular_constraint_pairs": [],
            "coordinated_fix_plan": {
                "install_command": "npm install",
                "uninstall_command": None,
                "warning": "test"
            }
        }
        reset = generate_reset_context(analysis)
        assert isinstance(reset, str)


# ─────────────────────────────────────────────
# 8. BOBCOIN SAVINGS
# ─────────────────────────────────────────────

class TestBobcoinSavings:

    def test_error_type_saves_12_bobcoins(self):
        analysis = {
            "issues": [
                {
                    "type": "error",
                    "title": "Critical Error Issue"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 12

    def test_incompatibility_type_saves_12_bobcoins(self):
        analysis = {
            "issues": [
                {
                    "type": "incompatibility",
                    "title": "Version Incompatibility"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 12

    def test_conflict_type_saves_4_bobcoins(self):
        analysis = {
            "issues": [
                {
                    "type": "conflict",
                    "title": "Package Conflict"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 4

    def test_redundancy_type_saves_4_bobcoins(self):
        analysis = {
            "issues": [
                {
                    "type": "redundancy",
                    "title": "Redundant Package"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 4

    def test_warning_type_saves_1_bobcoin(self):
        analysis = {
            "issues": [
                {
                    "type": "warning",
                    "title": "Minor Warning"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 1

    def test_circular_pair_saves_20_bobcoins(self):
        analysis = {
            "issues": [],
            "granite_interpretation": {
                "circular_constraint_pairs": [
                    {
                        "package_a": "mongoose",
                        "package_b": "mongodb",
                        "reason": "version conflict"
                    }
                ]
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["total_saved"] >= 20

    def test_granite_cost_is_0001(self):
        analysis = {
            "issues": [],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert savings["granite_cost"] == 0.0001

    def test_net_roi_string_present_and_correct(self):
        analysis = {
            "issues": [
                {
                    "type": "error",
                    "title": "Test Error"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert "net_roi" in savings
        assert isinstance(savings["net_roi"], str)
        assert "0.0001" in savings["net_roi"]

    def test_breakdown_list_present(self):
        analysis = {
            "issues": [
                {
                    "type": "error",
                    "title": "Test Error"
                }
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": []
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        assert "breakdown" in savings
        assert isinstance(savings["breakdown"], list)

    def test_combined_savings_add_correctly(self):
        analysis = {
            "issues": [
                {"type": "error", "title": "Error 1"},
                {"type": "conflict", "title": "Conflict 1"}
            ],
            "granite_interpretation": {
                "circular_constraint_pairs": [
                    {
                        "package_a": "a",
                        "package_b": "b",
                        "reason": "test"
                    }
                ]
            }
        }
        savings = estimate_bobcoin_savings(analysis)
        # error=12, conflict=4, circular=20
        assert savings["total_saved"] == 36


# ─────────────────────────────────────────────
# 9. TEMPLATE INTERPRET FALLBACK
# ─────────────────────────────────────────────

class TestTemplateInterpret:

    def test_works_without_credentials(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        assert result is not None
        assert isinstance(result, dict)

    def test_returns_interpreted_issues(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        assert "interpreted_issues" in result
        assert isinstance(result["interpreted_issues"], list)

    def test_bobclues_start_with_do_not(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        for issue in result["interpreted_issues"]:
            assert issue["bobclue"].startswith("DO NOT"), (
                f"Bobclue does not start with DO NOT: "
                f"{issue['bobclue']}"
            )

    def test_returns_coordinated_fix_plan(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        assert "coordinated_fix_plan" in result
        plan = result["coordinated_fix_plan"]
        assert "install_command" in plan
        assert "uninstall_command" in plan
        assert "warning" in plan

    def test_returns_circular_constraint_pairs(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        assert "circular_constraint_pairs" in result
        assert isinstance(
            result["circular_constraint_pairs"], list
        )

    def test_processes_npm_audit_findings(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        issues = result["interpreted_issues"]
        titles = [i["title"] for i in issues]
        has_security = any(
            "security" in t.lower() or 
            "vulnerab" in t.lower() or
            "mongoose" in t.lower() or
            "body-parser" in t.lower()
            for t in titles
        )
        assert has_security

    def test_processes_circular_dep_findings(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        pairs = result["circular_constraint_pairs"]
        assert len(pairs) >= 1

    def test_processes_node_version_findings(
        self, sample_raw_findings
    ):
        result = template_interpret(sample_raw_findings)
        issues = result["interpreted_issues"]
        titles = [i["title"].lower() for i in issues]
        has_node = any(
            "node" in t or "version" in t 
            for t in titles
        )
        assert has_node

    def test_works_with_empty_findings(
        self, empty_raw_findings
    ):
        result = template_interpret(empty_raw_findings)
        assert result is not None
        assert "interpreted_issues" in result
        assert result["interpreted_issues"] == []


# ─────────────────────────────────────────────
# 10. GRANITE SCHEMA VALIDATION
# ─────────────────────────────────────────────

class TestGraniteSchemaValidation:

    def test_valid_schema_passes(self):
        valid = {
            "interpreted_issues": [
                {
                    "title": "Test",
                    "explanation": "Test explanation",
                    "bobclue": "DO NOT do this",
                    "severity": "critical",
                    "fix": "Fix this way"
                }
            ],
            "circular_constraint_pairs": [
                {
                    "package_a": "mongoose",
                    "package_b": "mongodb",
                    "reason": "version conflict"
                }
            ],
            "coordinated_fix_plan": {
                "install_command": "npm install mongoose@6",
                "uninstall_command": None,
                "warning": "Be careful"
            }
        }
        assert _validate_interpretation_schema(valid) is True

    def test_missing_interpreted_issues_fails(self):
        invalid = {
            "circular_constraint_pairs": [],
            "coordinated_fix_plan": {
                "install_command": "npm install",
                "uninstall_command": None,
                "warning": "test"
            }
        }
        assert _validate_interpretation_schema(invalid) is False

    def test_bobclue_not_starting_with_do_not_fails(self):
        invalid = {
            "interpreted_issues": [
                {
                    "title": "Test",
                    "explanation": "Test",
                    "bobclue": "Please avoid this",
                    "severity": "critical",
                    "fix": "Fix it"
                }
            ],
            "circular_constraint_pairs": [],
            "coordinated_fix_plan": {
                "install_command": "npm install",
                "uninstall_command": None,
                "warning": "test"
            }
        }
        assert _validate_interpretation_schema(invalid) is False

    def test_invalid_severity_fails(self):
        invalid = {
            "interpreted_issues": [
                {
                    "title": "Test",
                    "explanation": "Test",
                    "bobclue": "DO NOT do this",
                    "severity": "extreme",
                    "fix": "Fix it"
                }
            ],
            "circular_constraint_pairs": [],
            "coordinated_fix_plan": {
                "install_command": "npm install",
                "uninstall_command": None,
                "warning": "test"
            }
        }
        assert _validate_interpretation_schema(invalid) is False

    def test_missing_fix_plan_fails(self):
        invalid = {
            "interpreted_issues": [],
            "circular_constraint_pairs": []
        }
        assert _validate_interpretation_schema(invalid) is False

    def test_non_dict_input_fails(self):
        assert _validate_interpretation_schema([]) is False
        assert _validate_interpretation_schema("string") is False
        assert _validate_interpretation_schema(None) is False


# ─────────────────────────────────────────────
# 11. INTERPRET FINDINGS SAFE
# ─────────────────────────────────────────────

class TestInterpretFindingsSafe:

    def test_falls_back_to_template_without_credentials(
        self, sample_raw_findings
    ):
        result = interpret_findings_safe(
            sample_raw_findings,
            api_key=None,
            project_id=None
        )
        assert result is not None
        assert "interpreted_issues" in result

    def test_falls_back_to_template_with_empty_credentials(
        self, sample_raw_findings
    ):
        result = interpret_findings_safe(
            sample_raw_findings,
            api_key="",
            project_id=""
        )
        assert result is not None
        assert "interpreted_issues" in result

    @patch('scanner.granite_interpreter.requests.post')
    def test_falls_back_on_api_error(
        self, mock_post, sample_raw_findings
    ):
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )
        result = interpret_findings_safe(
            sample_raw_findings,
            api_key="fake_key",
            project_id="fake_project"
        )
        assert result is not None
        assert "interpreted_issues" in result

    @patch('scanner.granite_interpreter.requests.post')
    def test_api_key_not_exposed_in_result(
        self, mock_post, sample_raw_findings
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "results": [{
                    "generated_text": json.dumps({
                        "interpreted_issues": [],
                        "circular_constraint_pairs": [],
                        "coordinated_fix_plan": {
                            "install_command": "npm install",
                            "uninstall_command": None,
                            "warning": "test"
                        }
                    })
                }]
            }
        )
        secret_key = "super_secret_api_key_xyz_123"
        result = interpret_findings_safe(
            sample_raw_findings,
            api_key=secret_key,
            project_id="fake_project"
        )
        result_str = json.dumps(result)
        assert secret_key not in result_str


# ─────────────────────────────────────────────
# 12. GRANITE RESPONSE PARSING
# ─────────────────────────────────────────────

class TestGraniteResponseParsing:

    def test_parses_clean_json(self):
        valid_json = json.dumps({
            "interpreted_issues": [],
            "circular_constraint_pairs": [],
            "coordinated_fix_plan": {
                "install_command": "npm install",
                "uninstall_command": None,
                "warning": "test"
            }
        })
        result = _parse_granite_response(valid_json)
        assert isinstance(result, dict)

    def test_extracts_json_from_mixed_text(self):
        mixed = 'Here is the analysis: {"interpreted_issues": [], "circular_constraint_pairs": [], "coordinated_fix_plan": {"install_command": "npm install", "uninstall_command": null, "warning": "test"}} Hope that helps!'
        result = _parse_granite_response(mixed)
        assert isinstance(result, dict)
        assert "interpreted_issues" in result

    def test_raises_on_no_json(self):
        from scanner.granite_interpreter import GraniteResponseError
        with pytest.raises(GraniteResponseError):
            _parse_granite_response(
                "This has no JSON object at all"
            )

    def test_raises_on_malformed_json(self):
        from scanner.granite_interpreter import GraniteResponseError
        with pytest.raises(GraniteResponseError):
            _parse_granite_response(
                "{this is not valid json at all}"
            )