"""
Property-based tests for admin_add_stock handler.

**Validates: Requirements 6.4**

Property 7: Stock addition is additive
- For any variant with current stock S and any valid quantity Q (1 <= Q <= 10000),
  adding stock via the add-stock API SHALL result in a new stock value of exactly S + Q.
"""

import json
import os
import sys
import importlib.util
import boto3
import pytest
from decimal import Decimal
from unittest.mock import patch
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Set environment before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['STOCK_MOVEMENTS_TABLE_NAME'] = 'StockMovements'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_add_stock', 'app.py')
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


def _make_event(product_id, variant_id, quantity, purchase_price_per_unit, supplier_name):
    """Create a mock API Gateway POST event for add-stock."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id, 'vid': variant_id},
        'body': json.dumps({
            'quantity': quantity,
            'purchase_price_per_unit': purchase_price_per_unit,
            'supplier_name': supplier_name,
        }),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Products_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _mock_create_inbound_movement(*args, **kwargs):
    """Mock for create_inbound_movement that accepts any signature."""
    return {'movement_id': 'mov_test123', 'type': 'inbound'}


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
        create_inbound_movement=_mock_create_inbound_movement,
    )


# --- Hypothesis strategies ---

# Starting stock: 0 to 99999
starting_stock_st = st.integers(min_value=0, max_value=99999)

# Quantity to add: 1 to 10000
quantity_st = st.integers(min_value=1, max_value=10000)


@settings(max_examples=100, deadline=None)
@given(
    starting_stock=starting_stock_st,
    quantity=quantity_st,
)
def test_stock_addition_is_additive(starting_stock, quantity):
    """
    Property 7: Stock addition is additive.

    **Validates: Requirements 6.4**

    For any variant with current stock S and any valid quantity Q (1 <= Q <= 10000),
    adding stock via the add-stock API SHALL result in a new stock value of exactly S + Q.
    """
    parent_id = 'prod-stock-test'
    variant_id = 'var-stock-test'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create StockMovements table
        movements = dynamodb.create_table(
            TableName='StockMovements',
            KeySchema=[{'AttributeName': 'movement_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'movement_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create variant with starting stock S
        producten.put_item(Item={
            'product_id': variant_id,
            'parent_id': parent_id,
            'is_parent': False,
            'variant_attributes': {'Maat': 'M'},
            'stock': starting_stock,
            'active': True,
        })

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.producten_table = producten
        handler_module.movements_table = movements

        # Execute the add-stock call
        event = _make_event(parent_id, variant_id, quantity, 5.00, 'test-supplier')
        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        status_code = response['statusCode']
        body = json.loads(response['body'])

        # Assert HTTP 200
        assert status_code == 200, (
            f"Expected 200 from add-stock, got {status_code}: {body}"
        )

        # Re-read the variant from DynamoDB
        result = producten.get_item(Key={'product_id': variant_id})
        assert 'Item' in result, "Variant should still exist after add-stock"

        new_stock = result['Item']['stock']

        # Assert stock == S + Q
        expected_stock = starting_stock + quantity
        assert new_stock == expected_stock, (
            f"Expected stock = {starting_stock} + {quantity} = {expected_stock}, "
            f"got {new_stock}"
        )
