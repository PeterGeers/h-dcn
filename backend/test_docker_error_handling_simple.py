#!/usr/bin/env python3
"""
Simple Docker Container Error Handling Test

This script tests the enhanced error handling in the Docker container environment
by directly testing the error handling functions and response structures.

Usage:
    python test_docker_error_handling_simple.py
"""

import json
import sys
import os

# Add the handler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'handler', 'generate_member_parquet'))

def test_pandas_error_messages():
    """Test pandas/pyarrow error message handling"""
    print("🧪 Testing pandas/pyarrow error message handling...")
    
    # Import the module
    import app
    
    # Check if pandas is available and error message is captured
    if not app.PANDAS_AVAILABLE:
        print(f"✅ Pandas not available (expected in test environment)")
        print(f"✅ Error captured: {app.PANDAS_ERROR}")
        
        # Test create_parquet_schema error handling
        try:
            app.create_parquet_schema()
            print("❌ Expected RuntimeError for missing pandas")
            return False
        except RuntimeError as e:
            error_msg = str(e)
            if 'PyArrow is required' in error_msg and 'not available' in error_msg:
                print("✅ Proper error message for missing PyArrow")
            else:
                print(f"❌ Unexpected error message: {error_msg}")
                return False
    else:
        print("ℹ️ Pandas is available in this environment")
    
    return True

def test_auth_error_messages():
    """Test authentication error message handling"""
    print("\n🧪 Testing authentication error message handling...")
    
    # Import the module
    import app
    
    # Check authentication availability
    print(f"✅ Auth available: {app.AUTH_AVAILABLE}")
    if not app.AUTH_AVAILABLE:
        print(f"✅ Auth error captured: {app.AUTH_ERROR}")
    
    # Test fallback authentication functions
    event = {'httpMethod': 'POST'}
    user_email, user_roles, auth_error = app.extract_user_credentials(event)
    
    if auth_error:
        print("✅ Authentication properly returns error for missing credentials")
        
        # Check error response structure
        if 'statusCode' in auth_error and 'body' in auth_error:
            print("✅ Error response has proper structure")
            
            try:
                error_body = json.loads(auth_error['body'])
                if 'error' in error_body:
                    print(f"✅ Error message: {error_body['error']}")
                else:
                    print("❌ Missing error field in response body")
                    return False
            except json.JSONDecodeError:
                print("❌ Invalid JSON in error response body")
                return False
        else:
            print("❌ Invalid error response structure")
            return False
    else:
        print("❌ Expected authentication error but got success")
        return False
    
    return True

def test_error_response_structure():
    """Test error response structure consistency"""
    print("\n🧪 Testing error response structure...")
    
    # Import the module
    import app
    
    # Test create_error_response function
    test_details = {
        'docker_context': True,
        'troubleshooting': {
            'check_logs': 'Review CloudWatch logs',
            'check_dependencies': 'Verify libraries'
        }
    }
    
    response = app.create_error_response(500, 'Test error message', test_details)
    
    # Verify response structure
    if 'statusCode' not in response:
        print("❌ Missing statusCode in response")
        return False
    
    if 'headers' not in response:
        print("❌ Missing headers in response")
        return False
    
    if 'body' not in response:
        print("❌ Missing body in response")
        return False
    
    try:
        body = json.loads(response['body'])
        
        if 'error' not in body:
            print("❌ Missing error field in response body")
            return False
        
        if 'docker_context' not in body:
            print("❌ Missing docker_context in response body")
            return False
        
        if 'troubleshooting' not in body:
            print("❌ Missing troubleshooting in response body")
            return False
        
        print("✅ Error response structure is correct")
        print(f"✅ Status code: {response['statusCode']}")
        print(f"✅ Error message: {body['error']}")
        print(f"✅ Docker context: {body['docker_context']}")
        print(f"✅ Troubleshooting keys: {list(body['troubleshooting'].keys())}")
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in response body")
        return False
    
    return True

def test_cors_headers():
    """Test CORS headers in error responses"""
    print("\n🧪 Testing CORS headers...")
    
    # Import the module
    import app
    
    # Test CORS headers function
    headers = app.cors_headers()
    
    required_headers = [
        'Access-Control-Allow-Origin',
        'Access-Control-Allow-Methods',
        'Access-Control-Allow-Headers'
    ]
    
    for header in required_headers:
        if header not in headers:
            print(f"❌ Missing CORS header: {header}")
            return False
    
    print("✅ All required CORS headers present")
    print(f"✅ Headers: {headers}")
    
    return True

def test_options_request_handling():
    """Test OPTIONS request handling"""
    print("\n🧪 Testing OPTIONS request handling...")
    
    # Import the module
    import app
    
    # Test OPTIONS request
    response = app.handle_options_request()
    
    if response['statusCode'] != 200:
        print(f"❌ Expected status 200, got {response['statusCode']}")
        return False
    
    if 'headers' not in response:
        print("❌ Missing headers in OPTIONS response")
        return False
    
    print("✅ OPTIONS request handled correctly")
    print(f"✅ Response: {response}")
    
    return True

def run_simple_tests():
    """Run all simple error handling tests"""
    print("🐳 Testing Docker Container Error Handling (Simple)")
    print("=" * 60)
    
    tests = [
        test_pandas_error_messages,
        test_auth_error_messages,
        test_error_response_structure,
        test_cors_headers,
        test_options_request_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ PASSED")
            else:
                failed += 1
                print("❌ FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Docker container error handling tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

if __name__ == '__main__':
    success = run_simple_tests()
    sys.exit(0 if success else 1)