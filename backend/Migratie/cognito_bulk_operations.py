#!/usr/bin/env python3
"""
Direct Cognito bulk operations for migration - bypasses API Gateway
"""
import boto3
import csv
import json
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = 'eu-west-1_VtKQHhXGN'

def bulk_import_users_from_csv(csv_file_path):
    """Import users from CSV file"""
    created_users = []
    existing_users = []
    errors = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            username = row.get('username')
            email = row.get('email')
            
            if not username or not email:
                errors.append(f"Missing username or email for row: {row}")
                continue
                
            try:
                # Check if user exists
                cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
                existing_users.append(username)
                continue
                
            except cognito_client.exceptions.UserNotFoundException:
                # Create user
                try:
                    user_attributes = [
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ]
                    
                    # Add other attributes
                    for key, value in row.items():
                        if key not in ['username', 'email', 'groups', 'tempPassword'] and value:
                            user_attributes.append({'Name': key, 'Value': str(value)})
                    
                    cognito_client.admin_create_user(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        UserAttributes=user_attributes,
                        TemporaryPassword=row.get('tempPassword', 'WelkomHDCN2024!'),
                        MessageAction='SUPPRESS'
                    )
                    
                    # Add to groups
                    groups = row.get('groups', '')
                    if groups:
                        group_list = [g.strip() for g in groups.split(';') if g.strip()]
                        for group_name in group_list:
                            try:
                                cognito_client.admin_add_user_to_group(
                                    UserPoolId=USER_POOL_ID,
                                    Username=username,
                                    GroupName=group_name
                                )
                            except Exception as group_error:
                                errors.append(f"Failed to add {username} to group {group_name}: {str(group_error)}")
                    
                    created_users.append(username)
                    print(f"✅ Created user: {username}")
                    
                except Exception as create_error:
                    errors.append(f"Failed to create user {username}: {str(create_error)}")
            
            except Exception as check_error:
                errors.append(f"Error checking user {username}: {str(check_error)}")
    
    print(f"\n📊 Import Summary:")
    print(f"Created: {len(created_users)} users")
    print(f"Already existed: {len(existing_users)} users") 
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\n❌ Errors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")

def bulk_assign_groups(assignments):
    """Bulk assign users to groups
    assignments = [{"username": "user@example.com", "groups": "group1;group2"}]
    """
    assigned_count = 0
    errors = []
    
    for assignment in assignments:
        username = assignment.get('username')
        groups = assignment.get('groups', '')
        
        if not username or not groups:
            continue
            
        group_list = [g.strip() for g in groups.split(';') if g.strip()]
        
        for group_name in group_list:
            try:
                cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    GroupName=group_name
                )
                assigned_count += 1
                print(f"✅ Added {username} to {group_name}")
            except Exception as e:
                errors.append(f"Failed to add {username} to {group_name}: {str(e)}")
    
    print(f"\n📊 Assignment Summary:")
    print(f"Assignments made: {assigned_count}")
    print(f"Errors: {len(errors)}")

if __name__ == "__main__":
    # Example usage
    print("🚀 Starting Cognito bulk operations...")
    
    # Import users from CSV
    bulk_import_users_from_csv('cognito-users.csv')
    
    # Example bulk group assignment
    # assignments = [
    #     {"username": "user1@hdcn.nl", "groups": "hdcnLeden;hdcnRegio_NoordHolland"},
    #     {"username": "user2@hdcn.nl", "groups": "hdcnLeden;hdcnBestuur"}
    # ]
    # bulk_assign_groups(assignments)