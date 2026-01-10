#!/usr/bin/env python3
"""
Create missing export roles for consistency
"""

import boto3

cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def main():
    try:
        response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
        all_groups = [group['GroupName'] for group in response['Groups']]
        
        # Check for export roles
        export_roles_needed = ['Members_Export', 'Events_Export', 'Products_Export']
        export_roles_existing = [g for g in all_groups if g.endswith('_Export')]
        
        print('Export roles found:')
        for group in sorted(export_roles_existing):
            print(f'  ✅ {group}')
        
        print('\nExport roles needed but missing:')
        for role in export_roles_needed:
            if role not in all_groups:
                print(f'  ❌ {role}')
                # Create it
                data_type = role.split('_')[0].lower()
                cognito_client.create_group(
                    GroupName=role,
                    UserPoolId=USER_POOL_ID,
                    Description=f'Export {data_type} data permissions'
                )
                print(f'  ✅ Created {role}')
            else:
                print(f'  ✅ {role} already exists')
        
        # Final summary
        print('\n📊 FINAL COMPLETE ROLE STRUCTURE:')
        response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
        all_groups = sorted([group['GroupName'] for group in response['Groups']])
        
        categories = {
            'Members': [g for g in all_groups if g.startswith('Members_')],
            'Events': [g for g in all_groups if g.startswith('Events_')],
            'Products': [g for g in all_groups if g.startswith('Products_')],
            'Communication': [g for g in all_groups if g.startswith('Communication_')],
            'System': [g for g in all_groups if g.startswith('System_')],
            'Regions': [g for g in all_groups if g.startswith('Regio_')]
        }
        
        for category, groups in categories.items():
            print(f'   {category} ({len(groups)}): {groups}')
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    main()