"""
Unit tests for the admin_create_variant handler.

Tests:
- Successful variant creation with variant_attributes
- Variant creation succeeds even when parent has variant_schema stored (no validation against it)
- Duplicate variant_attributes rejected with 409
- Missing parent product returns 404
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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_variant', 'app.py')
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


def _make_event(product_id='prod-1', variant_attributes=None, extra_body=None):
    """Create a mock API Gateway POST event for variant creation."""
    body = {}
    if variant_attributes is not None:
        body['variant_attributes'] = variant_attributes
    if extra_body:
        body.update(extra_body)

    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id} if product_id else None,
        'body': json.dumps(body),
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


class TestAdminCreateVariantNoSchemaValidation:
    """Tests verifying admin_create_variant does NOT validate against variant_schema."""

    def test_create_variant_ignores_variant_schema_on_parent(self, producten_table):
        """Variant creation succeeds even when attributes don't match parent's variant_schema.

        Previously, the handler would reject a variant if its attributes didn't
        match the parent's variant_schema. This test verifies that validation is removed.
        """
        table, handler = producten_table

        # Create a parent product with a variant_schema that only allows "Maat" axis
        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'prijs': '25',
            'is_parent': True,
            'active': True,
            'variant_schema': {'Maat': ['S', 'M', 'L']},
        })

        # Create variant with "Kleur" axis — NOT in the variant_schema
        # This should succeed because we no longer validate against variant_schema
        event = _make_event('prod-1', variant_attributes={'Kleur': 'Rood'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Variant created successfully'
        assert body['variant']['variant_attributes'] == {'Kleur': 'Rood'}

    def test_create_variant_with_new_axis_name_succeeds(self, producten_table):
        """Variant with a completely new axis name succeeds (no schema enforcement)."""
        table, handler = producten_table

        # Parent with a schema that lists specific axes
        table.put_item(Item={
            'product_id': 'prod-2',
            'naam': 'Pet H-DCN',
            'prijs': '15',
            'is_parent': True,
            'active': True,
            'variant_schema': {'Maat': ['One Size'], 'Kleur': ['Zwart', 'Wit']},
        })

        # Create variant with axis "Materiaal" — not in schema at all
        event = _make_event('prod-2', variant_attributes={'Materiaal': 'Katoen'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variant']['variant_attributes'] == {'Materiaal': 'Katoen'}

    def test_create_variant_with_value_not_in_schema_succeeds(self, producten_table):
        """Variant with an axis value not listed in variant_schema succeeds."""
        table, handler = producten_table

        # Parent's schema only lists S, M, L for Maat
        table.put_item(Item={
            'product_id': 'prod-3',
            'naam': 'Hoodie',
            'prijs': '45',
            'is_parent': True,
            'active': True,
            'variant_schema': {'Maat': ['S', 'M', 'L']},
        })

        # Create variant with value "XXL" — not in the schema's allowed values
        event = _make_event('prod-3', variant_attributes={'Maat': 'XXL'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variant']['variant_attributes'] == {'Maat': 'XXL'}


class TestAdminCreateVariantBasic:
    """Basic operation tests for admin_create_variant."""

    def test_create_variant_success(self, producten_table):
        """Successful variant creation with valid attributes."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'prijs': '25',
            'is_parent': True,
            'active': True,
        })

        event = _make_event('prod-1', variant_attributes={'Maat': 'M'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Variant created successfully'
        variant = body['variant']
        assert variant['parent_id'] == 'prod-1'
        assert variant['variant_attributes'] == {'Maat': 'M'}
        assert variant['is_parent'] is False

    def test_duplicate_variant_rejected(self, producten_table):
        """Duplicate variant_attributes for same parent returns 409."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-1',
            'naam': 'Club T-shirt',
            'prijs': '25',
            'is_parent': True,
            'active': True,
        })

        # Create first variant
        table.put_item(Item={
            'product_id': 'var-existing',
            'parent_id': 'prod-1',
            'is_parent': False,
            'variant_attributes': {'Maat': 'M'},
            'active': True,
        })

        # Try to create another variant with same attributes
        event = _make_event('prod-1', variant_attributes={'Maat': 'M'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'already exists' in body['error']

    def test_parent_not_found_returns_404(self, producten_table):
        """Creating a variant for a non-existent parent returns 404."""
        table, handler = producten_table

        event = _make_event('nonexistent-prod', variant_attributes={'Maat': 'S'})

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error']

    def test_missing_product_id_returns_400(self, producten_table):
        """Missing product ID in path returns 400."""
        table, handler = producten_table

        event = {
            'httpMethod': 'POST',
            'pathParameters': {},
            'body': json.dumps({'variant_attributes': {'Maat': 'S'}}),
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
        assert 'required' in body['error'].lower()
