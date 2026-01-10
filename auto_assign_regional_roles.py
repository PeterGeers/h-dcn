#!/usr/bin/env python3
"""
Auto-assign Regio_ roles to users based on email address patterns
"""

import boto3
import json
import re
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Email pattern to region mapping
EMAIL_REGION_PATTERNS = {
    # Pattern in email -> Regio role to assign
    'noord-holland': 'Regio_Noord-Holland',
    'noordholland': 'Regio_Noord-Holland',
    'zuid-holland': 'Regio_Zuid-Holland',
    'zuidholland': 'Regio_Zuid-Holland',
    'friesland': 'Regio_Friesland',
    'utrecht': 'Regio_Utrecht',
    'oost': 'Regio_Oost',
    'limburg': 'Regio_Limburg',
    'groningen-drenthe': 'Regio_Groningen/Drenthe',
    'groningen': 'Regio_Groningen/Drenthe',
    'drenthe': 'Regio_Groningen/Drenthe',
    'brabant-zeeland': 'Regio_Brabant/Zeeland',
    'brabant': 'Regio_Brabant/Zeeland',
    'zeeland': 'Regio_Brabant/Zeeland',
    'duitsland': 'Regio_Duitsland',
    'germany': 'Regio_Duitsland',
    'deutschland': 'Regio_Duitsland'
}

def get_all_users():
    """
    Get all users from Cognito with their email addresses and current groups
    
    Returns:
        list: List of user dictionaries with username, email, and groups
    """
    users = []
    
    try:
        paginator = cognito_client.get_paginator('list_users')
        
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for user in page['Users']:
                # Extract email
                email = None
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        email = attr['Value']
                        break
                
                if email:
                    # Get user's current groups
                    try:
                        groups_response = cognito_client.admin_list_groups_for_user(
                            UserPoolId=USER_POOL_ID,
                            Username=user['Username']
                        )
                        
                        current_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
                        
                        users.append({
                            'username': user['Username'],
                            'email': email,
                            'groups': current_groups,
                            'status': user.get('UserStatus', 'Unknown')
                        })
                        
                    except Exception as e:
                        print(f"   ⚠️  Error getting groups for {email}: {str(e)}")
        
        return users
        
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return []

def detect_region_from_email(email):
    """
    Detect which region a user belongs to based on their email address
    
    Args:
        email (str): User's email address
        
    Returns:
        str or None: Regio role name if detected, None otherwise
    """
    email_lower = email.lower()
    
    # Check each pattern
    for pattern, region_role in EMAIL_REGION_PATTERNS.items():
        if pattern in email_lower:
            return region_role
    
    return None

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
        return True, f"✅ Added to {group_name}"
    except Exception as e:
        return False, f"❌ Error adding to {group_name}: {str(e)}"

def main():
    """
    Auto-assign regional roles based on email patterns
    """
    print("🏷️  Auto-Assigning Regional Roles Based on Email Patterns")
    print("=" * 70)
    print(f"User Pool ID: {USER_POOL_ID}")
    print()
    
    # Step 1: Get all users
    print("👥 STEP 1: Getting all users...")
    users = get_all_users()
    print(f"   Found {len(users)} users")
    print()
    
    # Step 2: Analyze email patterns
    print("🔍 STEP 2: Analyzing email patterns for regional assignment...")
    
    results = {
        'assigned': [],
        'already_has_region': [],
        'no_pattern_match': [],
        'errors': []
    }
    
    for user in users:
        email = user['email']
        username = user['username']
        current_groups = user['groups']
        
        # Check if user already has a Regio_ role
        existing_region_roles = [g for g in current_groups if g.startswith('Regio_')]
        
        if existing_region_roles:
            results['already_has_region'].append({
                'email': email,
                'existing_roles': existing_region_roles
            })
            print(f"   ℹ️  {email} already has region role(s): {', '.join(existing_region_roles)}")
            continue
        
        # Detect region from email
        detected_region = detect_region_from_email(email)
        
        if detected_region:
            print(f"   🎯 {email} → {detected_region}")
            
            # Add the regional role
            success, message = add_user_to_group(username, detected_region)
            
            if success:
                results['assigned'].append({
                    'email': email,
                    'region_role': detected_region
                })
                print(f"      {message}")
            else:
                results['errors'].append({
                    'email': email,
                    'error': message
                })
                print(f"      {message}")
        else:
            results['no_pattern_match'].append(email)
            print(f"   ❓ {email} - no regional pattern detected")
    
    print()
    
    # Step 3: Summary
    print("📊 AUTO-ASSIGNMENT SUMMARY")
    print("=" * 70)
    
    print(f"✅ New regional roles assigned: {len(results['assigned'])}")
    if results['assigned']:
        print("   Assignments made:")
        for assignment in results['assigned']:
            print(f"   • {assignment['email']} → {assignment['region_role']}")
    
    print(f"\nℹ️  Users already had regional roles: {len(results['already_has_region'])}")
    if results['already_has_region']:
        print("   Existing assignments:")
        for existing in results['already_has_region']:
            print(f"   • {existing['email']} → {', '.join(existing['existing_roles'])}")
    
    print(f"\n❓ Users with no regional pattern: {len(results['no_pattern_match'])}")
    if results['no_pattern_match']:
        print("   No pattern detected:")
        for email in results['no_pattern_match'][:10]:  # Show first 10
            print(f"   • {email}")
        if len(results['no_pattern_match']) > 10:
            print(f"   ... and {len(results['no_pattern_match']) - 10} more")
    
    print(f"\n❌ Errors: {len(results['errors'])}")
    if results['errors']:
        for error in results['errors']:
            print(f"   • {error['email']}: {error['error']}")
    
    # Step 4: Pattern analysis
    print(f"\n🔍 EMAIL PATTERN ANALYSIS:")
    print(f"   Patterns used for detection:")
    for pattern, region in EMAIL_REGION_PATTERNS.items():
        assigned_count = len([a for a in results['assigned'] if a['region_role'] == region])
        existing_count = len([e for e in results['already_has_region'] 
                            if region in e['existing_roles']])
        total = assigned_count + existing_count
        if total > 0:
            print(f"   • '{pattern}' → {region} ({total} users)")
    
    # Step 5: Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if results['no_pattern_match']:
        print(f"   1. Review users with no regional pattern:")
        print(f"      • Consider adding them to 'Regio_All' for full access")
        print(f"      • Or manually assign specific regional roles")
    
    if results['assigned']:
        print(f"   2. Verify new assignments are correct:")
        print(f"      • Test login with regional users")
        print(f"      • Confirm they see only their region's data")
    
    print(f"   3. Next steps:")
    print(f"      • Implement frontend regional filtering")
    print(f"      • Test with assigned regional users")
    print(f"      • Migrate remaining _All role users")
    
    return len(results['errors']) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)