"""
Unit Tests for lock_orders Lambda Handler (unified lock/unlock).

Tests the unified admin lock/unlock endpoints:
- POST /admin/booking/lock?source_id={id}    → lock all submitted orders for a source
- POST /admin/booking/unlock?source_id={id}  → unlock all submitted/locked orders for a source
- POST /admin/booking/{id}/unlock            → unlock a specific submitted/locked order → draft

Test cases:
- Returns 403 when user is not admin
- Returns 400 when source_id is missing
- Successfully locks submitted orders (count + order_ids)
- Skips non-submitted orders (draft, already locked)
- Unlock: returns specific order to draft status
- Unlock: accepts submitted or locked orders
- Unlock: returns 404 when order doesn't exist
- Unlock: rejects draft orders
- Batch unlock: unlocks submitted and locked orders
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'lock_orders', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_SOURCE_ID = 'evt-12345678-1234-1234-1234-123456789abc'
TEST_ADMIN_EMAIL = 'admin@h-dcn.nl'
TEST_NON_ADMIN_EMAIL = 'user@h-dcn.nl'


def _make_lock_event(source_id=None, query_params=None, body=None):
    """Create API Gateway event for POST /admin/booking/lock."""
    qsp = query_params or {}
    if source_id and 'source_id' not in qsp:
        qsp['source_id'] = source_id
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': qsp if qsp else None,
        'pathParameters': None,
        'body': json.dumps(body) if body else None,
        'resource': '/admin/booking/lock',
    }


def _make_unlock_event(order_id):
    """Create API Gateway event for POST /admin/booking/{id}/unlock."""
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': {'id': order_id},
        'body': None,
        'resource': '/admin/booking/{id}/unlock',
    }


def _make_batch_unlock_event(source_id=None, query_params=None, body=None):
    """Create API Gateway event for POST /admin/booking/unlock."""
    qsp = query_params or {}
    if source_id and 'source_id' not in qsp:
        qsp['source_id'] = source_id
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': qsp if qsp else None,
        'pathParameters': None,
        'body': json.dumps(body) if body else None,
        'resource': '/admin/booking/unlock',
    }


# ---------------------------------------------------------------------------
# Auth patches
# ---------------------------------------------------------------------------

def _admin_auth_patches():
    """Return patch.multiple for admin user (events_crud permission)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_ADMIN_EMAIL, ['hdcnLeden', 'Events_CRUD', 'System_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_admin_auth_patches():
    """Return patch.multiple for non-admin user (no events_crud)."""
    def _validate_no_admin(roles, perms, email, region):
        if 'events_crud' in perms:
            return (False, {'statusCode': 403, 'body': json.dumps({'error': 'Access denied'})}, {})
        return (True, None, {})

    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_NON_ADMIN_EMAIL, ['hdcnLeden'], None),
        validate_permissions_with_regions=_validate_no_admin,
        log_successful_access=lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Orders table with GSI event-member-index
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
                {'AttributeName': 'source_id', 'AttributeType': 'S'},
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'event-member-index',
                    'KeySchema': [
                        {'AttributeName': 'source_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'member_id', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'members': members_table,
            'handler': handler,
        }


# ---------------------------------------------------------------------------
# Helper to seed orders
# ---------------------------------------------------------------------------

def _seed_order(orders_table, order_id, source_id=TEST_SOURCE_ID, member_id='mem-001',
                status='submitted', version=1):
    """Seed an order into the Orders table."""
    orders_table.put_item(Item={
        'order_id': order_id,
        'source_id': source_id,
        'member_id': member_id,
        'status': status,
        'items': [{'product_id': 'prod-001', 'item_fields_data': {'name': 'Test'}}],
        'version': version,
        'status_history': [],
        'created_at': '2025-01-10T08:00:00+00:00',
        'updated_at': '2025-01-15T10:30:00+00:00',
    })


# ---------------------------------------------------------------------------
# Tests: Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    """Tests for admin permission check."""

    def test_returns_403_when_user_is_not_admin(self, setup_tables):
        """Non-admin users cannot lock orders."""
        handler = setup_tables['handler']

        with _non_admin_auth_patches():
            event = _make_lock_event(source_id=TEST_SOURCE_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'denied' in body.get('error', '').lower() or 'admin' in body.get('error', '').lower()

    def test_unlock_returns_403_when_user_is_not_admin(self, setup_tables):
        """Non-admin users cannot unlock orders."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_order(orders_table, 'order-001', status='locked')

        with _non_admin_auth_patches():
            event = _make_unlock_event('order-001')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403


# ---------------------------------------------------------------------------
# Tests: Missing source_id
# ---------------------------------------------------------------------------

class TestMissingSourceId:
    """Tests for missing source_id parameter."""

    def test_returns_400_when_source_id_is_missing(self, setup_tables):
        """Lock endpoint requires source_id param."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_lock_event(source_id=None, query_params={})
            # Remove source_id from query params
            event['queryStringParameters'] = None
            event['body'] = None
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'source_id' in body.get('error', '').lower()

    def test_accepts_source_id_from_body(self, setup_tables):
        """Lock endpoint can read source_id from request body."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_order(orders_table, 'order-001', source_id=TEST_SOURCE_ID, status='submitted')

        with _admin_auth_patches():
            event = {
                'httpMethod': 'POST',
                'headers': {'Authorization': 'Bearer test-token'},
                'queryStringParameters': None,
                'pathParameters': None,
                'body': json.dumps({'source_id': TEST_SOURCE_ID}),
                'resource': '/admin/booking/lock',
            }
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 1


# ---------------------------------------------------------------------------
# Tests: Successful lock
# ---------------------------------------------------------------------------

class TestLockOrders:
    """Tests for successfully locking submitted orders."""

    def test_locks_submitted_orders(self, setup_tables):
        """Locks all submitted orders for a source_id and returns count + IDs."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed multiple orders with different statuses
        _seed_order(orders_table, 'order-001', status='submitted', member_id='mem-001')
        _seed_order(orders_table, 'order-002', status='submitted', member_id='mem-002')
        _seed_order(orders_table, 'order-003', status='draft', member_id='mem-003')
        _seed_order(orders_table, 'order-004', status='locked', member_id='mem-004')

        with _admin_auth_patches():
            event = _make_lock_event(source_id=TEST_SOURCE_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 2
        assert set(body['locked_order_ids']) == {'order-001', 'order-002'}
        assert body['skipped_count'] == 2  # draft + already locked

    def test_skips_non_submitted_orders(self, setup_tables):
        """Orders in draft or locked status are not affected."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-draft', status='draft', member_id='mem-001')
        _seed_order(orders_table, 'order-locked', status='locked', member_id='mem-002')

        with _admin_auth_patches():
            event = _make_lock_event(source_id=TEST_SOURCE_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 0
        assert body['locked_order_ids'] == []
        assert body['skipped_count'] == 2

    def test_locked_orders_persisted_in_dynamodb(self, setup_tables):
        """After locking, DynamoDB records show status=locked and incremented version."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='submitted', version=2, member_id='mem-001')

        with _admin_auth_patches():
            event = _make_lock_event(source_id=TEST_SOURCE_ID)
            handler.lambda_handler(event, None)

        # Verify in DynamoDB
        db_order = orders_table.get_item(Key={'order_id': 'order-001'})['Item']
        assert db_order['status'] == 'locked'
        assert db_order['version'] == 3  # incremented from 2
        assert len(db_order['status_history']) == 1
        assert db_order['status_history'][0]['from'] == 'submitted'
        assert db_order['status_history'][0]['to'] == 'locked'
        assert db_order['status_history'][0]['by'] == TEST_ADMIN_EMAIL

    def test_returns_zero_when_no_orders_exist(self, setup_tables):
        """Returns success with 0 count when no orders found for source."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_lock_event(source_id='nonexistent-source')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['locked_count'] == 0


# ---------------------------------------------------------------------------
# Tests: Unlock
# ---------------------------------------------------------------------------

class TestUnlockOrder:
    """Tests for unlocking a specific order."""

    def test_unlocks_locked_order_to_draft(self, setup_tables):
        """Unlock transitions a locked order to draft status (Req 10.3)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='locked', version=3, member_id='mem-001')

        with _admin_auth_patches():
            event = _make_unlock_event('order-001')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['status'] == 'draft'
        assert body['transition']['from'] == 'locked'
        assert body['transition']['to'] == 'draft'
        assert body['message'] == 'Order unlocked successfully'

    def test_unlocks_submitted_order_to_draft(self, setup_tables):
        """Unlock transitions a submitted order to draft status (Req 10.3)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='submitted', version=2, member_id='mem-001')

        with _admin_auth_patches():
            event = _make_unlock_event('order-001')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['status'] == 'draft'
        assert body['transition']['from'] == 'submitted'
        assert body['transition']['to'] == 'draft'

    def test_unlock_returns_404_when_order_does_not_exist(self, setup_tables):
        """Unlock returns 404 for non-existent order."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_unlock_event('nonexistent-order')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body.get('error', '').lower()

    def test_unlock_returns_400_for_draft_order(self, setup_tables):
        """Cannot unlock an order that is already in draft status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='draft', member_id='mem-001')

        with _admin_auth_patches():
            event = _make_unlock_event('order-001')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'draft' in body.get('error', '').lower()

    def test_unlock_persisted_in_dynamodb(self, setup_tables):
        """After unlock, DynamoDB shows status=draft with version incremented."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='locked', version=3, member_id='mem-001')

        with _admin_auth_patches():
            event = _make_unlock_event('order-001')
            handler.lambda_handler(event, None)

        db_order = orders_table.get_item(Key={'order_id': 'order-001'})['Item']
        assert db_order['status'] == 'draft'
        assert db_order['version'] == 4  # incremented from 3
        assert len(db_order['status_history']) == 1
        assert db_order['status_history'][0]['to'] == 'draft'


# ---------------------------------------------------------------------------
# Tests: OPTIONS preflight
# ---------------------------------------------------------------------------

class TestCORS:
    """Tests for CORS preflight handling."""

    def test_options_request_returns_200(self, setup_tables):
        """OPTIONS request returns 200 for CORS preflight."""
        handler = setup_tables['handler']
        response = handler.lambda_handler(
            {'httpMethod': 'OPTIONS', 'headers': {}, 'body': None},
            None
        )
        assert response['statusCode'] == 200


# ---------------------------------------------------------------------------
# Tests: Batch Unlock
# ---------------------------------------------------------------------------

class TestBatchUnlockOrders:
    """Tests for batch unlocking submitted/locked orders (Req 10.5)."""

    def test_batch_unlocks_submitted_and_locked_orders(self, setup_tables):
        """Batch unlock transitions all submitted and locked orders to draft."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='submitted', member_id='mem-001')
        _seed_order(orders_table, 'order-002', status='locked', member_id='mem-002')
        _seed_order(orders_table, 'order-003', status='draft', member_id='mem-003')

        with _admin_auth_patches():
            event = _make_batch_unlock_event(source_id=TEST_SOURCE_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['unlocked_count'] == 2
        assert set(body['unlocked_order_ids']) == {'order-001', 'order-002'}
        assert body['skipped_count'] == 1  # draft order skipped

    def test_batch_unlock_skips_draft_orders(self, setup_tables):
        """Batch unlock does not touch draft orders."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='draft', member_id='mem-001')
        _seed_order(orders_table, 'order-002', status='draft', member_id='mem-002')

        with _admin_auth_patches():
            event = _make_batch_unlock_event(source_id=TEST_SOURCE_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['unlocked_count'] == 0
        assert body['skipped_count'] == 2

    def test_batch_unlock_returns_zero_when_no_orders(self, setup_tables):
        """Returns success with 0 count when no orders found for source."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_batch_unlock_event(source_id='nonexistent-source')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['unlocked_count'] == 0

    def test_batch_unlock_persisted_in_dynamodb(self, setup_tables):
        """After batch unlock, DynamoDB records show status=draft and version incremented."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_order(orders_table, 'order-001', status='locked', version=5, member_id='mem-001')

        with _admin_auth_patches():
            event = _make_batch_unlock_event(source_id=TEST_SOURCE_ID)
            handler.lambda_handler(event, None)

        db_order = orders_table.get_item(Key={'order_id': 'order-001'})['Item']
        assert db_order['status'] == 'draft'
        assert db_order['version'] == 6
        assert len(db_order['status_history']) == 1
        assert db_order['status_history'][0]['from'] == 'locked'
        assert db_order['status_history'][0]['to'] == 'draft'

    def test_batch_unlock_requires_source_id(self, setup_tables):
        """Batch unlock returns 400 when source_id is missing."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_batch_unlock_event()
            event['queryStringParameters'] = None
            event['body'] = None
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'source_id' in body.get('error', '').lower()
