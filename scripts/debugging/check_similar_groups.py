#!/usr/bin/env python3
import boto3

cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
groups = response.get('Groups', [])

print('Groups containing "All":')
all_groups = []
for group in groups:
    if 'All' in group['GroupName'] or 'all' in group['GroupName']:
        all_groups.append(group['GroupName'])
        print(f'  - {group["GroupName"]}')

if not all_groups:
    print('  None found')

print()
print('Groups containing "Regio":')
regio_groups = []
for group in groups:
    if 'Regio' in group['GroupName']:
        regio_groups.append(group['GroupName'])
        print(f'  - {group["GroupName"]}')

if not regio_groups:
    print('  None found')

print()
print(f'Total groups: {len(groups)}')