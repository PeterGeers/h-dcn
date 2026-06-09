"""
Unit Tests for presmeet_manage_delegates Lambda Handler.

Tests the delegate management endpoint:
- Authentication and authorization
- Only primary delegate (or admin) can manage secondary delegates
- Add secondary: validate email exists in Members + has Regio_Pressmeet/Regio_All
- Remove secondary: primary can remove at any time
- Error cases: missing body, invalid action, user not found, no presmeet access

Requirements: 12.6-12.10
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
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')
os.environ.setdefault('COGNITO_USER_POOL_ID', 'eu-west-1_test')

import handler.presmeet_manage_delegates.app as app
from handler.presmeet_manage_delegates.app import lambda_handler


def create_jwt_token(email="primary@club.nl", groups=None):
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


def make_event(token=None, body=None, order_id='ord-1', method='POST'):
    """Helper to create an API Gateway event."""
    event = {
        'httpMethod': method,
        'headers': {},
        'pathParameters': {'id': order_id} if order_id else {},
        'body': json.dumps(body) if body else None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


def make_order(primary='primary@club.nl', secondary=None, status='draft'):
    """Helper to create a test order record."""
    return {
        'order_id': 'ord-1',
        'club_id': 'club-123',
        'event_id': 'evt-1',
        'event_type': 'presmeet',
        'status': status,
        'payment_status': 'unpaid',
        'total_amount': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'items': [],
        'delegates': {'primary': primary, 'secondary': secondary},
        'version': 1,
        'status_history': [],
        'created_at': '2027-01-10T08:00:00+00:00',
        'updated_at': '2027-01-10T08:00:00+00:00',
        'created_by': primary,
    }


class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_auth_header_returns_401(self):
        event = make_event(body={'action': 'add', 'email': 'test@club.nl'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_no_presmeet_access_returns_403(self):
        """User without Regio_Pressmeet or Regio_All should be rejected."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, body={'action': 'add', 'email': 'test@club.nl'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Regio_Pressmeet' in body['error'] or 'Regio_All' in body['error']


