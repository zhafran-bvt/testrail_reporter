#!/usr/bin/env python3
"""
Script to fix test files by updating them to use the new BaseTestCase.
"""

import re
from pathlib import Path


def fix_test_file(file_path):
    """Fix a single test file."""
    print(f"Fixing {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Skip if already using BaseTestCase
    if "from tests.test_base import" in content:
        print(f"  Already fixed: {file_path}")
        return

    # Skip if it doesn't use TestClient or unittest
    if "TestClient" not in content or "unittest" not in content:
        print(f"  Skipping (not a TestClient test): {file_path}")
        return

    original_content = content

    # Replace old imports and setup patterns
    patterns_to_replace = [
        # Replace old imports
        (
            r"import types\nimport unittest\nfrom unittest\.mock import Mock\n\nfrom fastapi\.testclient import TestClient\n\nimport app\.main as main",
            "from tests.test_base import BaseAPITestCase",
        ),
        # Replace class inheritance
        (r"class (\w+)\(unittest\.TestCase\):", r"class \1(BaseAPITestCase):"),
        # Remove old setUp methods that create fake clients
        (
            r'    def setUp\(self\):\s*"""Set up test client and mocks\.""".*?main\._default_priority_id = lambda: 1\n',
            "",
            re.DOTALL,
        ),
        # Replace fake_client references
        (r"self\.fake_client", "self.mock_client"),
        # Replace client creation patterns
        (r"self\.client = TestClient\(main\.app\)", ""),
        # Remove fake client setup
        (r"        # Create fake client.*?main\._default_priority_id = lambda: 1\n", "", re.DOTALL),
    ]

    for pattern, replacement, *flags in patterns_to_replace:
        flag = flags[0] if flags else 0
        content = re.sub(pattern, replacement, content, flags=flag)

    # Clean up empty setUp methods
    content = re.sub(r'    def setUp\(self\):\s*""".*?"""\s*pass\s*\n', "", content, flags=re.DOTALL)
    content = re.sub(r"    def setUp\(self\):\s*pass\s*\n", "", content)

    # Clean up multiple empty lines
    content = re.sub(r"\n\n\n+", "\n\n", content)

    # Only write if content changed
    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"  Fixed: {file_path}")
    else:
        print(f"  No changes needed: {file_path}")


def main():
    """Fix all test files."""
    test_dir = Path("tests")

    for test_file in test_dir.glob("test_*.py"):
        if test_file.name in ["test_base.py"]:  # Skip our base class
            continue
        fix_test_file(test_file)


if __name__ == "__main__":
    main()
