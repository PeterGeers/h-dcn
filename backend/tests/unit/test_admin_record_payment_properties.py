"""
Property-Based Tests for Admin Record Payment Handler

# Feature: presmeet-v3, Property 7: Payment handler input validation

Tests that for any payload missing order_id, non-numeric amount, amount outside
[0.01, 999999.99], missing date, or invalid date format, the handler returns 400
and does NOT modify any database records.

**Validates: Requirements 6.1**
"""

import json
import os
import sys
import importlib
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest
import boto3
from moto import mock_aws
from hypothesis import given, settings, assume, note, HealthCheck
from hypothesis import strategies as st

# Ensure paths are set up for handler imports
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_handler_dir = os.path.join(_backend_dir, 'handler', 'admin_record_payment')
_layers_path = os.path.join(_backend_dir, 'layers', 'auth-layer', 'python')

if _handler_dir not in sys.path:
    sys.path.insert(0, _handler_dir)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)


# ---- Fixtures ----

@pytest.fixture(autouse=True)
def mock_auth():
    """Mock auth layer so all requests pass authentication."""
    with patch('shared.auth_utils.extract_user_credentials') as mock_extract, \
         patch('shared.auth_utils.validate_permissions_with_regions') as mock_validate, \
         patch('shared.auth_utils.log_successful_access'):
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})
        yield


@pytest.fixture(autouse=True)
def setup_env():
    """Set required environment variables."""
    os.environ['ORDERS_TABLE_NAME'] = 'Orders'
    os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    yield


def _make_event(body: dict) -> dict:
    """Create a minimal API Gateway event with the given body."""
    return {
        'httpMethod': 'POST',
        'path': '/admin/payments/record',
        'headers': {'Authorization': 'Bearer fake-token'},
        'queryStringParameters': None,
        'body': json.dumps(body),
        'requestContext': {},
    }


def _invoke_handler(event: dict) -> dict:
    """Import and invoke the handler fresh (avoids module caching issues)."""
    if 'app' in sys.modules:
        del sys.modules['app']
    # Ensure our handler dir is first in sys.path
    if sys.path[0] != _handler_dir:
        if _handler_dir in sys.path:
            sys.path.remove(_handler_dir)
        sys.path.insert(0, _handler_dir)
    import app
    importlib.reload(app)
    return app.lambda_handler(event, None)


# ---- Hypothesis Strategies ----

# Valid date strings (ISO 8601) for use as baseline
valid_dates = st.sampled_from([
    '2024-01-15', '2024-06-30T12:00:00', '2024-12-31T23:59:59Z',
    '2025-03-01T10:30:00+01:00', '2023-07-20',
])

# Invalid date strings that should not parse as ISO 8601
invalid_date_strings = st.one_of(
    st.just('not-a-date'),
    st.just('2024-13-01'),       # month 13
    st.just('32-01-2024'),       # wrong order
    st.just('abcdef'),
    st.just('2024/01/15'),       # wrong separator
    st.just(''),                 # empty string
    st.from_regex(r'[a-z]{3,10}', fullmatch=True),  # random text
    st.from_regex(r'\d{1,2}-\d{1,2}-\d{4}', fullmatch=True),  # DD-MM-YYYY format
)

# Non-numeric amount values (excluding booleans since bool is subclass of int in Python)
non_numeric_amounts = st.one_of(
    st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('L',))),  # letters only
    st.just(None),
    st.lists(st.integers(), min_size=0, max_size=3),
    st.dictionaries(keys=st.text(min_size=1, max_size=5), values=st.integers(), min_size=0, max_size=2),
)

# Amounts outside valid range [0.01, 999999.99]
out_of_range_amounts = st.one_of(
    st.floats(min_value=-1000000, max_value=0.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
    st.just(0),
    st.just(0.0),
    st.just(-1),
    st.just(-0.01),
    st.just(1000000),
)


# ---- Shared settings ----
# deadline=None avoids flaky failures on first invocations which are slow due to module loading
pbt_settings = settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])


# =============================================================================
# Property 7: Payment handler input validation
# =============================================================================

