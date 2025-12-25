#!/usr/bin/env python3
"""
Script to assign hdcnLeden role to existing Cognito users who don't have it.

This script ensures all existing users in the H-DCN Cognito User Pool
have the basic hdcnLeden role assigned.
"""

import json
import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN User Pool ID
DEFAULT_ROLE = "hdcnLeden"

def list_all_users():
    """List all users in the Cognito User Pool"""
    try:
        logger.info("Listing all users in the User Pool...")
        
        users = []
        paginator = cognito_client.get_paginator('list_users')
        
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            users.extend(page['Users'])
        
        logger.info(f"Found {len(users)} users in the User Pool")
        return users
        
    except ClientError as e:
        logger.error(f"Error listing users: {e}")
        raise

def get_user_groups(username):
    """Get groups for a specific user"""
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        groups = [group['GroupName'] for group in response.get('Groups', [])]
        return groups
        
    except ClientError as e:
        logger.error(f"Error getting groups for user {username}: {e}")
        raise

def add_user_to_group(username, group_name):
    """Add user to a Cognito User Pool group"""
    try:
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        logger.info(f"Successfully added user {username} to group {group_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Group {group_name} not found in user pool")
        elif error_code == 'UserNotFoundException':
            logger.error(f"User {username} not found in user pool")
        else:
            logger.error(f"Error adding user to group: {error_code} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding user to group: {str(e)}")
        return False

def process_existing_users():
    """Process all existing users and assign hdcnLeden role if needed"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {
        "timestamp": timestamp,
        "total_users": 0,
        "users_with_role": 0,
        "users_without_role": 0,
        "role_assignments_attempted": 0,
        "role_assignments_successful": 0,
        "role_assignments_failed": 0,
        "processed_users": [],
        "errors": []
    }
    
    try:
        logger.info("=== Processing Existing Users for hdcnLeden Role ===")
        
        # Step 1: Get all users
        users = list_all_users()
        results["total_users"] = len(users)
        
        if not users:
            logger.info("No users found in the User Pool")
            return results
        
        # Step 2: Process each user
        for user in users:
            username = user['Username']
            user_status = user['UserStatus']
            
            # Get user email for display
            email = username  # Default to username
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    email = attr['Value']
                    break
            
            user_info = {
                "username": username,
                "email": email,
                "status": user_status,
                "had_role": False,
                "role_assigned": False,
                "groups_before": [],
                "groups_after": [],
                "error": None
            }
            
            try:
                logger.info(f"Processing user: {email} ({username})")
                
                # Check current groups
                current_groups = get_user_groups(username)
                user_info["groups_before"] = current_groups
                
                if DEFAULT_ROLE in current_groups:
                    user_info["had_role"] = True
                    results["users_with_role"] += 1
                    logger.info(f"  ✓ User already has {DEFAULT_ROLE} role")
                else:
                    results["users_without_role"] += 1
                    logger.info(f"  ✗ User missing {DEFAULT_ROLE} role - assigning...")
                    
                    # Assign the role
                    results["role_assignments_attempted"] += 1
                    success = add_user_to_group(username, DEFAULT_ROLE)
                    
                    if success:
                        user_info["role_assigned"] = True
                        results["role_assignments_successful"] += 1
                        logger.info(f"  ✓ Successfully assigned {DEFAULT_ROLE} role")
                        
                        # Verify the assignment
                        updated_groups = get_user_groups(username)
                        user_info["groups_after"] = updated_groups
                        
                        if DEFAULT_ROLE in updated_groups:
                            logger.info(f"  ✓ Role assignment verified")
                        else:
                            logger.warning(f"  ⚠ Role assignment not reflected in groups")
                    else:
                        results["role_assignments_failed"] += 1
                        user_info["error"] = "Failed to assign role"
                        logger.error(f"  ✗ Failed to assign {DEFAULT_ROLE} role")
                
            except Exception as e:
                error_msg = f"Error processing user {email}: {str(e)}"
                logger.error(error_msg)
                user_info["error"] = str(e)
                results["errors"].append(error_msg)
            
            results["processed_users"].append(user_info)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in process_existing_users: {str(e)}")
        results["errors"].append(str(e))
        return results

def main():
    """Main execution"""
    logger.info("Starting existing user role assignment...")
    
    try:
        # Process all existing users
        results = process_existing_users()
        
        # Save results to file
        results_file = f"existing_users_role_assignment_{results['timestamp']}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {results_file}")
        
        # Print summary
        print("\n" + "="*70)
        print("EXISTING USERS ROLE ASSIGNMENT SUMMARY")
        print("="*70)
        print(f"Total Users: {results['total_users']}")
        print(f"Users with {DEFAULT_ROLE} role: {results['users_with_role']}")
        print(f"Users without {DEFAULT_ROLE} role: {results['users_without_role']}")
        print(f"Role assignments attempted: {results['role_assignments_attempted']}")
        print(f"Role assignments successful: {results['role_assignments_successful']}")
        print(f"Role assignments failed: {results['role_assignments_failed']}")
        
        if results['errors']:
            print(f"Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        print("\nDetailed Results:")
        for user in results['processed_users']:
            status_icon = "✓" if user['had_role'] or user['role_assigned'] else "✗"
            print(f"  {status_icon} {user['email']}")
            if user['had_role']:
                print(f"    Already had role: {user['groups_before']}")
            elif user['role_assigned']:
                print(f"    Role assigned: {user['groups_before']} → {user['groups_after']}")
            elif user['error']:
                print(f"    Error: {user['error']}")
        
        print("="*70)
        
        # Return success if no failures
        success = results['role_assignments_failed'] == 0
        return success
        
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)