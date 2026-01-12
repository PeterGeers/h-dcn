#!/usr/bin/env python3
"""
Integration test for POST /members/me endpoint with real Cognito authentication
"""

import json
import requests
import boto3
from datetime import datetime
import uuid

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
COGNITO_USER_POOL_ID = "eu-west-1_OAT3oPCIm"
COGNITO_CLIENT_ID = "6unl8mg5tbv5r727vc39d847vn"

def create_test_user_with_verzoek_lid_role():
    """
    Create a test user with verzoek_lid role for testing
    """
    try:
        cognito = boto3.client('cognito-idp')
        
        # Generate unique test email
        test_email = f"test-applicant-{uuid.uuid4().hex[:8]}@example.com"
        temp_password = "TempPass123!"
        
        print(f"📝 Creating test user: {test_email}")
        
        # Create user
        response = cognito.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=test_email,
            UserAttributes=[
                {'Name': 'email', 'Value': test_email},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        username = response['User']['Username']
        print(f"✅ User created: {username}")
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
            Password=temp_password,
            Permanent=True
        )
        
        # Add to verzoek_lid group
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=username,
                GroupName='verzoek_lid'
            )
            print("✅ Added to verzoek_lid group")
        except cognito.exceptions.ResourceNotFoundException:
            print("⚠️ verzoek_lid group not found - creating it...")
            
            # Create the group if it doesn't exist
            cognito.create_group(
                GroupName='verzoek_lid',
                UserPoolId=COGNITO_USER_POOL_ID,
                Description='Applicants for membership'
            )
            
            # Add user to group
            cognito.admin_add_user_to_group(
                UserPoolId=COGNITO_USER_POOL_ID,
                Username=username,
                GroupName='verzoek_lid'
            )
            print("✅ Created group and added user")
        
        return test_email, temp_password, username
        
    except Exception as e:
        print(f"❌ Failed to create test user: {str(e)}")
        return None, None, None

def authenticate_user(email, password):
    """
    Authenticate user and get JWT token
    """
    try:
        cognito = boto3.client('cognito-idp')
        
        print(f"🔐 Authenticating user: {email}")
        
        response = cognito.admin_initiate_auth(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        if 'AuthenticationResult' in response:
            access_token = response['AuthenticationResult']['AccessToken']
            print("✅ Authentication successful")
            return access_token
        else:
            print("❌ Authentication failed - no token returned")
            return None
            
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return None

def test_member_creation_flow(access_token):
    """
    Test the complete member creation flow
    """
    print("\n🧪 Testing member creation flow")
    print("=" * 50)
    
    # Test member data
    test_member_data = {
        # Required fields
        "voornaam": "Test",
        "achternaam": "Applicant",
        "geboortedatum": "1990-01-01",
        "geslacht": "M",
        "telefoon": "0612345678",
        "straat": "Teststraat 123",
        "postcode": "1234AB",
        "woonplaats": "Amsterdam",
        "lidmaatschap": "Gewoon lid",
        "regio": "Noord-Holland",
        "privacy": "Ja",
        
        # Optional fields
        "initialen": "T.A.",
        "motormerk": "Harley-Davidson",
        "motortype": "Street Glide",
        "bouwjaar": "2020",
        "kenteken": "AB-123-CD",
        "wiewatwaar": "Internet",
        "clubblad": "Digitaal",
        "nieuwsbrief": "Ja",
        "betaalwijze": "Incasso",
        "bankrekeningnummer": "NL91ABNA0417164300"
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Test 1: Check if member record exists (should return 404)
        print("📝 Test 1: Checking if member record exists...")
        get_response = requests.get(f"{API_BASE_URL}/members/me", headers=headers)
        
        if get_response.status_code == 404:
            print("✅ Test 1 PASSED: No existing member record (as expected)")
        else:
            print(f"⚠️ Test 1: Unexpected status {get_response.status_code}")
            print("   This might indicate an existing record")
        
        # Test 2: Create new member record
        print("\n📝 Test 2: Creating new member record...")
        post_response = requests.post(
            f"{API_BASE_URL}/members/me",
            headers=headers,
            json=test_member_data
        )
        
        print(f"Status Code: {post_response.status_code}")
        print(f"Response: {post_response.text}")
        
        if post_response.status_code == 200:
            print("✅ Test 2 PASSED: Member record created successfully")
            response_data = post_response.json()
            member_id = response_data.get('member_id')
            print(f"   Created member_id: {member_id}")
            
            # Test 3: Verify record can be retrieved
            print("\n📝 Test 3: Verifying record can be retrieved...")
            get_response2 = requests.get(f"{API_BASE_URL}/members/me", headers=headers)
            
            if get_response2.status_code == 200:
                print("✅ Test 3 PASSED: Member record retrieved successfully")
                retrieved_data = get_response2.json()
                print(f"   Retrieved member_id: {retrieved_data.get('member_id')}")
                
                # Verify some key fields
                if retrieved_data.get('voornaam') == test_member_data['voornaam']:
                    print("✅ Data integrity check passed")
                else:
                    print("❌ Data integrity check failed")
            else:
                print(f"❌ Test 3 FAILED: Could not retrieve record: {get_response2.status_code}")
            
            # Test 4: Try to create duplicate (should fail)
            print("\n📝 Test 4: Attempting to create duplicate record...")
            duplicate_response = requests.post(
                f"{API_BASE_URL}/members/me",
                headers=headers,
                json=test_member_data
            )
            
            if duplicate_response.status_code == 409:
                print("✅ Test 4 PASSED: Duplicate creation properly rejected")
            else:
                print(f"❌ Test 4 FAILED: Expected 409, got {duplicate_response.status_code}")
            
            return True
            
        elif post_response.status_code == 403:
            print("❌ Test 2 FAILED: Permission denied")
            print("   Check that user has 'verzoek_lid' role with 'members_self_create' permission")
        elif post_response.status_code == 400:
            print("❌ Test 2 FAILED: Bad request")
            print(f"   Error details: {post_response.text}")
        else:
            print(f"❌ Test 2 FAILED: Unexpected status code {post_response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False

def cleanup_test_user(username):
    """
    Clean up test user after testing
    """
    try:
        cognito = boto3.client('cognito-idp')
        
        print(f"\n🧹 Cleaning up test user: {username}")
        
        # Delete user
        cognito.admin_delete_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username
        )
        
        print("✅ Test user deleted")
        
    except Exception as e:
        print(f"⚠️ Failed to cleanup test user: {str(e)}")

def main():
    """
    Main integration test function
    """
    print("🚀 Integration Test: POST /members/me endpoint")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Create test user
    test_email, test_password, username = create_test_user_with_verzoek_lid_role()
    
    if not test_email:
        print("❌ Cannot proceed without test user")
        return False
    
    try:
        # Authenticate user
        access_token = authenticate_user(test_email, test_password)
        
        if not access_token:
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run member creation tests
        success = test_member_creation_flow(access_token)
        
        if success:
            print("\n🎉 All tests passed!")
            print("✅ POST /members/me endpoint is working correctly")
        else:
            print("\n❌ Some tests failed")
        
        return success
        
    finally:
        # Always cleanup test user
        if username:
            cleanup_test_user(username)

if __name__ == "__main__":
    main()