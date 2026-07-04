"""
Unit tests for price validation integration in all 4 handlers.

Tests that each handler returns 400 for non-numeric price values
and stores valid prices as Decimal.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
import boto3
from moto import mock_aws

# Environment setup
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'

# Handler file paths
_admin_update_product_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_update_product', 'app.py')
)
_admin_create_variant_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_variant', 'app.py')
)
_admin_create_product_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_product', 'app.py')
)
_create_order_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'create_order', 'app.py')
)


def _load_handler(handler_file):
    """Load a handler module by file path using importlib."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _auth_patches():
    """Patch auth functions for all handlers."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _create_producten_table(dynamodb):
    """Create Producten table for tests."""
    table = dynamodb.create_table(
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
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Producten')
    return table


def _create_orders_table(dynamodb):
    """Create Orders table for tests."""
    table = dynamodb.create_table(
        TableName='Orders',
        KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'order_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Orders')
    return table


def _create_members_table(dynamodb):
    """Create Members table for tests."""
    table = dynamodb.create_table(
        TableName='Members',
        KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'member_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='Members')
    return table


# ---------------------------------------------------------------------------
# admin_update_product tests
# ---------------------------------------------------------------------------

class TestAdminUpdateProductPriceValidation:
    """Test price validation in admin_update_product handler."""

    @pytest.mark.parametrize('invalid_price', ['abc', '', True])
    @mock_aws
    def test_rejects_non_numeric_prijs(self, invalid_price):
        """Handler returns 400 for non-numeric prijs values."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)
        table.put_item(Item={
            'product_id': 'prod_001',
            'is_parent': True,
            'naam': 'Test Product',
        })

        app = _load_handler(_admin_update_product_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'PUT',
                'pathParameters': {'id': 'prod_001'},
                'body': json.dumps({'prijs': invalid_price}),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'numeric' in body['error'].lower() or 'prijs' in body['error'].lower()

    @mock_aws
    def test_stores_valid_prijs_as_decimal(self):
        """Handler stores valid numeric prijs as Decimal (DynamoDB Number)."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)
        table.put_item(Item={
            'product_id': 'prod_001',
            'is_parent': True,
            'naam': 'Test Product',
        })

        app = _load_handler(_admin_update_product_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'PUT',
                'pathParameters': {'id': 'prod_001'},
                'body': json.dumps({'prijs': '25.50'}),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify stored value is Decimal in DynamoDB
        item = table.get_item(Key={'product_id': 'prod_001'})['Item']
        assert isinstance(item['prijs'], Decimal)
        assert item['prijs'] == Decimal('25.50')


# ---------------------------------------------------------------------------
# admin_create_variant tests
# ---------------------------------------------------------------------------

class TestAdminCreateVariantPriceValidation:
    """Test price validation in admin_create_variant handler."""

    @pytest.mark.parametrize('invalid_price', ['abc', '', True])
    @mock_aws
    def test_rejects_non_numeric_prijs(self, invalid_price):
        """Handler returns 400 for non-numeric prijs values."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)
        table.put_item(Item={
            'product_id': 'prod_parent',
            'is_parent': True,
            'naam': 'Parent Product',
        })

        app = _load_handler(_admin_create_variant_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'POST',
                'pathParameters': {'id': 'prod_parent'},
                'body': json.dumps({
                    'naam': 'Variant A',
                    'prijs': invalid_price,
                    'variant_attributes': {'size': 'M'},
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'numeric' in body['error'].lower() or 'prijs' in body['error'].lower()

    @mock_aws
    def test_stores_valid_prijs_as_decimal(self):
        """Handler stores valid numeric prijs as Decimal."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)
        table.put_item(Item={
            'product_id': 'prod_parent',
            'is_parent': True,
            'naam': 'Parent Product',
        })

        app = _load_handler(_admin_create_variant_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'POST',
                'pathParameters': {'id': 'prod_parent'},
                'body': json.dumps({
                    'naam': 'Variant A',
                    'prijs': '19.99',
                    'variant_attributes': {'size': 'L'},
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        variant_id = body['variant']['product_id']

        # Verify stored value in DynamoDB
        item = table.get_item(Key={'product_id': variant_id})['Item']
        assert isinstance(item['prijs'], Decimal)
        assert item['prijs'] == Decimal('19.99')


# ---------------------------------------------------------------------------
# admin_create_product tests
# ---------------------------------------------------------------------------

class TestAdminCreateProductPriceValidation:
    """Test price validation in admin_create_product handler."""

    @pytest.mark.parametrize('invalid_price', ['abc', '', True])
    @mock_aws
    def test_rejects_non_numeric_price(self, invalid_price):
        """Handler returns 400 for non-numeric price values."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)

        app = _load_handler(_admin_create_product_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'POST',
                'pathParameters': {},
                'body': json.dumps({
                    'name': 'Test Product',
                    'price': invalid_price,
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'numeric' in body['error'].lower() or 'price' in body['error'].lower()

    @mock_aws
    def test_stores_valid_price_as_decimal(self):
        """Handler stores valid price as Decimal."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_producten_table(dynamodb)

        app = _load_handler(_admin_create_product_file)
        app.table = table

        with _auth_patches():
            event = {
                'httpMethod': 'POST',
                'pathParameters': {},
                'body': json.dumps({
                    'name': 'Test Product',
                    'price': '42.00',
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        product_id = body['product']['product_id']

        # Verify stored value in DynamoDB
        item = table.get_item(Key={'product_id': product_id})['Item']
        assert isinstance(item['price'], Decimal)
        assert item['price'] == Decimal('42.00')


# ---------------------------------------------------------------------------
# create_order tests
# ---------------------------------------------------------------------------

class TestCreateOrderPriceValidation:
    """Test price validation in create_order handler."""

    def _order_auth_patches(self):
        """Auth patches for create_order (includes get_registry_row_id)."""
        return patch.multiple(
            'app',
            extract_user_credentials=lambda event: ('user@h-dcn.nl', ['hdcnLeden'], None),
            validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
            log_successful_access=lambda *a, **kw: None,
            get_registry_row_id=lambda email: 'club_001',
        )

    @mock_aws
    def test_rejects_non_numeric_product_price(self):
        """Handler returns 400 when product has non-numeric price in DB."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        producten_table = _create_producten_table(dynamodb)
        orders_table = _create_orders_table(dynamodb)
        members_table = _create_members_table(dynamodb)

        # Product with non-numeric price string
        producten_table.put_item(Item={
            'product_id': 'prod_bad',
            'name': 'Bad Price Product',
            'price': 'abc',
        })

        # Member record
        members_table.put_item(Item={
            'member_id': 'mem_001',
            'email': 'user@h-dcn.nl',
        })

        app = _load_handler(_create_order_file)
        app.producten_table = producten_table
        app.orders_table = orders_table
        app.members_table = members_table

        with self._order_auth_patches():
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'items': [{'product_id': 'prod_bad', 'quantity': 1}],
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400

    @mock_aws
    def test_accepts_valid_numeric_price(self):
        """Handler accepts product with valid numeric price and creates order."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        producten_table = _create_producten_table(dynamodb)
        orders_table = _create_orders_table(dynamodb)
        members_table = _create_members_table(dynamodb)

        # Product with valid price
        producten_table.put_item(Item={
            'product_id': 'prod_good',
            'name': 'Good Product',
            'price': Decimal('15.00'),
        })

        # Member record
        members_table.put_item(Item={
            'member_id': 'mem_001',
            'email': 'user@h-dcn.nl',
        })

        app = _load_handler(_create_order_file)
        app.producten_table = producten_table
        app.orders_table = orders_table
        app.members_table = members_table

        with self._order_auth_patches():
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'items': [{'product_id': 'prod_good', 'quantity': 2}],
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['total_amount'] == 30  # 15.00 * 2

    @mock_aws
    def test_rejects_string_price_in_db(self):
        """Handler returns 400 when price stored as non-numeric string."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        producten_table = _create_producten_table(dynamodb)
        orders_table = _create_orders_table(dynamodb)
        members_table = _create_members_table(dynamodb)

        # Product with empty string price
        producten_table.put_item(Item={
            'product_id': 'prod_empty',
            'name': 'Empty Price',
            'price': 'not_a_number',
        })

        members_table.put_item(Item={
            'member_id': 'mem_001',
            'email': 'user@h-dcn.nl',
        })

        app = _load_handler(_create_order_file)
        app.producten_table = producten_table
        app.orders_table = orders_table
        app.members_table = members_table

        with self._order_auth_patches():
            event = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'items': [{'product_id': 'prod_empty', 'quantity': 1}],
                }),
                'headers': {'Authorization': 'Bearer test'},
            }
            response = app.lambda_handler(event, None)

        assert response['statusCode'] == 400
