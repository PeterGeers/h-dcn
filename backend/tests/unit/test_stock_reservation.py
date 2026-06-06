"""
Unit tests for shared.stock_reservation module.

Tests reserve_stock_for_order() covering:
- Atomic stock decrement + sold_count increment
- Idempotency guard (double-deduction prevention)
- Insufficient stock rejection for allow_oversell=false variants
- Allow oversell variants (stock may go negative)
- Multiple items in a single order
"""

import pytest
import boto3
import sys
import os
from decimal import Decimal
from moto import mock_aws

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.stock_reservation import (
    reserve_stock_for_order,
    InsufficientStockError,
    AlreadyReservedError,
    StockReservationError,
)


@pytest.fixture
def aws_env():
    """Set up mocked AWS credentials."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'


@pytest.fixture
def producten_table(aws_env):
    """Create a mocked Producten DynamoDB table with test variant records."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        yield table


def _create_variant(table, variant_id, stock=10, sold_count=0, allow_oversell=False):
    """Helper to insert a variant record."""
    table.put_item(Item={
        'product_id': variant_id,
        'is_parent': False,
        'parent_id': 'prod_test',
        'stock': stock,
        'sold_count': sold_count,
        'allow_oversell': allow_oversell,
        'active': True,
    })


class TestReserveStockForOrder:
    """Tests for the happy path of stock reservation."""

    def test_single_item_reserves_stock(self, producten_table):
        _create_variant(producten_table, 'var_001', stock=10, sold_count=0)

        order_items = [{'variant_id': 'var_001', 'quantity': 3}]
        results = reserve_stock_for_order(order_items, producten_table, 'order_abc')

        assert len(results) == 1
        assert results[0]['status'] == 'reserved'
        assert results[0]['variant_id'] == 'var_001'
        assert results[0]['quantity'] == 3

        # Verify DB state
        variant = producten_table.get_item(Key={'product_id': 'var_001'})['Item']
        assert variant['stock'] == 7
        assert variant['sold_count'] == 3
        assert variant['stock_reserved_for_order'] == 'order_abc'

    def test_multiple_items_reserves_all(self, producten_table):
        _create_variant(producten_table, 'var_001', stock=10, sold_count=0)
        _create_variant(producten_table, 'var_002', stock=5, sold_count=2)

        order_items = [
            {'variant_id': 'var_001', 'quantity': 2},
            {'variant_id': 'var_002', 'quantity': 3},
        ]
        results = reserve_stock_for_order(order_items, producten_table, 'order_xyz')

        assert all(r['status'] == 'reserved' for r in results)

        var1 = producten_table.get_item(Key={'product_id': 'var_001'})['Item']
        assert var1['stock'] == 8
        assert var1['sold_count'] == 2

        var2 = producten_table.get_item(Key={'product_id': 'var_002'})['Item']
        assert var2['stock'] == 2
        assert var2['sold_count'] == 5

    def test_preserves_stock_invariant(self, producten_table):
        """initial_stock - stock_after = sold_count_after - initial_sold_count = quantity"""
        initial_stock = 15
        initial_sold = 5
        quantity = 4

        _create_variant(producten_table, 'var_inv', stock=initial_stock, sold_count=initial_sold)

        reserve_stock_for_order(
            [{'variant_id': 'var_inv', 'quantity': quantity}],
            producten_table,
            'order_inv',
        )

        variant = producten_table.get_item(Key={'product_id': 'var_inv'})['Item']
        stock_after = variant['stock']
        sold_after = variant['sold_count']

        assert initial_stock - stock_after == quantity
        assert sold_after - initial_sold == quantity
        assert initial_stock - stock_after == sold_after - initial_sold


