"""
Unit tests for the get_product_byid handler.

Tests:
- Successful retrieval using product_id key
- 404 when product not found
- 400 when product ID is missing from path parameters
"""

import json
import os
import sys
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_product_byid')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _make_event(product_id=None):
    """Create a mock API Gateway event for GET /get-product-byid/{id}."""
    event = {
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
    if product_id is not None:
        event['pathParameters'] = {'id': product_id}
    else:
        event['pathParameters'] = None
    return event


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table with product_id as key."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Ensure our handler path is first in sys.path so `import app` resolves correctly
        if sys.path[0] != _handler_path:
            if _handler_path in sys.path:
                sys.path.remove(_handler_path)
            sys.path.insert(0, _handler_path)

        # Clear any stale app module cache
        if 'app' in sys.modules:
            del sys.modules['app']

        import app as handler_module
        handler_module.table = table

        yield table


def test_get_product_by_product_id(producten_table):
    """Successfully retrieves a product using product_id key."""
    import app as handler_module

    # Insert a product with product_id key
    # Use string for price to avoid Decimal serialization issues in moto
    producten_table.put_item(Item={
        'product_id': 'abc-123-uuid',
        'name': 'Club T-shirt',
        'price': '25',
        'is_parent': True,
        'active': True,
    })

    event = _make_event('abc-123-uuid')

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['product_id'] == 'abc-123-uuid'
    assert body['name'] == 'Club T-shirt'


def test_get_product_not_found_returns_404(producten_table):
    """Returns 404 when product_id does not exist."""
    import app as handler_module

    event = _make_event('non-existent-id')

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert 'not found' in body['error'].lower()


def test_missing_product_id_returns_400(producten_table):
    """Returns 400 when path parameters are missing."""
    import app as handler_module

    event = _make_event()  # No product_id in path

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'Missing' in body['error'] or 'product' in body['error'].lower()
