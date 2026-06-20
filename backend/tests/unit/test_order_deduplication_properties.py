"""
Property-Based Tests for Order Deduplication (Property 25)

Tests the create_order handler's deduplication logic: for any (club_id, event_id)
pair, repeated create_order calls always yield exactly one non-cancelled order.

**Validates: Requirements 18.1, 18.2, 18.4**

Uses Hypothesis for property-based testing with moto for DynamoDB mocking.
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, note, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws

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

# Strategy for club IDs (row_id from registry)
club_id_strategy = st.from_regex(r'row_[a-z0-9]{4,10}', fullmatch=True)

# Strategy for event IDs
event_id_strategy = st.from_regex(r'evt_[a-z0-9]{6,12}', fullmatch=True)

# Strategy for member IDs (UUIDs)
member_id_strategy = st.from_regex(
    r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',
    fullmatch=True
)

# Strategy for email addresses
email_local_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), min_codepoint=48, max_codepoint=122),
    min_size=2,
    max_size=20,
).filter(lambda s: '@' not in s and len(s) >= 2)

email_domain_strategy = st.from_regex(r'[a-z]{2,8}\.[a-z]{2,4}', fullmatch=True)

email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}",
    email_local_strategy,
    email_domain_strategy,
)

# Strategy for number of repeated calls (2-5 calls to test idempotency)
repeat_count_strategy = st.integers(min_value=2, max_value=5)


# =============================================================================
# Test Helpers
# =============================================================================

def _create_tables(dynamodb):
    """Create the DynamoDB tables needed by create_order handler."""
    # Orders table
    dynamodb.create_table(
        TableName='Orders',
        KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )

    # Members table
    dynamodb.create_table(
        TableName='Members',
        KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )

    # Producten table
    dynamodb.create_table(
        TableName='Producten',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


def _seed_member(dynamodb, member_id: str, email: str, club_id: str):
    """Insert a member record into the mocked Members table."""
    table = dynamodb.Table('Members')
    table.put_item(Item={
        'member_id': member_id,
        'email': email.lower(),
        'name': 'Test User',
        'club_id': club_id,
        'allowed_events': [],
    })


def _build_event(user_email: str, club_id: str, event_id: str):
    """Build an API Gateway event for POST /orders."""
    body = json.dumps({
        'event_id': event_id,
        'club_id': club_id,
        'items': [],
    })
    return {
        'httpMethod': 'POST',
        'body': body,
        'headers': {
            'Authorization': 'Bearer test-token',
        },
        'requestContext': {},
    }


def _auth_patches(user_email: str):
    """Create auth patches that simulate an authenticated event participant."""
    return patch.multiple(
        'create_order_app',
        extract_user_credentials=lambda event: (user_email, ['event_participant', 'hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region=None: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _count_non_cancelled_orders(dynamodb, club_id: str, event_id: str) -> int:
    """Count non-cancelled orders for a (club_id, event_id) pair via direct table scan."""
    table = dynamodb.Table('Orders')
    from boto3.dynamodb.conditions import Attr
    response = table.scan(
        FilterExpression=(
            Attr('club_id').eq(club_id)
            & Attr('event_id').eq(event_id)
            & Attr('status').ne('cancelled')
        )
    )
    return len(response.get('Items', []))


# =============================================================================
# Property 25: Order Deduplication
# =============================================================================

class TestProperty25OrderDeduplication:
    """
    # Feature: closed-community-booking, Property 25: Order Deduplication

    **Validates: Requirements 18.1, 18.2, 18.4**

    For any (club_id, event_id) pair, calling create_order SHALL:
    - Return the existing non-cancelled order with HTTP 200 if one exists
    - Create a new order with HTTP 201 if none exists
    After any number of create_order calls for the same pair, exactly one
    non-cancelled order SHALL exist.
    """

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        user_email=email_strategy,
        num_calls=repeat_count_strategy,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_repeated_calls_yield_exactly_one_non_cancelled_order(
        self, club_id: str, event_id: str, member_id: str,
        user_email: str, num_calls: int,
    ):
        """
        **Validates: Requirements 18.1, 18.2, 18.4**

        Repeated create_order calls for the same (club_id, event_id) always
        yield exactly one non-cancelled order in the database.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)
            _seed_member(dynamodb, member_id, user_email, club_id)

            # Reload handler inside mock_aws context
            handler_module = _load_handler()

            api_event = _build_event(user_email, club_id, event_id)

            with _auth_patches(user_email):
                responses = []
                for i in range(num_calls):
                    response = handler_module.lambda_handler(api_event, {})
                    responses.append(response)

            # Property: exactly one non-cancelled order exists
            count = _count_non_cancelled_orders(dynamodb, club_id, event_id)
            assert count == 1, (
                f"Expected exactly 1 non-cancelled order for "
                f"club_id={club_id}, event_id={event_id}, "
                f"got {count} after {num_calls} calls"
            )

            note(f"Made {num_calls} calls, found {count} non-cancelled order(s)")

    @given(
        club_id=club_id_strategy,
        event_id=event_id_strategy,
        member_id=member_id_strategy,
        user_email=email_strategy,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_first_call_returns_201_subsequent_return_200(
        self, club_id: str, event_id: str, member_id: str, user_email: str,
    ):
        """
        **Validates: Requirements 18.1, 18.2, 18.4**

        The first create_order call returns HTTP 201 (new order created).
        Subsequent calls for the same (club_id, event_id) return HTTP 200
        (existing order returned).
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)
            _seed_member(dynamodb, member_id, user_email, club_id)

            handler_module = _load_handler()

            api_event = _build_event(user_email, club_id, event_id)

            with _auth_patches(user_email):
                # First call: should create a new order (201)
                first_response = handler_module.lambda_handler(api_event, {})
                assert first_response['statusCode'] == 201, (
                    f"First call should return 201, got {first_response['statusCode']}"
                )

                first_body = json.loads(first_response['body'])
                first_order_id = first_body['order_id']

                # Second call: should return existing order (200)
                second_response = handler_module.lambda_handler(api_event, {})
                assert second_response['statusCode'] == 200, (
                    f"Second call should return 200, got {second_response['statusCode']}"
                )

                second_body = json.loads(second_response['body'])
                second_order_id = second_body['order_id']

                # Same order is returned
                assert first_order_id == second_order_id, (
                    f"Expected same order_id on dedup, "
                    f"got {first_order_id} vs {second_order_id}"
                )

            note(f"Order {first_order_id} returned consistently")

    @given(
        club_id=club_id_strategy,
        event_id_a=event_id_strategy,
        event_id_b=event_id_strategy,
        member_id=member_id_strategy,
        user_email=email_strategy,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_different_events_get_separate_orders(
        self, club_id: str, event_id_a: str, event_id_b: str,
        member_id: str, user_email: str,
    ):
        """
        **Validates: Requirements 18.1, 18.2, 18.4**

        Orders for different event_ids (same club_id) are independent —
        deduplication is scoped to (club_id, event_id) pairs.
        """
        assume(event_id_a != event_id_b)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)
            _seed_member(dynamodb, member_id, user_email, club_id)

            handler_module = _load_handler()

            event_a = _build_event(user_email, club_id, event_id_a)
            event_b = _build_event(user_email, club_id, event_id_b)

            with _auth_patches(user_email):
                resp_a = handler_module.lambda_handler(event_a, {})
                resp_b = handler_module.lambda_handler(event_b, {})

            assert resp_a['statusCode'] == 201, (
                f"First event order should return 201, got {resp_a['statusCode']}"
            )
            assert resp_b['statusCode'] == 201, (
                f"Second event order should return 201, got {resp_b['statusCode']}"
            )

            body_a = json.loads(resp_a['body'])
            body_b = json.loads(resp_b['body'])
            assert body_a['order_id'] != body_b['order_id'], (
                "Different events should produce different orders"
            )

            # Each event has exactly one non-cancelled order
            count_a = _count_non_cancelled_orders(dynamodb, club_id, event_id_a)
            count_b = _count_non_cancelled_orders(dynamodb, club_id, event_id_b)
            assert count_a == 1
            assert count_b == 1

            note(f"Event A order: {body_a['order_id']}, Event B order: {body_b['order_id']}")
