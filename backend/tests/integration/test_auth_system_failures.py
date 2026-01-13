"""
Integration Tests for Authentication System Failures
Tests real handler behavior when auth system fails and fallback mechanisms
"""

import json
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# Add the handler directories to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handler'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))


class TestAuthSystemFailureIntegration:
    """Test integration scenarios when auth system fails"""
    
    def load_handler_module(self, handler_path):
        """Dynamically load a handler module for testing"""
        spec = importlib.util.spec_from_file_location("handler", handler_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def test_handler_with_auth_import_failure(self):
        """Test handler behavior when shared auth import fails"""
        # Create a mock handler that simulates import failure
        mock_event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer valid.jwt.token'
            },
            'body': None
        }
        
        mock_context = Mock()
        mock_context.function_name = 'test_handler'
        
        # Simulate the try/except pattern used in handlers
        try:
            # This should fail
            from shared.auth_utils_nonexistent import extract_user_credentials
            assert False, "Should not reach this point"
        except ImportError as e:
            # Test the fallback pattern
            from shared.maintenance_fallback import create_smart_fallback_pattern
            
            fallback_handler = create_smart_fallback_pattern(mock_context, e, "test_handler")
            
            with patch('builtins.print') as mock_print:
                response = fallback_handler(mock_event, mock_context)
                
                # Verify maintenance response
                assert response['statusCode'] == 503
                body = json.loads(response['body'])
                assert body['status'] == 'maintenance'
                assert body['contact'] == 'webmaster@h-dcn.nl'
                
                # Verify structured logging
                mock_print.assert_called()
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                assert any('AUTH_SYSTEM_FAILURE' in call for call in print_calls)
    
    def test_handler_options_request_during_failure(self):
        """Test OPTIONS request handling during auth system failure"""
        mock_event = {
            'httpMethod': 'OPTIONS',
            'headers': {},
            'body': None
        }
        
        mock_context = Mock()
        mock_context.function_name = 'test_handler'
        
        # Simulate auth import failure and fallback
        from shared.maintenance_fallback import create_smart_fallback_handler
        
        fallback_handler = create_smart_fallback_handler("test_handler")
        
        with patch('builtins.print'):
            response = fallback_handler(mock_event, mock_context)
            
            # OPTIONS should still work during maintenance
            assert response['statusCode'] == 200
            assert response['body'] == ''
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_multiple_handler_failure_scenarios(self):
        """Test multiple handlers failing simultaneously"""
        handler_names = ['get_members', 'create_member', 'update_member', 'get_events']
        
        mock_context = Mock()
        import_error = ImportError("Shared auth system unavailable")
        
        responses = []
        
        for handler_name in handler_names:
            mock_context.function_name = handler_name
            
            from shared.maintenance_fallback import create_smart_fallback_handler
            fallback_handler = create_smart_fallback_handler(handler_name)
            
            mock_event = {
                'httpMethod': 'GET',
                'headers': {'Authorization': 'Bearer token'},
                'body': None
            }
            
            with patch('builtins.print'):
                response = fallback_handler(mock_event, mock_context)
                responses.append(response)
        
        # All handlers should return consistent maintenance responses
        for response in responses:
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['status'] == 'maintenance'
            assert body['contact'] == 'webmaster@h-dcn.nl'
            assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_auth_function_internal_failure(self):
        """Test when auth functions fail internally during base64 decoding"""
        # Create a JWT with valid format (3 parts) but invalid base64 content
        # This will pass the format check but fail during base64 decoding
        mock_event = {
            'headers': {
                'Authorization': 'Bearer valid.invalid_base64_content_that_will_fail.signature'
            }
        }
        
        from shared.auth_utils import extract_user_credentials
        
        # The function should handle internal failures gracefully
        email, roles, error = extract_user_credentials(mock_event)
        
        assert email is None
        assert roles is None
        assert error is not None
        assert error['statusCode'] == 503  # Should return maintenance response for internal failures
        
        body = json.loads(error['body'])
        assert body['error'] == 'Service Temporarily Unavailable'
        assert body['status'] == 'maintenance'
        assert 'webmaster@h-dcn.nl' in body['contact']
    
    def test_permission_validation_internal_failure(self):
        """Test when permission validation fails internally"""
        user_roles = ["hdcnLeden"]
        required_permissions = ["members_read"]
        
        # Patch the validate_permissions function to simulate internal failure
        with patch('shared.auth_utils.validate_permissions', side_effect=Exception("Permission system error")):
            from shared.auth_utils import validate_permissions_with_regions
            
            # The function should handle internal failures gracefully
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, required_permissions, "test@hdcn.nl"
            )
            
            assert is_authorized is False
            assert error_response is not None
            assert error_response['statusCode'] == 503  # Should return maintenance response
            assert regional_info is None
            
            body = json.loads(error_response['body'])
            assert body['status'] == 'maintenance'


