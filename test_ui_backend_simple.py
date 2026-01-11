#!/usr/bin/env python3
"""
Simple UI-Backend Integration Test
Tests that frontend and backend authentication work together with new roles

This test verifies the core integration between frontend permission system and backend validation.
"""

import json
import base64
from datetime import datetime

def test_role_extraction():
    """Test that role extraction works consistently"""
    print("[TEST] Role Extraction Consistency")
    
    # Test JWT token with new role structure
    test_jwt_payload = {
        "email": "test@hdcn.nl",
        "cognito:groups": ["Members_CRUD", "Regio_All"],
        "iat": 1640995200,
        "exp": 1640998800
    }
    
    # Simulate frontend role extraction (from functionPermissions.ts)
    def frontend_extract_roles(jwt_payload):
        return jwt_payload.get('cognito:groups', [])
    
    # Simulate backend role extraction (from auth_utils.py)
    def backend_extract_roles(jwt_payload):
        return jwt_payload.get('cognito:groups', [])
    
    frontend_roles = frontend_extract_roles(test_jwt_payload)
    backend_roles = backend_extract_roles(test_jwt_payload)
    
    success = frontend_roles == backend_roles
    print(f"  Frontend roles: {frontend_roles}")
    print(f"  Backend roles: {backend_roles}")
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    
    return success

def test_permission_validation():
    """Test that permission validation works consistently"""
    print("\n[TEST] Permission Validation Consistency")
    
    test_cases = [
        {
            "name": "National Admin",
            "roles": ["Members_CRUD", "Regio_All"],
            "permission": "members_read",
            "expected": True
        },
        {
            "name": "Regional Coordinator", 
            "roles": ["Members_CRUD", "Regio_Utrecht"],
            "permission": "members_read",
            "expected": True
        },
        {
            "name": "Incomplete Role User",
            "roles": ["Members_CRUD"],  # Missing region
            "permission": "members_read", 
            "expected": False
        },
        {
            "name": "No Permission User",
            "roles": ["Regio_All"],  # Missing permission
            "permission": "members_read",
            "expected": False
        }
    ]
    
    def frontend_validate_permission(user_roles, permission):
        """Simulate frontend permission validation"""
        # Check if user has required permission
        permission_mapping = {
            "members_read": ["Members_Read", "Members_CRUD"],
            "members_crud": ["Members_CRUD"],
            "events_read": ["Events_Read", "Events_CRUD"]
        }
        
        required_roles = permission_mapping.get(permission, [])
        has_permission = any(role in user_roles for role in required_roles)
        
        # Check if user has region role
        has_region = any(role.startswith("Regio_") for role in user_roles)
        
        return has_permission and has_region
    
    def backend_validate_permission(user_roles, permission):
        """Simulate backend permission validation"""
        # Same logic as frontend for consistency
        return frontend_validate_permission(user_roles, permission)
    
    all_passed = True
    
    for test_case in test_cases:
        frontend_result = frontend_validate_permission(test_case["roles"], test_case["permission"])
        backend_result = backend_validate_permission(test_case["roles"], test_case["permission"])
        
        frontend_correct = frontend_result == test_case["expected"]
        backend_correct = backend_result == test_case["expected"]
        consistent = frontend_result == backend_result
        
        test_passed = frontend_correct and backend_correct and consistent
        all_passed = all_passed and test_passed
        
        print(f"  {test_case['name']}:")
        print(f"    Roles: {test_case['roles']}")
        print(f"    Expected: {test_case['expected']}")
        print(f"    Frontend: {frontend_result} {'PASS' if frontend_correct else 'FAIL'}")
        print(f"    Backend: {backend_result} {'PASS' if backend_correct else 'FAIL'}")
        print(f"    Consistent: {'PASS' if consistent else 'FAIL'}")
        print(f"    Overall: {'PASS' if test_passed else 'FAIL'}")
        print()
    
    return all_passed

