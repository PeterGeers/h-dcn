#!/usr/bin/env python3
"""
Test Role-to-Permission Mappings - Verify All Mappings Work Correctly

This script specifically tests the role_permissions mapping defined in auth_utils.py
to ensure all role-to-permission mappings work correctly as required by the task.

Tests cover:
1. All permission roles and their mapped permissions
2. All region roles (should have no permissions by themselves)
3. Admin roles and their permissions
4. Organizational roles and their permissions
5. Special roles (hdcnLeden, Webshop_Management, etc.)
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / 'shared'))

from auth_utils import validate_permissions


class RolePermissionMappingTester:
    """Test all role-to-permission mappings"""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Define the expected role-to-permission mappings from auth_utils.py
        self.expected_mappings = {
            # Administrative roles
            'System_CRUD': ['*'],  # Full system access
            'System_User_Management': ['users_manage', 'roles_assign'],
            'System_Logs_Read': ['logs_read', 'audit_read'],
            
            # Permission roles (what you can do)
            'Members_CRUD': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
            'Members_Read': ['members_read', 'members_list'],
            'Members_Export': ['members_export'],
            'Events_CRUD': ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export'],
            'Events_Read': ['events_read', 'events_list'],
            'Events_Export': ['events_export'],
            'Products_CRUD': ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export'],
            'Products_Read': ['products_read', 'products_list'],
            'Products_Export': ['products_export'],
            'Communication_CRUD': ['communication_create', 'communication_read', 'communication_update', 'communication_delete'],
            'Communication_Read': ['communication_read'],
            'Communication_Export': ['communication_export'],
            
            # Region roles (where you can access) - these don't grant permissions by themselves
            'Regio_All': [],
            'Regio_Noord-Holland': [],
            'Regio_Zuid-Holland': [],
            'Regio_Friesland': [],
            'Regio_Utrecht': [],
            'Regio_Oost': [],
            'Regio_Limburg': [],
            'Regio_Groningen/Drenthe': [],
            'Regio_Brabant/Zeeland': [],
            'Regio_Duitsland': [],
            
            # Other roles
            'Members_Status_Approve': ['members_status_change'],
            'Webshop_Management': ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage'],
            
            # Organizational roles
            'National_Chairman': ['members_read', 'events_read', 'communication_read', 'reports_read'],
            'National_Secretary': ['members_read', 'events_read', 'communication_create', 'communication_read'],
            'National_Treasurer': ['members_read', 'payments_read', 'financial_reports'],
            
            # Basic member
            'hdcnLeden': ['profile_read', 'profile_update_own', 'events_read', 'products_read']
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
    
    def test_individual_role_permissions(self):
        """Test each role individually to verify its permissions"""
        print("\n=== Testing Individual Role-to-Permission Mappings ===")
        
        for role, expected_permissions in self.expected_mappings.items():
            if expected_permissions == ['*']:
                # Test admin role with wildcard permissions
                is_authorized, error_response = validate_permissions(
                    [role], ['any_permission_should_work'], f'{role.lower()}@test.com'
                )
                self.log_test_result(
                    f"{role} (admin wildcard access)",
                    is_authorized,
                    f"Expected wildcard access, got: {is_authorized}"
                )
            elif expected_permissions == []:
                # Test region roles (should have no permissions by themselves)
                is_authorized, error_response = validate_permissions(
                    [role], ['members_read'], f'{role.lower()}@test.com'
                )
                self.log_test_result(
                    f"{role} (region role - no permissions)",
                    not is_authorized,
                    f"Expected no permissions for region role, got: {is_authorized}"
                )
            else:
                # Test permission roles with their specific permissions
                for permission in expected_permissions:
                    is_authorized, error_response = validate_permissions(
                        [role], [permission], f'{role.lower()}@test.com'
                    )
                    self.log_test_result(
                        f"{role} -> {permission}",
                        is_authorized,
                        f"Expected access to {permission}, got: {is_authorized}"
                    )
    
    def test_permission_role_combinations(self):
        """Test that permission roles work correctly in combinations"""
        print("\n=== Testing Permission Role Combinations ===")
        
        # Test Members_CRUD includes all member permissions
        user_roles = ['Members_CRUD']
        member_permissions = ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export']
        
        for permission in member_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'crud_user@test.com'
            )
            self.log_test_result(
                f"Members_CRUD includes {permission}",
                is_authorized,
                f"Expected CRUD to include {permission}, got: {is_authorized}"
            )
        
        # Test Events_CRUD includes all event permissions
        user_roles = ['Events_CRUD']
        event_permissions = ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export']
        
        for permission in event_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'events_crud@test.com'
            )
            self.log_test_result(
                f"Events_CRUD includes {permission}",
                is_authorized,
                f"Expected Events_CRUD to include {permission}, got: {is_authorized}"
            )
        
        # Test Products_CRUD includes all product permissions
        user_roles = ['Products_CRUD']
        product_permissions = ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export']
        
        for permission in product_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'products_crud@test.com'
            )
            self.log_test_result(
                f"Products_CRUD includes {permission}",
                is_authorized,
                f"Expected Products_CRUD to include {permission}, got: {is_authorized}"
            )
    
    def test_read_only_roles(self):
        """Test that read-only roles don't grant write permissions"""
        print("\n=== Testing Read-Only Role Restrictions ===")
        
        # Test Members_Read doesn't grant create/update/delete
        user_roles = ['Members_Read']
        forbidden_permissions = ['members_create', 'members_update', 'members_delete']
        
        for permission in forbidden_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'read_only@test.com'
            )
            self.log_test_result(
                f"Members_Read should NOT grant {permission}",
                not is_authorized,
                f"Expected no access to {permission}, got: {is_authorized}"
            )
        
        # Test Events_Read doesn't grant create/update/delete
        user_roles = ['Events_Read']
        forbidden_permissions = ['events_create', 'events_update', 'events_delete']
        
        for permission in forbidden_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'events_read@test.com'
            )
            self.log_test_result(
                f"Events_Read should NOT grant {permission}",
                not is_authorized,
                f"Expected no access to {permission}, got: {is_authorized}"
            )
        
        # Test Products_Read doesn't grant create/update/delete
        user_roles = ['Products_Read']
        forbidden_permissions = ['products_create', 'products_update', 'products_delete']
        
        for permission in forbidden_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'products_read@test.com'
            )
            self.log_test_result(
                f"Products_Read should NOT grant {permission}",
                not is_authorized,
                f"Expected no access to {permission}, got: {is_authorized}"
            )
    
    def test_export_only_roles(self):
        """Test that export-only roles only grant export permissions"""
        print("\n=== Testing Export-Only Role Restrictions ===")
        
        # Test Members_Export only grants export, not CRUD
        user_roles = ['Members_Export']
        
        # Should grant export
        is_authorized, error_response = validate_permissions(
            user_roles, ['members_export'], 'export_user@test.com'
        )
        self.log_test_result(
            "Members_Export grants members_export",
            is_authorized,
            f"Expected export access, got: {is_authorized}"
        )
        
        # Should NOT grant CRUD
        forbidden_permissions = ['members_create', 'members_read', 'members_update', 'members_delete']
        for permission in forbidden_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'export_user@test.com'
            )
            self.log_test_result(
                f"Members_Export should NOT grant {permission}",
                not is_authorized,
                f"Expected no access to {permission}, got: {is_authorized}"
            )
    
    def test_organizational_roles(self):
        """Test organizational role permissions"""
        print("\n=== Testing Organizational Role Permissions ===")
        
        # Test National_Chairman permissions
        user_roles = ['National_Chairman']
        expected_permissions = ['members_read', 'events_read', 'communication_read', 'reports_read']
        
        for permission in expected_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'chairman@test.com'
            )
            self.log_test_result(
                f"National_Chairman -> {permission}",
                is_authorized,
                f"Expected chairman access to {permission}, got: {is_authorized}"
            )
        
        # Test National_Secretary permissions
        user_roles = ['National_Secretary']
        expected_permissions = ['members_read', 'events_read', 'communication_create', 'communication_read']
        
        for permission in expected_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'secretary@test.com'
            )
            self.log_test_result(
                f"National_Secretary -> {permission}",
                is_authorized,
                f"Expected secretary access to {permission}, got: {is_authorized}"
            )
        
        # Test National_Treasurer permissions
        user_roles = ['National_Treasurer']
        expected_permissions = ['members_read', 'payments_read', 'financial_reports']
        
        for permission in expected_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'treasurer@test.com'
            )
            self.log_test_result(
                f"National_Treasurer -> {permission}",
                is_authorized,
                f"Expected treasurer access to {permission}, got: {is_authorized}"
            )
    
    def test_special_roles(self):
        """Test special role permissions"""
        print("\n=== Testing Special Role Permissions ===")
        
        # Test hdcnLeden (basic member) permissions
        user_roles = ['hdcnLeden']
        expected_permissions = ['profile_read', 'profile_update_own', 'events_read', 'products_read']
        
        for permission in expected_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'member@test.com'
            )
            self.log_test_result(
                f"hdcnLeden -> {permission}",
                is_authorized,
                f"Expected basic member access to {permission}, got: {is_authorized}"
            )
        
        # Test Webshop_Management permissions
        user_roles = ['Webshop_Management']
        expected_permissions = ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage']
        
        for permission in expected_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'webshop@test.com'
            )
            self.log_test_result(
                f"Webshop_Management -> {permission}",
                is_authorized,
                f"Expected webshop access to {permission}, got: {is_authorized}"
            )
        
        # Test Members_Status_Approve permission
        user_roles = ['Members_Status_Approve']
        is_authorized, error_response = validate_permissions(
            user_roles, ['members_status_change'], 'approver@test.com'
        )
        self.log_test_result(
            "Members_Status_Approve -> members_status_change",
            is_authorized,
            f"Expected status approval access, got: {is_authorized}"
        )
    
    def test_multiple_role_combinations(self):
        """Test that multiple roles combine permissions correctly"""
        print("\n=== Testing Multiple Role Combinations ===")
        
        # Test Members_Read + Members_Export combination
        user_roles = ['Members_Read', 'Members_Export']
        combined_permissions = ['members_read', 'members_list', 'members_export']
        
        for permission in combined_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'combined@test.com'
            )
            self.log_test_result(
                f"Members_Read + Members_Export -> {permission}",
                is_authorized,
                f"Expected combined access to {permission}, got: {is_authorized}"
            )
        
        # Test Events_Read + Products_Read combination
        user_roles = ['Events_Read', 'Products_Read']
        combined_permissions = ['events_read', 'events_list', 'products_read', 'products_list']
        
        for permission in combined_permissions:
            is_authorized, error_response = validate_permissions(
                user_roles, [permission], 'multi_read@test.com'
            )
            self.log_test_result(
                f"Events_Read + Products_Read -> {permission}",
                is_authorized,
                f"Expected multi-resource read access to {permission}, got: {is_authorized}"
            )
    
    def test_invalid_role_mappings(self):
        """Test that invalid roles don't grant any permissions"""
        print("\n=== Testing Invalid Role Mappings ===")
        
        # Test completely invalid role
        user_roles = ['InvalidRole']
        is_authorized, error_response = validate_permissions(
            user_roles, ['members_read'], 'invalid@test.com'
        )
        self.log_test_result(
            "Invalid role grants no permissions",
            not is_authorized,
            f"Expected no access with invalid role, got: {is_authorized}"
        )
        
        # Test removed legacy role
        user_roles = ['Members_CRUD_All']
        is_authorized, error_response = validate_permissions(
            user_roles, ['members_read'], 'legacy@test.com'
        )
        self.log_test_result(
            "Removed legacy role grants no permissions",
            not is_authorized,
            f"Expected no access with removed legacy role, got: {is_authorized}"
        )
    
    def run_all_tests(self):
        """Run all role-to-permission mapping tests"""
        print("Testing Role-to-Permission Mappings - Comprehensive Verification")
        print("=" * 80)
        
        try:
            self.test_individual_role_permissions()
            self.test_permission_role_combinations()
            self.test_read_only_roles()
            self.test_export_only_roles()
            self.test_organizational_roles()
            self.test_special_roles()
            self.test_multiple_role_combinations()
            self.test_invalid_role_mappings()
            
            # Print summary
            print("\n" + "=" * 80)
            print("📊 Role-to-Permission Mapping Test Results:")
            print(f"✅ Passed: {self.test_results['passed']}")
            print(f"❌ Failed: {self.test_results['failed']}")
            
            if self.test_results['failed'] > 0:
                print("\n🔍 Failed Tests:")
                for error in self.test_results['errors']:
                    print(f"  - {error}")
                print("\n⚠️ Some role mappings failed. Authentication system needs attention.")
                return False
            else:
                print("\n🎉 All role-to-permission mappings work correctly!")
                print("\n✅ Verification Complete:")
                print("  - All permission roles map to correct permissions")
                print("  - All region roles correctly have no permissions by themselves")
                print("  - All admin roles work correctly")
                print("  - All organizational roles work correctly")
                print("  - All special roles work correctly")
                print("  - Multiple role combinations work correctly")
                print("  - Invalid roles correctly grant no permissions")
                print("\n🚀 Role-to-permission mappings are ready for production use!")
                return True
                
        except Exception as e:
            print(f"\n💥 Role mapping test suite failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main test function"""
    tester = RolePermissionMappingTester()
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()