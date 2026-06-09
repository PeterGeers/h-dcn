"""
Unit Tests for presmeet_upsert_order Lambda Handler

Tests the PUT /presmeet/orders/{id} endpoint:
- Authentication and authorization (Regio_Pressmeet/Regio_All required)
- Optimistic locking (version match, ConditionalCheckFailedException → 409)
- Version increment and updated_at on success
- No field validation on draft save (accept incomplete data)
- Reject locked order for delegates, allow for admin (Req 9.2)
- Revert submitted → draft on delegate edit (Req 2.6)
- Record admin edits in status_history (Req 9.2)
- Recalculate total_amount from items

Requirements: 2, 9.2
"""

import json
import os
import sys
import base64
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest

# Ensure the layers path and backend root are on sys.path
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python')
)
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear cached shared modules
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env vars before importing
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')

import handler.presmeet_upsert_order.app as app
from handler.presmeet_upsert_order.app import lambda_handler, _calculate_total_amount


# --- Test Helpers ---

def create_jwt_token(email="delegate@club.nl", groups=None):
    """Create a fake JWT token for testing."""
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


def make_event(token=None, order_id="order-123", body=None, method='PUT'):
    """Create an API Gateway event for PUT /presmeet/orders/{id}."""
    event = {
        'httpMethod': method,
        'headers': {},
        'pathParameters': {'id': order_id} if order_id else {},
        'body': json.dumps(body) if body else None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


def make_order(
    order_id="order-123",
    club_id="club-amsterdam",
    status="draft",
    version=1,
    primary="delegate@club.nl",
    secondary=None,
    items=None,
):
    """Create a sample order record."""
    order = {
        'order_id': order_id,
        'club_id': club_id,
        'event_id': 'event-pm2027',
        'event_type': 'presmeet',
        'channel': 'presmeet',
        'status': status,
        'version': version,
        'total_amount': Decimal('0'),
        'items': items or [],
        'delegates': {'primary': primary},
        'created_at': '2027-01-10T08:00:00Z',
        'updated_at': '2027-01-10T08:00:00Z',
    }
    if secondary:
        order['delegates']['secondary'] = secondary
    return order


# --- Test Classes ---

class TestOptionsRequest:
    """CORS preflight handling."""

    @patch.object(app, 'table')
    def test_options_returns_200(self, mock_table):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        mock_table.get_item.assert_not_called()


class TestAuthentication:
    """Authentication and access control."""

    @patch.object(app, 'table')
    def test_missing_auth_returns_401(self, mock_table):
        event = make_event(token=None, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    @patch.object(app, 'table')
    def test_no_presmeet_access_returns_403(self, mock_table):
        """User without Regio_Pressmeet or Regio_All gets 403."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Regio_Pressmeet' in body.get('error', '')

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value=None)
    @patch.object(app, 'table')
    def test_no_club_id_returns_403(self, mock_table, mock_get_club_id):
        """Non-admin user without club_id returns 403."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order()
        mock_table.get_item.return_value = {'Item': order}

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'club assignment' in body.get('error', '').lower()

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_wrong_club_returns_403(self, mock_table, mock_get_club_id):
        """Non-admin accessing order of a different club gets 403."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(club_id="club-rotterdam")
        mock_table.get_item.return_value = {'Item': order}

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'different club' in body.get('error', '')

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_non_delegate_returns_403(self, mock_table, mock_get_club_id):
        """User in same club but not a delegate on the order gets 403."""
        token = create_jwt_token(email="other@club.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(primary="delegate@club.nl")
        mock_table.get_item.return_value = {'Item': order}

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not a delegate' in body.get('error', '')

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_secondary_delegate_can_update(self, mock_table, mock_get_club_id):
        """Secondary delegate has edit access."""
        token = create_jwt_token(email="secondary@club.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(primary="delegate@club.nl", secondary="secondary@club.nl")
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {'Attributes': {**order, 'version': 2}}

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestInputValidation:
    """Request body validation."""

    @patch.object(app, 'table')
    def test_missing_order_id_returns_400(self, mock_table):
        token = create_jwt_token()
        event = make_event(token=token, order_id=None, body={'items': [], 'version': 1})
        event['pathParameters'] = {}
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Order ID' in body.get('error', '')

    @patch.object(app, 'table')
    def test_missing_items_returns_400(self, mock_table):
        token = create_jwt_token()
        event = make_event(token=token, body={'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'items' in body.get('error', '')

    @patch.object(app, 'table')
    def test_missing_version_returns_400(self, mock_table):
        token = create_jwt_token()
        event = make_event(token=token, body={'items': []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'version' in body.get('error', '')

    @patch.object(app, 'table')
    def test_invalid_version_type_returns_400(self, mock_table):
        token = create_jwt_token()
        event = make_event(token=token, body={'items': [], 'version': 'abc'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'integer' in body.get('error', '')

    @patch.object(app, 'table')
    def test_invalid_json_body_returns_400(self, mock_table):
        token = create_jwt_token()
        event = make_event(token=token, body=None)
        event['body'] = 'not json {'
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body.get('error', '')

    @patch.object(app, 'table')
    def test_order_not_found_returns_404(self, mock_table):
        token = create_jwt_token()
        mock_table.get_item.return_value = {'Item': None}

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404


class TestOptimisticLocking:
    """Optimistic locking via version field."""

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_version_conflict_returns_409(self, mock_table, mock_get_club_id):
        """ConditionalCheckFailedException returns 409 with current version."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=3)
        mock_table.get_item.return_value = {'Item': order}

        # Simulate ConditionalCheckFailedException
        exc = app.dynamodb.meta.client.exceptions.ConditionalCheckFailedException(
            error_response={'Error': {'Code': 'ConditionalCheckFailedException'}},
            operation_name='UpdateItem',
        )
        mock_table.update_item.side_effect = exc
        # When fetching current version after conflict
        mock_table.get_item.side_effect = [
            {'Item': order},  # initial fetch
            {'Item': {**order, 'version': Decimal('5')}},  # fetch after conflict
        ]
        mock_table.update_item.side_effect = exc

        event = make_event(token=token, body={'items': [], 'version': 3})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error'] == 'version_conflict'
        assert body['current_version'] == 5

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_successful_update_increments_version(self, mock_table, mock_get_club_id):
        """Successful update increments version by 1."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=2)
        mock_table.get_item.return_value = {'Item': order}

        updated_order = {**order, 'version': Decimal('3'), 'updated_at': '2027-01-15T10:30:00Z'}
        mock_table.update_item.return_value = {'Attributes': updated_order}

        items = [{'product_id': 'prod-1', 'unit_price': 50.0}]
        event = make_event(token=token, body={'items': items, 'version': 2})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['version'] == 3

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_update_sets_updated_at(self, mock_table, mock_get_club_id):
        """Successful update sets updated_at timestamp."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=1)
        mock_table.get_item.return_value = {'Item': order}

        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2'), 'updated_at': '2027-06-15T12:00:00+00:00'}
        }

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify update_item was called with updated_at in expression
        call_kwargs = mock_table.update_item.call_args[1]
        assert ':now' in call_kwargs['ExpressionAttributeValues']
        assert 'updated_at = :now' in call_kwargs['UpdateExpression']


class TestDraftSaveNoValidation:
    """No field validation on draft save (Req 2.4)."""

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_accepts_incomplete_items(self, mock_table, mock_get_club_id):
        """Incomplete item data is accepted without validation."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=1)
        mock_table.get_item.return_value = {'Item': order}

        # Items with missing fields — should still be accepted
        incomplete_items = [
            {'product_id': 'prod-meeting', 'item_fields_data': {}},
            {'product_id': 'prod-tshirt'},  # no fields at all
        ]
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2'), 'items': incomplete_items}
        }

        event = make_event(token=token, body={'items': incomplete_items, 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_accepts_empty_items_array(self, mock_table, mock_get_club_id):
        """Empty items array is accepted."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=1)
        mock_table.get_item.return_value = {'Item': order}

        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2'), 'items': []}
        }

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestLockedOrderBehavior:
    """Locked order handling (Req 2.5, 9.2)."""

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_delegate_cannot_edit_locked_order(self, mock_table, mock_get_club_id):
        """Delegate gets 403 when trying to edit a locked order."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(status="locked", version=5)
        mock_table.get_item.return_value = {'Item': order}

        event = make_event(token=token, body={'items': [], 'version': 5})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'locked' in body.get('error', '').lower()

    @patch.object(app, 'table')
    def test_admin_can_edit_locked_order(self, mock_table):
        """Admin can directly edit a locked order (Req 9.2)."""
        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["hdcnLeden", "Webshop_Management", "Regio_Pressmeet"]
        )
        order = make_order(status="locked", version=3)
        mock_table.get_item.return_value = {'Item': order}

        updated = {**order, 'version': Decimal('4'), 'status': 'locked'}
        mock_table.update_item.return_value = {'Attributes': updated}

        items = [{'product_id': 'prod-1', 'unit_price': 50.0}]
        event = make_event(token=token, body={'items': items, 'version': 3})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    @patch.object(app, 'table')
    def test_admin_edit_locked_records_status_history(self, mock_table):
        """Admin edit on locked order records in status_history with source='admin'."""
        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["hdcnLeden", "Webshop_Management", "Regio_Pressmeet"]
        )
        order = make_order(status="locked", version=2)
        mock_table.get_item.return_value = {'Item': order}

        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('3')}
        }

        event = make_event(token=token, body={'items': [], 'version': 2})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify status_history entry in update expression
        call_kwargs = mock_table.update_item.call_args[1]
        history_entry = call_kwargs['ExpressionAttributeValues'][':history_entry'][0]
        assert history_entry['from'] == 'locked'
        assert history_entry['to'] == 'locked'
        assert history_entry['by'] == 'admin@h-dcn.nl'
        assert history_entry['source'] == 'admin'


class TestSubmittedOrderRevert:
    """Submitted → draft revert on delegate edit (Req 2.6)."""

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_delegate_edit_reverts_submitted_to_draft(self, mock_table, mock_get_club_id):
        """Delegate editing submitted order reverts status to draft."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(status="submitted", version=4)
        mock_table.get_item.return_value = {'Item': order}

        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('5'), 'status': 'draft'}
        }

        event = make_event(token=token, body={'items': [], 'version': 4})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify status is set to draft in the update expression
        call_kwargs = mock_table.update_item.call_args[1]
        assert call_kwargs['ExpressionAttributeValues'][':draft'] == 'draft'
        assert '#current_status = :draft' in call_kwargs['UpdateExpression']

        # Verify status_history entry
        history_entry = call_kwargs['ExpressionAttributeValues'][':history_entry'][0]
        assert history_entry['from'] == 'submitted'
        assert history_entry['to'] == 'draft'
        assert history_entry['source'] == 'delegate'

    @patch.object(app, 'table')
    def test_admin_edit_submitted_reverts_to_draft(self, mock_table):
        """Admin editing submitted order also reverts to draft with source='admin'."""
        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["hdcnLeden", "Webshop_Management", "Regio_All"]
        )
        order = make_order(status="submitted", version=2)
        mock_table.get_item.return_value = {'Item': order}

        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('3'), 'status': 'draft'}
        }

        event = make_event(token=token, body={'items': [], 'version': 2})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        call_kwargs = mock_table.update_item.call_args[1]
        history_entry = call_kwargs['ExpressionAttributeValues'][':history_entry'][0]
        assert history_entry['from'] == 'submitted'
        assert history_entry['to'] == 'draft'
        assert history_entry['source'] == 'admin'


