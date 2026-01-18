#!/usr/bin/env python3
"""
Clean up duplicate _All roles that are no longer needed
We now have the simplified system with separate permission + region roles
"""

import boto3
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Target user for role migration
TARGET_USER_EMAIL = 'secretaris.groningen-drenthe@h-dcn.nl'

def list_all_groups():
    """
    List all Cognito groups to see what we have
    
    Returns:
        list: List of group names
    """
    try:
        groups = []
        paginator = cognito_client.get_paginator('list_groups')
        
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for group in page['Groups']:
                groups.append(group['GroupName'])
        
        return sorted(groups)
    except Exception as e:
        print(f"Error listing groups: {str(e)}")
        return []

def get_users_in_group(group_name):
    """
    Get all users in a specific group
    
    Args:
        group_name (str): Name of the group
        
    Returns:
        list: List of usernames in the group
    """
    try:
        users = []
        paginator = cognito_client.get_paginator('list_users_in_group')
        
        for page in paginator.paginate(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        ):
            for user in page['Users']:
                users.append(user['Username'])
        
        return users
    except Exception as e:
        print(f"Error getting users in group {group_name}: {str(e)}")
        return []

def get_user_by_email(email):
    """
    Find user by email address
    
    Args:
        email (str): Email address to search for
        
    Returns:
        tuple: (success, username_or_error, current_groups)
    """
    try:
        # List all users and find by email
        paginator = cognito_client.get_paginator('list_users')
        
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for user in page['Users']:
                # Check user attributes for email
                user_email = None
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        user_email = attr['Value']
                        break
                
                if user_email == email:
                    username = user['Username']
                    
                    # Get current groups
                    groups_response = cognito_client.admin_list_groups_for_user(
                        UserPoolId=USER_POOL_ID,
                        Username=username
                    )
                    
                    current_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
                    return True, username, current_groups
        
        return False, f"User with email {email} not found", []
        
    except Exception as e:
        return False, f"Error finding user: {str(e)}", []

def migrate_user_from_old_to_new_roles(username, old_role, new_roles):
    """
    Migrate user from old _All role to new permission + region roles
    
    Args:
        username (str): Cognito username
        old_role (str): Old _All role to remove
        new_roles (list): New roles to add
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Remove old role
        cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=old_role
        )
        
        # Add new roles
        for role in new_roles:
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=role
            )
        
        return True, f"✅ Migrated from {old_role} to {', '.join(new_roles)}"
        
    except Exception as e:
        return False, f"❌ Error migrating from {old_role}: {str(e)}"

def delete_group_if_empty(group_name):
    """
    Delete a group if it has no users
    
    Args:
        group_name (str): Name of the group to delete
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if group has users
        users = get_users_in_group(group_name)
        
        if users:
            return False, f"⚠️  Group '{group_name}' has {len(users)} users - cannot delete"
        
        # Delete empty group
        cognito_client.delete_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID
        )
        
        return True, f"✅ Deleted empty group '{group_name}'"
        
    except Exception as e:
        return False, f"❌ Error deleting group '{group_name}': {str(e)}"

