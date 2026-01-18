#!/usr/bin/env python3
"""
Restore the verzoek_lid group that was accidentally deleted.
"""

import boto3
import json
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def create_verzoek_lid_group():
    """Recreate the verzoek_lid group with correct properties"""
    try:
        response = cognito_client.create_group(
            UserPoolId=USER_POOL_ID,
            GroupName='verzoek_lid',
            Description='Membership applicants who have not been approved yet',
            Precedence=100
        )
        print("✅ Successfully created verzoek_lid group")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'GroupExistsException':
            print("⚠️  Group verzoek_lid already exists")
            return True
        else:
            print(f"❌ Error creating group: {e}")
            return False
    except Exception as e:
        print(f"❌ Error creating group: {e}")
        return False

def restore_user_to_group():
    """Add the user back to the verzoek_lid group"""
    user_id = "42653434-c081-7058-54f2-6a4026432cfc"  # The user that was moved
    
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            GroupName='verzoek_lid'
        )
        print(f"✅ Successfully added user {user_id} back to verzoek_lid group")
        return True
    except Exception as e:
        print(f"❌ Error adding user to group: {e}")
        return False

def main():
    print("🔧 Restoring verzoek_lid group...")
    print("=" * 50)
    
    # Step 1: Create the group
    print("1. Creating verzoek_lid group...")
    if not create_verzoek_lid_group():
        print("❌ Failed to create group!")
        return False
    
    # Step 2: Restore the user
    print("\n2. Restoring user to group...")
    if not restore_user_to_group():
        print("❌ Failed to restore user!")
        return False
    
    # Step 3: Verify
    print("\n3. Verifying restoration...")
    try:
        response = cognito_client.list_users_in_group(
            UserPoolId=USER_POOL_ID,
            GroupName='verzoek_lid'
        )
        users = response.get('Users', [])
        print(f"✅ verzoek_lid group now has {len(users)} users")
        
        if users:
            for user in users:
                print(f"   User: {user['Username']}")
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 verzoek_lid group has been restored!")
    print("   The group now exists with the correct lowercase name.")
    
    return True

if __name__ == "__main__":
    main()