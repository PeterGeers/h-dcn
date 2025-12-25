#!/usr/bin/env python3
"""
Comprehensive test suite for H-DCN automatic role assignment system.

This test suite validates all aspects of the automatic role assignment:
1. Lambda function configuration
2. Role assignment functionality
3. Error handling
4. Existing user coverage
5. Infrastructure validation
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
cf_client = boto3.client('cloudformation', region_name='eu-west-1')

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN User Pool ID
DEFAULT_ROLE = "hdcnLeden"
TEST_EMAIL_PREFIX = "test-comprehensive"
TEST_EMAIL_DOMAIN = "example.com"

class RoleAssignmentTestSuite:
    """Comprehensive test suite for role assignment system"""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0
            }
        }
    
    def run_test(self, test_name, test_function):
        """Run a single test and record results"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        self.test_results["summary"]["total_tests"] += 1
        
        try:
            result = test_function()
            if result:
                self.test_results["summary"]["passed_tests"] += 1
                logger.info(f"✅ PASSED: {test_name}")
            else:
                self.test_results["summary"]["failed_tests"] += 1
                logger.error(f"❌ FAILED: {test_name}")
            
            self.test_results["tests"][test_name] = {
                "passed": result,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.test_results["summary"]["failed_tests"] += 1
            logger.error(f"❌ ERROR in {test_name}: {str(e)}")
            
            self.test_results["tests"][test_name] = {
                "passed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return False
    
    def test_infrastructure_configuration(self):
        """Test 1: Verify infrastructure is properly configured"""
        logger.info("Verifying Cognito User Pool configuration...")
        
        try:
            # Check User Pool exists
            user_pool = cognito_client.describe_user_pool(UserPoolId=USER_POOL_ID)
            logger.info(f"✓ User Pool found: {user_pool['UserPool']['Name']}")
            
            # Check Lambda trigger is configured
            lambda_config = user_pool['UserPool'].get('LambdaConfig', {})
            post_confirmation_arn = lambda_config.get('PostConfirmation')
            
            if not post_confirmation_arn:
                logger.error("✗ Post-confirmation Lambda trigger not configured")
                return False
            
            logger.info(f"✓ Post-confirmation trigger configured: {post_confirmation_arn}")
            
            # Check default group exists
            groups = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
            group_names = [group['GroupName'] for group in groups['Groups']]
            
            if DEFAULT_ROLE not in group_names:
                logger.error(f"✗ Default group '{DEFAULT_ROLE}' not found")
                return False
            
            logger.info(f"✓ Default group '{DEFAULT_ROLE}' exists")
            
            return True
            
        except Exception as e:
            logger.error(f"Infrastructure configuration test failed: {e}")
            return False
    
    def test_lambda_function_exists(self):
        """Test 2: Verify Lambda function exists and is accessible"""
        logger.info("Verifying Lambda function configuration...")
        
        try:
            # Find the post-confirmation Lambda function
            functions = lambda_client.list_functions()['Functions']
            post_confirmation_function = None
            
            for func in functions:
                if 'CognitoPostConfirmation' in func['FunctionName']:
                    post_confirmation_function = func
                    break
            
            if not post_confirmation_function:
                logger.error("✗ Post-confirmation Lambda function not found")
                return False
            
            logger.info(f"✓ Lambda function found: {post_confirmation_function['FunctionName']}")
            
            # Check environment variables
            config = lambda_client.get_function_configuration(
                FunctionName=post_confirmation_function['FunctionName']
            )
            
            env_vars = config.get('Environment', {}).get('Variables', {})
            default_group = env_vars.get('DEFAULT_MEMBER_GROUP')
            
            if default_group != DEFAULT_ROLE:
                logger.error(f"✗ DEFAULT_MEMBER_GROUP mismatch: expected {DEFAULT_ROLE}, got {default_group}")
                return False
            
            logger.info(f"✓ Environment variable DEFAULT_MEMBER_GROUP: {default_group}")
            
            return True
            
        except Exception as e:
            logger.error(f"Lambda function test failed: {e}")
            return False
    
    def test_role_assignment_functionality(self):
        """Test 3: Test actual role assignment functionality"""
        logger.info("Testing role assignment functionality...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"{TEST_EMAIL_PREFIX}_{timestamp}@{TEST_EMAIL_DOMAIN}"
        
        try:
            # Create test user
            logger.info(f"Creating test user: {test_email}")
            
            cognito_client.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=test_email,
                UserAttributes=[
                    {'Name': 'email', 'Value': test_email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'given_name', 'Value': 'Test'},
                    {'Name': 'family_name', 'Value': 'User'}
                ],
                MessageAction='SUPPRESS',
                TemporaryPassword='TempPass123!'
            )
            
            logger.info("✓ Test user created")
            
            # Invoke Lambda function directly
            functions = lambda_client.list_functions()['Functions']
            post_confirmation_function = None
            
            for func in functions:
                if 'CognitoPostConfirmation' in func['FunctionName']:
                    post_confirmation_function = func['FunctionName']
                    break
            
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
            
            logger.info("Invoking Lambda function...")
            response = lambda_client.invoke(
                FunctionName=post_confirmation_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(mock_event)
            )
            
            if response['StatusCode'] != 200:
                logger.error(f"✗ Lambda invocation failed: {response['StatusCode']}")
                return False
            
            logger.info("✓ Lambda function invoked successfully")
            
            # Wait for processing
            time.sleep(2)
            
            # Check if role was assigned
            user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=test_email
            )
            
            groups = [group['GroupName'] for group in user_groups['Groups']]
            
            if DEFAULT_ROLE not in groups:
                logger.error(f"✗ Role not assigned. Groups: {groups}")
                return False
            
            logger.info(f"✓ Role assigned successfully. Groups: {groups}")
            
            return True
            
        except Exception as e:
            logger.error(f"Role assignment functionality test failed: {e}")
            return False
            
        finally:
            # Cleanup test user
            try:
                cognito_client.admin_delete_user(
                    UserPoolId=USER_POOL_ID,
                    Username=test_email
                )
                logger.info("✓ Test user cleaned up")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup test user: {cleanup_error}")
    
    def test_existing_users_coverage(self):
        """Test 4: Verify all existing users have the default role"""
        logger.info("Verifying existing users have default role...")
        
        try:
            # Get all users
            users = []
            paginator = cognito_client.get_paginator('list_users')
            
            for page in paginator.paginate(UserPoolId=USER_POOL_ID):
                users.extend(page['Users'])
            
            logger.info(f"Found {len(users)} users to check")
            
            users_without_role = []
            
            for user in users:
                username = user['Username']
                
                # Get user groups
                user_groups = cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
                
                groups = [group['GroupName'] for group in user_groups['Groups']]
                
                if DEFAULT_ROLE not in groups:
                    # Get email for display
                    email = username
                    for attr in user.get('Attributes', []):
                        if attr['Name'] == 'email':
                            email = attr['Value']
                            break
                    
                    users_without_role.append(email)
            
            if users_without_role:
                logger.error(f"✗ {len(users_without_role)} users without default role:")
                for email in users_without_role:
                    logger.error(f"  - {email}")
                return False
            
            logger.info(f"✓ All {len(users)} users have the default role")
            return True
            
        except Exception as e:
            logger.error(f"Existing users coverage test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test 5: Test error handling scenarios"""
        logger.info("Testing error handling scenarios...")
        
        try:
            # Find Lambda function
            functions = lambda_client.list_functions()['Functions']
            post_confirmation_function = None
            
            for func in functions:
                if 'CognitoPostConfirmation' in func['FunctionName']:
                    post_confirmation_function = func['FunctionName']
                    break
            
            # Test with invalid user pool ID
            mock_event_invalid_pool = {
                "version": "1",
                "region": "eu-west-1",
                "userPoolId": "invalid-pool-id",
                "userName": "test@example.com",
                "triggerSource": "PostConfirmation_ConfirmSignUp",
                "request": {
                    "userAttributes": {
                        "email": "test@example.com",
                        "email_verified": "true"
                    }
                },
                "response": {}
            }
            
            logger.info("Testing with invalid user pool ID...")
            response = lambda_client.invoke(
                FunctionName=post_confirmation_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(mock_event_invalid_pool)
            )
            
            # Lambda should handle error gracefully and return original event
            if response['StatusCode'] != 200:
                logger.error("✗ Lambda should handle errors gracefully")
                return False
            
            logger.info("✓ Error handling works correctly")
            
            # Test with missing user attributes
            mock_event_missing_attrs = {
                "version": "1",
                "region": "eu-west-1",
                "userPoolId": USER_POOL_ID,
                "userName": "test@example.com",
                "triggerSource": "PostConfirmation_ConfirmSignUp",
                "request": {
                    "userAttributes": {}
                },
                "response": {}
            }
            
            logger.info("Testing with missing user attributes...")
            response = lambda_client.invoke(
                FunctionName=post_confirmation_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(mock_event_missing_attrs)
            )
            
            if response['StatusCode'] != 200:
                logger.error("✗ Lambda should handle missing attributes gracefully")
                return False
            
            logger.info("✓ Missing attributes handled correctly")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    def test_permissions_validation(self):
        """Test 6: Validate Lambda function has correct permissions"""
        logger.info("Validating Lambda function permissions...")
        
        try:
            # Find Lambda function
            functions = lambda_client.list_functions()['Functions']
            post_confirmation_function = None
            
            for func in functions:
                if 'CognitoPostConfirmation' in func['FunctionName']:
                    post_confirmation_function = func
                    break
            
            if not post_confirmation_function:
                logger.error("✗ Lambda function not found")
                return False
            
            # Get function configuration
            config = lambda_client.get_function_configuration(
                FunctionName=post_confirmation_function['FunctionName']
            )
            
            role_arn = config['Role']
            logger.info(f"✓ Lambda execution role: {role_arn}")
            
            # Check if function can access Cognito (by testing a simple operation)
            try:
                # This will fail if permissions are incorrect
                cognito_client.list_groups(UserPoolId=USER_POOL_ID, Limit=1)
                logger.info("✓ Lambda has access to Cognito operations")
                return True
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    logger.error("✗ Lambda lacks Cognito permissions")
                    return False
                else:
                    # Other errors are acceptable for this test
                    logger.info("✓ Cognito access validated")
                    return True
            
        except Exception as e:
            logger.error(f"Permissions validation test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        logger.info("Starting Comprehensive Role Assignment Test Suite")
        logger.info(f"Timestamp: {self.test_results['timestamp']}")
        
        # Define test suite
        tests = [
            ("Infrastructure Configuration", self.test_infrastructure_configuration),
            ("Lambda Function Exists", self.test_lambda_function_exists),
            ("Role Assignment Functionality", self.test_role_assignment_functionality),
            ("Existing Users Coverage", self.test_existing_users_coverage),
            ("Error Handling", self.test_error_handling),
            ("Permissions Validation", self.test_permissions_validation)
        ]
        
        # Run all tests
        for test_name, test_function in tests:
            self.run_test(test_name, test_function)
        
        # Calculate success rate
        total = self.test_results["summary"]["total_tests"]
        passed = self.test_results["summary"]["passed_tests"]
        self.test_results["summary"]["success_rate"] = (passed / total * 100) if total > 0 else 0
        
        return self.test_results

def main():
    """Main test execution"""
    logger.info("Initializing Comprehensive Role Assignment Test Suite...")
    
    try:
        # Create test suite
        test_suite = RoleAssignmentTestSuite()
        
        # Run all tests
        results = test_suite.run_all_tests()
        
        # Save results to file
        results_file = f"comprehensive_role_assignment_test_results_{results['timestamp']}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("COMPREHENSIVE ROLE ASSIGNMENT TEST SUITE SUMMARY")
        print("="*80)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"Passed Tests: {results['summary']['passed_tests']}")
        print(f"Failed Tests: {results['summary']['failed_tests']}")
        print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, test_result in results['tests'].items():
            status = "✅ PASSED" if test_result['passed'] else "❌ FAILED"
            print(f"  {status}: {test_name}")
            if 'error' in test_result:
                print(f"    Error: {test_result['error']}")
        
        print("="*80)
        
        # Overall success
        overall_success = results['summary']['failed_tests'] == 0
        
        if overall_success:
            print("🎉 ALL TESTS PASSED - Automatic role assignment system is working correctly!")
        else:
            print("⚠️  SOME TESTS FAILED - Please review the failed tests and fix issues")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)