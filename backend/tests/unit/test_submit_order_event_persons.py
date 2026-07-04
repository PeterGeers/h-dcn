"""
Unit Tests for submit_order event persons validation (Requirements 9.1-9.9).

Tests the _validate_event_persons function which validates:
- Person name non-empty (Req 9.1)
- item_fields_data.name populated (Req 9.2)
- Required order_item_fields filled (Req 9.3)
- max_per_club limits (Req 9.4)
- max_per_event capacity (Req 9.5, 9.9)
- Variant validity (Req 9.6)
- Status transition draft → submitted (Req 9.7)
- Grouped per-person error messages (Req 9.8)
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from decimal import Decimal

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['COUNTERS_TABLE_NAME'] = 'Counters'

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

TEST_EVENT_ID = 'evt-99999999-aaaa-bbbb-cccc-000000000001'
TEST_MEMBER_ID = 'mem-persons-001'
TEST_MEMBER_EMAIL = 'delegate@h-dcn.nl'
TEST_PRODUCT_ID = 'prod-dinner'
TEST_PRODUCT_ID_2 = 'prod-shirt'
TEST_VARIANT_ID = 'var-dinner-001'
TEST_ORDER_ID = 'order-persons-001'
TEST_CLUB_ID = 'club-amsterdam'


def _make_event(order_id=None, method='POST'):
    """Create a minimal API Gateway event."""
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


def _auth_patches(email=TEST_MEMBER_EMAIL, roles=None):
    """Auth patches for the order owner."""
    if roles is None:
        roles = ['event_participant']
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, roles, None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and seed test data."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Orders table with GSI
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
                {'AttributeName': 'source_id', 'AttributeType': 'S'},
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'event-member-index',
                'KeySchema': [
                    {'AttributeName': 'source_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'member_id', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }],
            BillingMode='PAY_PER_REQUEST',
        )

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        producten_table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        counters_table = dynamodb.create_table(
            TableName='Counters',
            KeySchema=[{'AttributeName': 'counter_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'counter_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed member
        members_table.put_item(Item={
            'member_id': TEST_MEMBER_ID,
            'email': TEST_MEMBER_EMAIL,
            'member_type': TEST_EVENT_ID,
            'allowed_events': [TEST_EVENT_ID],
            'club_id': TEST_CLUB_ID,
        })

        # Seed products
        producten_table.put_item(Item={
            'product_id': TEST_PRODUCT_ID,
            'name': 'Gala Dinner',
            'price': Decimal('55'),
            'is_parent': True,
            'order_item_fields': [
                {'id': 'dietary', 'label': 'Dieetwensen', 'type': 'text', 'required': True},
                {'id': 'notes', 'label': 'Opmerkingen', 'type': 'text', 'required': False},
            ],
            'purchase_rules': {
                'max_per_club': Decimal('5'),
                'max_per_event': Decimal('20'),
            },
        })

        producten_table.put_item(Item={
            'product_id': TEST_PRODUCT_ID_2,
            'name': 'Event T-Shirt',
            'price': Decimal('25'),
            'is_parent': True,
            'order_item_fields': [],
            'purchase_rules': {
                'max_per_club': Decimal('10'),
            },
        })

        # Seed variant (valid variant for dinner product)
        producten_table.put_item(Item={
            'product_id': TEST_VARIANT_ID,
            'name': 'Gala Dinner - Table A',
            'parent_id': TEST_PRODUCT_ID,
            'price': Decimal('55'),
            'variant_attributes': {'table': 'A'},
        })

        # Seed event
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Gala Event 2025',
            'status': 'open',
            'product_ids': [TEST_PRODUCT_ID, TEST_PRODUCT_ID_2],
            'constraints': [],
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'events': events_table,
            'members': members_table,
            'producten': producten_table,
            'counters': counters_table,
            'handler': handler,
        }


def _seed_event_order(orders_table, persons, items, order_id=TEST_ORDER_ID,
                      club_id=TEST_CLUB_ID, status='draft', version=1):
    """Seed a draft event order with persons structure."""
    orders_table.put_item(Item={
        'order_id': order_id,
        'source_id': TEST_EVENT_ID,
        'event_id': TEST_EVENT_ID,
        'member_id': TEST_MEMBER_ID,
        'club_id': club_id,
        'status': status,
        'version': version,
        'persons': persons,
        'items': items,
        'delegates': {
            'primary': TEST_MEMBER_EMAIL,
            'primary_member_id': TEST_MEMBER_ID,
        },
    })


# ---------------------------------------------------------------------------
# Tests: Person Name Validation (Req 9.1)
# ---------------------------------------------------------------------------

class TestPersonNameValidation:
    """Req 9.1: Validate every person has a non-empty name."""

    def test_rejects_empty_person_name(self, setup_tables):
        """Returns 400 when a person has empty name."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': '', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': 'test', 'dietary': 'none'},
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'name' for e in errors)

    def test_rejects_whitespace_only_person_name(self, setup_tables):
        """Returns 400 when a person has whitespace-only name."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': '   ', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': '   ', 'dietary': 'none'},
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'name' for e in errors)


# ---------------------------------------------------------------------------
# Tests: item_fields_data.name Validation (Req 9.2)
# ---------------------------------------------------------------------------

class TestItemFieldsNameValidation:
    """Req 9.2: Validate item_fields_data.name populated on every line."""

    def test_rejects_missing_item_fields_name(self, setup_tables):
        """Returns 400 when item_fields_data.name is missing."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': 'Alice', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'dietary': 'vegan'},  # 'name' missing
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'item_fields_data.name' for e in errors)


