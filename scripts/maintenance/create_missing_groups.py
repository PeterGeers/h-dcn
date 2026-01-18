#!/usr/bin/env python3
"""
Create missing permission groups that were referenced in the migration
"""

import boto3
import json

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Missing groups that need to be created
MISSING_GROUPS = [
    {
        'name': 'Communication_Read',
        'description': 'Read access to communication functions'
    },
    {
        'name': 'Communication_CRUD',
        'description': 'Full CRUD access to communication functions'
    },
    {
        'name': 'Communication_Export',
        'description': 'Export access to communication functions'
    },
    {
        'name': 'System_CRUD',
        'description': 'Full CRUD access to system functions'
    }
]

def create_group(group_name, description):
    """Create a Cognito group"""
    try:
        cognito_client.create_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID,
            Description=description
        )
        return True, f"✅ Created group: {group_name}"
    except cognito_client.exceptions.GroupExistsException:
        return True, f"ℹ️  Group already exists: {group_name}"
    except Exception as e:
        return False, f"❌ Error creating group {group_name}: {str(e)}"

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
    """Create missing permission groups"""
    print("🏗️  Creating Missing Permission Groups")
    print("=" * 60)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Step 1: List current groups
    print("📋 STEP 1: Current groups...")
    current_groups = list_all_groups()
    
    permission_groups = [g for g in current_groups if not g.startswith('Regio_') and not g.startswith('hdcn') and not g.endswith('_All')]
    region_groups = [g for g in current_groups if g.startswith('Regio_')]
    
    print(f"   Permission groups: {len(permission_groups)}")
    for group in permission_groups:
        print(f"   • {group}")
    
    print(f"\n   Region groups: {len(region_groups)}")
    for group in region_groups:
        print(f"   • {group}")
    
    print()
    
    # Step 2: Create missing groups
    print("🏗️  STEP 2: Creating missing groups...")
    
    results = {
        'created': [],
        'already_existed': [],
        'errors': []
    }
    
    for group_info in MISSING_GROUPS:
        group_name = group_info['name']
        description = group_info['description']
        
        success, message = create_group(group_name, description)
        print(f"   {message}")
        
        if success:
            if "Created" in message:
                results['created'].append(group_name)
            else:
                results['already_existed'].append(group_name)
        else:
            results['errors'].append((group_name, message))
    
    print()
    
    # Step 3: Summary
    print("📊 GROUP CREATION SUMMARY")
    print("=" * 60)
    
    print(f"✅ Groups created: {len(results['created'])}")
    if results['created']:
        for group in results['created']:
            print(f"   • {group}")
    
    print(f"\nℹ️  Groups already existed: {len(results['already_existed'])}")
    if results['already_existed']:
        for group in results['already_existed']:
            print(f"   • {group}")
    
    print(f"\n❌ Errors: {len(results['errors'])}")
    if results['errors']:
        for group, error in results['errors']:
            print(f"   • {group}: {error}")
    
    # Step 4: Final group structure
    print(f"\n🎯 COMPLETE ROLE STRUCTURE:")
    
    final_groups = list_all_groups()
    final_permission_groups = [g for g in final_groups if not g.startswith('Regio_') and not g.startswith('hdcn') and not g.endswith('_All')]
    final_region_groups = [g for g in final_groups if g.startswith('Regio_')]
    
    print(f"   📋 Permission Groups ({len(final_permission_groups)}):")
    for group in sorted(final_permission_groups):
        print(f"      • {group}")
    
    print(f"\n   🌍 Region Groups ({len(final_region_groups)}):")
    for group in sorted(final_region_groups):
        print(f"      • {group}")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Re-run migration to assign users to newly created groups")
    print(f"   2. Verify all users have correct permission + region combinations")
    print(f"   3. Implement frontend regional filtering (Task 1.4.3)")
    print(f"   4. Test with regional users like secretaris.groningen-drenthe@h-dcn.nl")
    
    return len(results['errors']) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)