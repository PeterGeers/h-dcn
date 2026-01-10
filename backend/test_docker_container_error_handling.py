#!/usr/bin/env python3
"""
Test Docker Container Error Handling for generate_member_parquet

This script tests the enhanced error handling in the Docker container environment
for the generate_member_parquet Lambda function.

Tests:
1. Pandas/PyArrow library availability and error messages
2. Authentication error handling in Docker environment  
3. Fallback authentication behavior
4. Comprehensive error reporting and troubleshooting information

Usage:
    python test_docker_container_error_handling.py
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the handler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'handler', 'generate_member_parquet'))

class TestDockerContainerErrorHandling(unittest.TestCase):
    """Test error handling in Docker container environment"""
    
    def setUp(self):
        """Set up test environment"""
        self.maxDiff = None
        
    def test_pandas_import_error_handling(self):
        """Test error handling when pandas/pyarrow libraries are missing"""
        print("\n🧪 Testing pandas/pyarrow import error handling...")
        
        # Mock pandas import failure
        with patch.dict('sys.modules', {'pandas': None, 'pyarrow': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'pandas'")):
                # Import the module with mocked pandas failure
                import importlib
                import app
                importlib.reload(app)
                
                # Verify error state is captured
                self.assertFalse(app.PANDAS_AVAILABLE)
                self.assertIsNotNone(app.PANDAS_ERROR)
                self.assertIn('pandas', app.PANDAS_ERROR)
                
                # Test create_parquet_schema error handling
                try:
                    app.create_parquet_schema()
                    self.fail("Expected RuntimeError for missing pandas")
                except RuntimeError as e:
                    self.assertIn('PyArrow is required', str(e))
                    self.assertIn('not available', str(e))
                
                print("✅ Pandas import error handling works correctly")
    
    def test_authentication_fallback_error_handling(self):
        """Test authentication fallback error handling in Docker environment"""
        print("\n🧪 Testing authentication fallback error handling...")
        
        # Mock auth layer import failure
        with patch.dict('sys.modules', {'shared.auth_utils': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'shared.auth_utils'")):
                # Import the module with mocked auth failure
                import importlib
                import app
                importlib.reload(app)
                
                # Verify fallback state is captured
                self.assertFalse(app.AUTH_AVAILABLE)
                self.assertIsNotNone(app.AUTH_ERROR)
                self.assertIn('AuthLayer import failed', app.AUTH_ERROR)
                
                # Test fallback authentication functions
                event = {'httpMethod': 'POST'}
                user_email, user_roles, auth_error = app.extract_user_credentials(event)
                
                self.assertIsNone(user_email)
                self.assertIsNone(user_roles)
                self.assertIsNotNone(auth_error)
                
                # Verify error response structure
                self.assertEqual(auth_error['statusCode'], 401)
                error_body = json.loads(auth_error['body'])
                self.assertIn('Authentication system not available', error_body['error'])
                self.assertIn('AuthLayer could not be loaded', error_body['details'])
                self.assertIn('auth_error', error_body)
                
                print("✅ Authentication fallback error handling works correctly")
    
    def test_lambda_handler_pandas_error(self):
        """Test lambda_handler error handling when pandas is not available"""
        print("\n🧪 Testing lambda_handler pandas error handling...")
        
        # Mock successful auth but failed pandas
        with patch('app.AUTH_AVAILABLE', True), \
             patch('app.PANDAS_AVAILABLE', False), \
             patch('app.PANDAS_ERROR', 'Test pandas import error'), \
             patch('app.extract_user_credentials') as mock_auth:
            
            # Mock successful authentication
            mock_auth.return_value = ('test@example.com', ['Members_CRUD', 'Regio_All'], None)
            
            # Import and test
            import app
            
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({'options': {}})
            }
            context = {}
            
            response = app.lambda_handler(event, context)
            
            # Verify error response
            self.assertEqual(response['statusCode'], 500)
            response_body = json.loads(response['body'])
            
            self.assertIn('Required analytics libraries not available', response_body['error'])
            self.assertIn('pandas_error', response_body)
            self.assertIn('docker_context', response_body)
            self.assertIn('troubleshooting', response_body)
            
            # Verify troubleshooting information
            troubleshooting = response_body['troubleshooting']
            self.assertIn('check_layer', troubleshooting)
            self.assertIn('check_imports', troubleshooting)
            self.assertIn('check_permissions', troubleshooting)
            self.assertIn('check_memory', troubleshooting)
            
            print("✅ Lambda handler pandas error handling works correctly")
    
    def test_lambda_handler_auth_error(self):
        """Test lambda_handler error handling when authentication fails"""
        print("\n🧪 Testing lambda_handler authentication error handling...")
        
        # Mock failed auth
        with patch('app.AUTH_AVAILABLE', False), \
             patch('app.AUTH_ERROR', 'Test auth import error'), \
             patch('app.extract_user_credentials') as mock_auth:
            
            # Mock authentication failure
            auth_error_response = {
                'statusCode': 401,
                'body': json.dumps({
                    'error': 'Authentication system not available',
                    'details': 'AuthLayer could not be loaded in Docker container'
                })
            }
            mock_auth.return_value = (None, None, auth_error_response)
            
            # Import and test
            import app
            
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({'options': {}})
            }
            context = {}
            
            response = app.lambda_handler(event, context)
            
            # Verify error response
            self.assertEqual(response['statusCode'], 401)
            response_body = json.loads(response['body'])
            
            self.assertIn('Authentication system not available', response_body['error'])
            self.assertIn('docker_context', response_body)
            self.assertIn('troubleshooting', response_body)
            
            # Verify troubleshooting information
            troubleshooting = response_body['troubleshooting']
            self.assertIn('check_auth_layer', troubleshooting)
            self.assertIn('check_jwt_token', troubleshooting)
            
            print("✅ Lambda handler authentication error handling works correctly")
    
    def test_permission_error_handling(self):
        """Test permission error handling with enhanced details"""
        print("\n🧪 Testing permission error handling...")
        
        # Mock successful auth but insufficient permissions
        with patch('app.AUTH_AVAILABLE', True), \
             patch('app.PANDAS_AVAILABLE', True), \
             patch('app.extract_user_credentials') as mock_auth:
            
            # Mock authentication with insufficient permissions
            mock_auth.return_value = ('test@example.com', ['Members_Read'], None)
            
            # Import and test
            import app
            
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({'options': {}})
            }
            context = {}
            
            response = app.lambda_handler(event, context)
            
            # Verify error response
            self.assertEqual(response['statusCode'], 403)
            response_body = json.loads(response['body'])
            
            self.assertIn('Access denied', response_body['error'])
            self.assertIn('permission_denied', response_body)
            self.assertIn('docker_context', response_body)
            self.assertIn('troubleshooting', response_body)
            
            # Verify troubleshooting information
            troubleshooting = response_body['troubleshooting']
            self.assertIn('verify_roles', troubleshooting)
            self.assertIn('contact_admin', troubleshooting)
            
            print("✅ Permission error handling works correctly")
    
    def test_regional_access_error_handling(self):
        """Test regional access error handling with enhanced details"""
        print("\n🧪 Testing regional access error handling...")
        
        # Mock successful auth but insufficient regional access
        with patch('app.AUTH_AVAILABLE', True), \
             patch('app.PANDAS_AVAILABLE', True), \
             patch('app.extract_user_credentials') as mock_auth:
            
            # Mock authentication with Members_CRUD but only regional access
            mock_auth.return_value = ('test@example.com', ['Members_CRUD', 'Regio_Utrecht'], None)
            
            # Import and test
            import app
            
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({'options': {}})
            }
            context = {}
            
            response = app.lambda_handler(event, context)
            
            # Verify error response
            self.assertEqual(response['statusCode'], 403)
            response_body = json.loads(response['body'])
            
            self.assertIn('requires national access', response_body['error'])
            self.assertIn('regional_access_denied', response_body)
            self.assertIn('docker_context', response_body)
            self.assertIn('troubleshooting', response_body)
            
            # Verify troubleshooting information
            troubleshooting = response_body['troubleshooting']
            self.assertIn('verify_regio_all', troubleshooting)
            self.assertIn('understand_architecture', troubleshooting)
            
            print("✅ Regional access error handling works correctly")
    
    def test_comprehensive_error_reporting(self):
        """Test comprehensive error reporting in exception handler"""
        print("\n🧪 Testing comprehensive error reporting...")
        
        # Mock successful auth and pandas, but force an exception
        with patch('app.AUTH_AVAILABLE', True), \
             patch('app.PANDAS_AVAILABLE', True), \
             patch('app.extract_user_credentials') as mock_auth, \
             patch('app.load_members_from_dynamodb') as mock_load:
            
            # Mock successful authentication
            mock_auth.return_value = ('test@example.com', ['Members_CRUD', 'Regio_All'], None)
            
            # Mock DynamoDB error
            mock_load.side_effect = Exception("DynamoDB connection failed")
            
            # Import and test
            import app
            
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({'options': {}})
            }
            context = {}
            
            response = app.lambda_handler(event, context)
            
            # Verify error response
            self.assertEqual(response['statusCode'], 500)
            response_body = json.loads(response['body'])
            
            self.assertIn('Internal server error in Docker container', response_body['error'])
            self.assertIn('docker_context', response_body)
            self.assertIn('troubleshooting', response_body)
            self.assertIn('specific_issue', response_body)
            
            # Verify troubleshooting information
            troubleshooting = response_body['troubleshooting']
            self.assertIn('check_logs', troubleshooting)
            self.assertIn('check_dependencies', troubleshooting)
            
            print("✅ Comprehensive error reporting works correctly")

def run_tests():
    """Run all error handling tests"""
    print("🐳 Testing Docker Container Error Handling for generate_member_parquet")
    print("=" * 70)
    
    # Capture test output
    test_output = StringIO()
    runner = unittest.TextTestRunner(stream=test_output, verbosity=2)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDockerContainerErrorHandling)
    
    # Run tests
    result = runner.run(suite)
    
    # Print results
    print(f"\n📊 Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print(f"\n✅ All Docker container error handling tests passed!")
        return True
    else:
        print(f"\n❌ Some tests failed. Check the output above.")
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)