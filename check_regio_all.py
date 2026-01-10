#!/usr/bin/env python3
"""
Check if Regio_All group exists and who's in it
"""

import boto3

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def main():
    try:
        # Check if Regio_All group exists
        response = cognito_client.get_group(
            GroupName='Regio_All',
            UserPoolId=USER_POOL_ID
        )
        
        print('✅ Regio_All group exists')
        print(f'   Description: {response.get("Description", "No description")}')
        print(f'   Precedence: {response.get("Precedence", "Not set")}')
        
        # Check how many users are in this group
        users_response = cognito_client.list_users_in_group(
            UserPoolId=USER_POOL_ID,
            GroupName='Regio_All'
        )
        
        users = users_response.get('Users', [])
        print(f'   Users in group: {len(users)}')
        
        if users:
            print('   User details:')
            for user in users:
                # Get user email
                email = 'Unknown'
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        email = attr['Value']
                        break
                print(f'     • {user["Username"]} ({email})')
        else:
            print('   No users in Regio_All group')
        
    except cognito_client.exceptions.ResourceNotFoundException:
        print('❌ Regio_All group does not exist')
    except Exception as e:
        print(f'❌ Error checking Regio_All group: {str(e)}')

if __name__ == "__main__":
    main()