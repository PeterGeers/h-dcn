#!/usr/bin/env python3
"""
Test script for streamlined authentication logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from auth_utils import validate_permissions_with_regions, determine_regional_access

def test_streamlined_authentication():
    """Test streamlined authentication with new role structure"""
    
    test_cases = [
        {
            'name': 'System Admin',
            'roles': ['System_CRUD'],
            'permissions': ['members_read'],
            'expected': True
        },
        {
            'name': 'National Member Admin',
            'roles': ['Members_CRUD', 'Regio_All'],
            'permissions': ['members_read'],
            'expected': True
        },
        {
            'name': 'Regional Member Admin',
            'roles': ['Members_CRUD', 'Regio_Utrecht'],
            'permissions': ['members_read'],
            'expected': True
        },
        {
            'name': 'Missing Region',
            'roles': ['Members_CRUD'],
            'permissions': ['members_read'],
            'expected': False
        },
        {
            'name': 'Missing Permission',
            'roles': ['Regio_All'],
            'permissions': ['members_read'],
            'expected': False
        }
    ]

    print('🧪 Testing Streamlined Authentication Logic')
    print('=' * 50)

    all_passed = True
    for test in test_cases:
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            test['roles'], test['permissions'], 'test@hdcn.nl'
        )
        
        success = is_authorized == test['expected']
        status = '✅' if success else '❌'
        
        print(f'{status} {test["name"]}: {"PASS" if success else "FAIL"}')
        if not success:
            print(f'   Expected: {test["expected"]}, Got: {is_authorized}')
            all_passed = False
        elif regional_info:
            print(f'   Regional Access: {regional_info["access_type"]} - {regional_info["allowed_regions"]}')

    return all_passed

def test_regional_access():
    """Test regional access determination"""
    
    print('\n🎯 Testing Regional Access Determination')
    print('=' * 50)

    regional_tests = [
        (['System_CRUD'], 'admin'),
        (['Members_CRUD', 'Regio_All'], 'national'),
        (['Members_CRUD', 'Regio_Utrecht'], 'regional'),
        (['Members_CRUD'], 'none')
    ]

    all_passed = True
    for roles, expected_type in regional_tests:
        regional_info = determine_regional_access(roles)
        success = regional_info['access_type'] == expected_type
        status = '✅' if success else '❌'
        print(f'{status} {roles} -> {regional_info["access_type"]} ({"PASS" if success else "FAIL"})')
        if not success:
            all_passed = False

    return all_passed

def main():
    """Run all tests"""
    print('🚀 Testing Streamlined Authentication Optimizations')
    print('=' * 60)
    
    auth_passed = test_streamlined_authentication()
    regional_passed = test_regional_access()
    
    print('\n📊 Test Results Summary')
    print('=' * 30)
    
    if auth_passed and regional_passed:
        print('✅ All tests PASSED - Streamlined authentication is working correctly!')
        print('🎯 Authentication logic has been successfully optimized for new role structure only')
        return True
    else:
        print('❌ Some tests FAILED - Check the implementation')
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)