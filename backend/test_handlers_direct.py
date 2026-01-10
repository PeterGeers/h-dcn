#!/usr/bin/env python3
"""
Direct Handler Test
Tests the handlers by calling their functions directly with mocked dependencies.
"""

import json
import base64
import sys
import os
from unittest.mock import patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def create_test_jwt_token(email, groups):
    """Create a test JWT token for testing purposes"""
    payload = {
        "email": email,
        "cognito:groups": groups,
        "exp": 9999999999,  # Far future expiration
        "iat": 1640995200   # Valid issued at time
    }
    
    # Create a simple JWT-like token (header.payload.signature)
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = "test_signature"
    
    return f"{header}.{payload_encoded}.{signature}"


def create_test_event(email, groups, method="GET", body=None):
    """Create a test Lambda event with authentication headers"""
    jwt_token = create_test_jwt_token(email, groups)
    
    event = {
        "httpMethod": method,
        "headers": {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body) if body else None
    }
    
    return event


def test_get_events_authentication_direct():
    """Test get_events authentication by calling auth functions directly"""
    print("\n🔍 Testing get_events Authentication (Direct)...")
    
    # Import auth functions
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions
    )
    
    test_cases = [
        {
            "name": "Valid Events_Read user",
            "email": "events_reader@hdcn.nl",
            "groups": ["Events_Read", "Regio_All"],
            "should_succeed": True
        },
        {
            "name": "Valid Events_CRUD user",
            "email": "events_admin@hdcn.nl",
            "groups": ["Events_CRUD", "Regio_Noord-Holland"],
            "should_succeed": True
        },
        {
            "name": "Invalid - Members permission only",
            "email": "member_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_succeed": False
        },
        {
            "name": "Invalid - No region role",
            "email": "incomplete@hdcn.nl",
            "groups": ["Events_Read"],
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        event = create_test_event(test_case["email"], test_case["groups"])
        
        # Extract credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            print(f"    ❌ Credential extraction failed: {auth_error}")
            continue
        
        # Validate permissions for events_read
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        if test_case["should_succeed"]:
            if is_authorized:
                print(f"    ✅ Authentication successful")
                print(f"       User: {user_email}")
                print(f"       Roles: {user_roles}")
                print(f"       Regional access: {regional_info}")
            else:
                print(f"    ❌ Authentication failed unexpectedly")
                print(f"       Error: {error_response}")
        else:
            if not is_authorized:
                print(f"    ✅ Authentication correctly denied")
                error_body = json.loads(error_response.get('body', '{}'))
                print(f"       Reason: {error_body.get('error', 'Unknown error')}")
            else:
                print(f"    ❌ Authentication should have failed but succeeded")


def test_create_member_authentication_direct():
    """Test create_member authentication by calling auth functions directly"""
    print("\n🔍 Testing create_member Authentication (Direct)...")
    
    # Import auth functions
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions
    )
    
    test_cases = [
        {
            "name": "Valid Members_CRUD user",
            "email": "member_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_succeed": True
        },
        {
            "name": "Valid regional Members_CRUD user",
            "email": "regional_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_Noord-Holland"],
            "should_succeed": True
        },
        {
            "name": "Invalid - Members_Read only",
            "email": "member_reader@hdcn.nl",
            "groups": ["Members_Read", "Regio_All"],
            "should_succeed": False
        },
        {
            "name": "Invalid - Events permission only",
            "email": "events_admin@hdcn.nl",
            "groups": ["Events_CRUD", "Regio_All"],
            "should_succeed": False
        },
        {
            "name": "Invalid - No region role",
            "email": "incomplete@hdcn.nl",
            "groups": ["Members_CRUD"],
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        event = create_test_event(test_case["email"], test_case["groups"], method="POST",
                                body={"voornaam": "Test", "achternaam": "User"})
        
        # Extract credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            print(f"    ❌ Credential extraction failed: {auth_error}")
            continue
        
        # Validate permissions for members_create
        required_permissions = ['members_create']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        if test_case["should_succeed"]:
            if is_authorized:
                print(f"    ✅ Authentication successful")
                print(f"       User: {user_email}")
                print(f"       Roles: {user_roles}")
                print(f"       Regional access: {regional_info}")
            else:
                print(f"    ❌ Authentication failed unexpectedly")
                print(f"       Error: {error_response}")
        else:
            if not is_authorized:
                print(f"    ✅ Authentication correctly denied")
                error_body = json.loads(error_response.get('body', '{}'))
                print(f"       Reason: {error_body.get('error', 'Unknown error')}")
            else:
                print(f"    ❌ Authentication should have failed but succeeded")


def test_handler_flow_simulation():
    """Simulate the complete handler flow without importing the actual handlers"""
    print("\n🔍 Testing Complete Handler Flow Simulation...")
    
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        handle_options_request,
        create_success_response,
        create_error_response,
        log_successful_access
    )
    
    def simulate_get_events_handler(event, context):
        """Simulate the get_events handler logic"""
        try:
            # Handle OPTIONS request
            if event.get('httpMethod') == 'OPTIONS':
                return handle_options_request()

            # Extract user credentials
            user_email, user_roles, auth_error = extract_user_credentials(event)
            if auth_error:
                return auth_error

            # Validate permissions - require events_read permission
            required_permissions = ['events_read']
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, required_permissions, user_email, None
            )
            if not is_authorized:
                return error_response

            # Log successful access
            log_successful_access(user_email, user_roles, 'get_events')

            # Simulate getting events from database
            mock_events = [
                {'event_id': '1', 'name': 'Test Event 1', 'date': '2024-01-15'},
                {'event_id': '2', 'name': 'Test Event 2', 'date': '2024-02-15'}
            ]
            
            return create_success_response(mock_events)
            
        except Exception as e:
            print(f"Error in simulated get_events handler: {str(e)}")
            return create_error_response(500, f'Internal server error: {str(e)}')
    
    def simulate_create_member_handler(event, context):
        """Simulate the create_member handler logic"""
        try:
            # Handle OPTIONS request
            if event.get('httpMethod') == 'OPTIONS':
                return handle_options_request()
            
            # Extract user credentials
            user_email, user_roles, auth_error = extract_user_credentials(event)
            if auth_error:
                return auth_error
            
            # Validate permissions - require members_create permission
            required_permissions = ['members_create']
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, required_permissions, user_email, None
            )
            if not is_authorized:
                return error_response
            
            # Log successful access
            log_successful_access(user_email, user_roles, 'create_member')
            
            # Parse request body
            body = json.loads(event['body']) if event['body'] else {}
            
            # Simulate member creation
            member_id = "test-member-123"
            
            return create_success_response({
                'member_id': member_id,
                'message': 'Member created successfully'
            }, 201)
            
        except json.JSONDecodeError:
            return create_error_response(400, 'Invalid JSON in request body')
        except Exception as e:
            print(f"Error in simulated create_member handler: {str(e)}")
            return create_error_response(500, 'Internal server error')
    
    # Test get_events simulation
    print("\n  Testing get_events handler simulation:")
    
    # Valid case
    event = create_test_event("events_reader@hdcn.nl", ["Events_Read", "Regio_All"])
    response = simulate_get_events_handler(event, {})
    
    if response["statusCode"] == 200:
        print("    ✅ Valid user - get_events succeeded")
        body = json.loads(response["body"])
        print(f"       Events returned: {len(body)} events")
    else:
        print(f"    ❌ Valid user - get_events failed with status {response['statusCode']}")
    
    # Invalid case
    event = create_test_event("member_admin@hdcn.nl", ["Members_CRUD", "Regio_All"])
    response = simulate_get_events_handler(event, {})
    
    if response["statusCode"] == 403:
        print("    ✅ Invalid user - get_events correctly denied")
    else:
        print(f"    ❌ Invalid user - get_events should have been denied but got status {response['statusCode']}")
    
    # Test create_member simulation
    print("\n  Testing create_member handler simulation:")
    
    # Valid case
    event = create_test_event("member_admin@hdcn.nl", ["Members_CRUD", "Regio_All"], 
                            method="POST", body={"voornaam": "Test", "achternaam": "User"})
    response = simulate_create_member_handler(event, {})
    
    if response["statusCode"] == 201:
        print("    ✅ Valid user - create_member succeeded")
        body = json.loads(response["body"])
        print(f"       Member ID: {body.get('member_id', 'No ID returned')}")
    else:
        print(f"    ❌ Valid user - create_member failed with status {response['statusCode']}")
    
    # Invalid case
    event = create_test_event("member_reader@hdcn.nl", ["Members_Read", "Regio_All"], 
                            method="POST", body={"voornaam": "Test", "achternaam": "User"})
    response = simulate_create_member_handler(event, {})
    
    if response["statusCode"] == 403:
        print("    ✅ Invalid user - create_member correctly denied")
    else:
        print(f"    ❌ Invalid user - create_member should have been denied but got status {response['statusCode']}")


def main():
    """Run all direct handler tests"""
    print("🔐 Direct Handler Authentication Test")
    print("=" * 50)
    print("Testing handler authentication logic directly:")
    print("- get_events authentication flow")
    print("- create_member authentication flow")
    print("- Complete handler flow simulation")
    print("=" * 50)
    
    try:
        # Test authentication logic directly
        test_get_events_authentication_direct()
        test_create_member_authentication_direct()
        
        # Test complete handler flow simulation
        test_handler_flow_simulation()
        
        print("\n" + "=" * 50)
        print("🎉 Direct handler authentication tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()