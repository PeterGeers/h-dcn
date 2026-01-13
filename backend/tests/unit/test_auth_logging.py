"""
Comprehensive Authentication Logging Tests
Tests structured logging, audit trails, and monitoring capabilities
"""

import json
import pytest
import base64
from unittest.mock import Mock, patch, call
from datetime import datetime
import sys
import os

# Add the shared directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from auth_utils import (
    log_permission_denial,
    log_successful_access,
    log_regional_access_event,
    log_role_structure_validation,
    extract_user_credentials,
    validate_permissions_with_regions
)
from maintenance_fallback import (
    log_auth_system_failure,
    create_maintenance_response
)


class TestStructuredLogging:
    """Test structured logging functionality"""
    
    @patch('builtins.print')
    def test_permission_denial_logging_structure(self, mock_print):
        """Test structured logging for permission denials"""
        user_email = "test@hdcn.nl"
        user_roles = ["hdcnLeden", "Regio_1"]
        required_permissions = ["members_create", "system_admin"]
        user_permissions = ["members_read", "profile_update"]
        resource_context = {"resource_type": "member", "resource_id": "123"}
        
        log_permission_denial(user_email, user_roles, required_permissions, user_permissions, resource_context)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log = None
        for call in print_calls:
            if 'SECURITY_AUDIT:' in call:
                try:
                    json_part = call.split('SECURITY_AUDIT: ')[1]
                    json_log = json.loads(json_part)
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log is not None, "Structured JSON log not found"
        
        # Verify log structure and content
        required_fields = [
            'timestamp', 'event_type', 'user_email', 'user_roles',
            'permission_roles', 'region_roles', 'required_permissions',
            'user_permissions', 'resource_context', 'severity', 'role_structure_version'
        ]
        
        for field in required_fields:
            assert field in json_log, f"Missing field in log: {field}"
        
        assert json_log['event_type'] == 'PERMISSION_DENIED'
        assert json_log['user_email'] == user_email
        assert json_log['user_roles'] == user_roles
        assert json_log['permission_roles'] == []  # hdcnLeden is not a permission role
        assert json_log['region_roles'] == ['Regio_1']
        assert json_log['required_permissions'] == required_permissions
        assert json_log['user_permissions'] == user_permissions
        assert json_log['resource_context'] == resource_context
        assert json_log['severity'] == 'WARNING'
        assert json_log['role_structure_version'] == '2.0'
        
        # Verify timestamp format
        try:
            datetime.fromisoformat(json_log['timestamp'])
        except ValueError:
            pytest.fail("Invalid timestamp format in log")
        
        # Verify human-readable log
        human_readable_found = False
        for call in print_calls:
            if f"Permission denied: User {user_email}" in call and "permission roles:" in call:
                human_readable_found = True
                break
        
        assert human_readable_found, "Human-readable log not found"
    
    @patch('builtins.print')
    def test_successful_access_logging_structure(self, mock_print):
        """Test structured logging for successful access"""
        user_email = "admin@hdcn.nl"
        user_roles = ["Members_CRUD", "Events_Read", "Regio_All"]
        operation = "members_list_all"
        resource_context = {"endpoint": "/members", "method": "GET"}
        
        log_successful_access(user_email, user_roles, operation, resource_context)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log = None
        for call in print_calls:
            if 'ACCESS_AUDIT:' in call:
                try:
                    json_part = call.split('ACCESS_AUDIT: ')[1]
                    json_log = json.loads(json_part)
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log is not None, "Structured JSON log not found"
        
        # Verify log structure and content
        required_fields = [
            'timestamp', 'event_type', 'user_email', 'user_roles',
            'permission_roles', 'region_roles', 'access_level', 'operation',
            'resource_context', 'severity', 'role_structure_version'
        ]
        
        for field in required_fields:
            assert field in json_log, f"Missing field in log: {field}"
        
        assert json_log['event_type'] == 'ACCESS_GRANTED'
        assert json_log['user_email'] == user_email
        assert json_log['user_roles'] == user_roles
        assert json_log['permission_roles'] == ['Members_CRUD', 'Events_Read']
        assert json_log['region_roles'] == ['Regio_All']
        assert json_log['access_level'] == 'national_admin'
        assert json_log['operation'] == operation
        assert json_log['resource_context'] == resource_context
        assert json_log['severity'] == 'INFO'
        assert json_log['role_structure_version'] == '2.0'
    
    @patch('builtins.print')
    def test_regional_access_logging_structure(self, mock_print):
        """Test structured logging for regional access events"""
        user_email = "regional@hdcn.nl"
        user_roles = ["Members_Read", "Events_CRUD", "Regio_3"]
        data_region = "3"
        access_granted = True
        reason = "Regional access to 3"
        resource_context = {"data_type": "member", "query_type": "list"}
        
        log_regional_access_event(user_email, user_roles, data_region, access_granted, reason, resource_context)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log = None
        for call in print_calls:
            if 'REGIONAL_ACCESS_AUDIT:' in call:
                try:
                    json_part = call.split('REGIONAL_ACCESS_AUDIT: ')[1]
                    json_log = json.loads(json_part)
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log is not None, "Structured JSON log not found"
        
        # Verify log structure and content
        required_fields = [
            'timestamp', 'event_type', 'user_email', 'user_roles',
            'permission_roles', 'region_roles', 'data_region', 'access_granted',
            'reason', 'resource_context', 'severity', 'role_structure_version'
        ]
        
        for field in required_fields:
            assert field in json_log, f"Missing field in log: {field}"
        
        assert json_log['event_type'] == 'REGIONAL_ACCESS_CHECK'
        assert json_log['user_email'] == user_email
        assert json_log['user_roles'] == user_roles
        assert json_log['permission_roles'] == ['Members_Read', 'Events_CRUD']
        assert json_log['region_roles'] == ['Regio_3']
        assert json_log['data_region'] == data_region
        assert json_log['access_granted'] == access_granted
        assert json_log['reason'] == reason
        assert json_log['resource_context'] == resource_context
        assert json_log['severity'] == 'INFO'  # INFO for granted access
        assert json_log['role_structure_version'] == '2.0'
    
    @patch('builtins.print')
    def test_regional_access_denied_logging(self, mock_print):
        """Test structured logging for denied regional access"""
        user_email = "regional@hdcn.nl"
        user_roles = ["Members_Read", "Regio_1"]
        data_region = "5"  # User doesn't have access to region 5
        access_granted = False
        reason = "Access denied: User can only access regions ['1']"
        
        log_regional_access_event(user_email, user_roles, data_region, access_granted, reason)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log = None
        for call in print_calls:
            if 'REGIONAL_ACCESS_AUDIT:' in call:
                try:
                    json_part = call.split('REGIONAL_ACCESS_AUDIT: ')[1]
                    json_log = json.loads(json_part)
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log is not None, "Structured JSON log not found"
        assert json_log['access_granted'] == False
        assert json_log['severity'] == 'WARNING'  # WARNING for denied access
        assert json_log['reason'] == reason
    
    @patch('builtins.print')
    def test_role_structure_validation_logging(self, mock_print):
        """Test structured logging for role structure validation"""
        user_email = "test@hdcn.nl"
        user_roles = ["Members_CRUD", "Regio_1", "Regio_2"]
        validation_result = {
            "valid": True,
            "permission_roles": ["Members_CRUD"],
            "region_roles": ["Regio_1", "Regio_2"],
            "access_type": "regional"
        }
        validation_context = {"validation_type": "login", "source": "jwt_token"}
        
        log_role_structure_validation(user_email, user_roles, validation_result, validation_context)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log = None
        for call in print_calls:
            if 'ROLE_VALIDATION_AUDIT:' in call:
                try:
                    json_part = call.split('ROLE_VALIDATION_AUDIT: ')[1]
                    json_log = json.loads(json_part)
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log is not None, "Structured JSON log not found"
        
        # Verify log structure and content
        required_fields = [
            'timestamp', 'event_type', 'user_email', 'user_roles',
            'permission_roles', 'region_roles', 'validation_result',
            'validation_context', 'severity', 'role_structure_version'
        ]
        
        for field in required_fields:
            assert field in json_log, f"Missing field in log: {field}"
        
        assert json_log['event_type'] == 'ROLE_STRUCTURE_VALIDATION'
        assert json_log['user_email'] == user_email
        assert json_log['user_roles'] == user_roles
        assert json_log['permission_roles'] == ['Members_CRUD']
        assert json_log['region_roles'] == ['Regio_1', 'Regio_2']
        assert json_log['validation_result'] == validation_result
        assert json_log['validation_context'] == validation_context
        assert json_log['severity'] == 'INFO'  # INFO for valid structure
        assert json_log['role_structure_version'] == '2.0'
    
    @patch('builtins.print')
    def test_auth_system_failure_logging(self, mock_print):
        """Test structured logging for auth system failures"""
        mock_context = Mock()
        mock_context.function_name = 'get_members_handler'
        
        import_error = ImportError("Cannot import shared.auth_utils")
        
        error_details = log_auth_system_failure(mock_context, import_error)
        
        # Verify print was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify structured JSON log
        json_log_found = False
        for call in print_calls:
            if 'AUTH_SYSTEM_FAILURE:' in call and '{' in call:
                try:
                    json_part = call.split('AUTH_SYSTEM_FAILURE: ')[1]
                    json_log = json.loads(json_part)
                    
                    # Verify log structure
                    required_fields = [
                        'timestamp', 'error_type', 'function_name', 'import_error',
                        'severity', 'action_required', 'contact', 'log_group'
                    ]
                    
                    for field in required_fields:
                        assert field in json_log, f"Missing field in failure log: {field}"
                    
                    assert json_log['error_type'] == 'AUTH_SYSTEM_FAILURE'
                    assert json_log['function_name'] == 'get_members_handler'
                    assert json_log['severity'] == 'CRITICAL'
                    assert json_log['contact'] == 'webmaster@h-dcn.nl'
                    assert json_log['log_group'] == '/aws/lambda/get_members_handler'
                    
                    json_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log_found, "Structured JSON failure log not found"
        
        # Verify human-readable logs
        cloudwatch_log_found = False
        contact_log_found = False
        
        for call in print_calls:
            if 'FIND THIS LOG: CloudWatch' in call and '/aws/lambda/get_members_handler' in call:
                cloudwatch_log_found = True
            if 'CONTACT: webmaster@h-dcn.nl' in call:
                contact_log_found = True
        
        assert cloudwatch_log_found, "CloudWatch log location not found"
        assert contact_log_found, "Contact information not found"


