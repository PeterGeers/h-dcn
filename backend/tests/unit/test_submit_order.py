"""
Unit Tests for submit_order Lambda Handler.

Tests the unified submit_order handler:
- Returns 400 when order_id is missing
- Returns 404 when order doesn't exist
- Returns 403 when user is not order owner (and not delegate/admin)
- Returns 409 when order status is not "draft"
- Returns 400 when order has no items
- Webshop source: submits successfully with valid items
- Event source: returns 403 when event is not open
- Event source: submits successfully with valid items
- Event source: returns 400 with validation errors when items are invalid
- Optimistic locking: returns 409 on concurrent modification
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
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['COUNTERS_TABLE_NAME'] = 'Counters'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'submit_order', 'app.py')
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

TEST_EVENT_ID = 'evt-12345678-1234-1234-1234-123456789abc'
TEST_MEMBER_ID = 'mem-001'
TEST_MEMBER_EMAIL = 'user@h-dcn.nl'
TEST_OTHER_MEMBER_ID = 'mem-other'
TEST_OTHER_EMAIL = 'other@h-dcn.nl'
TEST_PRODUCT_ID = 'prod-001'
TEST_ORDER_ID = 'order-001'


def _make_event(order_id=None, method='POST'):
    """Create a minimal API Gateway event for submit_order."""
    path_params = {}
    if order_id:
        path_params['order_id'] = order_id
    return {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': path_params if path_params else None,
        'body': None,
    }


# ---------------------------------------------------------------------------
# Auth patches helper
# ---------------------------------------------------------------------------

def _auth_patches(email=TEST_MEMBER_EMAIL, roles=None):
    """Return a patch.multiple context for auth functions."""
    if roles is None:
        roles = ['hdcnLeden']
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, roles, None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _auth_patches_non_owner(email=TEST_OTHER_EMAIL, roles=None):
    """Auth patches for a different user (not the order owner, not admin)."""
    if roles is None:
        roles = ['hdcnLeden']

    def _validate_non_admin(roles, perms, email, region):
        """Allow events_read but deny admin (products_create)."""
        if 'products_create' in perms:
            return (False, None, {})
        return (True, None, {})

    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, roles, None),
        validate_permissions_with_regions=_validate_non_admin,
        log_successful_access=lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """
    Create mocked DynamoDB tables with correct schemas and GSI,
    seed test data, and load handler inside mock_aws context.
    """
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

        # Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Producten table
        producten_table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Counters table (used by generate_order_number)
        counters_table = dynamodb.create_table(
            TableName='Counters',
            KeySchema=[{'AttributeName': 'counter_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'counter_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed test member (owner)
        members_table.put_item(Item={
            'member_id': TEST_MEMBER_ID,
            'email': TEST_MEMBER_EMAIL,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'club_id': 'club-nl-001',
        })

        # Seed other member (non-owner)
        members_table.put_item(Item={
            'member_id': TEST_OTHER_MEMBER_ID,
            'email': TEST_OTHER_EMAIL,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'club_id': 'club-nl-002',
        })

        # Seed test product with order_item_fields
        producten_table.put_item(Item={
            'product_id': TEST_PRODUCT_ID,
            'name': 'Rally Dinner Ticket',
            'price': 45,
            'order_item_fields': [
                {
                    'id': 'guest_name',
                    'label': 'Naam gast',
                    'type': 'text',
                    'required': True,
                },
                {
                    'id': 'diet',
                    'label': 'Dieet',
                    'type': 'select',
                    'required': False,
                    'options': ['none', 'vegetarian', 'vegan'],
                },
            ],
        })

        # Seed test event (open, member-scoped)
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Test Rally 2025',
            'status': 'open',
            'order_scope': 'member',
            'product_ids': [TEST_PRODUCT_ID],
            'constraints': [],
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'events': events_table,
            'members': members_table,
            'producten': producten_table,
            'handler': handler,
        }


# ---------------------------------------------------------------------------
# Helper to seed a draft order
# ---------------------------------------------------------------------------

def _seed_draft_order(orders_table, order_id=TEST_ORDER_ID, member_id=TEST_MEMBER_ID,
                      source_id='webshop', items=None, version=1, status='draft',
                      delegates=None):
    """Seed an order into the Orders table."""
    item = {
        'order_id': order_id,
        'source_id': source_id,
        'member_id': member_id,
        'status': status,
        'items': items if items is not None else [],
        'version': version,
    }
    if delegates:
        item['delegates'] = delegates
    orders_table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Tests: Missing parameters
# ---------------------------------------------------------------------------

class TestMissingParameters:
    """Tests for missing required parameters."""

    def test_returns_400_when_order_id_is_missing(self, setup_tables):
        """Handler returns 400 when order_id path parameter is not provided."""
        handler = setup_tables['handler']

        with _auth_patches():
            event = _make_event(order_id=None)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'order' in body.get('error', '').lower() or 'id' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Order not found
# ---------------------------------------------------------------------------

class TestOrderNotFound:
    """Tests for non-existent order."""

    def test_returns_404_when_order_does_not_exist(self, setup_tables):
        """Returns 404 when order_id doesn't match any record."""
        handler = setup_tables['handler']

        with _auth_patches():
            event = _make_event(order_id='non-existent-order-999')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Ownership check
