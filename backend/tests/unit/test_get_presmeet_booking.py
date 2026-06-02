"""
Unit Tests for get_presmeet_booking Lambda Handler

Tests the get_presmeet_booking handler:
- Authentication and authorization flows
- Club-based access control
- Admin override via query parameter
- 404 when no booking exists
- 403 for club mismatch and missing club assignment

Requirements: 3.1–3.8, 9.1–9.6
"""

import json
import pytest
import base64
import importlib
from unittest.mock import patch, MagicMock
import sys
import os


# Ensure the layers path and backend root are on sys.path for package-style imports
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear any previously cached `shared` module that might not include presmeet_validation
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env var before importing
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')

# Use package-style import to avoid polluting the bare 'app' module cache
import handler.get_presmeet_booking.app as app
from handler.get_presmeet_booking.app import lambda_handler


def create_jwt_token(email="club@fhd.nl", groups=None):
    """Helper to create JWT tokens for testing."""
    if groups is None:
        groups = ["hdcnLeden", "club_amsterdam"]

    payload = {
        "email": email,
        "cognito:groups": groups,
        "exp": 9999999999,
        "iat": 1000000000,
    }

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')
    signature = "test_signature"

    return f"{header}.{payload_encoded}.{signature}"


def make_event(token=None, query_params=None, method='GET'):
    """Helper to create an API Gateway event."""
    event = {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': query_params,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


class TestGetPresMeetBookingAuth:
    """Test authentication flows for get_presmeet_booking."""

    @patch.object(app, 'orders_table')
    def test_missing_auth_returns_401(self, mock_table):
        """Unauthenticated request returns 401."""
        event = make_event(token=None)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 401
        mock_table.scan.assert_not_called()

    @patch.object(app, 'orders_table')
    def test_no_club_group_returns_403(self, mock_table):
        """User without club group returns 403 'Missing club assignment'."""
        token = create_jwt_token(groups=["hdcnLeden"])  # No club_ group
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Missing club assignment' in body.get('error', '')
        mock_table.scan.assert_not_called()


class TestGetPresMeetBookingAccess:
    """Test club-based access control."""

    @patch.object(app, 'orders_table')
    def test_returns_booking_for_matching_club(self, mock_table):
        """Club user gets their own booking."""
        booking = {
            'order_id': 'order-123',
            'source': 'presmeet',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [{'product_type': 'meeting_ticket', 'attributes': {'name': 'Jan', 'role': 'President'}}],
            'total_amount': '50.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(groups=["hdcnLeden", "club_amsterdam"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-123'
        assert body['club_id'] == 'amsterdam'

    @patch.object(app, 'orders_table')
    def test_returns_404_when_no_booking_exists(self, mock_table):
        """Returns 404 when no presmeet booking exists for the club."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token(groups=["hdcnLeden", "club_amsterdam"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Booking not found' in body.get('error', '')

    @patch.object(app, 'orders_table')
    def test_non_admin_cannot_use_club_id_param(self, mock_table):
        """Non-admin user providing club_id param still queries their own club."""
        booking = {
            'order_id': 'order-own',
            'source': 'presmeet',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        # User is in club_amsterdam, tries to pass club_id=rotterdam
        token = create_jwt_token(groups=["hdcnLeden", "club_amsterdam"])
        event = make_event(token=token, query_params={'club_id': 'rotterdam'})
        response = lambda_handler(event, None)

        # Should use user's own club_id (amsterdam), not the query param
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'amsterdam'


class TestGetPresMeetBookingAdmin:
    """Test admin access patterns."""

    @patch.object(app, 'orders_table')
    def test_admin_can_view_any_club_booking(self, mock_table):
        """Admin with club_id query parameter can view any club's booking."""
        booking = {
            'order_id': 'order-789',
            'source': 'presmeet',
            'club_id': 'rotterdam',
            'status': 'submitted',
            'items': [{'product_type': 'meeting_ticket', 'attributes': {'name': 'Piet', 'role': 'VP'}}],
            'total_amount': '50.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "admin", "webmaster"])
        event = make_event(token=token, query_params={'club_id': 'rotterdam'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-789'
        assert body['club_id'] == 'rotterdam'

    @patch.object(app, 'orders_table')
    def test_admin_without_club_id_param_and_no_club_group_returns_403(self, mock_table):
        """Admin without club group and without query param returns 403 (missing club assignment)."""
        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "admin", "webmaster"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Missing club assignment' in body.get('error', '')

    @patch.object(app, 'orders_table')
    def test_admin_with_own_club_group_gets_own_booking(self, mock_table):
        """Admin who is also in a club group gets their own booking by default."""
        booking = {
            'order_id': 'order-admin',
            'source': 'presmeet',
            'club_id': 'utrecht',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "admin", "club_utrecht"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'utrecht'

    @patch.object(app, 'orders_table')
    def test_webmaster_can_view_any_club_booking(self, mock_table):
        """Webmaster role (without 'admin') can also view any club's booking."""
        booking = {
            'order_id': 'order-wm',
            'source': 'presmeet',
            'club_id': 'eindhoven',
            'status': 'locked',
            'items': [],
            'total_amount': '100.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(email="webmaster@h-dcn.nl", groups=["hdcnLeden", "webmaster"])
        event = make_event(token=token, query_params={'club_id': 'eindhoven'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'eindhoven'


class TestGetPresMeetBookingPagination:
    """Test DynamoDB pagination handling."""

    @patch.object(app, 'orders_table')
    def test_handles_paginated_results(self, mock_table):
        """Handler correctly handles DynamoDB pagination."""
        booking = {
            'order_id': 'order-page',
            'source': 'presmeet',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
        }

        # First call returns empty with pagination key, second returns booking
        mock_table.scan.side_effect = [
            {'Items': [], 'LastEvaluatedKey': {'order_id': 'some-key'}},
            {'Items': [booking]},
        ]

        token = create_jwt_token(groups=["hdcnLeden", "club_amsterdam"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-page'
        assert mock_table.scan.call_count == 2


class TestGetPresMeetBookingMultipleOrders:
    """Test behavior when multiple bookings exist."""

    @patch.object(app, 'orders_table')
    def test_returns_first_booking_from_scan(self, mock_table):
        """When multiple bookings exist, returns the first from scan results."""
        booking_a = {
            'order_id': 'order-a',
            'source': 'presmeet',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
            'updated_at': '2024-01-01T10:00:00Z',
        }
        booking_b = {
            'order_id': 'order-b',
            'source': 'presmeet',
            'club_id': 'amsterdam',
            'status': 'submitted',
            'items': [{'product_type': 'meeting_ticket'}],
            'total_amount': '50.00',
            'updated_at': '2025-06-01T12:00:00Z',
        }
        mock_table.scan.return_value = {'Items': [booking_a, booking_b]}

        token = create_jwt_token(groups=["hdcnLeden", "club_amsterdam"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-a'


class TestOptionsRequest:
    """Test CORS preflight handling."""

    @patch.object(app, 'orders_table')
    def test_options_returns_cors_headers(self, mock_table):
        """OPTIONS request returns CORS preflight response."""
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_table.scan.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
