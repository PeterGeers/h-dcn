#!/usr/bin/env python3
"""
Security Fixes Verification Test
Tests authentication for handlers that were updated with security fixes:
- get_events/app.py (added authentication with events_read permission)
- create_member/app.py (added authentication with members_create permission)

This test verifies that the authentication works correctly with the new role structure.
"""

import json
import base64
import sys
import os
from datetime import datetime

# Add the backend directory to the path so we can import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        validate_user_has_new_role_structure,
        get_user_permissions_summary,
        quick_role_check
    )
    print("✅ Successfully imported shared auth_utils")
except ImportError as e:
    print(f"❌ Failed to import shared auth_utils: {e}")
    sys.exit(1)


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


def test_authentication_extraction():
    """Test that user credentials are extracted correctly"""
    print("\n🔍 Testing Authentication Extraction...")
    
    test_cases = [
        {
            "name": "Valid user with new role structure",
            "email": "admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_succeed": True
        },
        {
            "name": "Valid regional user",
            "email": "regional@hdcn.nl", 
            "groups": ["Members_Read", "Regio_Noord-Holland"],
            "should_succeed": True
        },
        {
            "name": "User with incomplete role structure (missing region)",
            "email": "incomplete@hdcn.nl",
            "groups": ["Members_CRUD"],
            "should_succeed": True  # Extraction should succeed, validation should fail
        },
        {
            "name": "User with no groups",
            "email": "nogroups@hdcn.nl",
            "groups": [],
            "should_succeed": True  # Extraction should succeed, validation should fail
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        event = create_test_event(test_case["email"], test_case["groups"])
        
        user_email, user_roles, auth_error = extract_user_credentials(event)
        
        if test_case["should_succeed"]:
            if auth_error is None:
                print(f"    ✅ Extraction successful: {user_email} with roles {user_roles}")
            else:
                print(f"    ❌ Extraction failed unexpectedly: {auth_error}")
        else:
            if auth_error is not None:
                print(f"    ✅ Extraction correctly failed: {auth_error}")
            else:
                print(f"    ❌ Extraction should have failed but succeeded")


def test_get_events_authentication():
    """Test authentication for get_events handler"""
    print("\n🔍 Testing get_events Handler Authentication...")
    
    test_cases = [
        {
            "name": "Admin user with full access",
            "email": "admin@hdcn.nl",
            "groups": ["System_CRUD"],
            "should_succeed": True,
            "expected_reason": "Admin access"
        },
        {
            "name": "User with Events_CRUD + Regio_All",
            "email": "events_admin@hdcn.nl",
            "groups": ["Events_CRUD", "Regio_All"],
            "should_succeed": True,
            "expected_reason": "Events CRUD permission with national access"
        },
        {
            "name": "User with Events_Read + Regional access",
            "email": "events_reader@hdcn.nl",
            "groups": ["Events_Read", "Regio_Noord-Holland"],
            "should_succeed": True,
            "expected_reason": "Events read permission with regional access"
        },
        {
            "name": "User with Members_CRUD but no Events permission",
            "email": "member_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_succeed": False,
            "expected_reason": "Wrong permission type"
        },
        {
            "name": "User with Events_Read but no region",
            "email": "incomplete@hdcn.nl",
            "groups": ["Events_Read"],
            "should_succeed": False,
            "expected_reason": "Missing region role"
        },
        {
            "name": "User with only region role",
            "email": "region_only@hdcn.nl",
            "groups": ["Regio_All"],
            "should_succeed": False,
            "expected_reason": "Missing permission role"
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
        
        # Test the specific permission validation for get_events
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        if test_case["should_succeed"]:
            if is_authorized:
                print(f"    ✅ Authorization successful: {test_case['expected_reason']}")
                print(f"       Regional info: {regional_info}")
            else:
                print(f"    ❌ Authorization failed unexpectedly")
                print(f"       Error: {error_response}")
        else:
            if not is_authorized:
                print(f"    ✅ Authorization correctly denied: {test_case['expected_reason']}")
                print(f"       Error: {error_response.get('body', 'No error body')}")
            else:
                print(f"    ❌ Authorization should have failed but succeeded")


def test_create_member_authentication():
    """Test authentication for create_member handler"""
    print("\n🔍 Testing create_member Handler Authentication...")
    
    test_cases = [
        {
            "name": "Admin user with full access",
            "email": "admin@hdcn.nl",
            "groups": ["System_CRUD"],
            "should_succeed": True,
            "expected_reason": "Admin access"
        },
        {
            "name": "User with Members_CRUD + Regio_All",
            "email": "member_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_succeed": True,
            "expected_reason": "Members CRUD permission with national access"
        },
        {
            "name": "User with Members_CRUD + Regional access",
            "email": "regional_admin@hdcn.nl",
            "groups": ["Members_CRUD", "Regio_Noord-Holland"],
            "should_succeed": True,
            "expected_reason": "Members CRUD permission with regional access"
        },
        {
            "name": "User with Members_Read (read-only)",
            "email": "member_reader@hdcn.nl",
            "groups": ["Members_Read", "Regio_All"],
            "should_succeed": False,
            "expected_reason": "Read-only user cannot create members"
        },
        {
            "name": "User with Events_CRUD but no Members permission",
            "email": "events_admin@hdcn.nl",
            "groups": ["Events_CRUD", "Regio_All"],
            "should_succeed": False,
            "expected_reason": "Wrong permission type"
        },
        {
            "name": "User with Members_CRUD but no region",
            "email": "incomplete@hdcn.nl",
            "groups": ["Members_CRUD"],
            "should_succeed": False,
            "expected_reason": "Missing region role"
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
        
        # Test the specific permission validation for create_member
        required_permissions = ['members_create']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        if test_case["should_succeed"]:
            if is_authorized:
                print(f"    ✅ Authorization successful: {test_case['expected_reason']}")
                print(f"       Regional info: {regional_info}")
            else:
                print(f"    ❌ Authorization failed unexpectedly")
                print(f"       Error: {error_response}")
        else:
            if not is_authorized:
                print(f"    ✅ Authorization correctly denied: {test_case['expected_reason']}")
                print(f"       Error: {error_response.get('body', 'No error body')}")
            else:
                print(f"    ❌ Authorization should have failed but succeeded")


def test_role_structure_validation():
    """Test the new role structure validation"""
    print("\n🔍 Testing Role Structure Validation...")
    
    test_cases = [
        {
            "name": "Valid new structure (Permission + Region)",
            "groups": ["Members_CRUD", "Regio_All"],
            "should_be_valid": True
        },
        {
            "name": "Valid admin structure",
            "groups": ["System_CRUD"],
            "should_be_valid": True
        },
        {
            "name": "Multiple permissions with region",
            "groups": ["Members_CRUD", "Events_Read", "Regio_Noord-Holland"],
            "should_be_valid": True
        },
        {
            "name": "Permission without region",
            "groups": ["Members_CRUD"],
            "should_be_valid": False
        },
        {
            "name": "Region without permission",
            "groups": ["Regio_All"],
            "should_be_valid": False
        },
        {
            "name": "No roles",
            "groups": [],
            "should_be_valid": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        result = validate_user_has_new_role_structure(test_case["groups"])
        
        if test_case["should_be_valid"]:
            if result["has_new_structure"]:
                print(f"    ✅ Valid structure: {result['validation_message']}")
            else:
                print(f"    ❌ Should be valid but isn't: {result['validation_message']}")
        else:
            if not result["has_new_structure"]:
                print(f"    ✅ Correctly invalid: {result['validation_message']}")
            else:
                print(f"    ❌ Should be invalid but isn't: {result['validation_message']}")


def test_regional_access():
    """Test regional access controls"""
    print("\n🔍 Testing Regional Access Controls...")
    
    test_cases = [
        {
            "name": "Regio_All user accessing any region",
            "groups": ["Members_Read", "Regio_All"],
            "test_region": "Noord-Holland",
            "should_have_access": True
        },
        {
            "name": "Regional user accessing their region",
            "groups": ["Members_Read", "Regio_Noord-Holland"],
            "test_region": "Noord-Holland",
            "should_have_access": True
        },
        {
            "name": "Regional user accessing different region",
            "groups": ["Members_Read", "Regio_Noord-Holland"],
            "test_region": "Zuid-Holland",
            "should_have_access": False
        },
        {
            "name": "Admin user accessing any region",
            "groups": ["System_CRUD"],
            "test_region": "Groningen/Drenthe",
            "should_have_access": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        regional_info = determine_regional_access(test_case["groups"])
        
        if test_case["should_have_access"]:
            if regional_info["has_full_access"] or test_case["test_region"] in regional_info["allowed_regions"]:
                print(f"    ✅ Access granted: {regional_info}")
            else:
                print(f"    ❌ Access should be granted but was denied: {regional_info}")
        else:
            if not regional_info["has_full_access"] and test_case["test_region"] not in regional_info["allowed_regions"]:
                print(f"    ✅ Access correctly denied: {regional_info}")
            else:
                print(f"    ❌ Access should be denied but was granted: {regional_info}")


def test_permission_mappings():
    """Test that permission mappings work correctly"""
    print("\n🔍 Testing Permission Mappings...")
    
    test_cases = [
        {
            "name": "Members_CRUD should grant members_create",
            "roles": ["Members_CRUD", "Regio_All"],
            "required_permission": "members_create",
            "should_have_permission": True
        },
        {
            "name": "Members_Read should grant members_read but not members_create",
            "roles": ["Members_Read", "Regio_All"],
            "required_permission": "members_create",
            "should_have_permission": False
        },
        {
            "name": "Events_CRUD should grant events_read",
            "roles": ["Events_CRUD", "Regio_All"],
            "required_permission": "events_read",
            "should_have_permission": True
        },
        {
            "name": "Events_Read should grant events_read",
            "roles": ["Events_Read", "Regio_All"],
            "required_permission": "events_read",
            "should_have_permission": True
        },
        {
            "name": "Members_CRUD should not grant events_read",
            "roles": ["Members_CRUD", "Regio_All"],
            "required_permission": "events_read",
            "should_have_permission": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        is_authorized, error_response = validate_permissions(
            test_case["roles"], 
            [test_case["required_permission"]], 
            "test@hdcn.nl"
        )
        
        if test_case["should_have_permission"]:
            if is_authorized:
                print(f"    ✅ Permission correctly granted")
            else:
                print(f"    ❌ Permission should be granted but was denied: {error_response}")
        else:
            if not is_authorized:
                print(f"    ✅ Permission correctly denied")
            else:
                print(f"    ❌ Permission should be denied but was granted")


def main():
    """Run all security verification tests"""
    print("🔐 Security Fixes Verification Test")
    print("=" * 50)
    print("Testing authentication for handlers with security fixes:")
    print("- get_events/app.py (events_read permission)")
    print("- create_member/app.py (members_create permission)")
    print("=" * 50)
    
    try:
        # Test basic authentication extraction
        test_authentication_extraction()
        
        # Test specific handler authentication
        test_get_events_authentication()
        test_create_member_authentication()
        
        # Test role structure validation
        test_role_structure_validation()
        
        # Test regional access controls
        test_regional_access()
        
        # Test permission mappings
        test_permission_mappings()
        
        print("\n" + "=" * 50)
        print("🎉 Security verification tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()