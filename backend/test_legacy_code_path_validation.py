#!/usr/bin/env python3
"""
Validate No Legacy Code Paths - Comprehensive Test

This test validates that no old role checking code is executed in the system.
It ensures that:
1. No legacy _All roles are referenced in active code paths
2. All handlers use the new role structure validation
3. Legacy role combinations are properly rejected
4. Only new role structure is accepted by the system

Task: **Validate no legacy code paths**: Ensure no old role checking code is executed
Status: Testing implementation
"""

import json
import os
import re
import sys
from pathlib import Path
import subprocess


class LegacyCodePathValidator:
    """Validates that no legacy code paths are being executed"""
    
    def __init__(self):
        self.backend_path = Path(__file__).parent
        self.handler_path = self.backend_path / "handler"
        self.shared_path = self.backend_path / "shared"
        
        # Define legacy patterns to search for
        self.legacy_patterns = {
            'legacy_all_roles': [
                r'Members_CRUD_All',
                r'Members_Read_All', 
                r'Members_Export_All',
                r'Events_CRUD_All',
                r'Events_Read_All',
                r'Events_Export_All',
                r'Products_CRUD_All',
                r'Products_Read_All',
                r'Products_Export_All',
                r'Communication_CRUD_All',
                r'Communication_Read_All',
                r'Communication_Export_All',
                r'System_CRUD_All'
            ],
            'legacy_role_checks': [
                r'@require_auth\(\[.*_All.*\]',
                r'in.*user_roles.*_All',
                r'role.*==.*_All',
                r'hdcnAdmins',
                r'Webmaster'
            ],
            'legacy_imports': [
                r'from.*auth_utils.*import.*require_auth',
                r'import.*require_auth'
            ]
        }
        
        # Files that are allowed to have legacy references (documentation, migration scripts, etc.)
        self.allowed_legacy_files = {
            'update_source_roles.py',
            'update_codebase_roles.py',
            'test_user_experience_new_roles.py',
            'test_ui_backend_simple.py',
            'test_ui_backend_integration.py',
            'validate-field-registry.js',
            'test-role-detection.js',
            'test-frontend-backend-integration.js',
            'roleMigrationPlan.md',
            'auth-standardization-implementation-guide.md',
            'handler-auth-standardization-plan.md',
            # Migration template files
            'update_product_migration_template.py',
            'update_payment_migration_template.py',
            # Test files that test legacy compatibility
            'functionPermissions.test.ts',
            'permissions.test.ts',
            'parameterService.test.ts'
        }
        
        self.test_results = {
            'legacy_code_found': [],
            'handlers_with_legacy': [],
            'active_legacy_paths': [],
            'validation_errors': []
        }
    
    def scan_for_legacy_code(self):
        """Scan all Python files for legacy code patterns"""
        print("🔍 Scanning for legacy code patterns...")
        
        # Scan Python files
        python_files = list(self.backend_path.rglob("*.py"))
        
        for file_path in python_files:
            # Skip allowed legacy files
            if file_path.name in self.allowed_legacy_files:
                continue
                
            # Skip test files that are specifically testing legacy compatibility
            if 'test_' in file_path.name and any(pattern in file_path.name for pattern in ['legacy', 'migration', 'compatibility']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for legacy patterns
                for pattern_type, patterns in self.legacy_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            relative_path = file_path.relative_to(self.backend_path)
                            self.test_results['legacy_code_found'].append({
                                'file': str(relative_path),
                                'pattern_type': pattern_type,
                                'pattern': pattern,
                                'matches': matches,
                                'line_numbers': self._find_line_numbers(content, pattern)
                            })
                            
                            # If it's a handler file, mark it specially
                            if 'handler/' in str(relative_path) and 'app.py' in file_path.name:
                                self.test_results['handlers_with_legacy'].append(str(relative_path))
                                
            except Exception as e:
                self.test_results['validation_errors'].append(f"Error reading {file_path}: {str(e)}")
    
    def _find_line_numbers(self, content, pattern):
        """Find line numbers where pattern matches"""
        lines = content.split('\n')
        line_numbers = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                line_numbers.append(i)
        return line_numbers
    
    def test_handler_legacy_rejection(self):
        """Test that handlers properly reject legacy role usage"""
        print("🧪 Testing handler legacy role rejection...")
        
        # Test cases with legacy roles that should be rejected
        legacy_test_cases = [
            {
                'name': 'Legacy Members_CRUD_All',
                'roles': ['Members_CRUD_All'],
                'should_fail': True,
                'reason': 'Legacy _All role should be rejected'
            },
            {
                'name': 'Legacy Products_CRUD_All',
                'roles': ['Products_CRUD_All'],
                'should_fail': True,
                'reason': 'Legacy _All role should be rejected'
            },
            {
                'name': 'Legacy hdcnAdmins',
                'roles': ['hdcnAdmins'],
                'should_fail': True,
                'reason': 'Legacy admin role should be rejected'
            },
            {
                'name': 'New Role Structure - Valid',
                'roles': ['Members_CRUD', 'Regio_All'],
                'should_fail': False,
                'reason': 'New role structure should be accepted'
            },
            {
                'name': 'New Role Structure - Regional',
                'roles': ['Members_CRUD', 'Regio_Utrecht'],
                'should_fail': False,
                'reason': 'New regional role structure should be accepted'
            }
        ]
        
        # Test each case by checking if the auth system would accept it
        for test_case in legacy_test_cases:
            try:
                # Import the auth validation function
                sys.path.append(str(self.shared_path))
                from auth_utils import validate_permissions_with_regions
                
                # Test the role combination
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    test_case['roles'], 
                    ['members_read'],  # Test with a basic permission
                    'test@example.com'
                )
                
                # Check if the result matches expectations
                if test_case['should_fail'] and is_authorized:
                    self.test_results['active_legacy_paths'].append({
                        'test_case': test_case['name'],
                        'roles': test_case['roles'],
                        'issue': 'Legacy roles were accepted when they should be rejected',
                        'expected': 'Rejection',
                        'actual': 'Accepted'
                    })
                elif not test_case['should_fail'] and not is_authorized:
                    self.test_results['active_legacy_paths'].append({
                        'test_case': test_case['name'],
                        'roles': test_case['roles'],
                        'issue': 'Valid new roles were rejected',
                        'expected': 'Acceptance',
                        'actual': 'Rejected',
                        'error': error_response
                    })
                    
            except Exception as e:
                self.test_results['validation_errors'].append(f"Error testing {test_case['name']}: {str(e)}")
    
    def validate_handler_implementations(self):
        """Validate that specific handlers are using new role structure"""
        print("🔧 Validating handler implementations...")
        
        # List of handlers that should be fully migrated
        critical_handlers = [
            'update_member/app.py',
            'update_product/app.py', 
            'update_event/app.py',
            'update_payment/app.py',
            'get_orders/app.py',
            'get_customer_orders/app.py',
            'delete_payment/app.py'
        ]
        
        for handler in critical_handlers:
            handler_path = self.handler_path / handler
            if handler_path.exists():
                try:
                    with open(handler_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for specific legacy patterns in this handler
                    legacy_issues = []
                    
                    # Check for hardcoded legacy role checks
                    if 'Members_CRUD_All' in content and 'deprecated' not in content.lower():
                        legacy_issues.append('Contains active Members_CRUD_All reference')
                    
                    if 'user_roles' in content and '_All' in content and 'legacy' not in content.lower():
                        legacy_issues.append('Contains active _All role checking')
                    
                    # Check for old require_auth decorator usage
                    if re.search(r'@require_auth\([^)]*_All', content):
                        legacy_issues.append('Uses old require_auth decorator with _All roles')
                    
                    if legacy_issues:
                        self.test_results['handlers_with_legacy'].append({
                            'handler': handler,
                            'issues': legacy_issues
                        })
                        
                except Exception as e:
                    self.test_results['validation_errors'].append(f"Error validating {handler}: {str(e)}")
    
    def check_auth_utils_implementation(self):
        """Check that auth_utils.py doesn't contain legacy role mappings"""
        print("🔐 Checking auth_utils.py implementation...")
        
        auth_utils_path = self.shared_path / "auth_utils.py"
        if auth_utils_path.exists():
            try:
                with open(auth_utils_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for legacy role mappings in the role_permissions dictionary
                legacy_in_auth = []
                
                # Look for _All roles in the role_permissions mapping
                if re.search(r"'[^']*_All':\s*\[", content):
                    legacy_in_auth.append('Contains _All roles in role_permissions mapping')
                
                # Look for legacy role checking functions
                if 'require_auth(' in content and '_All' in content:
                    legacy_in_auth.append('Contains legacy require_auth function with _All roles')
                
                if legacy_in_auth:
                    self.test_results['active_legacy_paths'].append({
                        'file': 'shared/auth_utils.py',
                        'issues': legacy_in_auth
                    })
                    
            except Exception as e:
                self.test_results['validation_errors'].append(f"Error checking auth_utils.py: {str(e)}")
    
    def run_comprehensive_validation(self):
        """Run all validation tests"""
        print("🚀 Starting comprehensive legacy code path validation...")
        print("=" * 60)
        
        # Run all validation steps
        self.scan_for_legacy_code()
        self.test_handler_legacy_rejection()
        self.validate_handler_implementations()
        self.check_auth_utils_implementation()
        
        # Generate report
        self.generate_validation_report()
        
        # Return success/failure
        has_issues = (
            len(self.test_results['legacy_code_found']) > 0 or
            len(self.test_results['handlers_with_legacy']) > 0 or
            len(self.test_results['active_legacy_paths']) > 0 or
            len(self.test_results['validation_errors']) > 0
        )
        
        return not has_issues
    
    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("\n📊 LEGACY CODE PATH VALIDATION REPORT")
        print("=" * 60)
        
        # Summary
        total_issues = (
            len(self.test_results['legacy_code_found']) +
            len(self.test_results['handlers_with_legacy']) +
            len(self.test_results['active_legacy_paths']) +
            len(self.test_results['validation_errors'])
        )
        
        if total_issues == 0:
            print("✅ SUCCESS: No legacy code paths found!")
            print("✅ All handlers are using new role structure")
            print("✅ Legacy role checking has been completely removed")
            return
        
        print(f"❌ ISSUES FOUND: {total_issues} legacy code path issues detected")
        print()
        
        # Legacy code found in files
        if self.test_results['legacy_code_found']:
            print("🔍 LEGACY CODE REFERENCES FOUND:")
            for issue in self.test_results['legacy_code_found']:
                print(f"  📄 {issue['file']}")
                print(f"     Pattern: {issue['pattern']}")
                print(f"     Type: {issue['pattern_type']}")
                print(f"     Matches: {issue['matches']}")
                print(f"     Lines: {issue['line_numbers']}")
                print()
        
        # Handlers with legacy code
        if self.test_results['handlers_with_legacy']:
            print("🚨 HANDLERS WITH LEGACY CODE:")
            for handler in self.test_results['handlers_with_legacy']:
                if isinstance(handler, dict):
                    print(f"  🔧 {handler['handler']}")
                    for issue in handler['issues']:
                        print(f"     - {issue}")
                else:
                    print(f"  🔧 {handler}")
                print()
        
        # Active legacy paths
        if self.test_results['active_legacy_paths']:
            print("⚠️ ACTIVE LEGACY CODE PATHS:")
            for path in self.test_results['active_legacy_paths']:
                print(f"  🚫 {path.get('test_case', path.get('file', 'Unknown'))}")
                if 'issue' in path:
                    print(f"     Issue: {path['issue']}")
                if 'roles' in path:
                    print(f"     Roles: {path['roles']}")
                if 'expected' in path:
                    print(f"     Expected: {path['expected']}, Actual: {path['actual']}")
                if 'issues' in path:
                    for issue in path['issues']:
                        print(f"     - {issue}")
                print()
        
        # Validation errors
        if self.test_results['validation_errors']:
            print("💥 VALIDATION ERRORS:")
            for error in self.test_results['validation_errors']:
                print(f"  ❌ {error}")
            print()
        
        # Recommendations
        print("🔧 RECOMMENDED ACTIONS:")
        if self.test_results['legacy_code_found']:
            print("  1. Remove or update legacy role references in identified files")
        if self.test_results['handlers_with_legacy']:
            print("  2. Update handlers to use new role structure validation")
        if self.test_results['active_legacy_paths']:
            print("  3. Fix active legacy code paths that are still accepting old roles")
        print("  4. Re-run this validation after fixes to confirm resolution")
        print()


def main():
    """Main execution function"""
    validator = LegacyCodePathValidator()
    
    try:
        success = validator.run_comprehensive_validation()
        
        if success:
            print("🎉 VALIDATION COMPLETE: No legacy code paths detected!")
            print("✅ Task: **Validate no legacy code paths** - PASSED")
            return True
        else:
            print("❌ VALIDATION FAILED: Legacy code paths still exist!")
            print("❌ Task: **Validate no legacy code paths** - FAILED")
            return False
            
    except Exception as e:
        print(f"💥 VALIDATION ERROR: {str(e)}")
        print("❌ Task: **Validate no legacy code paths** - ERROR")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)