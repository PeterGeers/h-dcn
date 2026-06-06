"""
Unit tests for the create_order handler.

Tests the unified order creation pipeline: purchase rules enforcement,
item fields validation, stock availability checks, payment method handling
(Mollie and bank transfer), persistent order mode with optimistic locking,
and Item_Fields_Data storage.

(Requirements: 5.7–5.12, 6.6–6.8, 8.4–8.6, 9.1–9.5, 10.1, 10.5–10.7,
 12.5–12.13, 16.1–16.7, 17.1–17.5)
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
    os.environ['ORDERS_TABLE_NAME'] = 'Orders'
    os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
    os.environ['MEMBERSHIPS_TABLE_NAME'] = 'Memberships'
    os.environ['CARTS_TABLE_NAME'] = 'Carts'
    os.environ['MEMBERS_TABLE_NAME'] = 'Members'
    os.environ['BANK_TRANSFER_IBAN'] = 'NL00TEST0123456789'
    os.environ['MOLLIE_WEBHOOK_URL'] = 'https://api.example.com/mollie-webhook'
    os.environ['MOLLIE_REDIRECT_URL'] = 'https://portal.h-dcn.nl/orders/{id}/confirmation'


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mocked DynamoDB tables for the create_order handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        memberships = dynamodb.create_table(
            TableName='Memberships',
            KeySchema=[{'AttributeName': 'membership_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'membership_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        carts = dynamodb.create_table(
            TableName='Carts',
            KeySchema=[{'AttributeName': 'cart_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'cart_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        members = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Add test data
        members.put_item(Item={
            'member_id': 'mem_001',
            'email': 'buyer@h-dcn.nl',
            'club_id': 'NL001',
            'status': 'active',
        })

        memberships.put_item(Item={
            'membership_id': 'ms_001',
            'member_id': 'mem_001',
            'status': 'active',
        })

        carts.put_item(Item={
            'cart_id': 'cart_001',
            'user_email': 'buyer@h-dcn.nl',
            'tenant': 'h-dcn',
            'items': [],
        })

        # Parent product with full config
        producten.put_item(Item={
            'product_id': 'prod_shirt',
            'is_parent': True,
            'name': 'Club T-shirt',
            'price': Decimal('25.00'),
            'active': True,
            'tenant': 'h-dcn',
            'variant_schema': {'Maat': ['S', 'M', 'L']},
            'order_item_fields': [
                {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True,
                 'validation': {'min_length': 2, 'max_length': 100}},
            ],
            'purchase_rules': {
                'max_per_order': 5,
                'max_per_member': 10,
            },
        })

        # Simple product without rules
        producten.put_item(Item={
            'product_id': 'prod_simple',
            'is_parent': True,
            'name': 'Simple Product',
            'price': Decimal('10.00'),
            'active': True,
            'tenant': 'h-dcn',
        })

        # Variant with stock
        producten.put_item(Item={
            'product_id': 'var_shirt_m',
            'is_parent': False,
            'parent_id': 'prod_shirt',
            'name': 'Club T-shirt - M',
            'variant_attributes': {'Maat': 'M'},
            'price': Decimal('25.00'),
            'stock': 10,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Variant with no stock
        producten.put_item(Item={
            'product_id': 'var_shirt_s',
            'is_parent': False,
            'parent_id': 'prod_shirt',
            'name': 'Club T-shirt - S',
            'variant_attributes': {'Maat': 'S'},
            'price': Decimal('25.00'),
            'stock': 0,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Variant with allow_oversell
        producten.put_item(Item={
            'product_id': 'var_simple_default',
            'is_parent': False,
            'parent_id': 'prod_simple',
            'name': 'Default Variant',
            'variant_attributes': {},
            'price': Decimal('10.00'),
            'stock': 0,
            'sold_count': 0,
            'allow_oversell': True,
            'active': True,
        })

        # PresMeet product with persistent order mode
        producten.put_item(Item={
            'product_id': 'prod_presmeet',
            'is_parent': True,
            'name': 'PresMeet Conference',
            'price': Decimal('100.00'),
            'active': True,
            'tenant': 'presmeet',
            'purchase_rules': {
                'max_per_club': 20,
                'order_mode': 'persistent',
            },
        })

        producten.put_item(Item={
            'product_id': 'var_presmeet_default',
            'is_parent': False,
            'parent_id': 'prod_presmeet',
            'variant_attributes': {},
            'price': Decimal('100.00'),
            'stock': 50,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # PresMeet cart
        carts.put_item(Item={
            'cart_id': 'cart_presmeet',
            'user_email': 'buyer@h-dcn.nl',
            'tenant': 'presmeet',
            'club_id': 'NL001',
            'items': [],
        })

        yield {
            'orders': orders,
            'producten': producten,
            'memberships': memberships,
            'carts': carts,
            'members': members,
            'dynamodb': dynamodb,
        }


def _make_event(body, user_email='buyer@h-dcn.nl', user_roles=None):
    """Helper to create a Lambda event."""
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
                event.get('_test_user_email', 'buyer@h-dcn.nl'),
                event.get('_test_user_roles', ['hdcnLeden']),
                None
            )

        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = (False, None, None)

        yield mock_extract, mock_validate


@pytest.fixture
def mock_mollie():
    """Mock Mollie client for testing."""
    with patch('shared.mollie_client.create_payment') as mock_create:
        mock_create.return_value = {
            'mollie_payment_id': 'tr_test123',
            'checkout_url': 'https://www.mollie.com/checkout/test',
            'status': 'open',
        }
        yield mock_create


class TestCreateOrderValidation:
    """Tests for order creation input validation."""

    def test_missing_cart_id_rejected(self, dynamodb_tables, mock_auth):
        """Order without cart_id returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'payment_method': 'bank_transfer',
            'items': [{'product_id': 'prod_simple', 'variant_id': 'var_simple_default', 'quantity': 1}],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'cart_id' in body.get('error', '')

    def test_missing_payment_method_rejected(self, dynamodb_tables, mock_auth):
        """Order without payment_method returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'items': [{'product_id': 'prod_simple', 'variant_id': 'var_simple_default', 'quantity': 1}],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_invalid_payment_method_rejected(self, dynamodb_tables, mock_auth):
        """Order with invalid payment_method returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bitcoin',
            'items': [{'product_id': 'prod_simple', 'variant_id': 'var_simple_default', 'quantity': 1}],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'payment_method' in body.get('error', '')

    def test_empty_items_rejected(self, dynamodb_tables, mock_auth):
        """Order with empty items array returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestPurchaseRulesEnforcement:
    """Tests for purchase rules enforcement in create_order (Req 16.1-16.7)."""

    def test_max_per_order_exceeded_rejected(self, dynamodb_tables, mock_auth):
        """Quantity exceeding max_per_order returns 400 with rule violation."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 10,  # max_per_order is 5
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'purchase_rule_violation'
        assert body['details']['rule'] == 'max_per_order'
        assert body['details']['limit'] == 5

    def test_max_per_order_allowed(self, dynamodb_tables, mock_auth):
        """Quantity within max_per_order is accepted."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 3,  # max_per_order is 5 - OK
                'item_fields_data': [
                    {'field_values': {'name': 'Jan'}},
                    {'field_values': {'name': 'Piet'}},
                    {'field_values': {'name': 'Kees'}},
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_no_purchase_rules_skips_validation(self, dynamodb_tables, mock_auth):
        """Product without purchase_rules passes validation (Req 16.7)."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 99,  # No rules, any quantity allowed
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestItemFieldsValidation:
    """Tests for item fields validation (Req 17.1-17.5)."""

    def test_missing_item_fields_data_rejected(self, dynamodb_tables, mock_auth):
        """Product with order_item_fields but no item_fields_data returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                # Missing item_fields_data
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_count_mismatch'

    def test_item_fields_count_mismatch_rejected(self, dynamodb_tables, mock_auth):
        """Wrong count of item_fields_data entries returns 400 (Req 17.5)."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 3,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan'}},
                    {'field_values': {'name': 'Piet'}},
                    # Missing third entry
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_count_mismatch'
        assert body['details']['expected'] == 3
        assert body['details']['actual'] == 2

    def test_required_field_empty_rejected(self, dynamodb_tables, mock_auth):
        """Empty required field returns 400 (Req 17.1)."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 1,
                'item_fields_data': [
                    {'field_values': {'name': ''}},  # Required but empty
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_validation_error'
        assert body['details']['field_id'] == 'name'
        assert body['details']['constraint'] == 'required'

    def test_valid_item_fields_accepted(self, dynamodb_tables, mock_auth):
        """Valid item_fields_data passes validation."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan Jansen'}},
                    {'field_values': {'name': 'Piet de Vries'}},
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestStockValidation:
    """Tests for stock availability validation (Req 6.6-6.8)."""

    def test_insufficient_stock_rejected(self, dynamodb_tables, mock_auth):
        """Variant with insufficient stock and allow_oversell=false returns 400."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_s',  # stock=0, allow_oversell=false
                'quantity': 1,
                'item_fields_data': [{'field_values': {'name': 'Jan'}}],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'insufficient_stock'
        assert body['details']['variant_id'] == 'var_shirt_s'
        assert body['details']['available'] == 0
        assert body['details']['requested'] == 1

    def test_allow_oversell_allows_zero_stock(self, dynamodb_tables, mock_auth):
        """Variant with allow_oversell=true passes stock check even at 0 stock."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',  # stock=0 but allow_oversell=true
                'quantity': 5,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_sufficient_stock_accepted(self, dynamodb_tables, mock_auth):
        """Variant with sufficient stock passes validation."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',  # stock=10
                'quantity': 5,
                'item_fields_data': [
                    {'field_values': {'name': f'Person {i}'}}
                    for i in range(5)
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestBankTransferPayment:
    """Tests for bank transfer payment method (Req 9.3, 9.4)."""

    def test_bank_transfer_creates_unpaid_order(self, dynamodb_tables, mock_auth):
        """Bank transfer creates order with payment_status 'unpaid'."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        assert body['payment_status'] == 'unpaid'
        assert 'transfer_instructions' in body
        assert 'reference' in body['transfer_instructions']
        assert body['transfer_instructions']['iban'] == 'NL00TEST0123456789'
        assert body['transfer_instructions']['amount'] == 10.0

    def test_bank_transfer_order_stored(self, dynamodb_tables, mock_auth):
        """Bank transfer order is persisted in DynamoDB."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 2,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        body = json.loads(response['body'])
        order_id = body['order_id']

        # Verify stored order
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert order['payment_status'] == 'unpaid'
        assert order['payment_method'] == 'bank_transfer'
        assert order['member_id'] == 'mem_001'
        assert order['user_email'] == 'buyer@h-dcn.nl'
        assert order['tenant'] == 'h-dcn'
        assert order['status'] == 'submitted'
        assert len(order['items']) == 1
        assert order['items'][0]['variant_id'] == 'var_simple_default'
        assert order['total_amount'] == Decimal('20.00')


class TestMolliePayment:
    """Tests for Mollie payment method (Req 9.1, 9.2, 9.5)."""

    def test_ideal_creates_pending_order_with_checkout_url(self, dynamodb_tables, mock_auth, mock_mollie):
        """iDEAL payment creates order with pending status and returns checkout_url."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'ideal',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        assert body['payment_status'] == 'pending'
        assert body['checkout_url'] == 'https://www.mollie.com/checkout/test'
        assert 'order_id' in body

    def test_creditcard_creates_pending_order(self, dynamodb_tables, mock_auth, mock_mollie):
        """Credit card payment creates order with pending status."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'creditcard',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['payment_status'] == 'pending'

    def test_mollie_error_returns_502(self, dynamodb_tables, mock_auth):
        """Mollie API failure returns 502."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        from shared.mollie_client import MollieError
        with patch('handler.create_order.app.create_payment', side_effect=MollieError("API timeout")):
            event = _make_event({
                'cart_id': 'cart_001',
                'payment_method': 'ideal',
                'items': [{
                    'product_id': 'prod_simple',
                    'variant_id': 'var_simple_default',
                    'quantity': 1,
                }],
            })

            response = handler_module.lambda_handler(event, None)
            assert response['statusCode'] == 502
            body = json.loads(response['body'])
            assert body['error'] == 'payment_provider_error'


