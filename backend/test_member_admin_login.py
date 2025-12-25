#!/usr/bin/env python3
"""
Test Member Administration Role User Login

This script tests the login flow for the Member Administration role user,
verifying JWT token contents, role extraction, and permission calculation.
"""

import boto3
import json
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
CLIENT_ID = "7p5t7sjl2s1rcu1emn85h20qeh"
REGION = "eu-west-1"

# Test user credentials
TEST_USERNAME = "test.memberadmin@hdcn-test.nl"
## TEMP_PASSWORD = ""

# Expected roles for Member Administration user
EXPECTED_ROLES = [
    "Members_CRUD_All",
    "Events_Read_All", 
    "Products_Read_All",
    "Communication_Read_All",
    "System_User_Management"
]

class MemberAdminLoginTest:
    """Test Member Administration role user login and JWT token validation"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.test_results = []
        self.access_token = None
        self.id_token = None
        self.refresh_token = None
        
    def log_result(self, test_name: str, success: bool, details: str = "", error: Exception = None):
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
        
    def test_1_user_exists_and_has_roles(self):
        """Test 1: Verify test user exists and has correct role assignments"""
        print("=" * 70)
        print("TEST 1: User Existence and Role Verification")
        print("=" * 70)
        
        try:
            # Get user details
            user_response = self.cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USERNAME
            )
            
            # Get user's groups
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USERNAME
            )
            
            user_status = user_response.get('UserStatus')
            user_enabled = user_response.get('Enabled')
            assigned_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
            
            # Check if user exists and is enabled
            user_exists = user_status is not None and user_enabled
            
            # Check if user has all expected roles
            has_all_roles = all(role in assigned_groups for role in EXPECTED_ROLES)
            missing_roles = [role for role in EXPECTED_ROLES if role not in assigned_groups]
            extra_roles = [role for role in assigned_groups if role not in EXPECTED_ROLES]
            
            self.log_result(
                "User existence check",
                user_exists,
                f"Status: {user_status}, Enabled: {user_enabled}"
            )
            
            self.log_result(
                "Role assignment verification",
                has_all_roles,
                f"Assigned groups: {assigned_groups}\n" +
                f"   Expected roles: {EXPECTED_ROLES}\n" +
                (f"   Missing roles: {missing_roles}\n" if missing_roles else "") +
                (f"   Extra roles: {extra_roles}" if extra_roles else "")
            )
            
            return user_exists and has_all_roles
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotFoundException':
                self.log_result(
                    "User existence check",
                    False,
                    f"User {TEST_USERNAME} not found. Run create_test_users.py first.",
                    e
                )
            else:
                self.log_result(
                    "User existence check",
                    False,
                    f"Error checking user: {error_code}",
                    e
                )
            return False
        except Exception as e:
            self.log_result(
                "User existence check",
                False,
                "Unexpected error checking user",
                e
            )
            return False
    
    def test_2_password_change_required(self):
        """Test 2: Handle password change requirement for new users"""
        print("=" * 70)
        print("TEST 2: Password Change Requirement")
        print("=" * 70)
        
        try:
            # Check if user needs to change password
            user_response = self.cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USERNAME
            )
            
            user_status = user_response.get('UserStatus')
            
            if user_status == 'FORCE_CHANGE_PASSWORD':
                print("🔄 User requires password change. Setting new password...")
                
                # Set permanent password
                new_password = 1
                self.cognito_client.admin_set_user_password(
                    UserPoolId=USER_POOL_ID,
                    Username=TEST_USERNAME,
                    Password=new_password,
                    Permanent=True
                )
                
                self.log_result(
                    "Password change handling",
                    True,
                    f"Password set for user. Status was: {user_status}"
                )
                
                # Update password for subsequent tests
                global TEMP_PASSWORD
                TEMP_PASSWORD = new_password
                
            elif user_status == 'CONFIRMED':
                self.log_result(
                    "Password status check",
                    True,
                    f"User already confirmed. Status: {user_status}"
                )
            else:
                self.log_result(
                    "Password status check",
                    False,
                    f"Unexpected user status: {user_status}"
                )
                return False
                
            return True
            
        except ClientError as e:
            self.log_result(
                "Password change handling",
                False,
                f"Error handling password change: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Password change handling",
                False,
                "Unexpected error handling password change",
                e
            )
            return False
    
    def test_3_authentication_flow(self):
        """Test 3: Test authentication flow and token retrieval"""
        print("=" * 70)
        print("TEST 3: Authentication Flow")
        print("=" * 70)
        
        try:
            # Use USER_SRP_AUTH flow (already enabled in your configuration)
            # This is the same flow real users would use
            auth_response = self.cognito_client.initiate_auth(
                ClientId=CLIENT_ID,
                AuthFlow='USER_SRP_AUTH',
                AuthParameters={
                    'USERNAME': TEST_USERNAME,
                    'PASSWORD': TEMP_PASSWORD
                }
            )
            
            # Extract tokens
            auth_result = auth_response.get('AuthenticationResult', {})
            self.access_token = auth_result.get('AccessToken')
            self.id_token = auth_result.get('IdToken')
            self.refresh_token = auth_result.get('RefreshToken')
            
            token_type = auth_result.get('TokenType')
            expires_in = auth_result.get('ExpiresIn')
            
            tokens_received = bool(self.access_token and self.id_token and self.refresh_token)
            
            self.log_result(
                "Authentication success",
                tokens_received,
                f"Token type: {token_type}, Expires in: {expires_in}s\n" +
                f"   Access token length: {len(self.access_token) if self.access_token else 0}\n" +
                f"   ID token length: {len(self.id_token) if self.id_token else 0}\n" +
                f"   Refresh token length: {len(self.refresh_token) if self.refresh_token else 0}"
            )
            
            return tokens_received
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.log_result(
                "Authentication flow",
                False,
                f"Authentication failed: {error_code}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Authentication flow",
                False,
                "Unexpected error during authentication",
                e
            )
            return False
    
    def decode_jwt_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token payload (without signature verification)"""
        try:
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return None
                
            # Decode payload (second part)
            payload = parts[1]
            
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
                
            # Decode base64
            decoded_bytes = base64.urlsafe_b64decode(payload)
            payload_json = json.loads(decoded_bytes.decode('utf-8'))
            
            return payload_json
            
        except Exception as e:
            print(f"Error decoding JWT: {e}")
            return None
    
    def test_4_jwt_token_contents(self):
        """Test 4: Verify JWT token contains correct role information"""
        print("=" * 70)
        print("TEST 4: JWT Token Contents Verification")
        print("=" * 70)
        
        if not self.id_token:
            self.log_result(
                "JWT token verification",
                False,
                "No ID token available for verification"
            )
            return False
        
        try:
            # Decode ID token payload
            id_payload = self.decode_jwt_payload(self.id_token)
            
            if not id_payload:
                self.log_result(
                    "JWT token decoding",
                    False,
                    "Failed to decode ID token payload"
                )
                return False
            
            # Extract key claims
            username = id_payload.get('cognito:username')
            email = id_payload.get('email')
            groups = id_payload.get('cognito:groups', [])
            token_use = id_payload.get('token_use')
            
            # Verify basic token structure
            basic_structure_valid = (
                username == TEST_USERNAME and
                email == TEST_USERNAME and
                token_use == 'id'
            )
            
            self.log_result(
                "JWT basic structure",
                basic_structure_valid,
                f"Username: {username}, Email: {email}, Token use: {token_use}"
            )
            
            # Verify groups claim contains expected roles
            has_groups_claim = 'cognito:groups' in id_payload
            groups_match_expected = set(groups) == set(EXPECTED_ROLES)
            missing_groups = [role for role in EXPECTED_ROLES if role not in groups]
            extra_groups = [group for group in groups if group not in EXPECTED_ROLES]
            
            self.log_result(
                "JWT groups claim verification",
                has_groups_claim and groups_match_expected,
                f"Groups in token: {groups}\n" +
                f"   Expected groups: {EXPECTED_ROLES}\n" +
                (f"   Missing groups: {missing_groups}\n" if missing_groups else "") +
                (f"   Extra groups: {extra_groups}" if extra_groups else "")
            )
            
            # Print full token payload for debugging
            print("🔍 Full ID Token Payload:")
            print(json.dumps(id_payload, indent=2))
            print()
            
            return basic_structure_valid and has_groups_claim and groups_match_expected
            
        except Exception as e:
            self.log_result(
                "JWT token contents verification",
                False,
                "Error verifying JWT token contents",
                e
            )
            return False
    
    def test_5_role_extraction_simulation(self):
        """Test 5: Simulate frontend role extraction from JWT token"""
        print("=" * 70)
        print("TEST 5: Role Extraction Simulation")
        print("=" * 70)
        
        if not self.id_token:
            self.log_result(
                "Role extraction simulation",
                False,
                "No ID token available for role extraction"
            )
            return False
        
        try:
            # Simulate frontend getUserRoles() function
            def getUserRoles(id_token: str) -> List[str]:
                """Simulate frontend role extraction function"""
                payload = self.decode_jwt_payload(id_token)
                if not payload:
                    return []
                return payload.get('cognito:groups', [])
            
            # Extract roles using simulated function
            extracted_roles = getUserRoles(self.id_token)
            
            # Simulate permission calculation
            ROLE_PERMISSIONS = {
                "hdcnLeden": ["view_own_profile", "webshop_access"],
                "Members_CRUD_All": ["members_create", "members_read", "members_update", "members_delete", "members_admin_fields"],
                "Events_Read_All": ["events_read", "events_list"],
                "Products_Read_All": ["products_read", "products_list"],
                "Communication_Read_All": ["communication_read", "communication_list"],
                "System_User_Management": ["users_manage", "roles_assign", "system_admin"]
            }
            
            def calculatePermissions(roles: List[str]) -> List[str]:
                """Simulate frontend permission calculation function"""
                permissions = set()
                for role in roles:
                    role_perms = ROLE_PERMISSIONS.get(role, [])
                    permissions.update(role_perms)
                return sorted(list(permissions))
            
            calculated_permissions = calculatePermissions(extracted_roles)
            
            # Verify role extraction worked
            roles_extracted_correctly = set(extracted_roles) == set(EXPECTED_ROLES)
            has_admin_permissions = any(perm.startswith('members_') for perm in calculated_permissions)
            has_system_permissions = 'system_admin' in calculated_permissions
            
            self.log_result(
                "Role extraction from JWT",
                roles_extracted_correctly,
                f"Extracted roles: {extracted_roles}"
            )
            
            self.log_result(
                "Permission calculation",
                has_admin_permissions and has_system_permissions,
                f"Calculated permissions ({len(calculated_permissions)}): {calculated_permissions}"
            )
            
            # Print role-to-permission mapping for verification
            print("🔐 Role-to-Permission Mapping:")
            for role in extracted_roles:
                perms = ROLE_PERMISSIONS.get(role, [])
                print(f"  {role}: {perms}")
            print()
            
            return roles_extracted_correctly and has_admin_permissions and has_system_permissions
            
        except Exception as e:
            self.log_result(
                "Role extraction simulation",
                False,
                "Error simulating role extraction",
                e
            )
            return False
    
    def test_6_token_validation_with_cognito(self):
        """Test 6: Validate tokens with Cognito service"""
        print("=" * 70)
        print("TEST 6: Token Validation with Cognito")
        print("=" * 70)
        
        if not self.access_token:
            self.log_result(
                "Token validation",
                False,
                "No access token available for validation"
            )
            return False
        
        try:
            # Use access token to get user info (validates token)
            user_info = self.cognito_client.get_user(
                AccessToken=self.access_token
            )
            
            username = user_info.get('Username')
            user_attributes = {attr['Name']: attr['Value'] for attr in user_info.get('UserAttributes', [])}
            
            token_valid = username == TEST_USERNAME
            
            self.log_result(
                "Access token validation",
                token_valid,
                f"Token validated for user: {username}\n" +
                f"   Email: {user_attributes.get('email')}\n" +
                f"   Given name: {user_attributes.get('given_name')}\n" +
                f"   Family name: {user_attributes.get('family_name')}"
            )
            
            return token_valid
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.log_result(
                "Token validation with Cognito",
                False,
                f"Token validation failed: {error_code}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Token validation with Cognito",
                False,
                "Unexpected error during token validation",
                e
            )
            return False
    
    def run_all_tests(self):
        """Run all Member Administration login tests"""
        print("🚀 Starting Member Administration Role Login Tests")
        print(f"👤 Test user: {TEST_USERNAME}")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"🔑 Client ID: {CLIENT_ID}")
        print()
        
        # Run all tests in sequence
        test_1_success = self.test_1_user_exists_and_has_roles()
        test_2_success = self.test_2_password_change_required()
        test_3_success = self.test_3_authentication_flow()
        test_4_success = self.test_4_jwt_token_contents()
        test_5_success = self.test_5_role_extraction_simulation()
        test_6_success = self.test_6_token_validation_with_cognito()
        
        # Summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()
        
        if passed_tests == total_tests:
            print("🎉 All Member Administration login tests passed!")
            print("✅ Member Administration role user can authenticate successfully")
            print("✅ JWT tokens contain correct role information")
            print("✅ Role extraction and permission calculation work correctly")
        else:
            print("⚠️ Some tests failed. Check details above.")
            print("❌ Member Administration login may not be working correctly")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f'member_admin_login_test_results_{timestamp}.json'
        
        with open(results_file, 'w') as f:
            json.dump({
                'test_summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests,
                    'success_rate': f"{(passed_tests/total_tests)*100:.1f}%"
                },
                'test_results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: {results_file}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = MemberAdminLoginTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)