# ---------------------------------------------------------------------------

class TestOwnershipCheck:
    """Tests for order ownership verification."""

    def test_returns_403_when_user_is_not_order_owner(self, setup_tables):
        """Returns 403 when authenticated user is not the order owner and not admin/delegate."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft order owned by TEST_MEMBER_ID
        _seed_draft_order(
            orders_table,
            items=[{'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Test'}}],
        )

        # Request as a different user (not owner, not admin, not delegate)
        with _auth_patches_non_owner():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'owner' in body.get('error', '').lower() or 'denied' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Status check
# ---------------------------------------------------------------------------

class TestStatusCheck:
    """Tests for order status validation."""

    def test_returns_409_when_order_status_is_not_draft(self, setup_tables):
        """Returns 409 when order is already submitted."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed an order that's already submitted
        _seed_draft_order(
            orders_table,
            status='submitted',
            items=[{'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Test'}}],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'submit' in body.get('error', '').lower() or 'status' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Empty items
# ---------------------------------------------------------------------------

class TestEmptyItems:
    """Tests for orders with no items."""

    def test_returns_400_when_order_has_no_items(self, setup_tables):
        """Returns 400 when trying to submit an order with empty items list."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft order with no items
        _seed_draft_order(orders_table, items=[])

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no items' in body.get('error', '').lower() or 'items' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Webshop source - successful submission
# ---------------------------------------------------------------------------

class TestWebshopSubmit:
    """Tests for webshop source submission."""

    def test_submits_successfully_with_valid_items(self, setup_tables):
        """Webshop order with valid items transitions to submitted status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft webshop order with valid items
        _seed_draft_order(
            orders_table,
            source_id='webshop',
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'item_fields_data': {
                    'guest_name': 'John Doe',
                    'diet': 'none',
                },
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert body['order_id'] == TEST_ORDER_ID
        assert 'submitted_at' in body


# ---------------------------------------------------------------------------
# Tests: Event source
# ---------------------------------------------------------------------------

class TestEventSubmit:
    """Tests for event source submission."""

    def test_returns_403_when_event_is_not_open(self, setup_tables):
        """Returns 403 when event status is not 'open'."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        events_table = setup_tables['events']

        # Update event status to 'closed'
        events_table.update_item(
            Key={'event_id': TEST_EVENT_ID},
            UpdateExpression='SET #s = :val',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':val': 'closed'},
        )

        # Seed a draft event order with valid items
        _seed_draft_order(
            orders_table,
            source_id=TEST_EVENT_ID,
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'item_fields_data': {
                    'guest_name': 'Jane Doe',
                    'diet': 'vegetarian',
                },
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not open' in body.get('error', '').lower() or 'registration' in body.get('error', '').lower()

    def test_submits_successfully_with_valid_items(self, setup_tables):
        """Event order with valid items transitions to submitted status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft event order with valid items
        _seed_draft_order(
            orders_table,
            source_id=TEST_EVENT_ID,
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'item_fields_data': {
                    'guest_name': 'Jane Doe',
                    'diet': 'vegetarian',
                },
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert body['order_id'] == TEST_ORDER_ID
        assert 'submitted_at' in body

    def test_returns_400_with_validation_errors_for_invalid_items(self, setup_tables):
        """Returns 400 with validation errors when items have missing required fields."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft event order with INVALID items (missing required guest_name)
        _seed_draft_order(
            orders_table,
            source_id=TEST_EVENT_ID,
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'item_fields_data': {
                    # 'guest_name' is MISSING (required field)
                    'diet': 'vegan',
                },
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'errors' in body
        assert len(body['errors']) > 0
        # Check the error references the required field
        error_messages = [e.get('message', '') for e in body['errors']]
        assert any('guest_name' in msg.lower() or 'naam gast' in msg.lower() for msg in error_messages)


# ---------------------------------------------------------------------------
# Tests: Optimistic locking
# ---------------------------------------------------------------------------

class TestOptimisticLocking:
    """Tests for concurrent modification detection."""

    def test_returns_409_on_concurrent_modification(self, setup_tables):
        """Returns 409 when order was modified between read and update (version mismatch)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a draft webshop order with version 1
        _seed_draft_order(
            orders_table,
            source_id='webshop',
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'item_fields_data': {'guest_name': 'Test User'},
            }],
            version=1,
        )

        # Simulate concurrent modification: update version in the table
        # AFTER handler reads it but BEFORE it writes. We achieve this by
        # patching the _get_order to return version=1 but actual table has version=2.
        orders_table.update_item(
            Key={'order_id': TEST_ORDER_ID},
            UpdateExpression='SET version = :v',
            ExpressionAttributeValues={':v': 2},
        )

        # Now the handler will read version=2 from the table.
        # But the condition expression checks version = read_version.
        # If we set version=2 in the table BEFORE the handler reads it,
        # that's fine — it will use version=2 in the condition.
        # Instead, we need the handler to read an older version.
        # We patch _get_order to return the order with version=1.
        stale_order = {
            'order_id': TEST_ORDER_ID,
            'source_id': 'webshop',
            'member_id': TEST_MEMBER_ID,
            'status': 'draft',
            'items': [{'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Test User'}}],
            'version': 1,
        }

        with _auth_patches():
            with patch.object(handler, '_get_order', return_value=stale_order):
                event = _make_event(order_id=TEST_ORDER_ID)
                response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'concurrent' in body.get('error', '').lower() or 'modified' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Registry Row — sold count filtering and max_per_order validation
