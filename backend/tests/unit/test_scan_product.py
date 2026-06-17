"""
Unit tests for the scan_product handler.

Tests:
- Canonical Dutch response fields (product_id, naam, artikelcode, prijs, is_parent, event_ids, active)
- Fallback: name → naam, price → prijs (for unmigrated records)
- Exclusion of variant records (is_parent: false)
- Exclusion of migration source records (source: "migration")
- Retention of records where is_parent is true or not set
- variant_schema is NOT included in response (removed)
"""

import json
import os
import sys
import importlib.util
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

# Path to the handler module (used for explicit import)
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')
)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _load_handler():
    """Load the scan_product handler module by file path, bypassing sys.path."""
    # Remove any cached 'app' module
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


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


class TestScanProductNormalization:
    """Tests for response field normalization — canonical Dutch fields."""

    def test_returns_canonical_dutch_fields(self, producten_table):
        """Returns all canonical Dutch fields for a product (without variant_schema)."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-001',
            'naam': 'Club T-shirt',
            'prijs': 25,
            'artikelcode': 'CT-01',
            'is_parent': True,
            'event_ids': ['evt-webshop'],
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert product['product_id'] == 'uuid-001'
        assert product['naam'] == 'Club T-shirt'
        assert product['artikelcode'] == 'CT-01'
        assert product['prijs'] == 25
        assert 'variant_schema' not in product
        assert product['is_parent'] is True
        assert product['event_ids'] == ['evt-webshop']
        assert product['active'] is True

    def test_naam_fallback_from_legacy_name(self, producten_table):
        """Uses legacy 'name' field as fallback for 'naam' when not present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-002',
            'name': 'Pet H-DCN',
            'prijs': 15,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        # Response uses canonical 'naam' field, falling back from 'name'
        assert body[0]['naam'] == 'Pet H-DCN'

    def test_prijs_fallback_from_legacy_price(self, producten_table):
        """Uses legacy 'price' field as fallback for 'prijs' when not present."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-003',
            'naam': 'Sticker',
            'price': 5,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert len(body) == 1
        # Response uses canonical 'prijs' field, falling back from 'price'
        assert body[0]['prijs'] == 5

    def test_naam_preferred_over_legacy_name(self, producten_table):
        """Canonical 'naam' is preferred over legacy 'name' when both exist."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-004',
            'naam': 'Canonical Naam',
            'name': 'Legacy Name',
            'prijs': 10,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert body[0]['naam'] == 'Canonical Naam'

    def test_prijs_preferred_over_legacy_price(self, producten_table):
        """Canonical 'prijs' is preferred over legacy 'price' when both exist."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-005',
            'naam': 'Test Product',
            'prijs': 25,
            'price': 30,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        # Canonical 'prijs' is the preferred source
        assert body[0]['prijs'] == 25

    def test_event_ids_returned_as_list(self, producten_table):
        """event_ids is returned as a list (not the old event_id string)."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'uuid-006',
            'naam': 'Event Product',
            'prijs': 50,
            'is_parent': True,
            'event_ids': ['evt-pm2027', 'evt-webshop'],
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        body = json.loads(response['body'])
        assert body[0]['event_ids'] == ['evt-pm2027', 'evt-webshop']


class TestScanProductVariantSchemaRemoval:
    """Tests verifying variant_schema is excluded from scan_product responses."""

    def test_variant_schema_excluded_when_stored_on_item(self, producten_table):
        """Even when a DynamoDB item has variant_schema stored, it is NOT in the response."""
        table, handler = producten_table

        # Store a product WITH variant_schema in DynamoDB (legacy data)
        table.put_item(Item={
            'product_id': 'uuid-schema-001',
            'naam': 'Product met Schema',
            'prijs': 30,
            'artikelcode': 'PS-01',
            'is_parent': True,
            'active': True,
            'variant_schema': {'Maat': ['S', 'M', 'L'], 'Kleur': ['Rood', 'Blauw']},
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert product['product_id'] == 'uuid-schema-001'
        assert product['naam'] == 'Product met Schema'
        # variant_schema must NOT appear in the response
        assert 'variant_schema' not in product

    def test_variant_schema_excluded_for_multiple_products(self, producten_table):
        """variant_schema is excluded from ALL products in a multi-product response."""
        table, handler = producten_table

        # Product with variant_schema
        table.put_item(Item={
            'product_id': 'uuid-multi-001',
            'naam': 'Product A',
            'prijs': 10,
            'is_parent': True,
            'active': True,
            'variant_schema': {'Maat': ['S', 'M']},
        })

        # Product without variant_schema
        table.put_item(Item={
            'product_id': 'uuid-multi-002',
            'naam': 'Product B',
            'prijs': 20,
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 2

        for product in body:
            assert 'variant_schema' not in product


class TestScanProductFiltering:
    """Tests for record exclusion filtering."""

    def test_excludes_variant_records(self, producten_table):
        """Excludes records where is_parent is explicitly false."""
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'parent-001',
            'naam': 'T-shirt',
            'prijs': 25,
            'is_parent': True,
            'active': True,
        })

        table.put_item(Item={
            'product_id': 'variant-001',
            'naam': 'T-shirt - L',
            'prijs': 25,
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

        table.put_item(Item={
            'product_id': 'normal-001',
            'naam': 'Normal Product',
            'prijs': 10,
            'is_parent': True,
            'active': True,
        })

        table.put_item(Item={
            'product_id': 'migration-001',
            'naam': 'Migrated Record',
            'prijs': 15,
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
        assert body[0]['naam'] == 'Legacy Product'
        assert body[0]['prijs'] == 20
