"""
Unit tests for admin_update_product handler.

Tests the modified handler that supports:
- Updating variant_schema with variant regeneration
- Updating order_item_fields and purchase_rules
- Validating all three new fields on update
- Handling variant_schema change: delete old variants, regenerate, reset stock to 0
- Preserving groep, subgroep, images update capability
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest
import boto3
from moto import mock_aws

# Add the handler directory and shared layer to the path
_update_handler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../handler/admin_update_product'))
sys.path.insert(0, _update_handler_path)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))

# Set environment variable before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


@pytest.fixture(autouse=True)
def _ensure_correct_app_module():
    """Ensure sys.modules['app'] points to the admin_update_product handler."""
    # Put our handler path first
    if _update_handler_path in sys.path:
        sys.path.remove(_update_handler_path)
    sys.path.insert(0, _update_handler_path)
    # Clear cached app module so next import resolves to our handler
    if 'app' in sys.modules:
        del sys.modules['app']
    yield
    # Clean up after test
    if 'app' in sys.modules:
        del sys.modules['app']


def _make_event(product_id, body):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': 'PUT',
        'pathParameters': {'id': product_id},
        'body': json.dumps(body),
        'headers': {'Authorization': 'Bearer fake-token'},
        'requestContext': {}
    }


def _seed_parent_product(table, product_id='prod_test123', **overrides):
    """Insert a parent product into the table."""
    item = {
        'product_id': product_id,
        'is_parent': True,
        'parent_id': None,
        'tenant': 'h-dcn',
        'name': 'Test Product',
        'price': Decimal('25.00'),
        'active': True,
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
    }
    item.update(overrides)
    # Remove None values
    item = {k: v for k, v in item.items() if v is not None}
    table.put_item(Item=item)
    return item


def _seed_variant(table, variant_id, parent_id='prod_test123', **overrides):
    """Insert a variant record into the table."""
    item = {
        'product_id': variant_id,
        'is_parent': False,
        'parent_id': parent_id,
        'tenant': 'h-dcn',
        'variant_attributes': {},
        'stock': 10,
        'sold_count': 5,
        'allow_oversell': False,
        'active': True,
        'created_at': '2024-01-01T00:00:00+00:00',
        'updated_at': '2024-01-01T00:00:00+00:00',
    }
    item.update(overrides)
    table.put_item(Item=item)
    return item


def _create_table(dynamodb):
    """Create the Producten table."""
    table = dynamodb.create_table(
        TableName='Producten',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Producten')
    return table


class TestAdminUpdateProductBasicFields:
    """Test basic field updates (name, price, groep, subgroep, images)."""

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_update_groep_subgroep(self, mock_log, mock_validate, mock_extract):
        """groep and subgroep fields can be updated."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        event = _make_event('prod_test123', {
            'groep': 'Kleding',
            'subgroep': 'T-shirts'
        })
        response = app.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['product']['groep'] == 'Kleding'
        assert body['product']['subgroep'] == 'T-shirts'

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_update_images(self, mock_log, mock_validate, mock_extract):
        """images field can be updated."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        images = ['https://s3.amazonaws.com/img1.jpg', 'https://s3.amazonaws.com/img2.jpg']
        event = _make_event('prod_test123', {'images': images})
        response = app.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['product']['images'] == images

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_update_nonexistent_product_returns_404(self, mock_log, mock_validate, mock_extract):
        """Updating a non-existent product returns 404."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        import app
        app.table = table

        event = _make_event('prod_nonexistent', {'name': 'New Name'})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 404

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_cannot_update_variant_record(self, mock_log, mock_validate, mock_extract):
        """Attempting to update a variant record returns 400."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_variant(table, 'var_prod_test123_default')

        import app
        app.table = table

        event = _make_event('var_prod_test123_default', {'name': 'Bad Update'})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'variant' in body['error'].lower()


class TestAdminUpdateProductNewFieldsValidation:
    """Test validation of variant_schema, order_item_fields, purchase_rules."""

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_variant_schema_rejected(self, mock_log, mock_validate, mock_extract):
        """Invalid variant_schema is rejected with validation errors."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        # Schema with duplicate values in an axis
        invalid_schema = {'Maat': ['S', 'M', 'S']}  # Duplicate 'S'
        event = _make_event('prod_test123', {'variant_schema': invalid_schema})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'errors' in body

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_order_item_fields_rejected(self, mock_log, mock_validate, mock_extract):
        """Invalid order_item_fields is rejected."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        # Missing required 'type' field
        invalid_fields = [{'id': 'name', 'label': 'Name'}]
        event = _make_event('prod_test123', {'order_item_fields': invalid_fields})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_purchase_rules_rejected(self, mock_log, mock_validate, mock_extract):
        """Invalid purchase_rules is rejected."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        # min_per_club > max_per_club
        invalid_rules = {'min_per_club': 10, 'max_per_club': 5}
        event = _make_event('prod_test123', {'purchase_rules': invalid_rules})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_valid_order_item_fields_accepted(self, mock_log, mock_validate, mock_extract):
        """Valid order_item_fields is accepted and stored."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        valid_fields = [
            {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
            {'id': 'email', 'label': 'E-mail', 'type': 'email', 'required': True}
        ]
        event = _make_event('prod_test123', {'order_item_fields': valid_fields})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['product']['order_item_fields'] == valid_fields

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_valid_purchase_rules_accepted(self, mock_log, mock_validate, mock_extract):
        """Valid purchase_rules is accepted and stored."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)
        _seed_parent_product(table)

        import app
        app.table = table

        valid_rules = {
            'max_per_order': 5,
            'max_per_member': 2,
            'requires_membership': True,
            'order_mode': 'single'
        }
        event = _make_event('prod_test123', {'purchase_rules': valid_rules})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['product']['purchase_rules'] == valid_rules


