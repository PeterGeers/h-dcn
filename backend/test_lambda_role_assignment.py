#!/usr/bin/env python3
"""
Test script to directly test the post-confirmation Lambda function.

This script creates a test user and directly invokes the Lambda function
to verify that automatic role assignment is working.
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
lambda_client = boto3.client('lambda', region_name='eu-west-1')

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN User Pool ID
CLIENT_ID = "7p5t7sjl2s1rcu1emn85h20qeh"  # H-DCN Web Client ID
DEFAULT_ROLE = "hdcnLeden"
TEST_EMAIL_PREFIX = "test-lambda-role"
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

def invoke_post_confirmation_lambda(username, email):
    """Directly invoke the post-confirmation Lambda function"""
    try:
        logger.info(f"Invoking post-confirmation Lambda for user: {email}")
        
        # Find the Lambda function name
        lambda_functions = lambda_client.list_functions()['Functions']
        post_confirmation_function = None
        
        for func in lambda_functions:
            if 'CognitoPostConfirmation' in func['FunctionName']:
                post_confirmation_function = func['FunctionName']
                logger.info(f"Found Lambda function: {post_confirmation_function}")
                break
        
        if not post_confirmation_function:
            raise Exception("Could not find post-confirmation Lambda function")
        
        # Create a mock Cognito post-confirmation event
        mock_event = {
            "version": "1",
            "region": "eu-west-1",
            "userPoolId": USER_POOL_ID,
            "userName": username,
            "triggerSource": "PostConfirmation_ConfirmSignUp",
            "request": {
                "userAttributes": {
                    "email": email,
                    "given_name": "Test",
                    "family_name": "User",
                    "email_verified": "true"
                }
            },
            "response": {}
        }
        
        logger.info(f"Invoking Lambda with event: {json.dumps(mock_event, indent=2)}")
        
        response = lambda_client.invoke(
            FunctionName=post_confirmation_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(mock_event)
        )
        
        # Parse the response
        payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            logger.info("✓ Lambda function invoked successfully")
            logger.info(f"Lambda response: {json.dumps(payload, indent=2)}")
            return True
        else:
            logger.error(f"✗ Lambda function failed with status: {response['StatusCode']}")
            logger.error(f"Response: {payload}")
            return False
        
    except Exception as e:
        logger.error(f"Error invoking Lambda function: {e}")
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

def test_lambda_role_assignment():
    """Test Lambda function role assignment directly"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"{TEST_EMAIL_PREFIX}_{timestamp}@{TEST_EMAIL_DOMAIN}"
    
    test_results = {
        "test_email": test_email,
        "timestamp": timestamp,
        "user_created": False,
        "lambda_invoked": False,
        "role_assigned": False,
        "expected_role": DEFAULT_ROLE,
        "actual_groups": [],
        "success": False,
        "error": None
    }
    
    try:
        logger.info("=== Testing Lambda Role Assignment ===")
        logger.info(f"Test email: {test_email}")
        
        # Step 1: Create test user
        create_response = create_test_user(test_email)
        if create_response:
            test_results["user_created"] = True
            logger.info("✓ Test user created successfully")
        else:
            logger.error("✗ Failed to create test user")
            return test_results
        
        # Step 2: Directly invoke the post-confirmation Lambda
        lambda_success = invoke_post_confirmation_lambda(test_email, test_email)
        test_results["lambda_invoked"] = lambda_success
        
        if lambda_success:
            logger.info("✓ Lambda function invoked successfully")
        else:
            logger.error("✗ Lambda function invocation failed")
            return test_results
        
        # Step 3: Wait a moment for processing
        time.sleep(3)
        
        # Step 4: Check if user was assigned to default role
        user_groups = check_user_groups(test_email)
        test_results["actual_groups"] = user_groups
        
        if DEFAULT_ROLE in user_groups:
            test_results["role_assigned"] = True
            test_results["success"] = True
            logger.info(f"✓ User successfully assigned to {DEFAULT_ROLE} role")
            logger.info("✓ Lambda role assignment is working correctly!")
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
    logger.info("Starting Lambda role assignment test...")
    
    try:
        # Run the test
        results = test_lambda_role_assignment()
        
        # Save results to file
        results_file = f"lambda_role_assignment_test_results_{results['timestamp']}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("LAMBDA ROLE ASSIGNMENT TEST SUMMARY")
        print("="*60)
        print(f"Test Email: {results['test_email']}")
        print(f"User Created: {'✓' if results['user_created'] else '✗'}")
        print(f"Lambda Invoked: {'✓' if results['lambda_invoked'] else '✗'}")
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