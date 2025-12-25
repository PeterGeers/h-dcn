#!/usr/bin/env python3
"""
Test Role Change Timing Requirements

This test specifically verifies that role assignment changes take effect 
immediately or within 5 minutes as required by the acceptance criteria.
"""

import json
import boto3
import time
from datetime import datetime, timedelta

# Configuration
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
TEST_USER = 'timing.test@hdcn-test.nl'
REGION = 'eu-west-1'

class RoleChangeTimingTest:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'test_user': TEST_USER,
            'user_pool_id': USER_POOL_ID,
            'timing_tests': []
        }
        
    def log_timing_test(self, test_name, change_time_seconds, success, details):
        """Log timing test result"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test': test_name,
            'change_time_seconds': change_time_seconds,
            'change_time_formatted': f"{change_time_seconds:.2f}s",
            'immediate': change_time_seconds < 5.0,
            'within_5_minutes': change_time_seconds < 300.0,
            'success': success,
            'details': details
        }
        self.test_results['timing_tests'].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        timing_status = "IMMEDIATE" if change_time_seconds < 5.0 else "WITHIN 5 MIN" if change_time_seconds < 300.0 else "TOO SLOW"
        
        print(f"{status} {test_name}")
        print(f"   Change Time: {change_time_seconds:.2f}s ({timing_status})")
        print(f"   Details: {details}")
        print()
        
    def ensure_test_user_exists(self):
        """Ensure test user exists"""
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
            
            # Add to basic member group
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='hdcnLeden'
            )
    
    def test_single_role_addition_timing(self):
        """Test timing for adding a single role"""
        print("=" * 80)
        print("TEST 1: Single Role Addition Timing")
        print("=" * 80)
        
        try:
            # Ensure clean state
            self.reset_user_to_basic_member()
            
            # Measure time to add a role
            start_time = time.time()
            
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='Members_Read_All'
            )
            
            # Verify the change is reflected
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            end_time = time.time()
            change_time = end_time - start_time
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            role_added = 'Members_Read_All' in current_groups
            
            success = role_added and change_time < 300.0  # Within 5 minutes
            details = f"Added Members_Read_All role\n   Current groups: {current_groups}\n   Role added successfully: {role_added}"
            
            self.log_timing_test("Single role addition", change_time, success, details)
            return success
            
        except Exception as e:
            self.log_timing_test("Single role addition", 999.0, False, f"Error: {str(e)}")
            return False
    
    def test_single_role_removal_timing(self):
        """Test timing for removing a single role"""
        print("=" * 80)
        print("TEST 2: Single Role Removal Timing")
        print("=" * 80)
        
        try:
            # Ensure user has the role first
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='Events_Read_All'
            )
            
            # Measure time to remove the role
            start_time = time.time()
            
            self.cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='Events_Read_All'
            )
            
            # Verify the change is reflected
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            end_time = time.time()
            change_time = end_time - start_time
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            role_removed = 'Events_Read_All' not in current_groups
            
            success = role_removed and change_time < 300.0  # Within 5 minutes
            details = f"Removed Events_Read_All role\n   Current groups: {current_groups}\n   Role removed successfully: {role_removed}"
            
            self.log_timing_test("Single role removal", change_time, success, details)
            return success
            
        except Exception as e:
            self.log_timing_test("Single role removal", 999.0, False, f"Error: {str(e)}")
            return False
    
    def test_multiple_role_changes_timing(self):
        """Test timing for multiple simultaneous role changes"""
        print("=" * 80)
        print("TEST 3: Multiple Role Changes Timing")
        print("=" * 80)
        
        try:
            # Start with clean state
            self.reset_user_to_basic_member()
            
            # Define the role changes
            roles_to_add = ['Members_Read_All', 'Events_Read_All', 'Products_Read_All']
            
            # Measure time for multiple role additions
            start_time = time.time()
            
            for role in roles_to_add:
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName=role
                )
            
            # Verify all changes are reflected
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            end_time = time.time()
            change_time = end_time - start_time
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            all_roles_added = all(role in current_groups for role in roles_to_add)
            
            success = all_roles_added and change_time < 300.0  # Within 5 minutes
            details = f"Added {len(roles_to_add)} roles: {roles_to_add}\n   Current groups: {current_groups}\n   All roles added: {all_roles_added}"
            
            self.log_timing_test("Multiple role changes", change_time, success, details)
            return success
            
        except Exception as e:
            self.log_timing_test("Multiple role changes", 999.0, False, f"Error: {str(e)}")
            return False
    
    def test_role_replacement_timing(self):
        """Test timing for replacing one set of roles with another"""
        print("=" * 80)
        print("TEST 4: Role Replacement Timing")
        print("=" * 80)
        
        try:
            # Start with some roles
            initial_roles = ['Members_Read_All', 'Events_Read_All']
            final_roles = ['Members_CRUD_All', 'System_User_Management']
            
            # Set initial roles
            self.reset_user_to_basic_member()
            for role in initial_roles:
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName=role
                )
            
            # Measure time to replace roles
            start_time = time.time()
            
            # Remove old roles
            for role in initial_roles + ['hdcnLeden']:  # Remove basic member too
                try:
                    self.cognito_client.admin_remove_user_from_group(
                        UserPoolId=USER_POOL_ID,
                        Username=TEST_USER,
                        GroupName=role
                    )
                except:
                    pass  # Ignore if role wasn't there
            
            # Add new roles
            for role in final_roles:
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USER,
                    GroupName=role
                )
            
            # Verify the changes are reflected
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            end_time = time.time()
            change_time = end_time - start_time
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            old_roles_removed = not any(role in current_groups for role in initial_roles)
            new_roles_added = all(role in current_groups for role in final_roles)
            
            success = old_roles_removed and new_roles_added and change_time < 300.0
            details = f"Replaced {initial_roles} with {final_roles}\n   Current groups: {current_groups}\n   Old roles removed: {old_roles_removed}\n   New roles added: {new_roles_added}"
            
            self.log_timing_test("Role replacement", change_time, success, details)
            return success
            
        except Exception as e:
            self.log_timing_test("Role replacement", 999.0, False, f"Error: {str(e)}")
            return False
    
    def test_rapid_successive_changes_timing(self):
        """Test timing for rapid successive role changes"""
        print("=" * 80)
        print("TEST 5: Rapid Successive Changes Timing")
        print("=" * 80)
        
        try:
            # Start with clean state
            self.reset_user_to_basic_member()
            
            # Define sequence of rapid changes
            change_sequence = [
                ('add', 'Members_Read_All'),
                ('add', 'Events_Read_All'),
                ('remove', 'Members_Read_All'),
                ('add', 'Products_Read_All'),
                ('remove', 'Events_Read_All'),
                ('add', 'Members_CRUD_All')
            ]
            
            # Measure time for rapid successive changes
            start_time = time.time()
            
            for action, role in change_sequence:
                if action == 'add':
                    self.cognito_client.admin_add_user_to_group(
                        UserPoolId=USER_POOL_ID,
                        Username=TEST_USER,
                        GroupName=role
                    )
                elif action == 'remove':
                    try:
                        self.cognito_client.admin_remove_user_from_group(
                            UserPoolId=USER_POOL_ID,
                            Username=TEST_USER,
                            GroupName=role
                        )
                    except:
                        pass  # Ignore if role wasn't there
            
            # Verify final state
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            end_time = time.time()
            change_time = end_time - start_time
            
            current_groups = [group['GroupName'] for group in groups_response['Groups']]
            expected_final_roles = ['hdcnLeden', 'Products_Read_All', 'Members_CRUD_All']
            final_state_correct = all(role in current_groups for role in expected_final_roles)
            
            success = final_state_correct and change_time < 300.0
            details = f"Performed {len(change_sequence)} rapid changes\n   Expected final roles: {expected_final_roles}\n   Current groups: {current_groups}\n   Final state correct: {final_state_correct}"
            
            self.log_timing_test("Rapid successive changes", change_time, success, details)
            return success
            
        except Exception as e:
            self.log_timing_test("Rapid successive changes", 999.0, False, f"Error: {str(e)}")
            return False
    
    def reset_user_to_basic_member(self):
        """Reset user to basic member role only"""
        try:
            # Get current groups
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER
            )
            
            # Remove from all groups
            for group in groups_response['Groups']:
                try:
                    self.cognito_client.admin_remove_user_from_group(
                        UserPoolId=USER_POOL_ID,
                        Username=TEST_USER,
                        GroupName=group['GroupName']
                    )
                except:
                    pass
            
            # Add back to basic member group
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='hdcnLeden'
            )
            
        except Exception as e:
            print(f"   Warning: Could not reset user to basic member: {str(e)}")
    
    def run_all_timing_tests(self):
        """Run all role change timing tests"""
        print("🚀 Starting Role Change Timing Tests")
        print(f"🎯 Task: Verify changes take effect immediately or within 5 minutes")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"👤 Test User: {TEST_USER}")
        print(f"⏱️ Timing Requirements: Immediate (<5s) or within 5 minutes (<300s)")
        print()
        
        # Ensure test user exists
        self.ensure_test_user_exists()
        
        # Run all timing tests
        test_results = []
        test_results.append(self.test_single_role_addition_timing())
        test_results.append(self.test_single_role_removal_timing())
        test_results.append(self.test_multiple_role_changes_timing())
        test_results.append(self.test_role_replacement_timing())
        test_results.append(self.test_rapid_successive_changes_timing())
        
        # Reset user to clean state
        self.reset_user_to_basic_member()
        
        # Analyze timing results
        timing_results = self.test_results['timing_tests']
        immediate_changes = sum(1 for test in timing_results if test['immediate'])
        within_5_min_changes = sum(1 for test in timing_results if test['within_5_minutes'])
        total_tests = len(timing_results)
        passed_tests = sum(test_results)
        
        # Calculate timing statistics
        change_times = [test['change_time_seconds'] for test in timing_results if test['success']]
        avg_time = sum(change_times) / len(change_times) if change_times else 0
        max_time = max(change_times) if change_times else 0
        min_time = min(change_times) if change_times else 0
        
        # Summary
        print("=" * 80)
        print("ROLE CHANGE TIMING TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()
        print("TIMING ANALYSIS:")
        print(f"  Immediate changes (<5s): {immediate_changes}/{total_tests}")
        print(f"  Within 5 minutes (<300s): {within_5_min_changes}/{total_tests}")
        print(f"  Average change time: {avg_time:.2f}s")
        print(f"  Fastest change time: {min_time:.2f}s")
        print(f"  Slowest change time: {max_time:.2f}s")
        print()
        
        if passed_tests == total_tests and within_5_min_changes == total_tests:
            print("🎉 All role change timing tests passed!")
            print("✅ Role changes take effect immediately or within 5 minutes")
            if immediate_changes == total_tests:
                print("✅ All changes were immediate (<5 seconds)")
            else:
                print(f"✅ {immediate_changes}/{total_tests} changes were immediate")
                print(f"✅ {within_5_min_changes - immediate_changes}/{total_tests} changes were within 5 minutes")
            print(f"✅ Average change time: {avg_time:.2f} seconds")
        else:
            print("❌ Some role change timing tests failed!")
            if within_5_min_changes < total_tests:
                print(f"❌ {total_tests - within_5_min_changes} changes exceeded 5 minute limit")
            if passed_tests < total_tests:
                print(f"❌ {total_tests - passed_tests} tests failed due to other issues")
        
        print()
        print("🔄 Next Steps:")
        if passed_tests == total_tests and within_5_min_changes == total_tests:
            print("  1. ✅ Role change timing requirements are met")
            print("  2. ✅ Changes are effective immediately or within acceptable timeframe")
            print("  3. 🔄 Frontend can rely on immediate role updates")
        else:
            print("  1. ❌ Investigate slow role changes")
            print("  2. 🔄 Check AWS Cognito service performance")
            print("  3. 🔄 Consider caching strategies if needed")
        
        # Save results
        results_file = f'role_change_timing_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"📄 Detailed results saved to: {results_file}")
        
        return passed_tests == total_tests and within_5_min_changes == total_tests

if __name__ == "__main__":
    tester = RoleChangeTimingTest()
    success = tester.run_all_timing_tests()
    exit(0 if success else 1)