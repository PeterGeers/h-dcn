#!/usr/bin/env python3

import boto3
import json

def test_cognito_user_data():
    """Test what data is available in Cognito for a user"""
    
    print("=" * 60)
    print("Testing Cognito User Data Retrieval")
    print("=" * 60)
    
    # Initialize Cognito client
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    
    # Test user - using the UUID from the JWT logs
    test_user_id = "c24584c4-5071-70e3-e44e-d3786b406450"
    test_email = "peter@pgeers.nl"
    
    print(f"🔍 Testing user: {test_user_id}")
    print(f"📧 Email: {test_email}")
    print()
    
    # Test 1: Get user by UUID (sub)
    print("📋 Test 1: Get user by Cognito UUID (sub)")
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=test_user_id
        )
        
        print("✅ Successfully retrieved user by UUID")
        print(f"📊 Response keys: {list(response.keys())}")
        print(f"👤 Username: {response.get('Username')}")
        print(f"📧 User status: {response.get('UserStatus')}")
        print()
        
        print("🏷️ User Attributes:")
        for attr in response.get('UserAttributes', []):
            print(f"   {attr['Name']}: {attr['Value']}")
        
        print()
        print("👥 User Groups:")
        groups = response.get('UserMFASettingList', [])
        print(f"   Groups in response: {groups}")
        
        # Check for member_id
        member_id = None
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'custom:member_id':
                member_id = attr['Value']
                break
        
        if member_id:
            print(f"✅ Found custom:member_id: {member_id}")
        else:
            print("❌ No custom:member_id found")
        
    except Exception as e:
        print(f"❌ Error getting user by UUID: {str(e)}")
    
    print()
    
    # Test 2: Get user by email
    print("📋 Test 2: Get user by email")
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=test_email
        )
        
        print("✅ Successfully retrieved user by email")
        print(f"👤 Username: {response.get('Username')}")
        
    except Exception as e:
        print(f"❌ Error getting user by email: {str(e)}")
    
    print()
    
    # Test 3: List groups for user
    print("📋 Test 3: List groups for user")
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=test_user_id
        )
        
        print("✅ Successfully retrieved user groups")
        groups = response.get('Groups', [])
        print(f"👥 User is in {len(groups)} groups:")
        for group in groups:
            print(f"   - {group['GroupName']}: {group.get('Description', 'No description')}")
        
    except Exception as e:
        print(f"❌ Error getting user groups: {str(e)}")

if __name__ == "__main__":
    test_cognito_user_data()