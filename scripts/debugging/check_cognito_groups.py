#!/usr/bin/env python3
import boto3
import json
import os

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

try:
    # List all groups with pagination
    groups = []
    next_token = None
    
    while True:
        if next_token:
            response = cognito_client.list_groups(
                UserPoolId=USER_POOL_ID,
                NextToken=next_token,
                Limit=60  # Maximum allowed
            )
        else:
            response = cognito_client.list_groups(
                UserPoolId=USER_POOL_ID,
                Limit=60  # Maximum allowed
            )
        
        groups.extend(response.get('Groups', []))
        next_token = response.get('NextToken')
        
        if not next_token:
            break
    
    print(f'Total groups found: {len(groups)}')
    print()
    
    # Look for Regio_All specifically
    regio_all_found = False
    for group in groups:
        if group['GroupName'] == 'Regio_All':
            regio_all_found = True
            print('✅ Regio_All group found:')
            print(f'  Name: {group["GroupName"]}')
            print(f'  Description: {group.get("Description", "No description")}')
            print(f'  Created: {group.get("CreationDate", "Unknown")}')
            print()
            
            # Get members of this group
            try:
                members_response = cognito_client.list_users_in_group(
                    UserPoolId=USER_POOL_ID,
                    GroupName='Regio_All'
                )
                users = members_response.get('Users', [])
                print(f'  Members: {len(users)} users')
                for user in users[:5]:  # Show first 5 users
                    email = 'No email'
                    for attr in user.get('Attributes', []):
                        if attr['Name'] == 'email':
                            email = attr['Value']
                            break
                    print(f'    - {user["Username"]} ({email})')
                if len(users) > 5:
                    print(f'    ... and {len(users) - 5} more users')
            except Exception as e:
                print(f'  Error getting members: {e}')
            break
    
    if not regio_all_found:
        print('❌ Regio_All group NOT found')
        print()
        print('Available groups:')
        for group in sorted(groups, key=lambda x: x['GroupName']):
            print(f'  - {group["GroupName"]}')
    
except Exception as e:
    print(f'Error: {e}')