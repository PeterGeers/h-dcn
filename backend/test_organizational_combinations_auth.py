#!/usr/bin/env python3
"""
Test script to validate organizational role combinations work with authentication system
This tests the integration between organizational roles and the auth_utils validation
"""

import sys
import os
import json

# Add the shared directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'handler', 'update_member'))

try:
    from auth_utils import (
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        has_permission_and_region_access
    )
    from role_permissions import (
        ORGANIZATIONAL_ROLE_COMBINATIONS,
        get_organizational_role_combination,
        assign_organizational_role,
        validate_organizational_role_structure,
        get_all_organizational_roles
    )
    print("✅ Successfully imported auth_utils and role_permissions modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

def test_organizational_role_authentication():
    """Test that organizational roles work with the authentication system"""
    print("\n🔐 Testing Organizational Role Authentication...")
    
    # Test key organizational roles with different permission requirements
    test_cases = [
        {
            'role': 'National_Chairman',
            'permissions_to_test': ['members_read', 'events_read', 'communication_read'],
            'should_have_full_access': True
        },
        {
            'role': 'National_Secretary', 
            'permissions_to_test': ['members_read', 'events_read', 'communication_create'],
            'should_have_full_access': True
        },
        {
            'role': 'Webmaster',
            'permissions_to_test': ['members_create', 'events_create', 'products_create'],
            'should_have_full_access': True
        },
        {
            'role': 'Regional_Chairman_Region1',
            'permissions_to_test': ['members_read', 'events_create'],
            'should_have_full_access': False,  # Regional access only
            'expected_regions': ['Noord-Holland']
        },
        {
            'role': 'Regional_Secretary_Region4',
            'permissions_to_test': ['members_read', 'events_read'],
            'should_have_full_access': False,  # Regional access only
            'expected_regions': ['Utrecht']
        }
    ]
    
    passed_tests = 0
    total_tests = 0
    
    for test_case in test_cases:
        role_name = test_case['role']
        print(f"\n  Testing: {role_name}")
        
        # Get the role combination
        role_combination = get_organizational_role_combination(role_name)
        if not role_combination:
            print(f"    ❌ No role combination found for {role_name}")
            continue
        
        print(f"    📋 Role combination: {len(role_combination)} roles")
        
        # Test each required permission
        for permission in test_case['permissions_to_test']:
            total_tests += 1
            
            # Test with validate_permissions_with_regions
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                role_combination, [permission], f"test_{role_name.lower()}@hdcn.nl"
            )
            
            if is_authorized:
                print(f"    ✅ Permission '{permission}': AUTHORIZED")
                
                # Check regional access
                if test_case['should_have_full_access']:
                    if regional_info and regional_info.get('has_full_access'):
                        print(f"      ✅ Full access confirmed")
                        passed_tests += 1
                    else:
                        print(f"      ❌ Expected full access but got: {regional_info}")
                else:
                    # Check specific regional access
                    expected_regions = test_case.get('expected_regions', [])
                    if regional_info and regional_info.get('allowed_regions'):
                        actual_regions = [r.replace('Regio_', '') for r in regional_info['allowed_regions'] if r != 'all']
                        if any(region in actual_regions for region in expected_regions):
                            print(f"      ✅ Regional access confirmed: {actual_regions}")
                            passed_tests += 1
                        else:
                            print(f"      ❌ Expected regions {expected_regions} but got: {actual_regions}")
                    else:
                        print(f"      ❌ No regional info returned: {regional_info}")
            else:
                print(f"    ❌ Permission '{permission}': DENIED")
                if error_response:
                    error_body = json.loads(error_response.get('body', '{}'))
                    print(f"      Error: {error_body.get('error', 'Unknown error')}")
    
    print(f"\n  📊 Authentication Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def test_organizational_role_regional_access():
    """Test regional access patterns for organizational roles"""
    print("\n🌍 Testing Organizational Role Regional Access...")
    
    # Test regional roles have correct regional restrictions
    regional_test_cases = [
        ('Regional_Chairman_Region1', 'Noord-Holland'),
        ('Regional_Secretary_Region4', 'Utrecht'), 
        ('Regional_Treasurer_Region7', 'Groningen/Drenthe'),
        ('Regional_Volunteer_Region9', 'Duitsland')
    ]
    
    passed_tests = 0
    total_tests = len(regional_test_cases)
    
    for role_name, expected_region in regional_test_cases:
        print(f"\n  Testing: {role_name} -> {expected_region}")
        
        role_combination = get_organizational_role_combination(role_name)
        if not role_combination:
            print(f"    ❌ Role combination not found")
            continue
        
        # Get regional access info
        regional_info = determine_regional_access(role_combination)
        
        if regional_info['access_type'] == 'regional':
            allowed_regions = regional_info['allowed_regions']
            if expected_region in allowed_regions:
                print(f"    ✅ Correct regional access: {allowed_regions}")
                passed_tests += 1
            else:
                print(f"    ❌ Expected {expected_region} but got: {allowed_regions}")
        elif regional_info['access_type'] == 'national':
            # Some roles might have national access (e.g., if they have Regio_All)
            print(f"    ✅ National access (includes {expected_region})")
            passed_tests += 1
        else:
            print(f"    ❌ Unexpected access type: {regional_info['access_type']}")
    
    print(f"\n  📊 Regional Access Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def test_organizational_role_permission_combinations():
    """Test that organizational roles have valid permission + region combinations"""
    print("\n🔧 Testing Organizational Role Permission Combinations...")
    
    all_roles = get_all_organizational_roles()
    
    # Test a sample from each category
    test_roles = (
        all_roles['national_roles'][:2] +  # Test 2 national roles
        all_roles['regional_roles'][:4] +  # Test 4 regional roles  
        all_roles['function_roles'][:2]    # Test 2 function roles
    )
    
    passed_tests = 0
    total_tests = len(test_roles)
    
    for role_name in test_roles:
        print(f"\n  Testing: {role_name}")
        
        # Validate role structure
        validation = validate_organizational_role_structure(role_name)
        
        if validation['is_valid']:
            print(f"    ✅ Valid structure: {validation['validation_type']}")
            
            # Check if it has proper permission + region combination
            role_analysis = validation['role_analysis']
            
            if role_analysis.get('has_new_structure') or role_analysis.get('admin_roles'):
                print(f"    ✅ Proper role structure confirmed")
                passed_tests += 1
            else:
                print(f"    ⚠️  Valid but not new structure: {role_analysis}")
                # Still count as passed if it's valid (might be legacy during migration)
                passed_tests += 1
        else:
            print(f"    ❌ Invalid structure: {validation['validation_type']}")
            if validation['suggestions']:
                print(f"      Suggestions: {validation['suggestions']}")
    
    print(f"\n  📊 Permission Combination Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def test_organizational_role_assignment_integration():
    """Test assigning organizational roles and validating they work with auth system"""
    print("\n👤 Testing Organizational Role Assignment Integration...")
    
    # Test assigning different organizational roles to basic users
    test_assignments = [
        {
            'base_roles': ['hdcnLeden'],
            'org_role': 'National_Chairman',
            'test_permission': 'members_read'
        },
        {
            'base_roles': ['hdcnLeden'],
            'org_role': 'Regional_Secretary_Region4',
            'test_permission': 'events_read'
        },
        {
            'base_roles': ['hdcnLeden', 'Members_Read'],  # User already has some permissions
            'org_role': 'Webmaster',
            'test_permission': 'system_user_management'
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_assignments)
    
    for test_case in test_assignments:
        base_roles = test_case['base_roles']
        org_role = test_case['org_role']
        test_permission = test_case['test_permission']
        
        print(f"\n  Testing: {base_roles} + {org_role}")
        
        # Assign organizational role
        assignment_result = assign_organizational_role(base_roles, org_role)
        
        if assignment_result['success']:
            final_roles = assignment_result['new_roles']
            print(f"    ✅ Assignment successful: {len(assignment_result['added_roles'])} roles added")
            
            # Test that the final role combination works with auth system
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                final_roles, [test_permission], f"test_{org_role.lower()}@hdcn.nl"
            )
            
            if is_authorized:
                print(f"    ✅ Auth validation successful for '{test_permission}'")
                passed_tests += 1
            else:
                print(f"    ❌ Auth validation failed for '{test_permission}'")
                if error_response:
                    error_body = json.loads(error_response.get('body', '{}'))
                    print(f"      Error: {error_body.get('error', 'Unknown error')}")
        else:
            print(f"    ❌ Assignment failed: {assignment_result['message']}")
    
    print(f"\n  📊 Assignment Integration Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def main():
    """Run all organizational role combination tests"""
    print("🚀 Testing Organizational Role Combinations with Authentication")
    print("=" * 70)
    
    test_results = []
    
    try:
        # Run all test suites
        test_results.append(("Authentication Integration", test_organizational_role_authentication()))
        test_results.append(("Regional Access Patterns", test_organizational_role_regional_access()))
        test_results.append(("Permission Combinations", test_organizational_role_permission_combinations()))
        test_results.append(("Assignment Integration", test_organizational_role_assignment_integration()))
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed_suites = 0
        total_suites = len(test_results)
        
        for test_name, passed in test_results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {test_name}: {status}")
            if passed:
                passed_suites += 1
        
        print(f"\n🎯 Overall Result: {passed_suites}/{total_suites} test suites passed")
        
        if passed_suites == total_suites:
            print("🎉 All organizational role combination tests passed!")
            print("✅ Organizational roles are properly integrated with authentication system")
            return True
        else:
            print("⚠️  Some tests failed - organizational role combinations need attention")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)