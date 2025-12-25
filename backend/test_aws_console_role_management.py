#!/usr/bin/env python3
"""
Test AWS Console Role Management Interface

This test verifies that the AWS Console (admin interface) allows role assignment changes
through the existing Cognito admin endpoints.
"""

import json
import boto3
import requests
import time
from datetime import datetime

# Configuration
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
API_BASE_URL = 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'
TEST_USER = 'console.test@hdcn-test.nl'

class AWSConsoleRoleManagementTest:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'test_user': TEST_USER,
            'api_base_url': API_BASE_URL,
            'user_pool_id': USER_POOL_ID,
            'tests': []
        }
        
    def log_test(self, test_name, success, details, error=None):
        """Log test result"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test': test_name,
            'success': success,
            'details': details,
            'error': str(error) if error else None
        }
        self.test_results['tests'].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
        print()
        
    def test_1_console_endpoints_available(self):
        """Test 1: Verify AWS Console admin endpoints are available"""
        print("=" * 80)
        print("TEST 1: AWS Console Admin Endpoints Available")
        print("=" * 80)
        
        try:
            # Test the main endpoints that would be used by AWS Console
            endpoints_to_test = [
                ('/cognito/users', 'GET', 'List users'),
                ('/cognito/groups', 'GET', 'List groups'),
                ('/cognito/pool', 'GET', 'Get pool info')
            ]
            
            available_endpoints = []
            for endpoint, method, description in endpoints_to_test:
                try:
                    url = f"{API_BASE_URL}{endpoint}"
                    if method == 'GET':
                        response = requests.get(url, timeout=10)
                    
                    if response.status_code in [200, 201]:
                        available_endpoints.append(f"{method} {endpoint} - {description}")
                        print(f"   ✅ {method} {endpoint} - {description} (Status: {response.status_code})")
                    else:
                        print(f"   ⚠️ {method} {endpoint} - {description} (Status: {response.status_code})")
                        
                except Exception as e:
                    print(f"   ❌ {method} {endpoint} - {description} (Error: {str(e)})")
            
            success = len(available_endpoints) >= 2  # At least 2 endpoints should work
            details = f"Available endpoints: {len(available_endpoints)}/3\n   " + "\n   ".join(available_endpoints)
            
            self.log_test("Console endpoints available", success, details)
            return success
            
        except Exception as e:
            self.log_test("Console endpoints available", False, "Failed to test endpoints", e)
            return False
    
    def test_2_user_role_query_via_console(self):
        """Test 2: Query user roles via console interface"""
        print("=" * 80)
        print("TEST 2: User Role Query via Console Interface")
        print("=" * 80)
        
        try:
            # First ensure test user exists
            try:
                self.cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER
                )
                print(f"   Test user {TEST_USER} exists")
            except self.cognito_client.exceptions.UserNotFoundException:
                # Create test user
                self.cognito_client.admin_create_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    UserAttributes=[
                        {'Name': 'email', 'Value': TEST_USER},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ],
                    MessageAction='SUPPRESS'
                )
                print(f"   Created test user {TEST_USER}")
            
            # Test querying user roles via console API
            url = f"{API_BASE_URL}/cognito/users/{TEST_USER}/groups"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                groups_data = response.json()
                current_groups = [group['GroupName'] for group in groups_data] if isinstance(groups_data, list) else []
                
                success = True
                details = f"Successfully queried user roles via console\n   User: {TEST_USER}\n   Current groups: {current_groups}\n   API response status: {response.status_code}"
                
            else:
                success = False
                details = f"Failed to query user roles\n   API response status: {response.status_code}\n   Response: {response.text[:200]}"
            
            self.log_test("User role query via console", success, details)
            return success
            
        except Exception as e:
            self.log_test("User role query via console", False, "Failed to query user roles", e)
            return False
    
    def test_3_role_assignment_via_console(self):
        """Test 3: Assign roles via console interface"""
        print("=" * 80)
        print("TEST 3: Role Assignment via Console Interface")
        print("=" * 80)
        
        try:
            # Test assigning a role via console API
            test_group = 'Members_Read_All'
            
            # First remove user from group if already there
            try:
                self.cognito_client.admin_remove_user_from_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName=test_group
                )
                print(f"   Removed {TEST_USER} from {test_group} (cleanup)")
            except:
                pass
            
            # Assign role via console API
            url = f"{API_BASE_URL}/cognito/users/{TEST_USER}/groups/{test_group}"
            response = requests.post(url, timeout=10)
            
            if response.status_code in [200, 201]:
                # Verify the assignment worked
                time.sleep(1)  # Brief delay for consistency
                
                groups_response = self.cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER
                )
                
                current_groups = [group['GroupName'] for group in groups_response['Groups']]
                assignment_successful = test_group in current_groups
                
                success = assignment_successful
                details = f"Role assignment via console API\n   User: {TEST_USER}\n   Assigned group: {test_group}\n   API response status: {response.status_code}\n   Assignment successful: {assignment_successful}\n   Current groups: {current_groups}"
                
            else:
                success = False
                details = f"Failed to assign role via console\n   API response status: {response.status_code}\n   Response: {response.text[:200]}"
            
            self.log_test("Role assignment via console", success, details)
            return success
            
        except Exception as e:
            self.log_test("Role assignment via console", False, "Failed to assign role", e)
            return False
    
    def test_4_role_removal_via_console(self):
        """Test 4: Remove roles via console interface"""
        print("=" * 80)
        print("TEST 4: Role Removal via Console Interface")
        print("=" * 80)
        
        try:
            test_group = 'Members_Read_All'
            
            # Ensure user has the role first
            try:
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName=test_group
                )
                print(f"   Ensured {TEST_USER} is in {test_group}")
            except:
                pass
            
            # Remove role via console API
            url = f"{API_BASE_URL}/cognito/users/{TEST_USER}/groups/{test_group}"
            response = requests.delete(url, timeout=10)
            
            if response.status_code in [200, 204]:
                # Verify the removal worked
                time.sleep(1)  # Brief delay for consistency
                
                groups_response = self.cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER
                )
                
                current_groups = [group['GroupName'] for group in groups_response['Groups']]
                removal_successful = test_group not in current_groups
                
                success = removal_successful
                details = f"Role removal via console API\n   User: {TEST_USER}\n   Removed group: {test_group}\n   API response status: {response.status_code}\n   Removal successful: {removal_successful}\n   Current groups: {current_groups}"
                
            else:
                success = False
                details = f"Failed to remove role via console\n   API response status: {response.status_code}\n   Response: {response.text[:200]}"
            
            self.log_test("Role removal via console", success, details)
            return success
            
        except Exception as e:
            self.log_test("Role removal via console", False, "Failed to remove role", e)
            return False
    
    def test_5_bulk_role_operations_via_console(self):
        """Test 5: Bulk role operations via console interface"""
        print("=" * 80)
        print("TEST 5: Bulk Role Operations via Console Interface")
        print("=" * 80)
        
        try:
            # Test bulk role assignment via console API
            test_groups = ['Members_Read_All', 'Events_Read_All']
            
            # Clear existing groups first
            try:
                current_groups_response = self.cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER
                )
                for group in current_groups_response['Groups']:
                    self.cognito_client.admin_remove_user_from_group(
                        UserPoolId=USER_POOL_ID,
                        Username=TEST_USER,
                        GroupName=group['GroupName']
                    )
                print(f"   Cleared existing groups for {TEST_USER}")
            except:
                pass
            
            # Assign multiple roles
            successful_assignments = 0
            for group in test_groups:
                url = f"{API_BASE_URL}/cognito/users/{TEST_USER}/groups/{group}"
                response = requests.post(url, timeout=10)
                if response.status_code in [200, 201]:
                    successful_assignments += 1
                    print(f"   ✅ Assigned {group} via console API")
                else:
                    print(f"   ❌ Failed to assign {group} (Status: {response.status_code})")
            
            # Verify all assignments
            time.sleep(1)
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            all_assigned = all(group in current_groups for group in test_groups)
            
            success = successful_assignments == len(test_groups) and all_assigned
            details = f"Bulk role operations via console\n   User: {TEST_USER}\n   Target groups: {test_groups}\n   Successful API calls: {successful_assignments}/{len(test_groups)}\n   All groups assigned: {all_assigned}\n   Final groups: {current_groups}"
            
            self.log_test("Bulk role operations via console", success, details)
            return success
            
        except Exception as e:
            self.log_test("Bulk role operations via console", False, "Failed bulk operations", e)
            return False
    
    def cleanup_test_user(self):
        """Clean up test user"""
        try:
            # Reset to basic member role
            try:
                current_groups_response = self.cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER
                )
                for group in current_groups_response['Groups']:
                    self.cognito_client.admin_remove_user_from_group(
                        UserPoolId=USER_POOL_ID,
                        Username=TEST_USER,
                        GroupName=group['GroupName']
                    )
                
                # Add back to basic member group
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName='hdcnLeden'
                )
                print(f"   Reset {TEST_USER} to basic member role")
            except:
                pass
        except:
            pass
    
    def run_all_tests(self):
        """Run all AWS Console role management tests"""
        print("🚀 Starting AWS Console Role Management Tests")
        print(f"🎯 Task: Verify AWS Console allows role assignment changes")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"👤 Test User: {TEST_USER}")
        print(f"🌐 API Base URL: {API_BASE_URL}")
        print()
        
        # Run all tests
        test_results = []
        test_results.append(self.test_1_console_endpoints_available())
        test_results.append(self.test_2_user_role_query_via_console())
        test_results.append(self.test_3_role_assignment_via_console())
        test_results.append(self.test_4_role_removal_via_console())
        test_results.append(self.test_5_bulk_role_operations_via_console())
        
        # Cleanup
        self.cleanup_test_user()
        
        # Summary
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        print("=" * 80)
        print("AWS CONSOLE ROLE MANAGEMENT TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()
        
        if passed_tests == total_tests:
            print("🎉 All AWS Console role management tests passed!")
            print("✅ AWS Console allows role assignment changes")
            print("✅ Console API endpoints are functional")
            print("✅ Role assignments work via console interface")
            print("✅ Role removals work via console interface")
            print("✅ Bulk operations work via console interface")
        else:
            print("❌ Some AWS Console role management tests failed!")
            print(f"❌ {total_tests - passed_tests} out of {total_tests} tests failed")
        
        print()
        print("🔄 Next Steps:")
        if passed_tests == total_tests:
            print("  1. ✅ AWS Console role management is working correctly")
            print("  2. 🔄 Administrators can change roles through console interface")
            print("  3. 🔄 Role changes are immediately effective")
        else:
            print("  1. ❌ Fix failing console interface tests")
            print("  2. 🔄 Verify API endpoints are properly deployed")
            print("  3. 🔄 Check network connectivity and permissions")
        
        # Save results
        results_file = f'aws_console_role_management_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"📄 Detailed results saved to: {results_file}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = AWSConsoleRoleManagementTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)