class TestTotalAmountRecalculation:
    """Recalculate total_amount from items × unit_price (Req 6.9)."""

    def test_calculate_total_simple(self):
        """Sum of unit_price for items without quantity."""
        items = [
            {'product_id': 'a', 'unit_price': 50.0},
            {'product_id': 'b', 'unit_price': 25.0},
            {'product_id': 'c', 'unit_price': 75.0},
        ]
        assert _calculate_total_amount(items) == Decimal('150.0')

    def test_calculate_total_with_quantity(self):
        """Items with explicit quantity multiply correctly."""
        items = [
            {'product_id': 'a', 'unit_price': 10.0, 'quantity': 3},
            {'product_id': 'b', 'unit_price': 25.0, 'quantity': 2},
        ]
        assert _calculate_total_amount(items) == Decimal('80.0')

    def test_calculate_total_empty_items(self):
        """Empty items array results in 0."""
        assert _calculate_total_amount([]) == Decimal('0')

    def test_calculate_total_missing_unit_price(self):
        """Items without unit_price contribute 0."""
        items = [
            {'product_id': 'a'},
            {'product_id': 'b', 'unit_price': 30.0},
        ]
        assert _calculate_total_amount(items) == Decimal('30.0')

    def test_calculate_total_none_values(self):
        """None values for unit_price/quantity treated as 0/1."""
        items = [
            {'product_id': 'a', 'unit_price': None, 'quantity': 5},
            {'product_id': 'b', 'unit_price': 20.0, 'quantity': None},
        ]
        # First item: 0 * 5 = 0, second item: 20 * 1 = 20
        assert _calculate_total_amount(items) == Decimal('20.0')

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_total_amount_in_update(self, mock_table, mock_get_club_id):
        """total_amount is passed to DynamoDB update."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=1)
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2'), 'total_amount': Decimal('125.0')}
        }

        items = [
            {'product_id': 'prod-1', 'unit_price': 50.0},
            {'product_id': 'prod-2', 'unit_price': 75.0},
        ]
        event = make_event(token=token, body={'items': items, 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        call_kwargs = mock_table.update_item.call_args[1]
        assert call_kwargs['ExpressionAttributeValues'][':total_amount'] == Decimal('125.0')


class TestAdminAccess:
    """Admin-specific access patterns."""

    @patch.object(app, 'table')
    def test_admin_skips_club_id_check(self, mock_table):
        """Admin does not need club_id to edit any order."""
        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["hdcnLeden", "Products_CRUD", "Regio_All"]
        )
        order = make_order(club_id="club-anywhere", version=1)
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2')}
        }

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    @patch.object(app, 'table')
    def test_regio_all_with_webshop_management_is_admin(self, mock_table):
        """Webshop_Management + Regio_All is admin."""
        token = create_jwt_token(
            email="mgmt@h-dcn.nl",
            groups=["hdcnLeden", "Webshop_Management", "Regio_All"]
        )
        order = make_order(status="locked", version=2)
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('3')}
        }

        event = make_event(token=token, body={'items': [], 'version': 2})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestDraftOrderUpdate:
    """Basic draft order updates."""

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_draft_update_no_status_change(self, mock_table, mock_get_club_id):
        """Updating a draft order does not change status or add status_history."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(status="draft", version=1)
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('2')}
        }

        event = make_event(token=token, body={'items': [], 'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # No status change or history for plain draft update
        call_kwargs = mock_table.update_item.call_args[1]
        assert ':draft' not in call_kwargs['ExpressionAttributeValues']
        assert ':history_entry' not in call_kwargs['ExpressionAttributeValues']

    @patch('handler.presmeet_upsert_order.app.get_club_id', return_value='club-amsterdam')
    @patch.object(app, 'table')
    def test_condition_expression_uses_version(self, mock_table, mock_get_club_id):
        """ConditionExpression checks version field."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        order = make_order(version=7)
        mock_table.get_item.return_value = {'Item': order}
        mock_table.update_item.return_value = {
            'Attributes': {**order, 'version': Decimal('8')}
        }

        event = make_event(token=token, body={'items': [], 'version': 7})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        call_kwargs = mock_table.update_item.call_args[1]
        assert call_kwargs['ConditionExpression'] == '#version = :expected_version'
        assert call_kwargs['ExpressionAttributeValues'][':expected_version'] == 7
        assert call_kwargs['ExpressionAttributeValues'][':new_version'] == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
