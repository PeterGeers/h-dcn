"""
Comprehensive Backend Authentication Testing
Tests auth flows, failure scenarios, and logging as specified in the centralized auth implementation plan
"""

import json
import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the shared directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    validate_permissions,
    determine_regional_access,
    check_regional_data_access,
    get_user_accessible_regions,
    cors_headers,
    create_error_response,
    create_success_response
)
from maintenance_fallback import (
    create_maintenance_response,
    log_auth_system_failure,
    create_smart_fallback_handler
)


class TestAuthenticationFlows:
    """Test core authentication flows with various scenarios"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None, username=None):
        """Helper to create valid JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "username": username or email,
            "cognito:username": username or email,
            "cognito:groups": groups,
            "exp": 9999999999,  # Far future expiry
            "iat": 1000000000
        }
        
        # Create a simple JWT (header.payload.signature)
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_successful_credential_extraction(self):
        """Test successful extraction of user credentials from JWT"""
        token = self.create_jwt_token("test@hdcn.nl", ["hdcnLeden", "Regio_1"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email == "test@hdcn.nl"
        assert "hdcnLeden" in roles
        assert "Regio_1" in roles
        assert error is None
    
    def test_enhanced_groups_header_priority(self):
        """Test that enhanced groups header takes priority over JWT groups"""
        token = self.create_jwt_token("test@hdcn.nl", ["hdcnLeden"])
        enhanced_groups = ["Members_CRUD", "Regio_All"]
        
        event = {
            'headers': {
                'Authorization': f'Bearer {token}',
                'X-Enhanced-Groups': json.dumps(enhanced_groups)
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email == "test@hdcn.nl"
        assert roles == enhanced_groups
        assert error is None
    
    def test_missing_authorization_header(self):
        """Test handling of missing authorization header"""
        event = {'headers': {}}
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'Authorization header required' in json.loads(error['body'])['error']
    
    def test_invalid_bearer_format(self):
        """Test handling of invalid bearer token format"""
        event = {
            'headers': {
                'Authorization': 'InvalidFormat token123'
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'Invalid authorization header format' in json.loads(error['body'])['error']
    
    def test_malformed_jwt_token(self):
        """Test handling of malformed JWT tokens"""
        event = {
            'headers': {
                'Authorization': 'Bearer invalid.jwt'  # Only 2 parts instead of 3
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'Invalid JWT token format' in json.loads(error['body'])['error']
    
    def test_empty_jwt_token(self):
        """Test handling of empty or null JWT tokens"""
        test_cases = ['', 'undefined', 'null']
        
        for invalid_token in test_cases:
            event = {
                'headers': {
                    'Authorization': f'Bearer {invalid_token}'
                }
            }
            
            email, roles, error = extract_user_credentials(event)
            
            assert email is None
            assert roles is None
            assert error is not None
            assert error['statusCode'] == 401
            assert 'Empty or invalid JWT token' in json.loads(error['body'])['error']
    
    def test_jwt_without_email(self):
        """Test handling of JWT tokens without email field"""
        payload = {
            "sub": "user123",
            "cognito:groups": ["hdcnLeden"],
            "exp": 9999999999
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        token = f"{header}.{payload_encoded}.{signature}"
        
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'User email not found in token' in json.loads(error['body'])['error']


class TestPermissionValidation:
    """Test permission validation with various role combinations"""
    
    def test_basic_member_permissions(self):
        """Test basic member permissions"""
        user_roles = ["hdcnLeden"]
        required_permissions = ["profile_read", "webshop_access"]
        
        is_authorized, error = validate_permissions(user_roles, required_permissions)
        
        assert is_authorized is True
        assert error is None
    
    def test_admin_permissions(self):
        """Test system admin permissions"""
        user_roles = ["System_CRUD"]
        required_permissions = ["members_create", "members_delete"]
        
        is_authorized, error = validate_permissions(user_roles, required_permissions)
        
        assert is_authorized is True
        assert error is None
    
    def test_permission_denied(self):
        """Test permission denial for insufficient permissions"""
        user_roles = ["hdcnLeden"]
        required_permissions = ["members_create", "system_admin"]
        
        is_authorized, error = validate_permissions(user_roles, required_permissions)
        
        assert is_authorized is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'Access denied: Insufficient permissions' in json.loads(error['body'])['error']
    
    def test_multiple_role_permissions(self):
        """Test combined permissions from multiple roles"""
        user_roles = ["Members_Read", "Events_CRUD", "Regio_1"]
        required_permissions = ["members_read", "events_create"]
        
        is_authorized, error = validate_permissions(user_roles, required_permissions)
        
        assert is_authorized is True
        assert error is None
    
    def test_regional_permission_validation(self):
        """Test regional permission validation"""
        user_roles = ["Members_Read", "Regio_1"]
        required_permissions = ["members_read"]
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, "test@hdcn.nl"
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info is not None
        assert regional_info['access_type'] == 'regional'
        assert '1' in regional_info['allowed_regions']
    
    def test_national_access_permissions(self):
        """Test national access permissions"""
        user_roles = ["Members_CRUD", "Regio_All"]
        required_permissions = ["members_read"]
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, "admin@hdcn.nl"
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info is not None
        assert regional_info['access_type'] == 'national'
        assert regional_info['has_full_access'] is True
    
    def test_missing_region_assignment(self):
        """Test permission denial when region assignment is missing"""
        user_roles = ["Members_CRUD"]  # Permission role without region
        required_permissions = ["members_read"]
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, "test@hdcn.nl"
        )
        
        assert is_authorized is False
        assert error_response is not None
        assert error_response['statusCode'] == 403
        assert 'Permission requires region assignment' in json.loads(error_response['body'])['error']


class TestRegionalAccess:
    """Test regional access control functionality"""
    
    def test_determine_regional_access_admin(self):
        """Test regional access determination for system admin"""
        user_roles = ["System_CRUD"]
        
        regional_info = determine_regional_access(user_roles)
        
        assert regional_info['has_full_access'] is True
        assert regional_info['allowed_regions'] == ['all']
        assert regional_info['access_type'] == 'admin'
    
    def test_determine_regional_access_national(self):
        """Test regional access determination for national roles"""
        user_roles = ["Members_Read", "Regio_All"]
        
        regional_info = determine_regional_access(user_roles)
        
        assert regional_info['has_full_access'] is True
        assert regional_info['allowed_regions'] == ['all']
        assert regional_info['access_type'] == 'national'
    
    def test_determine_regional_access_specific_regions(self):
        """Test regional access determination for specific regions"""
        user_roles = ["Members_Read", "Regio_1", "Regio_3"]
        
        regional_info = determine_regional_access(user_roles)
        
        assert regional_info['has_full_access'] is False
        assert set(regional_info['allowed_regions']) == {'1', '3'}
        assert regional_info['access_type'] == 'regional'
    
    def test_check_regional_data_access_allowed(self):
        """Test regional data access check - allowed"""
        user_roles = ["Members_Read", "Regio_1", "Regio_2"]
        data_region = "1"
        
        is_allowed, reason = check_regional_data_access(user_roles, data_region, "test@hdcn.nl")
        
        assert is_allowed is True
        assert "Regional access to 1" in reason
    
    def test_check_regional_data_access_denied(self):
        """Test regional data access check - denied"""
        user_roles = ["Members_Read", "Regio_1"]
        data_region = "3"  # User doesn't have access to region 3
        
        is_allowed, reason = check_regional_data_access(user_roles, data_region, "test@hdcn.nl")
        
        assert is_allowed is False
        assert "Access denied" in reason
        assert "can only access regions ['1']" in reason
    
    def test_get_user_accessible_regions(self):
        """Test getting user's accessible regions"""
        user_roles = ["Members_Read", "Regio_2", "Regio_5"]
        
        accessible_regions = get_user_accessible_regions(user_roles)
        
        assert set(accessible_regions) == {'2', '5'}


class TestFailureScenarios:
    """Test various failure scenarios and error handling"""
    
    @patch('shared.auth_utils.base64.urlsafe_b64decode')
    def test_jwt_decode_failure(self, mock_decode):
        """Test JWT decoding failure handling"""
        mock_decode.side_effect = Exception("Decode error")
        
        token = "header.payload.signature"
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 503  # Should fallback to maintenance response
    
    @patch('shared.auth_utils.json.loads')
    def test_json_parse_failure(self, mock_json_loads):
        """Test JSON parsing failure in JWT payload"""
        mock_json_loads.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        token = self.create_jwt_token()
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 503  # Should fallback to maintenance response
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    @patch('shared.maintenance_fallback.create_maintenance_response')
    def test_maintenance_fallback_integration(self, mock_maintenance):
        """Test integration with maintenance fallback system"""
        mock_maintenance.return_value = {
            'statusCode': 503,
            'body': json.dumps({'status': 'maintenance'})
        }
        
        # Simulate auth system failure
        with patch('shared.auth_utils.base64.urlsafe_b64decode', side_effect=Exception("System failure")):
            token = "invalid.token.here"
            event = {
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
            
            email, roles, error = extract_user_credentials(event)
            
            assert email is None
            assert roles is None
            assert error is not None
            mock_maintenance.assert_called_once()
    
    def test_invalid_enhanced_groups_header(self):
        """Test handling of invalid enhanced groups header"""
        token = self.create_jwt_token("test@hdcn.nl", ["hdcnLeden"])
        
        event = {
            'headers': {
                'Authorization': f'Bearer {token}',
                'X-Enhanced-Groups': 'invalid-json'  # Invalid JSON
            }
        }
        
        email, roles, error = extract_user_credentials(event)
        
        # Should fall back to JWT groups
        assert email == "test@hdcn.nl"
        assert roles == ["hdcnLeden"]
        assert error is None


class TestMaintenanceFallback:
    """Test maintenance fallback functionality"""
    
    def test_create_maintenance_response(self):
        """Test creation of maintenance response"""
        response = create_maintenance_response()
        
        assert response['statusCode'] == 503
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == 'Service Temporarily Unavailable'
        assert body['contact'] == 'webmaster@h-dcn.nl'
        assert body['status'] == 'maintenance'
        assert 'timestamp' in body
    
    def test_log_auth_system_failure(self):
        """Test structured logging of auth system failures"""
        mock_context = Mock()
        mock_context.function_name = "test_function"
        
        import_error = ImportError("Cannot import auth_utils")
        
        with patch('builtins.print') as mock_print:
            error_details = log_auth_system_failure(mock_context, import_error)
            
            assert error_details['error_type'] == 'AUTH_SYSTEM_FAILURE'
            assert error_details['function_name'] == 'test_function'
            assert error_details['severity'] == 'CRITICAL'
            assert error_details['contact'] == 'webmaster@h-dcn.nl'
            
            # Verify structured logging was called
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('AUTH_SYSTEM_FAILURE' in call for call in print_calls)
    
    def test_smart_fallback_handler_creation(self):
        """Test creation of smart fallback handler"""
        handler = create_smart_fallback_handler("test_handler")
        
        assert callable(handler)
        
        # Test the handler
        mock_context = Mock()
        mock_context.function_name = "test_function"
        
        event = {'httpMethod': 'GET'}
        
        with patch('builtins.print'):
            response = handler(event, mock_context)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['status'] == 'maintenance'
    
    def test_smart_fallback_options_handling(self):
        """Test smart fallback handler OPTIONS request handling"""
        handler = create_smart_fallback_handler("test_handler")
        
        mock_context = Mock()
        mock_context.function_name = "test_handler"  # Set function_name as string
        event = {'httpMethod': 'OPTIONS'}
        
        with patch('builtins.print'):
            response = handler(event, mock_context)
            
            assert response['statusCode'] == 200
            assert response['body'] == ''
            assert 'Access-Control-Allow-Origin' in response['headers']


class TestLoggingAndAudit:
    """Test logging and audit functionality"""
    
    def test_cors_headers(self):
        """Test CORS headers generation"""
        headers = cors_headers()
        
        expected_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Credentials"
        ]
        
        for header in expected_headers:
            assert header in headers
        
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "Authorization" in headers["Access-Control-Allow-Headers"]
        assert "X-Enhanced-Groups" in headers["Access-Control-Allow-Headers"]
    
    def test_create_error_response(self):
        """Test standardized error response creation"""
        response = create_error_response(400, "Bad Request", {"field": "email"})
        
        assert response['statusCode'] == 400
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error'] == "Bad Request"
        assert body['field'] == "email"
    
    def test_create_success_response(self):
        """Test standardized success response creation"""
        data = {"message": "Success", "user_id": "123"}
        response = create_success_response(data, 201)
        
        assert response['statusCode'] == 201
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['message'] == "Success"
        assert body['user_id'] == "123"
    
    @patch('builtins.print')
    def test_permission_denial_logging(self, mock_print):
        """Test permission denial logging"""
        from auth_utils import log_permission_denial
        
        user_email = "test@hdcn.nl"
        user_roles = ["hdcnLeden", "Regio_1"]
        required_permissions = ["members_create"]
        user_permissions = ["members_read", "profile_update"]
        
        log_permission_denial(user_email, user_roles, required_permissions, user_permissions)
        
        # Verify structured logging was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Check for structured JSON log
        json_log_found = False
        for call in print_calls:
            if 'SECURITY_AUDIT' in call:
                try:
                    log_data = json.loads(call.split('SECURITY_AUDIT: ')[1])
                    assert log_data['event_type'] == 'PERMISSION_DENIED'
                    assert log_data['user_email'] == user_email
                    assert log_data['role_structure_version'] == '2.0'
                    json_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log_found, "Structured JSON log not found in print calls"
    
    @patch('builtins.print')
    def test_successful_access_logging(self, mock_print):
        """Test successful access logging"""
        from auth_utils import log_successful_access
        
        user_email = "admin@hdcn.nl"
        user_roles = ["Members_CRUD", "Regio_All"]
        operation = "members_list"
        
        log_successful_access(user_email, user_roles, operation)
        
        # Verify structured logging was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Check for structured JSON log
        json_log_found = False
        for call in print_calls:
            if 'ACCESS_AUDIT' in call:
                try:
                    log_data = json.loads(call.split('ACCESS_AUDIT: ')[1])
                    assert log_data['event_type'] == 'ACCESS_GRANTED'
                    assert log_data['user_email'] == user_email
                    assert log_data['access_level'] == 'national_admin'
                    json_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log_found, "Structured JSON log not found in print calls"
    
    @patch('builtins.print')
    def test_regional_access_logging(self, mock_print):
        """Test regional access event logging"""
        from auth_utils import log_regional_access_event
        
        user_email = "regional@hdcn.nl"
        user_roles = ["Members_Read", "Regio_2"]
        data_region = "2"
        access_granted = True
        reason = "Regional access to 2"
        
        log_regional_access_event(user_email, user_roles, data_region, access_granted, reason)
        
        # Verify structured logging was called
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Check for structured JSON log
        json_log_found = False
        for call in print_calls:
            if 'REGIONAL_ACCESS_AUDIT' in call:
                try:
                    log_data = json.loads(call.split('REGIONAL_ACCESS_AUDIT: ')[1])
                    assert log_data['event_type'] == 'REGIONAL_ACCESS_CHECK'
                    assert log_data['user_email'] == user_email
                    assert log_data['data_region'] == data_region
                    assert log_data['access_granted'] == access_granted
                    json_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log_found, "Structured JSON log not found in print calls"


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_complete_auth_flow_basic_member(self):
        """Test complete authentication flow for basic member"""
        token = self.create_jwt_token("member@hdcn.nl", ["hdcnLeden"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Extract credentials
        email, roles, error = extract_user_credentials(event)
        assert email == "member@hdcn.nl"
        assert roles == ["hdcnLeden"]
        assert error is None
        
        # Validate permissions for member operations
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["profile_read", "webshop_access"], email
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info['access_type'] == 'basic_member'
    
    def test_complete_auth_flow_regional_admin(self):
        """Test complete authentication flow for regional admin"""
        token = self.create_jwt_token("regional@hdcn.nl", ["Members_CRUD", "Events_Read", "Regio_3"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Extract credentials
        email, roles, error = extract_user_credentials(event)
        assert email == "regional@hdcn.nl"
        assert roles == ["Members_CRUD", "Events_Read", "Regio_3"]
        assert error is None
        
        # Validate permissions for admin operations
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_read", "events_read"], email
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info['access_type'] == 'regional'
        assert '3' in regional_info['allowed_regions']
        
        # Test regional data access
        is_allowed, reason = check_regional_data_access(roles, "3", email)
        assert is_allowed is True
        
        # Test access to different region (should be denied)
        is_allowed, reason = check_regional_data_access(roles, "1", email)
        assert is_allowed is False
    
    def test_complete_auth_flow_national_admin(self):
        """Test complete authentication flow for national admin"""
        token = self.create_jwt_token("national@hdcn.nl", ["Members_CRUD", "Events_CRUD", "Regio_All"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Extract credentials
        email, roles, error = extract_user_credentials(event)
        assert email == "national@hdcn.nl"
        assert roles == ["Members_CRUD", "Events_CRUD", "Regio_All"]
        assert error is None
        
        # Validate permissions for admin operations
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_create", "events_delete"], email
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info['access_type'] == 'national'
        assert regional_info['has_full_access'] is True
        
        # Test access to any region
        for region in ["1", "2", "3", "4", "5"]:
            is_allowed, reason = check_regional_data_access(roles, region, email)
            assert is_allowed is True
    
    def test_auth_flow_with_enhanced_groups(self):
        """Test authentication flow with enhanced groups from frontend"""
        token = self.create_jwt_token("enhanced@hdcn.nl", ["hdcnLeden"])
        enhanced_groups = ["Members_Read", "Events_CRUD", "Regio_1", "Regio_2"]
        
        event = {
            'headers': {
                'Authorization': f'Bearer {token}',
                'X-Enhanced-Groups': json.dumps(enhanced_groups)
            }
        }
        
        # Extract credentials (should use enhanced groups)
        email, roles, error = extract_user_credentials(event)
        assert email == "enhanced@hdcn.nl"
        assert roles == enhanced_groups
        assert error is None
        
        # Validate enhanced permissions
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            roles, ["members_read", "events_create"], email
        )
        
        assert is_authorized is True
        assert error_response is None
        assert regional_info['access_type'] == 'regional'
        assert set(regional_info['allowed_regions']) == {'1', '2'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])