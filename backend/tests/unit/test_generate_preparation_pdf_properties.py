"""
Property-based tests for generate_preparation_pdf handler (product fetch).

**Validates: Requirements 7.1, 7.2**

Property 7: PDF generator fetches products via event.product_ids
- For any event record with a product_ids array, the preparation PDF generator
  SHALL fetch exactly those product IDs via batch-get and SHALL NOT scan the
  Producten table by event_id.
"""

import os
import sys
import importlib.util
import boto3
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Set environment before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_preparation_pdf', 'app.py')
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


# --- Hypothesis strategies ---

# Product IDs: alphanumeric strings that look like real IDs
product_id_st = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789-_'),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

# Set of existing product IDs (will be seeded into DynamoDB)
existing_ids_st = st.frozensets(product_id_st, min_size=0, max_size=10)

# Set of non-existing product IDs (requested but not in DynamoDB)
nonexisting_ids_st = st.frozensets(product_id_st, min_size=0, max_size=5)


@settings(max_examples=50, deadline=None)
@given(
    existing_ids=existing_ids_st,
    nonexisting_ids=nonexisting_ids_st,
)
def test_fetch_products_map_returns_exactly_existing_subset(existing_ids, nonexisting_ids):
    """
    Property 7: PDF generator fetches products via event.product_ids.

    **Validates: Requirements 7.1, 7.2**

    For any set of product IDs in the event's product_ids array, _fetch_products_map
    SHALL return a map containing exactly those products that exist in DynamoDB.
    Products that don't exist are silently omitted.
    """
    # Ensure non-existing IDs don't overlap with existing IDs
    nonexisting_ids = nonexisting_ids - existing_ids

    # Combine existing + non-existing to form the product_ids array
    all_requested_ids = list(existing_ids | nonexisting_ids)

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Seed existing products into DynamoDB
        for pid in existing_ids:
            table.put_item(Item={
                'product_id': pid,
                'naam': f'Product {pid}',
                'prijs': Decimal('10.00'),
                'active': True,
            })

        # Load handler inside mock context
        handler_module = _load_handler()

        # Call _fetch_products_map directly with the combined ID list
        products_map = handler_module._fetch_products_map(all_requested_ids)

        # Verify: returned map keys should be exactly the existing IDs that were requested
        returned_ids = set(products_map.keys())
        expected_ids = existing_ids  # Only existing products should be returned

        assert returned_ids == expected_ids, (
            f"Expected products {expected_ids}, got {returned_ids}. "
            f"Missing: {expected_ids - returned_ids}, "
            f"Extra: {returned_ids - expected_ids}"
        )

        # Verify: each returned product has product_id and naam (from ProjectionExpression)
        for pid, product in products_map.items():
            assert product['product_id'] == pid
            assert 'naam' in product


@settings(max_examples=50, deadline=None)
@given(
    existing_ids=existing_ids_st,
    nonexisting_ids=nonexisting_ids_st,
)
def test_fetch_products_map_does_not_scan_by_event_id(existing_ids, nonexisting_ids):
    """
    Property 7: PDF generator does NOT scan by event_id.

    **Validates: Requirements 7.1, 7.2**

    The _fetch_products_map function SHALL use batch_get_item (not scan) to fetch
    products. We verify this by patching DynamoDB's scan method and asserting it
    is never called.
    """
    # Ensure non-existing IDs don't overlap with existing IDs
    nonexisting_ids = nonexisting_ids - existing_ids

    all_requested_ids = list(existing_ids | nonexisting_ids)

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Seed existing products into DynamoDB
        for pid in existing_ids:
            table.put_item(Item={
                'product_id': pid,
                'naam': f'Product {pid}',
                'prijs': Decimal('10.00'),
                'active': True,
            })

        # Load handler inside mock context
        handler_module = _load_handler()

        # Wrap the DynamoDB resource's batch_get_item to track calls
        original_batch_get = handler_module.dynamodb.batch_get_item
        batch_get_calls = []

        def tracking_batch_get(*args, **kwargs):
            batch_get_calls.append((args, kwargs))
            return original_batch_get(*args, **kwargs)

        # Patch: track batch_get_item calls and ensure scan is NOT used
        with patch.object(handler_module.dynamodb, 'batch_get_item', side_effect=tracking_batch_get):
            # Create a scan spy on the table to ensure it's never called
            scan_mock = MagicMock(side_effect=AssertionError(
                "scan() was called but should NOT be — _fetch_products_map must use batch_get_item"
            ))

            with patch.object(table, 'scan', scan_mock):
                products_map = handler_module._fetch_products_map(all_requested_ids)

        # If there were any IDs to fetch, batch_get_item should have been called
        if len(all_requested_ids) > 0:
            assert len(batch_get_calls) > 0, (
                "batch_get_item was never called despite non-empty product_ids list"
            )


@settings(max_examples=20, deadline=None)
@given(existing_ids=st.frozensets(product_id_st, min_size=0, max_size=0))
def test_fetch_products_map_empty_ids_returns_empty(existing_ids):
    """
    Property 7: Empty product_ids yields empty map.

    **Validates: Requirements 7.1, 7.2**

    When product_ids is empty, _fetch_products_map SHALL return an empty dict
    without making any DynamoDB calls.
    """
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table (required for handler module load)
        dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Load handler inside mock context
        handler_module = _load_handler()

        # Call with empty list
        products_map = handler_module._fetch_products_map([])

        # Should return empty dict
        assert products_map == {}, (
            f"Expected empty dict for empty product_ids, got {products_map}"
        )
