"""
Unit tests for the get_variants handler.

Tests fetching variant records for a parent product via the
parent_id-index GSI, tenant access validation, and error cases.
(Requirements 6.2, 15.3)
"""

import json
import os
import sys
import pytest
import boto3
from decimal import Decimal
from moto import mock_aws
from unittest.mock import patch

# Add auth layer to path
_layers_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Add handler to path
_handler_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'handler'))
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)


@pytest.fixture
def aws_env():
    """Set up AWS mocked environment."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'


@pytest.fixture
def dynamodb_table(aws_env):
    """Create mocked DynamoDB Producten table with parent_id-index GSI."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

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
                    'KeySchema': [
                        {'AttributeName': 'parent_id', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table


@pytest.fixture
def setup_data(dynamodb_table):
    """Seed test data: parent product and variants."""
    # Create parent product
    dynamodb_table.put_item(Item={
        'product_id': 'prod_shirt01',
        'is_parent': True,
        'parent_id': 'NONE',
        'tenant': 'h-dcn',
        'name': 'Club T-shirt',
        'price': Decimal('25.00'),
        'active': True,
        'variant_schema': {'Maat': ['S', 'M', 'L']},
    })

    # Create variants
    dynamodb_table.put_item(Item={
        'product_id': 'var_prod_shirt01_s',
        'is_parent': False,
        'parent_id': 'prod_shirt01',
        'tenant': 'h-dcn',
        'name': 'Club T-shirt - S',
        'variant_attributes': {'Maat': 'S'},
        'price': Decimal('25.00'),
        'stock': 10,
        'sold_count': 2,
        'allow_oversell': False,
        'active': True,
    })

    dynamodb_table.put_item(Item={
        'product_id': 'var_prod_shirt01_m',
        'is_parent': False,
        'parent_id': 'prod_shirt01',
        'tenant': 'h-dcn',
        'name': 'Club T-shirt - M',
        'variant_attributes': {'Maat': 'M'},
        'price': Decimal('25.00'),
        'stock': 5,
        'sold_count': 0,
        'allow_oversell': False,
        'active': True,
    })

    dynamodb_table.put_item(Item={
        'product_id': 'var_prod_shirt01_l',
        'is_parent': False,
        'parent_id': 'prod_shirt01',
        'tenant': 'h-dcn',
        'name': 'Club T-shirt - L',
        'variant_attributes': {'Maat': 'L'},
        'price': Decimal('30.00'),
        'stock': 0,
        'sold_count': 0,
        'allow_oversell': True,
        'active': False,
    })

    # Create a presmeet product (should not be accessible to h-dcn only users)
    dynamodb_table.put_item(Item={
        'product_id': 'prod_presmeet01',
        'is_parent': True,
        'parent_id': 'NONE',
        'tenant': 'presmeet',
        'name': 'PresMeet Ticket',
        'price': Decimal('100.00'),
        'active': True,
    })

    return dynamodb_table


def _make_event(product_id, user_roles=None):
    """Build a mock API Gateway event."""
    return {
        'httpMethod': 'GET',
        'pathParameters': {'id': product_id},
        'headers': {'Authorization': 'Bearer mock_token'},
    }


class TestGetVariantsSuccess:
    """Tests for successful variant retrieval."""

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_returns_all_variants_for_parent(self, mock_auth, mock_log, setup_data):
        """Should return all variant records for a parent product."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('prod_shirt01')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['product_id'] == 'prod_shirt01'
        assert body['total_count'] == 3

        # Check that all variants are returned
        variant_ids = {v['product_id'] for v in body['variants']}
        assert 'var_prod_shirt01_s' in variant_ids
        assert 'var_prod_shirt01_m' in variant_ids
        assert 'var_prod_shirt01_l' in variant_ids

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_variant_fields_returned(self, mock_auth, mock_log, setup_data):
        """Should return correct fields on each variant record."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('prod_shirt01')
        response = lambda_handler(event, {})

        body = json.loads(response['body'])
        # Find the S variant
        s_variant = next(v for v in body['variants']
                         if v['product_id'] == 'var_prod_shirt01_s')

        assert s_variant['variant_attributes'] == {'Maat': 'S'}
        assert s_variant['stock'] == 10
        assert s_variant['sold_count'] == 2
        assert s_variant['allow_oversell'] is False
        assert s_variant['price'] == 25.0
        assert s_variant['active'] is True

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_product_with_no_variants(self, mock_auth, mock_log, setup_data):
        """Should return empty list when no variants exist for parent."""
        # Create a parent product without variants
        setup_data.put_item(Item={
            'product_id': 'prod_empty',
            'is_parent': True,
            'parent_id': 'NONE',
            'tenant': 'h-dcn',
            'name': 'Empty Product',
            'price': Decimal('10.00'),
            'active': True,
        })

        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('prod_empty')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['variants'] == []
        assert body['total_count'] == 0


class TestGetVariantsTenantAccess:
    """Tests for tenant access validation."""

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_tenant_access_denied(self, mock_auth, mock_log, setup_data):
        """Should return 403 when user lacks access to product's tenant."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        # hdcnLeden user trying to access presmeet product
        event = _make_event('prod_presmeet01')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['error'] == 'tenant_access_denied'

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('admin@h-dcn.nl', ['hdcnLeden', 'Regio_Pressmeet'], None))
    def test_dual_tenant_access_allowed(self, mock_auth, mock_log, setup_data):
        """User with both tenant roles can access presmeet products."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('prod_presmeet01')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 200


class TestGetVariantsErrors:
    """Tests for error cases."""

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_product_not_found(self, mock_auth, mock_log, setup_data):
        """Should return 404 when parent product doesn't exist."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('prod_nonexistent')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 404

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_missing_product_id(self, mock_auth, mock_log, setup_data):
        """Should return 400 when product ID is missing from path."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = {
            'httpMethod': 'GET',
            'pathParameters': {},
            'headers': {'Authorization': 'Bearer mock_token'},
        }
        response = lambda_handler(event, {})

        assert response['statusCode'] == 400

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_variant_id_rejected_as_parent(self, mock_auth, mock_log, setup_data):
        """Should return 400 when the ID points to a variant, not a parent."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = _make_event('var_prod_shirt01_s')
        response = lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_auth_error_propagated(self, setup_data):
        """Should return auth error when credentials are invalid."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        with patch('get_variants.app.extract_user_credentials',
                   return_value=(None, None, {'statusCode': 401, 'body': '{"error": "Unauthorized"}'})):
            from get_variants.app import lambda_handler

            event = _make_event('prod_shirt01')
            response = lambda_handler(event, {})

            assert response['statusCode'] == 401

    @patch('get_variants.app.log_successful_access')
    @patch('get_variants.app.extract_user_credentials',
           return_value=('buyer@h-dcn.nl', ['hdcnLeden'], None))
    def test_options_request(self, mock_auth, mock_log, setup_data):
        """Should handle OPTIONS preflight request."""
        import get_variants.app as handler_module
        handler_module.table = setup_data

        from get_variants.app import lambda_handler

        event = {'httpMethod': 'OPTIONS'}
        response = lambda_handler(event, {})

        assert response['statusCode'] == 200