# Requirements: 5.5, 5.7
# ---------------------------------------------------------------------------

class TestRegistryRowSoldCounts:
    """Tests for _calculate_sold_counts filtering by registry_row_id."""

    def test_sold_counts_excludes_current_registry_row(self, setup_tables):
        """
        _calculate_sold_counts excludes orders matching the current registry_row_id.
        This ensures a row doesn't count its own submitted order against capacity.
        Validates: Requirements 5.5, 5.7
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed submitted orders for different registry rows
        orders_table.put_item(Item={
            'order_id': 'order-row-a',
            'source_id': TEST_EVENT_ID,
            'member_id': 'mem-a',
            'registry_row_id': 'row-amsterdam',
            'status': 'submitted',
            'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 3}],
            'version': 1,
        })
        orders_table.put_item(Item={
            'order_id': 'order-row-b',
            'source_id': TEST_EVENT_ID,
            'member_id': 'mem-b',
            'registry_row_id': 'row-rotterdam',
            'status': 'submitted',
            'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 5}],
            'version': 1,
        })
        orders_table.put_item(Item={
            'order_id': 'order-row-c',
            'source_id': TEST_EVENT_ID,
            'member_id': 'mem-c',
            'registry_row_id': 'row-amsterdam',
            'status': 'submitted',
            'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 2}],
            'version': 1,
        })

        # Query all orders for the source
        all_orders = [
            {'order_id': 'order-row-a', 'source_id': TEST_EVENT_ID, 'registry_row_id': 'row-amsterdam', 'status': 'submitted', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 3}]},
            {'order_id': 'order-row-b', 'source_id': TEST_EVENT_ID, 'registry_row_id': 'row-rotterdam', 'status': 'submitted', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 5}]},
            {'order_id': 'order-row-c', 'source_id': TEST_EVENT_ID, 'registry_row_id': 'row-amsterdam', 'status': 'submitted', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 2}]},
        ]

        # When current_registry_row_id is 'row-amsterdam', only row-rotterdam's counts remain
        sold_counts = handler._calculate_sold_counts(all_orders, 'row-amsterdam')
        assert sold_counts.get(TEST_PRODUCT_ID, 0) == 5

    def test_sold_counts_includes_all_when_no_registry_row_id(self, setup_tables):
        """
        When current_registry_row_id is None, all submitted/locked orders are counted.
        This is the member-scoped case (no row filtering).
        Validates: Requirements 5.5
        """
        handler = setup_tables['handler']

        all_orders = [
            {'order_id': 'order-1', 'status': 'submitted', 'registry_row_id': 'row-x', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 2}]},
            {'order_id': 'order-2', 'status': 'submitted', 'registry_row_id': 'row-y', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 3}]},
            {'order_id': 'order-3', 'status': 'draft', 'registry_row_id': 'row-x', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 10}]},
        ]

        sold_counts = handler._calculate_sold_counts(all_orders, None)
        # Only submitted/locked orders counted, draft excluded
        assert sold_counts.get(TEST_PRODUCT_ID, 0) == 5

    def test_sold_counts_only_counts_submitted_and_locked(self, setup_tables):
        """
        Draft and cancelled orders are never counted in sold counts.
        Validates: Requirements 5.5
        """
        handler = setup_tables['handler']

        all_orders = [
            {'order_id': 'o-1', 'status': 'submitted', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 1}]},
            {'order_id': 'o-2', 'status': 'locked', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 2}]},
            {'order_id': 'o-3', 'status': 'draft', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 99}]},
            {'order_id': 'o-4', 'status': 'cancelled', 'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 99}]},
        ]

        sold_counts = handler._calculate_sold_counts(all_orders, None)
        assert sold_counts.get(TEST_PRODUCT_ID, 0) == 3


class TestMaxPerOrderValidation:
    """Tests for max_per_order purchase_rules enforcement."""

    def test_max_per_order_rejects_exceeding_quantity(self, setup_tables):
        """
        Returns 400 when order quantity exceeds max_per_order from purchase_rules.
        Validates: Requirements 5.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        producten_table = setup_tables['producten']

        # Update product with max_per_order = 2
        producten_table.update_item(
            Key={'product_id': TEST_PRODUCT_ID},
            UpdateExpression='SET purchase_rules = :pr',
            ExpressionAttributeValues={':pr': {'max_per_order': 2}},
        )

        # Seed a draft event order with 3 items (exceeds max_per_order)
        _seed_draft_order(
            orders_table,
            source_id=TEST_EVENT_ID,
            items=[
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 1'}},
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 2'}},
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 3'}},
            ],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'errors' in body
        # Check there's an error about max_per_order (field is 'purchase_rules' per shared validation)
        error_messages = ' '.join(e.get('message', '') for e in body['errors'])
        assert 'max_per_order' in error_messages

    def test_max_per_order_allows_within_limit(self, setup_tables):
        """
        Submission succeeds when quantity is within max_per_order limit.
        Validates: Requirements 5.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        producten_table = setup_tables['producten']

        # Update product with max_per_order = 3
        producten_table.update_item(
            Key={'product_id': TEST_PRODUCT_ID},
            UpdateExpression='SET purchase_rules = :pr',
            ExpressionAttributeValues={':pr': {'max_per_order': 3}},
        )

        # Seed a draft event order with exactly 3 items (at limit)
        _seed_draft_order(
            orders_table,
            source_id=TEST_EVENT_ID,
            items=[
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 1'}},
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 2'}},
                {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': 'Person 3'}},
            ],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_max_per_order_absent_means_unlimited(self, setup_tables):
        """
        When max_per_order is not set in purchase_rules, no limit is enforced.
        Validates: Requirements 5.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        producten_table = setup_tables['producten']

        # Ensure product has no purchase_rules with max_per_order
        producten_table.update_item(
            Key={'product_id': TEST_PRODUCT_ID},
            UpdateExpression='SET purchase_rules = :pr',
            ExpressionAttributeValues={':pr': {}},
        )

        # Seed a draft event order with many items
        items = [
            {'product_id': TEST_PRODUCT_ID, 'item_fields_data': {'guest_name': f'Person {i}'}}
            for i in range(10)
        ]
        _seed_draft_order(orders_table, source_id=TEST_EVENT_ID, items=items)

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
