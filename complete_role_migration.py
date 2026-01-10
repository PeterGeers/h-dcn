#!/usr/bin/env python3
"""
Complete the migration from old _All roles to new permission + region structure
"""

import boto3
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Define migration mappings
OLD_TO_NEW_MAPPINGS = {
    'Members_Read': ['Members_Read'],
    'Events_Read': ['Events_Read'], 
    'Products_Read': ['Products_Read'],
    'Communication_Read': ['Communication_Read'],
    'Communication_Export': ['Communication_Export'],
    'Communication_CRUD': ['Communication_CRUD'],
    'Members_CRUD': ['Members_CRUD'],
    'Events_CRUD': ['Events_CRUD'],
    'Products_CRUD': ['Products_CRUD'],
    'System_CRUD': ['System_CRUD']
}

def get_users_in_group(group_name):
    """Get all users in a specific group with their details"""
    try:
        users = []
        paginator = cognito_client.get_paginator('list_users_in_group')
        
        for page in paginator.paginate(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        ):
            for user in page['Users']:
                # Get user's email
                email = None
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        email = attr['Value']
                        break
                
                # Get user's current groups
                try:
                    groups_response = cognito_client.admin_list_groups_for_user(
                        UserPoolId=USER_POOL_ID,
                        Username=user['Username']
                    )
                    current_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
                except Exception as e:
                    current_groups = []
                
                users.append({
                    'username': user['Username'],
                    'email': email,
                    'current_groups': current_groups,
                    'status': user.get('UserStatus', 'Unknown')
                })
        
        return users
    except Exception as e:
        print(f"Error getting users in group {group_name}: {str(e)}")
        return []

def add_user_to_group(username, group_name):
    """Add user to a Cognito group"""
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True, f"✅ Added to {group_name}"
    except Exception as e:
        return False, f"❌ Error adding to {group_name}: {str(e)}"

def remove_user_from_group(username, group_name):
    """Remove user from a Cognito group"""
    try:
        cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True, f"✅ Removed from {group_name}"
    except Exception as e:
        return False, f"❌ Error removing from {group_name}: {str(e)}"

def user_has_regional_role(user_groups):
    """Check if user already has a regional role"""
    return any(group.startswith('Regio_') for group in user_groups)

def migrate_user_from_old_to_new(username, email, old_group, new_groups, current_groups):
    """Migrate a user from old _All group to new permission + region structure"""
    results = []
    
    # Add new permission groups
    for new_group in new_groups:
        if new_group not in current_groups:
            success, message = add_user_to_group(username, new_group)
            results.append(message)
        else:
            results.append(f"ℹ️  Already has {new_group}")
    
    # Add regional role if user doesn't have one
    if not user_has_regional_role(current_groups):
        # For most users, add Regio_All (full access)
        # Regional users should already have specific regional roles from auto-assignment
        success, message = add_user_to_group(username, 'Regio_All')
        results.append(message)
    else:
        results.append(f"ℹ️  Already has regional role")
    
    # Remove old group
    success, message = remove_user_from_group(username, old_group)
    results.append(message)
    
    return results

def main():
    """Complete the role migration"""
    print("🔄 Completing Role Migration to New Permission + Region Structure")
    print("=" * 80)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    migration_results = {
        'migrated_users': [],
        'already_migrated': [],
        'errors': []
    }
    
    # Process each old _All group
    for old_group, new_groups in OLD_TO_NEW_MAPPINGS.items():
        print(f"🔄 Processing {old_group} → {', '.join(new_groups)}...")
        
        users = get_users_in_group(old_group)
        
        if not users:
            print(f"   ℹ️  No users in {old_group}")
            continue
        
        print(f"   📊 Found {len(users)} users to migrate:")
        
        for user in users:
            email = user['email']
            username = user['username']
            current_groups = user['current_groups']
            
            print(f"\n   👤 {email}")
            print(f"      Current groups: {', '.join(current_groups)}")
            
            # Check if user already has the new permission groups
            has_new_permissions = all(new_group in current_groups for new_group in new_groups)
            has_regional_role = user_has_regional_role(current_groups)
            
            if has_new_permissions and has_regional_role:
                print(f"      ✅ Already migrated - has new permissions and regional role")
                migration_results['already_migrated'].append({
                    'email': email,
                    'old_group': old_group,
                    'status': 'already_migrated'
                })
                
                # Still remove from old group
                success, message = remove_user_from_group(username, old_group)
                print(f"      {message}")
            else:
                print(f"      🔄 Migrating...")
                
                try:
                    results = migrate_user_from_old_to_new(
                        username, email, old_group, new_groups, current_groups
                    )
                    
                    for result in results:
                        print(f"         {result}")
                    
                    migration_results['migrated_users'].append({
                        'email': email,
                        'old_group': old_group,
                        'new_groups': new_groups,
                        'results': results
                    })
                    
                except Exception as e:
                    error_msg = f"Error migrating {email}: {str(e)}"
                    print(f"         ❌ {error_msg}")
                    migration_results['errors'].append({
                        'email': email,
                        'error': error_msg
                    })
        
        print()
    
    # Summary
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    
    print(f"✅ Users migrated: {len(migration_results['migrated_users'])}")
    if migration_results['migrated_users']:
        for migration in migration_results['migrated_users']:
            print(f"   • {migration['email']}: {migration['old_group']} → {', '.join(migration['new_groups'])}")
    
    print(f"\nℹ️  Users already migrated: {len(migration_results['already_migrated'])}")
    if migration_results['already_migrated']:
        for migration in migration_results['already_migrated']:
            print(f"   • {migration['email']}: {migration['old_group']} (already had new structure)")
    
    print(f"\n❌ Errors: {len(migration_results['errors'])}")
    if migration_results['errors']:
        for error in migration_results['errors']:
            print(f"   • {error['email']}: {error['error']}")
    
    # Next steps
    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Verify migrated users have correct access")
    print(f"   2. Test frontend regional filtering with regional users")
    print(f"   3. Implement Task 1.4.3: Frontend Regional Filtering")
    print(f"   4. Delete empty old _All groups after verification")
    
    print(f"\n💡 NEW ROLE STRUCTURE ACTIVE:")
    print(f"   • Permission roles: Members_Read, Events_Read, Products_Read, etc.")
    print(f"   • Region roles: Regio_All (full access), Regio_Groningen/Drenthe, etc.")
    print(f"   • Users now have: Permission + Region combination")
    
    return len(migration_results['errors']) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)