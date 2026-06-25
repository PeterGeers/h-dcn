"""
Unit tests for the get_products handler (batch-get-by-IDs).

Tests the rewritten handler that accepts product_ids as a comma-separated
query parameter and returns those specific products via DynamoDB BatchGetItem.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import importlib.util
import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

# Environment setup
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler file path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_products', 'app.py')
)

# Expose handler path for conftest cleanup
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_products')
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


def _auth_patches():
    """Patch auth layer to allow all requests with hdcnLeden role."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['hdcnLeden'], None),
        log_successful_access=lambda *a, **kw: None,
    )


def _build_event(product_ids=None, include_param=True):
    """Build an API Gateway event for the get_products handler.

    Args:
        product_ids: Comma-separated string of product IDs, or None for empty string.
        include_param: If False, omits the product_ids param entirely.
    """
    event = {
        'httpMethod': 'GET',
        'headers': {'Authorization': 'Bearer fake-token'},
        'queryStringParameters': {},
    }
    if include_param:
        event['queryStringParameters']['product_ids'] = product_ids if product_ids is not None else ''
    else:
        # Missing product_ids param entirely
        event['queryStringParameters'] = {}
    return event


def _create_producten_table(dynamodb):
    """Create the Producten table."""
    return dynamodb.create_table(
        TableName='Producten',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


@pytest.fixture
def setup_table():
    """Create mocked Producten table, load handler inside mock context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)

        # Seed a few products
        table.put_item(Item={
            'product_id': 'prod_001',
            'naam': 'H-DCN T-shirt',
            'prijs': Decimal('25.00'),
            'active': True,
        })
        table.put_item(Item={
            'product_id': 'prod_002',
            'naam': 'H-DCN Pet',
            'prijs': Decimal('15.00'),
            'active': True,
        })
        table.put_item(Item={
            'product_id': 'prod_003',
            'naam': 'H-DCN Mok',
            'prijs': Decimal('10.00'),
            'active': True,
        })

        handler_module = _load_handler()
        yield table, handler_module


class TestGetProductsEmptyIds:
    """Test empty product_ids returns empty list (200).

    Validates: Requirement 6.3
    """

    def test_empty_string_product_ids_returns_200_empty(self, setup_table):
        """Empty product_ids param returns 200 with empty products list."""
        table, handler_module = setup_table
        event = _build_event(product_ids='')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['products'] == []
        assert body['total_count'] == 0

    def test_whitespace_only_product_ids_returns_200_empty(self, setup_table):
        """Whitespace-only product_ids returns 200 with empty products list."""
        table, handler_module = setup_table
        event = _build_event(product_ids='   ')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['products'] == []
        assert body['total_count'] == 0


class TestGetProductsMissingParam:
    """Test missing product_ids param returns 400.

    Validates: Requirement 6.2
    """

    def test_missing_product_ids_param_returns_400(self, setup_table):
        """Missing product_ids query parameter returns 400 error."""
        table, handler_module = setup_table
        event = _build_event(include_param=False)
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'product_ids' in body.get('error', '').lower()

    def test_null_query_string_parameters_returns_400(self, setup_table):
        """queryStringParameters being None returns 400."""
        table, handler_module = setup_table
        event = {
            'httpMethod': 'GET',
            'headers': {'Authorization': 'Bearer fake-token'},
            'queryStringParameters': None,
        }
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 400


class TestGetProductsNonExistentIds:
    """Test non-existent IDs are silently omitted.

    Validates: Requirement 6.4
    """

    def test_nonexistent_ids_omitted(self, setup_table):
        """Non-existent product IDs are silently omitted from response."""
        table, handler_module = setup_table
        event = _build_event(product_ids='prod_001,nonexistent_999,prod_002')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_ids = {p['product_id'] for p in body['products']}
        assert returned_ids == {'prod_001', 'prod_002'}
        assert body['total_count'] == 2

    def test_all_nonexistent_ids_returns_empty(self, setup_table):
        """All non-existent IDs returns 200 with empty list."""
        table, handler_module = setup_table
        event = _build_event(product_ids='fake_001,fake_002,fake_003')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['products'] == []
        assert body['total_count'] == 0

    def test_single_existing_id_returned(self, setup_table):
        """A single existing product ID is returned correctly."""
        table, handler_module = setup_table
        event = _build_event(product_ids='prod_003')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['products']) == 1
        assert body['products'][0]['product_id'] == 'prod_003'


class TestGetProductsChunking:
    """Test >100 IDs are chunked correctly for DynamoDB BatchGetItem.

    Validates: Requirements 6.1, 6.4
    """

    def test_more_than_100_ids_chunked(self, setup_table):
        """IDs exceeding 100 are processed in chunks via BatchGetItem."""
        table, handler_module = setup_table

        # Insert 150 products
        for i in range(150):
            table.put_item(Item={
                'product_id': f'bulk_{i:04d}',
                'naam': f'Bulk Product {i}',
                'prijs': Decimal('5.00'),
            })

        # Request all 150
        ids_list = [f'bulk_{i:04d}' for i in range(150)]
        product_ids_str = ','.join(ids_list)
        event = _build_event(product_ids=product_ids_str)
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_count'] == 150
        returned_ids = {p['product_id'] for p in body['products']}
        assert returned_ids == set(ids_list)

    def test_exactly_100_ids_no_chunking_needed(self, setup_table):
        """Exactly 100 IDs does not require chunking (single batch)."""
        table, handler_module = setup_table

        # Insert 100 products
        for i in range(100):
            table.put_item(Item={
                'product_id': f'exact_{i:03d}',
                'naam': f'Product {i}',
                'prijs': Decimal('1.00'),
            })

        ids_list = [f'exact_{i:03d}' for i in range(100)]
        product_ids_str = ','.join(ids_list)
        event = _build_event(product_ids=product_ids_str)
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_count'] == 100

    def test_101_ids_with_some_nonexistent(self, setup_table):
        """101 IDs with some non-existent are chunked; missing IDs omitted."""
        table, handler_module = setup_table

        # Insert only 50 products
        for i in range(50):
            table.put_item(Item={
                'product_id': f'chunk_{i:03d}',
                'naam': f'Chunk Product {i}',
                'prijs': Decimal('3.00'),
            })

        # Request 101 IDs — 50 exist, 51 don't
        ids_list = [f'chunk_{i:03d}' for i in range(101)]
        product_ids_str = ','.join(ids_list)
        event = _build_event(product_ids=product_ids_str)
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Only the 50 that exist should be returned
        assert body['total_count'] == 50


class TestGetProductsDuplicateIds:
    """Test that duplicate IDs are deduplicated."""

    def test_duplicate_ids_deduplicated(self, setup_table):
        """Duplicate product IDs in the request are deduplicated."""
        table, handler_module = setup_table
        event = _build_event(product_ids='prod_001,prod_001,prod_002,prod_002,prod_002')
        with _auth_patches():
            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        returned_ids = [p['product_id'] for p in body['products']]
        # Each product returned at most once
        assert len(returned_ids) == len(set(returned_ids))
        assert set(returned_ids) == {'prod_001', 'prod_002'}