class TestInputValidation:
    """Test request body validation."""

    def test_missing_order_id_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, body={'action': 'add', 'email': 'x@y.nl'}, order_id=None)
        # pathParameters will be {} so 'id' is missing
        event['pathParameters'] = {}
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'order' in body['error'].lower() or 'id' in body['error'].lower()

    def test_invalid_action_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, body={'action': 'invalid', 'email': 'x@y.nl'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'action' in body['error']

    def test_add_without_email_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, body={'action': 'add'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'email' in body['error'].lower()

    def test_invalid_json_returns_400(self):
        token = create_jwt_token()
        event = {
            'httpMethod': 'POST',
            'headers': {'Authorization': f'Bearer {token}'},
            'pathParameters': {'id': 'ord-1'},
            'body': 'not json {{{',
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'json' in body['error'].lower()


class TestOrderNotFound:
    """Test handling of non-existent orders."""

    @patch.object(app.orders_table, 'get_item', return_value={'Item': None})
    def test_order_not_found_returns_404(self, mock_get):
        mock_get.return_value = {}  # No 'Item' key
        token = create_jwt_token()
        event = make_event(token=token, body={'action': 'add', 'email': 'x@y.nl'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestAuthorizationPrimaryOnly:
    """Test that only primary delegate (or admin) can manage delegates."""

    @patch.object(app.orders_table, 'get_item')
    def test_secondary_delegate_cannot_manage(self, mock_get):
        """Secondary delegate should not be able to add/remove."""
        order = make_order(primary='primary@club.nl', secondary='secondary@club.nl')
        mock_get.return_value = {'Item': order}

        # Log in as secondary delegate
        token = create_jwt_token(email='secondary@club.nl')
        event = make_event(token=token, body={'action': 'remove'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'primary delegate' in body['error'].lower()

    @patch.object(app.orders_table, 'get_item')
    def test_unrelated_user_cannot_manage(self, mock_get):
        """User not on the order should not be able to manage delegates."""
        order = make_order(primary='primary@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='intruder@other.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'new@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=True)
    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_admin_can_manage_delegates(self, mock_update, mock_get, mock_groups, mock_member):
        """Admin can manage delegates even if not the primary."""
        order = make_order(primary='someone@club.nl')
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'someone@club.nl', 'secondary': 'new@club.nl'}
            }
        }

        token = create_jwt_token(
            email='admin@h-dcn.nl',
            groups=['Webshop_Management', 'Regio_Pressmeet']
        )
        event = make_event(token=token, body={'action': 'add', 'email': 'new@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['delegates']['secondary'] == 'new@club.nl'


class TestAddSecondaryDelegate:
    """Test adding a secondary delegate."""

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=True)
    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_add_secondary_success(self, mock_update, mock_get, mock_groups, mock_member):
        """Primary delegate can add a valid secondary delegate."""
        order = make_order(primary='primary@club.nl', secondary=None)
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'primary@club.nl', 'secondary': 'new@club.nl'}
            }
        }

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'new@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['delegates']['secondary'] == 'new@club.nl'
        assert 'added' in body['message'].lower()

    @patch.object(app.orders_table, 'get_item')
    def test_cannot_add_primary_as_secondary(self, mock_get):
        """Cannot set primary delegate as secondary."""
        order = make_order(primary='primary@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'primary@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'primary' in body['error'].lower()

    @patch.object(app.orders_table, 'get_item')
    def test_cannot_add_same_secondary_again(self, mock_get):
        """Cannot add the same secondary delegate twice."""
        order = make_order(primary='primary@club.nl', secondary='existing@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'existing@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'already' in body['error'].lower()

    @patch.object(app, '_member_exists', return_value=False)
    @patch.object(app.orders_table, 'get_item')
    def test_add_nonexistent_member_returns_404(self, mock_get, mock_member):
        """Cannot add a user who doesn't exist in the Members table."""
        order = make_order(primary='primary@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'ghost@nowhere.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=False)
    @patch.object(app.orders_table, 'get_item')
    def test_add_user_without_presmeet_access_returns_403(self, mock_get, mock_groups, mock_member):
        """Cannot add user who doesn't have Regio_Pressmeet or Regio_All."""
        order = make_order(primary='primary@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'nogroup@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'presmeet access' in body['error'].lower()

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=True)
    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_add_replaces_existing_secondary(self, mock_update, mock_get, mock_groups, mock_member):
        """Adding a new secondary when one exists should replace it."""
        order = make_order(primary='primary@club.nl', secondary='old@club.nl')
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'primary@club.nl', 'secondary': 'new@club.nl'}
            }
        }

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'new@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['delegates']['secondary'] == 'new@club.nl'


class TestRemoveSecondaryDelegate:
    """Test removing a secondary delegate."""

    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_remove_secondary_success(self, mock_update, mock_get):
        """Primary delegate can remove secondary at any time."""
        order = make_order(primary='primary@club.nl', secondary='secondary@club.nl')
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'primary@club.nl', 'secondary': None}
            }
        }

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'remove'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['delegates']['secondary'] is None
        assert 'removed' in body['message'].lower()

    @patch.object(app.orders_table, 'get_item')
    def test_remove_when_no_secondary_returns_400(self, mock_get):
        """Cannot remove secondary when none exists."""
        order = make_order(primary='primary@club.nl', secondary=None)
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'remove'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no secondary' in body['error'].lower()


class TestCaseInsensitiveEmails:
    """Test that email comparisons are case-insensitive."""

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=True)
    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_primary_check_case_insensitive(self, mock_update, mock_get, mock_groups, mock_member):
        """Primary delegate check should be case-insensitive."""
        order = make_order(primary='Primary@Club.NL', secondary=None)
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'Primary@Club.NL', 'secondary': 'new@club.nl'}
            }
        }

        # Login with different casing
        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'new@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    @patch.object(app.orders_table, 'get_item')
    def test_add_primary_case_insensitive_check(self, mock_get):
        """Cannot add primary as secondary even with different casing."""
        order = make_order(primary='primary@club.nl')
        mock_get.return_value = {'Item': order}

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'PRIMARY@CLUB.NL'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400


class TestMaxTwoDelegates:
    """Test that maximum 2 delegates per order is enforced (Req 12.9)."""

    @patch.object(app, '_member_exists', return_value=True)
    @patch.object(app, '_user_has_required_groups', return_value=True)
    @patch.object(app.orders_table, 'get_item')
    @patch.object(app.orders_table, 'update_item')
    def test_max_two_delegates_structure(self, mock_update, mock_get, mock_groups, mock_member):
        """Order delegates object stores exactly primary + optional secondary (max 2)."""
        order = make_order(primary='primary@club.nl', secondary=None)
        mock_get.return_value = {'Item': order}
        mock_update.return_value = {
            'Attributes': {
                'delegates': {'primary': 'primary@club.nl', 'secondary': 'second@club.nl'}
            }
        }

        token = create_jwt_token(email='primary@club.nl')
        event = make_event(token=token, body={'action': 'add', 'email': 'second@club.nl'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Structure enforces max 2: primary + secondary
        delegates = body['delegates']
        assert 'primary' in delegates
        assert 'secondary' in delegates
        # No third delegate field exists
        assert len([k for k in delegates.keys() if k not in ('primary', 'secondary')]) == 0

