"""
Unit Tests for admin_lock_orders and admin_unlock_order Lambda Handlers

Tests the admin order lock/unlock endpoints:
- admin_lock_orders: POST /admin/orders/{id}/lock
  - Single-order lock with status_history (timestamp, admin email, source: "manual")
  - Bulk lock (legacy mode) with channel/tenant filter
  - ConditionExpression concurrency check (409 on conflict)
  - Requires Webshop_Management + (Regio_Pressmeet or Regio_All)
- admin_unlock_order: POST /admin/orders/{id}/unlock
  - Set status back to submitted
  - Reject if event is closed (error: "edit directly instead")
  - ConditionExpression concurrency check (409 on conflict)
  - Requires Webshop_Management + (Regio_Pressmeet or Regio_All)

Requirements: 9
"""

import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import boto3
import pytest
from moto import mock_aws

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
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events')


# ============================================================
# Tests for admin_lock_orders
# ============================================================

class TestAdminLockOrders:
    """Unit tests for the admin_lock_orders handler."""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Set up mocked DynamoDB tables for each test."""
        with mock_aws():
            os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
            os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
            os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'

            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            self.orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[
                    {'AttributeName': 'order_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.meta.client.get_waiter('table_exists').wait(TableName='Orders')

            # Patch the table in the handler module
            with patch(
                'handler.admin_lock_orders.app.table', self.orders_table
            ):
                # Also patch dynamodb resource for ConditionalCheckFailedException
                with patch(
                    'handler.admin_lock_orders.app.dynamodb', dynamodb
                ):
                    yield

    def _create_order(self, order_id='order-001', status='submitted', event_id='event-pm2027'):
        """Helper to create an order in DynamoDB."""
        order = {
            'order_id': order_id,
            'club_id': 'club-amsterdam',
            'event_id': event_id,
            'event_type': 'presmeet',
            'status': status,
            'payment_status': 'unpaid',
            'total_amount': Decimal('150.00'),
            'items': [
                {
                    'product_id': 'prod-meeting',
                    'item_fields_data': {'name': 'Jan de Vries', 'role': 'President'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                }
            ],
            'version': 2,
            'status_history': [],
            'created_at': '2025-01-10T08:00:00+00:00',
            'updated_at': '2025-01-15T10:30:00+00:00',
            'created_by': 'delegate@club.nl',
        }
        self.orders_table.put_item(Item=order)
        return order

    def _make_event(self, order_id=None, body=None, method='POST'):
        """Create an API Gateway event."""
        event = {
            'httpMethod': method,
            'headers': {'Authorization': 'Bearer mock-token'},
            'queryStringParameters': None,
            'pathParameters': {'id': order_id} if order_id else None,
            'body': json.dumps(body) if body else None,
        }
        return event

    def _mock_admin_auth(self, user_email='admin@h-dcn.nl'):
        """Mock auth for an admin user with Webshop_Management + Regio_Pressmeet."""
        user_roles = ['hdcnLeden', 'Webshop_Management', 'Regio_Pressmeet']
        return (
            patch(
                'handler.admin_lock_orders.app.extract_user_credentials',
                return_value=(user_email, user_roles, None),
            ),
            patch('handler.admin_lock_orders.app.log_successful_access'),
        )

    def _mock_non_admin_auth(self, user_email='delegate@club.nl'):
        """Mock auth for a non-admin user (missing Webshop_Management)."""
        user_roles = ['hdcnLeden', 'Regio_Pressmeet']
        return (
            patch(
                'handler.admin_lock_orders.app.extract_user_credentials',
                return_value=(user_email, user_roles, None),
            ),
            patch('handler.admin_lock_orders.app.log_successful_access'),
        )

    # --- Import handler within mock context ---
    def _get_handler(self):
        from handler.admin_lock_orders.app import lambda_handler
        return lambda_handler

    # --- Single-order lock tests ---

    def test_lock_single_submitted_order(self):
        """Admin can lock a single submitted order via path parameter."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['status'] == 'locked'
        assert body['message'] == 'Order locked successfully'

    def test_lock_single_order_records_status_history(self):
        """Locking records transition in status_history with timestamp, admin email, source manual."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth(user_email='admin@h-dcn.nl')
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        body = json.loads(response['body'])
        transition = body['transition']
        assert transition['from'] == 'submitted'
        assert transition['to'] == 'locked'
        assert transition['by'] == 'admin@h-dcn.nl'
        assert transition['source'] == 'manual'
        assert 'at' in transition

    def test_lock_single_order_persisted_in_dynamodb(self):
        """After locking, DynamoDB shows status locked with status_history."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            handler(self._make_event(order_id='order-001'), None)

        db_order = self.orders_table.get_item(Key={'order_id': 'order-001'})['Item']
        assert db_order['status'] == 'locked'
        assert len(db_order['status_history']) == 1
        assert db_order['status_history'][0]['source'] == 'manual'

    def test_lock_non_submitted_order_returns_400(self):
        """Cannot lock an order that is not in submitted status."""
        self._create_order(order_id='order-001', status='draft')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'draft' in body['error'].lower()

    def test_lock_already_locked_order_returns_400(self):
        """Cannot lock an order that is already locked."""
        self._create_order(order_id='order-001', status='locked')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'locked' in body['error'].lower()

    def test_lock_nonexistent_order_returns_404(self):
        """Locking a non-existent order returns 404."""
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='nonexistent'), None)

        assert response['statusCode'] == 404

    def test_lock_concurrency_conflict_returns_409(self):
        """If order status changes between read and update, return 409."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        # Simulate: after get_item returns submitted, another process changes status
        original_update = self.orders_table.update_item

        def mock_update(*args, **kwargs):
            # First change the order status to simulate a concurrent modification
            self.orders_table.put_item(Item={
                'order_id': 'order-001',
                'status': 'draft',  # Changed by another process
                'club_id': 'club-amsterdam',
                'event_id': 'event-pm2027',
            })
            return original_update(*args, **kwargs)

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            # Patch update_item to simulate the race condition
            with patch.object(self.orders_table, 'update_item', side_effect=mock_update):
                response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'concurrently' in body['error'].lower()

    # --- Authorization tests ---

    def test_non_admin_returns_403(self):
        """User without Webshop_Management cannot lock orders."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        auth_patches = self._mock_non_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'webshop_management' in body['error'].lower()

    def test_webshop_management_without_regio_returns_403(self):
        """User with Webshop_Management but no Regio_Pressmeet/Regio_All gets 403."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        user_roles = ['hdcnLeden', 'Webshop_Management']  # No Regio
        with patch(
            'handler.admin_lock_orders.app.extract_user_credentials',
            return_value=('admin@h-dcn.nl', user_roles, None),
        ), patch('handler.admin_lock_orders.app.log_successful_access'):
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 403

    def test_regio_all_grants_access(self):
        """User with Webshop_Management + Regio_All can lock orders."""
        self._create_order(order_id='order-001', status='submitted')
        handler = self._get_handler()

        user_roles = ['hdcnLeden', 'Webshop_Management', 'Regio_All']
        with patch(
            'handler.admin_lock_orders.app.extract_user_credentials',
            return_value=('admin@h-dcn.nl', user_roles, None),
        ), patch('handler.admin_lock_orders.app.log_successful_access'):
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 200

    # --- Bulk lock tests ---

    def test_bulk_lock_all_submitted_orders(self):
        """Bulk mode locks all submitted orders when no channel filter."""
        self._create_order(order_id='order-001', status='submitted')
        self._create_order(order_id='order-002', status='submitted')
        self._create_order(order_id='order-003', status='draft')  # Should not be locked
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(body={}), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 2
        assert body['failed_count'] == 0

    def test_bulk_lock_filters_by_event_id(self):
        """Bulk lock with event_id filter only locks matching orders."""
        self._create_order(order_id='order-001', status='submitted', event_id='event-pm2027')
        self._create_order(order_id='order-002', status='submitted', event_id='event-other')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(body={'event_id': 'event-pm2027'}), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 1

    # --- Edge cases ---

    def test_options_request_returns_200(self):
        """OPTIONS request returns 200 for CORS preflight."""
        handler = self._get_handler()
        response = handler({'httpMethod': 'OPTIONS', 'headers': {}, 'body': None}, None)
        assert response['statusCode'] == 200

    def test_invalid_json_body_returns_400(self):
        """Invalid JSON in request body returns 400."""
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            event = {
                'httpMethod': 'POST',
                'headers': {'Authorization': 'Bearer mock-token'},
                'pathParameters': None,
                'body': 'not valid json{{{',
                'queryStringParameters': None,
            }
            response = handler(event, None)

        assert response['statusCode'] == 400


# ============================================================
# Tests for admin_unlock_order
# ============================================================

class TestAdminUnlockOrder:
    """Unit tests for the admin_unlock_order handler."""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Set up mocked DynamoDB tables for each test."""
        with mock_aws():
            os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
            os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
            os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'

            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            self.orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[
                    {'AttributeName': 'order_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )

            self.events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[
                    {'AttributeName': 'event_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )

            dynamodb.meta.client.get_waiter('table_exists').wait(TableName='Orders')
            dynamodb.meta.client.get_waiter('table_exists').wait(TableName='Events')

            with patch('handler.admin_unlock_order.app.table', self.orders_table):
                with patch('handler.admin_unlock_order.app.events_table', self.events_table):
                    with patch('handler.admin_unlock_order.app.dynamodb', dynamodb):
                        yield

    def _create_order(self, order_id='order-001', status='locked', event_id='event-pm2027'):
        """Helper to create an order."""
        order = {
            'order_id': order_id,
            'club_id': 'club-amsterdam',
            'event_id': event_id,
            'event_type': 'presmeet',
            'status': status,
            'payment_status': 'unpaid',
            'total_amount': Decimal('150.00'),
            'items': [],
            'version': 2,
            'status_history': [
                {
                    'from': 'submitted',
                    'to': 'locked',
                    'at': '2025-01-20T10:00:00+00:00',
                    'by': 'admin@h-dcn.nl',
                    'source': 'manual',
                }
            ],
            'created_at': '2025-01-10T08:00:00+00:00',
            'updated_at': '2025-01-20T10:00:00+00:00',
        }
        self.orders_table.put_item(Item=order)
        return order

    def _create_event(self, event_id='event-pm2027', status='open'):
        """Helper to create an event record."""
        event = {
            'event_id': event_id,
            'event_type': 'presmeet',
            'name': 'Presidents Meeting 2027',
            'status': status,
            'start_date': '2027-06-20',
            'end_date': '2027-06-22',
            'registration_open': '2027-01-01',
            'registration_close': '2027-05-01',
        }
        self.events_table.put_item(Item=event)
        return event

    def _make_event(self, order_id='order-001', method='POST'):
        """Create an API Gateway event."""
        return {
            'httpMethod': method,
            'headers': {'Authorization': 'Bearer mock-token'},
            'queryStringParameters': None,
            'pathParameters': {'id': order_id},
            'body': None,
        }

    def _mock_admin_auth(self, user_email='admin@h-dcn.nl'):
        """Mock auth for admin user."""
        user_roles = ['hdcnLeden', 'Webshop_Management', 'Regio_Pressmeet']
        return (
            patch(
                'handler.admin_unlock_order.app.extract_user_credentials',
                return_value=(user_email, user_roles, None),
            ),
            patch('handler.admin_unlock_order.app.log_successful_access'),
        )

    def _mock_non_admin_auth(self, user_email='delegate@club.nl'):
        """Mock auth for non-admin user."""
        user_roles = ['hdcnLeden', 'Regio_Pressmeet']
        return (
            patch(
                'handler.admin_unlock_order.app.extract_user_credentials',
                return_value=(user_email, user_roles, None),
            ),
            patch('handler.admin_unlock_order.app.log_successful_access'),
        )

    def _get_handler(self):
        from handler.admin_unlock_order.app import lambda_handler
        return lambda_handler

    # --- Successful unlock tests ---

    def test_unlock_locked_order_with_open_event(self):
        """Admin can unlock a locked order when the event is open."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['status'] == 'draft'
        assert body['message'] == 'Order unlocked successfully'

    def test_unlock_records_status_history(self):
        """Unlocking records transition in status_history."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth(user_email='admin@h-dcn.nl')
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        body = json.loads(response['body'])
        transition = body['transition']
        assert transition['from'] == 'locked'
        assert transition['to'] == 'draft'
        assert transition['by'] == 'admin@h-dcn.nl'
        assert transition['source'] == 'manual'
        assert 'at' in transition

    def test_unlock_persisted_in_dynamodb(self):
        """After unlock, DynamoDB shows status submitted with updated history."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            handler(self._make_event(order_id='order-001'), None)

        db_order = self.orders_table.get_item(Key={'order_id': 'order-001'})['Item']
        assert db_order['status'] == 'draft'
        # Should have 2 entries: the original lock + the unlock
        assert len(db_order['status_history']) == 2
        assert db_order['status_history'][1]['to'] == 'draft'

    # --- Event closed rejection tests ---

    def test_unlock_rejected_when_event_closed(self):
        """Unlock is rejected when the linked event is closed."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='closed')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'closed' in body['error'].lower()
        assert 'edit' in body['error'].lower() or 'directly' in body['error'].lower()

    def test_unlock_allowed_when_no_event_record(self):
        """Unlock succeeds if the event_id has no matching Event record (graceful)."""
        self._create_order(order_id='order-001', status='locked', event_id='missing-event')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 200

    def test_unlock_allowed_when_order_has_no_event_id(self):
        """Unlock succeeds if order has no event_id field."""
        order = {
            'order_id': 'order-no-event',
            'club_id': 'club-amsterdam',
            'status': 'locked',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'items': [],
            'version': 1,
            'status_history': [],
        }
        self.orders_table.put_item(Item=order)
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-no-event'), None)

        assert response['statusCode'] == 200

    # --- Status validation tests ---

    def test_unlock_non_locked_order_returns_400(self):
        """Cannot unlock an order that is not locked or submitted."""
        self._create_order(order_id='order-001', status='paid')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'paid' in body['error'].lower()

    def test_unlock_draft_order_returns_400(self):
        """Cannot unlock an order in draft status."""
        self._create_order(order_id='order-001', status='draft')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 400

    def test_unlock_nonexistent_order_returns_404(self):
        """Unlocking a non-existent order returns 404."""
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='nonexistent'), None)

        assert response['statusCode'] == 404

    # --- Concurrency check tests ---

    def test_unlock_concurrency_conflict_returns_409(self):
        """If order status changes between read and update, return 409."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        original_update = self.orders_table.update_item

        def mock_update(*args, **kwargs):
            # Simulate concurrent modification: status changed to paid (not submitted/locked)
            self.orders_table.put_item(Item={
                'order_id': 'order-001',
                'status': 'paid',
                'club_id': 'club-amsterdam',
                'event_id': 'event-pm2027',
            })
            return original_update(*args, **kwargs)

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            with patch.object(self.orders_table, 'update_item', side_effect=mock_update):
                response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'concurrently' in body['error'].lower()

    # --- Authorization tests ---

    def test_non_admin_returns_403(self):
        """User without Webshop_Management cannot unlock orders."""
        self._create_order(order_id='order-001', status='locked')
        handler = self._get_handler()

        auth_patches = self._mock_non_admin_auth()
        with auth_patches[0], auth_patches[1]:
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 403

    def test_webshop_management_without_regio_returns_403(self):
        """Webshop_Management alone (no Regio) is insufficient."""
        self._create_order(order_id='order-001', status='locked')
        handler = self._get_handler()

        user_roles = ['hdcnLeden', 'Webshop_Management']
        with patch(
            'handler.admin_unlock_order.app.extract_user_credentials',
            return_value=('admin@h-dcn.nl', user_roles, None),
        ), patch('handler.admin_unlock_order.app.log_successful_access'):
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 403

    def test_regio_all_grants_access(self):
        """Webshop_Management + Regio_All grants unlock access."""
        self._create_order(order_id='order-001', status='locked')
        self._create_event(event_id='event-pm2027', status='open')
        handler = self._get_handler()

        user_roles = ['hdcnLeden', 'Webshop_Management', 'Regio_All']
        with patch(
            'handler.admin_unlock_order.app.extract_user_credentials',
            return_value=('admin@h-dcn.nl', user_roles, None),
        ), patch('handler.admin_unlock_order.app.log_successful_access'):
            response = handler(self._make_event(order_id='order-001'), None)

        assert response['statusCode'] == 200

    # --- Edge cases ---

    def test_missing_order_id_returns_400(self):
        """Request without order_id path parameter returns 400."""
        handler = self._get_handler()

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1]:
            event = {
                'httpMethod': 'POST',
                'headers': {'Authorization': 'Bearer mock-token'},
                'pathParameters': None,
                'body': None,
                'queryStringParameters': None,
            }
            response = handler(event, None)

        assert response['statusCode'] == 400

    def test_options_request_returns_200(self):
        """OPTIONS request returns 200 for CORS preflight."""
        handler = self._get_handler()
        response = handler({'httpMethod': 'OPTIONS', 'headers': {}, 'body': None}, None)
        assert response['statusCode'] == 200
