"""
Property-Based Tests for Order Deduplication (Property 25).

Tests that for any (club_id, event_id) pair, calling create_order SHALL:
- Return the existing non-cancelled order with HTTP 200 if one exists
- Create a new order with HTTP 201 if none exists
- After any number of create_order calls for the same pair,
  exactly one non-cancelled order SHALL exist.

File: backend/tests/unit/test_order_deduplication_properties.py

**Validates: Requirements 18.1, 18.2, 18.4**
"""

import os
import sys
import json
import importlib.util
from decimal import Decimal

import boto3
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws
from unittest.mock import patch

# --- Environment setup for tests ---

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'

# --- Load handler module via importlib (per testing-backend.md steering) ---

_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'create_order', 'app.py'
    )
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    if 'create_order_app' in sys.modules:
        del sys.modules['create_order_app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('create_order_app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['create_order_app'] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for club IDs (row IDs from the registry)
club_id_strategy = st.from_regex(r'club_[a-z0-9]{4,10}', fullmatch=True)

# Strategy for event IDs
event_id_strategy = st.from_regex(r'evt_[a-z0-9]{6,12}', fullmatch=True)

# Strategy for member IDs (UUIDs)
member_id_strategy = st.from_regex(
    r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',
    fullmatch=True,
)

# Strategy for email addresses
email_strategy = st.from_regex(r'[a-z]{3,8}@[a-z]{3,6}\.[a-z]{2,3}', fullmatch=True)

# Strategy for the number of repeated calls (2-5 is enough to prove idempotency)
repeat_count_strategy = st.integers(min_value=2, max_value=5)


# =============================================================================
# Helpers
# =============================================================================

def _make_api_event(body: dict) -> dict:
    """Create a minimal API Gateway event."""
    return {
        "httpMethod": "POST",
        "path": "/orders",
        "headers": {"Authorization": "Bearer test-token"},
        "queryStringParameters": None,
        "body": json.dumps(body),
        "requestContext": {"apiId": "test", "stage": "Prod"},
    }


def _auth_patches(user_email: str, club_id: str):
    """Create auth patch context that mocks auth functions on the handler module."""
    return patch.multiple(
        'create_order_app',
        extract_user_credentials=lambda event: (user_email, ['event_participant', 'hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region=None: (False, None, None),
        log_successful_access=lambda *a, **kw: None,
        get_registry_row_id=lambda email: club_id,
    )


def _count_non_cancelled_orders(orders_table, club_id: str, event_id: str) -> int:
    """Count non-cancelled orders for a (club_id, event_id) pair."""
    from boto3.dynamodb.conditions import Attr

    filter_expr = (
        Attr('club_id').eq(club_id)
        & Attr('event_id').eq(event_id)
        & Attr('status').ne('cancelled')
    )
    response = orders_table.scan(FilterExpression=filter_expr)
    items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))
    return len(items)


# =============================================================================
# Property 25: Order Deduplication
# =============================================================================

class TestProperty25OrderDeduplication:
    """
    # Feature: closed-community-booking, Property 25: Order Deduplication

    **Validates: Requirements 18.1, 18.2, 18.4**

    For any (club_id, event_id) pair, calling create_order SHALL:
    return the existing non-cancelled order with HTTP 200 if one exists,
    or create a new order with HTTP 201 if none exists. After any number
    of create_order calls for the same pair, exactly one non-cancelled
    order SHALL exist.
    """

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        email=email_strategy,
        repeat_count=repeat_count_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_repeated_calls_yield_exactly_one_non_cancelled_order(
        self, club_id: str, event_id: str, member_id: str,
        email: str, repeat_count: int,
    ):
        """
        **Validates: Requirements 18.1, 18.2, 18.4**

        After N repeated create_order calls for the same (club_id, event_id),
        exactly one non-cancelled order SHALL exist in the Orders table.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            # Create Orders table
            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Create Members table with a member record
            members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            members_table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'club_id': club_id,
            })

            # Create Producten table (empty — no items in requests)
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Load handler inside mock_aws context
            handler_module = _load_handler()
            handler_module.orders_table = orders_table
            handler_module.members_table = members_table

            with _auth_patches(email, club_id):
                api_event = _make_api_event({
                    'event_id': event_id,
                    'club_id': club_id,
                    'items': [],
                })

                # First call — should create (201)
                response1 = handler_module.lambda_handler(api_event, None)
                assert response1['statusCode'] == 201, (
                    f"First call should create order (201), got {response1['statusCode']}"
                )

                body1 = json.loads(response1['body'])
                order1 = body1.get('data', body1)
                first_order_id = order1['order_id']

                # Repeated calls — should return existing (200)
                for i in range(repeat_count - 1):
                    response = handler_module.lambda_handler(api_event, None)
                    assert response['statusCode'] == 200, (
                        f"Call {i+2} should return existing order (200), "
                        f"got {response['statusCode']}"
                    )
                    body = json.loads(response['body'])
                    order = body.get('data', body)
                    assert order['order_id'] == first_order_id, (
                        f"Call {i+2} returned different order_id: "
                        f"{order['order_id']} != {first_order_id}"
                    )

                # Verify exactly one non-cancelled order exists
                count = _count_non_cancelled_orders(orders_table, club_id, event_id)
                assert count == 1, (
                    f"Expected exactly 1 non-cancelled order for "
                    f"(club_id={club_id}, event_id={event_id}), got {count}"
                )

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        email=email_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_first_call_creates_new_order_with_201(
        self, club_id: str, event_id: str, member_id: str, email: str,
    ):
        """
        **Validates: Requirements 18.1, 18.4**

        When no non-cancelled order exists for (club_id, event_id),
        create_order SHALL create a new order and return HTTP 201.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            members_table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'club_id': club_id,
            })

            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler_module = _load_handler()
            handler_module.orders_table = orders_table
            handler_module.members_table = members_table

            with _auth_patches(email, club_id):
                api_event = _make_api_event({
                    'event_id': event_id,
                    'club_id': club_id,
                    'items': [],
                })

                response = handler_module.lambda_handler(api_event, None)
                assert response['statusCode'] == 201

                body = json.loads(response['body'])
                order = body.get('data', body)
                assert order['status'] == 'draft'
                assert order['event_id'] == event_id
                assert order['club_id'] == club_id

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        email=email_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_existing_order_returned_with_200(
        self, club_id: str, event_id: str, member_id: str, email: str,
    ):
        """
        **Validates: Requirements 18.2, 18.4**

        When a non-cancelled order already exists for (club_id, event_id),
        create_order SHALL return it with HTTP 200.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            members_table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'club_id': club_id,
            })

            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Pre-seed an existing non-cancelled order
            existing_order_id = 'existing-order-12345'
            orders_table.put_item(Item={
                'order_id': existing_order_id,
                'event_id': event_id,
                'club_id': club_id,
                'member_id': member_id,
                'user_email': email.lower(),
                'status': 'draft',
                'payment_status': 'unpaid',
                'items': [],
                'total_amount': Decimal('0'),
                'total_paid': Decimal('0'),
                'version': 2,
                'created_at': '2025-01-01T00:00:00+00:00',
                'updated_at': '2025-01-01T00:00:00+00:00',
            })

            handler_module = _load_handler()
            handler_module.orders_table = orders_table
            handler_module.members_table = members_table

            with _auth_patches(email, club_id):
                api_event = _make_api_event({
                    'event_id': event_id,
                    'club_id': club_id,
                    'items': [],
                })

                response = handler_module.lambda_handler(api_event, None)
                assert response['statusCode'] == 200, (
                    f"Expected 200 for existing order, got {response['statusCode']}"
                )

                body = json.loads(response['body'])
                order = body.get('data', body)
                assert order['order_id'] == existing_order_id

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        email=email_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cancelled_order_ignored_new_order_created(
        self, club_id: str, event_id: str, member_id: str, email: str,
    ):
        """
        **Validates: Requirements 18.1, 18.4**

        A cancelled order for (club_id, event_id) SHALL be ignored;
        a new draft order SHALL be created with HTTP 201.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            members_table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'club_id': club_id,
            })

            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Pre-seed a CANCELLED order — should be ignored
            orders_table.put_item(Item={
                'order_id': 'cancelled-order-99999',
                'event_id': event_id,
                'club_id': club_id,
                'member_id': member_id,
                'user_email': email.lower(),
                'status': 'cancelled',
                'payment_status': 'unpaid',
                'items': [],
                'total_amount': Decimal('0'),
                'total_paid': Decimal('0'),
                'version': 1,
                'created_at': '2025-01-01T00:00:00+00:00',
                'updated_at': '2025-01-01T00:00:00+00:00',
            })

            handler_module = _load_handler()
            handler_module.orders_table = orders_table
            handler_module.members_table = members_table

            with _auth_patches(email, club_id):
                api_event = _make_api_event({
                    'event_id': event_id,
                    'club_id': club_id,
                    'items': [],
                })

                response = handler_module.lambda_handler(api_event, None)
                assert response['statusCode'] == 201, (
                    f"Expected 201 (new order) when only cancelled exists, "
                    f"got {response['statusCode']}"
                )

                body = json.loads(response['body'])
                order = body.get('data', body)
                assert order['order_id'] != 'cancelled-order-99999'
                assert order['status'] == 'draft'
