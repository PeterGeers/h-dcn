"""
Unit Tests for get_presmeet_booking Lambda Handler

Tests the get_presmeet_booking handler:
- Authentication and authorization flows
- Club-based access control (v2: Regio_Pressmeet + Member record club_id)
- Admin override via query parameter
- 404 when no booking exists
- 403 for missing club assignment or missing Regio_Pressmeet role
- Tenant filter in DynamoDB scan

Requirements: 1.3, 1.4, 2.1, 6.4, 11.4, 11.5
"""

import json
import pytest
import base64
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

# Clear any previously cached `shared` module that might not include club_identity
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env var before importing
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')

# Use package-style import to avoid polluting the bare 'app' module cache
import handler.get_presmeet_booking.app as app
from handler.get_presmeet_booking.app import lambda_handler


def create_jwt_token(email="club@fhd.nl", groups=None):
    """Helper to create JWT tokens for testing."""
    if groups is None:
        groups = ["hdcnLeden", "Regio_Pressmeet"]

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

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_no_regio_pressmeet_returns_403(self, mock_table, mock_get_club_id):
        """User without Regio_Pressmeet role returns 403 'PresMeet access required'."""
        token = create_jwt_token(groups=["hdcnLeden"])  # No Regio_Pressmeet
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'PresMeet access required' in body.get('error', '')
        mock_table.scan.assert_not_called()

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_no_club_id_returns_403(self, mock_table, mock_get_club_id):
        """User with Regio_Pressmeet but no club_id on Member record returns 403."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Missing club assignment' in body.get('error', '')
        mock_table.scan.assert_not_called()


class TestGetPresMeetBookingAccess:
    """Test club-based access control."""

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='amsterdam')
    @patch.object(app, 'orders_table')
    def test_returns_booking_for_matching_club(self, mock_table, mock_get_club_id):
        """Club user gets their own booking via Member record club_id."""
        booking = {
            'order_id': 'order-123',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [{'product_type': 'meeting_ticket', 'attributes': {'name': 'Jan', 'role': 'President'}}],
            'total_amount': '50.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-123'
        assert body['club_id'] == 'amsterdam'

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='amsterdam')
    @patch.object(app, 'orders_table')
    def test_returns_404_when_no_booking_exists(self, mock_table, mock_get_club_id):
        """Returns 404 when no presmeet booking exists for the club."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Booking not found' in body.get('error', '')

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='amsterdam')
    @patch.object(app, 'orders_table')
    def test_non_admin_cannot_use_club_id_param(self, mock_table, mock_get_club_id):
        """Non-admin user providing club_id param still queries their own club."""
        booking = {
            'order_id': 'order-own',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        # User has Regio_Pressmeet but not admin roles, tries to pass club_id=rotterdam
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'club_id': 'rotterdam'})
        response = lambda_handler(event, None)

        # Should use user's own club_id (amsterdam), not the query param
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'amsterdam'


class TestGetPresMeetBookingAdmin:
    """Test admin access patterns (v2: is_presmeet_admin check)."""

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_admin_can_view_any_club_booking(self, mock_table, mock_get_club_id):
        """Admin with club_id query parameter can view any club's booking."""
        booking = {
            'order_id': 'order-789',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'rotterdam',
            'status': 'submitted',
            'items': [{'product_type': 'meeting_ticket', 'attributes': {'name': 'Piet', 'role': 'VP'}}],
            'total_amount': '50.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        # v2 admin: Products_CRUD + Regio_Pressmeet
        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "Products_CRUD", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'club_id': 'rotterdam'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-789'
        assert body['club_id'] == 'rotterdam'

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_admin_without_club_id_param_and_no_member_record_returns_403(self, mock_table, mock_get_club_id):
        """Admin without query param and no Member record club_id returns 403."""
        # v2 admin: Products_CRUD + Regio_Pressmeet
        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "Products_CRUD", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Missing club assignment' in body.get('error', '')

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='utrecht')
    @patch.object(app, 'orders_table')
    def test_admin_with_own_club_gets_own_booking(self, mock_table, mock_get_club_id):
        """Admin who has a club_id on their Member record gets their own booking by default."""
        booking = {
            'order_id': 'order-admin',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'utrecht',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        # v2 admin: Products_CRUD + Regio_Pressmeet
        token = create_jwt_token(email="admin@h-dcn.nl", groups=["hdcnLeden", "Products_CRUD", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'utrecht'

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_products_read_admin_can_view_any_club(self, mock_table, mock_get_club_id):
        """Products_Read + Regio_Pressmeet is also admin (read access)."""
        booking = {
            'order_id': 'order-wm',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'eindhoven',
            'status': 'locked',
            'items': [],
            'total_amount': '100.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(email="reader@h-dcn.nl", groups=["hdcnLeden", "Products_Read", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'club_id': 'eindhoven'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'eindhoven'

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value=None)
    @patch.object(app, 'orders_table')
    def test_regio_all_with_management_role_is_admin(self, mock_table, mock_get_club_id):
        """Regio_All + Webshop_Management is also admin."""
        booking = {
            'order_id': 'order-ra',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'groningen',
            'status': 'submitted',
            'items': [],
            'total_amount': '75.00',
        }
        mock_table.scan.return_value = {'Items': [booking]}

        token = create_jwt_token(email="mgmt@h-dcn.nl", groups=["hdcnLeden", "Webshop_Management", "Regio_All"])
        event = make_event(token=token, query_params={'club_id': 'groningen'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'groningen'


class TestGetPresMeetBookingPagination:
    """Test DynamoDB pagination handling."""

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='amsterdam')
    @patch.object(app, 'orders_table')
    def test_handles_paginated_results(self, mock_table, mock_get_club_id):
        """Handler correctly handles DynamoDB pagination."""
        booking = {
            'order_id': 'order-page',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
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

        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token)
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'order-page'
        assert mock_table.scan.call_count == 2


class TestGetPresMeetBookingMultipleOrders:
    """Test behavior when multiple bookings exist."""

    @patch('handler.get_presmeet_booking.app.get_club_id', return_value='amsterdam')
    @patch.object(app, 'orders_table')
    def test_returns_first_booking_from_scan(self, mock_table, mock_get_club_id):
        """When multiple bookings exist, returns the first from scan results."""
        booking_a = {
            'order_id': 'order-a',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'amsterdam',
            'status': 'draft',
            'items': [],
            'total_amount': '0.00',
            'updated_at': '2024-01-01T10:00:00Z',
        }
        booking_b = {
            'order_id': 'order-b',
            'source': 'presmeet',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'amsterdam',
            'status': 'submitted',
            'items': [{'product_type': 'meeting_ticket'}],
            'total_amount': '50.00',
            'updated_at': '2025-06-01T12:00:00Z',
        }
        mock_table.scan.return_value = {'Items': [booking_a, booking_b]}

        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
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
