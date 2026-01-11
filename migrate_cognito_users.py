#!/usr/bin/env python3
"""
Script to migrate Cognito users from old pool to new pool
"""
import boto3
import json

def migrate_cognito_users():
    cognito = boto3.client('cognito-idp', region_name='eu-west-1')
    
    # Old and new pool IDs
    old_pool_id = 'eu-west-1_OAT3oPCIm'  # Current pool
    new_pool_id = 'NEW_POOL_ID'  # Will be created by new stack
    
    print("Starting Cognito user migration...")
    
    # 1. List all users from old pool
    paginator = cognito.get_paginator('list_users')
    users_to_migrate = []
    
    for page in paginator.paginate(UserPoolId=old_pool_id):
        users_to_migrate.extend(page['Users'])
    
    print(f"Found {len(users_to_migrate)} users to migrate")
    
    # 2. Create users in new pool
    for user in users_to_migrate:
        try:
            # Extract user attributes
            attributes = []
            for attr in user.get('Attributes', []):
                attributes.append({
                    'Name': attr['Name'],
                    'Value': attr['Value']
                })
            
            # Create user in new pool
            response = cognito.admin_create_user(
                UserPoolId=new_pool_id,
                Username=user['Username'],
                UserAttributes=attributes,
                MessageAction='SUPPRESS',  # Don't send welcome email
                TemporaryPassword='TempPass123!'
            )
            
            # Set permanent password if user was confirmed
            if user['UserStatus'] == 'CONFIRMED':
                cognito.admin_set_user_password(
                    UserPoolId=new_pool_id,
                    Username=user['Username'],
                    Password='TempPass123!',
                    Permanent=False  # User will need to change on first login
                )
            
            print(f"✅ Migrated user: {user['Username']}")
            
        except Exception as e:
            print(f"❌ Failed to migrate {user['Username']}: {str(e)}")
    
    print("Migration completed!")

if __name__ == "__main__":
    migrate_cognito_users()