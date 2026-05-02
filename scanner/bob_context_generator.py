"""
ZeroLoop Bob Context Generator

Generates IBM Bob IDE-specific context prompts from analysis results
and estimates Bobcoin savings from preventing retry loops.
"""

from typing import Dict, Any, List


def generate_bob_context(analysis_result: Dict[str, Any]) -> str:
    """
    Generate a structured markdown prompt for IBM Bob IDE.
    
    The prompt is formatted to be referenced throughout the session
    and includes explicit behavioral instructions for Bob.
    
    Args:
        analysis_result: JSON output from run_analysis()
        
    Returns:
        Markdown-formatted context prompt for Bob IDE
    """
    status = analysis_result.get("status", "UNKNOWN")
    status_message = analysis_result.get("status_message", "")
    summary = analysis_result.get("summary", {})
    issues = analysis_result.get("issues", [])
    timestamp = analysis_result.get("timestamp", "")
    project_path = analysis_result.get("project_path", "")
    
    # Build the context prompt
    lines = []
    
    # Header with clearance status
    lines.append("# 🛡️ ZeroLoop Pre-Flight Clearance Report")
    lines.append("")
    lines.append(f"**Project:** `{project_path}`")
    lines.append(f"**Scanned:** {timestamp}")
    lines.append("")
    
    # Clearance status with visual indicator
    status_emoji = {
        "BLOCKED": "🚫",
        "CAUTION": "⚠️",
        "CLEARED": "✅"
    }
    emoji = status_emoji.get(status, "❓")
    
    lines.append(f"## {emoji} CLEARANCE STATUS: **{status}**")
    lines.append("")
    lines.append(f"> {status_message}")
    lines.append("")
    
    # Summary statistics
    total_issues = summary.get("total_issues", 0)
    by_type = summary.get("by_type", {})
    
    lines.append("### 📊 Issue Summary")
    lines.append("")
    lines.append(f"- **Total Issues:** {total_issues}")
    lines.append(f"- **Critical (Errors):** {by_type.get('error', 0)}")
    lines.append(f"- **High (Incompatibilities):** {by_type.get('incompatibility', 0)}")
    lines.append(f"- **Medium (Conflicts):** {by_type.get('conflict', 0)}")
    lines.append(f"- **Low (Redundancies):** {by_type.get('redundancy', 0)}")
    lines.append(f"- **Warnings:** {by_type.get('warning', 0)}")
    lines.append(f"- **Info:** {by_type.get('info', 0)}")
    lines.append("")
    
    # Bob-specific behavioral instructions
    lines.append("---")
    lines.append("")
    lines.append("## 🤖 INSTRUCTIONS FOR BOB")
    lines.append("")
    lines.append("### Critical Rules")
    lines.append("")
    
    if status == "BLOCKED":
        lines.append("⛔ **DO NOT PROCEED** with code changes until critical issues are resolved.")
        lines.append("")
        lines.append("**You MUST:**")
        lines.append("1. Read ALL bobclues below before making ANY changes")
        lines.append("2. Ask the user to fix critical issues first")
        lines.append("3. Do NOT attempt to fix incompatibilities through code workarounds")
        lines.append("4. Do NOT install or upgrade packages without explicit user approval")
        lines.append("")
    elif status == "CAUTION":
        lines.append("⚠️ **PROCEED WITH CAUTION** - review all issues before making changes.")
        lines.append("")
        lines.append("**You MUST:**")
        lines.append("1. Read ALL bobclues below before making changes")
        lines.append("2. Mention relevant issues when suggesting code changes")
        lines.append("3. Avoid patterns that would worsen existing issues")
        lines.append("")
    else:
        lines.append("✅ **CLEARED TO PROCEED** - no critical issues detected.")
        lines.append("")
        lines.append("**You SHOULD:**")
        lines.append("1. Still review info messages below")
        lines.append("2. Follow project conventions")
        lines.append("3. Ask about missing configurations if needed")
        lines.append("")
    
    # Retry loop prevention
    lines.append("### 🔄 Retry Loop Prevention")
    lines.append("")
    lines.append("**If you encounter the same error twice:**")
    lines.append("1. STOP immediately")
    lines.append("2. Re-read this entire report")
    lines.append("3. Check if the error matches a bobclue below")
    lines.append("4. If yes, follow the bobclue's guidance")
    lines.append("5. If no, ask the user for clarification")
    lines.append("")
    lines.append("**DO NOT:**")
    lines.append("- Retry the same approach more than once")
    lines.append("- Ignore bobclues and try workarounds")
    lines.append("- Assume you can fix version incompatibilities with code changes")
    lines.append("- Install packages without checking for conflicts first")
    lines.append("")
    
    # Circuit Breaker for Circular Dependencies
    lines.append("### ⚠️ DEPENDENCY LOOP CIRCUIT BREAKER")
    lines.append("")
    lines.append("**⚠️ CRITICAL: Read this before modifying ANY packages! ⚠️**")
    lines.append("")
    
    # Extract circular pairs from analysis_result
    granite_data = analysis_result.get("granite_interpretation", {})
    circular_pairs = granite_data.get("circular_constraint_pairs", [])
    
    if circular_pairs:
        lines.append("**🚨 STOP if you are about to modify any of these packages:**")
        lines.append("")
        for pair in circular_pairs:
            pkg_a = pair.get("package_a", "unknown")
            pkg_b = pair.get("package_b", "unknown")
            reason = pair.get("reason", "No reason provided")
            lines.append(f"- **{pkg_a}** ↔️ **{pkg_b}**")
            lines.append(f"  - Reason: {reason}")
        lines.append("")
        lines.append("**⚠️ These packages have circular constraints. You MUST:**")
        lines.append("1. **STOP** if about to modify a package already modified in this session")
        lines.append("2. Review the coordinated upgrade plan below")
        lines.append("3. **WAIT for user approval** before making ANY changes")
        lines.append("4. **DO NOT** install packages individually")
        lines.append("")
        lines.append("**⚠️ If you retry the same approach twice:**")
        lines.append("1. **STOP immediately**")
        lines.append("2. Ask the user for guidance")
        lines.append("3. **DO NOT** attempt a third time")
        lines.append("")
    else:
        lines.append("✅ No circular dependency constraints detected.")
        lines.append("")
    
    # Coordinated Fix Plan
    coordinated_plan = granite_data.get("coordinated_fix_plan", {})
    
    if coordinated_plan and circular_pairs:
        lines.append("---")
        lines.append("")
        lines.append("### 🔧 COORDINATED FIX PLAN")
        lines.append("")
        lines.append("**Use this atomic command sequence to fix circular constraints:**")
        lines.append("")
        
        # Uninstall command (if present)
        uninstall_cmd = coordinated_plan.get("uninstall_command")
        if uninstall_cmd:
            lines.append("**Step 1: Remove conflicting packages**")
            lines.append("```bash")
            lines.append(uninstall_cmd)
            lines.append("```")
            lines.append("")
        
        # Install command (always present)
        install_cmd = coordinated_plan.get("install_command", "npm install")
        step_num = "2" if uninstall_cmd else "1"
        lines.append(f"**Step {step_num}: Install coordinated versions**")
        lines.append("```bash")
        lines.append(install_cmd)
        lines.append("```")
        lines.append("")
        
        # Warning
        warning = coordinated_plan.get("warning", "Review changes carefully")
        lines.append(f"**⚠️ WARNING:** {warning}")
        lines.append("")
        lines.append("**🚫 DO NOT run any other npm install commands before these complete!**")
        lines.append("")
    
    # List all bobclues
    if issues:
        lines.append("---")
        lines.append("")
        lines.append("## 🎯 BOBCLUES - READ BEFORE CODING")
        lines.append("")
        lines.append("These are critical guidance points extracted from detected issues.")
        lines.append("**Reference these throughout your session.**")
        lines.append("")
        
        # Group by severity
        critical_issues = [i for i in issues if i.get("type") in ["error", "incompatibility"]]
        high_issues = [i for i in issues if i.get("type") in ["conflict", "redundancy"]]
        low_issues = [i for i in issues if i.get("type") in ["warning", "info"]]
        
        if critical_issues:
            lines.append("### 🚨 CRITICAL - Must Fix Before Coding")
            lines.append("")
            for i, issue in enumerate(critical_issues, 1):
                lines.append(f"**{i}. {issue.get('title', 'Unknown Issue')}**")
                lines.append("")
                lines.append(f"**Category:** {issue.get('category', 'unknown')}")
                lines.append("")
                lines.append(f"**Detail:** {issue.get('detail', 'No details')}")
                lines.append("")
                lines.append(f"**🤖 BOBCLUE:**")
                lines.append(f"> {issue.get('bobclue', 'No guidance available')}")
                lines.append("")
                lines.append(f"**Fix:**")
                lines.append("```")
                lines.append(issue.get('fix', 'No fix available'))
                lines.append("```")
                lines.append("")
        
        if high_issues:
            lines.append("### ⚠️ HIGH PRIORITY - Review Before Coding")
            lines.append("")
            for i, issue in enumerate(high_issues, 1):
                lines.append(f"**{i}. {issue.get('title', 'Unknown Issue')}**")
                lines.append("")
                lines.append(f"**🤖 BOBCLUE:**")
                lines.append(f"> {issue.get('bobclue', 'No guidance available')}")
                lines.append("")
                lines.append(f"**Fix:** {issue.get('fix', 'No fix available')}")
                lines.append("")
        
        if low_issues:
            lines.append("### ℹ️ INFORMATIONAL - Good to Know")
            lines.append("")
            for i, issue in enumerate(low_issues, 1):
                lines.append(f"**{i}. {issue.get('title', 'Unknown Issue')}**")
                lines.append("")
                lines.append(f"**🤖 BOBCLUE:**")
                lines.append(f"> {issue.get('bobclue', 'No guidance available')}")
                lines.append("")
    
    # Errors to NOT fix through code
    lines.append("---")
    lines.append("")
    lines.append("## ❌ DO NOT FIX THROUGH CODE CHANGES")
    lines.append("")
    lines.append("The following issues **CANNOT** be fixed by modifying application code:")
    lines.append("")
    
    unfixable_by_code = []
    for issue in issues:
        issue_type = issue.get("type", "")
        category = issue.get("category", "")
        
        if issue_type in ["incompatibility", "error"] and category in ["dependencies", "node-version"]:
            unfixable_by_code.append(issue)
    
    if unfixable_by_code:
        for issue in unfixable_by_code:
            lines.append(f"- **{issue.get('title', 'Unknown')}**")
            lines.append(f"  - Requires: Package management or environment changes")
            lines.append(f"  - Do NOT: Try to work around with code")
            lines.append("")
    else:
        lines.append("✅ All detected issues can potentially be addressed through code changes.")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("## 📝 Session Guidelines")
    lines.append("")
    lines.append("1. **Keep this report open** in a separate tab for reference")
    lines.append("2. **Check bobclues** before implementing any solution")
    lines.append("3. **Stop and re-read** if you encounter repeated errors")
    lines.append("4. **Ask the user** if a bobclue conflicts with their request")
    lines.append("5. **Update the user** on which issues you're addressing")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by ZeroLoop - Preventing retry loops, one scan at a time* 🔄🚫")
    
    return "\n".join(lines)

