#!/usr/bin/env python3
"""
Comprehensive Error Handling Tests for Authentication System

This test validates that the authentication system provides proper error messages
for insufficient permissions across all scenarios mentioned in the role migration plan.

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
    log_permission_denial,
    validate_crud_access,
    has_permission_and_region_access,
    can_access_resource_region
)


class ComprehensiveErrorHandlingTester:
    """Test comprehensive error handling for insufficient permissions scenarios"""
    
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
                "Missing auth header has proper error message",
                'Authorization header required' in body.get('error', ''),
                f"Expected 'Authorization header required', got: {body.get('error', '')}"
            )
    
    def test_invalid_jwt_format(self):
        """Test 2: Invalid JWT Token Format"""
        print("\n=== Test 2: Invalid JWT Token Format ===")
        
        # Test invalid Bearer format
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'InvalidFormat token_here'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        self.log_test_result(
            "Invalid Bearer format returns 401 error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
        
        # Test malformed JWT token
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer invalid.jwt.token'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        self.log_test_result(
            "Malformed JWT returns 401 error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
    
    def test_missing_permission_roles(self):
        """Test 3: Missing Permission Roles"""
        print("\n=== Test 3: Missing Permission Roles ===")
        
        # User with only region role, no permission role
        user_roles = ['Regio_All']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'region_only@test.com'
        )
        
        self.log_test_result(
            "Region-only user denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
        
        self.log_test_result(
            "Region-only user gets 403 error",
            error_response is not None and error_response['statusCode'] == 403,
            f"Expected 403 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Region-only user gets proper error message",
                'Insufficient permissions' in body.get('error', ''),
                f"Expected 'Insufficient permissions', got: {body.get('error', '')}"
            )
    
    def test_missing_region_roles(self):
        """Test 4: Missing Region Roles"""
        print("\n=== Test 4: Missing Region Roles ===")
        
        # User with only permission role, no region role
        user_roles = ['Members_CRUD']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'permission_only@test.com'
        )
        
        self.log_test_result(
            "Permission-only user denied access",
            not is_authorized,
            f"Expected denial, got authorized: {is_authorized}"
        )
        
        self.log_test_result(
            "Permission-only user gets 403 error",
            error_response is not None and error_response['statusCode'] == 403,
            f"Expected 403 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Permission-only user gets region assignment error",
                'Permission requires region assignment' in body.get('error', ''),
                f"Expected 'Permission requires region assignment', got: {body.get('error', '')}"
            )
            
            self.log_test_result(
                "Permission-only user error includes missing info",
                'missing' in body and 'Region assignment' in body.get('missing', ''),
                f"Expected missing region assignment info, got: {body.get('missing', '')}"
            )
    
    def test_insufficient_permission_levels(self):
        """Test 5: Insufficient Permission Levels"""
        print("\n=== Test 5: Insufficient Permission Levels ===")
        
        # User with read permission trying to perform CRUD operation
        user_roles = ['Members_Read', 'Regio_All']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'read_only@test.com'
        )
        
        self.log_test_result(
            "Read-only user denied CRUD access",
            not is_authorized,
            f"Expected denial for CRUD, got authorized: {is_authorized}"
        )
        
        self.log_test_result(
            "Read-only user gets 403 error",
            error_response is not None and error_response['statusCode'] == 403,
            f"Expected 403 error, got {error_response['statusCode'] if error_response else 'None'}"
        )
        
        # Test export permission without proper role
        user_roles = ['Members_Read', 'Regio_All']  # Read but no export
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_export'], 'no_export@test.com'
        )
        
        self.log_test_result(
            "User without export permission denied export access",
            not is_authorized,
            f"Expected denial for export, got authorized: {is_authorized}"
        )
    
    def test_regional_access_violations(self):
        """Test 6: Regional Access Violations"""
        print("\n=== Test 6: Regional Access Violations ===")
        
        # User with regional access trying to access different region
        user_roles = ['Members_CRUD', 'Regio_Noord-Holland']
        
        # Test regional access check
        access_info = can_access_resource_region(user_roles, 'Zuid-Holland')
        
        self.log_test_result(
            "Regional user denied cross-region access",
            not access_info['can_access'],
            f"Expected denial for cross-region access, got: {access_info['can_access']}"
        )
        
        self.log_test_result(
            "Regional access denial has proper message",
            'Access denied' in access_info.get('message', '') and 'Zuid-Holland' in access_info.get('message', ''),
            f"Expected proper regional denial message, got: {access_info.get('message', '')}"
        )
        
        # Test CRUD access with regional restriction
        crud_result = validate_crud_access(user_roles, 'Members', 'read', 'Zuid-Holland')
        
        self.log_test_result(
            "CRUD validation respects regional restrictions",
            not crud_result['has_access'],
            f"Expected CRUD denial for wrong region, got access: {crud_result['has_access']}"
        )
    
    def test_invalid_role_combinations(self):
        """Test 7: Invalid Role Combinations"""
        print("\n=== Test 7: Invalid Role Combinations ===")
        
        # User with completely invalid roles
        user_roles = ['InvalidRole', 'AnotherInvalidRole']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'invalid_roles@test.com'
        )
        
        self.log_test_result(
            "Invalid roles denied access",
            not is_authorized,
            f"Expected denial with invalid roles, got authorized: {is_authorized}"
        )
        
        # User with mixed valid/invalid roles
        user_roles = ['Members_CRUD', 'InvalidRegion', 'Regio_All']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'mixed_roles@test.com'
        )
        
        self.log_test_result(
            "Mixed valid/invalid roles work for valid permissions",
            is_authorized,  # Should work because valid roles are present
            f"Expected authorization with mixed roles, got denied: {not is_authorized}"
        )
    
    def test_edge_cases_and_error_scenarios(self):
        """Test 8: Edge Cases and Error Scenarios"""
        print("\n=== Test 8: Edge Cases and Error Scenarios ===")
        
        # Test empty role list
        user_roles = []
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'empty_roles@test.com'
        )
        
        self.log_test_result(
            "Empty role list denied access",
            not is_authorized,
            f"Expected denial with empty roles, got authorized: {is_authorized}"
        )
        
        # Test None user roles
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                None, ['members_read'], 'none_roles@test.com'
            )
            self.log_test_result(
                "None roles handled gracefully",
                not is_authorized,  # Should be denied
                f"Expected denial with None roles, got authorized: {is_authorized}"
            )
        except Exception as e:
            self.log_test_result(
                "None roles handled gracefully",
                False,
                f"Should not crash with None roles: {str(e)}"
            )
        
        # Test empty required permissions
        user_roles = ['Members_CRUD', 'Regio_All']
        
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, [], 'empty_perms@test.com'
            )
            self.log_test_result(
                "Empty required permissions handled",
                True,  # Should not crash
                "Should handle empty required permissions gracefully"
            )
        except Exception as e:
            self.log_test_result(
                "Empty required permissions handled",
                False,
                f"Should not crash with empty permissions: {str(e)}"
            )
        
        # Test None required permissions
        try:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, None, 'none_perms@test.com'
            )
            self.log_test_result(
                "None required permissions handled",
                True,  # Should not crash
                "Should handle None required permissions gracefully"
            )
        except Exception as e:
            self.log_test_result(
                "None required permissions handled",
                False,
                f"Should not crash with None permissions: {str(e)}"
            )
    
    def test_specific_error_message_formats(self):
        """Test 9: Specific Error Message Formats"""
        print("\n=== Test 9: Specific Error Message Formats ===")
        
        # Test that error messages contain required information
        user_roles = ['Members_CRUD']  # Missing region
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'format_test@test.com'
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            
            # Check error structure
            self.log_test_result(
                "Error response has 'error' field",
                'error' in body,
                f"Expected 'error' field in response, got keys: {list(body.keys())}"
            )
            
            self.log_test_result(
                "Error response has 'required_structure' field",
                'required_structure' in body,
                f"Expected 'required_structure' field, got keys: {list(body.keys())}"
            )
            
            self.log_test_result(
                "Error response has 'user_roles' field",
                'user_roles' in body,
                f"Expected 'user_roles' field, got keys: {list(body.keys())}"
            )
            
            self.log_test_result(
                "Error response has 'missing' field",
                'missing' in body,
                f"Expected 'missing' field, got keys: {list(body.keys())}"
            )
            
            # Check CORS headers
            self.log_test_result(
                "Error response has CORS headers",
                'Access-Control-Allow-Origin' in error_response.get('headers', {}),
                f"Expected CORS headers, got: {list(error_response.get('headers', {}).keys())}"
            )
    
    def test_permission_and_region_access_function(self):
        """Test 10: has_permission_and_region_access Function Error Handling"""
        print("\n=== Test 10: Permission and Region Access Function ===")
        
        # Test missing permission
        user_roles = ['Regio_All']
        result = has_permission_and_region_access(user_roles, 'Members_CRUD')
        
        self.log_test_result(
            "Permission function denies access without permission role",
            not result['has_access'],
            f"Expected denial, got access: {result['has_access']}"
        )
        
        self.log_test_result(
            "Permission function provides proper message",
            'missing' in result['message'].lower(),
            f"Expected 'missing' in message, got: {result['message']}"
        )
        
        # Test missing region
        user_roles = ['Members_CRUD']
        result = has_permission_and_region_access(user_roles, 'Members_CRUD')
        
        self.log_test_result(
            "Permission function denies access without region role",
            not result['has_access'],
            f"Expected denial, got access: {result['has_access']}"
        )
        
        # Test specific region requirements
        user_roles = ['Members_CRUD', 'Regio_Noord-Holland']
        result = has_permission_and_region_access(user_roles, 'Members_CRUD', ['Zuid-Holland'])
        
        self.log_test_result(
            "Permission function respects specific region requirements",
            not result['has_access'],
            f"Expected denial for wrong region, got access: {result['has_access']}"
        )
    
    def run_all_tests(self):
        """Run all error handling tests"""
        print("🧪 COMPREHENSIVE ERROR HANDLING TESTS")
        print("=" * 60)
        print("Testing proper error messages for insufficient permissions")
        print("=" * 60)
        
        # Run all test categories
        self.test_missing_authorization_header()
        self.test_invalid_jwt_format()
        self.test_missing_permission_roles()
        self.test_missing_region_roles()
        self.test_insufficient_permission_levels()
        self.test_regional_access_violations()
        self.test_invalid_role_combinations()
        self.test_edge_cases_and_error_scenarios()
        self.test_specific_error_message_formats()
        self.test_permission_and_region_access_function()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 ERROR HANDLING TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📈 Success Rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100):.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        print("\n🎯 ERROR HANDLING VALIDATION COMPLETE")
        
        return self.test_results['failed'] == 0


if __name__ == "__main__":
    tester = ComprehensiveErrorHandlingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All error handling tests passed!")
        exit(0)
    else:
        print(f"\n💥 {tester.test_results['failed']} error handling tests failed!")
        exit(1)