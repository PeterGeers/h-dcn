"""
Unit tests for the insert_product handler.

Tests:
- Happy path: product created successfully and stored in DynamoDB
- Unauthorized: returns 403 when user lacks permissions
- Invalid request: missing body or invalid JSON returns 400
- Canonical Dutch field names are stored correctly (naam, prijs)
- Financial fields stored as DynamoDB Number type (Decimal)
- Image field converted to array when string is provided
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal

import boto3
import pytest
from unittest.mock import patch
from moto import mock_aws

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Path to the handler module
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'insert_product', 'app.py')
)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _load_handler():
    """Load the insert_product handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event(body: dict | None = None, method: str = 'POST') -> dict:
    """Create a mock API Gateway event for insert_product."""
    return {
        'httpMethod': method,
        'body': json.dumps(body) if body is not None else None,
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
    """Return a context manager that patches auth functions for authorized access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _unauthorized_patches():
    """Return a context manager that patches auth to simulate unauthorized access."""
    from shared.auth_utils import create_error_response
    error_resp = create_error_response(403, 'Insufficient permissions')
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('viewer@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, error_resp, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table and load the handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        yield table, handler_module


class TestInsertProductHappyPath:
    """Tests for successful product creation."""

    def test_creates_product_successfully(self, producten_table):
        """Happy path: inserts product and returns 201 with product_id."""
        table, handler = producten_table

        event = _make_event(body={
            'naam': 'Club T-shirt',
            'prijs': 25,
            'artikelcode': 'CT-01',
            'active': True,
            'is_parent': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'product_id' in body
        assert body['message'] == 'Product created successfully'

        # Verify product is stored in DynamoDB
        stored = table.get_item(Key={'product_id': body['product_id']})
        assert 'Item' in stored
        item = stored['Item']
        assert item['naam'] == 'Club T-shirt'
        assert item['artikelcode'] == 'CT-01'
        assert item['active'] is True
        assert item['is_parent'] is True

    def test_generates_unique_product_id(self, producten_table):
        """Each inserted product gets a unique UUID product_id."""
        table, handler = producten_table

        event1 = _make_event(body={'naam': 'Product A', 'prijs': 10})
        event2 = _make_event(body={'naam': 'Product B', 'prijs': 20})

        with _auth_patches():
            resp1 = handler.lambda_handler(event1, {})
            resp2 = handler.lambda_handler(event2, {})

        id1 = json.loads(resp1['body'])['product_id']
        id2 = json.loads(resp2['body'])['product_id']
        assert id1 != id2

    def test_adds_created_at_timestamp(self, producten_table):
        """Inserted product gets a createdAt timestamp."""
        table, handler = producten_table

        event = _make_event(body={'naam': 'Sticker', 'prijs': 5})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        product_id = json.loads(response['body'])['product_id']
        stored = table.get_item(Key={'product_id': product_id})
        assert 'createdAt' in stored['Item']

    def test_image_string_converted_to_array(self, producten_table):
        """When image is a string, it is stored as a single-element array."""
        table, handler = producten_table

        event = _make_event(body={
            'naam': 'Pet H-DCN',
            'prijs': 15,
            'image': 'https://s3.eu-west-1.amazonaws.com/bucket/pet.jpg',
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        product_id = json.loads(response['body'])['product_id']
        stored = table.get_item(Key={'product_id': product_id})
        item = stored['Item']
        assert item['image'] == ['https://s3.eu-west-1.amazonaws.com/bucket/pet.jpg']


class TestInsertProductUnauthorized:
    """Tests for unauthorized access."""

    def test_returns_403_when_user_lacks_permission(self, producten_table):
        """Returns 403 when user does not have products_create permission."""
        table, handler = producten_table

        event = _make_event(body={'naam': 'Product', 'prijs': 10})

        with _unauthorized_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 403

    def test_returns_auth_error_when_credentials_invalid(self, producten_table):
        """Returns error when extract_user_credentials fails."""
        table, handler = producten_table

        from shared.auth_utils import create_error_response
        auth_error = create_error_response(401, 'Invalid token')

        with patch.multiple(
            'app',
            extract_user_credentials=lambda event: (None, None, auth_error),
            validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
            log_successful_access=lambda *a, **kw: None,
        ):
            event = _make_event(body={'naam': 'Test', 'prijs': 10})
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 401


class TestInsertProductValidation:
    """Tests for input validation and error handling."""

    def test_returns_400_for_invalid_json(self, producten_table):
        """Returns 400 when request body is not valid JSON."""
        table, handler = producten_table

        event = {
            'httpMethod': 'POST',
            'body': 'not valid json{{{',
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

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body.get('error', body.get('message', ''))

    def test_handles_empty_body_gracefully(self, producten_table):
        """Handles null/empty body — creates product with only generated fields."""
        table, handler = producten_table

        event = _make_event(body={})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        # Handler creates product even with empty body (no server-side required field validation)
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'product_id' in body

    def test_handles_options_request(self, producten_table):
        """OPTIONS request returns CORS preflight response."""
        table, handler = producten_table

        event = _make_event(method='OPTIONS')

        response = handler.lambda_handler(event, {})
        assert response['statusCode'] == 200


class TestInsertProductDutchFields:
    """Tests verifying canonical Dutch field names are used."""

    def test_stores_naam_field(self, producten_table):
        """Product name stored under canonical 'naam' field."""
        table, handler = producten_table

        event = _make_event(body={'naam': 'Ledenvest', 'prijs': 75})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        product_id = json.loads(response['body'])['product_id']
        stored = table.get_item(Key={'product_id': product_id})
        assert stored['Item']['naam'] == 'Ledenvest'

    def test_stores_prijs_as_number_type(self, producten_table):
        """Financial field 'prijs' is stored as DynamoDB Number (Decimal)."""
        table, handler = producten_table

        # Send integer price (as frontend typically does via JSON)
        event = _make_event(body={'naam': 'Mok', 'prijs': 12})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        product_id = json.loads(response['body'])['product_id']
        stored = table.get_item(Key={'product_id': product_id})
        # DynamoDB/boto3 stores numbers as Decimal
        assert stored['Item']['prijs'] == Decimal('12')

    def test_stores_groep_and_subgroep(self, producten_table):
        """Category fields use canonical Dutch names groep/subgroep."""
        table, handler = producten_table

        event = _make_event(body={
            'naam': 'Helm Sticker',
            'prijs': 3,
            'groep': 'Accessoires',
            'subgroep': 'Stickers',
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        product_id = json.loads(response['body'])['product_id']
        stored = table.get_item(Key={'product_id': product_id})
        assert stored['Item']['groep'] == 'Accessoires'
        assert stored['Item']['subgroep'] == 'Stickers'
