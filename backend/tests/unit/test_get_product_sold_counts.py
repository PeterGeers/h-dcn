"""
Unit tests for get_product_sold_counts handler.

Tests the GET /products/sold-counts?event_id={id} endpoint that
aggregates product quantities across all non-cancelled orders for an event.

Requirements: 7.3, 7.5, 7.8
"""

import importlib.util
import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

# --- Environment setup (before importing handler) ---
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders-Test'

_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_product_sold_counts', 'app.py')
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


def _auth_patches(email='user@h-dcn.nl', roles=None):
    """Patch auth utilities for testing."""
    if roles is None:
        roles = ['hdcnLeden']
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, roles, None),
        log_successful_access=lambda *a, **kw: None,
    )


def _make_event(query_params=None, http_method='GET', headers=None):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': http_method,
        'queryStringParameters': query_params,
        'headers': headers or {'Authorization': 'Bearer fake.jwt.token'},
        'body': None,
    }


@pytest.fixture
def setup_tables():
    """Create mock DynamoDB Orders table and load handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Orders-Test',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        handler = _load_handler()
        yield table, handler


class TestAuthAccess:
    """Tests for authentication and authorization."""

    def test_event_participant_has_access(self, setup_tables):
        """event_participant role grants access."""
        table, handler = setup_tables
        with _auth_patches(roles=['event_participant']):
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200

    def test_hdcn_leden_has_access(self, setup_tables):
        """hdcnLeden role grants access."""
        table, handler = setup_tables
        with _auth_patches(roles=['hdcnLeden']):
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200

    def test_admin_has_access(self, setup_tables):
        """Admin roles grant access."""
        table, handler = setup_tables
        with _auth_patches(roles=['Products_CRUD']):
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200

    def test_no_valid_role_returns_403(self, setup_tables):
        """Users without event_participant, hdcnLeden, or admin roles get 403."""
        table, handler = setup_tables
        with _auth_patches(roles=['verzoek_lid']):
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 403

    def test_auth_failure_returns_error(self, setup_tables):
        """Authentication failure returns the auth error."""
        table, handler = setup_tables
        auth_error_response = {
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized'}),
            'headers': {},
        }
        with patch.object(handler, 'extract_user_credentials', return_value=(None, None, auth_error_response)):
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 401


class TestQueryParams:
    """Tests for query parameter validation."""

    def test_missing_event_id_returns_400(self, setup_tables):
        """Missing event_id query parameter returns 400."""
        table, handler = setup_tables
        with _auth_patches():
            event = _make_event(query_params={})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'event_id' in body.get('error', '')

    def test_null_query_params_returns_400(self, setup_tables):
        """Null queryStringParameters returns 400."""
        table, handler = setup_tables
        with _auth_patches():
            event = _make_event(query_params=None)
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 400


class TestAggregation:
    """Tests for product sold count aggregation."""

    def test_empty_orders_returns_empty_map(self, setup_tables):
        """No orders for event returns empty sold counts."""
        table, handler = setup_tables
        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-no-orders'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {}

    def test_aggregates_quantities_across_orders(self, setup_tables):
        """Aggregates product quantities from multiple orders."""
        table, handler = setup_tables

        # Insert orders
        table.put_item(Item={
            'order_id': 'order-1',
            'event_id': 'evt-001',
            'status': 'submitted',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('2')},
                {'product_id': 'prod-b', 'quantity': Decimal('1')},
            ],
        })
        table.put_item(Item={
            'order_id': 'order-2',
            'event_id': 'evt-001',
            'status': 'draft',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('3')},
                {'product_id': 'prod-c', 'quantity': Decimal('1')},
            ],
        })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {'prod-a': 5, 'prod-b': 1, 'prod-c': 1}

    def test_excludes_cancelled_orders(self, setup_tables):
        """Cancelled orders are excluded from the count."""
        table, handler = setup_tables

        table.put_item(Item={
            'order_id': 'order-1',
            'event_id': 'evt-001',
            'status': 'submitted',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('2')},
            ],
        })
        table.put_item(Item={
            'order_id': 'order-cancelled',
            'event_id': 'evt-001',
            'status': 'cancelled',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('5')},
            ],
        })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {'prod-a': 2}

    def test_excludes_orders_from_other_events(self, setup_tables):
        """Orders from other events are not counted."""
        table, handler = setup_tables

        table.put_item(Item={
            'order_id': 'order-1',
            'event_id': 'evt-001',
            'status': 'submitted',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('2')},
            ],
        })
        table.put_item(Item={
            'order_id': 'order-other',
            'event_id': 'evt-other',
            'status': 'submitted',
            'items': [
                {'product_id': 'prod-a', 'quantity': Decimal('10')},
            ],
        })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {'prod-a': 2}

    def test_handles_orders_without_items(self, setup_tables):
        """Orders with empty or missing items field don't crash."""
        table, handler = setup_tables

        table.put_item(Item={
            'order_id': 'order-empty',
            'event_id': 'evt-001',
            'status': 'draft',
            'items': [],
        })
        table.put_item(Item={
            'order_id': 'order-no-items',
            'event_id': 'evt-001',
            'status': 'draft',
        })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {}

    def test_handles_items_without_quantity_field(self, setup_tables):
        """Items without explicit quantity default to 1."""
        table, handler = setup_tables

        table.put_item(Item={
            'order_id': 'order-1',
            'event_id': 'evt-001',
            'status': 'submitted',
            'items': [
                {'product_id': 'prod-a'},  # No quantity field
                {'product_id': 'prod-a'},
            ],
        })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {'prod-a': 2}

    def test_includes_all_non_cancelled_statuses(self, setup_tables):
        """Draft, submitted, and locked orders are all included."""
        table, handler = setup_tables

        for status in ['draft', 'submitted', 'locked']:
            table.put_item(Item={
                'order_id': f'order-{status}',
                'event_id': 'evt-001',
                'status': status,
                'items': [
                    {'product_id': 'prod-a', 'quantity': Decimal('1')},
                ],
            })

        with _auth_patches():
            event = _make_event(query_params={'event_id': 'evt-001'})
            response = handler.lambda_handler(event, None)
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body == {'prod-a': 3}


class TestOptionsRequest:
    """Tests for CORS preflight handling."""

    def test_options_returns_cors_headers(self, setup_tables):
        """OPTIONS request is handled for CORS preflight."""
        table, handler = setup_tables
        event = _make_event(http_method='OPTIONS')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
