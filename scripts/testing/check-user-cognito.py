#!/usr/bin/env python3
"""
Script to check user details in Cognito User Pool
"""

import boto3
import json
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')

# User Pool ID (you may need to update this)
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
USERNAME = 'webmaster@h-dcn.nl'

def get_user_details(username):
    """Get detailed user information from Cognito"""
    try:
        print(f"Checking user: {username}")
        print("=" * 50)
        
        # Get user details
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        print(f"Username: {response.get('Username')}")
        print(f"User Status: {response.get('UserStatus')}")
        print(f"Enabled: {response.get('Enabled')}")
        print(f"User Create Date: {response.get('UserCreateDate')}")
        print(f"User Last Modified Date: {response.get('UserLastModifiedDate')}")
        
        print("\nUser Attributes:")
        for attr in response.get('UserAttributes', []):
            print(f"  {attr['Name']}: {attr['Value']}")
        
        # Get user's groups
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            
            print(f"\nUser Groups ({len(groups_response.get('Groups', []))}):")
            for group in groups_response.get('Groups', []):
                print(f"  - {group['GroupName']}")
                if 'Description' in group:
                    print(f"    Description: {group['Description']}")
                
        except ClientError as e:
            print(f"Error getting user groups: {e}")
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"User {username} not found in user pool")
        else:
            print(f"Error getting user details: {error_code} - {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def list_all_groups():
    """List all available groups in the user pool"""
    try:
        print("\n" + "=" * 50)
        print("Available Groups in User Pool:")
        print("=" * 50)
        
        response = cognito_client.list_groups(
            UserPoolId=USER_POOL_ID
        )
        
        groups = response.get('Groups', [])
        print(f"Total groups: {len(groups)}")
        
        for group in groups:
            print(f"\nGroup: {group['GroupName']}")
            if 'Description' in group:
                print(f"  Description: {group['Description']}")
            if 'Precedence' in group:
                print(f"  Precedence: {group['Precedence']}")
                
    except Exception as e:
        print(f"Error listing groups: {str(e)}")

if __name__ == "__main__":
    # Check user details
    user_details = get_user_details(USERNAME)
    
    # List all available groups
    list_all_groups()
    
    print("\n" + "=" * 50)
    print("Check completed!")