#!/usr/bin/env python3
import boto3

cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

# Get all users
response = cognito_client.list_users(UserPoolId=USER_POOL_ID)
users = response.get('Users', [])

print(f'Total users: {len(users)}')
print()

# Look for users who might need national access
national_candidates = []

for user in users:
    username = user['Username']
    
    # Get user's email
    email = 'No email'
    for attr in user.get('Attributes', []):
        if attr['Name'] == 'email':
            email = attr['Value']
            break
    
    # Get user's groups
    try:
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
        
        # Check if user has management roles but no regional assignment
        has_management = any(role in groups for role in ['Members_CRUD', 'System_User_Management'])
        has_region = any(role.startswith('Regio_') for role in groups)
        
        if has_management and not has_region:
            national_candidates.append({
                'username': username,
                'email': email,
                'groups': groups
            })
            
    except Exception as e:
        print(f'Error getting groups for {username}: {e}')

print('Users with management roles but no regional assignment:')
print('(These might need Regio_All access)')
print()

for candidate in national_candidates:
    print(f'  {candidate["email"]} ({candidate["username"]})')
    print(f'    Groups: {", ".join(candidate["groups"])}')
    print()

print(f'Found {len(national_candidates)} candidates for Regio_All group')