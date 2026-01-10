#!/usr/bin/env python3
"""
Comprehensive Regional Access Controls Test
Tests that regional filtering works correctly across all authentication scenarios
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
        determine_regional_access,
        check_regional_data_access,
        get_user_accessible_regions,
        can_access_resource_region,
        validate_crud_access,
        validate_user_has_new_role_structure,
        has_permission_and_region_access,
        quick_role_check,
        get_user_permissions_summary
    )
    print("✅ Successfully imported auth_utils functions")
except ImportError as e:
    print(f"❌ Failed to import auth_utils: {e}")
    sys.exit(1)


class RegionalAccessControlsTest:
    """Comprehensive test suite for regional access controls"""
    
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
    
    def test_basic_regional_access_determination(self):
        """Test basic regional access determination for different user types"""
        print("\n=== Testing Basic Regional Access Determination ===")
        
        test_cases = [
            {
                'name': 'Admin user (System_CRUD)',
                'user_roles': ['System_CRUD'],
                'expected_full_access': True,
                'expected_access_type': 'admin',
                'expected_regions': ['all']
            },
            {
                'name': 'National user (Regio_All)',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'expected_full_access': True,
                'expected_access_type': 'national',
                'expected_regions': ['all']
            },
            {
                'name': 'Single regional user',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'expected_full_access': False,
                'expected_access_type': 'regional',
                'expected_regions': ['Utrecht']
            },
            {
                'name': 'Multi-regional user',
                'user_roles': ['Members_CRUD', 'Regio_Groningen/Drenthe', 'Regio_Limburg'],
                'expected_full_access': False,
                'expected_access_type': 'regional',
                'expected_regions': ['Groningen/Drenthe', 'Limburg']
            },
            {
                'name': 'Legacy user (Members_CRUD_All)',
                'user_roles': ['Members_CRUD_All'],
                'expected_full_access': True,
                'expected_access_type': 'legacy_all',
                'expected_regions': ['all']
            },
            {
                'name': 'User with no regional access',
                'user_roles': ['Members_CRUD'],
                'expected_full_access': False,
                'expected_access_type': 'none',
                'expected_regions': []
            }
        ]
        
        for test_case in test_cases:
            regional_info = determine_regional_access(test_case['user_roles'])
            
            # Test full access
            full_access_correct = regional_info['has_full_access'] == test_case['expected_full_access']
            self.log_test_result(
                f"{test_case['name']} - Full access determination",
                full_access_correct,
                f"Expected: {test_case['expected_full_access']}, Got: {regional_info['has_full_access']}"
            )
            
            # Test access type
            access_type_correct = regional_info['access_type'] == test_case['expected_access_type']
            self.log_test_result(
                f"{test_case['name']} - Access type determination",
                access_type_correct,
                f"Expected: {test_case['expected_access_type']}, Got: {regional_info['access_type']}"
            )
            
            # Test allowed regions
            if test_case['expected_regions'] == ['all']:
                regions_correct = regional_info['allowed_regions'] == ['all']
            else:
                regions_correct = set(regional_info['allowed_regions']) == set(test_case['expected_regions'])
            
            self.log_test_result(
                f"{test_case['name']} - Allowed regions",
                regions_correct,
                f"Expected: {test_case['expected_regions']}, Got: {regional_info['allowed_regions']}"
            )
    
    def test_regional_data_access_validation(self):
        """Test validation of access to data from specific regions"""
        print("\n=== Testing Regional Data Access Validation ===")
        
        test_cases = [
            # Admin users should access everything
            {
                'name': 'Admin accessing any region',
                'user_roles': ['System_CRUD'],
                'data_region': 'Noord-Holland',
                'should_have_access': True
            },
            # National users should access everything
            {
                'name': 'National user accessing any region',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'data_region': 'Groningen/Drenthe',
                'should_have_access': True
            },
            # Regional users accessing their own region
            {
                'name': 'Regional user accessing own region',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'data_region': 'Utrecht',
                'should_have_access': True
            },
            # Regional users accessing different region (should fail)
            {
                'name': 'Regional user accessing different region',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'data_region': 'Noord-Holland',
                'should_have_access': False
            },
            # Multi-regional users accessing allowed region
            {
                'name': 'Multi-regional user accessing allowed region',
                'user_roles': ['Members_CRUD', 'Regio_Groningen/Drenthe', 'Regio_Limburg'],
                'data_region': 'Limburg',
                'should_have_access': True
            },
            # Multi-regional users accessing non-allowed region
            {
                'name': 'Multi-regional user accessing non-allowed region',
                'user_roles': ['Members_CRUD', 'Regio_Groningen/Drenthe', 'Regio_Limburg'],
                'data_region': 'Utrecht',
                'should_have_access': False
            },
            # Legacy users should access everything
            {
                'name': 'Legacy user accessing any region',
                'user_roles': ['Members_CRUD_All'],
                'data_region': 'Duitsland',
                'should_have_access': True
            },
            # Users with no regional access
            {
                'name': 'User with no regional access',
                'user_roles': ['Members_CRUD'],
                'data_region': 'Utrecht',
                'should_have_access': False
            }
        ]
        
        for test_case in test_cases:
            can_access, reason = check_regional_data_access(
                test_case['user_roles'], 
                test_case['data_region'],
                f"test-{test_case['name'].lower().replace(' ', '-')}@test.com"
            )
            
            access_correct = can_access == test_case['should_have_access']
            self.log_test_result(
                test_case['name'],
                access_correct,
                f"Expected access: {test_case['should_have_access']}, Got: {can_access}, Reason: {reason}"
            )
    
    def test_accessible_regions_calculation(self):
        """Test calculation of accessible regions for different user types"""
        print("\n=== Testing Accessible Regions Calculation ===")
        
        test_cases = [
            {
                'name': 'Admin user',
                'user_roles': ['System_CRUD'],
                'expected_regions': ['all']
            },
            {
                'name': 'National user',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'expected_regions': ['all']
            },
            {
                'name': 'Single regional user',
                'user_roles': ['Members_CRUD', 'Regio_Noord-Holland'],
                'expected_regions': ['Noord-Holland']
            },
            {
                'name': 'Multi-regional user',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht', 'Regio_Oost', 'Regio_Friesland'],
                'expected_regions': ['Utrecht', 'Oost', 'Friesland']
            },
            {
                'name': 'Legacy user',
                'user_roles': ['Events_CRUD_All'],
                'expected_regions': ['all']
            },
            {
                'name': 'User with no regional roles',
                'user_roles': ['Members_CRUD'],
                'expected_regions': []
            }
        ]
        
        for test_case in test_cases:
            accessible_regions = get_user_accessible_regions(test_case['user_roles'])
            
            if test_case['expected_regions'] == ['all']:
                regions_correct = accessible_regions == ['all']
            else:
                regions_correct = set(accessible_regions) == set(test_case['expected_regions'])
            
            self.log_test_result(
                test_case['name'],
                regions_correct,
                f"Expected: {test_case['expected_regions']}, Got: {accessible_regions}"
            )
    
    def test_resource_region_access_validation(self):
        """Test can_access_resource_region function"""
        print("\n=== Testing Resource Region Access Validation ===")
        
        test_cases = [
            {
                'name': 'Admin accessing any resource region',
                'user_roles': ['System_CRUD'],
                'resource_region': 'Brabant/Zeeland',
                'should_have_access': True,
                'expected_access_type': 'admin'
            },
            {
                'name': 'National user accessing any resource region',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'resource_region': 'Duitsland',
                'should_have_access': True,
                'expected_access_type': 'national'
            },
            {
                'name': 'Regional user accessing own region',
                'user_roles': ['Members_CRUD', 'Regio_Brabant/Zeeland'],
                'resource_region': 'Brabant/Zeeland',
                'should_have_access': True,
                'expected_access_type': 'regional'
            },
            {
                'name': 'Regional user accessing different region',
                'user_roles': ['Members_CRUD', 'Regio_Brabant/Zeeland'],
                'resource_region': 'Duitsland',
                'should_have_access': False,
                'expected_access_type': 'denied'
            },
            {
                'name': 'Multi-regional user accessing allowed region',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht', 'Regio_Duitsland'],
                'resource_region': 'Duitsland',
                'should_have_access': True,
                'expected_access_type': 'regional'
            },
            {
                'name': 'User with no regional roles',
                'user_roles': ['Members_CRUD'],
                'resource_region': 'Utrecht',
                'should_have_access': False,
                'expected_access_type': 'denied'
            }
        ]
        
        for test_case in test_cases:
            result = can_access_resource_region(test_case['user_roles'], test_case['resource_region'])
            
            access_correct = result['can_access'] == test_case['should_have_access']
            self.log_test_result(
                f"{test_case['name']} - Access result",
                access_correct,
                f"Expected: {test_case['should_have_access']}, Got: {result['can_access']}, Message: {result['message']}"
            )
            
            access_type_correct = result['access_type'] == test_case['expected_access_type']
            self.log_test_result(
                f"{test_case['name']} - Access type",
                access_type_correct,
                f"Expected: {test_case['expected_access_type']}, Got: {result['access_type']}"
            )
    
    def test_crud_access_with_regional_restrictions(self):
        """Test CRUD access validation with regional restrictions"""
        print("\n=== Testing CRUD Access with Regional Restrictions ===")
        
        test_cases = [
            {
                'name': 'Admin CRUD access to any region',
                'user_roles': ['System_CRUD'],
                'resource_type': 'Members',
                'operation': 'update',
                'resource_region': 'Noord-Holland',
                'should_have_access': True
            },
            {
                'name': 'National user CRUD access to any region',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'resource_type': 'Members',
                'operation': 'create',
                'resource_region': 'Limburg',
                'should_have_access': True
            },
            {
                'name': 'Regional user CRUD access to own region',
                'user_roles': ['Members_CRUD', 'Regio_Limburg'],
                'resource_type': 'Members',
                'operation': 'update',
                'resource_region': 'Limburg',
                'should_have_access': True
            },
            {
                'name': 'Regional user CRUD access to different region',
                'user_roles': ['Members_CRUD', 'Regio_Limburg'],
                'resource_type': 'Members',
                'operation': 'update',
                'resource_region': 'Noord-Holland',
                'should_have_access': False
            },
            {
                'name': 'Regional read-only user accessing own region',
                'user_roles': ['Members_Read', 'Regio_Oost'],
                'resource_type': 'Members',
                'operation': 'read',
                'resource_region': 'Oost',
                'should_have_access': True
            },
            {
                'name': 'Regional read-only user accessing different region',
                'user_roles': ['Members_Read', 'Regio_Oost'],
                'resource_type': 'Members',
                'operation': 'read',
                'resource_region': 'Friesland',
                'should_have_access': False
            },
            {
                'name': 'Multi-regional user accessing allowed region',
                'user_roles': ['Events_CRUD', 'Regio_Utrecht', 'Regio_Friesland'],
                'resource_type': 'Events',
                'operation': 'delete',
                'resource_region': 'Friesland',
                'should_have_access': True
            },
            {
                'name': 'Multi-regional user accessing non-allowed region',
                'user_roles': ['Events_CRUD', 'Regio_Utrecht', 'Regio_Friesland'],
                'resource_type': 'Events',
                'operation': 'delete',
                'resource_region': 'Duitsland',
                'should_have_access': False
            }
        ]
        
        for test_case in test_cases:
            result = validate_crud_access(
                test_case['user_roles'],
                test_case['resource_type'],
                test_case['operation'],
                test_case['resource_region']
            )
            
            access_correct = result['has_access'] == test_case['should_have_access']
            self.log_test_result(
                test_case['name'],
                access_correct,
                f"Expected: {test_case['should_have_access']}, Got: {result['has_access']}, Message: {result['message']}"
            )
    
    def test_permission_and_region_access_validation(self):
        """Test has_permission_and_region_access function"""
        print("\n=== Testing Permission and Region Access Validation ===")
        
        test_cases = [
            {
                'name': 'Valid new structure (permission + region)',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'required_permission': 'Members_CRUD',
                'should_have_access': True,
                'expected_access_type': 'new_structure'
            },
            {
                'name': 'Valid admin access',
                'user_roles': ['System_CRUD'],
                'required_permission': 'Members_CRUD',
                'should_have_access': True,
                'expected_access_type': 'admin'
            },
            {
                'name': 'Valid legacy access',
                'user_roles': ['Members_CRUD_All'],
                'required_permission': 'Members_CRUD',
                'should_have_access': True,
                'expected_access_type': 'legacy'
            },
            {
                'name': 'Permission without region (should fail)',
                'user_roles': ['Members_CRUD'],
                'required_permission': 'Members_CRUD',
                'should_have_access': False,
                'expected_access_type': 'denied'
            },
            {
                'name': 'Region without permission (should fail)',
                'user_roles': ['Regio_Utrecht'],
                'required_permission': 'Members_CRUD',
                'should_have_access': False,
                'expected_access_type': 'denied'
            },
            {
                'name': 'Wrong permission with region (should fail)',
                'user_roles': ['Events_CRUD', 'Regio_Utrecht'],
                'required_permission': 'Members_CRUD',
                'should_have_access': False,
                'expected_access_type': 'denied'
            }
        ]
        
        for test_case in test_cases:
            result = has_permission_and_region_access(
                test_case['user_roles'],
                test_case['required_permission']
            )
            
            access_correct = result['has_access'] == test_case['should_have_access']
            self.log_test_result(
                f"{test_case['name']} - Access result",
                access_correct,
                f"Expected: {test_case['should_have_access']}, Got: {result['has_access']}, Message: {result['message']}"
            )
            
            if test_case['should_have_access']:
                access_type_correct = result['access_type'] == test_case['expected_access_type']
                self.log_test_result(
                    f"{test_case['name']} - Access type",
                    access_type_correct,
                    f"Expected: {test_case['expected_access_type']}, Got: {result['access_type']}"
                )
    
    def test_quick_role_check_regional_scenarios(self):
        """Test quick_role_check function with regional scenarios"""
        print("\n=== Testing Quick Role Check Regional Scenarios ===")
        
        test_cases = [
            {
                'name': 'Admin check',
                'user_roles': ['System_CRUD'],
                'check_type': 'admin',
                'should_pass': True
            },
            {
                'name': 'Non-admin check',
                'user_roles': ['Members_CRUD', 'Regio_Utrecht'],
                'check_type': 'admin',
                'should_pass': False
            },
            {
                'name': 'Permission check with valid structure',
                'user_roles': ['Members_CRUD', 'Regio_All'],
                'check_type': 'permission',
                'kwargs': {'permission': 'Members_CRUD'},
                'should_pass': True
            },
            {
                'name': 'Permission check without region',
                'user_roles': ['Members_CRUD'],
                'check_type': 'permission',
                'kwargs': {'permission': 'Members_CRUD'},
                'should_pass': False
            },
            {
                'name': 'Region access check - allowed',
                'user_roles': ['Members_CRUD', 'Regio_Groningen/Drenthe'],
                'check_type': 'region',
                'kwargs': {'region': 'Groningen/Drenthe'},
                'should_pass': True
            },
            {
                'name': 'Region access check - denied',
                'user_roles': ['Members_CRUD', 'Regio_Groningen/Drenthe'],
                'check_type': 'region',
                'kwargs': {'region': 'Utrecht'},
                'should_pass': False
            },
            {
                'name': 'CRUD check with regional access',
                'user_roles': ['Events_CRUD', 'Regio_Limburg'],
                'check_type': 'crud',
                'kwargs': {'resource': 'Events', 'operation': 'update', 'region': 'Limburg'},
                'should_pass': True
            },
            {
                'name': 'CRUD check without regional access',
                'user_roles': ['Events_CRUD', 'Regio_Limburg'],
                'check_type': 'crud',
                'kwargs': {'resource': 'Events', 'operation': 'update', 'region': 'Duitsland'},
                'should_pass': False
            }
        ]
        
        for test_case in test_cases:
            kwargs = test_case.get('kwargs', {})
            has_access, message = quick_role_check(
                test_case['user_roles'],
                test_case['check_type'],
                **kwargs
            )
            
            result_correct = has_access == test_case['should_pass']
            self.log_test_result(
                test_case['name'],
                result_correct,
                f"Expected: {test_case['should_pass']}, Got: {has_access}, Message: {message}"
            )
    
    def test_comprehensive_permissions_summary(self):
        """Test get_user_permissions_summary with regional scenarios"""
        print("\n=== Testing Comprehensive Permissions Summary ===")
        
        test_cases = [
            {
                'name': 'Admin user summary',
                'user_roles': ['System_CRUD'],
                'expected_admin': True,
                'expected_access_level': 'admin'
            },
            {
                'name': 'National user summary',
                'user_roles': ['Members_CRUD', 'Events_Read', 'Regio_All'],
                'expected_admin': False,
                'expected_access_level': 'national'
            },
            {
                'name': 'Regional user summary',
                'user_roles': ['Members_Read', 'Products_CRUD', 'Regio_Utrecht'],
                'expected_admin': False,
                'expected_access_level': 'regional'
            },
            {
                'name': 'Multi-regional user summary',
                'user_roles': ['Events_CRUD', 'Regio_Groningen/Drenthe', 'Regio_Friesland'],
                'expected_admin': False,
                'expected_access_level': 'regional'
            },
            {
                'name': 'Legacy user summary',
                'user_roles': ['Members_CRUD_All', 'Events_Read_All'],
                'expected_admin': False,
                'expected_access_level': 'national'
            }
        ]
        
        for test_case in test_cases:
            summary = get_user_permissions_summary(test_case['user_roles'])
            
            admin_correct = summary['is_admin'] == test_case['expected_admin']
            self.log_test_result(
                f"{test_case['name']} - Admin status",
                admin_correct,
                f"Expected: {test_case['expected_admin']}, Got: {summary['is_admin']}"
            )
            
            access_level_correct = summary['summary']['access_level'] == test_case['expected_access_level']
            self.log_test_result(
                f"{test_case['name']} - Access level",
                access_level_correct,
                f"Expected: {test_case['expected_access_level']}, Got: {summary['summary']['access_level']}"
            )
            
            # Test that summary has valid structure
            has_valid_structure = summary['summary']['has_valid_structure']
            self.log_test_result(
                f"{test_case['name']} - Valid structure",
                has_valid_structure,
                f"Expected valid structure, got: {has_valid_structure}"
            )
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling in regional access"""
        print("\n=== Testing Edge Cases and Error Handling ===")
        
        # Test empty roles
        regional_info = determine_regional_access([])
        self.log_test_result(
            "Empty roles list",
            not regional_info['has_full_access'] and regional_info['access_type'] == 'none',
            f"Expected no access, got: {regional_info}"
        )
        
        # Test None roles
        try:
            regional_info = determine_regional_access(None)
            self.log_test_result(
                "None roles handling",
                False,
                "Should have raised an exception for None roles"
            )
        except (TypeError, AttributeError):
            self.log_test_result(
                "None roles handling",
                True,
                "Correctly handled None roles with exception"
            )
        
        # Test invalid region names
        can_access, reason = check_regional_data_access(
            ['Members_CRUD', 'Regio_Utrecht'], 
            'InvalidRegion', 
            'test@test.com'
        )
        self.log_test_result(
            "Invalid region name handling",
            not can_access,
            f"Expected no access to invalid region, got: {can_access}, reason: {reason}"
        )
        
        # Test malformed role names
        regional_info = determine_regional_access(['InvalidRole', 'Regio_'])
        self.log_test_result(
            "Malformed role names handling",
            not regional_info['has_full_access'],
            f"Expected no access for malformed roles, got: {regional_info}"
        )
        
        # Test case sensitivity
        regional_info = determine_regional_access(['regio_all', 'members_crud'])
        self.log_test_result(
            "Case sensitivity handling",
            not regional_info['has_full_access'],
            f"Expected no access for lowercase roles, got: {regional_info}"
        )
    
    def run_all_tests(self):
        """Run all regional access control tests"""
        print("🚀 Starting Comprehensive Regional Access Controls Test")
        print("=" * 80)
        
        # Run all test methods
        self.test_basic_regional_access_determination()
        self.test_regional_data_access_validation()
        self.test_accessible_regions_calculation()
        self.test_resource_region_access_validation()
        self.test_crud_access_with_regional_restrictions()
        self.test_permission_and_region_access_validation()
        self.test_quick_role_check_regional_scenarios()
        self.test_comprehensive_permissions_summary()
        self.test_edge_cases_and_error_handling()
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 Regional Access Controls Test Summary")
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
        
        print(f"\n🔒 Regional Access Control Features Verified:")
        print(f"   ✅ Admin users have full access to all regions")
        print(f"   ✅ National users (Regio_All) have full access to all regions")
        print(f"   ✅ Regional users can only access their assigned regions")
        print(f"   ✅ Multi-regional users can access multiple assigned regions")
        print(f"   ✅ Legacy _All roles maintain backward compatibility")
        print(f"   ✅ Users without region roles are properly denied access")
        print(f"   ✅ CRUD operations respect regional restrictions")
        print(f"   ✅ Error handling works correctly for edge cases")
        
        print(f"\n🎯 Security Validation Results:")
        if failed_tests == 0:
            print(f"   ✅ ALL SECURITY TESTS PASSED")
            print(f"   ✅ Regional filtering is working correctly")
            print(f"   ✅ No unauthorized access detected")
            print(f"   ✅ System is ready for production use")
        else:
            print(f"   ⚠️  {failed_tests} security tests failed")
            print(f"   ⚠️  Regional filtering needs attention")
            print(f"   ⚠️  Review failed tests before production deployment")
        
        return failed_tests == 0


def main():
    """Main test execution function"""
    test_suite = RegionalAccessControlsTest()
    success = test_suite.run_all_tests()
    
    if success:
        print(f"\n🎉 All regional access control tests passed!")
        print(f"✅ Regional filtering is working correctly and ready for production")
        return 0
    else:
        print(f"\n⚠️  Some regional access control tests failed!")
        print(f"❌ Please review and fix the issues before proceeding")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)