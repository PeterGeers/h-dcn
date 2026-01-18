#!/usr/bin/env python3
"""
Implement simplified regional role system for H-DCN
- Delete the 27 complex regional groups we just created
- Create new simplified permission + region role structure
- Update the target user with new roles
"""

import boto3
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Target user for testing
TARGET_USER_EMAIL = 'secretaris.groningen-drenthe@h-dcn.nl'

# Define the 9 H-DCN regions
REGIONS = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Brabant/Zeeland',
    'Duitsland'
]

# Old complex groups to delete (the 27 we just created)
OLD_GROUPS_TO_DELETE = []
for data_type in ['Members', 'Events', 'Products']:
    for region in REGIONS:
        OLD_GROUPS_TO_DELETE.append(f"{data_type}_Read_{region}")

# New simplified role structure
NEW_PERMISSION_ROLES = {
    'Members_Read': {
        'description': 'Permission to read member data',
        'precedence': 210
    },
    'Members_CRUD': {
        'description': 'Permission to create, read, update, delete member data',
        'precedence': 200
    },
    'Events_Read': {
        'description': 'Permission to read event data',
        'precedence': 310
    },
    'Events_CRUD': {
        'description': 'Permission to create, read, update, delete event data',
        'precedence': 300
    },
    'Products_Read': {
        'description': 'Permission to read product data',
        'precedence': 410
    },
    'Products_CRUD': {
        'description': 'Permission to create, read, update, delete product data',
        'precedence': 400
    }
}

NEW_REGION_ROLES = {
    'Regio_All': {
        'description': 'Access to all regions',
        'precedence': 100
    }
}

# Add individual region roles
for i, region in enumerate(REGIONS):
    NEW_REGION_ROLES[f'Regio_{region}'] = {
        'description': f'Access to {region} region only',
        'precedence': 110 + i
    }

def delete_cognito_group(group_name):
    """
    Delete a Cognito group if it exists
    
    Args:
        group_name (str): Name of the group to delete
    
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if group exists first
        try:
            cognito_client.get_group(
                GroupName=group_name,
                UserPoolId=USER_POOL_ID
            )
        except cognito_client.exceptions.ResourceNotFoundException:
            return True, f"Group '{group_name}' doesn't exist (already deleted)"
        
        # Delete the group
        cognito_client.delete_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID
        )
        
        return True, f"✅ Deleted group '{group_name}'"
        
    except Exception as e:
        return False, f"❌ Error deleting group '{group_name}': {str(e)}"

def create_cognito_group(group_name, description, precedence):
    """
    Create a Cognito group if it doesn't exist
    
    Args:
        group_name (str): Name of the group to create
        description (str): Description of the group
        precedence (int): Group precedence (lower = higher priority)
    
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if group already exists
        try:
            response = cognito_client.get_group(
                GroupName=group_name,
                UserPoolId=USER_POOL_ID
            )
            return True, f"Group '{group_name}' already exists"
        except cognito_client.exceptions.ResourceNotFoundException:
            # Group doesn't exist, create it
            pass
        
        # Create the group
        response = cognito_client.create_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID,
            Description=description,
            Precedence=precedence
        )
        
        return True, f"✅ Created group '{group_name}'"
        
    except Exception as e:
        return False, f"❌ Error creating group '{group_name}': {str(e)}"

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

def update_user_roles(username, remove_roles, add_roles):
    """
    Update user's Cognito group memberships
    
    Args:
        username (str): Cognito username
        remove_roles (list): Roles to remove
        add_roles (list): Roles to add
        
    Returns:
        tuple: (success, results_dict)
    """
    results = {
        'removed': [],
        'added': [],
        'errors': []
    }
    
    # Remove roles
    for role in remove_roles:
        try:
            cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=role
            )
            results['removed'].append(role)
        except Exception as e:
            results['errors'].append(f"Error removing {role}: {str(e)}")
    
    # Add roles
    for role in add_roles:
        try:
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=role
            )
            results['added'].append(role)
        except Exception as e:
            results['errors'].append(f"Error adding {role}: {str(e)}")
    
    return len(results['errors']) == 0, results

