"""
Property-based tests for product soft delete behaviour.

Tests the active filter on customer-facing listing (Property 15) and the
hard-delete guard that prevents deletion of sold products (Property 16).

Feature: order-pipeline-improvements, Property 15/16
"""

import os
import sys
import uuid

import boto3
import pytest
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from boto3.dynamodb.conditions import Attr


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Active field values: True, False, or missing (represented as None)
active_values = st.sampled_from([True, False, None])

# Order statuses for hard-delete guard testing
order_statuses = st.sampled_from([
    'draft', 'submitted', 'confirmed', 'completed', 'cancelled'
])

# Generate a list of order statuses for multiple orders referencing a product
order_status_lists = st.lists(order_statuses, min_size=1, max_size=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_producten_table(dynamodb):
    """Get existing or create the Producten table with required schema."""
    try:
        table = dynamodb.Table('Producten')
        table.load()
        return table
    except Exception:
        pass

    table = dynamodb.create_table(
        TableName='Producten',
        KeySchema=[
            {'AttributeName': 'product_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'product_id', 'AttributeType': 'S'},
            {'AttributeName': 'parent_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'parent_id-index',
                'KeySchema': [
                    {'AttributeName': 'parent_id', 'KeyType': 'HASH'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Producten')
    return table


def _get_or_create_orders_table(dynamodb):
    """Get existing or create the Orders table with required schema."""
    try:
        table = dynamodb.Table('Orders')
        table.load()
        return table
    except Exception:
        pass

    table = dynamodb.create_table(
        TableName='Orders',
        KeySchema=[
            {'AttributeName': 'order_id', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'order_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Orders')
    return table


def _apply_customer_listing_filter(table):
    """
    Apply the same filter expression used by get_products handler:
    is_parent=true AND (active != false OR active not exists)
    """
    filter_expr = (
        Attr('is_parent').eq(True) &
        (Attr('active').ne(False) | Attr('active').not_exists())
    )
    response = table.scan(FilterExpression=filter_expr)
    items = response.get('Items', [])
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))
    return items


def _count_non_cancelled_orders_for_product(orders_table, product_ids):
    """
    Replicate the _count_non_cancelled_orders_for_products logic from
    admin_delete_product handler. Scans for non-cancelled orders that
    reference any of the given product_ids.
    """
    matching_orders = set()
    product_id_set = set(product_ids)

    scan_kwargs = {
        'FilterExpression': Attr('status').ne('cancelled'),
        'ProjectionExpression': 'order_id, #items_attr',
        'ExpressionAttributeNames': {'#items_attr': 'items'},
    }

    response = orders_table.scan(**scan_kwargs)
    _check_orders_for_products(response.get('Items', []), product_id_set, matching_orders)

    while 'LastEvaluatedKey' in response:
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        response = orders_table.scan(**scan_kwargs)
        _check_orders_for_products(response.get('Items', []), product_id_set, matching_orders)

    return len(matching_orders)


def _check_orders_for_products(orders, product_id_set, matching_orders):
    """Check orders for product references."""
    for order in orders:
        order_id = order.get('order_id')
        items = order.get('items', [])
        for item in items:
            item_product_id = item.get('product_id')
            item_variant_id = item.get('variant_id')
            if item_product_id in product_id_set or item_variant_id in product_id_set:
                matching_orders.add(order_id)
                break


# ---------------------------------------------------------------------------
# Property 15: Customer-facing listing excludes inactive products
# Feature: order-pipeline-improvements, Property 15: Customer-facing listing excludes inactive products
# Validates: Requirements 8.1
# ---------------------------------------------------------------------------


@mock_aws
@given(active_flags=st.lists(active_values, min_size=1, max_size=10))
@settings(max_examples=200, deadline=None)
def test_property_15_customer_listing_excludes_inactive(active_flags):
    """For any query to the customer-facing product listing, the result set
    SHALL contain only products where active=true or active is missing.
    No product with active=false SHALL appear."""
    # Setup
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = _get_or_create_producten_table(dynamodb)

    # Create products with various active values (unique IDs per run)
    created_products = []
    for active_val in active_flags:
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        item = {
            'product_id': product_id,
            'name': f'Test Product {product_id}',
            'is_parent': True,
        }
        if active_val is not None:
            item['active'] = active_val
        # If active_val is None, we omit the field entirely (simulating missing)
        table.put_item(Item=item)
        created_products.append((product_id, active_val))

    # Apply the customer-facing filter and check ONLY our products
    results = _apply_customer_listing_filter(table)
    result_ids = {item['product_id'] for item in results}
    our_product_ids = {pid for pid, _ in created_products}

    # Assertions — only check our products (table may have items from prior runs)
    for product_id, active_val in created_products:
        if active_val is False:
            # Inactive products must NOT appear
            assert product_id not in result_ids, (
                f"Product {product_id} with active=False should NOT appear "
                f"in customer listing"
            )
        else:
            # Products with active=True or missing active field SHOULD appear
            assert product_id in result_ids, (
                f"Product {product_id} with active={active_val} should appear "
                f"in customer listing"
            )


# ---------------------------------------------------------------------------
# Property 16: Hard-delete guard prevents deletion of sold products
# Feature: order-pipeline-improvements, Property 16: Hard-delete guard prevents deletion of sold products
# Validates: Requirements 8.2, 8.6
# ---------------------------------------------------------------------------


@mock_aws
@given(order_statuses_list=order_status_lists)
@settings(max_examples=200, deadline=None)
def test_property_16_hard_delete_guard(order_statuses_list):
    """For any product referenced by at least one order with status other than
    cancelled, hard-delete SHALL be rejected. Hard-delete SHALL succeed only
    when zero non-cancelled orders reference the product."""
    # Setup
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    orders_table = _get_or_create_orders_table(dynamodb)

    # Use a unique product_id per test invocation to isolate data
    product_id = f"prod_{uuid.uuid4().hex[:12]}"

    # Create orders referencing this product with given statuses
    for status in order_statuses_list:
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        orders_table.put_item(Item={
            'order_id': order_id,
            'status': status,
            'items': [{'product_id': product_id, 'quantity': 1}],
        })

    # Apply the hard-delete guard logic
    non_cancelled_count = _count_non_cancelled_orders_for_product(
        orders_table, [product_id]
    )

    # Determine expected result
    has_non_cancelled = any(s != 'cancelled' for s in order_statuses_list)

    if has_non_cancelled:
        # Hard-delete must be blocked
        assert non_cancelled_count > 0, (
            f"Expected hard-delete to be blocked (non-cancelled orders exist: "
            f"{order_statuses_list}), but count was {non_cancelled_count}"
        )
    else:
        # All orders are cancelled → hard-delete must be allowed
        assert non_cancelled_count == 0, (
            f"Expected hard-delete to succeed (all orders cancelled: "
            f"{order_statuses_list}), but count was {non_cancelled_count}"
        )
