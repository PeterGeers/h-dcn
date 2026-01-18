#!/usr/bin/env python3
"""
Check what users were assigned to Regio_Duitsland and verify their email patterns
"""

import boto3
import json

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def get_users_in_group(group_name):
    """
    Get all users in a specific group with their email addresses
    
    Args:
        group_name (str): Name of the group
        
    Returns:
        list: List of user dictionaries with username and email
    """
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
                
                users.append({
                    'username': user['Username'],
                    'email': email,
                    'status': user.get('UserStatus', 'Unknown')
                })
        
        return users
    except Exception as e:
        print(f"Error getting users in group {group_name}: {str(e)}")
        return []

def main():
    """
    Check users assigned to Regio_Duitsland
    """
    print("🔍 Checking Users Assigned to Regio_Duitsland")
    print("=" * 60)
    
    # Get users in Regio_Duitsland
    duitsland_users = get_users_in_group('Regio_Duitsland')
    
    print(f"📊 Found {len(duitsland_users)} users in Regio_Duitsland:")
    print()
    
    correct_pattern_users = []
    incorrect_pattern_users = []
    
    for user in duitsland_users:
        email = user['email']
        username = user['username']
        status = user['status']
        
        print(f"👤 {email} ({username}) - Status: {status}")
        
        # Check if email follows correct pattern
        if email and email.endswith('@h-dcn.nl'):
            # Check if it has 'duitsland' before @h-dcn.nl
            local_part = email.split('@')[0]
            if 'duitsland' in local_part.lower():
                correct_pattern_users.append(user)
                print(f"   ✅ Correct pattern: ends with duitsland@h-dcn.nl")
            else:
                incorrect_pattern_users.append(user)
                print(f"   ❌ Incorrect pattern: doesn't contain 'duitsland' in local part")
        else:
            incorrect_pattern_users.append(user)
            print(f"   ❌ Incorrect pattern: doesn't end with @h-dcn.nl")
        
        print()
    
    # Summary
    print("📊 PATTERN ANALYSIS SUMMARY")
    print("=" * 60)
    
    print(f"✅ Users with correct pattern (*duitsland@h-dcn.nl): {len(correct_pattern_users)}")
    if correct_pattern_users:
        for user in correct_pattern_users:
            print(f"   • {user['email']}")
    
    print(f"\n❌ Users with incorrect pattern: {len(incorrect_pattern_users)}")
    if incorrect_pattern_users:
        for user in incorrect_pattern_users:
            print(f"   • {user['email']} - Should be removed from Regio_Duitsland")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if incorrect_pattern_users:
        print(f"   1. Remove incorrectly assigned users from Regio_Duitsland:")
        for user in incorrect_pattern_users:
            print(f"      • Remove {user['email']} from Regio_Duitsland")
        
        print(f"   2. Update email pattern matching to be more strict:")
        print(f"      • Only match emails ending with 'duitsland@h-dcn.nl'")
        print(f"      • Remove generic 'germany' and 'deutschland' patterns")
    
    if correct_pattern_users:
        print(f"   3. Keep correctly assigned users:")
        for user in correct_pattern_users:
            print(f"      • Keep {user['email']} in Regio_Duitsland")
    
    return len(incorrect_pattern_users) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)