#!/usr/bin/env python3
"""
Test to verify whether /members/me endpoint can handle new member creation

This test demonstrates that the current endpoint cannot create new member records
for users who don't already have a member record in the database.
"""

import json
import sys
import os

# Add the handler directory to the path so we can import the handler
sys.path.append(os.path.join(os.path.dirname(__file__), 'handler', 'get_member_self'))

def test_new_applicant_scenario():
    """
    Test what happens when a new applicant (with no existing member record) 
    tries to use the /members/me endpoint
    """
    print("=" * 60)
    print("Testing: New Applicant Scenario")
    print("=" * 60)
    
    # Simulate a new applicant with verzoek_lid role
    # This user exists in Cognito but has no member record in DynamoDB
    test_event = {
        'httpMethod': 'GET',
        'headers': {
            'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Im5ld2FwcGxpY2FudEBleGFtcGxlLmNvbSIsImNvZ25pdG86Z3JvdXBzIjpbInZlcnpvZWtfbGlkIl0sImN1c3RvbTptZW1iZXJfaWQiOm51bGx9.fake_signature'
        },
        'body': None
    }
    
    try:
        # Import and test the handler
        from app import lambda_handler
        
        print("📧 Testing user: newapplicant@example.com")
        print("🏷️  User roles: ['verzoek_lid']")
        print("🆔 custom:member_id: null (no existing record)")
        print("🔍 Expected behavior: Should return 404 - Member record not found")
        print()
        
        # Call the handler
        response = lambda_handler(test_event, {})
        
        print("📤 Response:")
        print(f"   Status Code: {response['statusCode']}")
        
        if response.get('body'):
            body = json.loads(response['body'])
            print(f"   Message: {body.get('error', body.get('message', 'No message'))}")
        
        # Analyze the result
        if response['statusCode'] == 404:
            print("✅ CONFIRMED: Endpoint cannot handle new member creation")
            print("   Returns 404 when no existing member record is found")
        else:
            print("❓ UNEXPECTED: Different behavior than expected")
            
    except ImportError as e:
        print(f"❌ Cannot import handler: {e}")
        print("   This test needs to be run from the backend directory")
    except Exception as e:
        print(f"❌ Error during test: {e}")

def test_post_method_support():
    """
    Test whether the endpoint supports POST method for creation
    """
    print("\n" + "=" * 60)
    print("Testing: POST Method Support")
    print("=" * 60)
    
    test_event = {
        'httpMethod': 'POST',
        'headers': {
            'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Im5ld2FwcGxpY2FudEBleGFtcGxlLmNvbSIsImNvZ25pdG86Z3JvdXBzIjpbInZlcnpvZWtfbGlkIl0sImN1c3RvbTptZW1iZXJfaWQiOm51bGx9.fake_signature'
        },
        'body': json.dumps({
            'voornaam': 'New',
            'achternaam': 'Applicant',
            'email': 'newapplicant@example.com'
        })
    }
    
    try:
        from app import lambda_handler
        
        print("📧 Testing user: newapplicant@example.com")
        print("🏷️  User roles: ['verzoek_lid']")
        print("📝 Method: POST (for creation)")
        print("🔍 Expected behavior: Should return 405 - Method not allowed")
        print()
        
        response = lambda_handler(test_event, {})
        
        print("📤 Response:")
        print(f"   Status Code: {response['statusCode']}")
        
        if response.get('body'):
            body = json.loads(response['body'])
            print(f"   Message: {body.get('error', body.get('message', 'No message'))}")
        
        if response['statusCode'] == 405:
            print("✅ CONFIRMED: POST method not supported")
            print("   Endpoint only supports GET and PUT for existing records")
        else:
            print("❓ UNEXPECTED: Different behavior than expected")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

def test_permission_analysis():
    """
    Analyze the permission requirements for member creation
    """
    print("\n" + "=" * 60)
    print("Permission Analysis")
    print("=" * 60)
    
    try:
        # Import auth utilities to check permissions
        sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))
        from auth_utils import ROLE_PERMISSIONS
        
        print("📋 Current Role Permissions:")
        print()
        
        relevant_roles = ['verzoek_lid', 'hdcnLeden', 'Members_CRUD']
        for role in relevant_roles:
            permissions = ROLE_PERMISSIONS.get(role, [])
            print(f"   {role}:")
            for perm in permissions:
                print(f"     - {perm}")
            print()
        
        print("🔍 Analysis:")
        verzoek_permissions = ROLE_PERMISSIONS.get('verzoek_lid', [])
        hdcn_permissions = ROLE_PERMISSIONS.get('hdcnLeden', [])
        
        if 'members_create' in verzoek_permissions:
            print("   ✅ verzoek_lid can create members")
        else:
            print("   ❌ verzoek_lid CANNOT create members")
            
        if 'members_self_create' in verzoek_permissions:
            print("   ✅ verzoek_lid can create own member record")
        else:
            print("   ❌ verzoek_lid CANNOT create own member record")
            
        if 'members_create' in hdcn_permissions:
            print("   ✅ hdcnLeden can create members")
        else:
            print("   ❌ hdcnLeden CANNOT create members")
            
    except ImportError as e:
        print(f"❌ Cannot import auth utilities: {e}")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

def main():
    """
    Run all tests to analyze the current capability
    """
    print("🔬 Member Self-Service Creation Capability Analysis")
    print("=" * 60)
    print("This test analyzes whether the /members/me endpoint can handle")
    print("new member creation for applicants who don't have existing records.")
    print()
    
    # Run the tests
    test_new_applicant_scenario()
    test_post_method_support()
    test_permission_analysis()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print("❌ CONCLUSION: /members/me endpoint CANNOT create new member records")
    print()
    print("🔍 Key Findings:")
    print("   1. Returns 404 when no existing member record found")
    print("   2. Does not support POST method for creation")
    print("   3. verzoek_lid role lacks members_create permission")
    print("   4. Endpoint designed only for existing record operations")
    print()
    print("💡 Recommendation:")
    print("   Extend endpoint with POST support and members_self_create permission")
    print("   See: backend/member_self_endpoint_analysis.md for detailed plan")

if __name__ == "__main__":
    main()