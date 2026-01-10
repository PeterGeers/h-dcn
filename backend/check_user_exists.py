#!/usr/bin/env python3
"""
Check if user exists in Cognito and add to verzoek_lid group
"""

import boto3
from botocore.exceptions import ClientError

def check_and_add_user():
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    email = 'peter.geers@live.nl'
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # First, try to get user info
        user_response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        print(f"✅ User {email} exists in Cognito")
        print(f"   Status: {user_response['UserStatus']}")
        print(f"   Username: {user_response['Username']}")
        
        # Now add to verzoek_lid group
        try:
            cognito_client.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=email,
                GroupName='verzoek_lid'
            )
            print(f"✅ Successfully added {email} to verzoek_lid group")
            
        except Exception as group_error:
            print(f"❌ Error adding to group: {str(group_error)}")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            print(f"❌ User {email} not found in User Pool {user_pool_id}")
        else:
            print(f"❌ Error: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    check_and_add_user()