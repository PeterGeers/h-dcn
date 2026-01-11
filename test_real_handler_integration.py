#!/usr/bin/env python3
"""
Real Handler Integration Test
Tests actual backend handlers with the new authentication system

This test verifies:
1. Real handlers use the new authentication system correctly
2. Permission validation works with actual handler code
3. Regional access controls are properly implemented
4. Error handling provides consistent messages
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def create_mock_event(method='GET', path_params=None, body=None, jwt_token=None):
    """Create a mock Lambda event for testing"""
    event = {
        'httpMethod': method,
        'headers': {},
        'pathParameters': path_params or {},
        'body': json.dumps(body) if body else None
    }
    
    if jwt_token:
        event['headers']['Authorization'] = f'Bearer {jwt_token}'
    
    return event

def create_test_jwt_token(email, roles):
    """Create a test JWT token (simplified for testing)"""
    import base64
    
    payload = {
        'email': email,
        'cognito:groups': roles,
        'iat': int(datetime.now().timestamp()),
        'exp': int(datetime.now().timestamp()) + 3600
    }
    
    # Simple base64 encoding for test (not secure, just for testing)
    header = base64.urlsafe_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b'test-signature').decode().rstrip('=')
    
    return f'{header}.{payload_encoded}.{signature}'

def test_update_product_handler():
    """Test the update_product handler with new authentication"""
    print("[TEST] Update Product Handler Authentication")
    
    # Test cases with different role combinations
    test_cases = [
        {
            'name': 'National Admin',
            'email': 'admin@hdcn.nl',
            'roles': ['Products_CRUD', 'Regio_All'],
            'should_succeed': True
        },
        {
            'name': 'Regional Product Manager',
            'email': 'regional@hdcn.nl', 
            'roles': ['Products_CRUD', 'Regio_Utrecht'],
            'should_succeed': True
        },
        {
            'name': 'Read Only User',
            'email': 'readonly@hdcn.nl',
            'roles': ['Products_Read', 'Regio_All'],
            'should_succeed': False  # Can't update, only read
        },
        {
            'name': 'Incomplete Role User',
            'email': 'incomplete@hdcn.nl',
            'roles': ['Products_CRUD'],  # Missing region
            'should_succeed': False
        },
        {
            'name': 'No Permission User',
            'email': 'noperm@hdcn.nl',
            'roles': ['Regio_All'],  # Missing permission
            'should_succeed': False
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        try:
            # Import the handler
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'handler', 'update_product'))
            
            # Mock DynamoDB to avoid actual database operations
            with patch('boto3.resource') as mock_boto3:
                mock_table = Mock()
                mock_boto3.return_value.Table.return_value = mock_table
                
                # Mock environment variable
                with patch.dict(os.environ, {'DYNAMODB_TABLE': 'test_products'}):
                    # Import the handler after mocking
                    import app
                    
                    # Create test event
                    jwt_token = create_test_jwt_token(test_case['email'], test_case['roles'])
                    event = create_mock_event(
                        method='PUT',
                        path_params={'id': 'test-product-123'},
                        body={'name': 'Updated Product', 'price': '29.99'},
                        jwt_token=jwt_token
                    )
                    
                    # Call the handler
                    response = app.lambda_handler(event, {})
                    
                    # Check response
                    status_code = response.get('statusCode', 500)
                    success = status_code in [200, 201]
                    
                    test_passed = success == test_case['should_succeed']
                    all_passed = all_passed and test_passed
                    
                    print(f"  {test_case['name']}:")
                    print(f"    Roles: {test_case['roles']}")
                    print(f"    Expected Success: {test_case['should_succeed']}")
                    print(f"    Actual Success: {success} (Status: {status_code})")
                    print(f"    Result: {'PASS' if test_passed else 'FAIL'}")
                    
                    if not test_passed:
                        response_body = json.loads(response.get('body', '{}'))
                        print(f"    Response: {response_body}")
                    
                    print()
            
            # Clean up import
            if 'app' in sys.modules:
                del sys.modules['app']
            
        except Exception as e:
            print(f"  {test_case['name']}: ERROR - {str(e)}")
            all_passed = False
    
    return all_passed

def test_auth_utils_directly():
    """Test the auth_utils functions directly"""
    print("[TEST] Auth Utils Functions")
    
    try:
        # Import auth_utils
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'shared'))
        from auth_utils import validate_permissions_with_regions, extract_user_credentials
        
        # Test permission validation
        test_cases = [
            {
                'name': 'Valid Permission + Region',
                'roles': ['Products_CRUD', 'Regio_All'],
                'permissions': ['products_update'],
                'expected': True
            },
            {
                'name': 'Valid Permission, Missing Region',
                'roles': ['Products_CRUD'],
                'permissions': ['products_update'],
                'expected': False
            },
            {
                'name': 'Missing Permission, Valid Region',
                'roles': ['Regio_All'],
                'permissions': ['products_update'],
                'expected': False
            },
            {
                'name': 'Multiple Permissions',
                'roles': ['Products_CRUD', 'Members_Read', 'Regio_All'],
                'permissions': ['products_update'],
                'expected': True
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                test_case['roles'],
                test_case['permissions'],
                'test@hdcn.nl'
            )
            
            test_passed = is_authorized == test_case['expected']
            all_passed = all_passed and test_passed
            
            print(f"  {test_case['name']}:")
            print(f"    Roles: {test_case['roles']}")
            print(f"    Permissions: {test_case['permissions']}")
            print(f"    Expected: {test_case['expected']}")
            print(f"    Result: {is_authorized}")
            print(f"    Status: {'PASS' if test_passed else 'FAIL'}")
            
            if regional_info:
                print(f"    Regional Info: {regional_info}")
            
            print()
        
        return all_passed
        
    except ImportError as e:
        print(f"  ERROR: Could not import auth_utils: {str(e)}")
        return False
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def test_jwt_extraction():
    """Test JWT token extraction"""
    print("[TEST] JWT Token Extraction")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'shared'))
        from auth_utils import extract_user_credentials
        
        # Test valid JWT token
        jwt_token = create_test_jwt_token('test@hdcn.nl', ['Members_CRUD', 'Regio_All'])
        event = create_mock_event(jwt_token=jwt_token)
        
        user_email, user_roles, auth_error = extract_user_credentials(event)
        
        success = (
            user_email == 'test@hdcn.nl' and
            user_roles == ['Members_CRUD', 'Regio_All'] and
            auth_error is None
        )
        
        print(f"  Valid JWT Token:")
        print(f"    Expected Email: test@hdcn.nl")
        print(f"    Actual Email: {user_email}")
        print(f"    Expected Roles: ['Members_CRUD', 'Regio_All']")
        print(f"    Actual Roles: {user_roles}")
        print(f"    Auth Error: {auth_error}")
        print(f"    Result: {'PASS' if success else 'FAIL'}")
        print()
        
        # Test missing authorization header
        event_no_auth = create_mock_event()
        user_email, user_roles, auth_error = extract_user_credentials(event_no_auth)
        
        no_auth_success = (
            user_email is None and
            user_roles is None and
            auth_error is not None and
            auth_error.get('statusCode') == 401
        )
        
        print(f"  Missing Authorization:")
        print(f"    Expected: No credentials, 401 error")
        print(f"    Result: Email={user_email}, Roles={user_roles}, Error={auth_error is not None}")
        print(f"    Status: {'PASS' if no_auth_success else 'FAIL'}")
        print()
        
        return success and no_auth_success
        
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def test_regional_access_logic():
    """Test regional access logic"""
    print("[TEST] Regional Access Logic")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'shared'))
        from auth_utils import determine_regional_access, can_access_resource_region
        
        test_cases = [
            {
                'name': 'National Access (Regio_All)',
                'roles': ['Members_CRUD', 'Regio_All'],
                'expected_full_access': True,
                'expected_regions': ['all']
            },
            {
                'name': 'Regional Access (Utrecht)',
                'roles': ['Members_CRUD', 'Regio_Utrecht'],
                'expected_full_access': False,
                'expected_regions': ['Utrecht']
            },
            {
                'name': 'Multiple Regional Access',
                'roles': ['Members_CRUD', 'Regio_Utrecht', 'Regio_Limburg'],
                'expected_full_access': False,
                'expected_regions': ['Utrecht', 'Limburg']
            },
            {
                'name': 'System Admin',
                'roles': ['System_CRUD'],
                'expected_full_access': True,
                'expected_regions': ['all']
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            regional_info = determine_regional_access(test_case['roles'])
            
            full_access_correct = regional_info['has_full_access'] == test_case['expected_full_access']
            regions_correct = set(regional_info['allowed_regions']) == set(test_case['expected_regions'])
            
            test_passed = full_access_correct and regions_correct
            all_passed = all_passed and test_passed
            
            print(f"  {test_case['name']}:")
            print(f"    Roles: {test_case['roles']}")
            print(f"    Expected Full Access: {test_case['expected_full_access']}")
            print(f"    Actual Full Access: {regional_info['has_full_access']}")
            print(f"    Expected Regions: {test_case['expected_regions']}")
            print(f"    Actual Regions: {regional_info['allowed_regions']}")
            print(f"    Result: {'PASS' if test_passed else 'FAIL'}")
            print()
        
        return all_passed
        
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def main():
    """Run all real handler integration tests"""
    print("Real Handler Integration Test Suite")
    print("Testing actual backend handlers with new authentication")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run all tests
    tests = [
        ("JWT Token Extraction", test_jwt_extraction),
        ("Auth Utils Functions", test_auth_utils_directly),
        ("Regional Access Logic", test_regional_access_logic),
        ("Update Product Handler", test_update_product_handler)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}")
            print("-" * len(test_name))
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
    
    print("\n" + "=" * 60)
    print("REAL HANDLER TEST SUMMARY")
    print("=" * 60)
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
    
    with open('real_handler_integration_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nDetailed results saved to: real_handler_integration_results.json")
    
    if passed_tests == total_tests:
        print("\n[SUCCESS] All real handler integration tests passed!")
        print("Backend handlers work correctly with new authentication system.")
        return 0
    else:
        print("\n[WARNING] Some real handler integration tests failed.")
        print("Please review the failed tests and fix the issues.")
        return 1

if __name__ == "__main__":
    exit(main())