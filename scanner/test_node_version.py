"""Test script for check_node_version function"""

import sys
from analyze import check_node_version

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    project_path = "test_project"
    
    print("Testing check_node_version()...\n")
    issues = check_node_version(project_path)
    
    if not issues:
        print("✅ No Node version issues detected!")
    else:
        print(f"⚠️  Found {len(issues)} issue(s):\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. [{issue['type'].upper()}] {issue['title']}")
            print(f"   Category: {issue['category']}")
            print(f"   Detail: {issue['detail']}")
            print(f"   🤖 Bob Clue: {issue['bobclue']}")
            print(f"   Fix: {issue['fix']}")
            print()

# Made with Bob