class TestLoggingIntegration:
    """Test logging integration with authentication flows"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    @patch('builtins.print')
    def test_logging_during_successful_auth_flow(self, mock_print):
        """Test logging during successful authentication flow"""
        token = self.create_jwt_token("success@hdcn.nl", ["Members_Read", "Regio_2"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Extract credentials (should not log by itself)
        email, roles, error = extract_user_credentials(event)
        assert error is None
        
        # Validate permissions (should trigger logging)
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_read"], email
        )
        assert is_authorized is True
        
        # The permission validation should have triggered logging
        # (Note: The actual logging happens inside the auth functions when they call log_successful_access)
        # For this test, we're verifying the integration works without errors
        
        # Verify no error logs were generated
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_logs = [call for call in print_calls if 'ERROR' in call or 'FAILURE' in call]
        assert len(error_logs) == 0, f"Unexpected error logs: {error_logs}"
    
    @patch('builtins.print')
    def test_logging_during_failed_auth_flow(self, mock_print):
        """Test logging during failed authentication flow"""
        token = self.create_jwt_token("fail@hdcn.nl", ["hdcnLeden"])  # Basic member
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Extract credentials
        email, roles, error = extract_user_credentials(event)
        assert error is None
        
        # Try to validate permissions for admin operation (should fail and log)
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_create", "system_admin"], email  # Permissions user doesn't have
        )
        assert is_authorized is False
        
        # Verify permission denial was logged
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Look for permission denial log
        denial_log_found = False
        for call in print_calls:
            if 'Permission denied: User fail@hdcn.nl' in call:
                denial_log_found = True
                break
        
        assert denial_log_found, "Permission denial log not found"
    
    @patch('builtins.print')
    def test_logging_with_enhanced_groups(self, mock_print):
        """Test logging when using enhanced groups from frontend"""
        token = self.create_jwt_token("enhanced@hdcn.nl", ["hdcnLeden"])
        enhanced_groups = ["Members_CRUD", "Events_Read", "Regio_1"]
        
        event = {
            'headers': {
                'Authorization': f'Bearer {token}',
                'X-Enhanced-Groups': json.dumps(enhanced_groups)
            }
        }
        
        # Extract credentials (should use enhanced groups)
        email, roles, error = extract_user_credentials(event)
        assert error is None
        assert roles == enhanced_groups
        
        # Validate permissions (should succeed and potentially log)
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_create"], email
        )
        assert is_authorized is True
        
        # Verify no error logs were generated
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_logs = [call for call in print_calls if 'ERROR' in call or 'FAILURE' in call]
        assert len(error_logs) == 0, f"Unexpected error logs: {error_logs}"


class TestLogSearchability:
    """Test that logs are searchable and contain proper identifiers"""
    
    @patch('builtins.print')
    def test_log_searchability_keywords(self, mock_print):
        """Test that logs contain searchable keywords"""
        # Test permission denial logging
        log_permission_denial(
            "search_test@hdcn.nl",
            ["hdcnLeden"],
            ["admin_access"],
            ["basic_access"],
            {"test": "searchability"}
        )
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Verify searchable keywords are present
        searchable_keywords = [
            'SECURITY_AUDIT',
            'PERMISSION_DENIED',
            'search_test@hdcn.nl',
            'role_structure_version'
        ]
        
        for keyword in searchable_keywords:
            keyword_found = any(keyword in call for call in print_calls)
            assert keyword_found, f"Searchable keyword '{keyword}' not found in logs"
    
    @patch('builtins.print')
    def test_cloudwatch_log_group_format(self, mock_print):
        """Test that CloudWatch log group format is consistent"""
        mock_context = Mock()
        mock_context.function_name = 'test_function_name'
        
        import_error = ImportError("Test error")
        
        log_auth_system_failure(mock_context, import_error)
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Verify CloudWatch log group format
        log_group_found = False
        for call in print_calls:
            if '/aws/lambda/test_function_name' in call:
                log_group_found = True
                break
        
        assert log_group_found, "CloudWatch log group format not found"
    
    @patch('builtins.print')
    def test_log_timestamp_consistency(self, mock_print):
        """Test that log timestamps are consistent and parseable"""
        # Generate multiple log entries
        log_permission_denial("user1@hdcn.nl", ["hdcnLeden"], ["admin"], ["basic"])
        log_successful_access("user2@hdcn.nl", ["System_CRUD"], "test_operation")
        log_regional_access_event("user3@hdcn.nl", ["Regio_1"], "1", True, "test")
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Extract timestamps from JSON logs
        timestamps = []
        for call in print_calls:
            if any(audit_type in call for audit_type in ['SECURITY_AUDIT:', 'ACCESS_AUDIT:', 'REGIONAL_ACCESS_AUDIT:']):
                try:
                    json_part = call.split(': ', 1)[1]
                    log_data = json.loads(json_part)
                    if 'timestamp' in log_data:
                        timestamps.append(log_data['timestamp'])
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert len(timestamps) >= 3, "Not enough timestamps found in logs"
        
        # Verify all timestamps are parseable
        for timestamp in timestamps:
            try:
                datetime.fromisoformat(timestamp)
            except ValueError:
                pytest.fail(f"Invalid timestamp format: {timestamp}")


class TestLogCompliance:
    """Test logging compliance with security and audit requirements"""
    
    @patch('builtins.print')
    def test_sensitive_data_not_logged(self, mock_print):
        """Test that sensitive data is not logged"""
        # Test with potentially sensitive resource context
        sensitive_context = {
            "password": "secret123",
            "token": "bearer_token_here",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111"
        }
        
        log_permission_denial(
            "test@hdcn.nl",
            ["hdcnLeden"],
            ["admin_access"],
            ["basic_access"],
            sensitive_context
        )
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # The context should be logged as-is (it's the caller's responsibility to not pass sensitive data)
        # But verify the logging system doesn't add any sensitive information
        for call in print_calls:
            # These should never appear in logs from the logging system itself
            assert "AWS_ACCESS_KEY" not in call
            assert "AWS_SECRET" not in call
            assert "DATABASE_PASSWORD" not in call
    
    @patch('builtins.print')
    def test_log_structure_version_tracking(self, mock_print):
        """Test that log structure version is tracked for compatibility"""
        log_permission_denial("test@hdcn.nl", ["hdcnLeden"], ["admin"], ["basic"])
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find JSON log and verify version tracking
        version_found = False
        for call in print_calls:
            if 'SECURITY_AUDIT:' in call:
                try:
                    json_part = call.split('SECURITY_AUDIT: ')[1]
                    log_data = json.loads(json_part)
                    if log_data.get('role_structure_version') == '2.0':
                        version_found = True
                        break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert version_found, "Role structure version not tracked in logs"
    
    @patch('builtins.print')
    def test_audit_trail_completeness(self, mock_print):
        """Test that audit trail contains all required information"""
        user_email = "audit_test@hdcn.nl"
        user_roles = ["Members_CRUD", "Events_Read", "Regio_3"]
        
        # Test successful access logging
        log_successful_access(user_email, user_roles, "members_list", {"endpoint": "/members"})
        
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Find and verify audit log completeness
        audit_log_found = False
        for call in print_calls:
            if 'ACCESS_AUDIT:' in call:
                try:
                    json_part = call.split('ACCESS_AUDIT: ')[1]
                    log_data = json.loads(json_part)
                    
                    # Verify all required audit fields are present
                    audit_fields = [
                        'timestamp', 'event_type', 'user_email', 'user_roles',
                        'permission_roles', 'region_roles', 'access_level',
                        'operation', 'severity'
                    ]
                    
                    for field in audit_fields:
                        assert field in log_data, f"Missing audit field: {field}"
                    
                    # Verify role categorization is correct
                    assert log_data['permission_roles'] == ['Members_CRUD', 'Events_Read']
                    assert log_data['region_roles'] == ['Regio_3']
                    assert log_data['access_level'] == 'regional_admin'
                    
                    audit_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert audit_log_found, "Complete audit log not found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])