class TestProperty7PaymentHandlerInputValidation:
    """
    # Feature: presmeet-v3, Property 7: Payment handler input validation

    **Validates: Requirements 6.1**

    For any request payload missing order_id, or with a non-numeric amount,
    or with amount outside [0.01, 999999.99], or missing date, or with an
    invalid date format, the handler SHALL return a 400 status with a
    descriptive error message and SHALL NOT modify any database records.
    """

    @given(
        amount=st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False),
        date=valid_dates,
        description=st.text(min_size=0, max_size=50),
    )
    @pbt_settings
    def test_missing_order_id_returns_400(self, amount, date, description):
        """
        **Validates: Requirements 6.1**

        When order_id is missing from the payload, handler returns 400
        and does not modify database.
        """
        body = {
            'amount': round(amount, 2),
            'date': date,
            'description': description,
        }
        # Explicitly omit order_id

        event = _make_event(body)
        response = _invoke_handler(event)

        note(f"Body: {body}, Response status: {response['statusCode']}")
        assert response['statusCode'] == 400

        response_body = json.loads(response['body'])
        assert 'order_id' in json.dumps(response_body).lower()

    @given(
        order_id=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('L', 'N'))),
        amount=non_numeric_amounts,
        date=valid_dates,
    )
    @pbt_settings
    def test_non_numeric_amount_returns_400(self, order_id, amount, date):
        """
        **Validates: Requirements 6.1**

        When amount is non-numeric (string, None, list, dict),
        handler returns 400.
        """
        body = {
            'order_id': order_id,
            'amount': amount,
            'date': date,
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        note(f"Amount: {amount!r}, Response status: {response['statusCode']}")
        assert response['statusCode'] == 400

    @given(
        order_id=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('L', 'N'))),
        amount=out_of_range_amounts,
        date=valid_dates,
    )
    @pbt_settings
    def test_amount_outside_range_returns_400(self, order_id, amount, date):
        """
        **Validates: Requirements 6.1**

        When amount is outside [0.01, 999999.99], handler returns 400.
        """
        # Ensure this is a numeric value that passes isinstance check but fails range
        assume(isinstance(amount, (int, float)))
        assume(not isinstance(amount, bool))
        assume(amount < 0.01 or amount > 999999.99)

        body = {
            'order_id': order_id,
            'amount': amount,
            'date': date,
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        note(f"Amount: {amount}, Response status: {response['statusCode']}")
        assert response['statusCode'] == 400

    @given(
        order_id=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('L', 'N'))),
        amount=st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False),
    )
    @pbt_settings
    def test_missing_date_returns_400(self, order_id, amount):
        """
        **Validates: Requirements 6.1**

        When date is missing from the payload, handler returns 400.
        """
        body = {
            'order_id': order_id,
            'amount': round(amount, 2),
            # date intentionally omitted
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        note(f"Body (no date): {body}, Response status: {response['statusCode']}")
        assert response['statusCode'] == 400

    @given(
        order_id=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('L', 'N'))),
        amount=st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False),
        date=invalid_date_strings,
    )
    @pbt_settings
    def test_invalid_date_format_returns_400(self, order_id, amount, date):
        """
        **Validates: Requirements 6.1**

        When date has an invalid format (not ISO 8601), handler returns 400.
        """
        body = {
            'order_id': order_id,
            'amount': round(amount, 2),
            'date': date,
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        note(f"Date: {date!r}, Response status: {response['statusCode']}")
        assert response['statusCode'] == 400

    @given(
        amount=st.floats(min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False),
        date=valid_dates,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @mock_aws
    def test_missing_order_id_does_not_modify_db(self, amount, date):
        """
        **Validates: Requirements 6.1**

        When order_id is missing, the Orders table is not modified.
        """
        # Set up mocked DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed a test order
        table.put_item(Item={
            'order_id': 'test_order_1',
            'total_amount': Decimal('100.00'),
            'amount_paid': Decimal('0'),
            'payment_status': 'unpaid',
            'payments': [],
        })

        body = {
            'amount': round(amount, 2),
            'date': date,
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        assert response['statusCode'] == 400

        # Verify the order was NOT modified
        item = table.get_item(Key={'order_id': 'test_order_1'})['Item']
        assert item['payment_status'] == 'unpaid'
        assert item['amount_paid'] == Decimal('0')
        assert item['payments'] == []

    @given(
        order_id=st.from_regex(r'[a-zA-Z0-9]{5,15}', fullmatch=True),
        amount=out_of_range_amounts,
        date=valid_dates,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @mock_aws
    def test_invalid_amount_does_not_modify_db(self, order_id, amount, date):
        """
        **Validates: Requirements 6.1**

        When amount is out of range, the Orders table is not modified.
        """
        assume(isinstance(amount, (int, float)))
        assume(not isinstance(amount, bool))
        assume(amount < 0.01 or amount > 999999.99)

        # Set up mocked DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed order matching the generated order_id
        table.put_item(Item={
            'order_id': order_id,
            'total_amount': Decimal('100.00'),
            'amount_paid': Decimal('0'),
            'payment_status': 'unpaid',
            'payments': [],
        })

        body = {
            'order_id': order_id,
            'amount': amount,
            'date': date,
        }

        event = _make_event(body)
        response = _invoke_handler(event)

        assert response['statusCode'] == 400

        # Verify the order was NOT modified
        item = table.get_item(Key={'order_id': order_id})['Item']
        assert item['payment_status'] == 'unpaid'
        assert item['amount_paid'] == Decimal('0')
        assert item['payments'] == []
