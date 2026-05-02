"""
ZeroLoop Scanner Package

A Node.js project analyzer that detects dependency conflicts,
version mismatches, and provides Bob-specific guidance.

Layer 1: Raw findings collection (analyze.py)
Layer 2: AI interpretation (granite_interpreter.py)
"""

from .analyze import (
    check_npm_audit,
    check_depcheck,
    check_node_version,
    check_circular_dependencies,
    run_analysis
)
from .granite_interpreter import (
    interpret_findings,
    template_interpret,
    interpret_findings_safe,
    GraniteAPIError,
    GraniteResponseError
)
from .bob_context_generator import (
    generate_bob_context,
    estimate_bobcoin_savings
)

__version__ = "0.2.0"
__all__ = [
    # Layer 1: Raw findings
    "check_npm_audit",
    "check_depcheck",
    "check_node_version",
    "check_circular_dependencies",
    "run_analysis",
    # Layer 2: Interpretation
    "interpret_findings",
    "template_interpret",
    "interpret_findings_safe",
    "GraniteAPIError",
    "GraniteResponseError",
    # Context generation
    "generate_bob_context",
    "estimate_bobcoin_savings"
]

# Made with Bob
