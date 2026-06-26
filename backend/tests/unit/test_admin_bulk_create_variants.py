"""
Unit tests for the admin_bulk_create_variants handler.

Tests:
- Happy path: creates variants from required_attributes on parent product
- Unauthorized: returns 403 when permissions are insufficient
- Invalid input: returns 400 for malformed request body (invalid JSON)
- Edge case: parent has no required_attributes
- Edge case: non-parent product returns 400
- Parent product not found returns 404
- Missing product_id returns 400
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
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_bulk_create_variants', 'app.py')
)

# Load the handler-local variant_helpers (single-arg generate_variant_combinations)
# The auth-layer version has a different signature; the handler intends to use this one.
_variant_helpers_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'shared', 'variant_helpers.py')
)


def _load_variant_helpers():
    """Load the handler-local variant_helpers module."""
    spec = importlib.util.spec_from_file_location('_handler_variant_helpers', _variant_helpers_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_handler():
    """Load handler module by file path, bypassing sys.path.

    Patches shared.variant_helpers to use the handler-local version
    (which has the correct single-arg signature for generate_variant_combinations).
    """
    if 'app' in sys.modules:
        del sys.modules['app']

    # Load the handler-local variant helpers first
    local_helpers = _load_variant_helpers()

    # Patch shared.variant_helpers in sys.modules so the handler imports the correct version
    if 'shared.variant_helpers' in sys.modules:
        del sys.modules['shared.variant_helpers']

    # Create a patched shared.variant_helpers module
    import types
    patched_module = types.ModuleType('shared.variant_helpers')
    patched_module.generate_variant_combinations = local_helpers.generate_variant_combinations
    patched_module.should_remove_default_variant = local_helpers.should_remove_default_variant
    sys.modules['shared.variant_helpers'] = patched_module

    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event(product_id: str = 'prod-1', body: dict = None) -> dict:
    """Create a mock API Gateway POST event for bulk variant creation."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id} if product_id else None,
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
    """Return a context manager that patches auth functions to deny access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('viewer@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (
            False,
            {'statusCode': 403, 'headers': {}, 'body': json.dumps({'error': 'Insufficient permissions'})},
            {}
        ),
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


class TestBulkCreateVariantsHappyPath:
    """Tests for successful bulk variant creation."""

    def test_creates_variants_from_single_axis(self, producten_table):
        """Creates variants for a parent with one required_attributes axis."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'prijs': '25',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Maat': {'type': 'string', 'enum': ['S', 'M', 'L']}
                }
            },
        })

        event = _make_event('prod-1')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_created'] == 3
        assert len(body['variants']) == 3
        assert 'variants created successfully' in body['message']

    def test_creates_variants_from_multiple_axes(self, producten_table):
        """Creates cartesian product of variants for multiple axes."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-2',
            'naam': 'Club Polo',
            'prijs': '35',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Maat': {'type': 'string', 'enum': ['S', 'M']},
                    'Kleur': {'type': 'string', 'enum': ['Zwart', 'Wit']}
                }
            },
        })

        event = _make_event('prod-2')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # 2 sizes × 2 colors = 4 variants
        assert body['total_created'] == 4
        assert len(body['variants']) == 4

    def test_variants_stored_in_dynamodb(self, producten_table):
        """Verifies variants are actually written to DynamoDB."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Pin',
            'prijs': '5',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Kleur': {'type': 'string', 'enum': ['Goud', 'Zilver']}
                }
            },
        })

        event = _make_event('prod-1')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Verify each created variant is in DynamoDB
        for variant in body['variants']:
            item_response = table.get_item(Key={'product_id': variant['product_id']})
            assert 'Item' in item_response
            assert item_response['Item']['parent_id'] == 'prod-1'
            assert item_response['Item']['is_parent'] is False

    def test_respects_body_defaults(self, producten_table):
        """Request body can override default price, stock, and allow_oversell."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Sticker',
            'prijs': '3',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Type': {'type': 'string', 'enum': ['Logo']}
                }
            },
        })

        event = _make_event('prod-1', body={
            'price': '10',
            'stock': 50,
            'allow_oversell': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        variant = body['variants'][0]
        assert variant['stock'] == 50
        assert variant['allow_oversell'] is True


class TestBulkCreateVariantsAuth:
    """Tests for authorization enforcement."""

    def test_unauthorized_returns_403(self, producten_table):
        """Returns 403 when user lacks Products_CRUD permission."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Maat': {'type': 'string', 'enum': ['S', 'M']}
                }
            },
        })

        event = _make_event('prod-1')

        with _unauthorized_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'permissions' in body['error'].lower() or 'Insufficient' in body['error']


class TestBulkCreateVariantsValidation:
    """Tests for input validation and error handling."""

    def test_invalid_json_body_returns_400(self, producten_table):
        """Returns 400 for invalid JSON in request body."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'is_parent': True,
            'active': True,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'Maat': {'type': 'string', 'enum': ['S']}
                }
            },
        })

        event = {
            'httpMethod': 'POST',
            'pathParameters': {'id': 'prod-1'},
            'body': '{invalid-json!!!',
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

    def test_missing_product_id_returns_400(self, producten_table):
        """Returns 400 when product_id is missing from path."""
        table, handler = producten_table

        event = {
            'httpMethod': 'POST',
            'pathParameters': {},
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

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'required' in body['error'].lower() or 'Product ID' in body['error']

    def test_non_parent_product_returns_400(self, producten_table):
        """Returns 400 when target product is not a parent."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'var-1',
            'naam': 'T-shirt M',
            'is_parent': False,
            'active': True,
            'parent_id': 'prod-parent',
        })

        event = _make_event('var-1')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'non-parent' in body['error'].lower() or 'Cannot add variants' in body['error']

    def test_parent_not_found_returns_404(self, producten_table):
        """Returns 404 when parent product doesn't exist."""
        table, handler = producten_table

        event = _make_event('nonexistent-prod')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()

    def test_no_required_attributes_returns_400(self, producten_table):
        """Returns 400 when parent has no required_attributes defined."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Simple Product',
            'is_parent': True,
            'active': True,
            # No required_attributes
        })

        event = _make_event('prod-1')

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'required_attributes' in body['error']
