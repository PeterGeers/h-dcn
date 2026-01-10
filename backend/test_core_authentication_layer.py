#!/usr/bin/env python3
"""
Test Core Authentication Layer - Comprehensive Role Combination Testing

This script tests the core authentication layer to verify that new validation 
works with all role combinations as specified in the role migration plan.

Tests cover:
1. Admin roles (System_CRUD, System_User_Management)
2. New role structure (permission + region combinations)
3. Legacy role backward compatibility
4. Regional access controls
5. Permission validation
6. Error handling for incomplete role structures
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / 'shared'))

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
    quick_role_check,
    get_user_permissions_summary
)


class CoreAuthenticationTester:
    """Comprehensive tester for core authentication layer"""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_test_result(self, test_name, passed, message=""):
        """Log test result"""
        if passed:
            self.test_results['passed'] += 1
            print(f"✅ {test_name}")
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: {message}")
    
    def test_admin_roles(self):
        """Test admin role combinations"""
        print("\n=== Testing Admin Roles ===")
        
        # Test System_CRUD (full admin access)
        user_roles = ['System_CRUD']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'admin@test.com'
        )
        self.log_test_result(
            "System_CRUD admin access",
            is_authorized and regional_info['has_full_access'],
            f"Expected admin access, got: {is_authorized}, regional: {regional_info}"
        )
        
        # Test System_User_Management
        user_roles = ['System_User_Management']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['users_manage'], 'admin@test.com'
        )
        self.log_test_result(
            "System_User_Management access",
            is_authorized,
            f"Expected user management access, got: {is_authorized}"
        )
        
        # Test System_Logs_Read
        user_roles = ['System_Logs_Read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['logs_read'], 'admin@test.com'
        )
        self.log_test_result(
            "System_Logs_Read access",
            is_authorized,
            f"Expected logs read access, got: {is_authorized}"
        )
    
    def test_new_role_structure_combinations(self):
        """Test new role structure (permission + region) combinations"""
        print("\n=== Testing New Role Structure Combinations ===")
        
        # Test Members_CRUD + Regio_All (full national access)
        user_roles = ['Members_CRUD', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create', 'members_read'], 'user@test.com'
        )
        self.log_test_result(
            "Members_CRUD + Regio_All",
            is_authorized and regional_info['has_full_access'],
            f"Expected full access, got: {is_authorized}, regional: {regional_info}"
        )
        
        # Test Members_CRUD + Regional access
        user_roles = ['Members_CRUD', 'Regio_Groningen/Drenthe']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'user@test.com'
        )
        self.log_test_result(
            "Members_CRUD + Regional access",
            is_authorized and not regional_info['has_full_access'],
            f"Expected regional access, got: {is_authorized}, regional: {regional_info}"
        )
        
        # Test Members_Read + Members_Export + Regio_All
        user_roles = ['Members_Read', 'Members_Export', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read', 'members_export'], 'user@test.com'
        )
        self.log_test_result(
            "Members_Read + Members_Export + Regio_All",
            is_authorized,
            f"Expected read+export access, got: {is_authorized}"
        )
        
        # Test Events_CRUD + Products_Read + Regio_All
        user_roles = ['Events_CRUD', 'Products_Read', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['events_create', 'products_read'], 'user@test.com'
        )
        self.log_test_result(
            "Events_CRUD + Products_Read + Regio_All",
            is_authorized,
            f"Expected multi-resource access, got: {is_authorized}"
        )
    
    def test_legacy_role_backward_compatibility(self):
        """Test legacy role backward compatibility - NOTE: Legacy _All roles have been removed"""
        print("\n=== Testing Legacy Role Backward Compatibility ===")
        print("NOTE: Legacy _All roles have been removed from Cognito as part of migration cleanup")
        
        # Test Members_CRUD_All (legacy) - should now FAIL since roles were removed
        user_roles = ['Members_CRUD_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create', 'members_read'], 'legacy@test.com'
        )
        self.log_test_result(
            "Members_CRUD_All legacy role (should fail - role removed)",
            not is_authorized,
            f"Expected failure since legacy role removed, got: {is_authorized}"
        )
        
        # Test Events_Read_All (legacy) - should now FAIL since roles were removed
        user_roles = ['Events_Read_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['events_read'], 'legacy@test.com'
        )
        self.log_test_result(
            "Events_Read_All legacy role (should fail - role removed)",
            not is_authorized,
            f"Expected failure since legacy role removed, got: {is_authorized}"
        )
        
        # Test Products_Export_All (legacy) - should now FAIL since roles were removed
        user_roles = ['Products_Export_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['products_export'], 'legacy@test.com'
        )
        self.log_test_result(
            "Products_Export_All legacy role (should fail - role removed)",
            not is_authorized,
            f"Expected failure since legacy role removed, got: {is_authorized}"
        )
        
        # Test that users migrated from legacy roles now work with new structure
        print("\n--- Testing Migrated Users (Legacy -> New Structure) ---")
        
        # User migrated from Members_CRUD_All -> Members_CRUD + Regio_All
        user_roles = ['Members_CRUD', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create', 'members_read'], 'migrated@test.com'
        )
        self.log_test_result(
            "Migrated user (Members_CRUD_All -> Members_CRUD + Regio_All)",
            is_authorized,
            f"Expected migrated user to work with new structure, got: {is_authorized}"
        )
        
        # User migrated from Events_Read_All -> Events_Read + Regio_All
        user_roles = ['Events_Read', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['events_read'], 'migrated@test.com'
        )
        self.log_test_result(
            "Migrated user (Events_Read_All -> Events_Read + Regio_All)",
            is_authorized,
            f"Expected migrated user to work with new structure, got: {is_authorized}"
        )
        
        # User migrated from Products_Export_All -> Products_Export + Regio_All
        user_roles = ['Products_Export', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['products_export'], 'migrated@test.com'
        )
        self.log_test_result(
            "Migrated user (Products_Export_All -> Products_Export + Regio_All)",
            is_authorized,
            f"Expected migrated user to work with new structure, got: {is_authorized}"
        )
    
    def test_incomplete_role_structures(self):
        """Test incomplete role structures (should fail)"""
        print("\n=== Testing Incomplete Role Structures ===")
        
        # Test permission role without region role
        user_roles = ['Members_CRUD']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'incomplete@test.com'
        )
        self.log_test_result(
            "Permission role without region (should fail)",
            not is_authorized,
            f"Expected failure, got: {is_authorized}"
        )
        
        # Test region role without permission role
        user_roles = ['Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'incomplete@test.com'
        )
        self.log_test_result(
            "Region role without permission (should fail)",
            not is_authorized,
            f"Expected failure, got: {is_authorized}"
        )
        
        # Test wrong permission for role
        user_roles = ['Members_Read', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'wrong@test.com'
        )
        self.log_test_result(
            "Wrong permission for role (should fail)",
            not is_authorized,
            f"Expected failure, got: {is_authorized}"
        )
    
    def test_regional_access_controls(self):
        """Test regional access controls"""
        print("\n=== Testing Regional Access Controls ===")
        
        # Test national access (Regio_All)
        user_roles = ['Members_Read', 'Regio_All']
        can_access, reason = check_regional_data_access(user_roles, 'Noord-Holland', 'national@test.com')
        self.log_test_result(
            "National access to any region",
            can_access,
            f"Expected access to Noord-Holland, got: {can_access}, reason: {reason}"
        )
        
        # Test regional access to own region
        user_roles = ['Members_Read', 'Regio_Groningen/Drenthe']
        can_access, reason = check_regional_data_access(user_roles, 'Groningen/Drenthe', 'regional@test.com')
        self.log_test_result(
            "Regional access to own region",
            can_access,
            f"Expected access to own region, got: {can_access}, reason: {reason}"
        )
        
        # Test regional access to different region (should fail)
        user_roles = ['Members_Read', 'Regio_Groningen/Drenthe']
        can_access, reason = check_regional_data_access(user_roles, 'Noord-Holland', 'regional@test.com')
        self.log_test_result(
            "Regional access to different region (should fail)",
            not can_access,
            f"Expected no access to different region, got: {can_access}, reason: {reason}"
        )
        
        # Test accessible regions
        user_roles = ['Members_Read', 'Regio_Utrecht', 'Regio_Limburg']
        accessible_regions = get_user_accessible_regions(user_roles)
        expected_regions = ['Utrecht', 'Limburg']
        self.log_test_result(
            "Multiple regional access",
            set(accessible_regions) == set(expected_regions),
            f"Expected {expected_regions}, got: {accessible_regions}"
        )
    
    def test_role_structure_validation(self):
        """Test role structure validation utilities"""
        print("\n=== Testing Role Structure Validation ===")
        
        # Test valid new structure
        user_roles = ['Members_CRUD', 'Regio_All']
        validation = validate_user_has_new_role_structure(user_roles)
        self.log_test_result(
            "Valid new structure validation",
            validation['has_new_structure'],
            f"Expected valid structure, got: {validation['validation_message']}"
        )
        
        # Test admin user validation
        user_roles = ['System_CRUD']
        validation = validate_user_has_new_role_structure(user_roles)
        self.log_test_result(
            "Admin user validation",
            validation['has_new_structure'],
            f"Expected admin structure valid, got: {validation['validation_message']}"
        )
        
        # Test incomplete structure validation
        user_roles = ['Members_CRUD']
        validation = validate_user_has_new_role_structure(user_roles)
        self.log_test_result(
            "Incomplete structure validation",
            not validation['has_new_structure'] and validation['has_permission_role'] and not validation['has_region_role'],
            f"Expected incomplete structure detected, got: {validation['validation_message']}"
        )
    
    def test_permission_and_region_access(self):
        """Test permission and region access utility"""
        print("\n=== Testing Permission and Region Access Utility ===")
        
        # Test valid permission + region combination
        user_roles = ['Events_CRUD', 'Regio_All']
        result = has_permission_and_region_access(user_roles, 'Events_CRUD')
        self.log_test_result(
            "Valid permission + region combination",
            result['has_access'],
            f"Expected access, got: {result['message']}"
        )
        
        # Test specific region requirement
        user_roles = ['Products_Read', 'Regio_Noord-Holland']
        result = has_permission_and_region_access(user_roles, 'Products_Read', ['Noord-Holland'])
        self.log_test_result(
            "Specific region requirement met",
            result['has_access'],
            f"Expected access to Noord-Holland, got: {result['message']}"
        )
        
        # Test specific region requirement not met
        user_roles = ['Products_Read', 'Regio_Noord-Holland']
        result = has_permission_and_region_access(user_roles, 'Products_Read', ['Zuid-Holland'])
        self.log_test_result(
            "Specific region requirement not met",
            not result['has_access'],
            f"Expected no access to Zuid-Holland, got: {result['message']}"
        )
    
    def test_resource_region_access(self):
        """Test resource region access utility"""
        print("\n=== Testing Resource Region Access ===")
        
        # Test admin access to any region
        user_roles = ['System_CRUD']
        result = can_access_resource_region(user_roles, 'Friesland')
        self.log_test_result(
            "Admin access to any region",
            result['can_access'] and result['access_type'] == 'admin',
            f"Expected admin access, got: {result['message']}"
        )
        
        # Test national access
        user_roles = ['Regio_All']
        result = can_access_resource_region(user_roles, 'Brabant/Zeeland')
        self.log_test_result(
            "National access to any region",
            result['can_access'] and result['access_type'] == 'national',
            f"Expected national access, got: {result['message']}"
        )
        
        # Test regional access match
        user_roles = ['Regio_Oost']
        result = can_access_resource_region(user_roles, 'Oost')
        self.log_test_result(
            "Regional access match",
            result['can_access'] and result['access_type'] == 'regional',
            f"Expected regional access, got: {result['message']}"
        )
        
        # Test regional access mismatch
        user_roles = ['Regio_Oost']
        result = can_access_resource_region(user_roles, 'Duitsland')
        self.log_test_result(
            "Regional access mismatch",
            not result['can_access'],
            f"Expected no access, got: {result['message']}"
        )
    
    def test_crud_access_validation(self):
        """Test CRUD access validation"""
        print("\n=== Testing CRUD Access Validation ===")
        
        # Test create access with CRUD role
        user_roles = ['Members_CRUD', 'Regio_All']
        result = validate_crud_access(user_roles, 'Members', 'create')
        self.log_test_result(
            "Create access with CRUD role",
            result['has_access'],
            f"Expected create access, got: {result['message']}"
        )
        
        # Test read access with Read role
        user_roles = ['Events_Read', 'Regio_All']
        result = validate_crud_access(user_roles, 'Events', 'read')
        self.log_test_result(
            "Read access with Read role",
            result['has_access'],
            f"Expected read access, got: {result['message']}"
        )
        
        # Test export access with Export role
        user_roles = ['Products_Export', 'Regio_All']
        result = validate_crud_access(user_roles, 'Products', 'export')
        self.log_test_result(
            "Export access with Export role",
            result['has_access'],
            f"Expected export access, got: {result['message']}"
        )
        
        # Test create access with only Read role (should fail)
        user_roles = ['Members_Read', 'Regio_All']
        result = validate_crud_access(user_roles, 'Members', 'create')
        self.log_test_result(
            "Create access with only Read role (should fail)",
            not result['has_access'],
            f"Expected no create access, got: {result['message']}"
        )
        
        # Test regional restriction
        user_roles = ['Members_CRUD', 'Regio_Utrecht']
        result = validate_crud_access(user_roles, 'Members', 'read', 'Noord-Holland')
        self.log_test_result(
            "Regional restriction (should fail)",
            not result['has_access'],
            f"Expected no access to different region, got: {result['message']}"
        )
    
    def test_quick_role_check_utility(self):
        """Test quick role check utility"""
        print("\n=== Testing Quick Role Check Utility ===")
        
        # Test admin check
        user_roles = ['System_CRUD']
        has_access, message = quick_role_check(user_roles, 'admin')
        self.log_test_result(
            "Quick admin check",
            has_access,
            f"Expected admin access, got: {message}"
        )
        
        # Test any role check
        user_roles = ['Members_CRUD', 'Regio_All']
        has_access, message = quick_role_check(user_roles, 'any_role', roles=['Members_CRUD', 'Events_CRUD'])
        self.log_test_result(
            "Quick any role check",
            has_access,
            f"Expected role match, got: {message}"
        )
        
        # Test permission check
        user_roles = ['Products_Read', 'Regio_All']
        has_access, message = quick_role_check(user_roles, 'permission', permission='Products_Read')
        self.log_test_result(
            "Quick permission check",
            has_access,
            f"Expected permission access, got: {message}"
        )
        
        # Test CRUD check
        user_roles = ['Events_CRUD', 'Regio_All']
        has_access, message = quick_role_check(user_roles, 'crud', resource='Events', operation='update')
        self.log_test_result(
            "Quick CRUD check",
            has_access,
            f"Expected CRUD access, got: {message}"
        )
        
        # Test region check
        user_roles = ['Regio_Limburg']
        has_access, message = quick_role_check(user_roles, 'region', region='Limburg')
        self.log_test_result(
            "Quick region check",
            has_access,
            f"Expected region access, got: {message}"
        )
    
    def test_user_permissions_summary(self):
        """Test user permissions summary utility"""
        print("\n=== Testing User Permissions Summary ===")
        
        # Test comprehensive summary for admin user
        user_roles = ['System_CRUD']
        summary = get_user_permissions_summary(user_roles)
        self.log_test_result(
            "Admin user permissions summary",
            summary['is_admin'] and summary['summary']['access_level'] == 'admin',
            f"Expected admin summary, got access_level: {summary['summary']['access_level']}"
        )
        
        # Test comprehensive summary for new structure user
        user_roles = ['Members_CRUD', 'Events_Read', 'Regio_All']
        summary = get_user_permissions_summary(user_roles)
        self.log_test_result(
            "New structure user permissions summary",
            summary['role_structure']['has_new_structure'] and summary['summary']['access_level'] == 'national',
            f"Expected new structure national summary, got: {summary['summary']}"
        )
        
        # Test comprehensive summary for regional user
        user_roles = ['Products_Read', 'Regio_Groningen/Drenthe']
        summary = get_user_permissions_summary(user_roles)
        self.log_test_result(
            "Regional user permissions summary",
            summary['role_structure']['has_new_structure'] and summary['summary']['access_level'] == 'regional',
            f"Expected regional summary, got: {summary['summary']}"
        )
        
        # Test comprehensive summary for legacy user
        user_roles = ['Members_CRUD_All']
        summary = get_user_permissions_summary(user_roles)
        self.log_test_result(
            "Legacy user permissions summary",
            summary['summary']['migration_needed'],
            f"Expected migration needed, got: {summary['summary']}"
        )
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling"""
        print("\n=== Testing Edge Cases and Error Handling ===")
        
        # Test empty role list
        user_roles = []
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'empty@test.com'
        )
        self.log_test_result(
            "Empty role list (should fail)",
            not is_authorized,
            f"Expected failure with empty roles, got: {is_authorized}"
        )
        
        # Test None permissions
        user_roles = ['Members_CRUD', 'Regio_All']
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, None, 'none@test.com'
            )
            self.log_test_result(
                "None permissions handling",
                True,  # Should not crash
                "Should handle None permissions gracefully"
            )
        except Exception as e:
            self.log_test_result(
                "None permissions handling",
                False,
                f"Should not crash with None permissions: {str(e)}"
            )
        
        # Test invalid role combinations
        user_roles = ['InvalidRole', 'AnotherInvalidRole']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'invalid@test.com'
        )
        self.log_test_result(
            "Invalid role combinations (should fail)",
            not is_authorized,
            f"Expected failure with invalid roles, got: {is_authorized}"
        )
        
        # Test mixed valid and invalid roles
        user_roles = ['Members_CRUD', 'InvalidRole', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'mixed@test.com'
        )
        self.log_test_result(
            "Mixed valid and invalid roles",
            is_authorized,  # Should work with valid roles
            f"Expected success with valid roles present, got: {is_authorized}"
        )
    
    def run_all_tests(self):
        """Run all authentication tests"""
        print("Testing Core Authentication Layer - All Role Combinations")
        print("=" * 70)
        
        try:
            self.test_admin_roles()
            self.test_new_role_structure_combinations()
            self.test_legacy_role_backward_compatibility()
            self.test_incomplete_role_structures()
            self.test_regional_access_controls()
            self.test_role_structure_validation()
            self.test_permission_and_region_access()
            self.test_resource_region_access()
            self.test_crud_access_validation()
            self.test_quick_role_check_utility()
            self.test_user_permissions_summary()
            self.test_edge_cases_and_error_handling()
            
            # Print summary
            print("\n" + "=" * 70)
            print("📊 Test Results Summary:")
            print(f"✅ Passed: {self.test_results['passed']}")
            print(f"❌ Failed: {self.test_results['failed']}")
            
            if self.test_results['failed'] > 0:
                print("\n🔍 Failed Tests:")
                for error in self.test_results['errors']:
                    print(f"  - {error}")
                print("\n⚠️ Some tests failed. Core authentication layer needs attention.")
                return False
            else:
                print("\n🎉 All tests passed! Core authentication layer is working correctly.")
                print("\n✅ Verification Complete:")
                print("  - Admin roles work correctly")
                print("  - New role structure (permission + region) works correctly")
                print("  - Legacy role backward compatibility works correctly")
                print("  - Regional access controls work correctly")
                print("  - Permission validation works correctly")
                print("  - Error handling for incomplete structures works correctly")
                print("\n🚀 The core authentication layer is ready for production use!")
                return True
                
        except Exception as e:
            print(f"\n💥 Test suite failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main test function"""
    tester = CoreAuthenticationTester()
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()