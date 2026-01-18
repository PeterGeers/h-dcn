#!/usr/bin/env python3
"""
Test the backend API that fetches user groups for Google SSO users
This API is called during the OAuth callback to get existing user permissions
"""

import requests
import json
import boto3

def test_user_groups_api():
    """Test the hdcn-cognito-admin/get-user-groups API endpoint"""
    
    email = "test@example.com"
    api_url = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/hdcn-cognito-admin/get-user-groups"
    
    print(f"🔍 Testing user groups API for: {email}")
    print(f"API URL: {api_url}")
    print("=" * 60)
    
    # Test the API call that happens during Google SSO
    try:
        # Create a test request (without actual JWT token for now)
        payload = {
            "email": email
        }
        
        headers = {
            "Content-Type": "application/json",
            # Note: In real flow, this would have a valid JWT token
            # "Authorization": "Bearer <jwt_token>"
        }
        
        print(f"📤 Making API request...")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        print(f"\n📥 Response received:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Success! Response data:")
                print(json.dumps(data, indent=2))
                
                groups = data.get('groups', [])
                print(f"\n🔍 User groups found: {groups}")
                
                if 'hdcnLeden' in groups:
                    print(f"✅ Peter has hdcnLeden role - should NOT be redirected")
                else:
                    print(f"❌ Peter missing hdcnLeden role - would be redirected")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw response: {response.text}")
                
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 401:
                print(f"\n💡 This is expected - API requires valid JWT token")
                print(f"   In real Google SSO flow, the ID token would be provided")
            elif response.status_code == 403:
                print(f"\n💡 Permission denied - check API permissions")
            elif response.status_code == 500:
                print(f"\n💡 Server error - check backend logs")
                
    except requests.exceptions.Timeout:
        print(f"❌ API request timed out")
    except requests.exceptions.ConnectionError:
        print(f"❌ Failed to connect to API")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def check_cognito_user_directly():
    """Directly check what Cognito returns for Peter's groups"""
    
    print(f"\n" + "=" * 60)
    print(f"🔍 Direct Cognito check for comparison")
    print("=" * 60)
    
    try:
        cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
        
        # Get user by email
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter='email = "test@example.com"'
        )
        
        users = response.get('Users', [])
        if users:
            user = users[0]
            username = user['Username']
            
            # Get user's groups
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            
            groups = [g['GroupName'] for g in groups_response.get('Groups', [])]
            
            print(f"✅ Cognito groups for {user.get('Username')}: {groups}")
            
            # This is what the backend API should return
            expected_api_response = {
                "groups": groups,
                "user": {
                    "email": "test@example.com",
                    "username": username
                }
            }
            
            print(f"\n💡 Expected API response:")
            print(json.dumps(expected_api_response, indent=2))
            
        else:
            print(f"❌ User not found in Cognito")
            
    except Exception as e:
        print(f"❌ Error checking Cognito: {e}")

if __name__ == "__main__":
    test_user_groups_api()
    check_cognito_user_directly()
    
    print(f"\n" + "=" * 60)
    print(f"📋 SUMMARY")
    print("=" * 60)
    print(f"1. The backend API might be failing during Google SSO")
    print(f"2. This would cause empty groups array in frontend")
    print(f"3. Empty groups would trigger redirect to new-member-application")
    print(f"4. Peter should test with fresh browser session")
    print(f"5. Check browser console for API errors during login")