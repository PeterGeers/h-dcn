#!/usr/bin/env python3
"""
Error Handling Validation Test

This test validates that the authentication system provides proper error messages
for insufficient permissions as specified in the role migration plan.

This is the final validation test for the error handling task.

Author: H-DCN Role Migration Team
Date: 2026-01-09
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
    validate_permissions,
    create_error_response,
    cors_headers,
    has_permission_and_region_access,
    can_access_resource_region,
    validate_crud_access
)


class ErrorHandlingValidator:
    """Validate error handling for insufficient permissions"""
    
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
            'exp': 9999999999
        }
        
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
        
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.mock_signature"
    
    def validate_critical_error_scenarios(self):
        """Validate the critical error scenarios from the role migration plan"""
        print("\n=== Critical Error Scenarios Validation ===")
        
        # Scenario 1: National Administrator (should work)
        user_roles = ['Members_CRUD', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'national_admin@test.com'
        )
        
        self.log_test_result(
            "National Administrator has full access",
            is_authorized and regional_info['has_full_access'],
            f"Expected full access, got authorized: {is_authorized}, full_access: {regional_info['has_full_access'] if regional_info else 'None'}"
        )
        
        # Scenario 2: Regional Coordinator (should work for their region)
        user_roles = ['Members_CRUD', 'Regio_Groningen/Drenthe']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'regional_coord@test.com'
        )
        
        self.log_test_result(
            "Regional Coordinator has regional access",
            is_authorized and not regional_info['has_full_access'],
            f"Expected regional access, got authorized: {is_authorized}, full_access: {regional_info['has_full_access'] if regional_info else 'None'}"
        )
        
        # Scenario 3: Read-Only User (should be denied CRUD operations)
        user_roles = ['Members_Read', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'read_only@test.com'
        )
        
        self.log_test_result(
            "Read-Only User denied CRUD operations",
            not is_authorized,
            f"Expected denial for CRUD, got authorized: {is_authorized}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Read-Only User gets proper error message",
                'Insufficient permissions' in body.get('error', ''),
                f"Expected 'Insufficient permissions', got: {body.get('error', '')}"
            )
        
        # Scenario 4: Export User (should be denied CRUD operations)
        user_roles = ['Members_Export', 'Regio_All']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_create'], 'export_only@test.com'
        )
        
        self.log_test_result(
            "Export User denied CRUD operations",
            not is_authorized,
            f"Expected denial for CRUD, got authorized: {is_authorized}"
        )
        
        # Scenario 5: Incomplete Role User (permission but no region)
        user_roles = ['Members_CRUD']  # Missing region role
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'incomplete@test.com'
        )
        
        self.log_test_result(
            "Incomplete Role User denied access",
            not is_authorized,
            f"Expected denial for incomplete roles, got authorized: {is_authorized}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Incomplete Role User gets region requirement error",
                'Permission role requires region role' in body.get('error', ''),
                f"Expected region requirement error, got: {body.get('error', '')}"
            )
            
            self.log_test_result(
                "Incomplete Role User error includes missing info",
                'missing' in body and 'Region assignment' in body.get('missing', ''),
                f"Expected missing region info, got: {body.get('missing', '')}"
            )
    
    def validate_error_message_structure(self):
        """Validate that error messages have proper structure and information"""
        print("\n=== Error Message Structure Validation ===")
        
        # Test missing region role error structure
        user_roles = ['Members_CRUD']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'structure_test@test.com'
        )
        
        if error_response:
            # Validate HTTP status code
            self.log_test_result(
                "Error response has 403 status code",
                error_response['statusCode'] == 403,
                f"Expected 403, got {error_response['statusCode']}"
            )
            
            # Validate CORS headers
            headers = error_response.get('headers', {})
            self.log_test_result(
                "Error response includes CORS headers",
                'Access-Control-Allow-Origin' in headers,
                f"Expected CORS headers, got: {list(headers.keys())}"
            )
            
            # Validate body structure
            body = json.loads(error_response['body'])
            required_fields = ['error', 'required_structure', 'user_roles', 'missing']
            
            for field in required_fields:
                self.log_test_result(
                    f"Error response includes '{field}' field",
                    field in body,
                    f"Expected '{field}' field, got keys: {list(body.keys())}"
                )
            
            # Validate error message content
            self.log_test_result(
                "Error message is descriptive",
                len(body.get('error', '')) > 10,
                f"Expected descriptive error, got: '{body.get('error', '')}'"
            )
            
            # Validate required structure guidance
            self.log_test_result(
                "Error includes role structure guidance",
                'Permission (' in body.get('required_structure', '') and 'Region (' in body.get('required_structure', ''),
                f"Expected role structure guidance, got: '{body.get('required_structure', '')}'"
            )
    
    def validate_regional_access_errors(self):
        """Validate regional access violation error messages"""
        print("\n=== Regional Access Error Validation ===")
        
        # Test cross-region access denial
        user_roles = ['Members_CRUD', 'Regio_Noord-Holland']
        access_info = can_access_resource_region(user_roles, 'Zuid-Holland')
        
        self.log_test_result(
            "Cross-region access properly denied",
            not access_info['can_access'],
            f"Expected denial, got access: {access_info['can_access']}"
        )
        
        self.log_test_result(
            "Cross-region denial has descriptive message",
            'Access denied' in access_info['message'] and 'Zuid-Holland' in access_info['message'],
            f"Expected descriptive denial, got: '{access_info['message']}'"
        )
        
        # Test CRUD validation with regional restrictions
        crud_result = validate_crud_access(user_roles, 'Members', 'read', 'Zuid-Holland')
        
        self.log_test_result(
            "CRUD validation respects regional restrictions",
            not crud_result['has_access'],
            f"Expected CRUD denial for wrong region, got access: {crud_result['has_access']}"
        )
        
        self.log_test_result(
            "CRUD regional denial has proper message",
            'Access denied' in crud_result['message'],
            f"Expected proper denial message, got: '{crud_result['message']}'"
        )
    
    def validate_authentication_errors(self):
        """Validate authentication-level error messages"""
        print("\n=== Authentication Error Validation ===")
        
        # Test missing authorization header
        event = {
            'httpMethod': 'GET',
            'headers': {}
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        self.log_test_result(
            "Missing auth header returns proper error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got: {error_response['statusCode'] if error_response else 'None'}"
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            self.log_test_result(
                "Missing auth header has clear message",
                'Authorization header required' in body.get('error', ''),
                f"Expected clear message, got: '{body.get('error', '')}'"
            )
        
        # Test invalid JWT format
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'InvalidFormat'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        self.log_test_result(
            "Invalid auth format returns proper error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got: {error_response['statusCode'] if error_response else 'None'}"
        )
    
    def run_validation(self):
        """Run complete error handling validation"""
        print("🧪 ERROR HANDLING VALIDATION")
        print("=" * 60)
        print("Validating proper error messages for insufficient permissions")
        print("As specified in the role migration plan")
        print("=" * 60)
        
        # Run all validation categories
        self.validate_critical_error_scenarios()
        self.validate_error_message_structure()
        self.validate_regional_access_errors()
        self.validate_authentication_errors()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 ERROR HANDLING VALIDATION SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        
        if self.test_results['passed'] + self.test_results['failed'] > 0:
            success_rate = (self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100)
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED VALIDATIONS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        else:
            print("\n🎉 All error handling validations passed!")
            print("\n✅ TASK COMPLETE: Error handling provides proper messages for insufficient permissions")
            print("✅ Users receive clear, actionable error messages")
            print("✅ Error responses include proper HTTP status codes and CORS headers")
            print("✅ Regional access violations are properly handled")
            print("✅ Authentication errors are clearly communicated")
        
        print("\n🎯 ERROR HANDLING VALIDATION COMPLETE")
        
        return self.test_results['failed'] == 0


if __name__ == "__main__":
    validator = ErrorHandlingValidator()
    success = validator.run_validation()
    
    if success:
        print("\n🎉 ERROR HANDLING TASK SUCCESSFULLY COMPLETED!")
        exit(0)
    else:
        print(f"\n💥 {validator.test_results['failed']} error handling validations failed!")
        exit(1)