def generate_reset_context(analysis_result: Dict[str, Any]) -> str:
    """
    Generate a concise reset prompt for Bob when he's stuck in a loop.
    
    Under 200 words, focuses only on circular constraints and circuit breaker.
    
    Args:
        analysis_result: JSON output from run_analysis()
        
    Returns:
        Markdown-formatted reset context (< 200 words)
    """
    lines = []
    
    # Header
    lines.append("# 🛑 STOP — RE-READ YOUR CONSTRAINTS")
    lines.append("")
    
    # Extract circular pairs
    granite_data = analysis_result.get("granite_interpretation", {})
    circular_pairs = granite_data.get("circular_constraint_pairs", [])
    
    if circular_pairs:
        lines.append("**Circular Constraint Pairs:**")
        lines.append("")
        for pair in circular_pairs:
            pkg_a = pair.get("package_a", "unknown")
            pkg_b = pair.get("package_b", "unknown")
            lines.append(f"- **{pkg_a}** ↔️ **{pkg_b}**")
        lines.append("")
        
        # Coordinated fix
        coordinated_plan = granite_data.get("coordinated_fix_plan", {})
        install_cmd = coordinated_plan.get("install_command", "npm install")
        lines.append("**Coordinated Fix:**")
        lines.append("```bash")
        lines.append(install_cmd)
        lines.append("```")
        lines.append("")
    else:
        lines.append("No circular constraints detected.")
        lines.append("")
    
    # Circuit breaker reminder
    lines.append("**⚠️ Circuit Breaker:** If modifying a package already modified in this session, STOP and get user approval. If retrying same approach twice, STOP and ask for guidance.")
    lines.append("")
    
    return "\n".join(lines)



