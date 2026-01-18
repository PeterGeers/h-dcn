#!/usr/bin/env python3
"""
Check Cognito user attributes for peter@pgeers.nl
"""

import boto3
import json
from botocore.exceptions import ClientError

def check_cognito_user():
    """Check Cognito user attributes"""
    
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    username = 'peter@pgeers.nl'
    
    print(f"Checking Cognito user: {username}")
    print(f"User Pool ID: {user_pool_id}")
    
    try:
        # Get user details
        response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        
        print(f"\n✅ User found!")
        print(f"Username: {response.get('Username')}")
        print(f"User Status: {response.get('UserStatus')}")
        print(f"Enabled: {response.get('Enabled')}")
        
        # Check user attributes
        user_attributes = response.get('UserAttributes', [])
        print(f"\n📋 User Attributes ({len(user_attributes)} total):")
        
        custom_member_id = None
        for attr in user_attributes:
            name = attr['Name']
            value = attr['Value']
            print(f"  {name}: {value}")
            
            if name == 'custom:member_id':
                custom_member_id = value
        
        # Check if custom:member_id exists
        if custom_member_id:
            print(f"\n✅ custom:member_id found: {custom_member_id}")
        else:
            print(f"\n❌ custom:member_id NOT found!")
            print("This explains why the /members/me endpoint is failing.")
            
        # Check user groups
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=user_pool_id,
                Username=username
            )
            
            groups = groups_response.get('Groups', [])
            print(f"\n👥 User Groups ({len(groups)} total):")
            for group in groups:
                print(f"  - {group['GroupName']}: {group.get('Description', 'No description')}")
                
        except Exception as e:
            print(f"\n❌ Error getting user groups: {str(e)}")
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"❌ User not found: {username}")
        else:
            print(f"❌ Error: {error_code} - {str(e)}")
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    check_cognito_user()