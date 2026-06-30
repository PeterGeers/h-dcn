"""
Unit tests for admin_event_dashboard handler.

Tests: registration stats, order status breakdown, payment breakdown,
per-product capacity, auth enforcement.

Requirements: 14.1, 14.2, 14.3, 14.4
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws

# Set AWS env vars before any handler import
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-bucket'

# Handler file path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_event_dashboard', 'app.py')
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


def _auth_patches():
    """Patch auth for admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD', 'Events_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_admin_auth_patches():
    """Patch auth for non-admin access (event_participant only)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@test.nl', ['event_participant'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _make_event(method='GET', event_id='evt-001', path_params=None):
    """Build an API Gateway event."""
    return {
        'httpMethod': method,
        'pathParameters': path_params or {'event_id': event_id},
        'queryStringParameters': None,
        'headers': {'Authorization': 'Bearer test-token'},
        'body': None,
    }


# --- S3 registry fixture ---
REGISTRY_JSON = json.dumps({
    'version': '1.0',
    'rows': [
        {'row_id': 'row-1', 'label': 'Club Alpha', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'row-2', 'label': 'Club Beta', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'row-3', 'label': 'Club Gamma', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'row-4', 'label': 'Club Delta', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'row-5', 'label': 'Club Epsilon', 'allowed_emails': [], 'logo_url': None},
    ],
})


@pytest.fixture
def setup_aws():
    """Set up mocked AWS resources (DynamoDB + S3) and load handler."""
    with mock_aws():
        # Create DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        products_table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create S3 bucket with registry
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        s3.put_object(
            Bucket='test-bucket',
            Key='events/evt-001/registry.json',
            Body=REGISTRY_JSON.encode('utf-8'),
        )

        # Load handler inside mock context
        handler_module = _load_handler()

        yield {
            'events_table': events_table,
            'orders_table': orders_table,
            'products_table': products_table,
            's3': s3,
            'handler': handler_module,
        }


def _seed_event(events_table, event_id='evt-001', claims=None):
    """Insert an event record with registry config and optional claims."""
    events_table.put_item(Item={
        'event_id': event_id,
        'name': 'Test Event',
        'status': 'open',
        'registry_config': {
            's3_path': f'events/{event_id}/registry.json',
            'row_label': 'club',
            'claim_mode': 'first_come_first_served',
            'max_delegates_per_row': 2,
        },
        'registry_claims': claims or {},
    })


def _seed_order(orders_table, order_id, event_id='evt-001', status='draft',
                payment_status='unpaid', total_amount=0, total_paid=0, items=None):
    """Insert an order record."""
    orders_table.put_item(Item={
        'order_id': order_id,
        'event_id': event_id,
        'status': status,
        'payment_status': payment_status,
        'total_amount': Decimal(str(total_amount)),
        'total_paid': Decimal(str(total_paid)),
        'items': items or [],
    })


def _seed_product(products_table, product_id, name, event_id='evt-001', max_per_event=None):
    """Insert a product record."""
    item = {
        'product_id': product_id,
        'name': name,
        'event_id': event_id,
        'is_parent': True,
        'active': True,
    }
    if max_per_event is not None:
        item['purchase_rules'] = {'max_per_event': max_per_event}
    products_table.put_item(Item=item)


# --- Tests ---

class TestAdminAccess:
    """Test auth enforcement."""

    def test_non_admin_gets_403(self, setup_aws):
        """Non-admin user should get 403."""
        handler = setup_aws['handler']
        with _non_admin_auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        assert result['statusCode'] == 403

    def test_admin_gets_200(self, setup_aws):
        """Admin user should get 200 for valid event."""
        _seed_event(setup_aws['events_table'])
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        assert result['statusCode'] == 200

    def test_missing_event_id_gets_error(self, setup_aws):
        """Missing event_id should return 400 or equivalent error."""
        handler = setup_aws['handler']
        with _auth_patches():
            # With pathParameters containing no event_id key
            event = _make_event()
            event['pathParameters'] = {'event_id': ''}
            result = handler.lambda_handler(event, None)
        assert result['statusCode'] == 400

    def test_nonexistent_event_gets_404(self, setup_aws):
        """Non-existent event should return 404."""
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(event_id='no-such-event'), None)
        assert result['statusCode'] == 404

    def test_options_returns_cors(self, setup_aws):
        """OPTIONS should return CORS headers."""
        handler = setup_aws['handler']
        result = handler.lambda_handler(_make_event(method='OPTIONS'), None)
        assert result['statusCode'] == 200


class TestRegistrationStats:
    """Test total/claimed/unclaimed rows and registration percentage (Req 14.1)."""

    def test_no_claims(self, setup_aws):
        """All rows unclaimed → 0% registration."""
        _seed_event(setup_aws['events_table'])
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['total_rows'] == 5
        assert body['claimed_rows'] == 0
        assert body['unclaimed_rows'] == 5
        assert body['registration_pct'] == 0

    def test_partial_claims(self, setup_aws):
        """2 out of 5 claimed → 40%."""
        claims = {
            'row-1': {'member_id': 'm1', 'email': 'a@t.nl', 'name': 'A', 'claimed_at': '2025-01-01T00:00:00Z'},
            'row-3': {'member_id': 'm2', 'email': 'b@t.nl', 'name': 'B', 'claimed_at': '2025-01-01T00:00:00Z'},
        }
        _seed_event(setup_aws['events_table'], claims=claims)
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['total_rows'] == 5
        assert body['claimed_rows'] == 2
        assert body['unclaimed_rows'] == 3
        assert body['registration_pct'] == 40

    def test_all_claimed(self, setup_aws):
        """All 5 claimed → 100%."""
        claims = {
            f'row-{i}': {'member_id': f'm{i}', 'email': f'{i}@t.nl', 'name': f'U{i}', 'claimed_at': '2025-01-01T00:00:00Z'}
            for i in range(1, 6)
        }
        _seed_event(setup_aws['events_table'], claims=claims)
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['total_rows'] == 5
        assert body['claimed_rows'] == 5
        assert body['unclaimed_rows'] == 0
        assert body['registration_pct'] == 100


class TestOrderStatusBreakdown:
    """Test order status breakdown (Req 14.2)."""

    def test_empty_orders(self, setup_aws):
        """No orders → all counts zero."""
        _seed_event(setup_aws['events_table'])
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['orders_by_status'] == {'draft': 0, 'submitted': 0, 'locked': 0}

    def test_mixed_statuses(self, setup_aws):
        """Orders with mixed statuses aggregated correctly."""
        _seed_event(setup_aws['events_table'])
        orders_table = setup_aws['orders_table']
        _seed_order(orders_table, 'o1', status='draft')
        _seed_order(orders_table, 'o2', status='draft')
        _seed_order(orders_table, 'o3', status='submitted')
        _seed_order(orders_table, 'o4', status='locked')
        _seed_order(orders_table, 'o5', status='locked')
        _seed_order(orders_table, 'o6', status='locked')

        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['orders_by_status'] == {'draft': 2, 'submitted': 1, 'locked': 3}

    def test_cancelled_orders_excluded(self, setup_aws):
        """Cancelled orders should not appear in breakdown."""
        _seed_event(setup_aws['events_table'])
        orders_table = setup_aws['orders_table']
        _seed_order(orders_table, 'o1', status='submitted')
        # This cancelled order should use a different event_id approach
        # Since we filter by status != cancelled in the scan, it won't be returned
        orders_table.put_item(Item={
            'order_id': 'o-cancelled',
            'event_id': 'evt-001',
            'status': 'cancelled',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0'),
            'total_paid': Decimal('0'),
            'items': [],
        })

        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['orders_by_status'] == {'draft': 0, 'submitted': 1, 'locked': 0}


class TestPaymentBreakdown:
    """Test payment status breakdown and revenue (Req 14.3)."""

    def test_revenue_calculation(self, setup_aws):
        """Revenue collected/expected calculated from orders."""
        _seed_event(setup_aws['events_table'])
        orders_table = setup_aws['orders_table']
        # Submitted order, fully paid
        _seed_order(orders_table, 'o1', status='submitted', payment_status='paid',
                    total_amount=150, total_paid=150)
        # Locked order, partially paid
        _seed_order(orders_table, 'o2', status='locked', payment_status='partial',
                    total_amount=200, total_paid=100)
        # Draft order, unpaid (not counted in expected)
        _seed_order(orders_table, 'o3', status='draft', payment_status='unpaid',
                    total_amount=75, total_paid=0)

        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])

        assert body['orders_by_payment'] == {'unpaid': 1, 'partial': 1, 'paid': 1}
        # revenue_collected = 150 + 100 + 0 = 250
        assert body['revenue_collected'] == 250
        # revenue_expected = 150 (submitted) + 200 (locked) = 350 (draft not counted)
        assert body['revenue_expected'] == 350


class TestProductCapacity:
    """Test per-product capacity usage (Req 14.4)."""

    def test_product_capacity_aggregation(self, setup_aws):
        """Products with max_per_event show sold_count vs capacity."""
        _seed_event(setup_aws['events_table'])
        products_table = setup_aws['products_table']
        orders_table = setup_aws['orders_table']

        _seed_product(products_table, 'prod-1', 'Dinner Ticket', max_per_event=100)
        _seed_product(products_table, 'prod-2', 'T-Shirt', max_per_event=50)
        _seed_product(products_table, 'prod-3', 'Parking', max_per_event=None)  # No limit

        # Orders with items
        _seed_order(orders_table, 'o1', status='submitted', items=[
            {'product_id': 'prod-1', 'quantity': 3},
            {'product_id': 'prod-2', 'quantity': 1},
        ])
        _seed_order(orders_table, 'o2', status='draft', items=[
            {'product_id': 'prod-1', 'quantity': 2},
            {'product_id': 'prod-3', 'quantity': 5},
        ])

        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])

        # prod-3 has no max_per_event, so should not appear in capacity list
        capacity = {p['product_id']: p for p in body['product_capacity']}
        assert 'prod-1' in capacity
        assert 'prod-2' in capacity
        assert 'prod-3' not in capacity

        assert capacity['prod-1']['sold_count'] == 5  # 3 + 2
        assert capacity['prod-1']['max_per_event'] == 100
        assert capacity['prod-1']['product_name'] == 'Dinner Ticket'

        assert capacity['prod-2']['sold_count'] == 1
        assert capacity['prod-2']['max_per_event'] == 50

    def test_no_products_returns_empty_capacity(self, setup_aws):
        """Event with no products returns empty capacity list."""
        _seed_event(setup_aws['events_table'])
        handler = setup_aws['handler']
        with _auth_patches():
            result = handler.lambda_handler(_make_event(), None)
        body = json.loads(result['body'])
        assert body['product_capacity'] == []
