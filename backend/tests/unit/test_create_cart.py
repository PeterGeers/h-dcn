"""
Unit tests for the create_cart handler.

Tests the unified cart creation logic: tenant derivation, club_id support,
variant_id references (not selectedOption), and item validation.
(Requirements 6.1, 6.3, 6.5, 12.5)
"""

import json
import os
import sys
import pytest
import boto3
from decimal import Decimal
from moto import mock_aws
from unittest.mock import patch, MagicMock

# Add auth layer to path
_layers_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Add handler root to path
_handler_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
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
    os.environ['MEMBERS_TABLE_NAME'] = 'Members'


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mocked DynamoDB Carts and Members tables."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Carts table
        carts = dynamodb.create_table(
            TableName='Carts',
            KeySchema=[{'AttributeName': 'cart_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'cart_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create Members table
        members = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Add a PresMeet member with club_id
        members.put_item(Item={
            'member_id': 'mem_001',
            'email': 'presmeet@example.com',
            'club_id': 'NL001',
            'status': 'active',
        })

        yield {'carts': carts, 'members': members, 'dynamodb': dynamodb}


def _make_event(body, user_email='user@h-dcn.nl', user_roles=None):
    """Helper to create a Lambda event with auth mocked."""
    if user_roles is None:
        user_roles = ['hdcnLeden']
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer mock-token'},
        'body': json.dumps(body),
        '_test_user_email': user_email,
        '_test_user_roles': user_roles,
    }


@pytest.fixture
def mock_auth():
    """Mock auth utilities for testing."""
    with patch('shared.auth_utils.extract_user_credentials') as mock_extract, \
         patch('shared.auth_utils.validate_permissions_with_regions') as mock_validate, \
         patch('shared.auth_utils.log_successful_access'):
        
        def extract_side_effect(event):
            return (
                event.get('_test_user_email', 'user@h-dcn.nl'),
                event.get('_test_user_roles', ['hdcnLeden']),
                None
            )
        
        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = (True, None, {'has_full_access': False})
        
        yield mock_extract, mock_validate


class TestCreateCartTenant:
    """Tests for tenant field on cart record."""

    def test_cart_created_with_tenant_hdcn(self, dynamodb_tables, mock_auth):
        """Cart for hdcnLeden user gets tenant 'h-dcn'."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={'customer_id': 'cust_123'},
            user_roles=['hdcnLeden']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        cart_id = body['cart_id']

        # Verify the record in DynamoDB
        carts_table = dynamodb_tables['carts']
        item = carts_table.get_item(Key={'cart_id': cart_id})['Item']
        assert item['tenant'] == 'h-dcn'

    def test_cart_created_with_tenant_presmeet(self, dynamodb_tables, mock_auth):
        """Cart for PresMeet user gets tenant 'presmeet' and club_id."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={'customer_id': 'cust_456', 'tenant': 'presmeet'},
            user_email='presmeet@example.com',
            user_roles=['Regio_Pressmeet']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        cart_id = body['cart_id']

        # Verify the record in DynamoDB
        carts_table = dynamodb_tables['carts']
        item = carts_table.get_item(Key={'cart_id': cart_id})['Item']
        assert item['tenant'] == 'presmeet'
        assert item['club_id'] == 'NL001'

    def test_tenant_access_denied_for_wrong_tenant(self, dynamodb_tables, mock_auth):
        """User requesting a tenant they don't have access to gets 403."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={'customer_id': 'cust_789', 'tenant': 'presmeet'},
            user_roles=['hdcnLeden']  # Only has h-dcn access
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 403


class TestCreateCartVariantId:
    """Tests for variant_id reference enforcement."""

    def test_cart_items_with_variant_id_accepted(self, dynamodb_tables, mock_auth):
        """Items with variant_id are accepted."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={
                'customer_id': 'cust_001',
                'items': [
                    {
                        'product_id': 'prod_abc',
                        'variant_id': 'var_prod_abc_m',
                        'quantity': 2,
                        'unit_price': '25.00',
                        'variant_attributes': {'Maat': 'M'},
                    }
                ]
            },
            user_roles=['hdcnLeden']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        cart_id = body['cart_id']

        # Verify stored items
        carts_table = dynamodb_tables['carts']
        item = carts_table.get_item(Key={'cart_id': cart_id})['Item']
        assert len(item['items']) == 1
        assert item['items'][0]['variant_id'] == 'var_prod_abc_m'
        assert item['items'][0]['product_id'] == 'prod_abc'
        assert 'selectedOption' not in item['items'][0]

    def test_cart_items_with_selectedOption_rejected(self, dynamodb_tables, mock_auth):
        """Items with legacy selectedOption field are rejected."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={
                'customer_id': 'cust_001',
                'items': [
                    {
                        'product_id': 'prod_abc',
                        'variant_id': 'var_prod_abc_m',
                        'selectedOption': 'M',  # Legacy field - should be rejected
                        'quantity': 1,
                    }
                ]
            },
            user_roles=['hdcnLeden']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'selectedOption' in body['error']

    def test_cart_items_missing_variant_id_rejected(self, dynamodb_tables, mock_auth):
        """Items missing variant_id are rejected."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={
                'customer_id': 'cust_001',
                'items': [
                    {
                        'product_id': 'prod_abc',
                        'quantity': 1,
                        # Missing variant_id
                    }
                ]
            },
            user_roles=['hdcnLeden']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'variant_id' in body['error']


