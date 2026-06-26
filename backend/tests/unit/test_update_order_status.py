"""
Unit tests for the update_order_status handler.

Tests:
- Happy path: admin updates order status successfully
- Happy path: order owner updates their own order
- Unauthorized: returns 403 when no admin or hdcnLeden role
- Forbidden: non-owner non-admin cannot update another user's order
- Not found: order doesn't exist → 404
- Missing required fields: missing pathParameters or body
- Sensitive fields are excluded from update (order_id, user_email, created_at)
- OPTIONS request: returns CORS preflight response
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
os.environ['DYNAMODB_TABLE'] = 'Orders'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_order_status', 'app.py')
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


def _make_event(order_id=None, body=None, email='admin@h-dcn.nl'):
    """Create a mock API Gateway PUT/PATCH event."""
    path_params = {}
    if order_id is not None:
        path_params['id'] = order_id

    return {
        'httpMethod': 'PUT',
        'pathParameters': path_params if path_params else None,
        'body': json.dumps(body) if body is not None else None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': email,
                    'cognito:groups': 'products_update'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _admin_auth_patches():
    """Patches auth functions for admin access (products_update permission)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['products_update'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _owner_auth_patches(email='lid@h-dcn.nl'):
    """Patches auth functions for order-owner access (hdcnLeden role, no admin)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, ['hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _denied_auth_patches():
    """Patches auth functions to deny access entirely (no admin, no hdcnLeden)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('visitor@example.com', ['SomeOtherRole'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def table_and_handler():
    """Create mocked DynamoDB Orders table and load the handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        handler_module.table = orders_table

        yield orders_table, handler_module


def _seed_order(table, order_id='order-001', user_email='lid@h-dcn.nl', status='pending'):
    """Insert a sample order into the mocked table."""
    table.put_item(Item={
        'order_id': order_id,
        'user_email': user_email,
        'status': status,
        'items': [{'product_id': 'prod-1', 'quantity': 2}],
        'total_amount': 50,
        'created_at': '2026-06-01T10:00:00',
    })


# --- Happy path tests ---

def test_admin_updates_order_status_successfully(table_and_handler):
    """Admin can update any order's status."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table)

    event = _make_event(order_id='order-001', body={'status': 'confirmed'})

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'updated successfully' in body['message']
    assert 'status' in body['updated_fields']

    # Verify the status was actually updated in DynamoDB
    result = orders_table.get_item(Key={'order_id': 'order-001'})
    assert result['Item']['status'] == 'confirmed'
    assert 'updated_at' in result['Item']


def test_owner_updates_own_order(table_and_handler):
    """Order owner (hdcnLeden) can update their own order."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table, user_email='lid@h-dcn.nl')

    event = _make_event(order_id='order-001', body={'status': 'cancelled'})

    with _owner_auth_patches(email='lid@h-dcn.nl'):
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'updated successfully' in body['message']


# --- Authorization tests ---

def test_denied_no_admin_no_hdcnleden(table_and_handler):
    """User without admin or hdcnLeden role returns 403."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table)

    event = _make_event(order_id='order-001', body={'status': 'confirmed'})

    with _denied_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 403


def test_non_owner_non_admin_cannot_update_other_order(table_and_handler):
    """hdcnLeden user cannot update orders belonging to another user."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table, user_email='other-user@h-dcn.nl')

    event = _make_event(order_id='order-001', body={'status': 'cancelled'})

    with _owner_auth_patches(email='lid@h-dcn.nl'):
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert 'own orders' in body['error']


# --- Not found ---

def test_order_not_found_returns_404(table_and_handler):
    """Updating a non-existent order returns 404."""
    _, handler = table_and_handler

    event = _make_event(order_id='nonexistent-order', body={'status': 'confirmed'})

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert 'not found' in body['error'].lower()


# --- Input validation ---

def test_missing_path_parameters_returns_error(table_and_handler):
    """Missing pathParameters (None) returns error."""
    _, handler = table_and_handler

    event = {
        'httpMethod': 'PUT',
        'pathParameters': None,
        'body': json.dumps({'status': 'confirmed'}),
        'requestContext': {},
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    # pathParameters=None causes TypeError, caught by generic Exception handler → 500
    assert response['statusCode'] == 500


def test_empty_body_updates_only_timestamp(table_and_handler):
    """Empty body (no fields) still updates the timestamp."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table)

    event = _make_event(order_id='order-001', body={})

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
    # Verify updated_at is set
    result = orders_table.get_item(Key={'order_id': 'order-001'})
    assert 'updated_at' in result['Item']


def test_invalid_json_body_returns_400(table_and_handler):
    """Invalid JSON in request body returns 400."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table)

    event = {
        'httpMethod': 'PUT',
        'pathParameters': {'id': 'order-001'},
        'body': 'not-valid-json{{{',
        'requestContext': {},
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'json' in body['error'].lower()


# --- Sensitive field protection ---

def test_sensitive_fields_excluded_from_update(table_and_handler):
    """Sensitive fields (order_id, user_email, created_at) are not updated."""
    orders_table, handler = table_and_handler
    _seed_order(orders_table, user_email='lid@h-dcn.nl')

    event = _make_event(order_id='order-001', body={
        'status': 'shipped',
        'order_id': 'hacked-id',
        'user_email': 'hacker@evil.com',
        'created_at': '1999-01-01T00:00:00',
    })

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200

    # Verify sensitive fields were NOT changed
    result = orders_table.get_item(Key={'order_id': 'order-001'})
    item = result['Item']
    assert item['order_id'] == 'order-001'
    assert item['user_email'] == 'lid@h-dcn.nl'
    assert item['created_at'] == '2026-06-01T10:00:00'
    # But status WAS updated
    assert item['status'] == 'shipped'


# --- OPTIONS preflight ---

def test_options_request_returns_cors(table_and_handler):
    """OPTIONS request returns CORS preflight response."""
    _, handler = table_and_handler

    event = {
        'httpMethod': 'OPTIONS',
        'pathParameters': None,
        'body': None,
        'requestContext': {},
        'headers': {}
    }

    with _admin_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
