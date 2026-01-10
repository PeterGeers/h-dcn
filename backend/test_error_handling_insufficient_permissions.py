#!/usr/bin/env python3
"""
Test Error Handling for Insufficient Permissions

This test validates that the authentication system provides proper error messages
when users have insufficient permissions for various operations.

Test Categories:
1. Missing Authorization Headers
2. Invalid JWT Tokens
3. Missing Permission Roles
4. Missing Region Roles
5. Insufficient Permission Levels
6. Regional Access Violations
7. Invalid Role Combinations
8. Edge Cases and Error Scenarios

Author: H-DCN Role Migration Team
Date: 2026-01-09
"""

import sys
import os
import json
import base64
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'shared'))

from auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    validate_permissions,
    create_error_response,
    cors_headers,
    log_permission_denial
)


class InsufficientPermissionsErrorTester:
    """Test error handling for insufficient permissions scenarios"""
    
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_test_result(self, test_name, passed, details=""):
        """Log test result"""
        if passed:
            self.test_results['passed'] += 1
            print(f"✅ {test_name}")
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {details}")
            print(f"❌ {test_name}: {details}")
    
    def create_mock_jwt_token(self, email, groups):
        """Create a mock JWT token for testing"""
        payload = {
            'email': email,
            'cognito:groups': groups,
            'exp': 9999999999  # Far future expiration
        }
        
        # Create a simple base64 encoded payload (not a real JWT, but sufficient for testing)
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
        
        # Simple mock JWT format: header.payload.signature
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload_b64}.mock_signature"
    
    def test_missing_authorization_header(self):
        """Test 1: Missing Authorization Header"""
        print("\n=== Test 1: Missing Authorization Header ===")
        
        # Event without authorization header
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        user_email, user_roles, error_response = extract_user_credentials(event)
        
        # Should return error
        self.log_test_result(
            "Missing auth header returns None credentials",
            user_email is None and user_roles is None,
            f"Expected None credentials, got email={user_email}, roles={user_roles}"
        )
        
        self.log_test_result(
            "Missing auth header returns 401 error",
            error_response is not None and error_response['statusCode'] == 401,
            f"Expected 401 error, got 