class TestAuthSystemRecovery:
    """Test authentication system recovery scenarios"""
    
    def test_auth_system_recovery_after_failure(self):
        """Test system behavior when auth system recovers"""
        # First, simulate failure
        with patch('shared.auth_utils.base64.urlsafe_b64decode', side_effect=Exception("Temporary failure")):
            from shared.auth_utils import extract_user_credentials
            
            mock_event = {
                'headers': {
                    'Authorization': 'Bearer valid.jwt.token'
                }
            }
            
            email, roles, error = extract_user_credentials(mock_event)
            
            # Should get maintenance response
            assert email is None
            assert roles is None
            assert error is not None
            assert error['statusCode'] == 503
        
        # Then, test recovery (without the patch, normal operation should work)
        import base64
        
        payload = {
            "email": "test@hdcn.nl",
            "cognito:groups": ["hdcnLeden"]
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        token = f"{header}.{payload_encoded}.{signature}"
        
        mock_event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        email, roles, error = extract_user_credentials(mock_event)
        
        # Should work normally after recovery
        assert email == "test@hdcn.nl"
        assert roles == ["hdcnLeden"]
        assert error is None
    
    def test_partial_auth_system_failure(self):
        """Test when only part of auth system fails"""
        # Test when credential extraction works but permission validation fails
        import base64
        
        payload = {
            "email": "test@hdcn.nl",
            "cognito:groups": ["hdcnLeden"]
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        token = f"{header}.{payload_encoded}.{signature}"
        
        mock_event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        from shared.auth_utils import extract_user_credentials
        
        # Credential extraction should work
        email, roles, error = extract_user_credentials(mock_event)
        assert email == "test@hdcn.nl"
        assert roles == ["hdcnLeden"]
        assert error is None
        
        # But permission validation might fail
        with patch('shared.auth_utils.validate_permissions', side_effect=Exception("Permission system down")):
            from shared.auth_utils import validate_permissions_with_regions
            
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                roles, ["members_read"], email
            )
            
            # Should get maintenance response for permission validation failure
            assert is_authorized is False
            assert error_response is not None
            assert error_response['statusCode'] == 503
            assert regional_info is None


class TestLoggingDuringFailures:
    """Test logging behavior during authentication failures"""
    
    @patch('builtins.print')
    def test_structured_logging_during_auth_failure(self, mock_print):
        """Test that structured logging works during auth failures"""
        mock_context = Mock()
        mock_context.function_name = 'test_handler'
        
        import_error = ImportError("Cannot import shared auth")
        
        from shared.maintenance_fallback import log_auth_system_failure
        
        error_details = log_auth_system_failure(mock_context, import_error)
        
        # Verify structured logging
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        # Check for structured JSON log
        json_log_found = False
        for call in print_calls:
            if 'AUTH_SYSTEM_FAILURE' in call and '{' in call:
                try:
                    # Extract JSON part
                    json_part = call.split('AUTH_SYSTEM_FAILURE: ')[1]
                    log_data = json.loads(json_part)
                    
                    assert log_data['error_type'] == 'AUTH_SYSTEM_FAILURE'
                    assert log_data['function_name'] == 'test_handler'
                    assert log_data['severity'] == 'CRITICAL'
                    assert log_data['contact'] == 'webmaster@h-dcn.nl'
                    assert 'timestamp' in log_data
                    
                    json_log_found = True
                    break
                except (IndexError, json.JSONDecodeError):
                    continue
        
        assert json_log_found, "Structured JSON log not found"
        
        # Check for human-readable logs
        human_readable_logs = [call for call in print_calls if 'FIND THIS LOG' in call or 'CONTACT' in call]
        assert len(human_readable_logs) >= 2, "Human-readable logs not found"
    
    @patch('builtins.print')
    def test_cloudwatch_log_group_identification(self, mock_print):
        """Test that CloudWatch log group is properly identified in logs"""
        mock_context = Mock()
        mock_context.function_name = 'get_members_handler'
        
        import_error = ImportError("Auth system unavailable")
        
        from shared.maintenance_fallback import log_auth_system_failure
        
        log_auth_system_failure(mock_context, import_error)
        
        # Verify CloudWatch log group is mentioned
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        log_group_mentioned = False
        for call in print_calls:
            if '/aws/lambda/get_members_handler' in call:
                log_group_mentioned = True
                break
        
        assert log_group_mentioned, "CloudWatch log group not mentioned in logs"
    
    @patch('builtins.print')
    def test_contact_information_in_logs(self, mock_print):
        """Test that contact information is included in failure logs"""
        mock_context = Mock()
        mock_context.function_name = 'test_handler'
        
        import_error = ImportError("System failure")
        
        from shared.maintenance_fallback import log_auth_system_failure
        
        log_auth_system_failure(mock_context, import_error)
        
        # Verify contact information is in logs
        mock_print.assert_called()
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        
        contact_mentioned = False
        for call in print_calls:
            if 'webmaster@h-dcn.nl' in call:
                contact_mentioned = True
                break
        
        assert contact_mentioned, "Contact information not found in logs"


class TestCORSHandlingDuringFailures:
    """Test CORS header handling during authentication failures"""
    
    def test_cors_headers_in_maintenance_response(self):
        """Test that CORS headers are present in maintenance responses"""
        from shared.maintenance_fallback import create_maintenance_response
        
        response = create_maintenance_response()
        
        # Verify all required CORS headers are present
        required_cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Credentials"
        ]
        
        for header in required_cors_headers:
            assert header in response['headers'], f"Missing CORS header: {header}"
        
        # Verify header values
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Authorization' in response['headers']['Access-Control-Allow-Headers']
        assert 'X-Enhanced-Groups' in response['headers']['Access-Control-Allow-Headers']
    
    def test_cors_headers_in_auth_error_responses(self):
        """Test that CORS headers are present in auth error responses"""
        from shared.auth_utils import extract_user_credentials
        
        # Test with missing authorization header
        mock_event = {'headers': {}}
        
        email, roles, error = extract_user_credentials(mock_event)
        
        assert error is not None
        assert 'Access-Control-Allow-Origin' in error['headers']
        assert error['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_options_request_during_auth_failure(self):
        """Test OPTIONS request handling during auth system failure"""
        from shared.maintenance_fallback import create_smart_fallback_handler
        
        handler = create_smart_fallback_handler("test_handler")
        
        mock_context = Mock()
        mock_context.function_name = 'test_handler'
        
        options_event = {
            'httpMethod': 'OPTIONS',
            'headers': {},
            'body': None
        }
        
        with patch('builtins.print'):
            response = handler(options_event, mock_context)
            
            # OPTIONS should return 200 with proper CORS headers
            assert response['statusCode'] == 200
            assert response['body'] == ''
            
            # Verify CORS headers
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert 'Access-Control-Allow-Methods' in response['headers']
            assert 'Access-Control-Allow-Headers' in response['headers']


class TestErrorResponseConsistency:
    """Test consistency of error responses across different failure scenarios"""
    
    def test_maintenance_response_format_consistency(self):
        """Test that all maintenance responses have consistent format"""
        from shared.maintenance_fallback import create_maintenance_response
        
        # Test multiple calls to ensure consistency
        responses = [create_maintenance_response() for _ in range(5)]
        
        for response in responses:
            assert response['statusCode'] == 503
            
            body = json.loads(response['body'])
            required_fields = ['error', 'message', 'contact', 'status', 'retry_after', 'timestamp']
            
            for field in required_fields:
                assert field in body, f"Missing field in maintenance response: {field}"
            
            assert body['error'] == 'Service Temporarily Unavailable'
            assert body['contact'] == 'webmaster@h-dcn.nl'
            assert body['status'] == 'maintenance'
            assert body['retry_after'] == '300'
    
    def test_auth_error_response_format_consistency(self):
        """Test that auth error responses have consistent format"""
        from shared.auth_utils import extract_user_credentials
        
        # Test different auth error scenarios
        test_cases = [
            {'headers': {}},  # Missing auth header
            {'headers': {'Authorization': 'InvalidFormat'}},  # Invalid format
            {'headers': {'Authorization': 'Bearer invalid.jwt'}},  # Invalid JWT
        ]
        
        for event in test_cases:
            email, roles, error = extract_user_credentials(event)
            
            assert email is None
            assert roles is None
            assert error is not None
            assert error['statusCode'] in [401, 503]  # Either auth error or maintenance
            
            # Verify response structure
            assert 'headers' in error
            assert 'body' in error
            assert 'Access-Control-Allow-Origin' in error['headers']
            
            body = json.loads(error['body'])
            assert 'error' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])