"""Test script for check_circular_dependencies function"""

import sys
from analyze import check_circular_dependencies

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    project_path = "test_project"
    
    print("Testing check_circular_dependencies()...\n")
    issues = check_circular_dependencies(project_path)
    
    if not issues:
        print("✅ No circular dependency issues detected!")
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
