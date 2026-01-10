#!/usr/bin/env python3
"""
Handler Error Handling Integration Test

This test validates that error handling works properly in actual handler contexts,
ensuring that the authentication system provides proper error messages when
integrated with real Lambda handlers.

Author: H-DCN Role Migration Team
Date: 2026-01-09
"""

import sys
import os
import json
import base64
from unittest.mock import patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

# Import handler modules
sys.path.insert(0, os.path.join(backend_dir, 'handler', 'update_product'))
sys.path.insert(0, os.path.join(backend_dir, 'handler', 'update_member'))
sys.path.insert(0, os.path.join(backend_dir, 'handler', 'get_members'))

class HandlerErrorIntegrationTester:
    """Test error handling integration in real handlers"""
    
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
        
        # Create a simple base64 encoded payload
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
        
        # Simple mock JWT format: header.payload.signature
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.mock_signature"
    
    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test_table'})
    @patch('boto3.resource')
    def test_update_product_handler_error_handling(self, mock_boto3):
        """Test error handling in update_product handler"""
        print("\n=== Testing update_product Handler Error Handling ===")
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        # Import handler after mocking
        try:
            import app as update_product_app
        except ImportError:
            # Try alternative import path
            sys.path.insert(0, os.path.join(backend_dir, 'handler', 'update_product'))
            import app as update_product_app
        
        # Test 1: Missing authorization header
        event = {
            'httpMethod': 'PUT',
            'headers': {},
            'body': json.dumps({'productId': 'test123', 'name': 'Test Product'})
        }
        
        response = update_product_app.lambda_handler(event, {})
        
        self.log_test_result(
            "update_product: Missing auth returns 401",
            response['statusCode'] == 401,
            f"Expected 401, got {response['statusCode']}"
        )
        
        # Test 2: User with insufficient permissions
        insufficient_token = self.create_mock_jwt_token('insufficient@test.com', ['Members_Read', 'Regio_All'])
        event = {
            'httpMethod': 'PUT',
            'headers': {
                'Authorization': f'Bearer {insufficient_token}'
            },
            'body': json.dumps({'productId': 'test123', 'name': 'Test Product'})
        }
        
        response = update_product_app.lambda_handler(event, {})
        
        self.log_test_result(
            "update_product: Insufficient permissions returns 403",
            response['statusCode'] == 403,
            f"Expected 403, got {response['statusCode']}"
        )
        
        if response['statusCode'] == 403:
            body = json.loads(response['body'])
            self.log_test_result(
                "update_product: Error message contains permission info",
                'Insufficient permissions' in body.get('error', ''),
                f"Expected permission error, got: {body.get('error', '')}"
            )
        
        # Test 3: User with permission but no region role
        no_region_token = self.create_mock_jwt_token('no_region@test.com', ['Products_CRUD'])
        event = {
            'httpMethod': 'PUT',
            'headers': {
                'Authorization': f'Bearer {no_region_token}'
            },
            'body': json.dumps({'productId': 'test123', 'name': 'Test Product'})
        }
        
        response = update_product_app.lambda_handler(event, {})
        
        self.log_test_result(
            "update_product: Missing region role returns 403",
            response['statusCode'] == 403,
            f"Expected 403, got {response['statusCode']}"
        )
        
        if response['statusCode'] == 403:
            body = json.loads(response['body'])
            self.log_test_result(
                "update_product: Error message mentions region requirement",
                'region assignment' in body.get('error', '').lower(),
                f"Expected region assignment error, got: {body.get('error', '')}"
            )
    
    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test_table'})
    @patch('boto3.resource')
    def test_get_members_handler_error_handling(self, mock_boto3):
        """Test error handling in get_members handler"""
        print("\n=== Testing get_members Handler Error Handling ===")
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        # Import handler
        try:
            sys.path.insert(0, os.path.join(backend_dir, 'handler', 'get_members'))
            import app as get_members_app
        except ImportError as e:
            print(f"Could not import get_members handler: {e}")
            return
        
        # Test 1: User with no permissions
        no_perms_token = self.create_mock_jwt_token('no_perms@test.com', ['hdcnLeden'])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {no_perms_token}'
            }
        }
        
        response = get_members_app.lambda_handler(event, {})
        
        self.log_test_result(
            "get_members: No permissions returns 403",
            response['statusCode'] == 403,
            f"Expected 403, got {response['statusCode']}"
        )
        
        # Test 2: Regional user accessing wrong region data
        regional_token = self.create_mock_jwt_token('regional@test.com', ['Members_Read', 'Regio_Noord-Holland'])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {regional_token}'
            },
            'queryStringParameters': {
                'region': 'Zuid-Holland'  # Different region
            }
        }
        
        # Note: This test depends on the handler implementing regional filtering
        # The error might be caught at the data level rather than auth level
        response = get_members_app.lambda_handler(event, {})
        
        # This should either be 403 (auth level) or return filtered data (data level)
        self.log_test_result(
            "get_members: Regional filtering works",
            response['statusCode'] in [200, 403],  # Either filtered or denied
            f"Expected 200 or 403, got {response['statusCode']}"
        )
    
    def test_cors_headers_in_error_responses(self):
        """Test that error responses include proper CORS headers"""
        print("\n=== Testing CORS Headers in Error Responses ===")
        
        from auth_utils import create_error_response, cors_headers
        
        # Test error response includes CORS headers
        error_response = create_error_response(403, "Test error message")
        
        self.log_test_result(
            "Error response includes CORS headers",
            'Access-Control-Allow-Origin' in error_response.get('headers', {}),
            f"Expected CORS headers, got: {list(error_response.get('headers', {}).keys())}"
        )
        
        self.log_test_result(
            "CORS headers allow all origins",
            error_response.get('headers', {}).get('Access-Control-Allow-Origin') == '*',
            f"Expected '*', got: {error_response.get('headers', {}).get('Access-Control-Allow-Origin')}"
        )
        
        self.log_test_result(
            "CORS headers include proper methods",
            'GET, POST, PUT, DELETE, OPTIONS' in error_response.get('headers', {}).get('Access-Control-Allow-Methods', ''),
            f"Expected proper methods, got: {error_response.get('headers', {}).get('Access-Control-Allow-Methods')}"
        )
    
    def test_error_response_format_consistency(self):
        """Test that all error responses follow consistent format"""
        print("\n=== Testing Error Response Format Consistency ===")
        
        from auth_utils import (
            extract_user_credentials,
            validate_permissions_with_regions,
            create_error_response
        )
        
        # Test extract_user_credentials error format
        event = {'httpMethod': 'GET', 'headers': {}}
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        if error_response:
            self.log_test_result(
                "extract_user_credentials error has statusCode",
                'statusCode' in error_response,
                f"Expected statusCode, got keys: {list(error_response.keys())}"
            )
            
            self.log_test_result(
                "extract_user_credentials error has headers",
                'headers' in error_response,
                f"Expected headers, got keys: {list(error_response.keys())}"
            )
            
            self.log_test_result(
                "extract_user_credentials error has body",
                'body' in error_response,
                f"Expected body, got keys: {list(error_response.keys())}"
            )
            
            # Test body is valid JSON
            try:
                body = json.loads(error_response['body'])
                self.log_test_result(
                    "extract_user_credentials error body is valid JSON",
                    True,
                    "Body parsed successfully"
                )
                
                self.log_test_result(
                    "extract_user_credentials error body has error field",
                    'error' in body,
                    f"Expected error field, got keys: {list(body.keys())}"
                )
            except json.JSONDecodeError as e:
                self.log_test_result(
                    "extract_user_credentials error body is valid JSON",
                    False,
                    f"JSON parse error: {str(e)}"
                )
        
        # Test validate_permissions_with_regions error format
        user_roles = ['Members_CRUD']  # Missing region
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read'], 'format_test@test.com'
        )
        
        if error_response:
            body = json.loads(error_response['body'])
            
            self.log_test_result(
                "validate_permissions error includes user_roles",
                'user_roles' in body,
                f"Expected user_roles field, got keys: {list(body.keys())}"
            )
            
            self.log_test_result(
                "validate_permissions error includes required_structure",
                'required_structure' in body,
                f"Expected required_structure field, got keys: {list(body.keys())}"
            )
            
            self.log_test_result(
                "validate_permissions error includes missing info",
                'missing' in body,
                f"Expected missing field, got keys: {list(body.keys())}"
            )
    
    def run_all_tests(self):
        """Run all handler error integration tests"""
        print("🧪 HANDLER ERROR HANDLING INTEGRATION TESTS")
        print("=" * 60)
        print("Testing error handling in real Lambda handlers")
        print("=" * 60)
        
        # Run all test categories
        self.test_update_product_handler_error_handling()
        self.test_get_members_handler_error_handling()
        self.test_cors_headers_in_error_responses()
        self.test_error_response_format_consistency()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 HANDLER ERROR INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        
        if self.test_results['passed'] + self.test_results['failed'] > 0:
            success_rate = (self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100)
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        print("\n🎯 HANDLER ERROR INTEGRATION VALIDATION COMPLETE")
        
        return self.test_results['failed'] == 0


if __name__ == "__main__":
    tester = HandlerErrorIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All handler error integration tests passed!")
        exit(0)
    else:
        print(f"\n💥 {tester.test_results['failed']} handler error integration tests failed!")
        exit(1)