class TestIdempotency:
    """Tests for the idempotency guard preventing double-deduction."""

    def test_second_call_same_order_returns_already_reserved(self, producten_table):
        _create_variant(producten_table, 'var_idem', stock=10, sold_count=0)
        order_items = [{'variant_id': 'var_idem', 'quantity': 3}]

        # First call
        results1 = reserve_stock_for_order(order_items, producten_table, 'order_dup')
        assert results1[0]['status'] == 'reserved'

        # Second call (retry) — should NOT deduct again
        results2 = reserve_stock_for_order(order_items, producten_table, 'order_dup')
        assert results2[0]['status'] == 'already_reserved'

        # Verify stock was only decremented once
        variant = producten_table.get_item(Key={'product_id': 'var_idem'})['Item']
        assert variant['stock'] == 7
        assert variant['sold_count'] == 3

    def test_different_order_can_reserve_after_first(self, producten_table):
        """A different order_id should be able to reserve (not blocked by first)."""
        _create_variant(producten_table, 'var_multi', stock=10, sold_count=0)

        reserve_stock_for_order(
            [{'variant_id': 'var_multi', 'quantity': 2}],
            producten_table,
            'order_first',
        )

        # Different order should succeed
        results = reserve_stock_for_order(
            [{'variant_id': 'var_multi', 'quantity': 3}],
            producten_table,
            'order_second',
        )
        assert results[0]['status'] == 'reserved'

        variant = producten_table.get_item(Key={'product_id': 'var_multi'})['Item']
        assert variant['stock'] == 5  # 10 - 2 - 3
        assert variant['sold_count'] == 5


class TestInsufficientStock:
    """Tests for stock enforcement on allow_oversell=false variants."""

    def test_rejects_when_stock_less_than_quantity(self, producten_table):
        _create_variant(producten_table, 'var_low', stock=2, sold_count=0, allow_oversell=False)

        with pytest.raises(InsufficientStockError) as exc_info:
            reserve_stock_for_order(
                [{'variant_id': 'var_low', 'quantity': 5}],
                producten_table,
                'order_fail',
            )

        assert exc_info.value.variant_id == 'var_low'
        assert exc_info.value.available == 2
        assert exc_info.value.requested == 5

        # Verify stock unchanged
        variant = producten_table.get_item(Key={'product_id': 'var_low'})['Item']
        assert variant['stock'] == 2
        assert variant['sold_count'] == 0

    def test_allows_exact_stock_quantity(self, producten_table):
        _create_variant(producten_table, 'var_exact', stock=5, sold_count=0, allow_oversell=False)

        results = reserve_stock_for_order(
            [{'variant_id': 'var_exact', 'quantity': 5}],
            producten_table,
            'order_exact',
        )
        assert results[0]['status'] == 'reserved'

        variant = producten_table.get_item(Key={'product_id': 'var_exact'})['Item']
        assert variant['stock'] == 0
        assert variant['sold_count'] == 5

    def test_rejects_zero_stock(self, producten_table):
        _create_variant(producten_table, 'var_zero', stock=0, sold_count=10, allow_oversell=False)

        with pytest.raises(InsufficientStockError) as exc_info:
            reserve_stock_for_order(
                [{'variant_id': 'var_zero', 'quantity': 1}],
                producten_table,
                'order_zero',
            )
        assert exc_info.value.available == 0


class TestAllowOversell:
    """Tests for variants with allow_oversell=true."""

    def test_allows_oversell_even_when_stock_insufficient(self, producten_table):
        _create_variant(producten_table, 'var_os', stock=2, sold_count=0, allow_oversell=True)

        results = reserve_stock_for_order(
            [{'variant_id': 'var_os', 'quantity': 5}],
            producten_table,
            'order_os',
        )
        assert results[0]['status'] == 'reserved'

        variant = producten_table.get_item(Key={'product_id': 'var_os'})['Item']
        assert variant['stock'] == -3  # Negative is allowed
        assert variant['sold_count'] == 5

    def test_oversell_idempotency_still_works(self, producten_table):
        _create_variant(producten_table, 'var_os2', stock=2, sold_count=0, allow_oversell=True)

        reserve_stock_for_order(
            [{'variant_id': 'var_os2', 'quantity': 5}],
            producten_table,
            'order_os_dup',
        )
        results = reserve_stock_for_order(
            [{'variant_id': 'var_os2', 'quantity': 5}],
            producten_table,
            'order_os_dup',
        )
        assert results[0]['status'] == 'already_reserved'

        variant = producten_table.get_item(Key={'product_id': 'var_os2'})['Item']
        assert variant['stock'] == -3  # Only decremented once


class TestErrorCases:
    """Tests for error handling."""

    def test_variant_not_found_raises_error(self, producten_table):
        with pytest.raises(StockReservationError) as exc_info:
            reserve_stock_for_order(
                [{'variant_id': 'nonexistent', 'quantity': 1}],
                producten_table,
                'order_err',
            )
        assert 'not found' in str(exc_info.value)
        assert exc_info.value.variant_id == 'nonexistent'

    def test_empty_order_items_returns_empty(self, producten_table):
        results = reserve_stock_for_order([], producten_table, 'order_empty')
        assert results == []