class TestPersistentOrders:
    """Tests for persistent order mode (Req 12.5-12.13)."""

    def test_persistent_order_creates_with_version(self, dynamodb_tables, mock_auth):
        """Persistent order is created with version=1."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_presmeet',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_presmeet',
                'variant_id': 'var_presmeet_default',
                'quantity': 5,
            }],
        }, user_roles=['Regio_Pressmeet'])

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        order_id = body['order_id']

        # Verify stored order has version
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert order['version'] == 1
        assert order['club_id'] == 'NL001'

    def test_persistent_order_updates_existing(self, dynamodb_tables, mock_auth):
        """Second order for same club updates existing persistent order."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        # Create first order
        orders_table = dynamodb_tables['orders']
        orders_table.put_item(Item={
            'order_id': 'existing_order',
            'club_id': 'NL001',
            'status': 'submitted',
            'version': 1,
            'total_paid': Decimal('0'),
            'items': [{
                'product_id': 'prod_presmeet',
                'variant_id': 'var_presmeet_default',
                'quantity': 3,
                'unit_price': Decimal('100.00'),
                'line_total': Decimal('300.00'),
            }],
        })

        event = _make_event({
            'cart_id': 'cart_presmeet',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_presmeet',
                'variant_id': 'var_presmeet_default',
                'quantity': 7,
            }],
        }, user_roles=['Regio_Pressmeet'])

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Should update existing order
        assert body['order_id'] == 'existing_order'
        assert body['version'] == 2

    def test_optimistic_locking_rejects_stale_version(self, dynamodb_tables, mock_auth):
        """Stale version in request returns 409 conflict."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        # Create existing persistent order at version 3
        orders_table = dynamodb_tables['orders']
        orders_table.put_item(Item={
            'order_id': 'locked_order',
            'club_id': 'NL001',
            'status': 'submitted',
            'version': 3,
            'total_paid': Decimal('0'),
            'items': [{
                'product_id': 'prod_presmeet',
                'variant_id': 'var_presmeet_default',
                'quantity': 2,
                'unit_price': Decimal('100.00'),
                'line_total': Decimal('200.00'),
            }],
        })

        event = _make_event({
            'cart_id': 'cart_presmeet',
            'payment_method': 'bank_transfer',
            'version': 2,  # Stale version
            'items': [{
                'product_id': 'prod_presmeet',
                'variant_id': 'var_presmeet_default',
                'quantity': 5,
            }],
        }, user_roles=['Regio_Pressmeet'])

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error'] == 'version_conflict'
        assert body['details']['current_version'] == 3


class TestItemFieldsDataStorage:
    """Tests for Item_Fields_Data persistence on order (Req 10.1, 10.5)."""

    def test_item_fields_data_flattened_on_order(self, dynamodb_tables, mock_auth):
        """Item fields data is stored flattened with field_id, field_label, value, item_index."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan Jansen'}},
                    {'field_values': {'name': 'Piet de Vries'}},
                ],
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        order_id = body['order_id']

        # Verify stored Item_Fields_Data
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        item_fields = order['items'][0]['item_fields_data']

        # Should have 2 entries (1 field x 2 items)
        assert len(item_fields) == 2

        # First item
        assert item_fields[0]['item_index'] == 1
        assert item_fields[0]['field_id'] == 'name'
        assert item_fields[0]['field_label'] == 'Naam'
        assert item_fields[0]['value'] == 'Jan Jansen'

        # Second item
        assert item_fields[1]['item_index'] == 2
        assert item_fields[1]['field_id'] == 'name'
        assert item_fields[1]['field_label'] == 'Naam'
        assert item_fields[1]['value'] == 'Piet de Vries'

    def test_no_item_fields_for_product_without_definition(self, dynamodb_tables, mock_auth):
        """Products without order_item_fields don't store item_fields_data."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_001',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        order_id = body['order_id']

        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert 'item_fields_data' not in order['items'][0]


class TestCartOwnershipValidation:
    """Tests for cart ownership validation."""

    def test_wrong_user_cart_rejected(self, dynamodb_tables, mock_auth):
        """Cart belonging to another user returns 403."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        # Add a cart belonging to a different user
        dynamodb_tables['carts'].put_item(Item={
            'cart_id': 'cart_other',
            'user_email': 'other@h-dcn.nl',
            'tenant': 'h-dcn',
            'items': [],
        })

        event = _make_event({
            'cart_id': 'cart_other',  # Belongs to other@h-dcn.nl
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 403

    def test_nonexistent_cart_returns_404(self, dynamodb_tables, mock_auth):
        """Non-existent cart returns 404."""
        import importlib
        import handler.create_order.app as handler_module
        importlib.reload(handler_module)

        event = _make_event({
            'cart_id': 'cart_nonexistent',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_simple',
                'variant_id': 'var_simple_default',
                'quantity': 1,
            }],
        })

        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 404