class TestCreateCartEmptyItems:
    """Tests for creating cart with no items (empty cart)."""

    def test_empty_cart_created_successfully(self, dynamodb_tables, mock_auth):
        """Cart with no items is created successfully."""
        import importlib
        import handler.create_cart.app as handler_module
        importlib.reload(handler_module)

        event = _make_event(
            body={'customer_id': 'cust_empty'},
            user_roles=['hdcnLeden']
        )
        
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        cart_id = body['cart_id']

        carts_table = dynamodb_tables['carts']
        item = carts_table.get_item(Key={'cart_id': cart_id})['Item']
        assert item['items'] == []
        assert item['total_amount'] == Decimal('0')
        assert item['tenant'] == 'h-dcn'


class TestValidateCartItems:
    """Unit tests for the validate_cart_items function."""

    def test_valid_items(self):
        """Valid items pass validation."""
        from handler.create_cart.app import validate_cart_items
        is_valid, error = validate_cart_items([
            {'product_id': 'p1', 'variant_id': 'v1', 'quantity': 1},
            {'product_id': 'p2', 'variant_id': 'v2', 'quantity': 5},
        ])
        assert is_valid is True
        assert error is None

    def test_empty_list_valid(self):
        """Empty items list is valid."""
        from handler.create_cart.app import validate_cart_items
        is_valid, error = validate_cart_items([])
        assert is_valid is True

    def test_non_list_invalid(self):
        """Non-list input is rejected."""
        from handler.create_cart.app import validate_cart_items
        is_valid, error = validate_cart_items("not a list")
        assert is_valid is False
        assert "array" in error

    def test_zero_quantity_invalid(self):
        """Zero quantity is rejected."""
        from handler.create_cart.app import validate_cart_items
        is_valid, error = validate_cart_items([
            {'product_id': 'p1', 'variant_id': 'v1', 'quantity': 0},
        ])
        assert is_valid is False
        assert "positive integer" in error

    def test_selectedOption_rejected(self):
        """Item with selectedOption is rejected."""
        from handler.create_cart.app import validate_cart_items
        is_valid, error = validate_cart_items([
            {'product_id': 'p1', 'variant_id': 'v1', 'quantity': 1, 'selectedOption': 'M'},
        ])
        assert is_valid is False
        assert "selectedOption" in error
