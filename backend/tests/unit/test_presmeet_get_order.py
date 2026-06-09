"""
Unit Tests for presmeet_get_order Lambda Handler.

Tests the presmeet_get_order handler:
- Authentication and authorization flows
- Club-based access control (Regio_Pressmeet + Member record club_id)
- Admin override via query parameter
- Auto-creation of draft order when event is open and no order exists
- Rejection when event is not open and no order exists
- Returning existing order with all fields
- Conditional PutItem race condition handling
- Delegate access validation (primary/secondary)
- 403 for missing club assignment

Requirements: 1, 15
"""

import json
import pytest
import base64
from unittest.mock import patch, MagicMock
from decimal import Decimal
import sys
import os

# Ensure the layers path and backend root are on sys.path
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear any previously cached shared modules
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env vars before importing
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')

import handler.presmeet_get_order.app as app
from handler.presmeet_get_order.app import lambda_handler


def create_jwt_token(email="delegate@club.nl", groups=None):
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


class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_auth_header_returns_401(self):
        event = make_event(query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_no_presmeet_access_returns_403(self):
        """User without Regio_Pressmeet or Regio_All should be rejected."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'PresMeet access required' in body['error']


class TestMissingEventId:
    """Test missing event_id parameter."""

    def test_missing_event_id_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, query_params={})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'event_id' in body['error']

    def test_null_query_params_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, query_params=None)
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestMissingClubId:
    """Test user without club_id assignment."""

    @patch.object(app, 'get_club_id', return_value=None)
    def test_no_club_id_returns_403(self, mock_get_club):
        token = create_jwt_token()
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'club assignment' in body['error'].lower() or 'club' in body.get('details', '').lower()


class TestExistingOrder:
    """Test retrieving an existing order."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club')
    def test_returns_existing_order(self, mock_query, mock_club):
        existing_order = {
            'order_id': 'ord-1',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'delegate@club.nl', 'secondary': None},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'delegate@club.nl',
        }
        mock_query.return_value = existing_order

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'ord-1'
        assert body['version'] == 1
        assert body['delegates']['primary'] == 'delegate@club.nl'
        assert body['status'] == 'draft'

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club')
    def test_returns_order_with_items_and_version(self, mock_query, mock_club):
        existing_order = {
            'order_id': 'ord-2',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'partial',
            'total_amount': Decimal('150.00'),
            'total_paid': Decimal('50.00'),
            'items': [
                {
                    'product_id': 'prod-meeting',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Jan', 'role': 'President'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                }
            ],
            'delegates': {'primary': 'delegate@club.nl', 'secondary': 'piet@club.nl'},
            'version': 3,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-15T10:30:00+00:00',
            'created_by': 'delegate@club.nl',
        }
        mock_query.return_value = existing_order

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['version'] == 3
        assert body['total_amount'] == 150.0
        assert len(body['items']) == 1


class TestDelegateAccess:
    """Test delegate-based access validation."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club')
    def test_secondary_delegate_can_access(self, mock_query, mock_club):
        existing_order = {
            'order_id': 'ord-1',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'jan@club.nl', 'secondary': 'piet@club.nl'},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'jan@club.nl',
        }
        mock_query.return_value = existing_order

        token = create_jwt_token(email="piet@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club')
    def test_non_delegate_gets_403(self, mock_query, mock_club):
        existing_order = {
            'order_id': 'ord-1',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'jan@club.nl', 'secondary': 'piet@club.nl'},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'jan@club.nl',
        }
        mock_query.return_value = existing_order

        # User is not in delegates
        token = create_jwt_token(email="intruder@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'delegate' in body['error'].lower()

    @patch.object(app, 'is_presmeet_admin', return_value=True)
    @patch.object(app, '_query_order_by_event_and_club')
    def test_admin_can_access_any_order(self, mock_query, mock_admin):
        existing_order = {
            'order_id': 'ord-1',
            'club_id': 'club-456',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'someone@other.nl', 'secondary': None},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'someone@other.nl',
        }
        mock_query.return_value = existing_order

        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(token=token, query_params={'event_id': 'evt-1', 'club_id': 'club-456'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200


class TestAutoCreateDraftOrder:
    """Test auto-creation of draft order when event is open."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club', return_value=None)
    @patch.object(app, '_get_event')
    @patch.object(app, '_create_draft_order')
    def test_creates_draft_when_event_open(self, mock_create, mock_event, mock_query, mock_club):
        mock_event.return_value = {
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'status': 'open',
            'name': 'PresMeet 2027',
        }
        new_order = {
            'order_id': 'new-uuid',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'delegate@club.nl', 'secondary': None},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'delegate@club.nl',
        }
        mock_create.return_value = new_order

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['status'] == 'draft'
        assert body['version'] == 1
        assert body['delegates']['primary'] == 'delegate@club.nl'
        assert body['items'] == []
        mock_create.assert_called_once()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club', return_value=None)
    @patch.object(app, '_get_event')
    def test_rejects_when_event_closed(self, mock_event, mock_query, mock_club):
        mock_event.return_value = {
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'status': 'closed',
            'name': 'PresMeet 2027',
        }

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not active' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club', return_value=None)
    @patch.object(app, '_get_event')
    def test_rejects_when_event_draft(self, mock_event, mock_query, mock_club):
        mock_event.return_value = {
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'status': 'draft',
            'name': 'PresMeet 2027',
        }

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not active' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club', return_value=None)
    @patch.object(app, '_get_event', return_value=None)
    def test_returns_404_when_event_not_found(self, mock_event, mock_query, mock_club):
        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'nonexistent'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestRaceCondition:
    """Test conditional PutItem handling for duplicate prevention."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_query_order_by_event_and_club')
    @patch.object(app, '_get_event')
    @patch.object(app, '_create_draft_order', return_value=None)
    def test_race_condition_returns_existing_order(
        self, mock_create, mock_event, mock_query, mock_club
    ):
        """When create returns None (race condition), re-query should return the order."""
        # First call returns None (no order), second call returns the order
        existing_order = {
            'order_id': 'ord-existing',
            'club_id': 'club-123',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'delegate@club.nl', 'secondary': None},
            'version': 1,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-10T08:00:00+00:00',
            'created_by': 'delegate@club.nl',
        }
        mock_query.side_effect = [None, existing_order]
        mock_event.return_value = {
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'status': 'open',
        }

        token = create_jwt_token(email="delegate@club.nl")
        event = make_event(token=token, query_params={'event_id': 'evt-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'ord-existing'


class TestAdminAccess:
    """Test admin access patterns."""

    @patch.object(app, 'is_presmeet_admin', return_value=True)
    @patch.object(app, '_query_order_by_event_and_club')
    def test_admin_can_query_any_club_via_param(self, mock_query, mock_admin):
        existing_order = {
            'order_id': 'ord-1',
            'club_id': 'club-other',
            'event_id': 'evt-1',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('200.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'someone@club.nl', 'secondary': None},
            'version': 2,
            'status_history': [],
            'created_at': '2027-01-10T08:00:00+00:00',
            'updated_at': '2027-01-12T09:00:00+00:00',
            'created_by': 'someone@club.nl',
        }
        mock_query.return_value = existing_order

        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(token=token, query_params={'event_id': 'evt-1', 'club_id': 'club-other'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'club-other'
        # Verify club_id from query param was used
        mock_query.assert_called_with('evt-1', 'club-other')
