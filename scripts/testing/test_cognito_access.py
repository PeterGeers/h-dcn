#!/usr/bin/env python3
"""
Test Cognito access to verify credentials and user pool
"""

import boto3
from botocore.exceptions import ClientError

def test_cognito_access():
    """Test basic Cognito access"""
    
    print("🔍 Testing Cognito Access")
    print("=" * 40)
    
    try:
        # Initialize Cognito client
        cognito = boto3.client('cognito-idp', region_name='eu-west-1')
        user_pool_id = 'eu-west-1_OAT3oPCIm'
        
        print(f"User Pool ID: {user_pool_id}")
        print(f"Region: eu-west-1")
        
        # Test 1: Describe user pool
        print("\n📝 Test 1: Describe user pool...")
        try:
            response = cognito.describe_user_pool(UserPoolId=user_pool_id)
            print("✅ User pool exists and accessible")
            print(f"   Pool Name: {response['UserPool']['Name']}")
            print(f"   Creation Date: {response['UserPool']['CreationDate']}")
        except ClientError as e:
            print(f"❌ User pool access failed: {e}")
            return False
        
        # Test 2: List groups
        print("\n📝 Test 2: List groups...")
        try:
            groups_response = cognito.list_groups(UserPoolId=user_pool_id, Limit=5)
            groups = groups_response.get('Groups', [])
            print(f"✅ Found {len(groups)} groups")
            for group in groups[:3]:  # Show first 3 groups
                print(f"   - {group['GroupName']}")
        except ClientError as e:
            print(f"❌ List groups failed: {e}")
            return False
        
        # Test 3: Check if verzoek_lid group exists
        print("\n📝 Test 3: Check verzoek_lid group...")
        try:
            group_response = cognito.get_group(
                GroupName='verzoek_lid',
                UserPoolId=user_pool_id
            )
            print("✅ verzoek_lid group exists")
            print(f"   Description: {group_response['Group'].get('Description', 'No description')}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("⚠️ verzoek_lid group does not exist")
                print("   This group needs to be created for testing")
            else:
                print(f"❌ Error checking group: {e}")
        
        print("\n✅ Cognito access test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Cognito access test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_cognito_access()
    if success:
        print("\n🎉 Cognito is accessible - can proceed with integration tests")
    else:
        print("\n❌ Cognito access issues - check AWS credentials and permissions")