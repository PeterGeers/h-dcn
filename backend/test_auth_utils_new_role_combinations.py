#!/usr/bin/env python3
"""
Test auth_utils with new role combinations - Comprehensive Verification

This script tests the auth_utils.py functions with all new role combinations
to verify that the new permission + region role structure works correctly.

Tests cover:
1. validate_permissions_with_regions() with all valid role combinations
2. Regional access validation and filtering
3. Permission validation for CRUD operations
4. New role structure validation
5. Edge cases and error conditions
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
        validate_user_has_new_role_structure,
        is_admin_user,
        has_permission_and_region_access,
        can_access_resource_region,
        validate_crud_access,
        get_user_permissions_summary,
        quick_role_check
    )
    print("✅ Successfully imported auth_utils functions")
except ImportError as e:
    print(f"❌ Failed to import auth_utils: {e}")
    sys.exit(1)


class AuthUtilsNewRoleTest:
    """Comprehensive test suite for new role combinations in auth_utils"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
        # Define test role combinations
        self.permission_roles = [
            'Members_CRUD', 'Members_Read', 'Members_Export',
            'Events_CRUD', 'Events_Read', 'Events_Export',
            'Products_CRUD', 'Products_Read', 'Products_Export',
            'Communication_CRUD', 'Communication_Read', 'Communication_Export'
        ]
        
        self.region_roles = [
            'Regio_All',
            'Regio_Noord-Holland',
            'Regio_Zuid-Holland',
            'Regio_Friesland',
            'Regio_Utrecht',
            'Regio_Oost',
            'Regio_Limburg',
            'Regio_Groningen/Drenthe',
            'Regio_Brabant/Zeeland',
            'Regio_Duitsland'
        ]
        
        self.admin_roles = [
            'System_CRUD',
            'System_User_Management'
        ]
        
        self.other_roles = [
            'Members_Status_Approve',
            'Webshop_Management',
            'National_Chairman',
            'National_Secretary',
            'National_Treasurer',
            'hdcnLeden'
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
    
    def test_admin_roles_full_access(self):
        """Test that admin roles have full access regardless of region roles"""
        print("\n🔧 Testing Admin Roles Full Access")
        
        for admin_role in self.admin_roles:
            # Test admin role alone
            user_roles = [admin_role]
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['members_read'], 'test@example.com'
            )
            
            self.log_test(
                f"Admin role {admin_role} alone has full access",
                is_authorized and regional_info and regional_info.get('has_full_access'),
                f"Roles: {user_roles}, Regional info: {regional_info}"
            )
            
            # Test admin role with region roles (should still work)
            user_roles = [admin_role, 'Regio_Noord-Holland']
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['members_read'], 'test@example.com'
            )
            
            self.log_test(
                f"Admin role {admin_role} with region role has full access",
                is_authorized and regional_info and regional_info.get('has_full_access'),
                f"Roles: {user_roles}, Regional info: {regional_info}"
            )
    
    def test_new_role_structure_combinations(self):
        """Test all valid permission + region role combinations"""
        print("\n🔧 Testing New Role Structure Combinations")
        
        # Test each permission role with each region role for matching resource types
        resource_types = ['Members', 'Events', 'Products', 'Communication']
        
        for resource_type in resource_types:
            # Get permission roles for this resource type
            resource_permission_roles = [role for role in self.permission_roles if role.startswith(resource_type)]
            
            for permission_role in resource_permission_roles:
                for region_role in self.region_roles:
                    user_roles = [permission_role, region_role]
                    
                    # Determine expected permissions based on role type
                    if 'CRUD' in permission_role:
                        test_permissions = [f'{resource_type.lower()}_create', f'{resource_type.lower()}_read', 
                                          f'{resource_type.lower()}_update', f'{resource_type.lower()}_delete']
                    elif 'Read' in permission_role:
                        test_permissions = [f'{resource_type.lower()}_read']
                    elif 'Export' in permission_role:
                        test_permissions = [f'{resource_type.lower()}_export']
                    else:
                        test_permissions = [f'{resource_type.lower()}_read']
                    
                    # Test permission validation
                    for permission in test_permissions:
                        is_authorized, error_response, regional_info = validate_permissions_with_regions(
                            user_roles, [permission], 'test@example.com'
                        )
                        
                        # Should be authorized for matching resource type permissions
                        expected_authorized = True
                        
                        self.log_test(
                            f"{permission_role} + {region_role} -> {permission}",
                            is_authorized == expected_authorized,
                            f"Expected: {expected_authorized}, Got: {is_authorized}, Roles: {user_roles}"
                        )
    
    def test_incomplete_role_structures(self):
        """Test that incomplete role structures are properly rejected"""
        print("\n🔧 Testing Incomplete Role Structures")
        
        # Test permission role without region role
        for permission_role in self.permission_roles:
            user_roles = [permission_role]
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['members_read'], 'test@example.com'
            )
            
            self.log_test(
                f"Permission role {permission_role} without region role is rejected",
                not is_authorized,
                f"Roles: {user_roles}, Should be rejected for missing region role"
            )
        
        # Test region role without permission role
        for region_role in self.region_roles:
            user_roles = [region_role]
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['members_read'], 'test@example.com'
            )
            
            self.log_test(
                f"Region role {region_role} without permission role is rejected",
                not is_authorized,
                f"Roles: {user_roles}, Should be rejected for missing permission role"
            )
    
    def test_regional_access_validation(self):
        """Test regional access validation and filtering"""
        print("\n🔧 Testing Regional Access Validation")
        
        test_cases = [
            # (user_roles, data_region, should_have_access, reason)
            (['Members_Read', 'Regio_All'], 'Noord-Holland', True, 'Regio_All grants access to all regions'),
            (['Members_Read', 'Regio_Noord-Holland'], 'Noord-Holland', True, 'Matching region access'),
            (['Members_Read', 'Regio_Noord-Holland'], 'Zuid-Holland', False, 'Different region access'),
            (['Members_Read', 'Regio_Groningen/Drenthe'], 'Groningen/Drenthe', True, 'Complex region name matching'),
            (['System_CRUD'], 'Noord-Holland', True, 'Admin access to all regions'),
            (['Members_Read', 'Regio_Noord-Holland', 'Regio_Zuid-Holland'], 'Zuid-Holland', True, 'Multiple region access'),
        ]
        
        for user_roles, data_region, expected_access, reason in test_cases:
            can_access, access_reason = check_regional_data_access(user_roles, data_region, 'test@example.com')
            
            self.log_test(
                f"Regional access: {user_roles} -> {data_region}",
                can_access == expected_access,
                f"Expected: {expected_access} ({reason}), Got: {can_access} ({access_reason})"
            )
    
    def test_crud_operations_validation(self):
        """Test CRUD operations validation with new role structure"""
        print("\n🔧 Testing CRUD Operations Validation")
        
        test_cases = [
            # (user_roles, resource_type, operation, should_have_access)
            (['Members_CRUD', 'Regio_All'], 'Members', 'create', True),
            (['Members_CRUD', 'Regio_All'], 'Members', 'read', True),
            (['Members_CRUD', 'Regio_All'], 'Members', 'update', True),
            (['Members_CRUD', 'Regio_All'], 'Members', 'delete', True),
            (['Members_Read', 'Regio_All'], 'Members', 'read', True),
            (['Members_Read', 'Regio_All'], 'Members', 'create', False),
            (['Members_Export', 'Regio_All'], 'Members', 'export', True),
            (['Members_Export', 'Regio_All'], 'Members', 'read', False),
            (['Events_CRUD', 'Regio_All'], 'Events', 'create', True),
            (['Products_Read', 'Regio_All'], 'Products', 'read', True),
            (['Communication_CRUD', 'Regio_All'], 'Communication', 'update', True),
        ]
        
        for user_roles, resource_type, operation, expected_access in test_cases:
            result = validate_crud_access(user_roles, resource_type, operation)
            
            self.log_test(
                f"CRUD: {user_roles} -> {resource_type}.{operation}",
                result['has_access'] == expected_access,
                f"Expected: {expected_access}, Got: {result['has_access']}, Message: {result['message']}"
            )
    
    def test_role_structure_validation(self):
        """Test new role structure validation function"""
        print("\n🔧 Testing Role Structure Validation")
        
        test_cases = [
            # (user_roles, expected_valid_structure, description)
            (['Members_CRUD', 'Regio_All'], True, 'Valid permission + region structure'),
            (['System_CRUD'], True, 'Admin role (no region needed)'),
            (['Members_Read'], False, 'Permission without region'),
            (['Regio_All'], False, 'Region without permission'),
            (['Members_CRUD', 'Regio_Noord-Holland', 'Events_Read'], True, 'Multiple permissions with region'),
            (['hdcnLeden'], False, 'Legacy role only'),
            ([], False, 'No roles'),
        ]
        
        for user_roles, expected_valid, description in test_cases:
            validation_result = validate_user_has_new_role_structure(user_roles)
            
            self.log_test(
                f"Role structure validation: {description}",
                validation_result['has_new_structure'] == expected_valid,
                f"Roles: {user_roles}, Expected: {expected_valid}, Got: {validation_result['has_new_structure']}, Message: {validation_result['validation_message']}"
            )
    
    def test_permission_and_region_access_helper(self):
        """Test the has_permission_and_region_access helper function"""
        print("\n🔧 Testing Permission and Region Access Helper")
        
        test_cases = [
            # (user_roles, required_permission, required_regions, expected_access, description)
            (['Members_CRUD', 'Regio_All'], 'Members_CRUD', None, True, 'Valid permission + region'),
            (['Members_CRUD', 'Regio_Noord-Holland'], 'Members_CRUD', ['Noord-Holland'], True, 'Specific region match'),
            (['Members_CRUD', 'Regio_Noord-Holland'], 'Members_CRUD', ['Zuid-Holland'], False, 'Region mismatch'),
            (['System_CRUD'], 'Members_CRUD', ['Noord-Holland'], True, 'Admin override'),
            (['Members_Read', 'Regio_All'], 'Members_CRUD', None, False, 'Insufficient permission'),
        ]
        
        for user_roles, required_permission, required_regions, expected_access, description in test_cases:
            result = has_permission_and_region_access(user_roles, required_permission, required_regions)
            
            self.log_test(
                f"Permission + Region helper: {description}",
                result['has_access'] == expected_access,
                f"Roles: {user_roles}, Required: {required_permission}, Regions: {required_regions}, Expected: {expected_access}, Got: {result['has_access']}"
            )
    
    def test_quick_role_check_utility(self):
        """Test the quick_role_check utility function"""
        print("\n🔧 Testing Quick Role Check Utility")
        
        test_cases = [
            # (user_roles, check_type, kwargs, expected_result, description)
            (['System_CRUD'], 'admin', {}, True, 'Admin check'),
            (['Members_Read'], 'admin', {}, False, 'Non-admin check'),
            (['Members_CRUD', 'Events_Read'], 'any_role', {'roles': ['Members_CRUD', 'Products_CRUD']}, True, 'Any role match'),
            (['Members_CRUD', 'Regio_All'], 'permission', {'permission': 'Members_CRUD'}, True, 'Permission check'),
            (['Members_CRUD', 'Regio_Noord-Holland'], 'region', {'region': 'Noord-Holland'}, True, 'Region access check'),
        ]
        
        for user_roles, check_type, kwargs, expected_result, description in test_cases:
            has_access, message = quick_role_check(user_roles, check_type, **kwargs)
            
            self.log_test(
                f"Quick check: {description}",
                has_access == expected_result,
                f"Roles: {user_roles}, Check: {check_type}, Expected: {expected_result}, Got: {has_access}, Message: {message}"
            )
    
    def test_user_permissions_summary(self):
        """Test comprehensive user permissions summary"""
        print("\n🔧 Testing User Permissions Summary")
        
        test_cases = [
            (['System_CRUD'], 'admin'),
            (['Members_CRUD', 'Regio_All'], 'national'),
            (['Members_Read', 'Regio_Noord-Holland'], 'regional'),
            (['hdcnLeden'], 'regional'),  # Basic member
        ]
        
        for user_roles, expected_access_level in test_cases:
            summary = get_user_permissions_summary(user_roles)
            
            self.log_test(
                f"Permissions summary for {user_roles}",
                summary['summary']['access_level'] == expected_access_level,
                f"Expected access level: {expected_access_level}, Got: {summary['summary']['access_level']}"
            )
    
    def test_edge_cases_and_error_conditions(self):
        """Test edge cases and error conditions"""
        print("\n🔧 Testing Edge Cases and Error Conditions")
        
        # Test with empty roles
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            [], ['members_read'], 'test@example.com'
        )
        self.log_test(
            "Empty roles list is rejected",
            not is_authorized,
            "Empty roles should be rejected"
        )
        
        # Test with invalid permission
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            ['Members_CRUD', 'Regio_All'], ['invalid_permission'], 'test@example.com'
        )
        self.log_test(
            "Invalid permission is rejected",
            not is_authorized,
            "Invalid permissions should be rejected"
        )
        
        # Test with None values
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                None, ['members_read'], 'test@example.com'
            )
            self.log_test(
                "None roles handled gracefully",
                not is_authorized,
                "None roles should be handled gracefully"
            )
        except Exception as e:
            self.log_test(
                "None roles handled gracefully",
                False,
                f"Exception raised: {e}"
            )
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Comprehensive Auth Utils New Role Combinations Test")
        print("=" * 80)
        
        # Run all test suites
        self.test_admin_roles_full_access()
        self.test_new_role_structure_combinations()
        self.test_incomplete_role_structures()
        self.test_regional_access_validation()
        self.test_crud_operations_validation()
        self.test_role_structure_validation()
        self.test_permission_and_region_access_helper()
        self.test_quick_role_check_utility()
        self.test_user_permissions_summary()
        self.test_edge_cases_and_error_conditions()
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🏁 TEST SUMMARY")
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
        results_file = f"auth_utils_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': self.total_tests,
                    'passed_tests': self.passed_tests,
                    'failed_tests': self.total_tests - self.passed_tests,
                    'success_rate': self.passed_tests / self.total_tests * 100,
                    'timestamp': datetime.now().isoformat()
                },
                'test_results': self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")


def main():
    """Main test execution"""
    tester = AuthUtilsNewRoleTest()
    tester.run_all_tests()


if __name__ == "__main__":
    main()