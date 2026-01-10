"""
Focused test for backend handler role validation
Tests the core authentication and authorization functionality
"""

import json
import pytest
import sys
import os
from unittest.mock import Mock, patch
import base64

# Add the backend directory to the path
backend_dir = os.path.join(os.path.dirname(__file__), '../../')
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

def create_jwt_token(user_email, roles):
    """Create a mock JWT token with user email and roles"""
    payload = {
        'email': user_email,
        'cognito:groups': roles
    }
    payload_json = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    return f"header.{payload_b64}.signature"

def create_test_event(user_email, roles, body=None):
    """Create a test Lambda event"""
    jwt_token = create_jwt_token(user_email, roles)
    
    return {
        'httpMethod': 'PUT',
        'path': '/test/test-id',
        'pathParameters': {'id': 'test-id'},
        'headers': {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body) if body else None
    }

class TestRoleValidationResults:
    """Test and document the actual role validation results"""
    
    @patch('boto3.resource')
    def test_products_handler_role_validation(self, mock_boto3):
        """Test update_product handler with various role combinations"""
        # Mock DynamoDB
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.update_item.return_value = {}
        
        # Import the handler
        sys.path.insert(0, os.path.join(backend_dir, 'handler/update_product'))
        from app import lambda_handler
        
        test_cases = [
            {
                'name': 'Valid Products Admin',
                'roles': ['Products_CRUD', 'Regio_All'],
                'expected_status': 200,
                'should_call_db': True
            },
            {
                'name': 'System Admin',
                'roles': ['System_CRUD'],
                'expected_status': 200,
                'should_call_db': True
            },
            {
                'name': 'Legacy Role',
                'roles': ['Products_CRUD_All'],
                'expected_status': 200,
                'should_call_db': True
            },
            {
                'name': 'Wrong Permission Type',
                'roles': ['Events_CRUD', 'Regio_All'],
                'expected_status': 403,
                'should_call_db': False
            },
            {
                'name': 'Incomplete Role (No Region)',
                'roles': ['Products_CRUD'],
                'expected_status': 403,
                'should_call_db': False
            },
            {
                'name': 'Member Permission (Wrong Type)',
                'roles': ['Members_CRUD', 'Regio_All'],
                'expected_status': 403,
                'should_call_db': False
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            # Reset mock
            mock_table.reset_mock()
            
            # Create event
            event = create_test_event(
                f"test-{test_case['name'].lower().replace(' ', '-')}@hdcn.nl",
                test_case['roles'],
                body={'name': 'Updated Product'}
            )
            
            # Execute handler
            response = lambda_handler(event, {})
            
            # Check results
            actual_status = response['statusCode']
            db_called = mock_table.update_item.called
            
            result = {
                'test_case': test_case['name'],
                'roles': test_case['roles'],
                'expected_status': test_case['expected_status'],
                'actual_status': actual_status,
                'expected_db_call': test_case['should_call_db'],
                'actual_db_call': db_called,
                'status_match': actual_status == test_case['expected_status'],
                'db_call_match': db_called == test_case['should_call_db']
            }
            
            results.append(result)
        
        # Print results
        print("\n🧪 Products Handler Role Validation Results:")
        print("=" * 80)
        
        for result in results:
            status_icon = "✅" if result['status_match'] else "❌"
            db_icon = "✅" if result['db_call_match'] else "❌"
            
            print(f"\n{status_icon} {result['test_case']}")
            print(f"   Roles: {result['roles']}")
            print(f"   Status: Expected {result['expected_status']}, Got {result['actual_status']} {status_icon}")
            print(f"   DB Call: Expected {result['expected_db_call']}, Got {result['actual_db_call']} {db_icon}")
        
        # Summary
        passed_tests = sum(1 for r in results if r['status_match'] and r['db_call_match'])
        total_tests = len(results)
        
        print(f"\n📊 Summary: {passed_tests}/{total_tests} tests passed")
        
        # Verify key scenarios work
        valid_scenarios = [r for r in results if r['test_case'] in ['Valid Products Admin', 'System Admin', 'Legacy Role']]
        invalid_scenarios = [r for r in results if r['test_case'] in ['Wrong Permission Type', 'Incomplete Role (No Region)', 'Member Permission (Wrong Type)']]
        
        valid_all_pass = all(r['status_match'] and r['db_call_match'] for r in valid_scenarios)
        invalid_all_blocked = all(r['status_match'] and r['db_call_match'] for r in invalid_scenarios)
        
        if valid_all_pass:
            print("✅ All valid role combinations work correctly")
        else:
            print("❌ Some valid role combinations failed")
            
        if invalid_all_blocked:
            print("✅ All invalid role combinations are properly blocked")
        else:
            print("❌ Some invalid role combinations were not blocked")
        
        return results
    
    @patch('boto3.resource')
    def test_member_handler_role_validation(self, mock_boto3):
        """Test update_member handler with various role combinations"""
        # Mock DynamoDB
        mock_table = Mock()
        mock_boto3.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-id',
                'email': 'member@hdcn.nl',
                'regio': 'Noord-Holland'
            }
        }
        mock_table.update_item.return_value = {}
        
        # Import the handler
        sys.path.insert(0, os.path.join(backend_dir, 'handler/update_member'))
        from app import lambda_handler
        
        test_cases = [
            {
                'name': 'Valid Members Admin',
                'roles': ['Members_CRUD', 'Regio_All'],
                'expected_success': True
            },
            {
                'name': 'System Admin',
                'roles': ['System_CRUD'],
                'expected_success': True
            },
            {
                'name': 'Legacy Role',
                'roles': ['Members_CRUD_All'],
                'expected_success': True
            },
            {
                'name': 'Wrong Permission Type',
                'roles': ['Products_CRUD', 'Regio_All'],
                'expected_success': False
            },
            {
                'name': 'Incomplete Role (No Region)',
                'roles': ['Members_CRUD'],
                'expected_success': False
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            # Reset mock
            mock_table.reset_mock()
            
            # Create event
            event = create_test_event(
                f"test-{test_case['name'].lower().replace(' ', '-')}@hdcn.nl",
                test_case['roles'],
                body={'firstName': 'Updated'}
            )
            
            # Execute handler
            response = lambda_handler(event, {})
            
            # Check results
            actual_success = response['statusCode'] == 200
            
            result = {
                'test_case': test_case['name'],
                'roles': test_case['roles'],
                'expected_success': test_case['expected_success'],
                'actual_success': actual_success,
                'status_code': response['statusCode'],
                'match': actual_success == test_case['expected_success']
            }
            
            results.append(result)
        
        # Print results
        print("\n🧪 Members Handler Role Validation Results:")
        print("=" * 80)
        
        for result in results:
            icon = "✅" if result['match'] else "❌"
            
            print(f"\n{icon} {result['test_case']}")
            print(f"   Roles: {result['roles']}")
            print(f"   Expected Success: {result['expected_success']}")
            print(f"   Actual Success: {result['actual_success']} (Status: {result['status_code']})")
        
        # Summary
        passed_tests = sum(1 for r in results if r['match'])
        total_tests = len(results)
        
        print(f"\n📊 Summary: {passed_tests}/{total_tests} tests passed")
        
        return results

def test_authentication_error_handling():
    """Test authentication error handling"""
    print("\n🧪 Authentication Error Handling:")
    print("=" * 50)
    
    # Import a handler
    sys.path.insert(0, os.path.join(backend_dir, 'handler/update_product'))
    from app import lambda_handler
    
    # Test missing authorization header
    event_no_auth = {
        'httpMethod': 'PUT',
        'pathParameters': {'id': 'test-id'},
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'name': 'Test'})
    }
    
    response = lambda_handler(event_no_auth, {})
    
    if response['statusCode'] == 401:
        print("✅ Missing authorization header properly rejected (401)")
    else:
        print(f"❌ Missing authorization header returned {response['statusCode']}, expected 401")
    
    # Test invalid JWT token
    event_bad_jwt = {
        'httpMethod': 'PUT',
        'pathParameters': {'id': 'test-id'},
        'headers': {
            'Authorization': 'Bearer invalid.token.here',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'name': 'Test'})
    }
    
    response = lambda_handler(event_bad_jwt, {})
    
    if response['statusCode'] == 401:
        print("✅ Invalid JWT token properly rejected (401)")
    else:
        print(f"❌ Invalid JWT token returned {response['statusCode']}, expected 401")

