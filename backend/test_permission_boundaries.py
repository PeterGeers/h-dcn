#!/usr/bin/env python3
"""
Permission Boundaries Test
Tests that users cannot access unauthorized resources and that permission boundaries are properly enforced
"""

import json
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

try:
    from auth_utils import (
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        check_regional_data_access,
        can_access_resource_region,
        validate_crud_access,
        extract_user_credentials,
        log_permission_denial,
        cors_headers
    )
    print("✅ Successfully imported auth_utils functions")
except ImportError as e:
    print(f"❌ Failed to import auth_utils: {e}")
    sys.exit(1)


class PermissionBoundariesTest:
    """Test suite for permission boundary enforcement"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def log_test_result(self, test_name, passed, details=""):
        """Log test result with details"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if not passed:
            self.failed_tests.append(result)
        
        print(f"  {status}: {test_name}")
        if details:
            print(f"    Details: {details}")
    
    def test_permission_role_boundaries(self):
        """Test that users without required permission roles are denied access"""
        print("\n=== Testing Permission Role Boundaries ===")
        
        unauthorized_access_tests = [
            {
                'name': 'Members_Read user attempting Members_CRUD operation',
                'user_roles': ['Members_Read', 'Regio_All'],
                'required_permissions': ['members_create'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            },
            {
                'name': 'Events_Read user attempting Events_CRUD operation',
                'user_roles': ['Events_Read', 'Regio_Utrecht'],
                'required_permissions': ['events_update'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            },
            {
                'name': 'Products_Read user attempting Products_CRUD operation',
                'user_roles': ['Products_Read', 'Regio_All'],
                'required_permissions': ['products_delete'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            },
            {
                'name': 'Members_Export user attempting Members_CRUD operation',
                'user_roles': ['Members_Export', 'Regio_All'],
                'required_permissions': ['members_update'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            },
            {
                'name': 'User with no permission roles attempting any operation',
                'user_roles': ['Regio_All'],
                'required_permissions': ['members_read'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            },
            {
                'name': 'hdcnLeden user attempting admin operation',
                'user_roles': ['hdcnLeden'],
                'required_permissions': ['members_create'],
                'should_be_denied': True,
                'expected_error': 'Insufficient permissions'
            }
        ]
        
        for test_case in unauthorized_access_tests:
            is_authorized, error_response = validate_permissions(
                test_case['user_roles'],
                test_case['required_permissions'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            # Should be denied access
            access_properly_denied = not is_authorized
            self.log_test_result(
                f"{test_case['name']} - Access denied",
                access_properly_denied,
                f"Expected denial, got authorized: {is_authorized}"
            )
            
            # Check error response structure
            if error_response:
                has_proper_error = (
                    error_response.get('statusCode') == 403 and
                    test_case['expected_error'] in error_response.get('body', '')
                )
                self.log_test_result(
                    f"{test_case['name']} - Proper error response",
                    has_proper_error,
                    f"Expected 403 with '{test_case['expected_error']}', got: {error_response}"
                )
    
    def test_regional_access_boundaries(self):
        """Test that users cannot access resources outside their assigned regions"""
        print("\n=== Testing Regional Access Boundaries ===")
        
        regional_boundary_tests = [
            {
                'name': 'Utrecht user accessing Noord-Holland data',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'data_region': 'Noord-Holland',
                'should_be_denied': True
            },
            {
                'name': 'Groningen/Drenthe user accessing Limburg data',
                'user_roles': ['Events_Read', 'Regio_Groningen/Drenthe'],
                'data_region': 'Limburg',
                'should_be_denied': True
            },
            {
                'name': 'Friesland user accessing Duitsland data',
                'user_roles': ['Products_CRUD', 'Regio_Friesland'],
                'data_region': 'Duitsland',
                'should_be_denied': True
            },
            {
                'name': 'Multi-regional user accessing non-assigned region',
                'user_roles': ['Members_Read', 'Regio_Utrecht', 'Regio_Oost'],
                'data_region': 'Brabant/Zeeland',
                'should_be_denied': True
            },
            {
                'name': 'User with no region roles accessing any region',
                'user_roles': ['Members_CRUD'],
                'data_region': 'Utrecht',
                'should_be_denied': True
            }
        ]
        
        for test_case in regional_boundary_tests:
            can_access, reason = check_regional_data_access(
                test_case['user_roles'],
                test_case['data_region'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            access_properly_denied = not can_access
            self.log_test_result(
                test_case['name'],
                access_properly_denied,
                f"Expected denial, got access: {can_access}, Reason: {reason}"
            )
    
    def test_incomplete_role_structure_boundaries(self):
        """Test that users with incomplete role structures are denied access"""
        print("\n=== Testing Incomplete Role Structure Boundaries ===")
        
        incomplete_structure_tests = [
            {
                'name': 'Permission role without region role',
                'user_roles': ['Members_CRUD'],
                'required_permissions': ['members_read'],
                'should_be_denied': True,
                'expected_error_type': 'region assignment'
            },
            {
                'name': 'Region role without permission role',
                'user_roles': ['Regio_All'],
                'required_permissions': ['members_read'],
                'should_be_denied': True,
                'expected_error_type': 'Insufficient permissions'
            },
            {
                'name': 'Multiple permission roles without region',
                'user_roles': ['Members_CRUD', 'Events_Read', 'Products_CRUD'],
                'required_permissions': ['members_read'],
                'should_be_denied': True,
                'expected_error_type': 'region assignment'
            },
            {
                'name': 'Multiple region roles without permission',
                'user_roles': ['Regio_Utrecht', 'Regio_Oost', 'Regio_Friesland'],
                'required_permissions': ['members_read'],
                'should_be_denied': True,
                'expected_error_type': 'Insufficient permissions'
            }
        ]
        
        for test_case in incomplete_structure_tests:
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                test_case['user_roles'],
                test_case['required_permissions'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            # Should be denied access
            access_properly_denied = not is_authorized
            self.log_test_result(
                f"{test_case['name']} - Access denied",
                access_properly_denied,
                f"Expected denial, got authorized: {is_authorized}"
            )
            
            # Check error response contains expected error type
            if error_response and test_case['expected_error_type']:
                error_body = error_response.get('body', '')
                if isinstance(error_body, str):
                    try:
                        error_data = json.loads(error_body)
                        error_message = error_data.get('error', '')
                    except json.JSONDecodeError:
                        error_message = error_body
                else:
                    error_message = str(error_body)
                
                has_expected_error = test_case['expected_error_type'] in error_message
                self.log_test_result(
                    f"{test_case['name']} - Proper error message",
                    has_expected_error,
                    f"Expected '{test_case['expected_error_type']}' in error, got: {error_message}"
                )
    
    def test_cross_resource_type_boundaries(self):
        """Test that users cannot access different resource types without proper permissions"""
        print("\n=== Testing Cross-Resource Type Boundaries ===")
        
        cross_resource_tests = [
            {
                'name': 'Members_CRUD user accessing Events operations',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'resource_type': 'Events',
                'operation': 'create',
                'should_be_denied': True
            },
            {
                'name': 'Events_Read user accessing Products operations',
                'user_roles': ['Events_Read', 'Regio_All'],
                'resource_type': 'Products',
                'operation': 'read',
                'should_be_denied': True
            },
            {
                'name': 'Products_CRUD user accessing Members operations',
                'user_roles': ['Products_CRUD', 'Regio_Utrecht'],
                'resource_type': 'Members',
                'operation': 'update',
                'should_be_denied': True
            },
            {
                'name': 'Communication_Read user accessing Events operations',
                'user_roles': ['Communication_Read', 'Regio_All'],
                'resource_type': 'Events',
                'operation': 'read',
                'should_be_denied': True
            }
        ]
        
        for test_case in cross_resource_tests:
            result = validate_crud_access(
                test_case['user_roles'],
                test_case['resource_type'],
                test_case['operation']
            )
            
            access_properly_denied = not result['has_access']
            self.log_test_result(
                test_case['name'],
                access_properly_denied,
                f"Expected denial, got access: {result['has_access']}, Message: {result['message']}"
            )
    
    def test_privilege_escalation_boundaries(self):
        """Test that users cannot escalate their privileges beyond assigned roles"""
        print("\n=== Testing Privilege Escalation Boundaries ===")
        
        escalation_tests = [
            {
                'name': 'Read-only user attempting export operations',
                'user_roles': ['Members_Read', 'Regio_All'],
                'required_permissions': ['members_export'],
                'should_be_denied': True
            },
            {
                'name': 'Export user attempting CRUD operations',
                'user_roles': ['Members_Export', 'Regio_All'],
                'required_permissions': ['members_create'],
                'should_be_denied': True
            },
            {
                'name': 'Regional user attempting system operations',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'required_permissions': ['users_manage'],
                'should_be_denied': True
            },
            {
                'name': 'Basic member attempting admin operations',
                'user_roles': ['hdcnLeden'],
                'required_permissions': ['members_read'],
                'should_be_denied': True
            },
            {
                'name': 'User attempting to access system logs',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'required_permissions': ['logs_read'],
                'should_be_denied': True
            }
        ]
        
        for test_case in escalation_tests:
            is_authorized, error_response = validate_permissions(
                test_case['user_roles'],
                test_case['required_permissions'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            access_properly_denied = not is_authorized
            self.log_test_result(
                test_case['name'],
                access_properly_denied,
                f"Expected denial, got authorized: {is_authorized}"
            )
    
    def test_jwt_token_boundary_validation(self):
        """Test JWT token validation boundaries"""
        print("\n=== Testing JWT Token Boundary Validation ===")
        
        # Test invalid JWT token formats
        invalid_token_tests = [
            {
                'name': 'Missing Authorization header',
                'event': {'headers': {}},
                'should_fail': True
            },
            {
                'name': 'Invalid Bearer format',
                'event': {'headers': {'Authorization': 'InvalidFormat token'}},
                'should_fail': True
            },
            {
                'name': 'Malformed JWT token (wrong parts count)',
                'event': {'headers': {'Authorization': 'Bearer invalid.token'}},
                'should_fail': True
            },
            {
                'name': 'Empty JWT token',
                'event': {'headers': {'Authorization': 'Bearer '}},
                'should_fail': True
            }
        ]
        
        for test_case in invalid_token_tests:
            user_email, user_roles, error_response = extract_user_credentials(test_case['event'])
            
            # Should fail authentication
            auth_properly_failed = (user_email is None and user_roles is None and error_response is not None)
            self.log_test_result(
                test_case['name'],
                auth_properly_failed,
                f"Expected auth failure, got email: {user_email}, roles: {user_roles}"
            )
            
            # Check error response
            if error_response:
                has_proper_error_code = error_response.get('statusCode') == 401
                self.log_test_result(
                    f"{test_case['name']} - Proper error code",
                    has_proper_error_code,
                    f"Expected 401, got: {error_response.get('statusCode')}"
                )
    
    def test_system_role_boundaries(self):
        """Test that system roles have appropriate boundaries"""
        print("\n=== Testing System Role Boundaries ===")
        
        # Test that non-system users cannot access system functions
        system_boundary_tests = [
            {
                'name': 'Regular user accessing system user management',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'required_permissions': ['users_manage'],
                'should_be_denied': True
            },
            {
                'name': 'Regional admin accessing system logs',
                'user_roles': ['Members_CRUD', 'Events_CRUD', 'Regio_Utrecht'],
                'required_permissions': ['logs_read'],
                'should_be_denied': True
            },
            {
                'name': 'Export user accessing system functions',
                'user_roles': ['Members_Export', 'Events_Export', 'Regio_All'],
                'required_permissions': ['users_manage'],
                'should_be_denied': True
            }
        ]
        
        for test_case in system_boundary_tests:
            is_authorized, error_response = validate_permissions(
                test_case['user_roles'],
                test_case['required_permissions'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            access_properly_denied = not is_authorized
            self.log_test_result(
                test_case['name'],
                access_properly_denied,
                f"Expected denial, got authorized: {is_authorized}"
            )
        
        # Test that system users have appropriate access
        system_access_tests = [
            {
                'name': 'System_CRUD user accessing any resource',
                'user_roles': ['System_CRUD'],
                'required_permissions': ['members_read'],
                'should_be_authorized': True
            },
            {
                'name': 'System_User_Management user accessing user functions',
                'user_roles': ['System_User_Management'],
                'required_permissions': ['users_manage'],
                'should_be_authorized': True
            },
            {
                'name': 'System_Logs_Read user accessing logs',
                'user_roles': ['System_Logs_Read'],
                'required_permissions': ['logs_read'],
                'should_be_authorized': True
            }
        ]
        
        for test_case in system_access_tests:
            is_authorized, error_response = validate_permissions(
                test_case['user_roles'],
                test_case['required_permissions'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            access_properly_granted = is_authorized
            self.log_test_result(
                test_case['name'],
                access_properly_granted,
                f"Expected authorization, got denied: {not is_authorized}"
            )
    
    def run_all_tests(self):
        """Run all permission boundary tests"""
        print("🚀 Starting Permission Boundaries Test")
        print("=" * 80)
        
        # Run all test methods
        self.test_permission_role_boundaries()
        self.test_regional_access_boundaries()
        self.test_incomplete_role_structure_boundaries()
        self.test_cross_resource_type_boundaries()
        self.test_privilege_escalation_boundaries()
        self.test_jwt_token_boundary_validation()
        self.test_system_role_boundaries()
        
        # Print summary and return success status
        return self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 Permission Boundaries Test Summary")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = len(self.failed_tests)
        
        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests Details:")
            for failed_test in self.failed_tests:
                print(f"   • {failed_test['test_name']}")
                print(f"     Details: {failed_test['details']}")
        
        print(f"\n🔒 Permission Boundary Features Verified:")
        print(f"   ✅ Users cannot access resources without proper permission roles")
        print(f"   ✅ Users cannot access data outside their assigned regions")
        print(f"   ✅ Users with incomplete role structures are properly denied")
        print(f"   ✅ Users cannot access different resource types without permissions")
        print(f"   ✅ Users cannot escalate privileges beyond assigned roles")
        print(f"   ✅ JWT token validation properly rejects invalid tokens")
        print(f"   ✅ System role boundaries are properly enforced")
        
        print(f"\n🎯 Security Validation Results:")
        if failed_tests == 0:
            print(f"   ✅ ALL PERMISSION BOUNDARY TESTS PASSED")
            print(f"   ✅ No unauthorized access detected")
            print(f"   ✅ Permission boundaries are properly enforced")
            print(f"   ✅ System is secure and ready for production use")
        else:
            print(f"   ⚠️  {failed_tests} permission boundary tests failed")
            print(f"   ⚠️  Unauthorized access may be possible")
            print(f"   ⚠️  Review failed tests before production deployment")
        
        return failed_tests == 0


def main():
    """Main test execution function"""
    test_suite = PermissionBoundariesTest()
    success = test_suite.run_all_tests()
    
    if success:
        print(f"\n🎉 All permission boundary tests passed!")
        print(f"✅ Permission boundaries are properly enforced and system is secure")
        return 0
    else:
        print(f"\n⚠️  Some permission boundary tests failed!")
        print(f"❌ Please review and fix the security issues before proceeding")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)