class TestAdminUpdateProductVariantRegeneration:
    """Test variant_schema change triggers regeneration."""

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_variant_schema_change_regenerates_variants(self, mock_log, mock_validate, mock_extract):
        """Changing variant_schema deletes old variants and creates new ones."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        # Seed parent with existing schema
        _seed_parent_product(table, variant_schema={'Maat': ['S', 'M']})
        # Seed existing variants
        _seed_variant(table, 'var_prod_test123_s', variant_attributes={'Maat': 'S'}, stock=10)
        _seed_variant(table, 'var_prod_test123_m', variant_attributes={'Maat': 'M'}, stock=5)

        import app
        app.table = table

        # Update with new schema
        new_schema = {'Maat': ['S', 'M', 'L', 'XL']}
        event = _make_event('prod_test123', {'variant_schema': new_schema})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variants_regenerated'] is True
        assert body['variant_count'] == 4  # S, M, L, XL

        # Verify old variants were deleted and new ones created
        scan_result = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq('prod_test123')
        )
        variants = scan_result['Items']
        assert len(variants) == 4

        # All new variants should have stock = 0
        for v in variants:
            assert v['stock'] == 0

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_removing_variant_schema_creates_default_variant(self, mock_log, mock_validate, mock_extract):
        """Setting variant_schema to empty creates a Default_Variant."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        # Seed parent with existing schema and variants
        _seed_parent_product(table, variant_schema={'Maat': ['S', 'M']})
        _seed_variant(table, 'var_prod_test123_s', variant_attributes={'Maat': 'S'})
        _seed_variant(table, 'var_prod_test123_m', variant_attributes={'Maat': 'M'})

        import app
        app.table = table

        # Remove schema by setting to empty dict
        event = _make_event('prod_test123', {'variant_schema': {}})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variants_regenerated'] is True
        assert body['variant_count'] == 1  # Default variant

        # Verify default variant was created
        scan_result = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq('prod_test123')
        )
        variants = scan_result['Items']
        assert len(variants) == 1
        assert variants[0]['variant_attributes'] == {}

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_same_variant_schema_no_regeneration(self, mock_log, mock_validate, mock_extract):
        """Updating with the same variant_schema doesn't regenerate."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        schema = {'Maat': ['S', 'M']}
        _seed_parent_product(table, variant_schema=schema)
        _seed_variant(table, 'var_prod_test123_s', variant_attributes={'Maat': 'S'}, stock=10)
        _seed_variant(table, 'var_prod_test123_m', variant_attributes={'Maat': 'M'}, stock=5)

        import app
        app.table = table

        event = _make_event('prod_test123', {'variant_schema': schema})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Same schema = no regeneration
        assert 'variants_regenerated' not in body

        # Verify existing variants still have their original stock
        scan_result = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq('prod_test123')
        )
        variants = scan_result['Items']
        assert len(variants) == 2
        stock_values = sorted([int(v['stock']) for v in variants])
        assert stock_values == [5, 10]

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_update_without_variant_schema_no_regeneration(self, mock_log, mock_validate, mock_extract):
        """Updating other fields without variant_schema doesn't regenerate."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        _seed_parent_product(table, variant_schema={'Maat': ['S', 'M']})
        _seed_variant(table, 'var_prod_test123_s', variant_attributes={'Maat': 'S'}, stock=10)

        import app
        app.table = table

        event = _make_event('prod_test123', {'name': 'Updated Name'})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'variants_regenerated' not in body
        assert body['product']['name'] == 'Updated Name'

    @mock_aws
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_multi_axis_variant_schema_regeneration(self, mock_log, mock_validate, mock_extract):
        """Multi-axis schema generates correct number of combinations."""
        mock_extract.return_value = ('admin@h-dcn.nl', ['Products_CRUD'], None)
        mock_validate.return_value = (True, None, {})

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_table(dynamodb)

        _seed_parent_product(table)
        _seed_variant(table, 'var_prod_test123_default', variant_attributes={})

        import app
        app.table = table

        # Set multi-axis schema: 3 sizes × 2 genders = 6 variants
        new_schema = {'Maat': ['S', 'M', 'L'], 'Gender': ['Male', 'Female']}
        event = _make_event('prod_test123', {'variant_schema': new_schema})
        response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variants_regenerated'] is True
        assert body['variant_count'] == 6

        # Verify all 6 were created
        scan_result = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq('prod_test123')
        )
        variants = scan_result['Items']
        assert len(variants) == 6

        # Verify all have stock = 0
        for v in variants:
            assert v['stock'] == 0
            assert v['is_parent'] is False
