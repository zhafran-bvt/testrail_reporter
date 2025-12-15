#!/usr/bin/env python3
"""
Script to fix unittest mocking patterns in test files.
"""

import os
import re
from pathlib import Path

def fix_test_file(file_path):
    """Fix mocking patterns in a test file."""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track if we made changes
    original_content = content
    
    # Replace _make_client with proper dependency injection
    content = re.sub(
        r'app\.main\._make_client',
        'app.core.dependencies.get_testrail_client',
        content
    )
    
    # Replace the patching pattern with BaseAPITestCase usage
    # Pattern: with patch("app.core.dependencies.get_testrail_client") as mock_make_client:
    #              mock_tr_client = Mock()
    #              mock_make_client.return_value = mock_tr_client
    pattern = r'with patch\("app\.core\.dependencies\.get_testrail_client"\) as mock_make_client:\s*\n\s*mock_tr_client = Mock\(\)\s*\n\s*mock_make_client\.return_value = mock_tr_client'
    
    # Replace with comment to use self.mock_client
    replacement = '# Use self.mock_client from BaseAPITestCase'
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Replace mock_tr_client references with self.mock_client
    content = re.sub(r'mock_tr_client\.', 'self.mock_client.', content)
    
    # Fix imports - ensure we have the right imports
    if 'from tests.test_base import BaseAPITestCase' not in content:
        # Add the import after other imports
        import_pattern = r'(from tests\.test_base import [^\n]*)'
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern,
                r'\1',
                content
            )
        else:
            # Add import after unittest imports
            content = re.sub(
                r'(import unittest[^\n]*\n)',
                r'\1from tests.test_base import BaseAPITestCase\n',
                content
            )
    
    # Remove unnecessary patch imports if they're no longer needed
    # This is more complex, so we'll leave it for now
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Updated {file_path}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {file_path}")
        return False

def main():
    """Fix all test files."""
    test_dir = Path("tests")
    
    # Files that need fixing
    files_to_fix = [
        "test_add_cases_to_run.py",
        "test_dashboard_e2e.py", 
        "test_dashboard_endpoints.py",
        "test_error_handling.py",
        "test_manage_delete_endpoints.py",
        "test_manage_update_endpoints.py",
        "test_management_user_flows.py",
        "test_remove_cases_from_run.py",
        "test_run_case_management.py"
    ]
    
    fixed_count = 0
    for file_name in files_to_fix:
        file_path = test_dir / file_name
        if file_path.exists():
            if fix_test_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n🎉 Fixed {fixed_count} files")

if __name__ == "__main__":
    main()