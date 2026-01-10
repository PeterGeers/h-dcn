#!/usr/bin/env python3
"""
Update regional user roles for secretaris.groningen-drenthe@h-dcn.nl
Replace broad access with specific regional access
"""

import boto3
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Target user
TARGET_USER_EMAIL = 'secretaris.groningen-drenthe@h-dcn.nl'

# Role changes for Groningen/Drenthe regional secretary
ROLE_CHANGES = {
    'remove': [
        'Members_Read',    # Too broad - replace with regional
        'Events_Read'      # Too broad - replace with regional
    ],
    'add': [
        'Members_Read_Groningen/Drenthe',  # Regional member access
        'Events_Read_Groningen/Drenthe'    # Regional event access
    ],
    'keep': [
        'hdcnLeden',                # Basic member role
        'Communication_Export', # Communication permissions
        'Communication_Read',   # Communication permissions  
        'Products_Read'         # Products (usually not regional)
    ]
}

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

def remove_user_from_group(username, group_name):
    """
    Remove user from a Cognito group
    
    Args:
        username (str): Cognito username
        group_name (str): Group name to remove from
        
    Returns:
        tuple: (success, message)
    """
    try:
        cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True, f"✅ Removed from group: {group_name}"
    except Exception as e:
        return False, f"❌ Error removing from group {group_name}: {str(e)}"

def add_user_to_group(username, group_name):
    """
    Add user to a Cognito group
    
    Args:
        username (str): Cognito username
        group_name (str): Group name to add to
        
    Returns:
        tuple: (success, message)
    """
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True, f"✅ Added to group: {group_name}"
    except Exception as e:
        return False, f"❌ Error adding to group {group_name}: {str(e)}"

def validate_group_exists(group_name):
    """
    Check if a Cognito group exists
    
    Args:
        group_name (str): Group name to check
        
    Returns:
        bool: True if group exists, False otherwise
    """
    try:
        cognito_client.get_group(
            GroupName=group_name,
            UserPoolId=USER_POOL_ID
        )
        return True
    except cognito_client.exceptions.ResourceNotFoundException:
        return False
    except Exception:
        return False

def main():
    """
    Update regional user roles
    """
    print("🔄 Updating Regional User Roles")
    print("=" * 60)
    print(f"Target User: {TARGET_USER_EMAIL}")
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Find the user
    print("🔍 Finding user...")
    success, username_or_error, current_groups = get_user_by_email(TARGET_USER_EMAIL)
    
    if not success:
        print(f"❌ {username_or_error}")
        return False
    
    username = username_or_error
    print(f"✅ Found user: {username}")
    print(f"   Current groups ({len(current_groups)}): {', '.join(current_groups)}")
    print()
    
    # Validate that new groups exist
    print("🔍 Validating new groups exist...")
    missing_groups = []
    for group in ROLE_CHANGES['add']:
        if not validate_group_exists(group):
            missing_groups.append(group)
    
    if missing_groups:
        print(f"❌ Missing groups: {', '.join(missing_groups)}")
        print("   Run create_regional_groups.py first!")
        return False
    
    print("✅ All new groups exist")
    print()
    
    # Show planned changes
    print("📋 PLANNED ROLE CHANGES:")
    print(f"   Remove: {', '.join(ROLE_CHANGES['remove'])}")
    print(f"   Add: {', '.join(ROLE_CHANGES['add'])}")
    print(f"   Keep: {', '.join(ROLE_CHANGES['keep'])}")
    print()
    
    # Perform role changes
    results = {
        'removed': [],
        'added': [],
        'errors': []
    }
    
    # Remove broad access roles
    print("🗑️  Removing broad access roles...")
    for group in ROLE_CHANGES['remove']:
        if group in current_groups:
            success, message = remove_user_from_group(username, group)
            if success:
                results['removed'].append(group)
            else:
                results['errors'].append(message)
            print(f"   {message}")
        else:
            print(f"   ℹ️  User not in group: {group}")
    
    print()
    
    # Add regional access roles
    print("➕ Adding regional access roles...")
    for group in ROLE_CHANGES['add']:
        if group not in current_groups:
            success, message = add_user_to_group(username, group)
            if success:
                results['added'].append(group)
            else:
                results['errors'].append(message)
            print(f"   {message}")
        else:
            print(f"   ℹ️  User already in group: {group}")
    
    print()
    
    # Get updated groups
    print("🔍 Verifying updated roles...")
    try:
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        updated_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
        print(f"✅ Updated groups ({len(updated_groups)}): {', '.join(sorted(updated_groups))}")
        
    except Exception as e:
        print(f"❌ Error getting updated groups: {str(e)}")
        updated_groups = []
    
    print()
    
    # Summary
    print("📊 ROLE UPDATE SUMMARY")
    print("=" * 60)
    print(f"✅ Roles removed: {len(results['removed'])}")
    print(f"✅ Roles added: {len(results['added'])}")
    print(f"❌ Errors: {len(results['errors'])}")
    
    if results['removed']:
        print(f"\n🗑️  REMOVED ROLES ({len(results['removed'])}):")
        for role in results['removed']:
            print(f"   • {role}")
    
    if results['added']:
        print(f"\n➕ ADDED ROLES ({len(results['added'])}):")
        for role in results['added']:
            print(f"   • {role}")
    
    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"   • {error}")
    
    # Validate expected final state
    expected_groups = set(ROLE_CHANGES['keep'] + ROLE_CHANGES['add'])
    actual_groups = set(updated_groups)
    
    print(f"\n🎯 FINAL VALIDATION:")
    print(f"   Expected groups: {len(expected_groups)}")
    print(f"   Actual groups: {len(actual_groups)}")
    
    missing = expected_groups - actual_groups
    extra = actual_groups - expected_groups
    
    if missing:
        print(f"   ⚠️  Missing expected groups: {', '.join(missing)}")
    
    if extra:
        print(f"   ℹ️  Extra groups: {', '.join(extra)}")
    
    success = len(results['errors']) == 0 and len(missing) == 0
    
    if success:
        print(f"\n🎉 SUCCESS: Regional roles updated successfully!")
        print(f"   User {TARGET_USER_EMAIL} now has regional access to Groningen/Drenthe only")
        print(f"   • Members: Members_Read_Groningen/Drenthe")
        print(f"   • Events: Events_Read_Groningen/Drenthe") 
        print(f"   • Products: Products_Read (not regional)")
        print(f"   • Communication: Full access (Communication_Read, Communication_Export)")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: Some issues occurred")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)