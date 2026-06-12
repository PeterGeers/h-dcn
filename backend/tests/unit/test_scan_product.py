"""
Unit tests for the scan_product handler.

Tests:
- Unified response normalization (product_id, name, price, variant_schema, is_parent, event_id, active)
- Fallback: naam → name, prijs → price
- Exclusion of variant records (is_parent: false)
- Exclusion of migration source records (source: "migration")
- Retention of records where is_parent is true or not set
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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _make_event():
    """Create a mock API Gateway event for GET /scan-product/."""
    return {
        'httpMethod': 'GET',
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Products_Read'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Ensure handler path is first in sys.path (critical for full-suite runs)
        handler_base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
        )
        handler_base_n = os.path.normpath(handler_base) + os.sep
        sys.path[:] = [
            p for p in sys.path
            if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
            and os.path.normpath(p) != os.path.normpath(handler_base)
        ]
        sys.path.insert(0, _handler_path)

        # Clear stale app module cache
        if 'app' in sys.modules:
            del sys.modules['app']

        import app as handler_module
        yield table, handler_module


class TestScanProductNormalization:
    """Tests for response field normalization."""

    def test_returns_unified_fields(self, producten_table):
        """Returns all required unified fields for a product."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-001',
            'name': 'Club T-shirt',
            'price': 25,
            'variant_schema': {'Maat': ['S', 'M', 'L']},
            'is_parent': True,
            'event_id': None,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert product['product_id'] == 'uuid-001'
        assert product['name'] == 'Club T-shirt'
        assert product['price'] == 25
        assert product['variant_schema'] == {'Maat': ['S', 'M', 'L']}
        assert product['is_parent'] is True
        assert product['event_id'] is None
        assert product['active'] is True

    def test_naam_fallback_for_name(self, producten_table):
        """Uses naam as fallback when name is not present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-002',
            'naam': 'Pet H-DCN',
            'price': 15,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'Pet H-DCN'

    def test_prijs_fallback_for_price(self, producten_table):
        """Uses prijs as fallback when price is not present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-003',
            'name': 'Sticker',
            'prijs': 5,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['price'] == 5

    def test_name_preferred_over_naam(self, producten_table):
        """Uses name field when both name and naam are present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-004',
            'name': 'Correct Name',
            'naam': 'Legacy Name',
            'price': 10,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert body[0]['name'] == 'Correct Name'

    def test_price_preferred_over_prijs(self, producten_table):
        """Uses price field when both price and prijs are present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-005',
            'name': 'Test Product',
            'price': 30,
            'prijs': 25,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert body[0]['price'] == 30


class TestScanProductFiltering:
    """Tests for record exclusion filtering."""

    def test_excludes_variant_records(self, producten_table):
        """Excludes records where is_parent is explicitly false."""
        table, handler = producten_table

        # Parent product (should be included)
        table.put_item(Item={
            'product_id': 'parent-001',
            'name': 'T-shirt',
            'price': 25,
            'is_parent': True,
            'active': True,
        })

        # Variant record (should be excluded)
        table.put_item(Item={
            'product_id': 'variant-001',
            'name': 'T-shirt - L',
            'price': 25,
            'is_parent': False,
            'parent_id': 'parent-001',
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['product_id'] == 'parent-001'

    def test_excludes_migration_source_records(self, producten_table):
        """Excludes records where source equals migration."""
        table, handler = producten_table

        # Normal product (should be included)
        table.put_item(Item={
            'product_id': 'normal-001',
            'name': 'Normal Product',
            'price': 10,
            'is_parent': True,
            'active': True,
        })

        # Migration source record (should be excluded)
        table.put_item(Item={
            'product_id': 'migration-001',
            'name': 'Migrated Record',
            'price': 15,
            'is_parent': True,
            'source': 'migration',
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['product_id'] == 'normal-001'

    def test_includes_records_without_is_parent(self, producten_table):
        """Includes records where is_parent attribute does not exist."""
        table, handler = producten_table

        # Legacy record without is_parent field (should be included)
        table.put_item(Item={
            'product_id': 'legacy-001',
            'naam': 'Legacy Product',
            'prijs': 20,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['product_id'] == 'legacy-001'
        assert body[0]['name'] == 'Legacy Product'
        assert body[0]['price'] == 20
