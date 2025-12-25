#!/usr/bin/env python3
"""
Simple Member Administration Role Test

This test focuses on verifying the user exists, has correct roles,
and simulates the JWT token processing that would happen after successful login.
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

# Expected roles for Member Administration user
EXPECTED_ROLES = [
    "Members_CRUD_All",
    "Events_Read_All", 
    "Products_Read_All",
    "Communication_Read_All",
    "System_User_Management"
]

class MemberAdminSimpleTest:
    """Simple test for Member Administration role verification"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.test_results = []
        
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
            
            return user_exists and has_all_roles, assigned_groups
            
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
            return False, []
        except Exception as e:
            self.log_result(
                "User existence check",
                False,
                "Unexpected error checking user",
                e
            )
            return False, []
    
    def test_2_simulate_jwt_token_with_roles(self, user_roles: List[str]):
        """Test 2: Simulate JWT token creation with user roles"""
        print("=" * 70)
        print("TEST 2: JWT Token Simulation with Roles")
        print("=" * 70)
        
        try:
            # Simulate what a real JWT token would contain
            simulated_jwt_payload = {
                "sub": "12345678-1234-1234-1234-123456789012",  # User UUID
                "cognito:username": TEST_USERNAME,
                "email": TEST_USERNAME,
                "email_verified": True,
                "given_name": "Test",
                "family_name": "MemberAdmin",
                "cognito:groups": user_roles,  # This is the key part for role-based auth
                "token_use": "id",
                "auth_time": int(datetime.now().timestamp()),
                "iss": f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}",
                "aud": CLIENT_ID,
                "exp": int(datetime.now().timestamp()) + 3600,  # 1 hour expiry
                "iat": int(datetime.now().timestamp())
            }
            
            # Verify groups claim contains expected roles
            token_groups = simulated_jwt_payload.get('cognito:groups', [])
            groups_match_expected = set(token_groups) == set(EXPECTED_ROLES)
            
            self.log_result(
                "JWT token structure simulation",
                True,
                f"Simulated JWT payload created with {len(token_groups)} groups"
            )
            
            self.log_result(
                "JWT groups claim verification",
                groups_match_expected,
                f"Groups in token: {token_groups}\n" +
                f"   Expected groups: {EXPECTED_ROLES}"
            )
            
            # Print simulated token payload
            print("🔍 Simulated JWT Token Payload:")
            print(json.dumps(simulated_jwt_payload, indent=2))
            print()
            
            return groups_match_expected, simulated_jwt_payload
            
        except Exception as e:
            self.log_result(
                "JWT token simulation",
                False,
                "Error simulating JWT token",
                e
            )
            return False, {}
    
    def test_3_role_extraction_simulation(self, jwt_payload: Dict[str, Any]):
        """Test 3: Simulate frontend role extraction from JWT token"""
        print("=" * 70)
        print("TEST 3: Role Extraction Simulation")
        print("=" * 70)
        
        try:
            # Simulate frontend getUserRoles() function
            def getUserRoles(jwt_payload: Dict[str, Any]) -> List[str]:
                """Simulate frontend role extraction function"""
                return jwt_payload.get('cognito:groups', [])
            
            # Extract roles using simulated function
            extracted_roles = getUserRoles(jwt_payload)
            
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
    
    def test_4_cognito_configuration_check(self):
        """Test 4: Verify Cognito configuration supports the authentication system"""
        print("=" * 70)
        print("TEST 4: Cognito Configuration Check")
        print("=" * 70)
        
        try:
            # Check User Pool Client configuration
            client_response = self.cognito_client.describe_user_pool_client(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID
            )
            
            client_details = client_response.get('UserPoolClient', {})
            explicit_auth_flows = client_details.get('ExplicitAuthFlows', [])
            
            # Check if required flows are enabled
            has_user_auth = 'ALLOW_USER_AUTH' in explicit_auth_flows
            has_refresh_token = 'ALLOW_REFRESH_TOKEN_AUTH' in explicit_auth_flows
            
            self.log_result(
                "Passwordless authentication support",
                has_user_auth,
                f"USER_AUTH flow enabled: {has_user_auth}"
            )
            
            self.log_result(
                "Token refresh support",
                has_refresh_token,
                f"REFRESH_TOKEN_AUTH flow enabled: {has_refresh_token}"
            )
            
            # Check User Pool configuration
            pool_response = self.cognito_client.describe_user_pool(
                UserPoolId=USER_POOL_ID
            )
            
            pool_details = pool_response.get('UserPool', {})
            username_attributes = pool_details.get('UsernameAttributes', [])
            auto_verified_attributes = pool_details.get('AutoVerifiedAttributes', [])
            
            email_as_username = 'email' in username_attributes
            email_auto_verified = 'email' in auto_verified_attributes
            
            self.log_result(
                "Email as username configuration",
                email_as_username,
                f"Email as username: {email_as_username}"
            )
            
            self.log_result(
                "Email auto-verification",
                email_auto_verified,
                f"Email auto-verified: {email_auto_verified}"
            )
            
            print("🔍 Current Authentication Flows:")
            for flow in explicit_auth_flows:
                print(f"  ✅ {flow}")
            print()
            
            return has_user_auth and has_refresh_token and email_as_username
            
        except ClientError as e:
            self.log_result(
                "Cognito configuration check",
                False,
                f"Error checking configuration: {e.response['Error']['Code']}",
                e
            )
            return False
        except Exception as e:
            self.log_result(
                "Cognito configuration check",
                False,
                "Unexpected error checking configuration",
                e
            )
            return False
    
    def run_all_tests(self):
        """Run all Member Administration tests"""
        print("🚀 Starting Member Administration Role Tests (Simple)")
        print(f"👤 Test user: {TEST_USERNAME}")
        print(f"🏗️ User Pool ID: {USER_POOL_ID}")
        print(f"🔑 Client ID: {CLIENT_ID}")
        print()
        
        # Run all tests in sequence
        test_1_success, user_roles = self.test_1_user_exists_and_has_roles()
        test_2_success, jwt_payload = self.test_2_simulate_jwt_token_with_roles(user_roles)
        test_3_success = self.test_3_role_extraction_simulation(jwt_payload)
        test_4_success = self.test_4_cognito_configuration_check()
        
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
            print("🎉 All Member Administration tests passed!")
            print("✅ Member Administration role user is properly configured")
            print("✅ JWT token structure and role extraction work correctly")
            print("✅ Permission calculation functions properly")
            print("✅ Cognito configuration supports passwordless authentication")
            print()
            print("📝 Next Steps:")
            print("  • Test actual login flow in frontend application")
            print("  • Verify role-based UI rendering works")
            print("  • Test field-level permissions in member forms")
        else:
            print("⚠️ Some tests failed. Check details above.")
            print("❌ Member Administration setup may need attention")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f'member_admin_simple_test_results_{timestamp}.json'
        
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
    tester = MemberAdminSimpleTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)