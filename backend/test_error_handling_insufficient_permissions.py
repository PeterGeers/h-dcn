#!/usr/bin/env python3
"""
Test Error Handling for Insufficient Permissions

This test validates that the authentication system provides proper error messages
when users have insufficient permissions for various operations.

Test Categories:
1. Missing Authorization Headers
2. Invalid JWT Tokens
3. Missing Permission Roles
4. Missing Region Roles
5. Insufficient Permission Levels
6. Regional Access Violations
7. Invalid Role Combinations
8. Edge Cases and Error Scenarios

Author: H-DCN Role Migration Team
Date: 2026-01-09
"""

import sys
import os
import json
import base64
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

from auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    validate_permissions,
    create_error_response,
    cors_headers,
    log_permission_denial
)


class InsufficientPermissionsErrorTester:
    """Test error handling for insufficient permissions scenarios"""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_test_result(self, test_name, passed, details=""):
        """Log test result"""
        if passed:
            self.test_results['passed'] += 1
            print(f"✅ {test_name}")
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {details}")
            print(f"❌ {test_name}: {details}")
    
    def create_mock_jwt_token(self, email, groups):
        """Create a mock JWT token for testing"""
        payload = {
            'email': email,
            'cognito:groups': groups,
            'exp': 9999999999  # Far future expiration
        }
        
        # Create a simple base64 encoded payload (not a real JWT, but sufficient for testing)
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
        
        # Simple mock JWT format: header.payload.signature
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.mock_signature"
    
    def test_missing_authorization_header(self):
        """Test 1: Missing Authorization Header"""
        print("\n=== Test 1: Missing Authorization Header ===")
        
        # Event without authorization header
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        # Should return error
        self.log_test_result(
            "Missing auth header returns None credentials",
            user_email is None and user_roles is None,
            f"Expected None credentials, got email={user_email}, roles={user_roles}"
        )
        
        self.log_test_result(
            "Missing auth header returns 401 error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Missing auth header has clear message",
                'Authorization header required' in body.get('error', ''),
                f"Expected clear message, got: '{body.get('error', '')}'"
            )
    
    def test_invalid_jwt_format(self):
        """Test 2: Invalid JWT Format"""
        print("\n=== Test 2: Invalid JWT Format ===")
        
        # Event with invalid authorization format
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'InvalidFormat'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        self.log_test_result(
            "Invalid JWT format returns None credentials",
            user_email is None and user_roles is None,
            f"Expected None credentials, got email={user_email}, roles={user_roles}"
        )
        
        self.log_test_result(
            "Invalid JWT format returns 401 error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
    
    def test_missing_permission_roles(self):
        """Test 3: Missing Permission Roles"""
        print("\n=== Test 3: Missing Permission Roles ===")
        
        # User with only region role, no permission role
        user_roles = ['Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'no_permission@test.com'
        )
        
        self.log_test_result(
            "User with only region role denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Missing permission role has proper error message",
                'Insufficient permissions' in body.get('error', ''),
                f"Expected permission error, got: '{body.get('error', '')}'"
            )
    
    def test_missing_region_roles(self):
        """Test 4: Missing Region Roles"""
        print("\n=== Test 4: Missing Region Roles ===")
        
        # User with permission role but no region role
        user_roles = ['Members_CRUD']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'no_region@test.com'
        )
        
        self.log_test_result(
            "User with only permission role denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Missing region role has proper error message",
                'Permission requires region assignment' in body.get('error', ''),
                f"Expected region requirement error, got: '{body.get('error', '')}'"
            )
            
            self.log_test_result(
                "Missing region role error includes guidance",
                'required_structure' in body and 'Permission (' in body.get('required_structure', ''),
                f"Expected structure guidance, got: '{body.get('required_structure', '')}'"
            )
    
    def test_insufficient_permission_levels(self):
        """Test 5: Insufficient Permission Levels"""
        print("\n=== Test 5: Insufficient Permission Levels ===")
        
        # Read-only user trying to perform CRUD operations
        user_roles = ['Members_Read', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'read_only@test.com'
        )
        
        self.log_test_result(
            "Read-only user denied CRUD operations",
            not is_authorized,
            f"Expected denial for CRUD, got authorized: {is_authorized}"
        )
        
        # Export user trying to perform CRUD operations
        user_roles = ['Members_Export', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_update'], 'export_only@test.com'
        )
        
        self.log_test_result(
            "Export user denied CRUD operations",
            not is_authorized,
            f"Expected denial for CRUD, got authorized: {is_authorized}"
        )
    
    def test_regional_access_violations(self):
        """Test 6: Regional Access Violations"""
        print("\n=== Test 6: Regional Access Violations ===")
        
        # User trying to access different region
        user_roles = ['Members_CRUD', 'Regio_Noord-Holland']
        
        # Test regional access check
        from auth_utils import can_access_resource_region
        access_result = can_access_resource_region(user_roles, 'Zuid-Holland')
        
        self.log_test_result(
            "Cross-region access properly denied",
            not access_result['can_access'],
            f"Expected denial, got access: {access_result['can_access']}"
        )
        
        self.log_test_result(
            "Cross-region denial has descriptive message",
            'Access denied' in access_result['message'],
            f"Expected descriptive denial, got: '{access_result['message']}'"
        )
    
    def test_invalid_role_combinations(self):
        """Test 7: Invalid Role Combinations"""
        print("\n=== Test 7: Invalid Role Combinations ===")
        
        # Empty roles
        user_roles = []
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'no_roles@test.com'
        )
        
        self.log_test_result(
            "User with no roles denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
        
        # Invalid role names
        user_roles = ['InvalidRole', 'AnotherInvalidRole']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'invalid_roles@test.com'
        )
        
        self.log_test_result(
            "User with invalid roles denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
    
    def test_edge_cases_and_error_scenarios(self):
        """Test 8: Edge Cases and Error Scenarios"""
        print("\n=== Test 8: Edge Cases and Error Scenarios ===")
        
        # Test with None user_roles
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                None, ['members_read'], 'none_roles@test.com'
            )
            self.log_test_result(
                "None user_roles handled gracefully",
                not is_authorized,
                f"Expected denial, got authorized: {is_authorized}"
            )
        except Exception as e:
            self.log_test_result(
                "None user_roles handled gracefully",
                False,
                f"Exception raised: {str(e)}"
            )
        
        # Test with empty required permissions
        user_roles = ['Members_CRUD', 'Regio_All']
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, [], 'empty_perms@test.com'
            )
            self.log_test_result(
                "Empty required permissions handled gracefully",
                is_authorized,  # Should be authorized if no permissions required
                f"Expected authorization, got authorized: {is_authorized}"
            )
        except Exception as e:
            self.log_test_result(
                "Empty required permissions handled gracefully",
                False,
                f"Exception raised: {str(e)}"
            )
    
    def run_all_tests(self):
        """Run all error handling tests"""
        print("🧪 INSUFFICIENT PERMISSIONS ERROR HANDLING TESTS")
        print("=" * 70)
        print("Testing proper error messages for insufficient permissions")
        print("New role structure only (no backward compatibility)")
        print("=" * 70)
        
        # Run all test categories
        self.test_missing_authorization_header()
        self.test_invalid_jwt_format()
        self.test_missing_permission_roles()
        self.test_missing_region_roles()
        self.test_insufficient_permission_levels()
        self.test_regional_access_violations()
        self.test_invalid_role_combinations()
        self.test_edge_cases_and_error_scenarios()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 ERROR HANDLING TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        
        if self.test_results['passed'] + self.test_results['failed'] > 0:
            success_rate = (self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100)
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        else:
            print("\n🎉 All error handling tests passed!")
            print("\n✅ COMPREHENSIVE ERROR HANDLING VALIDATION COMPLETE")
            print("✅ Authentication errors properly handled")
            print("✅ Permission errors provide clear messages")
            print("✅ Regional access violations properly detected")
            print("✅ Invalid role combinations properly rejected")
            print("✅ Edge cases handled gracefully")
        
        print("\n🎯 INSUFFICIENT PERMISSIONS ERROR TESTING COMPLETE")
        
        return self.test_results['failed'] == 0


if __name__ == "__main__":
    tester = InsufficientPermissionsErrorTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL ERROR HANDLING TESTS PASSED!")
        exit(0)
    else:
        print(f"\n💥 {tester.test_results['failed']} error handling tests failed!")
        exit(1)