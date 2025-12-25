#!/usr/bin/env python3
"""
Test script to verify automatic hdcnLeden role assignment for new users.

This script tests the post-confirmation Lambda trigger to ensure new users
automatically receive the hdcnLeden role when they complete email verification.
"""

import json
import boto3
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN User Pool ID (new authentication pool)
DEFAULT_ROLE = "hdcnLeden"
TEST_EMAIL_PREFIX = "test-role-assignment"
TEST_EMAIL_DOMAIN = "example.com"

def create_test_user(email):
    """Create a test user in Cognito User Pool"""
    try:
        logger.info(f"Creating test user: {email}")
        
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': 'true'
                },
                {
                    'Name': 'given_name',
                    'Value': 'Test'
                },
                {
                    'Name': 'family_name',
                    'Value': 'User'
                }
            ],
            MessageAction='SUPPRESS',  # Don't send welcome email
            TemporaryPassword='TempPass123!'
        )
        
        logger.info(f"Test user created successfully: {email}")
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            logger.warning(f"User {email} already exists")
            return None
        else:
            logger.error(f"Error creating test user: {e}")
            raise

def simulate_email_confirmation(username):
    """Simulate email confirmation by setting user status to CONFIRMED"""
    try:
        logger.info(f"Confirming user: {username}")
        
        # Set user status to CONFIRMED to trigger post-confirmation
        response = cognito_client.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        logger.info(f"User confirmed successfully: {username}")
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotAuthorizedException':
            logger.info(f"User {username} is already confirmed")
            return None
        else:
            logger.error(f"Error confirming user: {e}")
            raise

def check_user_groups(username):
    """Check which groups a user belongs to"""
    try:
        logger.info(f"Checking groups for user: {username}")
        
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        groups = [group['GroupName'] for group in response.get('Groups', [])]
        logger.info(f"User {username} belongs to groups: {groups}")
        
        return groups
        
    except ClientError as e:
        logger.error(f"Error checking user groups: {e}")
        raise

def cleanup_test_user(username):
    """Delete test user from Cognito User Pool"""
    try:
        logger.info(f"Cleaning up test user: {username}")
        
        response = cognito_client.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        logger.info(f"Test user deleted successfully: {username}")
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            logger.warning(f"User {username} not found for cleanup")
            return None
        else:
            logger.error(f"Error deleting test user: {e}")
            raise

def test_automatic_role_assignment():
    """Test automatic role assignment for new users"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"{TEST_EMAIL_PREFIX}_{timestamp}@{TEST_EMAIL_DOMAIN}"
    
    test_results = {
        "test_email": test_email,
        "timestamp": timestamp,
        "user_created": False,
        "user_confirmed": False,
        "role_assigned": False,
        "expected_role": DEFAULT_ROLE,
        "actual_groups": [],
        "success": False,
        "error": None
    }
    
    try:
        # Step 1: Create test user
        logger.info("=== Testing Automatic Role Assignment ===")
        logger.info(f"Test email: {test_email}")
        
        create_response = create_test_user(test_email)
        if create_response:
            test_results["user_created"] = True
            logger.info("✓ Test user created successfully")
        else:
            logger.error("✗ Failed to create test user")
            return test_results
        
        # Step 2: Simulate email confirmation (triggers post-confirmation Lambda)
        time.sleep(2)  # Brief delay to ensure user is ready
        
        confirm_response = simulate_email_confirmation(test_email)
        test_results["user_confirmed"] = True
        logger.info("✓ User email confirmation simulated")
        
        # Step 3: Wait for Lambda trigger to process
        logger.info("Waiting for post-confirmation Lambda to process...")
        time.sleep(5)  # Wait for Lambda trigger to complete
        
        # Step 4: Check if user was assigned to default role
        user_groups = check_user_groups(test_email)
        test_results["actual_groups"] = user_groups
        
        if DEFAULT_ROLE in user_groups:
            test_results["role_assigned"] = True
            test_results["success"] = True
            logger.info(f"✓ User successfully assigned to {DEFAULT_ROLE} role")
            logger.info("✓ Automatic role assignment is working correctly!")
        else:
            logger.error(f"✗ User was NOT assigned to {DEFAULT_ROLE} role")
            logger.error(f"  Expected: {DEFAULT_ROLE}")
            logger.error(f"  Actual groups: {user_groups}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        test_results["error"] = str(e)
        return test_results
        
    finally:
        # Cleanup: Delete test user
        try:
            if test_results["user_created"]:
                cleanup_test_user(test_email)
                logger.info("✓ Test user cleaned up successfully")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup test user: {cleanup_error}")

def main():
    """Main test execution"""
    logger.info("Starting automatic role assignment verification test...")
    
    try:
        # Run the test
        results = test_automatic_role_assignment()
        
        # Save results to file
        results_file = f"automatic_role_assignment_test_results_{results['timestamp']}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("AUTOMATIC ROLE ASSIGNMENT TEST SUMMARY")
        print("="*60)
        print(f"Test Email: {results['test_email']}")
        print(f"User Created: {'✓' if results['user_created'] else '✗'}")
        print(f"User Confirmed: {'✓' if results['user_confirmed'] else '✗'}")
        print(f"Role Assigned: {'✓' if results['role_assigned'] else '✗'}")
        print(f"Expected Role: {results['expected_role']}")
        print(f"Actual Groups: {results['actual_groups']}")
        print(f"Overall Success: {'✓' if results['success'] else '✗'}")
        
        if results['error']:
            print(f"Error: {results['error']}")
        
        print("="*60)
        
        return results['success']
        
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)