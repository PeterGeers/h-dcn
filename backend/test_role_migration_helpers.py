#!/usr/bin/env python3
"""
Test script for role migration helper functions
This script tests the new migration helper functions in auth_utils.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from auth_utils import (
    convert_legacy_role_to_new_structure,
    convert_legacy_role_list_to_new_structure,
    get_equivalent_new_roles_for_legacy_check,
    validate_permissions_with_legacy_fallback,
    create_backward_compatible_role_check,
    generate_migration_report_for_handler,
    validate_user_has_new_role_structure
)


def test_convert_legacy_role_to_new_structure():
    """Test converting single legacy roles"""
    print("=== Testing convert_legacy_role_to_new_structure ===")
    
    # Test legacy role conversion - FOR MIGRATION TESTING ONLY
    # These roles have been removed from production
    result = convert_legacy_role_to_new_structure('Members_CRUD_All')  # DEPRECATED ROLE - TEST ONLY
    print(f"Members_CRUD_All -> {result}")  # DEPRECATED ROLE - TEST ONLY
    assert result['permission_role'] == 'Members_CRUD'
    assert result['region_role'] == 'Regio_All'
    assert result['is_legacy'] == True
    
    # Test non-legacy role
    result = convert_legacy_role_to_new_structure('Members_CRUD')
    print(f"Members_CRUD -> {result}")
    assert result['is_legacy'] == False
    
    # Test region role
    result = convert_legacy_role_to_new_structure('Regio_Groningen/Drenthe')
    print(f"Regio_Groningen/Drenthe -> {result}")
    assert result['region_role'] == 'Regio_Groningen/Drenthe'
    assert result['permission_role'] is None
    
    print("✅ convert_legacy_role_to_new_structure tests passed\n")


def test_convert_legacy_role_list_to_new_structure():
    """Test converting role lists"""
    print("=== Testing convert_legacy_role_list_to_new_structure ===")
    
    # Test mixed role list
    user_roles = ['Members_CRUD_All', 'Events_Read_All', 'hdcnAdmins', 'Regio_Noord-Holland']
    result = convert_legacy_role_list_to_new_structure(user_roles)
    print(f"Input: {user_roles}")
    print(f"Output: {result}")
    
    assert 'Members_CRUD' in result['new_roles']
    assert 'Regio_All' in result['new_roles']
    assert 'Events_Read' in result['new_roles']
    assert 'Events_Export' in result['new_roles']  # Legacy read included export
    assert 'hdcnAdmins' in result['new_roles']
    assert 'Regio_Noord-Holland' in result['new_roles']
    assert len(result['legacy_roles_found']) == 2
    
    print("✅ convert_legacy_role_list_to_new_structure tests passed\n")


def test_get_equivalent_new_roles_for_legacy_check():
    """Test getting equivalent new roles for legacy checks"""
    print("=== Testing get_equivalent_new_roles_for_legacy_check ===")
    
    legacy_roles = ['Members_CRUD_All', 'Products_Read_All']
    result = get_equivalent_new_roles_for_legacy_check(legacy_roles)
    print(f"Input: {legacy_roles}")
    print(f"Output: {result}")
    
    assert len(result['new_role_combinations']) == 2
    assert ['Members_CRUD', 'Regio_All'] in result['new_role_combinations']
    assert 'members_create' in result['permission_requirements']
    assert 'products_read' in result['permission_requirements']
    
    print("✅ get_equivalent_new_roles_for_legacy_check tests passed\n")


def test_create_backward_compatible_role_check():
    """Test backward compatible role checker"""
    print("=== Testing create_backward_compatible_role_check ===")
    
    # Create checker for legacy roles
    legacy_roles = ['Members_CRUD_All']
    role_checker = create_backward_compatible_role_check(legacy_roles)
    
    # Test with legacy role
    user_roles = ['Members_CRUD_All', 'Other_Role']
    has_access, details = role_checker(user_roles)
    print(f"Legacy role test: {has_access}, {details}")
    assert has_access == True
    assert details['access_type'] == 'legacy'
    
    # Test with new structure
    user_roles = ['Members_CRUD', 'Regio_All']
    has_access, details = role_checker(user_roles)
    print(f"New structure test: {has_access}, {details}")
    assert has_access == True
    assert details['access_type'] == 'new_structure'
    
    # Test with admin role
    user_roles = ['hdcnAdmins']
    has_access, details = role_checker(user_roles)
    print(f"Admin role test: {has_access}, {details}")
    assert has_access == True
    assert details['access_type'] == 'admin'
    
    # Test with no access
    user_roles = ['Some_Other_Role']
    has_access, details = role_checker(user_roles)
    print(f"No access test: {has_access}, {details}")
    assert has_access == False
    assert details['access_type'] == 'denied'
    
    print("✅ create_backward_compatible_role_check tests passed\n")


def test_validate_user_has_new_role_structure():
    """Test new role structure validation"""
    print("=== Testing validate_user_has_new_role_structure ===")
    
    # Test valid new structure
    user_roles = ['Members_CRUD', 'Regio_All']
    result = validate_user_has_new_role_structure(user_roles)
    print(f"Valid new structure: {result}")
    assert result['has_new_structure'] == True
    assert result['has_permission_role'] == True
    assert result['has_region_role'] == True
    
    # Test admin user
    user_roles = ['hdcnAdmins']
    result = validate_user_has_new_role_structure(user_roles)
    print(f"Admin user: {result}")
    assert result['has_new_structure'] == True
    
    # Test missing region role
    user_roles = ['Members_CRUD']
    result = validate_user_has_new_role_structure(user_roles)
    print(f"Missing region: {result}")
    assert result['has_new_structure'] == False
    assert result['has_permission_role'] == True
    assert result['has_region_role'] == False
    
    # Test legacy roles
    user_roles = ['Members_CRUD_All']
    result = validate_user_has_new_role_structure(user_roles)
    print(f"Legacy roles: {result}")
    assert len(result['legacy_roles']) == 1
    
    print("✅ validate_user_has_new_role_structure tests passed\n")


def test_generate_migration_report_for_handler():
    """Test migration report generation"""
    print("=== Testing generate_migration_report_for_handler ===")
    
    # Test handler with legacy roles
    current_roles = ['Members_CRUD_All', 'Products_CRUD_All', 'hdcnAdmins']
    report = generate_migration_report_for_handler('update_member', current_roles)
    print(f"Migration report: {report}")
    
    assert report['migration_needed'] == True
    assert len(report['new_role_structure']) > 0
    assert 'Replace legacy role checks' in report['recommendations'][0]
    assert report['backward_compatibility_code'] is not None
    
    # Test handler with no legacy roles
    current_roles = ['hdcnAdmins']
    report = generate_migration_report_for_handler('admin_handler', current_roles)
    print(f"No migration needed: {report}")
    
    assert report['migration_needed'] == False
    
    print("✅ generate_migration_report_for_handler tests passed\n")


def main():
    """Run all tests"""
    print("🧪 Testing Role Migration Helper Functions\n")
    
    try:
        test_convert_legacy_role_to_new_structure()
        test_convert_legacy_role_list_to_new_structure()
        test_get_equivalent_new_roles_for_legacy_check()
        test_create_backward_compatible_role_check()
        test_validate_user_has_new_role_structure()
        test_generate_migration_report_for_handler()
        
        print("🎉 All tests passed! Role migration helper functions are working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()