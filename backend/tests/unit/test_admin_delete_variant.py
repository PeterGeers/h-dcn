"""
Unit tests for the admin_delete_variant handler.

Tests:
- Successful deletion when no orders reference the variant
- 409 Conflict when orders reference the variant
- 404 when variant not found
- 400 when variant doesn't belong to product
- 400 when path parameters are missing
- Auth permission check
"""

import json
import os
import sys
import importlib.util
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

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


def _make_event(product_id=None, variant_id=None):
    """Create a mock API Gateway DELETE event."""
    path_params = {}
    if product_id is not None:
        path_params['id'] = product_id
    if variant_id is not None:
        path_params['vid'] = variant_id

    return {
        'httpMethod': 'DELETE',
        'pathParameters': path_params if path_params else None,
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


def _denied_auth_patches():
    """Return a context manager that patches auth functions to deny access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('viewer@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (
            False,
            {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'})},
            {}
        ),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def tables_and_handler():
    """Create mocked DynamoDB tables and load the handler."""
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

        handler_module = _load_handler()
        handler_module.table = producten
        handler_module.orders_table = orders

        yield producten, orders, handler_module


def test_delete_variant_success(tables_and_handler):
    """Variant with no order references is deleted successfully."""
    producten, orders, handler = tables_and_handler

    # Create parent product
    producten.put_item(Item={
        'product_id': 'prod-1',
        'is_parent': True,
        'variant_schema': {'Maat': ['S', 'M', 'L']},
    })

    # Create variant
    producten.put_item(Item={
        'product_id': 'var-1',
        'parent_id': 'prod-1',
        'is_parent': False,
        'variant_attributes': {'Maat': 'M'},
        'active': True,
        'stock': 5,
    })

    event = _make_event('prod-1', 'var-1')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'deleted successfully' in body['message']

    # Verify variant is gone
    result = producten.get_item(Key={'product_id': 'var-1'})
    assert 'Item' not in result


def test_delete_variant_blocked_by_orders(tables_and_handler):
    """Variant referenced by orders returns 409 Conflict."""
    producten, orders, handler = tables_and_handler

    # Create parent and variant
    producten.put_item(Item={
        'product_id': 'prod-1',
        'is_parent': True,
        'variant_schema': {'Maat': ['S', 'M']},
    })
    producten.put_item(Item={
        'product_id': 'var-1',
        'parent_id': 'prod-1',
        'is_parent': False,
        'variant_attributes': {'Maat': 'M'},
        'active': True,
    })

    # Create orders referencing this variant
    orders.put_item(Item={
        'order_id': 'order-1',
        'line_items': [{'variant_id': 'var-1', 'quantity': 2}],
    })
    orders.put_item(Item={
        'order_id': 'order-2',
        'line_items': [{'variant_id': 'var-1', 'quantity': 1}],
    })

    event = _make_event('prod-1', 'var-1')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 409
    body = json.loads(response['body'])
    assert 'referenced by 2 order(s)' in body['error']
    assert 'Deactivate instead' in body['error']

    # Verify variant still exists
    result = producten.get_item(Key={'product_id': 'var-1'})
    assert 'Item' in result


def test_delete_variant_not_found(tables_and_handler):
    """Non-existent variant returns 404."""
    producten, orders, handler = tables_and_handler

    event = _make_event('prod-1', 'nonexistent-var')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert 'Variant not found' in body['error']


def test_delete_variant_wrong_parent(tables_and_handler):
    """Variant not belonging to specified product returns 400."""
    producten, orders, handler = tables_and_handler

    # Create variant belonging to a different product
    producten.put_item(Item={
        'product_id': 'var-1',
        'parent_id': 'prod-other',
        'is_parent': False,
        'variant_attributes': {'Maat': 'M'},
        'active': True,
    })

    event = _make_event('prod-1', 'var-1')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'does not belong to the specified product' in body['error']


def test_delete_variant_missing_path_params(tables_and_handler):
    """Missing path parameters returns 400."""
    _, _, handler = tables_and_handler

    # Missing variant_id
    event = _make_event('prod-1', None)

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'Product ID and Variant ID are required' in body['error']


def test_delete_variant_no_path_params(tables_and_handler):
    """No path parameters at all returns 400."""
    _, _, handler = tables_and_handler

    event = {
        'httpMethod': 'DELETE',
        'pathParameters': None,
        'body': None,
        'requestContext': {'authorizer': {'claims': {}}},
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_delete_variant_permission_denied(tables_and_handler):
    """User without Products_CRUD permission is denied."""
    _, _, handler = tables_and_handler

    event = _make_event('prod-1', 'var-1')

    with _denied_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 403


def test_delete_variant_does_not_modify_parent_schema(tables_and_handler):
    """After deletion, parent record is not modified (no schema rebuild)."""
    producten, orders, handler = tables_and_handler

    # Create parent
    producten.put_item(Item={
        'product_id': 'prod-1',
        'is_parent': True,
        'variant_schema': {'Maat': ['S', 'M', 'L']},
    })

    # Create variants: S, M, L
    producten.put_item(Item={
        'product_id': 'var-s',
        'parent_id': 'prod-1',
        'is_parent': False,
        'variant_attributes': {'Maat': 'S'},
        'active': True,
    })
    producten.put_item(Item={
        'product_id': 'var-m',
        'parent_id': 'prod-1',
        'is_parent': False,
        'variant_attributes': {'Maat': 'M'},
        'active': True,
    })
    producten.put_item(Item={
        'product_id': 'var-l',
        'parent_id': 'prod-1',
        'is_parent': False,
        'variant_attributes': {'Maat': 'L'},
        'active': True,
    })

    # Delete var-m
    event = _make_event('prod-1', 'var-m')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200

    # Verify parent schema is unchanged (no sync rebuild happens)
    parent = producten.get_item(Key={'product_id': 'prod-1'})['Item']
    schema = parent.get('variant_schema', {})
    # Schema is NOT rebuilt — stays as-is from before deletion
    assert schema == {'Maat': ['S', 'M', 'L']}
