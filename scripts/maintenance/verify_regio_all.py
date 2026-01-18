#!/usr/bin/env python3
import boto3
import json

cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

try:
    # List all groups with pagination to ensure we get all groups
    all_groups = []
    paginator = cognito_client.get_paginator('list_groups')
    
    for page in paginator.paginate(UserPoolId=USER_POOL_ID):
        all_groups.extend(page.get('Groups', []))
    
    print(f'Total groups found (with pagination): {len(all_groups)}')
    print()
    
    # Look for Regio_All specifically
    regio_all_group = None
    for group in all_groups:
        if group['GroupName'] == 'Regio_All':
            regio_all_group = group
            break
    
    if regio_all_group:
        print('✅ Regio_All group found:')
        print(f'  Name: {regio_all_group["GroupName"]}')
        print(f'  Description: {regio_all_group.get("Description", "No description")}')
        print(f'  Created: {regio_all_group.get("CreationDate", "Unknown")}')
        
        # Get members
        try:
            members_response = cognito_client.list_users_in_group(
                UserPoolId=USER_POOL_ID,
                GroupName='Regio_All'
            )
            users = members_response.get('Users', [])
            print(f'  Members: {len(users)} users')
            
            for user in users:
                email = 'No email'
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        email = attr['Value']
                        break
                print(f'    - {user["Username"]} ({email})')
                
        except Exception as e:
            print(f'  Error getting members: {e}')
    else:
        print('❌ Regio_All group NOT found')
        
        # Show all regional groups
        print('\nRegional groups found:')
        regional_groups = [g for g in all_groups if g['GroupName'].startswith('Regio_')]
        for group in sorted(regional_groups, key=lambda x: x['GroupName']):
            print(f'  - {group["GroupName"]}')
        
        print(f'\nTotal regional groups: {len(regional_groups)}')
        print('Expected: 9 regional groups + Regio_All = 10 total')
    
    # Also check if there are any groups with similar names
    print('\nAll groups containing "All" or "all":')
    all_containing_groups = [g for g in all_groups if 'All' in g['GroupName'] or 'all' in g['GroupName']]
    if all_containing_groups:
        for group in all_containing_groups:
            print(f'  - {group["GroupName"]}')
    else:
        print('  None found')

except Exception as e:
    print(f'Error: {e}')