# ---------------------------------------------------------------------------
# Tests: Required order_item_fields (Req 9.3)
# ---------------------------------------------------------------------------

class TestRequiredFieldsValidation:
    """Req 9.3: Validate all required order_item_fields filled."""

    def test_rejects_missing_required_field(self, setup_tables):
        """Returns 400 when a required order_item_field is missing."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': 'Bob', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': 'Bob'},  # 'dietary' required but missing
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'dietary' for e in errors)


# ---------------------------------------------------------------------------
# Tests: max_per_club Validation (Req 9.4)
# ---------------------------------------------------------------------------

class TestMaxPerClubValidation:
    """Req 9.4: Validate per-order quantity limits not exceeded."""

    def test_rejects_exceeding_max_per_club(self, setup_tables):
        """Returns 400 when product quantity exceeds max_per_club."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # max_per_club for TEST_PRODUCT_ID is 5; create 6 items
        persons = [{'name': f'Person {i}', 'person_index': i} for i in range(6)]
        items = [{
            'product_id': TEST_PRODUCT_ID,
            'person_index': i,
            'quantity': 1,
            'item_fields_data': {'name': f'Person {i}', 'dietary': 'none'},
            'unit_price': Decimal('55'),
            'line_total': Decimal('55'),
        } for i in range(6)]

        _seed_event_order(orders_table, persons=persons, items=items)

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'max_per_order' for e in errors)


# ---------------------------------------------------------------------------
# Tests: max_per_event Validation (Req 9.5, 9.9)
# ---------------------------------------------------------------------------

