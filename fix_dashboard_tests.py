#!/usr/bin/env python3
"""
Script to fix all _make_client patterns in test_dashboard_endpoints.py
"""

import re


def fix_dashboard_tests():
    """Fix all _make_client patterns in test_dashboard_endpoints.py"""

    with open("tests/test_dashboard_endpoints.py", "r") as f:
        content = f.read()

    # Pattern 1: Remove TestClient imports and instantiation
    content = re.sub(r"\s*from fastapi\.testclient import TestClient\s*", "\n", content)
    content = re.sub(r"\s*from app\.main import app\s*", "\n", content)
    content = re.sub(r"\s*TestClient\(app\)\s*", "\n", content)
    content = re.sub(r"\s*client = TestClient\(app\)\s*", "\n", content)

    # Pattern 2: Remove _make_client patches and replace with direct mock usage
    # This is more complex, so we'll do it step by step

    # First, find all instances of the pattern and replace them
    pattern = r'(\s*)with patch\("app\.main\._make_client"\) as mock_make_client:\s*\n\s*mock_tr_client = Mock\(\)\s*\n\s*mock_make_client\.return_value = mock_tr_client\s*\n'

    def replace_patch(match):
        indent = match.group(1)
        return f"{indent}# Use self.mock_client from BaseAPITestCase\n"

    content = re.sub(pattern, replace_patch, content)

    # Replace mock_tr_client with self.mock_client
    content = re.sub(r"mock_tr_client\.", "self.mock_client.", content)

    # Remove any remaining cache clearing comments that are now orphaned
    content = re.sub(r"\s*# Clear cache before test\s*", "\n", content)
    content = re.sub(r"\s*# Clear cache to ensure API is called\s*", "\n", content)

    # Clean up extra whitespace
    content = re.sub(r"\n\n\n+", "\n\n", content)

    with open("tests/test_dashboard_endpoints.py", "w") as f:
        f.write(content)

    print("Fixed all _make_client patterns in test_dashboard_endpoints.py")


if __name__ == "__main__":
    fix_dashboard_tests()
