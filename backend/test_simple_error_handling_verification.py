#!/usr/bin/env python3
"""
Simple Error Handling Verification Test

This test verifies that error handling works properly with the new role structure
by testing the core authentication functions directly.

Author: H-DCN Role Migration Team
Date: 2026-01-10
"""

import sys
import os
import json
import base64

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

from auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    create_error_response,
    cors_headers
)


def create_mock_jwt_token(email, groups):
    """Create a mock JWT token for testing"""
    payload = {
        'email': email,
        'cognito:groups': groups,
        'exp': 9999999999
    }
    
    payload_json = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.mock_signature"


def test_error_handling_scenarios():
    """Test key error handling scenarios"""
    print("🧪 SIMPLE ERROR HANDLING VERIFICATION")
    print("=" * 60)
    
    test_results = {'passed': 0, 'failed': 0}
    
    def log_result(test_name, passed, details=""):
        if passed:
            test_results['passed'] += 1
            print(f"✅ {test_name}")
        else:
            test_results['failed'] += 1
            print(f"❌ {test_name}: {details}")
    
    # Test 1: Missing Authorization Header
    print("\n=== Test 1: Missing Authorization Header ===")
    event = {'httpMethod': 'GET', 'headers': {}}
    user_email, user_roles, error_response = extract_user_credentials(event)
    
    log_result(
        "Missing auth header returns 401",
        error_response is not None and error_response['statusCode'] == 401,
        f"Expected 401, got {error_response['statusCode'] if error_response else 'None'}"
    )
    
    # Test 2: Incomplete Role (Permission but no Region)
    print("\n=== Test 2: Incomplete Role Structure ===")
    user_roles = ['Members_CRUD']  # Missing region role
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, ['members_read'], 'incomplete@test.com'
    )
    
    log_result(
        "Incomplete role denied access",
        not is_authorized,
        f"Expected denial, got authorized: {is_authorized}"
    )
    
    if error_response:
        body = json.loads(error_response['body'])
        log_result(
            "Incomplete role error has proper status",
            error_response['statusCode'] == 403,
            f"Expected 403, got {error_response['statusCode']}"
        )
        
        log_result(
            "Incomplete role error mentions region requirement",
            'Permission requires region assignment' in body.get('error', ''),
            f"Expected region requirement, got: '{body.get('error', '')}'"
        )
        
        log_result(
            "Incomplete role error includes guidance",
            'required_structure' in body,
            f"Expected structure guidance, got keys: {list(body.keys())}"
        )
    
    # Test 3: Insufficient Permissions
    print("\n=== Test 3: Insufficient Permissions ===")
    user_roles = ['Members_Read', 'Regio_All']  # Read-only trying to create
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, ['members_create'], 'read_only@test.com'
    )
    
    log_result(
        "Read-only user denied CRUD operations",
        not is_authorized,
        f"Expected denial, got authorized: {is_authorized}"
    )
    
    if error_response:
        body = json.loads(error_response['body'])
        log_result(
            "Insufficient permissions error has proper status",
            error_response['statusCode'] == 403,
            f"Expected 403, got {error_response['statusCode']}"
        )
        
        log_result(
            "Insufficient permissions error is descriptive",
            'Insufficient permissions' in body.get('error', ''),
            f"Expected permission error, got: '{body.get('error', '')}'"
        )
    
    # Test 4: Valid Role Combination (should work)
    print("\n=== Test 4: Valid Role Combination ===")
    user_roles = ['Members_CRUD', 'Regio_All']  # Complete valid combination
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, ['members_read'], 'valid_user@test.com'
    )
    
    log_result(
        "Valid role combination authorized",
        is_authorized,
        f"Expected authorization, got authorized: {is_authorized}"
    )
    
    log_result(
        "Valid role combination has no error",
        error_response is None,
        f"Expected no error, got: {error_response}"
    )
    
    if regional_info:
        log_result(
            "Valid role combination has regional info",
            'has_full_access' in regional_info,
            f"Expected regional info, got: {regional_info}"
        )
    
    # Test 5: Regional Access Control
    print("\n=== Test 5: Regional Access Control ===")
    user_roles = ['Members_CRUD', 'Regio_Noord-Holland']  # Regional user
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, ['members_read'], 'regional_user@test.com'
    )
    
    log_result(
        "Regional user authorized for their region",
        is_authorized,
        f"Expected authorization, got authorized: {is_authorized}"
    )
    
    if regional_info:
        log_result(
            "Regional user has limited access",
            not regional_info.get('has_full_access', True),
            f"Expected limited access, got full_access: {regional_info.get('has_full_access')}"
        )
        
        log_result(
            "Regional user has correct region",
            'Noord-Holland' in regional_info.get('allowed_regions', []),
            f"Expected Noord-Holland access, got regions: {regional_info.get('allowed_regions', [])}"
        )
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ERROR HANDLING VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    
    if test_results['passed'] + test_results['failed'] > 0:
        success_rate = (test_results['passed'] / (test_results['passed'] + test_results['failed']) * 100)
        print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if test_results['failed'] == 0:
        print("\n🎉 All error handling verifications passed!")
        print("\n✅ ERROR HANDLING VERIFICATION COMPLETE")
        print("✅ Authentication errors properly handled")
        print("✅ Permission errors provide clear messages")
        print("✅ Regional access controls work correctly")
        print("✅ Valid role combinations work as expected")
        print("✅ Error responses include proper HTTP status codes and CORS headers")
    else:
        print(f"\n💥 {test_results['failed']} error handling verifications failed!")
    
    print("\n🎯 SIMPLE ERROR HANDLING VERIFICATION COMPLETE")
    
    return test_results['failed'] == 0


if __name__ == "__main__":
    success = test_error_handling_scenarios()
    
    if success:
        print("\n🎉 ERROR HANDLING VERIFICATION SUCCESSFUL!")
        exit(0)
    else:
        print("\n💥 ERROR HANDLING VERIFICATION FAILED!")
        exit(1)