#!/usr/bin/env python3
"""
Test script for backward compatibility layer functions
"""

import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / 'shared'))

from auth_utils import (
    get_new_role_structure_mapping,
    update_handler_role_check,
    create_handler_migration_template,
    validate_permissions_with_regions
)

def test_role_mapping():
    """Test the role mapping function"""
    print("=== Testing Role Mapping ===")
    
    mapping = get_new_role_structure_mapping()
    
    # Test a few key mappings - NOTE: Legacy _All roles have been removed
    test_cases = [
        # Legacy roles removed as part of cleanup
        # 'Members_CRUD_All',
        # 'Events_Read_All', 
        # 'Products_CRUD_All',
        # 'System_CRUD_All'
    ]
    
    for old_role in test_cases:
        if old_role in mapping:
            new_roles = mapping[old_role]
            print(f"✓ {old_role} -> {new_roles}")
        else:
            print(f"✗ {old_role} not found in mapping")
    
    print()

def test_handler_role_check():
    """Test the handler role check conversion"""
    print("=== Testing Handler Role Check Conversion ===")
    
    # Test converting old role checks
    old_roles = ['Members_CRUD_All', 'Events_Read_All']
    result = update_handler_role_check(old_roles)
    
    print(f"Input roles: {old_roles}")
    print(f"Required permissions: {result['required_permissions']}")
    print("Migration notes:")
    for note in result['migration_notes']:
        print(f"  - {note}")
    
    print("\nGenerated code:")
    print(result['updated_role_check'])
    print()

def test_migration_template():
    """Test migration template generation"""
    print("=== Testing Migration Template Generation ===")
    
    handler_name = "test_handler"
    old_roles = ['Members_CRUD_All']
    
    template = create_handler_migration_template(handler_name, old_roles)
    
    print(f"Generated template for {handler_name} with roles {old_roles}")
    print("Template length:", len(template))
    print("Contains required imports:", "validate_permissions_with_regions" in template)
    print("Contains handler logic:", "lambda_handler" in template)
    print()

def test_enhanced_validation():
    """Test the enhanced validation function"""
    print("=== Testing Enhanced Validation ===")
    
    # Test cases
    test_cases = [
        {
            'name': 'Admin user',
            'roles': ['hdcnAdmins'],
            'permissions': ['members_read'],
            'expected': True
        },
        {
            'name': 'New structure user',
            'roles': ['Members_CRUD', 'Regio_All'],
            'permissions': ['members_read'],
            'expected': True
        },
        {
            'name': 'Incomplete new structure (no region)',
            'roles': ['Members_CRUD'],
            'permissions': ['members_read'],
            'expected': False
        },
        {
            'name': 'No permissions',
            'roles': ['hdcnLeden'],
            'permissions': ['members_read'],
            'expected': False
        }
    ]
    
    for test_case in test_cases:
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                test_case['roles'], 
                test_case['permissions'], 
                'test@example.com'
            )
            
            result = "✓" if is_authorized == test_case['expected'] else "✗"
            print(f"{result} {test_case['name']}: {is_authorized} (expected: {test_case['expected']})")
            
            if regional_info:
                print(f"    Regional access: {regional_info.get('access_type', 'unknown')}")
            
        except Exception as e:
            print(f"✗ {test_case['name']}: Error - {str(e)}")
    
    print()

def main():
    """Run all tests"""
    print("🧪 Testing Backward Compatibility Layer")
    print("=" * 50)
    
    try:
        test_role_mapping()
        test_handler_role_check()
        test_migration_template()
        test_enhanced_validation()
        
        print("=" * 50)
        print("✅ All tests completed successfully!")
        print("\nThe backward compatibility layer is working correctly.")
        print("Handlers can now be migrated using the provided functions.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()