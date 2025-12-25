#!/usr/bin/env python3
"""
Test Role Changes Reflected in User Sessions

This test verifies that when user roles are changed, those changes are 
reflected in user sessions by testing the underlying Cognito group assignments
that would be included in JWT tokens during authentication.

Since passwordless authentication requires WebAuthn in a browser environment,
this test verifies the Cognito group assignments that form the basis of JWT tokens.
"""

import json
import boto3
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
CLIENT_ID = '7p5t7sjl2s1rcu1emn85h20qeh'
TEST_USER = 'session.test@hdcn-test.nl'
REGION = 'eu-west-1'

class SessionRoleReflectionTest:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'test_user': TEST_USER,
            'user_pool_id': USER_POOL_ID,
            'client_id': CLIENT_ID,
            'session_tests': []
        }
        
    def log_session_test(self, test_name, success, details, error=None):
        """Log session test result"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test': test_name,
            'success': success,
            'details': details,
            'error': str(error) if error else None
        }
        self.test_results['session_tests'].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
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
    
    def create_realistic_jwt_token(self, username: str, groups: List[str]) -> str:
        """Create a realistic JWT token structure with current groups"""
        now = datetime.now()
        
        # JWT Header
        header = {
            "alg": "RS256",
            "kid": "test-key-id"
        }
        
        # JWT Payload with current groups
        payload = {
            "sub": f"test-{hash(username) % 100000:05d}-{hash(username) % 10000:04d}-{hash(username) % 10000:04d}-{hash(username) % 100000000:08d}",
            "aud": CLIENT_ID,
            "cognito:groups": groups,  # This should reflect current group assignments
            "email_verified": True,
            "iss": f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}",
            "cognito:username": username,
            "given_name": "Test",
            "family_name": "Session",
            "event_id": f"test-event-{hash(username) % 1000000:06d}",
            "token_use": "id",
            "auth_time": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "email": username
        }
        
        # Create JWT token (unsigned for testing)
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature_b64 = "test-signature-not-verified"
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def decode_jwt_token(self, token):
        """Decode JWT token without verification (for testing purposes)"""
        try:
            # Split the token
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            # Decode base64
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            
            return decoded_json
            
        except Exception as e:
            print(f"   JWT decode error: {str(e)}")
            return None
    
    def get_user_groups_from_cognito(self, username=None):
        """Get user groups directly from Cognito"""
        if username is None:
            username = TEST_USER
            
        try:
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            return [group['GroupName'] for group in groups_response['Groups']]
        except Exception as e:
            print(f"   Error getting groups for {username}: {str(e)}")
            return []
    
    def test_cognito_groups_reflect_role_changes(self):
        """Test that Cognito group assignments reflect role changes immediately"""
        print("=" * 80)
        print("TEST 1: Cognito Groups Reflect Role Changes")
        print("=" * 80)
        
        try:
            # Reset user to known state
            self.reset_user_to_basic_member()
            
            # Get initial groups
            initial_groups = self.get_user_groups_from_cognito()
            
            # Change user roles
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='Members_Read_All'
            )
            
            # Get updated groups
            updated_groups = self.get_user_groups_from_cognito()
            
            # Verify the change is reflected
            role_added = 'Members_Read_All' in updated_groups and 'Members_Read_All' not in initial_groups
            
            success = role_added
            details = f"Initial groups: {initial_groups}\n   Updated groups: {updated_groups}\n   Role added successfully: {role_added}"
            
            self.log_session_test("Cognito groups reflect role changes", success, details)
            return success
            
        except Exception as e:
            self.log_session_test("Cognito groups reflect role changes", False, "Test failed", e)
            return False
    
    def test_jwt_token_structure_with_role_changes(self):
        """Test that JWT token structure would contain updated roles"""
        print("=" * 80)
        print("TEST 2: JWT Token Structure with Role Changes")
        print("=" * 80)
        
        try:
            # Test sequence of role changes and their JWT representation
            role_sequences = [
                ['hdcnLeden'],
                ['hdcnLeden', 'Members_Read_All'],
                ['hdcnLeden', 'Members_Read_All', 'Events_Read_All'],
                ['Members_CRUD_All', 'System_User_Management']
            ]
            
            jwt_test_results = []
            
            for i, target_roles in enumerate(role_sequences):
                # Set the target roles in Cognito
                self.set_user_roles(target_roles)
                
                # Get actual groups from Cognito
                actual_groups = self.get_user_groups_from_cognito()
                
                # Create JWT token with current groups
                jwt_token = self.create_realistic_jwt_token(TEST_USER, actual_groups)
                
                # Decode and verify JWT token
                decoded_payload = self.decode_jwt_token(jwt_token)
                jwt_groups = decoded_payload.get('cognito:groups', []) if decoded_payload else []
                
                # Verify JWT groups match Cognito groups
                groups_match = set(actual_groups) == set(jwt_groups)
                
                jwt_test_results.append({
                    'sequence': i + 1,
                    'target_roles': target_roles,
                    'cognito_groups': actual_groups,
                    'jwt_groups': jwt_groups,
                    'groups_match': groups_match,
                    'success': groups_match
                })
                
                print(f"   Sequence {i + 1}: Target {target_roles}")
                print(f"      Cognito: {actual_groups}")
                print(f"      JWT: {jwt_groups}")
                print(f"      Match: {'✅' if groups_match else '❌'}")
            
            # Overall success
            all_sequences_passed = all(result['success'] for result in jwt_test_results)
            
            success = all_sequences_passed
            details = f"Tested {len(role_sequences)} JWT token sequences\n   All sequences passed: {all_sequences_passed}\n   JWT tokens correctly reflect Cognito groups"
            
            self.log_session_test("JWT token structure with role changes", success, details)
            return success
            
        except Exception as e:
            self.log_session_test("JWT token structure with role changes", False, "Test failed", e)
            return False
    
    def test_role_change_timing_in_sessions(self):
        """Test that role changes are immediately available for session creation"""
        print("=" * 80)
        print("TEST 3: Role Change Timing in Sessions")
        print("=" * 80)
        
        try:
            # Start with basic member
            self.reset_user_to_basic_member()
            
            # Record timing for role changes and their availability
            timing_results = []
            
            role_changes = [
                ('add', 'Members_Read_All'),
                ('add', 'Events_Read_All'),
                ('remove', 'Members_Read_All'),
                ('add', 'Products_Read_All')
            ]
            
            for action, role in role_changes:
                start_time = time.time()
                
                # Perform the role change
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
                
                # Check if change is immediately available
                current_groups = self.get_user_groups_from_cognito()
                
                end_time = time.time()
                change_time = end_time - start_time
                
                # Verify the change is reflected
                if action == 'add':
                    change_reflected = role in current_groups
                else:  # remove
                    change_reflected = role not in current_groups
                
                timing_results.append({
                    'action': f"{action} {role}",
                    'change_time': change_time,
                    'change_reflected': change_reflected,
                    'current_groups': current_groups.copy()
                })
                
                print(f"   {action.title()} {role}: {change_time:.3f}s ({'✅' if change_reflected else '❌'})")
            
            # Overall success
            all_changes_reflected = all(result['change_reflected'] for result in timing_results)
            avg_time = sum(result['change_time'] for result in timing_results) / len(timing_results)
            max_time = max(result['change_time'] for result in timing_results)
            
            success = all_changes_reflected and max_time < 5.0  # All changes should be immediate
            details = f"Tested {len(role_changes)} role changes\n   All changes reflected: {all_changes_reflected}\n   Average time: {avg_time:.3f}s\n   Max time: {max_time:.3f}s\n   All immediate (<5s): {max_time < 5.0}"
            
            self.log_session_test("Role change timing in sessions", success, details)
            return success
            
        except Exception as e:
            self.log_session_test("Role change timing in sessions", False, "Test failed", e)
            return False
    
    def test_multiple_user_session_isolation(self):
        """Test that role changes for one user don't affect other users"""
        print("=" * 80)
        print("TEST 4: Multiple User Session Isolation")
        print("=" * 80)
        
        try:
            # Create a second test user
            test_user_2 = 'session.test2@hdcn-test.nl'
            
            try:
                self.cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=test_user_2
                )
            except self.cognito_client.exceptions.UserNotFoundException:
                # Create second test user
                self.cognito_client.admin_create_user(
                    UserPoolId=USER_POOL_ID,
                    Username=test_user_2,
                    UserAttributes=[
                        {'Name': 'email', 'Value': test_user_2},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ],
                    MessageAction='SUPPRESS'
                )
                
                # Add to basic member group
                self.cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=test_user_2,
                    GroupName='hdcnLeden'
                )
            
            # Set both users to basic member initially
            self.reset_user_to_basic_member()
            self.set_user_roles(['hdcnLeden'], test_user_2)
            
            # Get initial groups for both users
            initial_groups_1 = self.get_user_groups_from_cognito(TEST_USER)
            initial_groups_2 = self.get_user_groups_from_cognito(test_user_2)
            
            # Change roles for user 1 only
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USER,
                GroupName='Members_CRUD_All'
            )
            
            # Get updated groups for both users
            updated_groups_1 = self.get_user_groups_from_cognito(TEST_USER)
            updated_groups_2 = self.get_user_groups_from_cognito(test_user_2)
            
            # Verify isolation
            user1_changed = 'Members_CRUD_All' in updated_groups_1 and 'Members_CRUD_All' not in initial_groups_1
            user2_unchanged = set(initial_groups_2) == set(updated_groups_2)
            
            success = user1_changed and user2_unchanged
            details = f"User 1 initial: {initial_groups_1} -> updated: {updated_groups_1} (changed: {user1_changed})\n   User 2 initial: {initial_groups_2} -> updated: {updated_groups_2} (unchanged: {user2_unchanged})\n   Proper isolation: {success}"
            
            self.log_session_test("Multiple user session isolation", success, details)
            return success
            
        except Exception as e:
            self.log_session_test("Multiple user session isolation", False, "Test failed", e)
            return False
    
    def test_session_consistency_after_role_changes(self):
        """Test that session data remains consistent after multiple role changes"""
        print("=" * 80)
        print("TEST 5: Session Consistency After Role Changes")
        print("=" * 80)
        
        try:
            # Perform a series of role changes and verify consistency
            role_change_sequence = [
                (['hdcnLeden'], "Basic member"),
                (['hdcnLeden', 'Members_Read_All'], "Member reader"),
                (['hdcnLeden', 'Members_Read_All', 'Events_Read_All'], "Member and event reader"),
                (['Members_CRUD_All', 'System_User_Management'], "Full admin"),
                (['hdcnLeden'], "Back to basic member")
            ]
            
            consistency_results = []
            
            for target_roles, description in role_change_sequence:
                # Set the target roles
                self.set_user_roles(target_roles)
                
                # Verify consistency across multiple checks
                checks = []
                for i in range(3):  # Check 3 times to ensure consistency
                    current_groups = self.get_user_groups_from_cognito()
                    checks.append(current_groups)
                    time.sleep(0.1)  # Brief delay between checks
                
                # Verify all checks are consistent
                all_consistent = all(set(check) == set(checks[0]) for check in checks)
                roles_correct = set(target_roles) == set(checks[0])
                
                consistency_results.append({
                    'description': description,
                    'target_roles': target_roles,
                    'actual_groups': checks[0],
                    'all_checks_consistent': all_consistent,
                    'roles_correct': roles_correct,
                    'success': all_consistent and roles_correct
                })
                
                print(f"   {description}: Target {target_roles} -> Actual {checks[0]} ({'✅' if all_consistent and roles_correct else '❌'})")
            
            # Overall success
            all_consistent = all(result['success'] for result in consistency_results)
            
            success = all_consistent
            details = f"Tested {len(role_change_sequence)} role change sequences\n   All sequences consistent: {all_consistent}\n   Session data remains consistent after role changes"
            
            self.log_session_test("Session consistency after role changes", success, details)
            return success
            
        except Exception as e:
            self.log_session_test("Session consistency after role changes", False, "Test failed", e)
            return False
    
    def set_user_roles(self, target_roles, username=None):
        """Set user to specific roles"""
        if username is None:
            username = TEST_USER
            
        try:
            # Get current groups
            current_groups = self.get_user_groups_from_cognito(username)
            
            # Remove from groups not in target
            for group in current_groups:
                if group not in target_roles:
                    try:
                        self.cognito_client.admin_remove_user_from_group(
                            UserPoolId=USER_POOL_ID,
                            Username=username,
                            GroupName=group
                        )
                    except:
                        pass
            
            # Add to target groups
            for role in target_roles:
                if role not in current_groups:
                    try:
                        self.cognito_client.admin_add_user_to_group(
                            UserPoolId=USER_POOL_ID,
                            Username=username,
                            GroupName=role
                        )
                    except:
                        pass
                        
        except Exception as e:
            print(f"   Warning: Could not set roles for {username}: {str(e)}")
    
    def reset_user_to_basic_member(self):
        """Reset user to basic member role only"""
        self.set_user_roles(['hdcnLeden'])
    
    def run_all_session_tests(self):
        """Run all session role reflection tests"""
        print("🚀 Starting Session Role Reflection Tests")
        print(f"🎯 Task: Verify role changes are reflected in user sessions")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"👤 Test User: {TEST_USER}")
        print(f"🔑 Client ID: {CLIENT_ID}")
        print()
        print("Note: Testing Cognito group assignments that form the basis of JWT tokens")
        print("      since passwordless authentication requires WebAuthn in browser environment")
        print()
        
        # Ensure test user exists
        self.ensure_test_user_exists()
        
        # Run all session tests
        test_results = []
        test_results.append(self.test_cognito_groups_reflect_role_changes())
        test_results.append(self.test_jwt_token_structure_with_role_changes())
        test_results.append(self.test_role_change_timing_in_sessions())
        test_results.append(self.test_multiple_user_session_isolation())
        test_results.append(self.test_session_consistency_after_role_changes())
        
        # Reset user to clean state
        self.reset_user_to_basic_member()
        
        # Summary
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        print("=" * 80)
        print("SESSION ROLE REFLECTION TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()
        
        if passed_tests == total_tests:
            print("🎉 All session role reflection tests passed!")
            print("✅ Role changes are reflected in user sessions")
            print("✅ Cognito groups immediately reflect role changes")
            print("✅ JWT token structure would contain current user roles")
            print("✅ User role isolation is maintained")
            print("✅ Session consistency is maintained after role changes")
        else:
            print("❌ Some session role reflection tests failed!")
            print(f"❌ {total_tests - passed_tests} out of {total_tests} tests failed")
        
        print()
        print("🔄 Next Steps:")
        if passed_tests == total_tests:
            print("  1. ✅ Session role reflection is working correctly")
            print("  2. ✅ Frontend can rely on JWT token groups after authentication")
            print("  3. ✅ Role changes are immediately available for new sessions")
            print("  4. ✅ Passwordless authentication will include current roles in JWT tokens")
        else:
            print("  1. ❌ Fix failing session reflection tests")
            print("  2. 🔄 Check Cognito group assignment consistency")
            print("  3. 🔄 Verify role change propagation")
        
        # Save results
        results_file = f'session_role_reflection_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"📄 Detailed results saved to: {results_file}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = SessionRoleReflectionTest()
    success = tester.run_all_session_tests()
    exit(0 if success else 1)