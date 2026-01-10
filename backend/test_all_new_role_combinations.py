#!/usr/bin/env python3
"""
Test all new role combinations across all handlers - Comprehensive Verification

This script tests the specific role combinations mentioned in the task:
- Members_CRUD + Regio_All (national admin)
- Members_CRUD + Regio_Utrecht (regional admin)
- Members_Read + Regio_All (national read-only)
- Members_Export + Regio_All (export user)

Tests verify these combinations work across all handlers and authentication scenarios.
"""

import sys
import os
import json
from datetime import datetime

# Add the shared directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

try:
    from auth_utils import (
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        check_regional_data_access,
        get_user_accessible_regions,
        is_admin_user,
        has_permission_and_region_access,
        can_access_resource_region,
        validate_crud_access
    )
    print("✅ Successfully imported auth_utils functions")
except ImportError as e:
    print(f"❌ Failed to import auth_utils: {e}")
    sys.exit(1)


class AllNewRoleCombinationsTest:
    """Test suite for the specific role combinations mentioned in the task"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
        # Define the specific role combinations to test
        self.test_role_combinations = [
            {
                'name': 'National Admin',
                'roles': ['Members_CRUD', 'Regio_All'],
                'description': 'Full member management, all regions',
                'expected_permissions': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
                'expected_regional_access': 'national'
            },
            {
                'name': 'Regional Admin',
                'roles': ['Members_CRUD', 'Regio_Utrecht'],
                'description': 'Full member management, Utrecht region only',
                'expected_permissions': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
                'expected_regional_access': 'regional'
            },
            {
                'name': 'National Read-Only',
                'roles': ['Members_Read', 'Regio_All'],
                'description': 'Read member data, all regions',
                'expected_permissions': ['members_read', 'members_list'],
                'expected_regional_access': 'national'
            },
            {
                'name': 'Export User',
                'roles': ['Members_Export', 'Regio_All'],
                'description': 'Export member data, all regions',
                'expected_permissions': ['members_export', 'members_read'],
                'expected_regional_access': 'national'
            }
        ]
        
        # Define handler scenarios to test
        self.handler_scenarios = [
            {
                'handler': 'get_members',
                'required_permissions': ['members_read'],
                'description': 'Read member list'
            },
            {
                'handler': 'get_member_byid',
                'required_permissions': ['members_read'],
                'description': 'Read specific member'
            },
            {
                'handler': 'create_member',
                'required_permissions': ['members_create'],
                'description': 'Create new member'
            },
            {
                'handler': 'update_member',
                'required_permissions': ['members_update'],
                'description': 'Update member data'
            },
            {
                'handler': 'delete_member',
                'required_permissions': ['members_delete'],
                'description': 'Delete member'
            },
            {
                'handler': 'generate_member_parquet',
                'required_permissions': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                'description': 'Generate parquet files (Docker container)'
            },
            {
                'handler': 'download_parquet',
                'required_permissions': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                'description': 'Download parquet files'
            }
        ]
    
    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"   Details: {details}")
    
    def test_role_combination_basic_validation(self):
        """Test basic validation for each role combination"""
        print("\n🔧 Testing Basic Role Combination Validation")
        
        for combo in self.test_role_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            
            # Test that the role combination is valid (has both permission and region)
            regional_info = determine_regional_access(user_roles)
            
            # Check regional access type
            expected_regional = combo['expected_regional_access']
            actual_regional = 'national' if regional_info['has_full_access'] else 'regional'
            
            self.log_test(
                f"{combo_name}: Regional access type",
                actual_regional == expected_regional,
                f"Expected: {expected_regional}, Got: {actual_regional}, Regional info: {regional_info}"
            )
            
            # Test permission validation for expected permissions
            for permission in combo['expected_permissions']:
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles, [permission], f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
                )
                
                self.log_test(
                    f"{combo_name}: Has {permission} permission",
                    is_authorized,
                    f"Roles: {user_roles}, Permission: {permission}, Error: {error_response}"
                )
    
    def test_role_combinations_across_handlers(self):
        """Test each role combination against all handler scenarios"""
        print("\n🔧 Testing Role Combinations Across All Handlers")
        
        for combo in self.test_role_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            user_permissions = combo['expected_permissions']
            
            print(f"\n--- Testing {combo_name} ({user_roles}) ---")
            
            for scenario in self.handler_scenarios:
                handler_name = scenario['handler']
                required_permissions = scenario['required_permissions']
                description = scenario['description']
                
                # Check if user has any of the required permissions
                has_any_required = any(perm in user_permissions for perm in required_permissions)
                
                # Test with validate_permissions_with_regions
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles, required_permissions, f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
                )
                
                self.log_test(
                    f"{combo_name} -> {handler_name} ({description})",
                    is_authorized == has_any_required,
                    f"Expected: {has_any_required}, Got: {is_authorized}, Required: {required_permissions}, User has: {user_permissions}"
                )
    
    def test_regional_access_validation(self):
        """Test regional access validation for each role combination"""
        print("\n🔧 Testing Regional Access Validation")
        
        test_regions = ['Utrecht', 'Noord-Holland', 'Zuid-Holland', 'Groningen/Drenthe']
        
        for combo in self.test_role_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            
            print(f"\n--- Testing Regional Access for {combo_name} ---")
            
            for region in test_regions:
                can_access, reason = check_regional_data_access(user_roles, region, f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl")
                
                # Determine expected access
                if 'Regio_All' in user_roles:
                    expected_access = True  # National access
                elif f'Regio_{region}' in user_roles:
                    expected_access = True  # Regional match
                else:
                    expected_access = False  # No access to this region
                
                self.log_test(
                    f"{combo_name}: Access to {region} region",
                    can_access == expected_access,
                    f"Expected: {expected_access}, Got: {can_access}, Reason: {reason}, Roles: {user_roles}"
                )
    
    def test_permission_boundaries(self):
        """Test that users can't access unauthorized resources"""
        print("\n🔧 Testing Permission Boundaries")
        
        # Test scenarios where access should be denied
        boundary_tests = [
            {
                'combo_name': 'National Read-Only',
                'roles': ['Members_Read', 'Regio_All'],
                'denied_permissions': ['members_create', 'members_update', 'members_delete'],
                'description': 'Read-only user should not have write permissions'
            },
            {
                'combo_name': 'Export User',
                'roles': ['Members_Export', 'Regio_All'],
                'denied_permissions': ['members_create', 'members_update', 'members_delete'],
                'description': 'Export user should not have write permissions'
            },
            {
                'combo_name': 'Regional Admin',
                'roles': ['Members_CRUD', 'Regio_Utrecht'],
                'denied_regions': ['Noord-Holland', 'Zuid-Holland', 'Groningen/Drenthe'],
                'description': 'Regional admin should not access other regions'
            }
        ]
        
        for test in boundary_tests:
            combo_name = test['combo_name']
            user_roles = test['roles']
            
            # Test denied permissions
            if 'denied_permissions' in test:
                for permission in test['denied_permissions']:
                    is_authorized, error_response, regional_info = validate_permissions_with_regions(
                        user_roles, [permission], f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
                    )
                    
                    self.log_test(
                        f"{combo_name}: Denied {permission}",
                        not is_authorized,
                        f"Should be denied {permission}, but got authorized: {is_authorized}"
                    )
            
            # Test denied regions
            if 'denied_regions' in test:
                for region in test['denied_regions']:
                    can_access, reason = check_regional_data_access(user_roles, region, f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl")
                    
                    self.log_test(
                        f"{combo_name}: Denied access to {region}",
                        not can_access,
                        f"Should be denied access to {region}, but got access: {can_access}, Reason: {reason}"
                    )
    
    def test_crud_operations_comprehensive(self):
        """Test CRUD operations comprehensively for each role combination"""
        print("\n🔧 Testing CRUD Operations Comprehensive")
        
        # Map operations to required permissions (using the actual permission names from auth_utils.py)
        operation_permissions = {
            'create': ['members_create'],
            'read': ['members_read'],
            'update': ['members_update'],
            'delete': ['members_delete'],
            'export': ['members_export']
        }
        
        for combo in self.test_role_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            user_permissions = combo['expected_permissions']
            
            print(f"\n--- Testing CRUD Operations for {combo_name} ---")
            
            for operation, required_perms in operation_permissions.items():
                # Use validate_permissions_with_regions for consistent testing
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles, required_perms, f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
                )
                
                # Determine expected access based on user's actual permissions
                has_required_permission = any(perm in user_permissions for perm in required_perms)
                
                self.log_test(
                    f"{combo_name}: {operation} operation",
                    is_authorized == has_required_permission,
                    f"Expected: {has_required_permission}, Got: {is_authorized}, Required: {required_perms}, User has: {user_permissions}"
                )
    
    def test_docker_container_scenarios(self):
        """Test Docker container specific scenarios (parquet generation)"""
        print("\n🔧 Testing Docker Container Scenarios")
        
        # Docker container handlers require specific permission combinations
        docker_scenarios = [
            {
                'handler': 'generate_member_parquet',
                'required_permissions': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                'description': 'Docker container parquet generation'
            }
        ]
        
        for combo in self.test_role_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            user_permissions = combo['expected_permissions']
            
            for scenario in docker_scenarios:
                handler_name = scenario['handler']
                required_permissions = scenario['required_permissions']
                description = scenario['description']
                
                # For Docker container, user needs ANY of the required permissions
                has_any_required = any(perm in user_permissions for perm in required_permissions)
                
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles, required_permissions, f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
                )
                
                self.log_test(
                    f"{combo_name} -> Docker {handler_name}",
                    is_authorized == has_any_required,
                    f"Expected: {has_any_required}, Got: {is_authorized}, Required: {required_permissions}, User has: {user_permissions}"
                )
    
    def test_edge_cases_and_error_conditions(self):
        """Test edge cases and error conditions for role combinations"""
        print("\n🔧 Testing Edge Cases and Error Conditions")
        
        # Test incomplete role combinations
        incomplete_combinations = [
            {
                'name': 'Permission without Region',
                'roles': ['Members_CRUD'],
                'should_fail': True,
                'description': 'Should fail - missing region role'
            },
            {
                'name': 'Region without Permission',
                'roles': ['Regio_All'],
                'should_fail': True,
                'description': 'Should fail - missing permission role'
            },
            {
                'name': 'Empty Roles',
                'roles': [],
                'should_fail': True,
                'description': 'Should fail - no roles'
            }
        ]
        
        for combo in incomplete_combinations:
            user_roles = combo['roles']
            combo_name = combo['name']
            should_fail = combo['should_fail']
            
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['members_read'], f"test_{combo_name.lower().replace(' ', '_')}@hdcn.nl"
            )
            
            self.log_test(
                f"Edge case: {combo_name}",
                (not is_authorized) == should_fail,
                f"Roles: {user_roles}, Should fail: {should_fail}, Actually failed: {not is_authorized}"
            )
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive New Role Combinations Test")
        print("=" * 80)
        print("Testing specific role combinations:")
        for combo in self.test_role_combinations:
            print(f"  - {combo['name']}: {combo['roles']} ({combo['description']})")
        print("=" * 80)
        
        # Run all test suites
        self.test_role_combination_basic_validation()
        self.test_role_combinations_across_handlers()
        self.test_regional_access_validation()
        self.test_permission_boundaries()
        self.test_crud_operations_comprehensive()
        self.test_docker_container_scenarios()
        self.test_edge_cases_and_error_conditions()
        
        # Print summary
        self.print_test_summary()
        
        return self.passed_tests == self.total_tests
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🏁 TEST SUMMARY - All New Role Combinations")
        print("=" * 80)
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests / self.total_tests * 100):.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test['passed']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test_name']}")
                if test['details']:
                    print(f"    {test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        # Save detailed results
        results_file = f"all_new_role_combinations_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': self.total_tests,
                    'passed_tests': self.passed_tests,
                    'failed_tests': self.total_tests - self.passed_tests,
                    'success_rate': self.passed_tests / self.total_tests * 100,
                    'timestamp': datetime.now().isoformat(),
                    'tested_combinations': self.test_role_combinations
                },
                'test_results': self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")


def main():
    """Main test execution"""
    tester = AllNewRoleCombinationsTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All role combination tests passed successfully!")
        return True
    else:
        print("\n⚠️ Some role combination tests failed - review results above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)