class TestMaxPerEventValidation:
    """Req 9.5, 9.9: Validate per-event capacity via Sold_Count."""

    def test_rejects_exceeding_max_per_event(self, setup_tables):
        """Returns 400 when event capacity is exceeded."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # max_per_event for TEST_PRODUCT_ID is 20.
        # Seed 18 sold items from another club's submitted order.
        orders_table.put_item(Item={
            'order_id': 'order-other-club',
            'source_id': TEST_EVENT_ID,
            'event_id': TEST_EVENT_ID,
            'member_id': 'mem-other',
            'club_id': 'club-other',
            'status': 'submitted',
            'version': 1,
            'items': [{'product_id': TEST_PRODUCT_ID, 'quantity': 1,
                       'item_fields_data': {'name': f'Guest {i}', 'dietary': 'n'},
                       'unit_price': Decimal('55'), 'line_total': Decimal('55'),
                       'person_index': i} for i in range(18)],
        })

        # Now try to submit with 3 items (18 + 3 = 21 > 20)
        persons = [{'name': f'Guest {i}', 'person_index': i} for i in range(3)]
        items = [{
            'product_id': TEST_PRODUCT_ID,
            'person_index': i,
            'quantity': 1,
            'item_fields_data': {'name': f'Guest {i}', 'dietary': 'none'},
            'unit_price': Decimal('55'),
            'line_total': Decimal('55'),
        } for i in range(3)]

        _seed_event_order(orders_table, persons=persons, items=items)

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        capacity_errors = [e for e in errors if e['field'] == 'max_per_event']
        assert len(capacity_errors) >= 1
        # Should include remaining capacity info (Req 9.9)
        assert capacity_errors[0].get('remaining') == 2


# ---------------------------------------------------------------------------
# Tests: Variant Validity (Req 9.6)
# ---------------------------------------------------------------------------

class TestVariantValidation:
    """Req 9.6: Validate variant_id references exist."""

    def test_rejects_invalid_variant_id(self, setup_tables):
        """Returns 400 when variant_id doesn't exist."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': 'Alice', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'variant_id': 'nonexistent-variant-id',
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': 'Alice', 'dietary': 'none'},
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'variant_id' for e in errors)

    def test_rejects_variant_from_wrong_product(self, setup_tables):
        """Returns 400 when variant belongs to a different product."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Use valid variant but reference it from wrong product
        _seed_event_order(orders_table,
            persons=[{'name': 'Alice', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID_2,  # Shirt product
                'variant_id': TEST_VARIANT_ID,     # Dinner variant!
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': 'Alice'},
                'unit_price': Decimal('25'),
                'line_total': Decimal('25'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        assert any(e['field'] == 'variant_id' for e in errors)


# ---------------------------------------------------------------------------
# Tests: Successful Submission (Req 9.7)
# ---------------------------------------------------------------------------

class TestSuccessfulSubmission:
    """Req 9.7: Transition draft → submitted when all validations pass."""

    def test_submits_valid_order_with_persons(self, setup_tables):
        """Valid order with persons transitions to submitted status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[{'name': 'Alice', 'person_index': 0}],
            items=[{
                'product_id': TEST_PRODUCT_ID,
                'person_index': 0,
                'quantity': 1,
                'item_fields_data': {'name': 'Alice', 'dietary': 'vegetarian'},
                'unit_price': Decimal('55'),
                'line_total': Decimal('55'),
            }],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert 'submitted_at' in body


# ---------------------------------------------------------------------------
# Tests: Grouped Error Messages (Req 9.8)
# ---------------------------------------------------------------------------

class TestGroupedErrors:
    """Req 9.8: Return errors grouped per person."""

    def test_returns_errors_with_person_index(self, setup_tables):
        """Errors include person_index for grouping."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        _seed_event_order(orders_table,
            persons=[
                {'name': '', 'person_index': 0},
                {'name': 'Bob', 'person_index': 1},
            ],
            items=[
                {
                    'product_id': TEST_PRODUCT_ID,
                    'person_index': 0,
                    'quantity': 1,
                    'item_fields_data': {'name': '', 'dietary': 'none'},
                    'unit_price': Decimal('55'),
                    'line_total': Decimal('55'),
                },
                {
                    'product_id': TEST_PRODUCT_ID,
                    'person_index': 1,
                    'quantity': 1,
                    'item_fields_data': {'name': 'Bob', 'dietary': 'none'},
                    'unit_price': Decimal('55'),
                    'line_total': Decimal('55'),
                },
            ],
        )

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body.get('errors', [])
        # Errors for person 0 should have person_index=0
        person_0_errors = [e for e in errors if e.get('person_index') == 0]
        assert len(person_0_errors) >= 1
        # Person 1 (Bob, valid) should not have name errors
        person_1_name_errors = [
            e for e in errors
            if e.get('person_index') == 1 and e.get('field') == 'name'
        ]
        assert len(person_1_name_errors) == 0