def test_options_request_handling():
    """Test CORS OPTIONS request handling"""
    print("\n🧪 CORS OPTIONS Request Handling:")
    print("=" * 40)
    
    # Import a handler
    sys.path.insert(0, os.path.join(backend_dir, 'handler/update_product'))
    from app import lambda_handler
    
    # Test OPTIONS request
    event_options = {
        'httpMethod': 'OPTIONS',
        'pathParameters': {'id': 'test-id'},
        'headers': {}
    }
    
    response = lambda_handler(event_options, {})
    
    if response['statusCode'] == 200:
        print("✅ OPTIONS request returns 200")
    else:
        print(f"❌ OPTIONS request returned {response['statusCode']}, expected 200")
    
    if 'Access-Control-Allow-Origin' in response.get('headers', {}):
        print("✅ CORS headers present")
    else:
        print("❌ CORS headers missing")

def test_role_migration_summary():
    """Run all tests and provide comprehensive summary"""
    print("\n🚀 Backend Handler Role Migration Test Suite")
    print("=" * 60)
    
    # Run individual tests
    test_instance = TestRoleValidationResults()
    
    with patch('boto3.resource'):
        products_results = test_instance.test_products_handler_role_validation()
        member_results = test_instance.test_member_handler_role_validation()
    
    test_authentication_error_handling()
    test_options_request_handling()
    
    # Overall summary
    print("\n🎯 MIGRATION VALIDATION SUMMARY:")
    print("=" * 40)
    
    # Check key success criteria
    criteria_met = []
    
    # Products handler validation
    products_valid = any(r['status_match'] and r['roles'] == ['Products_CRUD', 'Regio_All'] for r in products_results)
    products_blocks_wrong = any(r['status_match'] and r['roles'] == ['Events_CRUD', 'Regio_All'] and r['actual_status'] == 403 for r in products_results)
    
    if products_valid:
        criteria_met.append("✅ Products handler accepts valid role combinations")
    else:
        criteria_met.append("❌ Products handler rejects valid role combinations")
    
    if products_blocks_wrong:
        criteria_met.append("✅ Products handler blocks invalid role combinations")
    else:
        criteria_met.append("❌ Products handler allows invalid role combinations")
    
    # Member handler validation
    member_valid = any(r['match'] and r['roles'] == ['Members_CRUD', 'Regio_All'] for r in member_results)
    member_blocks_wrong = any(r['match'] and r['roles'] == ['Products_CRUD', 'Regio_All'] and not r['actual_success'] for r in member_results)
    
    if member_valid:
        criteria_met.append("✅ Member handler accepts valid role combinations")
    else:
        criteria_met.append("❌ Member handler rejects valid role combinations")
    
    if member_blocks_wrong:
        criteria_met.append("✅ Member handler blocks invalid role combinations")
    else:
        criteria_met.append("❌ Member handler allows invalid role combinations")
    
    # System admin access
    system_admin_works = any(r['status_match'] and r['roles'] == ['System_CRUD'] for r in products_results)
    if system_admin_works:
        criteria_met.append("✅ System admin has full access")
    else:
        criteria_met.append("❌ System admin access blocked")
    
    # Legacy compatibility
    legacy_works = any(r['status_match'] and 'CRUD_All' in str(r['roles']) for r in products_results)
    if legacy_works:
        criteria_met.append("✅ Legacy roles maintain backward compatibility")
    else:
        criteria_met.append("❌ Legacy roles broken")
    
    # Print all criteria
    for criterion in criteria_met:
        print(criterion)
    
    # Final assessment
    success_count = sum(1 for c in criteria_met if c.startswith("✅"))
    total_count = len(criteria_met)
    
    print(f"\n📊 Overall Success Rate: {success_count}/{total_count} criteria met")
    
    if success_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Backend handlers ready for production.")
    elif success_count >= total_count * 0.8:
        print("\n⚠️  Most tests passed. Minor issues need attention.")
    else:
        print("\n❌ Significant issues found. Migration needs work.")
    
    return {
        'products_results': products_results,
        'member_results': member_results,
        'success_rate': success_count / total_count,
        'criteria_met': criteria_met
    }

if __name__ == '__main__':
    # Run the comprehensive test suite
    results = test_role_migration_summary()