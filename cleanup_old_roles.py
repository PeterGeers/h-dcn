#!/usr/bin/env python3
"""
Clean up old _All roles that are no longer needed after migration
"""

import boto3
import json

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Old roles that should be deleted (users already migrated)
# NOTE: These deprecated _All roles have been removed from production
OLD_ROLES_TO_DELETE = [
    # DEPRECATED ROLES - ALREADY REMOVED FROM PRODUCTION
    'Members_CRUD_All',
    'Members_Read_All', 
    'Events_CRUD_All',
    'Events_Read_All',
    'Products_CRUD_All',
    'Products_Read_All',
    'Communication_CRUD_All',
    'Communication_Read_All',
    'Communication_Export_All',
    'System_CRUD_All'
]

def get_users_in_group(group_name):
    """Get count of users in a group"""
    try:
        users = []
        paginator = cognito_client.get_paginator('list_users_in_group')
        
        for page in paginator.paginate(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        ):
            users.extend(page['Users'])
        
        return len(users), [user['Username'] for user in users]
    except Exception as e:
        return 0, []

def delete_group_if_empty(group_name):
    """Delete a group if it has no users"""
    try:
        user_count, usernames = get_users_in_group(group_name)
        
        if user_count > 0:
            return False, f"⚠️  Group '{group_name}' has {user_count} users - cannot delete"
        
        # Delete empty group
        cognito_client.delete_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID
        )
        
        return True, f"✅ Deleted empty group '{group_name}'"
        
    except cognito_client.exceptions.ResourceNotFoundException:
        return True, f"ℹ️  Group '{group_name}' does not exist"
    except Exception as e:
        return False, f"❌ Error deleting group '{group_name}': {str(e)}"

def list_all_groups():
    """List all current groups"""
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

def main():
    """Clean up old _All roles"""
    print("🧹 Cleaning Up Old _All Roles")
    print("=" * 60)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Step 1: List current groups
    print("📋 STEP 1: Current groups...")
    all_groups = list_all_groups()
    
    old_groups = [g for g in all_groups if g in OLD_ROLES_TO_DELETE]
    new_groups = [g for g in all_groups if not g.endswith('_All') and not g.startswith('hdcn')]
    region_groups = [g for g in all_groups if g.startswith('Regio_')]
    
    print(f"   📊 Group Analysis:")
    print(f"   • Old _All groups to delete: {len(old_groups)}")
    print(f"   • New permission groups: {len(new_groups)}")
    print(f"   • Region groups: {len(region_groups)}")
    print()
    
    # Step 2: Check each old group for users
    print("🔍 STEP 2: Checking old groups for users...")
    
    groups_with_users = []
    empty_groups = []
    
    for group in old_groups:
        user_count, usernames = get_users_in_group(group)
        print(f"   📊 {group}: {user_count} users")
        
        if user_count > 0:
            groups_with_users.append((group, user_count, usernames))
            print(f"      ⚠️  Has users: {', '.join(usernames[:3])}{' ...' if len(usernames) > 3 else ''}")
        else:
            empty_groups.append(group)
            print(f"      ✅ Empty - can be deleted")
    
    print()
    
    # Step 3: Delete empty groups
    print("🗑️  STEP 3: Deleting empty old groups...")
    
    deletion_results = {
        'deleted': [],
        'errors': []
    }
    
    for group in empty_groups:
        success, message = delete_group_if_empty(group)
        print(f"   {message}")
        
        if success and "Deleted" in message:
            deletion_results['deleted'].append(group)
        elif not success:
            deletion_results['errors'].append((group, message))
    
    print()
    
    # Step 4: Summary
    print("📊 CLEANUP SUMMARY")
    print("=" * 60)
    
    print(f"✅ Groups deleted: {len(deletion_results['deleted'])}")
    if deletion_results['deleted']:
        for group in deletion_results['deleted']:
            print(f"   • {group}")
    
    print(f"\n⚠️  Groups with users (cannot delete): {len(groups_with_users)}")
    if groups_with_users:
        for group, count, usernames in groups_with_users:
            print(f"   • {group} ({count} users)")
            print(f"     Users: {', '.join(usernames[:5])}{' ...' if len(usernames) > 5 else ''}")
    
    print(f"\n❌ Errors: {len(deletion_results['errors'])}")
    if deletion_results['errors']:
        for group, error in deletion_results['errors']:
            print(f"   • {group}: {error}")
    
    # Step 5: Final role structure
    print(f"\n🎯 FINAL ROLE STRUCTURE:")
    
    final_groups = list_all_groups()
    
    # Member roles
    member_roles = [g for g in final_groups if g.startswith('Members_')]
    print(f"   👥 Member Roles ({len(member_roles)}):")
    for role in sorted(member_roles):
        print(f"      • {role}")
    
    # Event roles  
    event_roles = [g for g in final_groups if g.startswith('Events_')]
    print(f"   📅 Event Roles ({len(event_roles)}):")
    for role in sorted(event_roles):
        print(f"      • {role}")
    
    # Product roles
    product_roles = [g for g in final_groups if g.startswith('Products_')]
    print(f"   📦 Product Roles ({len(product_roles)}):")
    for role in sorted(product_roles):
        print(f"      • {role}")
    
    # Region roles
    region_roles = [g for g in final_groups if g.startswith('Regio_')]
    print(f"   🌍 Region Roles ({len(region_roles)}):")
    for role in sorted(region_roles):
        print(f"      • {role}")
    
    print(f"\n💡 NEXT STEPS:")
    if groups_with_users:
        print(f"   1. ⚠️  Some old groups still have users - migration may be incomplete")
        print(f"   2. Check why these users weren't migrated:")
        for group, count, usernames in groups_with_users:
            print(f"      • {group}: {', '.join(usernames[:3])}")
        print(f"   3. Complete migration for remaining users")
        print(f"   4. Then re-run this cleanup script")
    else:
        print(f"   1. ✅ All old groups cleaned up successfully")
        print(f"   2. Update codebase to use new role names")
        print(f"   3. Test authentication with new roles")
        print(f"   4. Deploy updated backend handlers")
    
    return len(deletion_results['errors']) == 0 and len(groups_with_users) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)