def main():
    """
    Implement simplified regional role system
    """
    print("🔄 Implementing Simplified Regional Role System")
    print("=" * 70)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Step 1: Delete old complex groups
    print("🗑️  STEP 1: Deleting old complex regional groups...")
    delete_results = {
        'deleted': [],
        'not_found': [],
        'errors': []
    }
    
    for group_name in OLD_GROUPS_TO_DELETE:
        success, message = delete_cognito_group(group_name)
        if success:
            if "doesn't exist" in message:
                delete_results['not_found'].append(group_name)
            else:
                delete_results['deleted'].append(group_name)
        else:
            delete_results['errors'].append((group_name, message))
        print(f"   {message}")
    
    print(f"\n   📊 Deletion Summary:")
    print(f"   ✅ Deleted: {len(delete_results['deleted'])}")
    print(f"   ℹ️  Not found: {len(delete_results['not_found'])}")
    print(f"   ❌ Errors: {len(delete_results['errors'])}")
    print()
    
    # Step 2: Create new simplified permission roles
    print("🔧 STEP 2: Creating new permission roles...")
    permission_results = {
        'created': [],
        'existing': [],
        'errors': []
    }
    
    for role_name, config in NEW_PERMISSION_ROLES.items():
        success, message = create_cognito_group(
            role_name, 
            config['description'], 
            config['precedence']
        )
        
        if success:
            if "already exists" in message:
                permission_results['existing'].append(role_name)
            else:
                permission_results['created'].append(role_name)
        else:
            permission_results['errors'].append((role_name, message))
        print(f"   {message}")
    
    print(f"\n   📊 Permission Roles Summary:")
    print(f"   ✅ Created: {len(permission_results['created'])}")
    print(f"   ℹ️  Existing: {len(permission_results['existing'])}")
    print(f"   ❌ Errors: {len(permission_results['errors'])}")
    print()
    
    # Step 3: Create new region roles
    print("🌍 STEP 3: Creating new region roles...")
    region_results = {
        'created': [],
        'existing': [],
        'errors': []
    }
    
    for role_name, config in NEW_REGION_ROLES.items():
        success, message = create_cognito_group(
            role_name, 
            config['description'], 
            config['precedence']
        )
        
        if success:
            if "already exists" in message:
                region_results['existing'].append(role_name)
            else:
                region_results['created'].append(role_name)
        else:
            region_results['errors'].append((role_name, message))
        print(f"   {message}")
    
    print(f"\n   📊 Region Roles Summary:")
    print(f"   ✅ Created: {len(region_results['created'])}")
    print(f"   ℹ️  Existing: {len(region_results['existing'])}")
    print(f"   ❌ Errors: {len(region_results['errors'])}")
    print()
    
    # Step 4: Update target user with new roles
    print(f"👤 STEP 4: Updating user {TARGET_USER_EMAIL}...")
    
    # Find user
    success, username_or_error, current_groups = get_user_by_email(TARGET_USER_EMAIL)
    if not success:
        print(f"   ❌ {username_or_error}")
        return False
    
    username = username_or_error
    print(f"   ✅ Found user: {username}")
    print(f"   Current groups: {', '.join(current_groups)}")
    
    # Define role changes for regional secretary
    roles_to_remove = [
        'Members_Read',  # Replace with Members_Read + Regio_Groningen/Drenthe
        'Events_Read'    # Replace with Events_Read + Regio_Groningen/Drenthe
    ]
    
    roles_to_add = [
        'Members_Read',              # Permission to read members
        'Events_Read',               # Permission to read events  
        'Products_Read',             # Permission to read products
        'Regio_Groningen/Drenthe'   # Regional access restriction
    ]
    
    # Only remove/add roles that need changing
    actual_remove = [role for role in roles_to_remove if role in current_groups]
    actual_add = [role for role in roles_to_add if role not in current_groups]
    
    print(f"   Will remove: {', '.join(actual_remove) if actual_remove else 'None'}")
    print(f"   Will add: {', '.join(actual_add) if actual_add else 'None'}")
    
    if actual_remove or actual_add:
        success, user_results = update_user_roles(username, actual_remove, actual_add)
        
        print(f"\n   📊 User Update Results:")
        print(f"   ✅ Removed: {', '.join(user_results['removed']) if user_results['removed'] else 'None'}")
        print(f"   ✅ Added: {', '.join(user_results['added']) if user_results['added'] else 'None'}")
        if user_results['errors']:
            print(f"   ❌ Errors: {', '.join(user_results['errors'])}")
    else:
        print(f"   ℹ️  No role changes needed")
    
    print()
    
    # Final summary
    print("🎯 FINAL SUMMARY")
    print("=" * 70)
    
    total_new_roles = len(NEW_PERMISSION_ROLES) + len(NEW_REGION_ROLES)
    total_created = len(permission_results['created']) + len(region_results['created'])
    total_existing = len(permission_results['existing']) + len(region_results['existing'])
    
    print(f"✅ Old complex system: {len(delete_results['deleted'])} groups deleted")
    print(f"✅ New simplified system: {total_created} groups created, {total_existing} already existed")
    print(f"✅ Total new role structure: {total_new_roles} groups")
    print(f"   • {len(NEW_PERMISSION_ROLES)} permission roles (Members_Read, Events_Read, etc.)")
    print(f"   • {len(NEW_REGION_ROLES)} region roles (Regio_All, Regio_Groningen/Drenthe, etc.)")
    
    print(f"\n🎉 NEW ROLE SYSTEM BENEFITS:")
    print(f"   • Reduced from 30+ roles to {total_new_roles} roles")
    print(f"   • Flexible permission + region combinations")
    print(f"   • Easy to understand and maintain")
    print(f"   • Scalable for new permissions or regions")
    
    print(f"\n👤 USER EXAMPLE: {TARGET_USER_EMAIL}")
    print(f"   New roles: Members_Read + Events_Read + Products_Read + Regio_Groningen/Drenthe")
    print(f"   Access: Can read member/event data from Groningen/Drenthe region only")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)