def main():
    """
    Clean up duplicate _All roles
    """
    print("🧹 Cleaning Up Duplicate _All Roles")
    print("=" * 60)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Step 1: List all current groups
    print("📋 STEP 1: Listing all current groups...")
    all_groups = list_all_groups()
    
    # Categorize groups
    old_all_groups = [g for g in all_groups if g.endswith('_All')]
    new_permission_groups = [g for g in all_groups if g in ['Members_Read', 'Members_CRUD', 'Events_Read', 'Events_CRUD', 'Products_Read', 'Products_CRUD']]
    new_region_groups = [g for g in all_groups if g.startswith('Regio_')]
    other_groups = [g for g in all_groups if g not in old_all_groups and g not in new_permission_groups and g not in new_region_groups]
    
    print(f"   📊 Group Analysis:")
    print(f"   • Old _All groups: {len(old_all_groups)}")
    print(f"   • New permission groups: {len(new_permission_groups)}")
    print(f"   • New region groups: {len(new_region_groups)}")
    print(f"   • Other groups: {len(other_groups)}")
    print()
    
    print(f"   🗂️  Old _All groups to review:")
    for group in old_all_groups:
        users = get_users_in_group(group)
        print(f"   • {group} ({len(users)} users)")
    print()
    
    # Step 2: Migrate our target user if needed
    print(f"👤 STEP 2: Checking target user {TARGET_USER_EMAIL}...")
    success, username_or_error, current_groups = get_user_by_email(TARGET_USER_EMAIL)
    
    if not success:
        print(f"   ❌ {username_or_error}")
    else:
        username = username_or_error
        print(f"   ✅ Found user: {username}")
        print(f"   Current groups: {', '.join(current_groups)}")
        
        # Check if user has any old _All groups that need migration
        user_old_groups = [g for g in current_groups if g in old_all_groups]
        
        if user_old_groups:
            print(f"   ⚠️  User has old _All groups: {', '.join(user_old_groups)}")
            
            # We already migrated Members_Read and Events_Read
            # Check if there are others like Products_Read
            if 'Products_Read' in user_old_groups:
                print(f"   🔄 Migrating Products_Read to Products_Read...")
                success, message = migrate_user_from_old_to_new_roles(
                    username, 
                    'Products_Read', 
                    ['Products_Read']  # Don't add region restriction for products
                )
                print(f"   {message}")
        else:
            print(f"   ✅ User already has new role structure")
    
    print()
    
    # Step 3: Check which _All groups can be safely deleted
    print("🗑️  STEP 3: Checking which _All groups can be deleted...")
    
    # Define the old _All groups that should be replaced
    replaceable_groups = {
        'Members_Read': ['Members_Read', 'Regio_All'],
        'Events_Read': ['Events_Read', 'Regio_All'],
        'Products_Read': ['Products_Read', 'Regio_All']  # Products usually not regional, but could be
    }
    
    deletion_results = {
        'deleted': [],
        'has_users': [],
        'errors': []
    }
    
    for old_group in replaceable_groups.keys():
        if old_group in all_groups:
            users = get_users_in_group(old_group)
            print(f"   📊 {old_group}: {len(users)} users")
            
            if users:
                # List the users for manual review
                print(f"      Users: {', '.join(users[:5])}{' ...' if len(users) > 5 else ''}")
                deletion_results['has_users'].append((old_group, len(users)))
            else:
                # Try to delete empty group
                success, message = delete_group_if_empty(old_group)
                if success:
                    deletion_results['deleted'].append(old_group)
                else:
                    deletion_results['errors'].append((old_group, message))
                print(f"      {message}")
    
    print()
    
    # Step 4: Summary and recommendations
    print("📊 CLEANUP SUMMARY")
    print("=" * 60)
    
    print(f"✅ Groups deleted: {len(deletion_results['deleted'])}")
    if deletion_results['deleted']:
        for group in deletion_results['deleted']:
            print(f"   • {group}")
    
    print(f"\n⚠️  Groups with users (need manual migration): {len(deletion_results['has_users'])}")
    if deletion_results['has_users']:
        for group, user_count in deletion_results['has_users']:
            print(f"   • {group} ({user_count} users)")
    
    print(f"\n❌ Errors: {len(deletion_results['errors'])}")
    if deletion_results['errors']:
        for group, error in deletion_results['errors']:
            print(f"   • {group}: {error}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if deletion_results['has_users']:
        print(f"   1. Migrate users from old _All groups to new permission + region structure:")
        for group, user_count in deletion_results['has_users']:
            if group == 'Members_Read':
                print(f"      • {group} users → Members_Read + Regio_All (or specific region)")
            elif group == 'Events_Read':
                print(f"      • {group} users → Events_Read + Regio_All (or specific region)")
            elif group == 'Products_Read':
                print(f"      • {group} users → Products_Read + Regio_All")
    
    print(f"   2. New role structure is now active:")
    print(f"      • Permission roles: {', '.join(new_permission_groups)}")
    print(f"      • Region roles: {', '.join(new_region_groups)}")
    
    print(f"\n🎯 CURRENT STATUS:")
    print(f"   • Target user ({TARGET_USER_EMAIL}) has new role structure")
    print(f"   • Old _All groups still exist but should be migrated")
    print(f"   • New simplified system is ready for use")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)