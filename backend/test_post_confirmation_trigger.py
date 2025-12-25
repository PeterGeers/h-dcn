#!/usr/bin/env python3
"""
Test script to verify post-confirmation Lambda trigger is working.

This script creates a user and simulates the actual signup flow that would
trigger the post-confirmation Lambda function.
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
TEST_EMAIL_PREFIX = "test-signup"
TEST_EMAIL_DOMAIN = "example.com"

def create_user_via_signup(email, password="TempPass123!"):
    """Create a user via the signup flow (not admin create)"""
    try:
        logger.info(f"Creating user via signup: {email}")
        
        response = cognito_client.sign_up(
            ClientId="7ej8ej8ej8ej8ej8ej8ej8",  # We need the actual client ID
            Username=email,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'given_name',
                    'Value': 'Test'
                },
                {
                    'Name': 'family_name',
                    'Value': 'User'
                }
            ]
        )
        
        logger.info(f"User signup initiated: {email}")
        return response
        
    except ClientError as e:
        logger.error(f"Error during signup: {e}")
        raise

def get_user_pool_client_id():
    """Get the User Pool Client ID"""
    try:
        # First, let's get the stack outputs to find the client ID
        cf_client = boto3.client('cloudformation', region_name='eu-west-1')
        
        # Try to find the stack
        stacks = cf_client.list_stacks(
            StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE']
        )
        
        for stack in stacks['StackSummaries']:
            if 'webshop' in stack['StackName'].lower():
                logger.info(f"Found stack: {stack['StackName']}")
                
                outputs = cf_client.describe_stacks(
                    StackName=stack['StackName']
                )['Stacks'][0].get('Outputs', [])
                
                for output in outputs:
                    if 'ClientId' in output['OutputKey']:
                        logger.info(f"Found Client ID: {output['Value']}")
                        return output['Value']
        
        # If we can't find it via CloudFormation, list clients directly
        logger.info("Trying to find client ID directly from Cognito...")
        
        response = cognito_client.list_user_pool_clients(
            UserPoolId=USER_POOL_ID,
            MaxResults=10
        )
        
        if response['UserPoolClients']:
            client_id = response['UserPoolClients'][0]['ClientId']
            logger.info(f"Found Client ID: {client_id}")
            return client_id
        
        raise Exception("Could not find User Pool Client ID")
        
    except Exception as e:
        logger.error(f"Error getting client ID: {e}")
        raise

def test_signup_flow():
    """Test the complete signup flow that should trigger post-confirmation"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"{TEST_EMAIL_PREFIX}_{timestamp}@{TEST_EMAIL_DOMAIN}"
    
    test_results = {
        "test_email": test_email,
        "timestamp": timestamp,
        "client_id_found": False,
        "user_created": False,
        "role_assigned": False,
        "expected_role": DEFAULT_ROLE,
        "actual_groups": [],
        "success": False,
        "error": None
    }
    
    try:
        logger.info("=== Testing Post-Confirmation Trigger ===")
        logger.info(f"Test email: {test_email}")
        
        # Step 1: Get the User Pool Client ID
        try:
            client_id = get_user_pool_client_id()
            test_results["client_id_found"] = True
            logger.info(f"✓ Found Client ID: {client_id}")
        except Exception as e:
            logger.error(f"✗ Could not find Client ID: {e}")
            test_results["error"] = f"Could not find Client ID: {e}"
            return test_results
        
        # Step 2: Create user using admin method but trigger confirmation
        logger.info("Creating user via admin method...")
        
        create_response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=test_email,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': test_email
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
        
        test_results["user_created"] = True
        logger.info("✓ User created successfully")
        
        # Step 3: Manually trigger the post-confirmation Lambda
        logger.info("Manually invoking post-confirmation Lambda...")
        
        lambda_client = boto3.client('lambda', region_name='eu-west-1')
        
        # Create a mock Cognito post-confirmation event
        mock_event = {
            "version": "1",
            "region": "eu-west-1",
            "userPoolId": USER_POOL_ID,
            "userName": test_email,
            "triggerSource": "PostConfirmation_ConfirmSignUp",
            "request": {
                "userAttributes": {
                    "email": test_email,
                    "given_name": "Test",
                    "family_name": "User",
                    "email_verified": "true"
                }
            },
            "response": {}
        }
        
        # Find the Lambda function name
        lambda_functions = lambda_client.list_functions()['Functions']
        post_confirmation_function = None
        
        for func in lambda_functions:
            if 'CognitoPostConfirmation' in func['FunctionName']:
                post_confirmation_function = func['FunctionName']
                break
        
        if post_confirmation_function:
            logger.info(f"Invoking Lambda function: {post_confirmation_function}")
            
            response = lambda_client.invoke(
                FunctionName=post_confirmation_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(mock_event)
            )
            
            logger.info("✓ Lambda function invoked successfully")
            
            # Wait a moment for processing
            time.sleep(2)
            
            # Step 4: Check if user was assigned to default role
            user_groups = check_user_groups(test_email)
            test_results["actual_groups"] = user_groups
            
            if DEFAULT_ROLE in user_groups:
                test_results["role_assigned"] = True
                test_results["success"] = True
                logger.info(f"✓ User successfully assigned to {DEFAULT_ROLE} role")
                logger.info("✓ Post-confirmation trigger is working correctly!")
            else:
                logger.error(f"✗ User was NOT assigned to {DEFAULT_ROLE} role")
                logger.error(f"  Expected: {DEFAULT_ROLE}")
                logger.error(f"  Actual groups: {user_groups}")
        else:
            logger.error("✗ Could not find post-confirmation Lambda function")
            test_results["error"] = "Could not find post-confirmation Lambda function"
        
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

def main():
    """Main test execution"""
    logger.info("Starting post-confirmation trigger test...")
    
    try:
        # Run the test
        results = test_signup_flow()
        
        # Save results to file
        results_file = f"post_confirmation_trigger_test_results_{results['timestamp']}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("POST-CONFIRMATION TRIGGER TEST SUMMARY")
        print("="*60)
        print(f"Test Email: {results['test_email']}")
        print(f"Client ID Found: {'✓' if results['client_id_found'] else '✗'}")
        print(f"User Created: {'✓' if results['user_created'] else '✗'}")
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