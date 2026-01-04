#!/usr/bin/env python3
"""
Script to manage user roles in Cognito User Pool
"""

import boto3
import sys
from botocore.exceptions import ClientError

def remove_user_from_group(email, group_name):
    """Remove user from a Cognito group"""
    
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Remove user from group
        response = cognito_client.admin_remove_user_from_group(
            UserPoolId=user_pool_id,
            Username=email,
            GroupName=group_name
        )
        
        print(f"✅ Successfully removed {email} from group '{group_name}'")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"❌ User {email} not found in User Pool")
        elif error_code == 'ResourceNotFoundException':
            print(f"❌ Group '{group_name}' not found in User Pool")
        else:
            print(f"❌ Error removing user from group: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def add_user_to_group(email, group_name):
    """Add user to a Cognito group"""
    
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Add user to group
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=email,
            GroupName=group_name
        )
        
        print(f"✅ Successfully added {email} to group '{group_name}'")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"❌ User {email} not found in User Pool")
        elif error_code == 'ResourceNotFoundException':
            print(f"❌ Group '{group_name}' not found in User Pool")
        else:
            print(f"❌ Error adding user to group: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def list_user_groups(email):
    """List all groups for a user"""
    
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Get user's groups
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        groups = response.get('Groups', [])
        print(f"\n👤 Groups for user {email}:")
        if groups:
            for group in groups:
                print(f"  - {group['GroupName']}: {group.get('Description', 'No description')}")
        else:
            print("  - No groups assigned")
        
        return [group['GroupName'] for group in groups]
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"❌ User {email} not found in User Pool")
        else:
            print(f"❌ Error listing user groups: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return []

def main():
    email = 'peter.geers@live.nl'
    
    print(f"🔧 Managing roles for user: {email}")
    print("=" * 50)
    
    # Show current groups
    current_groups = list_user_groups(email)
    
    if not current_groups:
        print("\n❌ User has no groups or doesn't exist")
        return
    
    print(f"\n🎯 Actions:")
    print("1. Remove from hdcnLeden group")
    print("2. Add to Verzoek_lid group")
    print("3. Show current groups only")
    print("4. Remove from Verzoek_lid and add back to hdcnLeden")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        if 'hdcnLeden' in current_groups:
            remove_user_from_group(email, 'hdcnLeden')
        else:
            print(f"ℹ️  User is not in hdcnLeden group")
            
    elif choice == '2':
        if 'Verzoek_lid' not in current_groups:
            add_user_to_group(email, 'Verzoek_lid')
        else:
            print(f"ℹ️  User is already in Verzoek_lid group")
            
    elif choice == '3':
        print("ℹ️  Current groups shown above")
        
    elif choice == '4':
        if 'Verzoek_lid' in current_groups:
            remove_user_from_group(email, 'Verzoek_lid')
        if 'hdcnLeden' not in current_groups:
            add_user_to_group(email, 'hdcnLeden')
    else:
        print("❌ Invalid choice")
        return
    
    # Show final groups
    print("\n" + "=" * 50)
    list_user_groups(email)

if __name__ == "__main__":
    main()