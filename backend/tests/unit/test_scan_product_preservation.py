"""
Preservation property test for scan_product handler.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 3: Preservation - scan_product existing fields unchanged

For any request to the scan_product endpoint, the handler SHALL continue to
return `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`,
and `active` fields with identical values and Decimal-to-number conversion.

This test verifies the CURRENT (unfixed) behavior of the existing 7 fields.
It MUST PASS on unfixed code to establish the baseline that must be preserved
after the fix is applied.
"""

import json
import importlib.util
import os
import sys
from decimal import Decimal

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws
from unittest.mock import patch

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Path to the handler module (used for explicit import)
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')
)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

def _load_handler():
    """Load the scan_product handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Helpers
# =============================================================================

def _make_event():
    """Create a mock API Gateway event for GET /scan-product/."""
    return {
        'httpMethod': 'GET',
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'user@h-dcn.nl',
                    'cognito:groups': 'Products_Read'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def decimal_price_strategy():
    """Generate Decimal price values that exercise Decimal-to-number conversion.

    Includes whole numbers (should become int) and fractional values (should become float).
    """
    return st.one_of(
        # Whole number Decimals → should convert to int
        st.integers(min_value=0, max_value=9999).map(Decimal),
        # Fractional Decimals → should convert to float
        st.tuples(
            st.integers(min_value=0, max_value=9999),
            st.integers(min_value=1, max_value=99)
        ).map(lambda t: Decimal(f"{t[0]}.{t[1]:02d}")),
    )


@st.composite
def product_item_strategy(draw):
    """Generate a DynamoDB product item with varying Decimal values,
    missing optional fields, and None values.

    This exercises the preservation of the 7 existing fields:
    product_id, name, price, variant_schema, is_parent, event_id, active.
    """
    product_id = draw(st.uuids().map(str))

    # Name field: use 'name', 'naam', or both
    naming = draw(st.sampled_from(['name', 'naam', 'both', 'none']))
    name_value = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Z')),
        min_size=1, max_size=30
    ).filter(lambda s: s.strip() != ''))

    # Price field: use 'price', 'prijs', or both — with Decimal values
    pricing = draw(st.sampled_from(['price', 'prijs', 'both', 'none']))
    price_value = draw(decimal_price_strategy())
    alt_price_value = draw(decimal_price_strategy())

    # Optional fields
    has_variant_schema = draw(st.booleans())
    has_event_id = draw(st.booleans())
    is_active = draw(st.one_of(st.just(True), st.just(False), st.just(None)))

    record = {
        'product_id': product_id,
        'is_parent': True,  # Required to pass the scan filter
    }

    # Name fields
    if naming == 'name':
        record['name'] = name_value
    elif naming == 'naam':
        record['naam'] = name_value
    elif naming == 'both':
        record['name'] = name_value
        record['naam'] = f"alt_{name_value}"
    # 'none' → neither field present

    # Price fields (Decimal values from DynamoDB)
    if pricing == 'price':
        record['price'] = price_value
    elif pricing == 'prijs':
        record['prijs'] = price_value
    elif pricing == 'both':
        record['price'] = price_value
        record['prijs'] = alt_price_value
    # 'none' → neither field present

    # variant_schema
    if has_variant_schema:
        record['variant_schema'] = {'Maat': ['S', 'M', 'L']}

    # event_id
    if has_event_id:
        record['event_id'] = draw(st.uuids().map(str))

    # active
    if is_active is not None:
        record['active'] = is_active

    return record


# =============================================================================
# Property 3: Preservation - existing fields unchanged
# =============================================================================

class TestScanProductPreservation:
    """
    **Validates: Requirements 3.1, 3.2**

    Property 3: Preservation - scan_product existing fields unchanged

    For any product item in DynamoDB, the scan_product handler returns
    the 7 existing fields (product_id, name, price, variant_schema, is_parent,
    event_id, active) with correct values and Decimal-to-number conversion.

    These tests MUST PASS on unfixed code — they establish baseline behavior.
    """

    @given(product=product_item_strategy())
    @settings(max_examples=50, deadline=None)
    def test_existing_seven_fields_are_returned(self, product):
        """
        For any generated product item, all 7 existing fields are present
        as keys in the response.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # DynamoDB doesn't accept None values — filter them out
            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body) == 1

            result = body[0]

            # All 7 existing fields must be present as keys
            required_fields = ['product_id', 'name', 'price', 'variant_schema',
                               'is_parent', 'event_id', 'active']
            for field in required_fields:
                assert field in result, (
                    f"Existing field '{field}' must remain in response. "
                    f"Keys returned: {list(result.keys())}"
                )

    @given(product=product_item_strategy())
    @settings(max_examples=50, deadline=None)
    def test_product_id_preserved_exactly(self, product):
        """product_id is returned unchanged from DynamoDB."""
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]
            assert result['product_id'] == product['product_id']

    @given(product=product_item_strategy())
    @settings(max_examples=50, deadline=None)
    def test_decimal_to_number_conversion(self, product):
        """
        Decimal price values from DynamoDB are converted correctly:
        - Whole number Decimals → int
        - Fractional Decimals → float
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # Determine expected price
            if 'price' in product and product['price'] is not None:
                expected_decimal = product['price']
            elif 'prijs' in product and product['prijs'] is not None:
                expected_decimal = product['prijs']
            else:
                # No price field → should be None
                assert result['price'] is None
                return

            # Check Decimal conversion
            if expected_decimal == int(expected_decimal):
                # Whole number → should be int
                assert result['price'] == int(expected_decimal), (
                    f"Decimal {expected_decimal} should convert to int {int(expected_decimal)}, "
                    f"got {result['price']}"
                )
            else:
                # Fractional → should be float
                assert result['price'] == float(expected_decimal), (
                    f"Decimal {expected_decimal} should convert to float {float(expected_decimal)}, "
                    f"got {result['price']}"
                )

    @given(product=product_item_strategy())
    @settings(max_examples=50, deadline=None)
    def test_name_fallback_logic_preserved(self, product):
        """
        Name resolution logic: 'name' takes precedence, 'naam' is fallback.
        This behavior must be preserved after the fix.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # Verify name fallback: name > naam > None
            if 'name' in product and product['name'] is not None:
                assert result['name'] == product['name']
            elif 'naam' in product and product['naam'] is not None:
                assert result['name'] == product['naam']
            else:
                assert result['name'] is None

    @given(product=product_item_strategy())
    @settings(max_examples=50, deadline=None)
    def test_is_parent_and_active_preserved(self, product):
        """
        is_parent and active fields are returned as-is from DynamoDB.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # is_parent
            expected_is_parent = product.get('is_parent')
            assert result['is_parent'] == expected_is_parent

            # active
            expected_active = product.get('active')
            assert result['active'] == expected_active
