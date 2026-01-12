#!/usr/bin/env python3
import boto3
import json
import os

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def check_user_status(email):
    """Check user's Cognito status and groups"""
    try:
        # First, try to get user by email
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"'
        )
        
        users = response.get('Users', [])
        if not users:
            print(f"❌ User {email} not found in Cognito")
            return None
        
        user = users[0]
        username = user['Username']
        
        print(f"✅ User found in Cognito:")
        print(f"  Username: {username}")
        print(f"  Status: {user.get('UserStatus', 'Unknown')}")
        print(f"  Enabled: {user.get('Enabled', False)}")
        print(f"  Created: {user.get('UserCreateDate', 'Unknown')}")
        print(f"  Last Modified: {user.get('UserLastModifiedDate', 'Unknown')}")
        
        # Get user attributes
        print(f"\n  Attributes:")
        for attr in user.get('Attributes', []):
            print(f"    {attr['Name']}: {attr['Value']}")
        
        # Get user's groups
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            
            groups = groups_response.get('Groups', [])
            print(f"\n  Groups ({len(groups)}):")
            if groups:
                for group in groups:
                    print(f"    - {group['GroupName']}: {group.get('Description', 'No description')}")
            else:
                print("    No groups assigned")
                
        except Exception as e:
            print(f"  Error getting groups: {e}")
        
        return user
        
    except Exception as e:
        print(f"Error checking user status: {e}")
        return None

if __name__ == "__main__":
    email = "peter@pgeers.nl"
    print(f"Checking Cognito status for: {email}")
    print("=" * 50)
    
    user = check_user_status(email)
    
    if user:
        print(f"\n" + "=" * 50)
        print("ANALYSIS:")
        
        # Check if user should have hdcnLeden role based on member record
        print(f"- User exists in Cognito ✅")
        print(f"- User status: {user.get('UserStatus', 'Unknown')}")
        
        # Get groups
        username = user['Username']
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            groups = [g['GroupName'] for g in groups_response.get('Groups', [])]
            
            if 'hdcnLeden' in groups:
                print(f"- Has hdcnLeden role ✅")
            else:
                print(f"- Missing hdcnLeden role ❌")
                print(f"  This could cause redirect to new-member-application")
                
            if 'verzoek_lid' in groups:
                print(f"- Has verzoek_lid role (applicant status)")
                
        except Exception as e:
            print(f"- Error checking groups: {e}")