#!/usr/bin/env python3
"""
Fix the verzoek_lid group case mismatch issue.

The Cognito group is named "Verzoek_lid" but the frontend expects "verzoek_lid".
This script will:
1. Create a new group "verzoek_lid" with the same properties
2. Move all users from "Verzoek_lid" to "verzoek_lid"
3. Delete the old "Verzoek_lid" group
"""

import boto3
import json
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def get_group_info(group_name):
    """Get information about a specific group"""
    try:
        all_groups = []
        next_token = None
        
        while True:
            params = {'UserPoolId': USER_POOL_ID}
            if next_token:
                params['NextToken'] = next_token
                
            response = cognito_client.list_groups(**params)
            groups = response.get('Groups', [])
            all_groups.extend(groups)
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        
        print(f"   Debug: Found {len(all_groups)} total groups across all pages")
        print(f"   Debug: Looking for group: '{group_name}'")
        
        # Print all group names for debugging
        for i, group in enumerate(all_groups):
            print(f"   Debug: Group {i+1}: '{group['GroupName']}'")
        
        for group in all_groups:
            if group['GroupName'] == group_name:
                return group
        return None
    except Exception as e:
        print(f"Error getting group info: {e}")
        return None

def get_users_in_group(group_name):
    """Get all users in a specific group"""
    try:
        response = cognito_client.list_users_in_group(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        )
        return response.get('Users', [])
    except Exception as e:
        print(f"Error getting users in group {group_name}: {e}")
        return []

def create_group(group_name, description, precedence=None):
    """Create a new group"""
    try:
        params = {
            'UserPoolId': USER_POOL_ID,
            'GroupName': group_name,
            'Description': description
        }
        
        if precedence is not None:
            params['Precedence'] = precedence
            
        response = cognito_client.create_group(**params)
        print(f"✅ Created group: {group_name}")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'GroupExistsException':
            print(f"⚠️  Group {group_name} already exists")
            return True
        else:
            print(f"❌ Error creating group {group_name}: {e}")
            return False
    except Exception as e:
        print(f"❌ Error creating group {group_name}: {e}")
        return False

def add_user_to_group(username, group_name):
    """Add a user to a group"""
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True
    except Exception as e:
        print(f"❌ Error adding user {username} to group {group_name}: {e}")
        return False

def remove_user_from_group(username, group_name):
    """Remove a user from a group"""
    try:
        cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True
    except Exception as e:
        print(f"❌ Error removing user {username} from group {group_name}: {e}")
        return False

def delete_group(group_name):
    """Delete a group"""
    try:
        cognito_client.delete_group(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        )
        print(f"✅ Deleted group: {group_name}")
        return True
    except Exception as e:
        print(f"❌ Error deleting group {group_name}: {e}")
        return False

def main():
    print("🔧 Fixing verzoek_lid group case mismatch...")
    print("=" * 60)
    
    old_group_name = "Verzoek_lid"
    new_group_name = "verzoek_lid"
    
    # Step 1: Check if old group exists
    print(f"1. Checking if {old_group_name} group exists...")
    old_group = get_group_info(old_group_name)
    
    if not old_group:
        print(f"❌ Group {old_group_name} not found!")
        return False
    
    print(f"✅ Found {old_group_name} group:")
    print(f"   Description: {old_group.get('Description', 'No description')}")
    print(f"   Precedence: {old_group.get('Precedence', 'Not set')}")
    print(f"   Created: {old_group.get('CreationDate', 'Unknown')}")
    
    # Step 2: Check if new group already exists
    print(f"\n2. Checking if {new_group_name} group already exists...")
    new_group = get_group_info(new_group_name)
    
    if new_group:
        print(f"⚠️  Group {new_group_name} already exists!")
        print("   This means the fix may have already been applied.")
        
        # Check if there are users in the old group
        old_users = get_users_in_group(old_group_name)
        if old_users:
            print(f"   But {old_group_name} still has {len(old_users)} users.")
            print("   Will proceed to migrate them.")
        else:
            print(f"   {old_group_name} has no users. Will just delete it.")
    else:
        # Step 3: Create new group with same properties
        print(f"\n3. Creating {new_group_name} group...")
        success = create_group(
            new_group_name,
            old_group.get('Description', 'Membership applicants who have not been approved yet'),
            old_group.get('Precedence')
        )
        
        if not success:
            print("❌ Failed to create new group!")
            return False
    
    # Step 4: Get users from old group
    print(f"\n4. Getting users from {old_group_name} group...")
    users = get_users_in_group(old_group_name)
    print(f"   Found {len(users)} users in {old_group_name}")
    
    if users:
        # Step 5: Move users to new group
        print(f"\n5. Moving users to {new_group_name} group...")
        success_count = 0
        
        for user in users:
            username = user['Username']
            print(f"   Moving user: {username}")
            
            # Add to new group
            if add_user_to_group(username, new_group_name):
                # Remove from old group
                if remove_user_from_group(username, old_group_name):
                    success_count += 1
                    print(f"   ✅ Successfully moved {username}")
                else:
                    print(f"   ⚠️  Added {username} to new group but failed to remove from old group")
            else:
                print(f"   ❌ Failed to move {username}")
        
        print(f"\n   Successfully moved {success_count}/{len(users)} users")
    
    # Step 6: Delete old group
    print(f"\n6. Deleting {old_group_name} group...")
    if delete_group(old_group_name):
        print("✅ Old group deleted successfully!")
    else:
        print("❌ Failed to delete old group!")
        return False
    
    # Step 7: Verify the fix
    print(f"\n7. Verifying the fix...")
    final_group = get_group_info(new_group_name)
    if final_group:
        final_users = get_users_in_group(new_group_name)
        print(f"✅ {new_group_name} group exists with {len(final_users)} users")
        
        # Check that old group is gone
        old_group_check = get_group_info(old_group_name)
        if not old_group_check:
            print(f"✅ {old_group_name} group has been removed")
        else:
            print(f"⚠️  {old_group_name} group still exists!")
    else:
        print(f"❌ {new_group_name} group not found after fix!")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Group case mismatch fix completed successfully!")
    print(f"   The group is now correctly named '{new_group_name}'")
    print("   The frontend should now be able to see and use this group.")
    
    return True

if __name__ == "__main__":
    main()