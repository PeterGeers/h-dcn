"""
Property-based tests for admin_delete_variant handler.

**Validates: Requirements 3.3, 3.4, 3.5**

Property 6: Delete correctness depends on order references
- For any variant, the delete API SHALL succeed (remove record, update parent schema)
  if and only if no orders reference that variant's product_id.
- If orders DO reference it, the API SHALL return 409 and the record SHALL remain unchanged.
"""

import json
import os
import sys
import importlib.util
import boto3
import pytest
from unittest.mock import patch
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Set environment before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_delete_variant', 'app.py')
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


def _make_event(product_id, variant_id):
    """Create a mock API Gateway DELETE event."""
    return {
        'httpMethod': 'DELETE',
        'pathParameters': {'id': product_id, 'vid': variant_id},
        'body': None,
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


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Hypothesis strategies ---

# Strategy for generating variant attribute keys (size axes)
axis_name_st = st.sampled_from(['Maat', 'Kleur', 'Gender', 'Lengte', 'Stijl'])

# Strategy for generating attribute values
attr_value_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_ '),
    min_size=1,
    max_size=10
)

# Strategy for variant attributes (1-3 axes)
variant_attrs_st = st.dictionaries(
    keys=axis_name_st,
    values=attr_value_st,
    min_size=1,
    max_size=3
)

# Strategy for stock values (DynamoDB stores as Decimal, use int)
stock_st = st.integers(min_value=0, max_value=9999)

# Strategy for price (as string, like DynamoDB stores it)
price_st = st.one_of(
    st.none(),
    st.decimals(min_value=0, max_value=999, places=2).map(str)
)

# Strategy for number of orders referencing the variant (0 = no orders)
order_count_st = st.integers(min_value=0, max_value=3)


@settings(max_examples=100, deadline=None)
@given(
    variant_attrs=variant_attrs_st,
    stock=stock_st,
    price=price_st,
    num_orders=order_count_st,
)
def test_delete_correctness_depends_on_order_references(
    variant_attrs, stock, price, num_orders
):
    """
    Property 6: Delete correctness depends on order references.

    **Validates: Requirements 3.3, 3.4, 3.5**

    For any variant:
    - If no orders reference it → delete succeeds (200), record removed from DB
    - If orders reference it → delete fails (409), record unchanged in DB
    """
    # Filter out empty attribute values that could cause issues
    assume(all(v.strip() for v in variant_attrs.values()))

    parent_id = 'prod-prop-test'
    variant_id = 'var-prop-test'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
                {'AttributeName': 'parent_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'parent_id-index',
                    'KeySchema': [{'AttributeName': 'parent_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create Orders table
        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Build the variant item
        variant_item = {
            'product_id': variant_id,
            'parent_id': parent_id,
            'is_parent': False,
            'variant_attributes': variant_attrs,
            'active': True,
            'stock': stock,
        }
        if price is not None:
            variant_item['prijs'] = price

        # Create parent product
        producten.put_item(Item={
            'product_id': parent_id,
            'is_parent': True,
            'variant_schema': {k: [v] for k, v in variant_attrs.items()},
        })

        # Create variant
        producten.put_item(Item=variant_item)

        # Create orders referencing this variant (if num_orders > 0)
        for i in range(num_orders):
            orders.put_item(Item={
                'order_id': f'order-{i}',
                'line_items': [{'variant_id': variant_id, 'quantity': 1}],
            })

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.table = producten
        handler_module.orders_table = orders

        # Execute the delete
        event = _make_event(parent_id, variant_id)
        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        status_code = response['statusCode']
        body = json.loads(response['body'])

        if num_orders == 0:
            # No orders → delete should succeed
            assert status_code == 200, (
                f"Expected 200 (delete success) when no orders exist, got {status_code}: {body}"
            )
            # Verify variant is removed from DB
            result = producten.get_item(Key={'product_id': variant_id})
            assert 'Item' not in result, (
                "Variant record should be deleted from DB when no orders reference it"
            )
        else:
            # Orders exist → delete should be rejected with 409
            assert status_code == 409, (
                f"Expected 409 (conflict) when {num_orders} order(s) exist, got {status_code}: {body}"
            )
            # Verify variant record is unchanged
            result = producten.get_item(Key={'product_id': variant_id})
            assert 'Item' in result, (
                "Variant record should remain in DB when orders reference it"
            )
            stored = result['Item']
            assert stored['variant_attributes'] == variant_attrs
            assert stored['stock'] == stock
            assert stored['active'] is True
            if price is not None:
                assert stored.get('prijs') == price
