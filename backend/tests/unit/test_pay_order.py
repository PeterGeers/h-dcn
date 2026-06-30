"""
Unit Tests for pay_order Lambda Handler — registry_row_id on payment records.

Tests:
- Payment record includes registry_row_id from the order (event order)
- Payment record does NOT include registry_row_id for webshop orders

Requirements: 1.5
"""

import importlib.util
import json
import os
import sys
from decimal import Decimal

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
os.environ['PAYMENTS_TABLE_NAME'] = 'Payments'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['MOLLIE_API_KEY'] = ''  # Empty = mock mode
os.environ['PAYMENT_REDIRECT_URL'] = 'https://portal.h-dcn.nl'
os.environ['MOLLIE_WEBHOOK_URL'] = ''

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'pay_order', 'app.py')
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

TEST_EVENT_ID = 'evt-pay-1234-abcd'
TEST_MEMBER_ID = 'mem-pay-001'
TEST_MEMBER_EMAIL = 'payer@h-dcn.nl'
TEST_ORDER_ID = 'order-pay-001'
TEST_REGISTRY_ROW_ID = 'row-amsterdam-001'


def _make_event(order_id=TEST_ORDER_ID, method='POST', body=None):
    """Create API Gateway event for POST /orders/{id}/pay."""
    return {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': {'id': order_id} if order_id else None,
        'body': json.dumps(body) if body else json.dumps({'method': 'ideal'}),
    }


# ---------------------------------------------------------------------------
# Auth patches
# ---------------------------------------------------------------------------

def _auth_patches(email=TEST_MEMBER_EMAIL):
    """Return patch.multiple for authenticated user."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, ['hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
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

        # Orders table
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Payments table
        payments_table = dynamodb.create_table(
            TableName='Payments',
            KeySchema=[{'AttributeName': 'payment_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'payment_id', 'AttributeType': 'S'}],
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

        # Seed member
        members_table.put_item(Item={
            'member_id': TEST_MEMBER_ID,
            'email': TEST_MEMBER_EMAIL,
            'registry_row_id': TEST_REGISTRY_ROW_ID,
            'allowed_events': [TEST_EVENT_ID],
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'payments': payments_table,
            'members': members_table,
            'producten': producten_table,
            'handler': handler,
        }


# ---------------------------------------------------------------------------
# Tests: Payment record uses registry_row_id
# Requirements: 1.5
# ---------------------------------------------------------------------------

class TestPaymentRegistryRowId:
    """Tests that payment records correctly include registry_row_id from the order."""

    def test_payment_record_includes_registry_row_id_for_event_order(self, setup_tables):
        """
        When an event order has registry_row_id, the payment record must include it.
        Validates: Requirements 1.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        payments_table = setup_tables['payments']

        # Seed an event order with registry_row_id and submitted status
        orders_table.put_item(Item={
            'order_id': TEST_ORDER_ID,
            'source_id': TEST_EVENT_ID,
            'event_id': TEST_EVENT_ID,
            'member_id': TEST_MEMBER_ID,
            'registry_row_id': TEST_REGISTRY_ROW_ID,
            'status': 'submitted',
            'payment_status': 'unpaid',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
            'total_amount': Decimal('45.00'),
            'total_paid': Decimal('0'),
            'version': 1,
        })

        with _auth_patches():
            event = _make_event(order_id=TEST_ORDER_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        payment_id = body['payment_id']

        # Verify payment record in DynamoDB includes registry_row_id
        payment_resp = payments_table.get_item(Key={'payment_id': payment_id})
        assert 'Item' in payment_resp
        payment = payment_resp['Item']
        assert payment['registry_row_id'] == TEST_REGISTRY_ROW_ID
        assert payment['order_id'] == TEST_ORDER_ID

    def test_payment_record_excludes_registry_row_id_for_webshop_order(self, setup_tables):
        """
        Webshop orders (no registry_row_id) should not have registry_row_id on payment record.
        Validates: Requirements 1.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        payments_table = setup_tables['payments']

        # Seed a webshop order (no event_id, no registry_row_id)
        orders_table.put_item(Item={
            'order_id': 'order-webshop-001',
            'source_id': 'webshop',
            'member_id': TEST_MEMBER_ID,
            'status': 'submitted',
            'payment_status': 'unpaid',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
            'total_amount': Decimal('25.00'),
            'total_paid': Decimal('0'),
            'version': 1,
        })

        with _auth_patches():
            event = _make_event(order_id='order-webshop-001')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        payment_id = body['payment_id']

        # Verify payment record does NOT have registry_row_id
        payment_resp = payments_table.get_item(Key={'payment_id': payment_id})
        payment = payment_resp['Item']
        assert 'registry_row_id' not in payment