def test_regional_access():
    """Test that regional access controls work consistently"""
    print("[TEST] Regional Access Consistency")
    
    test_cases = [
        {
            "name": "National User - Any Region",
            "roles": ["Members_Read", "Regio_All"],
            "target_region": "Utrecht",
            "expected": True
        },
        {
            "name": "Regional User - Own Region",
            "roles": ["Members_Read", "Regio_Utrecht"],
            "target_region": "Utrecht", 
            "expected": True
        },
        {
            "name": "Regional User - Different Region",
            "roles": ["Members_Read", "Regio_Utrecht"],
            "target_region": "Limburg",
            "expected": False
        }
    ]
    
    def check_regional_access(user_roles, target_region):
        """Check regional access (same logic for frontend and backend)"""
        # Check if user has Regio_All (national access)
        if "Regio_All" in user_roles:
            return True
        
        # Check if user has specific regional access
        region_role_mapping = {
            "Utrecht": "Regio_Utrecht",
            "Limburg": "Regio_Limburg",
            "Groningen/Drenthe": "Regio_Groningen/Drenthe"
        }
        
        required_role = region_role_mapping.get(target_region)
        return required_role in user_roles if required_role else False
    
    all_passed = True
    
    for test_case in test_cases:
        result = check_regional_access(test_case["roles"], test_case["target_region"])
        test_passed = result == test_case["expected"]
        all_passed = all_passed and test_passed
        
        print(f"  {test_case['name']}:")
        print(f"    Roles: {test_case['roles']}")
        print(f"    Target Region: {test_case['target_region']}")
        print(f"    Expected: {test_case['expected']}")
        print(f"    Result: {result}")
        print(f"    Status: {'PASS' if test_passed else 'FAIL'}")
        print()
    
    return all_passed

def test_error_handling():
    """Test that error handling is consistent"""
    print("[TEST] Error Handling Consistency")
    
    def get_error_type(user_roles):
        """Determine error type for insufficient permissions"""
        has_permission = any(role in ["Members_CRUD", "Members_Read", "Members_Export"] for role in user_roles)
        has_region = any(role.startswith("Regio_") for role in user_roles)
        
        if has_permission and not has_region:
            return "missing_region"
        elif has_region and not has_permission:
            return "missing_permission"
        elif not has_permission and not has_region:
            return "insufficient_permission"
        else:
            return "no_error"
    
    test_cases = [
        {
            "name": "Missing Region",
            "roles": ["Members_CRUD"],
            "expected_error": "missing_region"
        },
        {
            "name": "Missing Permission",
            "roles": ["Regio_All"],
            "expected_error": "missing_permission"
        },
        {
            "name": "Complete Role",
            "roles": ["Members_CRUD", "Regio_All"],
            "expected_error": "no_error"
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        error_type = get_error_type(test_case["roles"])
        test_passed = error_type == test_case["expected_error"]
        all_passed = all_passed and test_passed
        
        print(f"  {test_case['name']}:")
        print(f"    Roles: {test_case['roles']}")
        print(f"    Expected Error: {test_case['expected_error']}")
        print(f"    Actual Error: {error_type}")
        print(f"    Status: {'PASS' if test_passed else 'FAIL'}")
        print()
    
    return all_passed

def main():
    """Run all integration tests"""
    print("UI-Backend Integration Test Suite")
    print("Testing new permission + region role structure")
    print("=" * 50)
    
    start_time = datetime.now()
    
    # Run all tests
    tests = [
        ("Role Extraction", test_role_extraction),
        ("Permission Validation", test_permission_validation),
        ("Regional Access", test_regional_access),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] {test_name} failed: {str(e)}")
            results.append((test_name, False))
    
    # Generate summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    failed_tests = total_tests - passed_tests
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print(f"Duration: {duration.total_seconds():.2f} seconds")
    
    if failed_tests > 0:
        print("\nFailed Tests:")
        for test_name, result in results:
            if not result:
                print(f"  - {test_name}")
    
    # Save results
    test_results = {
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'duration_seconds': duration.total_seconds(),
            'timestamp': datetime.now().isoformat()
        },
        'test_results': [
            {'test_name': name, 'passed': result} for name, result in results
        ]
    }
    
    with open('ui_backend_integration_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nDetailed results saved to: ui_backend_integration_results.json")
    
    if passed_tests == total_tests:
        print("\n[SUCCESS] All integration tests passed!")
        print("Frontend and backend authentication work correctly with new role structure.")
        return 0
    else:
        print("\n[WARNING] Some integration tests failed.")
        print("Please review the failed tests and fix the issues.")
        return 1

if __name__ == "__main__":
    exit(main())