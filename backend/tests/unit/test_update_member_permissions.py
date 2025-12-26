import json
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the handler path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_member'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'hdcn_cognito_admin'))

from app import extract_user_roles_from_jwt, validate_field_permissions, lambda_handler, log_field_permission_denial, log_successful_field_update


class TestUpdateMemberPermissions:
    """Test role-based permission validation for update_member handler"""
    
    def test_extract_user_roles_from_jwt_success(self):
        """Test successful JWT token extraction"""
        # Create a mock JWT token payload
        import base64
        payload = {
            "email": "test@example.com",
            "cognito:groups": ["hdcnLeden", "Members_Read_All"]
        }
        payload_json = json.dumps(payload)
        payload_encoded = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        # Create mock JWT token (header.payload.signature)
        mock_jwt = f"header.{payload_encoded}.signature"
        
        event = {
            'headers': {
                'Authorization': f'Bearer {mock_jwt}'
            }
        }
        
        user_email, user_roles, error = extract_user_roles_from_jwt(event)
        
        assert user_email == "test@example.com"
        assert user_roles == ["hdcnLeden", "Members_Read_All"]
        assert error is None
    
    def test_extract_user_roles_missing_auth_header(self):
        """Test JWT extraction with missing Authorization header"""
        event = {'headers': {}}
        
        user_email, user_roles, error = extract_user_roles_from_jwt(event)
        
        assert user_email is None
        assert user_roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'Authorization header required' in error['body']
    
    def test_extract_user_roles_invalid_bearer_format(self):
        """Test JWT extraction with invalid Bearer format"""
        event = {
            'headers': {
                'Authorization': 'InvalidFormat token'
            }
        }
        
        user_email, user_roles, error = extract_user_roles_from_jwt(event)
        
        assert user_email is None
        assert user_roles is None
        assert error is not None
        assert error['statusCode'] == 401
        assert 'Invalid authorization header format' in error['body']
    
    @patch('app.table')
    def test_validate_field_permissions_own_record_personal_fields(self, mock_table):
        """Test validation for user editing their own personal fields"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'
        member_id = 'test-123'
        fields_to_update = {'voornaam': 'Updated Name', 'telefoon': '123456789'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []
    
    @patch('app.table')
    def test_validate_field_permissions_own_record_admin_fields_denied(self, mock_table):
        """Test validation denies regular user editing administrative fields on own record"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'
        member_id = 'test-123'
        fields_to_update = {'voornaam': 'Updated Name', 'status': 'active'}  # status is admin field
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'status' in forbidden_fields
        assert 'administrative privileges' in error['body']
    
    @patch('app.table')
    def test_validate_field_permissions_other_record_denied(self, mock_table):
        """Test validation denies user editing another user's record"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'other-123',
                'email': 'other@example.com',
                'voornaam': 'Other'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'  # Different from record email
        member_id = 'other-123'
        fields_to_update = {'voornaam': 'Updated Name'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'voornaam' in forbidden_fields
        assert 'only modify your own' in error['body']
    
    @patch('app.table')
    def test_validate_field_permissions_admin_role_allowed(self, mock_table):
        """Test validation allows admin role to edit all fields"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'other-123',
                'email': 'other@example.com',
                'voornaam': 'Other'
            }
        }
        
        user_roles = ['Members_CRUD_All']  # Admin role
        user_email = 'admin@example.com'
        member_id = 'other-123'
        fields_to_update = {'voornaam': 'Updated Name', 'status': 'active'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []
    
    @patch('app.table')
    def test_validate_field_permissions_member_not_found(self, mock_table):
        """Test validation when member record is not found"""
        # Mock DynamoDB response - no item found
        mock_table.get_item.return_value = {}
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'
        member_id = 'nonexistent-123'
        fields_to_update = {'voornaam': 'Updated Name'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 404
        assert 'Member record not found' in error['body']
    
    @patch('app.extract_user_roles_from_jwt')
    @patch('app.validate_field_permissions')
    @patch('app.table')
    def test_lambda_handler_success(self, mock_table, mock_validate, mock_extract):
        """Test successful lambda handler execution"""
        # Mock JWT extraction
        mock_extract.return_value = ('test@example.com', ['hdcnLeden'], None)
        
        # Mock field validation
        mock_validate.return_value = (True, None, [])
        
        # Mock DynamoDB get_item for member record (needed for enhanced logging)
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        # Mock DynamoDB update
        mock_table.update_item.return_value = {}
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'voornaam': 'Updated Name'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        assert 'Member updated successfully' in result['body']
    
    @patch('app.extract_user_roles_from_jwt')
    def test_lambda_handler_auth_error(self, mock_extract):
        """Test lambda handler with authentication error"""
        # Mock JWT extraction error
        auth_error = {
            'statusCode': 401,
            'headers': {},
            'body': json.dumps({'error': 'Authorization header required'})
        }
        mock_extract.return_value = (None, None, auth_error)
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'voornaam': 'Updated Name'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 401
        assert 'Authorization header required' in result['body']
    
    @patch('app.extract_user_roles_from_jwt')
    @patch('app.validate_field_permissions')
    @patch('app.table')
    def test_lambda_handler_permission_error(self, mock_table, mock_validate, mock_extract):
        """Test lambda handler with permission error"""
        # Mock JWT extraction success
        mock_extract.return_value = ('test@example.com', ['hdcnLeden'], None)
        
        # Mock DynamoDB get_item for member record (needed for status validation)
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'status': 'pending'
            }
        }
        
        # Mock field validation error
        permission_error = {
            'statusCode': 403,
            'headers': {},
            'body': json.dumps({'error': 'Access denied'})
        }
        mock_validate.return_value = (False, permission_error, ['status'])
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'status': 'active'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 403
        assert 'Access denied' in result['body']
    
    def test_lambda_handler_options_request(self):
        """Test lambda handler handles OPTIONS request for CORS"""
        event = {
            'httpMethod': 'OPTIONS'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert result['body'] == ''

    # Additional tests for different role combinations
    @patch('app.table')
    def test_validate_field_permissions_multiple_roles_combined(self, mock_table):
        """Test validation with user having multiple roles with combined permissions"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        # User with both basic member and read-all permissions
        user_roles = ['hdcnLeden', 'Members_Read_All']
        user_email = 'test@example.com'
        member_id = 'test-123'
        fields_to_update = {'voornaam': 'Updated Name', 'telefoon': '123456789'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_regional_role_own_record(self, mock_table):
        """Test validation with regional role editing own record"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'regional-123',
                'email': 'regional@example.com',
                'voornaam': 'Regional'
            }
        }
        
        # Regional secretary role (has read permissions but not full CRUD)
        user_roles = ['hdcnLeden', 'Members_Read_Region1']
        user_email = 'regional@example.com'
        member_id = 'regional-123'
        fields_to_update = {'voornaam': 'Updated Name', 'telefoon': '123456789'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_mixed_valid_invalid_fields(self, mock_table):
        """Test validation with mix of valid and invalid fields"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'
        member_id = 'test-123'
        # Mix of personal (allowed) and administrative (forbidden) fields
        fields_to_update = {
            'voornaam': 'Updated Name',  # Personal field - allowed
            'telefoon': '123456789',     # Personal field - allowed
            'status': 'active',          # Administrative field - forbidden
            'lidnummer': '12345'         # Administrative field - forbidden
        }
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'status' in forbidden_fields
        assert 'lidnummer' in forbidden_fields
        assert len(forbidden_fields) == 2

    @patch('app.table')
    def test_validate_field_permissions_webmaster_role_all_access(self, mock_table):
        """Test validation with webmaster role having full access"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'other-123',
                'email': 'other@example.com',
                'voornaam': 'Other'
            }
        }
        
        # Webmaster should have full access to all fields
        user_roles = ['Members_CRUD_All', 'System_CRUD_All']
        user_email = 'webmaster@example.com'
        member_id = 'other-123'
        fields_to_update = {
            'voornaam': 'Updated Name',
            'status': 'active',
            'lidnummer': '12345',
            'regio': '1'
        }
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_motorcycle_fields_own_record(self, mock_table):
        """Test validation for motorcycle fields on own record"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'biker-123',
                'email': 'biker@example.com',
                'voornaam': 'Biker'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'biker@example.com'
        member_id = 'biker-123'
        fields_to_update = {
            'motormerk': 'Harley-Davidson',
            'motortype': 'Street Glide',
            'kenteken': 'ABC-123',
            'bouwjaar': '2020'
        }
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_motorcycle_fields_other_record_denied(self, mock_table):
        """Test validation denies motorcycle fields on other user's record"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'other-123',
                'email': 'other@example.com',
                'voornaam': 'Other'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'user@example.com'  # Different from record email
        member_id = 'other-123'
        fields_to_update = {
            'motormerk': 'Harley-Davidson',
            'motortype': 'Street Glide'
        }
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'motormerk' in forbidden_fields
        assert 'motortype' in forbidden_fields

    @patch('app.table')
    def test_validate_field_permissions_status_field_special_handling(self, mock_table):
        """Test that status field requires special Members_CRUD_All permission"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        # Test with Members_Read_All (should not allow status changes)
        user_roles = ['Members_Read_All']
        user_email = 'admin@example.com'
        member_id = 'test-123'
        fields_to_update = {'status': 'active'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is False
        assert error is not None
        assert 'status' in forbidden_fields
        
        # Test with Members_CRUD_All (should allow status changes)
        user_roles = ['Members_CRUD_All']
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_case_insensitive_email_matching(self, mock_table):
        """Test that email matching is case insensitive for own record detection"""
        # Mock DynamoDB response with lowercase email
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'TEST@EXAMPLE.COM'  # Uppercase version
        member_id = 'test-123'
        fields_to_update = {'voornaam': 'Updated Name'}
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('app.table')
    def test_validate_field_permissions_empty_fields_update(self, mock_table):
        """Test validation with empty fields update"""
        # Mock DynamoDB response
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'test@example.com',
                'voornaam': 'Test'
            }
        }
        
        user_roles = ['hdcnLeden']
        user_email = 'test@example.com'
        member_id = 'test-123'
        fields_to_update = {}  # Empty update
        
        is_valid, error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, fields_to_update
        )
        
        assert is_valid is True
        assert error is None
        assert forbidden_fields == []

    @patch('builtins.print')
    def test_log_field_permission_denial_own_record(self, mock_print):
        """Test logging for field permission denial on own record"""
        log_field_permission_denial(
            user_email='test@example.com',
            user_roles=['hdcnLeden'],
            member_id='test-123',
            forbidden_fields=['status'],
            field_categories={'administrative': ['status']},
            is_own_record=True,
            member_email='test@example.com'
        )
        
        # Check that logging was called
        assert mock_print.call_count == 2
        
        # Check structured log entry
        structured_log_call = mock_print.call_args_list[0][0][0]
        assert 'SECURITY_AUDIT:' in structured_log_call
        assert 'FIELD_PERMISSION_DENIED' in structured_log_call
        assert 'WARNING' in structured_log_call  # Own record should be WARNING severity
        
        # Check human-readable log
        readable_log_call = mock_print.call_args_list[1][0][0]
        assert 'Field permission denied' in readable_log_call
        assert 'test@example.com' in readable_log_call
        assert 'own record' in readable_log_call

    @patch('builtins.print')
    def test_log_field_permission_denial_other_record(self, mock_print):
        """Test logging for field permission denial on other user's record"""
        log_field_permission_denial(
            user_email='user@example.com',
            user_roles=['hdcnLeden'],
            member_id='other-123',
            forbidden_fields=['voornaam'],
            field_categories={'personal': ['voornaam']},
            is_own_record=False,
            member_email='other@example.com'
        )
        
        # Check that logging was called
        assert mock_print.call_count == 2
        
        # Check structured log entry
        structured_log_call = mock_print.call_args_list[0][0][0]
        assert 'SECURITY_AUDIT:' in structured_log_call
        assert 'HIGH' in structured_log_call  # Other record should be HIGH severity
        
        # Check human-readable log
        readable_log_call = mock_print.call_args_list[1][0][0]
        assert 'another user\'s record (other@example.com)' in readable_log_call

    @patch('builtins.print')
    def test_log_successful_field_update(self, mock_print):
        """Test logging for successful field updates"""
        log_successful_field_update(
            user_email='test@example.com',
            user_roles=['hdcnLeden'],
            member_id='test-123',
            updated_fields=['voornaam', 'telefoon'],
            field_values={'voornaam': 'New Name', 'telefoon': '123456789'},
            member_email='test@example.com'
        )
        
        # Check that logging was called (should be at least 1 call for AUDIT_LOG)
        assert mock_print.call_count >= 1
        
        # Check structured log entry
        log_call = mock_print.call_args_list[0][0][0]
        assert 'AUDIT_LOG:' in log_call
        assert 'FIELD_UPDATE_SUCCESS' in log_call
        assert 'test@example.com' in log_call
        assert 'field_count' in log_call

    @patch('builtins.print')
    def test_log_administrative_field_changes(self, mock_print):
        """Test enhanced logging for administrative field changes"""
        from app import log_administrative_field_changes
        
        # Test with non-critical administrative fields
        log_administrative_field_changes(
            user_email='admin@example.com',
            user_roles=['Members_CRUD_All'],
            member_id='test-123',
            member_email='member@example.com',
            admin_fields=['created_at', 'updated_at'],  # Non-critical admin fields
            field_values={'created_at': '2023-01-01', 'updated_at': '2023-12-26'}
        )
        
        # Check that logging was called multiple times
        assert mock_print.call_count >= 2
        
        # Check structured admin audit log
        admin_log_call = None
        readable_log_call = None
        
        for call in mock_print.call_args_list:
            call_text = call[0][0]
            if 'ADMIN_AUDIT:' in call_text:
                admin_log_call = call_text
            elif 'ADMINISTRATIVE CHANGE:' in call_text:
                readable_log_call = call_text
        
        assert admin_log_call is not None
        assert 'ADMINISTRATIVE_FIELD_UPDATE' in admin_log_call
        assert 'HIGH' in admin_log_call  # Non-critical fields should be HIGH severity
        
        assert readable_log_call is not None
        assert 'admin@example.com' in readable_log_call
        assert 'Members_CRUD_All' in readable_log_call

    @patch('builtins.print')
    def test_log_critical_administrative_changes(self, mock_print):
        """Test logging for critical administrative field changes"""
        from app import log_administrative_field_changes
        
        log_administrative_field_changes(
            user_email='admin@example.com',
            user_roles=['Members_CRUD_All'],
            member_id='test-123',
            member_email='member@example.com',
            admin_fields=['status', 'lidnummer'],  # Critical fields
            field_values={'status': 'suspended', 'lidnummer': '99999'}
        )
        
        # Check that logging was called multiple times
        assert mock_print.call_count >= 3  # Admin audit + readable + critical warning
        
        # Check for critical change warning
        critical_log_found = False
        for call in mock_print.call_args_list:
            call_text = call[0][0]
            if 'CRITICAL ADMINISTRATIVE CHANGE:' in call_text:
                critical_log_found = True
                assert 'immediate review recommended' in call_text
                break
        
        assert critical_log_found, "Critical administrative change warning not found"

    # Status field specific tests
    @patch('app.table')
    def test_validate_status_change_success_with_members_crud_all(self, mock_table):
        """Test successful status change validation with Members_CRUD_All role"""
        from app import validate_status_change
        
        user_roles = ['Members_CRUD_All']
        user_email = 'admin@example.com'
        member_id = 'test-123'
        new_status = 'active'
        current_status = 'pending'
        
        is_valid, error, validation_details = validate_status_change(
            user_roles, user_email, member_id, new_status, current_status
        )
        
        assert is_valid is True
        assert error is None
        assert validation_details['validation_result'] == 'APPROVED'
        assert validation_details['new_status'] == 'active'
        assert validation_details['current_status'] == 'pending'

    @patch('app.table')
    def test_validate_status_change_denied_insufficient_role(self, mock_table):
        """Test status change validation denied for insufficient role"""
        from app import validate_status_change
        
        user_roles = ['hdcnLeden', 'Members_Read_All']  # No Members_CRUD_All
        user_email = 'user@example.com'
        member_id = 'test-123'
        new_status = 'active'
        current_status = 'pending'
        
        is_valid, error, validation_details = validate_status_change(
            user_roles, user_email, member_id, new_status, current_status
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 403
        assert 'Members_CRUD_All role' in error['body']
        assert validation_details['validation_result'] == 'DENIED'
        assert validation_details['reason'] == 'Missing Members_CRUD_All role'

    @patch('app.table')
    def test_validate_status_change_invalid_status_value(self, mock_table):
        """Test status change validation with invalid status value"""
        from app import validate_status_change
        
        user_roles = ['Members_CRUD_All']
        user_email = 'admin@example.com'
        member_id = 'test-123'
        new_status = 'invalid_status'  # Invalid status
        current_status = 'active'
        
        is_valid, error, validation_details = validate_status_change(
            user_roles, user_email, member_id, new_status, current_status
        )
        
        assert is_valid is False
        assert error is not None
        assert error['statusCode'] == 400
        assert 'Invalid status value' in error['body']
        assert validation_details['validation_result'] == 'DENIED'
        assert 'Invalid status value' in validation_details['reason']

    @patch('builtins.print')
    def test_log_status_change_denial(self, mock_print):
        """Test logging for status change denials"""
        from app import log_status_change_denial
        
        log_status_change_denial(
            user_email='user@example.com',
            user_roles=['hdcnLeden'],
            member_id='test-123',
            attempted_status='active',
            current_status='pending',
            reason='Insufficient role permissions'
        )
        
        # Check that logging was called
        assert mock_print.call_count == 2
        
        # Check structured log entry
        structured_log_call = mock_print.call_args_list[0][0][0]
        assert 'STATUS_SECURITY_AUDIT:' in structured_log_call
        assert 'STATUS_CHANGE_DENIED' in structured_log_call
        assert 'HIGH' in structured_log_call
        
        # Check human-readable log
        readable_log_call = mock_print.call_args_list[1][0][0]
        assert 'STATUS CHANGE DENIED' in readable_log_call
        assert 'user@example.com' in readable_log_call
        assert 'active' in readable_log_call

    @patch('builtins.print')
    def test_log_status_change_success(self, mock_print):
        """Test logging for successful status changes"""
        from app import log_status_change_success
        
        log_status_change_success(
            user_email='admin@example.com',
            user_roles=['Members_CRUD_All'],
            member_id='test-123',
            member_email='member@example.com',
            old_status='pending',
            new_status='active'
        )
        
        # Check that logging was called
        assert mock_print.call_count >= 2
        
        # Check structured log entry
        structured_log_found = False
        readable_log_found = False
        
        for call in mock_print.call_args_list:
            call_text = call[0][0]
            if 'STATUS_CHANGE_AUDIT:' in call_text:
                structured_log_found = True
                assert 'STATUS_CHANGE_SUCCESS' in call_text
                assert 'CRITICAL' in call_text
            elif 'STATUS CHANGE SUCCESS:' in call_text:
                readable_log_found = True
                assert 'admin@example.com' in call_text
                assert 'pending' in call_text
                assert 'active' in call_text
        
        assert structured_log_found, "Structured status change log not found"
        assert readable_log_found, "Readable status change log not found"

    @patch('builtins.print')
    def test_log_critical_status_change(self, mock_print):
        """Test logging for critical status changes (suspended, inactive, etc.)"""
        from app import log_status_change_success
        
        log_status_change_success(
            user_email='admin@example.com',
            user_roles=['Members_CRUD_All'],
            member_id='test-123',
            member_email='member@example.com',
            old_status='active',
            new_status='suspended'  # Critical status
        )
        
        # Check for critical status change warning
        critical_log_found = False
        for call in mock_print.call_args_list:
            call_text = call[0][0]
            if 'CRITICAL STATUS CHANGE:' in call_text:
                critical_log_found = True
                assert 'suspended' in call_text
                assert 'immediate review recommended' in call_text
                break
        
        assert critical_log_found, "Critical status change warning not found"

    def test_determine_status_change_type(self):
        """Test status change type determination"""
        from app import determine_status_change_type
        
        # Test approval
        assert determine_status_change_type('pending', 'approved') == 'approval'
        assert determine_status_change_type('new_applicant', 'approved') == 'approval'
        
        # Test rejection
        assert determine_status_change_type('pending', 'rejected') == 'rejection'
        assert determine_status_change_type('new_applicant', 'rejected') == 'rejection'
        
        # Test deactivation
        assert determine_status_change_type('active', 'suspended') == 'deactivation'
        assert determine_status_change_type('active', 'inactive') == 'deactivation'
        
        # Test reactivation
        assert determine_status_change_type('suspended', 'active') == 'reactivation'
        assert determine_status_change_type('inactive', 'approved') == 'reactivation'
        
        # Test initial status set
        assert determine_status_change_type(None, 'active') == 'initial_status_set'
        assert determine_status_change_type('', 'pending') == 'initial_status_set'
        
        # Test general status update
        assert determine_status_change_type('active', 'pending') == 'status_update'

    @patch('app.extract_user_roles_from_jwt')
    @patch('app.table')
    def test_lambda_handler_status_change_success(self, mock_table, mock_extract):
        """Test lambda handler with successful status change"""
        # Mock JWT extraction
        mock_extract.return_value = ('admin@example.com', ['Members_CRUD_All'], None)
        
        # Mock DynamoDB get_item for member record
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'member@example.com',
                'status': 'pending',
                'voornaam': 'Test'
            }
        }
        
        # Mock DynamoDB update
        mock_table.update_item.return_value = {}
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'status': 'active'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        assert 'Member updated successfully' in result['body']

    @patch('app.extract_user_roles_from_jwt')
    @patch('app.table')
    def test_lambda_handler_status_change_denied_insufficient_role(self, mock_table, mock_extract):
        """Test lambda handler with status change denied due to insufficient role"""
        # Mock JWT extraction with insufficient role
        mock_extract.return_value = ('user@example.com', ['hdcnLeden'], None)
        
        # Mock DynamoDB get_item for member record
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'member@example.com',
                'status': 'pending',
                'voornaam': 'Test'
            }
        }
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'status': 'active'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 403
        assert 'Members_CRUD_All role' in result['body']

    @patch('app.extract_user_roles_from_jwt')
    @patch('app.table')
    def test_lambda_handler_status_change_invalid_value(self, mock_table, mock_extract):
        """Test lambda handler with invalid status value"""
        # Mock JWT extraction with sufficient role
        mock_extract.return_value = ('admin@example.com', ['Members_CRUD_All'], None)
        
        # Mock DynamoDB get_item for member record
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'member@example.com',
                'status': 'active',
                'voornaam': 'Test'
            }
        }
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({'status': 'invalid_status'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        assert 'Invalid status value' in result['body']

    @patch('app.extract_user_roles_from_jwt')
    @patch('app.table')
    def test_lambda_handler_mixed_fields_with_status(self, mock_table, mock_extract):
        """Test lambda handler with mixed fields including status"""
        # Mock JWT extraction with sufficient role
        mock_extract.return_value = ('admin@example.com', ['Members_CRUD_All'], None)
        
        # Mock DynamoDB get_item for member record
        mock_table.get_item.return_value = {
            'Item': {
                'member_id': 'test-123',
                'email': 'member@example.com',
                'status': 'pending',
                'voornaam': 'Test'
            }
        }
        
        # Mock DynamoDB update
        mock_table.update_item.return_value = {}
        
        event = {
            'httpMethod': 'PUT',
            'pathParameters': {'id': 'test-123'},
            'body': json.dumps({
                'voornaam': 'Updated Name',
                'status': 'active',
                'telefoon': '123456789'
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        assert 'Member updated successfully' in result['body']