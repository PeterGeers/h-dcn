import json
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the handler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handler/hdcn_cognito_admin'))

from app import lambda_handler, calculate_user_permissions


@pytest.fixture
def mock_cognito_client():
    """Mock Cognito client for testing"""
    with patch('app.cognito_client') as mock_client:
        yield mock_client


@pytest.fixture
def auth_headers():
    """Sample authorization headers for testing"""
    return {
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InRlc3RAdGVzdC5jb20iLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJjb2duaXRvOmdyb3VwcyI6WyJoZGNuTGVkZW4iXX0.test'
    }


@pytest.fixture
def api_event():
    """Base API Gateway event structure"""
    return {
        'httpMethod': 'GET',
        'path': '/auth/login',
        'headers': {},
        'body': None,
        'queryStringParameters': None,
        'pathParameters': None
    }


class TestCalculateUserPermissions:
    """Test the calculate_user_permissions function"""
    
    def test_basic_member_permissions(self):
        """Test permissions for basic member role"""
        roles = ['hdcnLeden']
        permissions = calculate_user_permissions(roles)
        
        expected_permissions = [
            'events:read_public',
            'members:read_own',
            'members:update_own_motorcycle',
            'members:update_own_personal',
            'products:browse_catalog',
            'webshop:access'
        ]
        
        assert permissions == expected_permissions
    
    def test_admin_permissions(self):
        """Test permissions for admin roles"""
        roles = ['Members_CRUD_All', 'System_User_Management']
        permissions = calculate_user_permissions(roles)
        
        # Should include both member management and system permissions
        assert 'members:read_all' in permissions
        assert 'members:create' in permissions
        assert 'members:update_all' in permissions
        assert 'members:delete' in permissions
        assert 'system:user_management' in permissions
        assert 'cognito:admin_access' in permissions
    
    def test_multiple_roles_combine_permissions(self):
        """Test that multiple roles combine permissions correctly"""
        roles = ['hdcnLeden', 'Events_Read_All']
        permissions = calculate_user_permissions(roles)
        
        # Should include permissions from both roles
        assert 'members:read_own' in permissions  # from hdcnLeden
        assert 'events:read_all' in permissions   # from Events_Read_All
        assert 'events:export_all' in permissions # from Events_Read_All
    
    def test_empty_roles(self):
        """Test with no roles assigned"""
        roles = []
        permissions = calculate_user_permissions(roles)
        
        assert permissions == []
    
    def test_unknown_role(self):
        """Test with unknown role"""
        roles = ['UnknownRole']
        permissions = calculate_user_permissions(roles)
        
        assert permissions == []


class TestAuthEndpoints:
    """Test the authentication endpoints"""
    
    def test_get_auth_login_missing_authorization(self, api_event, mock_cognito_client):
        """Test GET /auth/login without authorization header"""
        event = api_event.copy()
        event['path'] = '/auth/login'
        event['httpMethod'] = 'GET'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Authorization header required' in body['error']
    
    def test_get_auth_permissions_missing_authorization(self, api_event, mock_cognito_client):
        """Test GET /auth/permissions without authorization header"""
        event = api_event.copy()
        event['path'] = '/auth/permissions'
        event['httpMethod'] = 'GET'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Authorization header required' in body['error']
    
    def test_get_user_roles_missing_authorization(self, api_event, mock_cognito_client):
        """Test GET /auth/users/{user_id}/roles without authorization header"""
        event = api_event.copy()
        event['path'] = '/auth/users/test@test.com/roles'
        event['httpMethod'] = 'GET'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Authorization header required' in body['error']
    
    def test_assign_user_roles_missing_authorization(self, api_event, mock_cognito_client):
        """Test POST /auth/users/{user_id}/roles without authorization header"""
        event = api_event.copy()
        event['path'] = '/auth/users/test@test.com/roles'
        event['httpMethod'] = 'POST'
        event['body'] = json.dumps({'roles': ['hdcnLeden']})
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Authorization header required' in body['error']
    
    def test_remove_user_role_missing_authorization(self, api_event, mock_cognito_client):
        """Test DELETE /auth/users/{user_id}/roles/{role} without authorization header"""
        event = api_event.copy()
        event['path'] = '/auth/users/test@test.com/roles/hdcnLeden'
        event['httpMethod'] = 'DELETE'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Authorization header required' in body['error']
    
    def test_invalid_endpoint(self, api_event, mock_cognito_client):
        """Test invalid endpoint returns 404"""
        event = api_event.copy()
        event['path'] = '/auth/invalid'
        event['httpMethod'] = 'GET'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Endpoint not found' in body['error']
    
    def test_cors_headers_present(self, api_event, mock_cognito_client):
        """Test that CORS headers are present in responses"""
        event = api_event.copy()
        event['path'] = '/auth/login'
        event['httpMethod'] = 'GET'
        
        response = lambda_handler(event, {})
        
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers
        assert headers['Access-Control-Allow-Origin'] == '*'
    
    def test_options_request(self, api_event, mock_cognito_client):
        """Test OPTIONS request for CORS preflight"""
        event = api_event.copy()
        event['path'] = '/auth/login'
        event['httpMethod'] = 'OPTIONS'
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers


if __name__ == '__main__':
    pytest.main([__file__])