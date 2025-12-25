#!/usr/bin/env python3
"""
Test script for H-DCN Cognito Automatic Role Assignment

This script tests that new users automatically get assigned the 'hdcnLeden' role
when they complete the signup and confirmation process.

Tests:
1. Create a new test user
2. Confirm the user (simulating email verification)
3. Verify the user is automatically assigned to the 'hdcnLeden' group
4. Clean up test user
"""

import boto3
import json
import time
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Configuration from deployed stack
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
CLIENT_ID = "7p5t7sjl2s1rcu1emn85h20qeh"
REGION = "eu-west-1"
DEFAULT_MEMBER_GROUP = "hdcnLeden"

# Test user configuration
TEST_EMAIL = f"role.test.{uuid.uuid4().hex[:8]}@example.com"
TEST_GIVEN_NAME = "RoleTest"
TEST_FAMILY_NAME = "User"

class AutomaticRoleAssignmentTest:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.test_results = []
        self.test_user_created = False
        
    def log_result(self, test_name, success, details="", error=None):
        """Log test result with timestamp"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "success": success,
            "details": details,
            "error": str(error) if error else None
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
        print()
        
    def test_1_verify_default_group_exists(self):
        """Test 1: Verify the default member group exists in the user pool"""
        print("=" * 60)
        print("TEST 1: Verify Default Group Exists")
        print("=" * 60)
        
        try:
            # List all groups in the user pool
            response = self.cognito_client.list_groups(
                UserPoolId=USER_POOL_ID
            )
            
            groups = response.get('Groups', [])
            group_names = [group['GroupName'] for group in groups]
            
            # Check if the default member group exists
            default_group_exists = DEFAULT_MEMBER_GROUP in group_names
            
            if default_group_exists:
                # Get details of the default group
                group_details = next(group for group in groups if group['GroupName'] == DEFAULT_MEMBER_GROUP)
                self.log_result(
                    "Default member group exists",
                    True,
                    f"Group '{DEFAULT_MEMBER_GROUP}' found with description: '{group_details.get('Description', 'No description')}', "
                    f"precedence: {group_details.get('Precedence', 'Not set')}"
                )
            else:
                self.log_result(
                    "Default member group exists",
                    False,
                    f"Group '{DEFAULT_MEMBER_GROUP}' not found. Available groups: {group_names}"
                )
            
            return default_group_exists
            
        except ClientError as e:
            self.log_result(
                "Default member group verification",
                False,
                f"Error checking groups: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Default member group verification",
                False,
                "Unexpected error checking groups",
                e
            )
            return False
    
    def test_2_create_test_user(self):
        """Test 2: Create a test user for role assignment testing"""
        print("=" * 60)
        print("TEST 2: Create Test User")
        print("=" * 60)
        
        try:
            # Create test user using SignUp API
            response = self.cognito_client.sign_up(
                ClientId=CLIENT_ID,
                Username=TEST_EMAIL,
                Password="TempPassword123!",  # Required by API but will be optional in passwordless flow
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': TEST_EMAIL
                    },
                    {
                        'Name': 'given_name',
                        'Value': TEST_GIVEN_NAME
                    },
                    {
                        'Name': 'family_name',
                        'Value': TEST_FAMILY_NAME
                    }
                ]
            )
            
            user_sub = response.get('UserSub')
            self.test_user_created = True
            
            self.log_result(
                "Test user creation",
                True,
                f"User created with email {TEST_EMAIL}, UserSub: {user_sub}"
            )
            
            # Verify user status is UNCONFIRMED
            user_info = self.cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            
            user_status = user_info.get('UserStatus')
            self.log_result(
                "User status after creation",
                user_status == 'UNCONFIRMED',
                f"User status: {user_status} (expected: UNCONFIRMED)"
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                self.log_result(
                    "Test user creation",
                    False,
                    "User already exists - please run cleanup or use different email",
                    e
                )
            else:
                self.log_result(
                    "Test user creation",
                    False,
                    f"Unexpected error during user creation: {error_code}",
                    e
                )
            return False
        except Exception as e:
            self.log_result(
                "Test user creation",
                False,
                "Unexpected error during user creation",
                e
            )
            return False
    
    def test_3_check_groups_before_confirmation(self):
        """Test 3: Verify user has no groups before confirmation"""
        print("=" * 60)
        print("TEST 3: Check Groups Before Confirmation")
        print("=" * 60)
        
        try:
            # Get user's groups before confirmation
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            
            groups_before = response.get('Groups', [])
            group_names_before = [group['GroupName'] for group in groups_before]
            
            self.log_result(
                "Groups before confirmation",
                len(groups_before) == 0,
                f"User has {len(groups_before)} groups before confirmation: {group_names_before}"
            )
            
            return len(groups_before) == 0
            
        except ClientError as e:
            self.log_result(
                "Check groups before confirmation",
                False,
                f"Error checking user groups: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Check groups before confirmation",
                False,
                "Unexpected error checking user groups",
                e
            )
            return False
    
    def test_4_confirm_user_and_trigger_post_confirmation(self):
        """Test 4: Confirm user to trigger post-confirmation Lambda"""
        print("=" * 60)
        print("TEST 4: Confirm User and Trigger Post-Confirmation")
        print("=" * 60)
        
        try:
            # Admin confirm user to trigger post-confirmation Lambda
            self.cognito_client.admin_confirm_sign_up(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            
            self.log_result(
                "User confirmation",
                True,
                f"User {TEST_EMAIL} confirmed successfully"
            )
            
            # Wait a moment for the Lambda trigger to execute
            print("⏳ Waiting 3 seconds for post-confirmation Lambda to execute...")
            time.sleep(3)
            
            # Verify user status is now CONFIRMED
            user_info = self.cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            
            user_status = user_info.get('UserStatus')
            self.log_result(
                "User status after confirmation",
                user_status == 'CONFIRMED',
                f"User status: {user_status} (expected: CONFIRMED)"
            )
            
            return user_status == 'CONFIRMED'
            
        except ClientError as e:
            self.log_result(
                "User confirmation",
                False,
                f"Error confirming user: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "User confirmation",
                False,
                "Unexpected error confirming user",
                e
            )
            return False
    
    def test_5_verify_automatic_role_assignment(self):
        """Test 5: Verify user was automatically assigned to default member group"""
        print("=" * 60)
        print("TEST 5: Verify Automatic Role Assignment")
        print("=" * 60)
        
        try:
            # Get user's groups after confirmation
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            
            groups_after = response.get('Groups', [])
            group_names_after = [group['GroupName'] for group in groups_after]
            
            # Check if user was assigned to default member group
            has_default_group = DEFAULT_MEMBER_GROUP in group_names_after
            
            if has_default_group:
                # Get details of the assigned group
                default_group_details = next(
                    group for group in groups_after 
                    if group['GroupName'] == DEFAULT_MEMBER_GROUP
                )
                
                self.log_result(
                    "Automatic role assignment",
                    True,
                    f"User successfully assigned to '{DEFAULT_MEMBER_GROUP}' group. "
                    f"Group description: '{default_group_details.get('Description', 'No description')}'. "
                    f"Total groups: {len(groups_after)}"
                )
            else:
                self.log_result(
                    "Automatic role assignment",
                    False,
                    f"User was NOT assigned to '{DEFAULT_MEMBER_GROUP}' group. "
                    f"Current groups: {group_names_after}"
                )
            
            return has_default_group
            
        except ClientError as e:
            self.log_result(
                "Verify automatic role assignment",
                False,
                f"Error checking user groups after confirmation: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Verify automatic role assignment",
                False,
                "Unexpected error checking user groups after confirmation",
                e
            )
            return False
    
    def test_6_verify_lambda_trigger_configuration(self):
        """Test 6: Verify Lambda trigger is properly configured"""
        print("=" * 60)
        print("TEST 6: Verify Lambda Trigger Configuration")
        print("=" * 60)
        
        try:
            # Get user pool configuration to check Lambda triggers
            response = self.cognito_client.describe_user_pool(
                UserPoolId=USER_POOL_ID
            )
            
            user_pool = response.get('UserPool', {})
            lambda_config = user_pool.get('LambdaConfig', {})
            
            # Check if PostConfirmation trigger is configured
            post_confirmation_arn = lambda_config.get('PostConfirmation')
            
            if post_confirmation_arn:
                self.log_result(
                    "PostConfirmation Lambda trigger configured",
                    True,
                    f"PostConfirmation trigger ARN: {post_confirmation_arn}"
                )
                
                # Also check other Lambda triggers for completeness
                custom_message_arn = lambda_config.get('CustomMessage')
                if custom_message_arn:
                    self.log_result(
                        "CustomMessage Lambda trigger configured",
                        True,
                        f"CustomMessage trigger ARN: {custom_message_arn}"
                    )
                
                return True
            else:
                self.log_result(
                    "PostConfirmation Lambda trigger configured",
                    False,
                    "PostConfirmation trigger is not configured in the user pool"
                )
                return False
            
        except ClientError as e:
            self.log_result(
                "Verify Lambda trigger configuration",
                False,
                f"Error checking user pool configuration: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Verify Lambda trigger configuration",
                False,
                "Unexpected error checking user pool configuration",
                e
            )
            return False
    
    def cleanup_test_user(self):
        """Clean up test user after testing"""
        if not self.test_user_created:
            return
            
        try:
            self.cognito_client.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_EMAIL
            )
            print(f"🧹 Cleaned up test user: {TEST_EMAIL}")
        except ClientError as e:
            print(f"⚠️ Could not clean up test user: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error during cleanup: {e}")
    
    def run_all_tests(self):
        """Run all automatic role assignment tests"""
        print("🚀 Starting H-DCN Automatic Role Assignment Tests")
        print(f"📧 Test email: {TEST_EMAIL}")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"👥 Default member group: {DEFAULT_MEMBER_GROUP}")
        print()
        
        # Run all tests in sequence
        test_1_success = self.test_1_verify_default_group_exists()
        if not test_1_success:
            print("❌ Cannot proceed without default group. Exiting.")
            return False
        
        test_2_success = self.test_2_create_test_user()
        if not test_2_success:
            print("❌ Cannot proceed without test user. Exiting.")
            return False
        
        test_3_success = self.test_3_check_groups_before_confirmation()
        test_4_success = self.test_4_confirm_user_and_trigger_post_confirmation()
        
        if not test_4_success:
            print("❌ User confirmation failed. Cannot test role assignment.")
            self.cleanup_test_user()
            return False
        
        test_5_success = self.test_5_verify_automatic_role_assignment()
        test_6_success = self.test_6_verify_lambda_trigger_configuration()
        
        # Summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()
        
        # Key result: Did automatic role assignment work?
        role_assignment_success = test_5_success
        
        if role_assignment_success:
            print("🎉 AUTOMATIC ROLE ASSIGNMENT TEST PASSED!")
            print(f"✅ New users are automatically assigned to '{DEFAULT_MEMBER_GROUP}' group")
        else:
            print("❌ AUTOMATIC ROLE ASSIGNMENT TEST FAILED!")
            print(f"❌ New users are NOT automatically assigned to '{DEFAULT_MEMBER_GROUP}' group")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
        else:
            print("⚠️ Some tests failed. Check details above.")
        
        # Save detailed results
        results_file = 'automatic_role_assignment_test_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"📄 Detailed results saved to: {results_file}")
        
        # Cleanup
        self.cleanup_test_user()
        
        return role_assignment_success

if __name__ == "__main__":
    tester = AutomaticRoleAssignmentTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)