def estimate_bobcoin_savings(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate Bobcoin savings from preventing retry loops.
    
    Cost model:
    - Critical issues (error, incompatibility): 12 Bobcoins saved
    - High issues (conflict, redundancy): 4 Bobcoins saved
    - Medium issues (warning): 1 Bobcoin saved
    - Circular constraint pairs: 20 Bobcoins saved each
    - Granite scan cost: $0.0001
    
    Args:
        analysis_result: JSON output from run_analysis()
        
    Returns:
        Dictionary with:
        - total_saved: Total Bobcoins saved
        - breakdown: List of savings per issue
        - summary: Summary by severity
        - granite_cost: Cost of Granite scan
        - net_roi: ROI summary string
    """
    issues = analysis_result.get("issues", [])
    
    # Updated cost model - direct Bobcoin values
    cost_model = {
        "error": 12,
        "incompatibility": 12,
        "conflict": 4,
        "redundancy": 4,
        "warning": 1,
        "info": 0
    }
    
    breakdown = []
    total_saved = 0
    
    summary_by_severity = {
        "critical": {"count": 0, "saved": 0},
        "high": {"count": 0, "saved": 0},
        "medium": {"count": 0, "saved": 0},
        "low": {"count": 0, "saved": 0}
    }
    
    for issue in issues:
        issue_type = issue.get("type", "info")
        title = issue.get("title", "Unknown Issue")
        
        # Get Bobcoin value for this issue type
        saved = cost_model.get(issue_type, 0)
        
        total_saved += saved
        
        # Categorize by severity
        if issue_type in ["error", "incompatibility"]:
            severity = "critical"
        elif issue_type in ["conflict", "redundancy"]:
            severity = "high"
        elif issue_type == "warning":
            severity = "medium"
        else:
            severity = "low"
        
        summary_by_severity[severity]["count"] += 1
        summary_by_severity[severity]["saved"] += saved
        
        if saved > 0:
            breakdown.append({
                "issue": title,
                "type": issue_type,
                "severity": severity,
                "estimated_loops_prevented": 4 if severity == "critical" else (2 if severity == "high" else 1),
                "cost_per_loop": 3 if severity == "critical" else (2 if severity == "high" else 1),
                "bobcoins_saved": saved
            })
    
    # Add savings for circular constraint pairs
    granite_data = analysis_result.get("granite_interpretation", {})
    circular_pairs = granite_data.get("circular_constraint_pairs", [])
    circular_savings = len(circular_pairs) * 20  # 20 Bobcoins per pair
    total_saved += circular_savings
    
    if circular_pairs:
        for pair in circular_pairs:
            pkg_a = pair.get("package_a", "unknown")
            pkg_b = pair.get("package_b", "unknown")
            breakdown.append({
                "issue": f"Circular constraint: {pkg_a} ↔️ {pkg_b}",
                "type": "circular_constraint",
                "severity": "critical",
                "estimated_loops_prevented": 5,
                "cost_per_loop": 4,
                "bobcoins_saved": 20
            })
        
        summary_by_severity["critical"]["count"] += len(circular_pairs)
        summary_by_severity["critical"]["saved"] += circular_savings
    
    # Calculate ROI
    granite_cost = 0.0001  # $0.0001 per scan
    bobcoin_value = 0.10  # Approximate dollar value per Bobcoin
    net_roi = f"Spent ${granite_cost:.4f}, saved ~${total_saved * bobcoin_value:.2f} worth of Bobcoin capacity"
    
    return {
        "total_saved": total_saved,
        "breakdown": breakdown,
        "summary": summary_by_severity,
        "granite_cost": granite_cost,
        "net_roi": net_roi,
        "explanation": (
            f"ZeroLoop prevented an estimated {total_saved} Bobcoins worth of retry loops "
            f"(including {len(circular_pairs)} circular constraint pairs at 20 Bobcoins each). "
            f"Critical issues save 12 Bobcoins, high-priority 4 Bobcoins, medium 1 Bobcoin. "
            f"{net_roi}."
        )
    }


# Example usage and testing
if __name__ == "__main__":
    import sys
    import json
    from analyze import run_analysis
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("Usage: python bob_context_generator.py <command> [args]")
        print("\nCommands:")
        print("  full_context    - Generate full Bob context (reads JSON from stdin)")
        print("  reset_context   - Generate reset context (reads JSON from stdin)")
        print("  estimate_savings - Estimate Bobcoin savings (reads JSON from stdin)")
        print("  all <project_path> - Run full analysis and generate all outputs")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "full_context":
        # Read analysis result from stdin
        analysis_result = json.loads(sys.stdin.read())
        context = generate_bob_context(analysis_result)
        print(context)
    
    elif command == "reset_context":
        # Read analysis result from stdin
        analysis_result = json.loads(sys.stdin.read())
        context = generate_reset_context(analysis_result)
        print(context)
    
    elif command == "estimate_savings":
        # Read analysis result from stdin
        analysis_result = json.loads(sys.stdin.read())
        savings = estimate_bobcoin_savings(analysis_result)
        print(json.dumps(savings))
    
    elif command == "all":
        # Legacy mode - run full analysis
        if len(sys.argv) < 3:
            print("Error: 'all' command requires project_path")
            sys.exit(1)
        
        project_path = sys.argv[2]
        
        # Run analysis
        print("Running analysis...")
        result = run_analysis(project_path)
        
        # Generate Bob context
        print("\n" + "="*80)
        print("BOB CONTEXT PROMPT")
        print("="*80 + "\n")
        context = generate_bob_context(result)
        print(context)
        
        # Estimate savings
        print("\n" + "="*80)
        print("BOBCOIN SAVINGS ESTIMATE")
        print("="*80 + "\n")
        savings = estimate_bobcoin_savings(result)
        print(json.dumps(savings, indent=2))
    
    else:
        print(f"Error: Unknown command '{command}'")
        sys.exit(1)

# Made with Bob