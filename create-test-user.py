#!/usr/bin/env python3
"""
Create test user for passkey testing
"""
import boto3
import json
import os
from datetime import datetime

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN User Pool ID
TEST_EMAIL = "test@h-dcn.nl"  # Email used in mobile test

def create_test_user():
    """Create a test user for passkey testing"""
    
    # Initialize Cognito client
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Check if user already exists
        try:
            response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            print(f"✓ User {TEST_EMAIL} already exists")
            print(f"  Status: {response['UserStatus']}")
            return True
            
        except cognito_client.exceptions.UserNotFoundException:
            print(f"Creating new user: {TEST_EMAIL}")
            
            # Create user
            response = cognito_client.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL,
                UserAttributes=[
                    {'Name': 'email', 'Value': TEST_EMAIL},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'given_name', 'Value': 'Test'},
                    {'Name': 'family_name', 'Value': 'User'}
                ],
                MessageAction='SUPPRESS',  # Don't send welcome email
                TemporaryPassword='TempPass123!'
            )
            
            print(f"✓ User {TEST_EMAIL} created successfully")
            
            # Set user status to CONFIRMED (skip password setup)
            cognito_client.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL,
                Password='TempPass123!',
                Permanent=False  # User will need to change password, but we'll use passkeys
            )
            
            # Add to basic member group
            try:
                cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_EMAIL,
                    GroupName='hdcnLeden'
                )
                print(f"✓ Added {TEST_EMAIL} to hdcnLeden group")
            except Exception as e:
                print(f"⚠ Could not add to group (group may not exist): {e}")
            
            return True
            
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Creating Test User for Passkey Testing")
    print("=" * 50)
    
    success = create_test_user()
    
    if success:
        print("\n✓ Test user setup complete!")
        print(f"You can now test passkey registration with: {TEST_EMAIL}")
    else:
        print("\n✗ Failed to create test user")