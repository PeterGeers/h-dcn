#!/usr/bin/env python3
"""
Script to create the Verzoek_lid Cognito User Pool group
"""

import boto3
import os
from botocore.exceptions import ClientError

def create_verzoek_lid_group():
    """Create the Verzoek_lid group in Cognito User Pool"""
    
    # Get User Pool ID from environment or use default
    user_pool_id = os.environ.get('USER_POOL_ID', 'eu-west-1_OAT3oPCIm')
    
    # Initialize Cognito client
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Create the Verzoek_lid group
        response = cognito_client.create_group(
            GroupName='Verzoek_lid',
            UserPoolId=user_pool_id,
            Description='Membership applicants who have not been approved yet',
            Precedence=100  # Lower precedence than hdcnLeden (which should be higher priority)
        )
        
        print(f"✅ Successfully created Verzoek_lid group in User Pool {user_pool_id}")
        print(f"Group details: {response['Group']}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'GroupExistsException':
            print(f"ℹ️  Group 'Verzoek_lid' already exists in User Pool {user_pool_id}")
        else:
            print(f"❌ Error creating group: {e.response['Error']['Message']}")
            raise
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise

def list_existing_groups():
    """List all existing groups in the User Pool"""
    
    user_pool_id = os.environ.get('USER_POOL_ID', 'eu-west-1_OAT3oPCIm')
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        response = cognito_client.list_groups(UserPoolId=user_pool_id)
        
        print(f"\n📋 Existing groups in User Pool {user_pool_id}:")
        for group in response['Groups']:
            print(f"  - {group['GroupName']}: {group.get('Description', 'No description')}")
            
    except Exception as e:
        print(f"❌ Error listing groups: {str(e)}")

if __name__ == "__main__":
    print("🚀 Creating Verzoek_lid Cognito User Pool group...")
    
    # List existing groups first
    list_existing_groups()
    
    # Create the new group
    create_verzoek_lid_group()
    
    # List groups again to confirm
    list_existing_groups()
    
    print("\n✅ Done!")