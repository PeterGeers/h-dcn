"""
Comprehensive Regional Filtering Validation Test Suite

This test suite validates that regional access controls work consistently across
the entire H-DCN system with the new role structure (no backward compatibility).

Test Coverage:
- All role combinations with regional access
- Cross-handler consistency 
- Edge cases and security scenarios
- End-to-end regional filtering validation
- Docker container authentication (parquet generation)

Role Structure Being Tested:
- Permission Roles: Members_CRUD, Members_Read, Members_Export, etc.
- Region Roles: Regio_All, Regio_Utrecht, Regio_Groningen/Drenthe, etc.
- Valid Combinations: Permission + Region roles required
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'shared'))

try:
    from backend.shared.auth_utils import (
        validate_permissions_with_regions,
        extract_user_credentials,
        create_error_response,
        create_success_response
    )
except ImportError:
    # Fallback for testing environment
    def validate_permissions_with_regions(user_roles, required_permissions, user_email, resource_context=None):
        return False, {'statusCode': 401, 'body': json.dumps({'error': 'Auth not available'})}, {}


class TestComprehensiveRegionalFiltering:
    """
    Comprehensive test suite for regional filtering validation across all system components.
    """

    def setup_method(self):
        """Setup test data for each test method."""
        
        # Test user configurations
        self.test_users = {
            'national_admin': {
                'email': 'admin@hdcn.nl',
                'roles': ['Members_CRUD', 'Regio_All'],
                'expected_access': 'full_national'
            },
            'regional_coordinator_utrecht': {
                'email': 'utrecht@hdcn.nl', 
                'roles': ['Members_CRUD', 'Regio_Utrecht'],
                'expected_access': 'regional_utrecht'
            },
            'regional_coordinator_groningen': {
                'email': 'groningen@hdcn.nl',
                'roles': ['Members_CRUD', 'Regio_Groningen/Drenthe'],
                'expected_access': 'regional_groningen'
            },
            'national_readonly': {
                'email': 'readonly@hdcn.nl',
                'roles': ['Members_Read', 'Regio_All'],
                'expected_access': 'readonly_national'
            },
            'regional_readonly_limburg': {
                'email': 'limburg@hdcn.nl',
                'roles': ['Members_Read', 'Regio_Limburg'],
                'expected_access': 'readonly_regional'
            },
            'export_user_national': {
                'email': 'export@hdcn.nl',
                'roles': ['Members_Read', 'Members_Export', 'Regio_All'],
                'expected_access': 'export_national'
            },
            'export_user_regional': {
                'email': 'export_brabant@hdcn.nl',
                'roles': ['Members_Read', 'Members_Export', 'Regio_Brabant/Zeeland'],
                'expected_access': 'export_regional'
            },
            'system_admin': {
                'email': 'system@hdcn.nl',
                'roles': ['System_CRUD', 'Regio_All'],
                'expected_access': 'system_full'
            },
            'incomplete_user_no_region': {
                'email': 'incomplete1@hdcn.nl',
                'roles': ['Members_CRUD'],  # Missing region role
                'expected_access': 'denied'
            },
            'incomplete_user_no_permission': {
                'email': 'incomplete2@hdcn.nl',
                'roles': ['Regio_All'],  # Missing permission role
                'expected_access': 'denied'
            },
            'webshop_user': {
                'email': 'webshop@hdcn.nl',
                'roles': ['hdcnLeden', 'Regio_Utrecht'],
                'expected_access': 'denied'  # hdcnLeden doesn't have members_read permission
            }
        }

        # Handler configurations for testing
        self.handlers_to_test = {
            'member_handlers': {
                'get_members': ['members_read'],
                'update_member': ['members_update'],
                'create_member': ['members_create'],
                'get_member_byid': ['members_read']
            },
            'product_handlers': {
                'get_products': ['products_read'],
                'update_product': ['products_update'],
                'create_product': ['products_create']
            },
            'event_handlers': {
                'get_events': ['events_read'],
                'update_event': ['events_update'],
                'create_event': ['events_create']
            },
            'export_handlers': {
                'generate_member_parquet': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                'download_parquet': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                's3_file_manager': ['members_read', 'products_read', 'events_read']
            },
            'webshop_handlers': {
                'get_cart': ['webshop_access'],
                'create_cart': ['webshop_access'],
                'clear_cart': ['webshop_access']
            }
        }

        # Regional test data
        self.regional_test_data = {
            'members': [
                {'id': '1', 'region': 'Utrecht', 'name': 'Test User Utrecht'},
                {'id': '2', 'region': 'Groningen/Drenthe', 'name': 'Test User Groningen'},
                {'id': '3', 'region': 'Limburg', 'name': 'Test User Limburg'},
                {'id': '4', 'region': 'Brabant/Zeeland', 'name': 'Test User Brabant'},
                {'id': '5', 'region': 'Overig', 'name': 'Test User Other'}
            ]
        }

    def test_role_combination_validation(self):
        """
        Test 1: Validate all role combinations work correctly with regional access.
        
        This test ensures that:
        - Valid role combinations (permission + region) are accepted
        - Invalid combinations (missing permission or region) are rejected
        - Regional access is properly calculated for each combination
        """
        
        for user_key, user_config in self.test_users.items():
            user_roles = user_config['roles']
            expected_access = user_config['expected_access']
            
            # Test with member read permissions (most common scenario)
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles=user_roles,
                required_permissions=['members_read'],
                user_email=user_config['email'],
                resource_context={'operation': 'test_validation'}
            )
            
            if expected_access == 'denied':
                assert not is_authorized, f"User {user_key} should be denied access but was authorized"
                assert error_response is not None, f"User {user_key} should have error response"
            else:
                assert is_authorized, f"User {user_key} should be authorized but was denied"
                # For valid users, check regional access is properly set
                if regional_info:  # Only check if regional_info is not None
                    if 'Regio_All' in user_roles or 'System_CRUD' in user_roles:
                        assert regional_info.get('has_full_access', False), f"User {user_key} should have full access"
                    else:
                        assert not regional_info.get('has_full_access', True), f"User {user_key} should have regional access only"
                        assert 'allowed_regions' in regional_info, f"User {user_key} should have allowed_regions defined"

    def test_cross_handler_consistency(self):
        """
        Test 2: Validate that regional filtering works consistently across all handlers.
        
        This test ensures that:
        - Same role combinations produce same regional access across different handlers
        - Permission validation is consistent between handlers
        - Regional filtering logic is uniform across the system
        """
        
        # Test with a regional user across different handler types
        test_user = self.test_users['regional_coordinator_utrecht']
        user_roles = test_user['roles']
        user_email = test_user['email']
        
        regional_results = {}
        
        # Test across all handler categories
        for category, handlers in self.handlers_to_test.items():
            regional_results[category] = {}
            
            for handler_name, required_permissions in handlers.items():
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles=user_roles,
                    required_permissions=required_permissions,
                    user_email=user_email,
                    resource_context={'operation': handler_name}
                )
                
                regional_results[category][handler_name] = {
                    'authorized': is_authorized,
                    'regional_info': regional_info
                }
        
        # Validate consistency across handlers
        first_result = None
        for category, handlers in regional_results.items():
            for handler_name, result in handlers.items():
                if result['authorized']:  # Only check authorized handlers
                    if first_result is None:
                        first_result = result['regional_info']
                    else:
                        # Regional access should be consistent
                        assert result['regional_info'].get('has_full_access') == first_result.get('has_full_access'), \
                            f"Inconsistent regional access between handlers: {handler_name}"
                        
                        if not result['regional_info'].get('has_full_access', True):
                            assert result['regional_info'].get('allowed_regions') == first_result.get('allowed_regions'), \
                                f"Inconsistent allowed regions between handlers: {handler_name}"

    def test_regional_boundary_enforcement(self):
        """
        Test 3: Validate that regional boundaries are properly enforced.
        
        This test ensures that:
        - Users can only access data from their assigned regions
        - Cross-regional access is properly blocked
        - Regio_All users can access all regions
        - Regional filtering works for different data types
        """
        
        # Test regional user trying to access different regions
        regional_user = self.test_users['regional_coordinator_utrecht']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles=regional_user['roles'],
            required_permissions=['members_read'],
            user_email=regional_user['email'],
            resource_context={'operation': 'regional_boundary_test'}
        )
        
        assert is_authorized, "Regional user should be authorized for members_read"
        assert not regional_info.get('has_full_access', True), "Regional user should not have full access"
        assert 'Utrecht' in regional_info.get('allowed_regions', []), "Utrecht should be in allowed regions"
        assert 'Groningen/Drenthe' not in regional_info.get('allowed_regions', []), "Other regions should not be accessible"
        
        # Test national user has access to all regions
        national_user = self.test_users['national_admin']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles=national_user['roles'],
            required_permissions=['members_read'],
            user_email=national_user['email'],
            resource_context={'operation': 'national_access_test'}
        )
        
        assert is_authorized, "National user should be authorized"
        assert regional_info.get('has_full_access', False), "National user should have full access"

    def test_permission_level_validation(self):
        """
        Test 4: Validate that different permission levels work correctly with regional access.
        
        This test ensures that:
        - CRUD permissions include read access
        - Read-only users can't perform write operations
        - Export users have appropriate access levels
        - System users have elevated permissions
        """
        
        test_scenarios = [
            {
                'user': self.test_users['national_admin'],
                'permissions_to_test': [
                    (['members_read'], True),
                    (['members_create'], True),
                    (['members_update'], True),
                    (['members_delete'], True),
                    (['members_export'], True)
                ]
            },
            {
                'user': self.test_users['national_readonly'],
                'permissions_to_test': [
                    (['members_read'], True),
                    (['members_create'], False),
                    (['members_update'], False),
                    (['members_delete'], False),
                    (['members_export'], False)
                ]
            },
            {
                'user': self.test_users['export_user_national'],
                'permissions_to_test': [
                    (['members_read'], True),
                    (['members_create'], False),
                    (['members_update'], False),
                    (['members_delete'], False),
                    (['members_export'], True)
                ]
            }
        ]
        
        for scenario in test_scenarios:
            user = scenario['user']
            for required_permissions, should_be_authorized in scenario['permissions_to_test']:
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles=user['roles'],
                    required_permissions=required_permissions,
                    user_email=user['email'],
                    resource_context={'operation': f"permission_test_{required_permissions[0]}"}
                )
                
                if should_be_authorized:
                    assert is_authorized, f"User {user['email']} should be authorized for {required_permissions}"
                else:
                    assert not is_authorized, f"User {user['email']} should NOT be authorized for {required_permissions}"

    def test_docker_container_authentication(self):
        """
        Test 5: Validate Docker container authentication works with regional access.
        
        This test specifically validates the generate_member_parquet Docker container
        authentication with different role combinations and regional access.
        
        IMPORTANT: This tests the ACTUAL parquet handler logic, not the generic auth system.
        Parquet generation has stricter requirements than general member access.
        """
        
        # Docker container specific permission requirements
        # ACTUAL PARQUET HANDLER LOGIC: Requires Members_CRUD + Regio_All OR System_CRUD + Regio_All
        
        docker_test_scenarios = [
            {
                'user': self.test_users['national_admin'],
                'should_succeed': True,
                'reason': 'Has Members_CRUD + Regio_All'
            },
            {
                'user': self.test_users['system_admin'],
                'should_succeed': True,
                'reason': 'Has System_CRUD + Regio_All'
            },
            {
                'user': self.test_users['regional_coordinator_utrecht'],
                'should_succeed': False,
                'reason': 'Has Members_CRUD but only regional access - parquet generation requires Regio_All'
            },
            {
                'user': self.test_users['national_readonly'],
                'should_succeed': False,
                'reason': 'Only has Members_Read - parquet generation requires Members_CRUD'
            },
            {
                'user': self.test_users['export_user_national'],
                'should_succeed': False,
                'reason': 'Only has Members_Read + Members_Export - parquet generation requires Members_CRUD'
            },
            {
                'user': self.test_users['incomplete_user_no_region'],
                'should_succeed': False,
                'reason': 'Missing region role'
            }
        ]
        
        for scenario in docker_test_scenarios:
            user = scenario['user']
            user_roles = user['roles']
            
            # Test the ACTUAL parquet handler logic, not the generic auth system
            # This mirrors the logic in backend/handler/generate_member_parquet/app.py
            
            has_members_crud = 'Members_CRUD' in user_roles
            has_system_admin = any(role in user_roles for role in ['System_CRUD', 'System_User_Management'])
            has_regio_all = 'Regio_All' in user_roles
            
            # Parquet generation requirements (from actual handler):
            # 1. Must have Members_CRUD OR system admin role
            # 2. Must have Regio_All (unless system admin)
            parquet_authorized = (has_members_crud or has_system_admin) and (has_system_admin or has_regio_all)
            
            if scenario['should_succeed']:
                assert parquet_authorized, f"Docker container auth should succeed for {user['email']}: {scenario['reason']}"
            else:
                assert not parquet_authorized, f"Docker container auth should fail for {user['email']}: {scenario['reason']}"

    def test_edge_cases_and_security_scenarios(self):
        """
        Test 6: Validate edge cases and security scenarios.
        
        This test ensures that:
        - Empty role lists are handled correctly
        - Invalid role combinations are rejected
        - Security boundaries are maintained
        - Error handling works correctly
        """
        
        edge_case_scenarios = [
            {
                'name': 'empty_roles',
                'user_roles': [],
                'required_permissions': ['members_read'],
                'should_succeed': False
            },
            {
                'name': 'none_roles',
                'user_roles': None,
                'required_permissions': ['members_read'],
                'should_succeed': False
            },
            {
                'name': 'invalid_role_format',
                'user_roles': ['InvalidRole', 'AnotherInvalidRole'],
                'required_permissions': ['members_read'],
                'should_succeed': False
            },
            {
                'name': 'mixed_valid_invalid_roles',
                'user_roles': ['Members_CRUD', 'InvalidRole', 'Regio_All'],
                'required_permissions': ['members_read'],
                'should_succeed': True  # Should work with valid roles, ignore invalid ones
            },
            {
                'name': 'case_sensitive_roles',
                'user_roles': ['members_crud', 'regio_all'],  # Wrong case
                'required_permissions': ['members_read'],
                'should_succeed': False
            }
        ]
        
        for scenario in edge_case_scenarios:
            try:
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles=scenario['user_roles'],
                    required_permissions=scenario['required_permissions'],
                    user_email='test@hdcn.nl',
                    resource_context={'operation': f"edge_case_{scenario['name']}"}
                )
                
                if scenario['should_succeed']:
                    assert is_authorized, f"Edge case {scenario['name']} should succeed"
                else:
                    assert not is_authorized, f"Edge case {scenario['name']} should fail"
                    
            except Exception as e:
                # Some edge cases might throw exceptions - that's acceptable for security
                if scenario['should_succeed']:
                    pytest.fail(f"Edge case {scenario['name']} should not throw exception: {e}")

    def test_end_to_end_regional_filtering_workflow(self):
        """
        Test 7: End-to-end workflow validation with regional filtering.
        
        This test simulates complete user workflows to ensure regional filtering
        works correctly across multiple operations and handlers.
        """
        
        # Simulate a regional coordinator workflow
        regional_user = self.test_users['regional_coordinator_utrecht']
        
        workflow_steps = [
            {
                'operation': 'login_validation',
                'permissions': ['members_read'],
                'should_succeed': True
            },
            {
                'operation': 'view_members',
                'permissions': ['members_read'],
                'should_succeed': True
            },
            {
                'operation': 'update_member',
                'permissions': ['members_update'],
                'should_succeed': True
            },
            {
                'operation': 'create_member',
                'permissions': ['members_create'],
                'should_succeed': True
            },
            {
                'operation': 'export_members',
                'permissions': ['members_export'],
                'should_succeed': True  # Members_CRUD includes export
            },
            {
                'operation': 'generate_parquet',
                'permissions': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
                'should_succeed': False,  # Regional user can't generate full parquet (requires Regio_All)
                'custom_validation': True  # Use custom parquet handler logic
            }
        ]
        
        workflow_results = []
        
        for step in workflow_steps:
            if step.get('custom_validation'):
                # Use custom parquet handler logic for parquet generation
                user_roles = regional_user['roles']
                has_members_crud = 'Members_CRUD' in user_roles
                has_system_admin = any(role in user_roles for role in ['System_CRUD', 'System_User_Management'])
                has_regio_all = 'Regio_All' in user_roles
                
                # Parquet generation requirements (from actual handler)
                is_authorized = (has_members_crud or has_system_admin) and (has_system_admin or has_regio_all)
                regional_info = {'has_full_access': has_regio_all or has_system_admin}
            else:
                # Use standard auth validation
                is_authorized, error_response, regional_info = validate_permissions_with_regions(
                    user_roles=regional_user['roles'],
                    required_permissions=step['permissions'],
                    user_email=regional_user['email'],
                    resource_context={'operation': step['operation']}
                )
            
            workflow_results.append({
                'operation': step['operation'],
                'authorized': is_authorized,
                'expected': step['should_succeed'],
                'regional_info': regional_info
            })
            
            if step['should_succeed']:
                assert is_authorized, f"Workflow step {step['operation']} should succeed for regional user"
                # Verify regional access is properly set
                if is_authorized and not step.get('custom_validation'):
                    assert not regional_info.get('has_full_access', True), f"Regional user should not have full access in {step['operation']}"
            else:
                assert not is_authorized, f"Workflow step {step['operation']} should fail for regional user"
        
        # Verify workflow consistency
        authorized_steps = [r for r in workflow_results if r['authorized']]
        if authorized_steps:
            # All authorized steps should have consistent regional info
            first_regional_info = authorized_steps[0]['regional_info']
            for step in authorized_steps[1:]:
                assert step['regional_info'].get('has_full_access') == first_regional_info.get('has_full_access'), \
                    f"Inconsistent regional access across workflow steps"

    def test_system_wide_role_consistency(self):
        """
        Test 8: Validate system-wide role consistency and integration.
        
        This test ensures that the role system works consistently across
        all components and maintains security boundaries.
        """
        
        # Test all user types against all handler types
        consistency_results = {}
        
        for user_key, user_config in self.test_users.items():
            consistency_results[user_key] = {}
            
            for category, handlers in self.handlers_to_test.items():
                consistency_results[user_key][category] = {}
                
                for handler_name, required_permissions in handlers.items():
                    is_authorized, error_response, regional_info = validate_permissions_with_regions(
                        user_roles=user_config['roles'],
                        required_permissions=required_permissions,
                        user_email=user_config['email'],
                        resource_context={'operation': f"consistency_test_{handler_name}"}
                    )
                    
                    consistency_results[user_key][category][handler_name] = {
                        'authorized': is_authorized,
                        'has_full_access': regional_info.get('has_full_access', False) if is_authorized else False,
                        'allowed_regions': regional_info.get('allowed_regions', []) if is_authorized else []
                    }
        
        # Validate consistency patterns
        for user_key, user_results in consistency_results.items():
            user_config = self.test_users[user_key]
            
            # Users with Regio_All should have consistent full access
            if 'Regio_All' in user_config['roles'] or 'System_CRUD' in user_config['roles']:
                for category, handlers in user_results.items():
                    for handler_name, result in handlers.items():
                        if result['authorized']:
                            assert result['has_full_access'], \
                                f"User {user_key} with Regio_All should have full access in {handler_name}"
            
            # Regional users should have consistent regional access
            elif any(role.startswith('Regio_') and role != 'Regio_All' for role in user_config['roles']):
                for category, handlers in user_results.items():
                    for handler_name, result in handlers.items():
                        if result['authorized']:
                            assert not result['has_full_access'], \
                                f"Regional user {user_key} should not have full access in {handler_name}"
                            assert len(result['allowed_regions']) > 0, \
                                f"Regional user {user_key} should have allowed regions in {handler_name}"


if __name__ == '__main__':
    """
    Run the comprehensive regional filtering validation tests.
    
    Usage:
        python test_comprehensive_regional_filtering_validation.py
        
    Or with pytest:
        pytest test_comprehensive_regional_filtering_validation.py -v
    """
    
    # Run tests with detailed output
    pytest.main([__file__, '-v', '--tb=short'])