"""
Property-based tests for get_products handler (batch-get-by-IDs).

**Validates: Requirements 6.1, 6.4**

Property 3: Batch-get returns exactly the existing subset
- For any list of product IDs passed to get_products, the response SHALL contain
  exactly the set of products whose IDs both appear in the request AND exist in
  DynamoDB — no more, no less.
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
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_products', 'app.py')
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


def _make_event(product_ids_csv: str) -> dict:
    """Create a mock API Gateway GET event for get_products."""
    return {
        'httpMethod': 'GET',
        'queryStringParameters': {'product_ids': product_ids_csv},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'user@h-dcn.nl',
                    'cognito:groups': 'hdcnLeden'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['hdcnLeden'], None),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Hypothesis strategies ---

# Product IDs: alphanumeric strings that look like real IDs
product_id_st = st.text(
    alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789-_'),
    min_size=3,
    max_size=20,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

# Set of existing product IDs (products that will be in DynamoDB)
existing_ids_st = st.frozensets(product_id_st, min_size=1, max_size=10)

# Set of non-existing product IDs (products NOT in DynamoDB)
nonexisting_ids_st = st.frozensets(product_id_st, min_size=0, max_size=10)


@settings(max_examples=50, deadline=None)
@given(
    existing_ids=existing_ids_st,
    nonexisting_ids=nonexisting_ids_st,
)
def test_batch_get_returns_exactly_existing_subset(existing_ids, nonexisting_ids):
    """
    Property 3: Batch-get returns exactly the existing subset.

    **Validates: Requirements 6.1, 6.4**

    For any list of product IDs passed to get_products, the response SHALL contain
    exactly the set of products whose IDs both appear in the request AND exist in
    DynamoDB — no more, no less.
    """
    # Ensure non-existing IDs don't overlap with existing IDs
    nonexisting_ids = nonexisting_ids - existing_ids
    assume(len(existing_ids) > 0)

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

        # Build request with a mix of existing + non-existing IDs
        # Request a subset of existing IDs plus all non-existing IDs
        requested_existing = set(list(existing_ids)[:max(1, len(existing_ids))])
        requested_ids = requested_existing | nonexisting_ids
        assume(len(requested_ids) > 0)

        product_ids_csv = ','.join(requested_ids)
        api_event = _make_event(product_ids_csv)

        with _auth_patches():
            response = handler_module.lambda_handler(api_event, {})

        # Should return 200
        assert response['statusCode'] == 200, (
            f"Expected 200, got {response['statusCode']}: {response['body']}"
        )

        body = json.loads(response['body'])
        returned_products = body['products']
        returned_ids = {p['product_id'] for p in returned_products}

        # The expected result is the intersection of requested IDs and existing IDs
        expected_ids = requested_ids & existing_ids

        # Assert: returned IDs exactly match the expected intersection
        assert returned_ids == expected_ids, (
            f"Expected products {expected_ids}, got {returned_ids}. "
            f"Missing: {expected_ids - returned_ids}, "
            f"Extra: {returned_ids - expected_ids}"
        )
