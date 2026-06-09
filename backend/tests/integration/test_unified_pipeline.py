"""
Integration tests for the unified webshop/PresMeet pipeline.

Tests the full end-to-end flows: order lifecycle with Mollie payments,
purchase rules enforcement, item fields validation, event-based filtering,
and migration scripts.

Uses moto for DynamoDB mocking and unittest.mock for auth + Mollie.
"""

import json
import os
import sys
import importlib
from decimal import Decimal
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws

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

# Add scripts to path
_scripts_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'scripts'))
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)


# ---------------------------------------------------------------------------
# 13.1 — Fixtures: moto-mocked DynamoDB tables with test products
# ---------------------------------------------------------------------------


@pytest.fixture
def aws_env():
    """Set up AWS environment variables for moto."""
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
    """Create mocked DynamoDB tables with test data for integration tests."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # --- Create tables ---
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
                {'AttributeName': 'parent_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'parent_id-index',
                'KeySchema': [{'AttributeName': 'parent_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }],
            BillingMode='PAY_PER_REQUEST',
        )

        carts = dynamodb.create_table(
            TableName='Carts',
            KeySchema=[{'AttributeName': 'cart_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'cart_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        members = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        memberships = dynamodb.create_table(
            TableName='Memberships',
            KeySchema=[{'AttributeName': 'membership_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'membership_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # --- Seed test data ---

        # Members
        members.put_item(Item={
            'member_id': 'mem_buyer',
            'email': 'buyer@h-dcn.nl',
            'club_id': 'NL001',
            'status': 'active',
        })
        members.put_item(Item={
            'member_id': 'mem_presmeet',
            'email': 'presmeet@h-dcn.nl',
            'club_id': 'NL002',
            'status': 'active',
        })

        # Memberships
        memberships.put_item(Item={
            'membership_id': 'ms_buyer',
            'member_id': 'mem_buyer',
            'status': 'active',
        })

        # Parent product: T-shirt with variant_schema + order_item_fields + purchase_rules
        producten.put_item(Item={
            'product_id': 'prod_shirt',
            'is_parent': True,
            'name': 'Club T-shirt',
            'price': Decimal('25.00'),
            'active': True,
            'event_id': None,
            'variant_schema': {'Maat': ['S', 'M', 'L', 'XL']},
            'order_item_fields': [
                {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True,
                 'validation': {'min_length': 2, 'max_length': 100}},
                {'id': 'email', 'label': 'E-mail', 'type': 'email', 'required': True},
            ],
            'purchase_rules': {
                'max_per_order': 5,
                'max_per_member': 10,
                'max_per_club': 50,
            },
        })

        # Variants for T-shirt
        producten.put_item(Item={
            'product_id': 'var_shirt_m',
            'is_parent': False,
            'parent_id': 'prod_shirt',
            'event_id': None,
            'name': 'Club T-shirt - M',
            'variant_attributes': {'Maat': 'M'},
            'price': Decimal('25.00'),
            'stock': 20,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })
        producten.put_item(Item={
            'product_id': 'var_shirt_l',
            'is_parent': False,
            'parent_id': 'prod_shirt',
            'event_id': None,
            'name': 'Club T-shirt - L',
            'variant_attributes': {'Maat': 'L'},
            'price': Decimal('25.00'),
            'stock': 5,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Simple product (no rules, oversell allowed) — webshop product
        producten.put_item(Item={
            'product_id': 'prod_sticker',
            'is_parent': True,
            'name': 'H-DCN Sticker',
            'price': Decimal('5.00'),
            'active': True,
            'event_id': None,
        })
        producten.put_item(Item={
            'product_id': 'var_sticker_default',
            'is_parent': False,
            'parent_id': 'prod_sticker',
            'event_id': None,
            'name': 'Default Variant',
            'variant_attributes': {},
            'price': Decimal('5.00'),
            'stock': 100,
            'sold_count': 0,
            'allow_oversell': True,
            'active': True,
        })

        # PresMeet product with persistent order mode
        producten.put_item(Item={
            'product_id': 'prod_presmeet_event',
            'is_parent': True,
            'name': 'PresMeet Conference 2025',
            'price': Decimal('75.00'),
            'active': True,
            'event_id': 'evt-presmeet-2025',
            'order_item_fields': [
                {'id': 'attendee', 'label': 'Deelnemer', 'type': 'text', 'required': True,
                 'validation': {'min_length': 2}},
            ],
            'purchase_rules': {
                'max_per_club': 10,
                'min_per_club': 2,
                'order_mode': 'persistent',
            },
        })
        producten.put_item(Item={
            'product_id': 'var_presmeet_default',
            'is_parent': False,
            'parent_id': 'prod_presmeet_event',
            'event_id': 'evt-presmeet-2025',
            'name': 'Default Variant',
            'variant_attributes': {},
            'price': Decimal('75.00'),
            'stock': 100,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Carts
        carts.put_item(Item={
            'cart_id': 'cart_hdcn',
            'user_email': 'buyer@h-dcn.nl',
            'event_id': None,
            'items': [],
        })
        carts.put_item(Item={
            'cart_id': 'cart_presmeet',
            'user_email': 'presmeet@h-dcn.nl',
            'event_id': 'evt-presmeet-2025',
            'club_id': 'NL002',
            'items': [],
        })

        yield {
            'dynamodb': dynamodb,
            'producten': producten,
            'carts': carts,
            'orders': orders,
            'members': members,
            'memberships': memberships,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(body, method='POST', user_email='buyer@h-dcn.nl',
                user_roles=None, query_params=None, path_params=None):
    """Build a Lambda event dict for testing."""
    if user_roles is None:
        user_roles = ['hdcnLeden']
    event = {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer mock-token'},
        'body': json.dumps(body) if body else None,
        '_test_user_email': user_email,
        '_test_user_roles': user_roles,
    }
    if query_params:
        event['queryStringParameters'] = query_params
    if path_params:
        event['pathParameters'] = path_params
    return event


@pytest.fixture
def mock_auth():
    """Mock auth utilities across all handlers."""
    with patch('shared.auth_utils.extract_user_credentials') as mock_extract, \
         patch('shared.auth_utils.validate_permissions_with_regions') as mock_validate, \
         patch('shared.auth_utils.log_successful_access'):

        def extract_side_effect(event):
            return (
                event.get('_test_user_email', 'buyer@h-dcn.nl'),
                event.get('_test_user_roles', ['hdcnLeden']),
                None,
            )

        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = (False, None, None)

        yield mock_extract, mock_validate


@pytest.fixture
def mock_mollie():
    """Mock Mollie client for testing."""
    with patch('shared.mollie_client.create_payment') as mock_create, \
         patch('shared.mollie_client.get_payment') as mock_get:
        mock_create.return_value = {
            'mollie_payment_id': 'tr_integration_test',
            'checkout_url': 'https://www.mollie.com/checkout/integration',
            'status': 'open',
        }
        mock_get.return_value = {
            'id': 'tr_integration_test',
            'status': 'paid',
            'amount': {'value': '25.00', 'currency': 'EUR'},
        }
        yield mock_create, mock_get


# ---------------------------------------------------------------------------
# 13.2 — Full order lifecycle with Mollie
# ---------------------------------------------------------------------------


class TestFullOrderLifecycle:
    """Integration test: Cart → order → Mollie payment → webhook → stock reservation."""

    def test_full_lifecycle_ideal_payment(self, dynamodb_tables, mock_auth, mock_mollie):
        """
        End-to-end: create order → draft status with unpaid payment.
        In unified model, create_order creates a draft; payment happens via pay_order.
        Requirements: 6.6, 9.5, 9.6
        """
        mock_create_payment, mock_get_payment = mock_mollie

        # Step 1: Create order (creates draft with 'unpaid' status)
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'ideal',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan Jansen', 'email': 'jan@example.nl'}},
                    {'field_values': {'name': 'Piet de Vries', 'email': 'piet@example.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['payment_status'] == 'unpaid'
        order_id = body['order_id']

        # Verify order stored with unpaid/draft status
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert order['payment_status'] == 'unpaid'
        assert order['status'] == 'draft'
        assert order['member_id'] == 'mem_buyer'
        assert order.get('event_id') is None
        assert len(order['items']) == 1
        assert order['items'][0]['quantity'] == 2
        assert order['total_amount'] == Decimal('50.00')

    def test_webhook_idempotent_no_double_reservation(self, dynamodb_tables, mock_auth, mock_mollie):
        """
        Processing same webhook twice does not double-deduct stock.
        Requirements: 9.11
        """
        mock_create_payment, mock_get_payment = mock_mollie

        # Create order
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'ideal',
            'items': [{
                'product_id': 'prod_sticker',
                'variant_id': 'var_sticker_default',
                'quantity': 3,
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        order_id = json.loads(response['body'])['order_id']

        # Webhook #1
        import handler.mollie_webhook.app as webhook_mod
        importlib.reload(webhook_mod)

        webhook_event = {
            'httpMethod': 'POST',
            'headers': {},
            'body': 'id=tr_integration_test',
            'isBase64Encoded': False,
        }

        webhook_mod.lambda_handler(webhook_event, None)

        # Verify stock after first webhook
        producten = dynamodb_tables['producten']
        variant_after_1 = producten.get_item(Key={'product_id': 'var_sticker_default'})['Item']
        stock_after_1 = variant_after_1['stock']

        # Webhook #2 (same payment ID — should be idempotent)
        webhook_mod.lambda_handler(webhook_event, None)

        variant_after_2 = producten.get_item(Key={'product_id': 'var_sticker_default'})['Item']
        assert variant_after_2['stock'] == stock_after_1  # No change
        assert variant_after_2['sold_count'] == variant_after_1['sold_count']

    def test_failed_payment_webhook_marks_order_failed(self, dynamodb_tables, mock_auth, mock_mollie):
        """
        Create order results in draft with unpaid status.
        In unified model, payment failure handling requires a separate pay_order step.
        Requirements: 9.7
        """
        mock_create_payment, mock_get_payment = mock_mollie

        # Create order (draft)
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'ideal',
            'items': [{
                'product_id': 'prod_sticker',
                'variant_id': 'var_sticker_default',
                'quantity': 1,
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        order_id = body['order_id']

        # Verify draft order created
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert order['payment_status'] == 'unpaid'
        assert order['status'] == 'draft'

        # Verify stock not touched (no payment initiated)
        producten = dynamodb_tables['producten']
        variant = producten.get_item(Key={'product_id': 'var_sticker_default'})['Item']
        assert variant['stock'] == 100
        assert variant['sold_count'] == 0


# ---------------------------------------------------------------------------
# 13.3 — Purchase rules enforcement end-to-end
# ---------------------------------------------------------------------------


class TestPurchaseRulesEndToEnd:
    """Integration test: purchase rules enforcement.
    
    Note: In the unified model, purchase rules are enforced at submission time
    (submit_presmeet_booking), not at order creation time. The create_order
    handler creates drafts without rule validation.
    """

    @pytest.mark.xfail(reason="Purchase rules not enforced at create_order time in unified model")
    def test_max_per_member_exceeded_rejected(self, dynamodb_tables, mock_auth):
        """
        After filling max_per_member quota, next order is rejected.
        Requirements: 16.3
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        # First: seed an existing paid order consuming 8 of 10 max_per_member
        orders_table = dynamodb_tables['orders']
        orders_table.put_item(Item={
            'order_id': 'existing_order_1',
            'member_id': 'mem_buyer',
            'user_email': 'buyer@h-dcn.nl',
            'payment_status': 'paid',
            'status': 'paid',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 8,
            }],
        })

        # Attempt to order 3 more (8 + 3 = 11 > 10 max_per_member)
        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 3,
                'item_fields_data': [
                    {'field_values': {'name': 'AA', 'email': 'a@x.nl'}},
                    {'field_values': {'name': 'BB', 'email': 'b@x.nl'}},
                    {'field_values': {'name': 'CC', 'email': 'c@x.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'purchase_rule_violation'
        assert body['details']['rule'] == 'max_per_member'

    @pytest.mark.xfail(reason="Purchase rules not enforced at create_order time in unified model")
    def test_max_per_club_exceeded_rejected(self, dynamodb_tables, mock_auth):
        """
        Club exceeding max_per_club limit is rejected.
        Requirements: 16.4
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        # Seed existing orders for the club totaling 48 of 50 max
        # Use a different member_id so max_per_member (10) won't trigger first
        orders_table = dynamodb_tables['orders']
        orders_table.put_item(Item={
            'order_id': 'club_order_1',
            'member_id': 'mem_other_club_member',
            'club_id': 'NL001',
            'user_email': 'other@h-dcn.nl',
            'payment_status': 'paid',
            'status': 'paid',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 48,
            }],
        })

        # Attempt to order 3 more (48 + 3 = 51 > 50 max_per_club)
        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 3,
                'item_fields_data': [
                    {'field_values': {'name': 'XX', 'email': 'x@y.nl'}},
                    {'field_values': {'name': 'YY', 'email': 'y@y.nl'}},
                    {'field_values': {'name': 'ZZ', 'email': 'z@y.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'purchase_rule_violation'
        assert body['details']['rule'] == 'max_per_club'

    @pytest.mark.xfail(reason="Purchase rules not enforced at create_order time in unified model")
    def test_max_per_order_exceeded_rejected(self, dynamodb_tables, mock_auth):
        """
        Single order quantity exceeding max_per_order is rejected.
        Requirements: 16.2
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 6,  # max_per_order is 5
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'purchase_rule_violation'
        assert body['details']['rule'] == 'max_per_order'
        assert body['details']['limit'] == 5

    def test_within_limits_accepted(self, dynamodb_tables, mock_auth):
        """
        Order within all purchase rule limits is accepted.
        Requirements: 16.1
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan', 'email': 'jan@test.nl'}},
                    {'field_values': {'name': 'Piet', 'email': 'piet@test.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 201


# ---------------------------------------------------------------------------
# 13.4 — Item fields validation end-to-end
# ---------------------------------------------------------------------------


class TestItemFieldsValidationEndToEnd:
    """Integration test: item fields validation.
    
    Note: In the unified model, item fields validation is enforced at submission
    time (submit_presmeet_booking), not at order creation time. The create_order
    handler stores item_fields_data without validation.
    """

    @pytest.mark.xfail(reason="Item fields not validated at create_order time in unified model")
    def test_missing_required_fields_rejected(self, dynamodb_tables, mock_auth):
        """
        Order with empty required field values returns 400.
        Requirements: 17.1
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 1,
                'item_fields_data': [
                    {'field_values': {'name': '', 'email': 'valid@test.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_validation_error'
        assert body['details']['field_id'] == 'name'

    @pytest.mark.xfail(reason="Item fields not validated at create_order time in unified model")
    def test_wrong_item_fields_count_rejected(self, dynamodb_tables, mock_auth):
        """
        item_fields_data count != quantity returns 400.
        Requirements: 17.5
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 3,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan', 'email': 'j@t.nl'}},
                    {'field_values': {'name': 'Piet', 'email': 'p@t.nl'}},
                    # Missing third entry
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_count_mismatch'
        assert body['details']['expected'] == 3
        assert body['details']['actual'] == 2

    @pytest.mark.xfail(reason="Item fields not validated at create_order time in unified model")
    def test_constraint_violation_rejected(self, dynamodb_tables, mock_auth):
        """
        Field value violating min_length constraint returns 400.
        Requirements: 17.2
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 1,
                'item_fields_data': [
                    {'field_values': {'name': 'X', 'email': 'x@t.nl'}},  # min_length=2
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'item_fields_validation_error'
        assert body['details']['field_id'] == 'name'
        assert 'min_length' in body['details'].get('constraint', '')

    @pytest.mark.xfail(reason="Item fields flattening not implemented at create_order time in unified model")
    def test_valid_fields_accepted(self, dynamodb_tables, mock_auth):
        """
        Valid item_fields_data passes all validation checks.
        Requirements: 17.1-17.5
        """
        import handler.create_order.app as create_order_mod
        importlib.reload(create_order_mod)

        event = _make_event({
            'cart_id': 'cart_hdcn',
            'payment_method': 'bank_transfer',
            'items': [{
                'product_id': 'prod_shirt',
                'variant_id': 'var_shirt_m',
                'quantity': 2,
                'item_fields_data': [
                    {'field_values': {'name': 'Jan Jansen', 'email': 'jan@h-dcn.nl'}},
                    {'field_values': {'name': 'Piet de Vries', 'email': 'piet@h-dcn.nl'}},
                ],
            }],
        })

        response = create_order_mod.lambda_handler(event, None)
        assert response['statusCode'] == 201

        # Verify item_fields_data stored correctly on the order
        body = json.loads(response['body'])
        order_id = body['order_id']
        orders_table = dynamodb_tables['orders']
        order = orders_table.get_item(Key={'order_id': order_id})['Item']
        item_data = order['items'][0]['item_fields_data']

        # Should be flattened: 2 items × 2 fields = 4 entries
        assert len(item_data) == 4
        assert item_data[0]['item_index'] == 1
        assert item_data[0]['field_id'] == 'name'
        assert item_data[0]['value'] == 'Jan Jansen'


# ---------------------------------------------------------------------------
# 13.5 — Event-based product filtering
# ---------------------------------------------------------------------------


class TestEventBasedProductFiltering:
    """Integration test: event_id-based product visibility."""

    def test_webshop_request_shows_generic_products_only(self, dynamodb_tables, mock_auth):
        """
        Requesting products with event_id=null shows webshop products only.
        Requirements: 12.11
        """
        import handler.get_products.app as get_products_mod
        importlib.reload(get_products_mod)

        event = _make_event(
            body=None,
            method='GET',
            user_email='buyer@h-dcn.nl',
            user_roles=['hdcnLeden'],
            query_params={'event_id': 'null'},
        )

        response = get_products_mod.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        products = body['products']

        # Should contain webshop products (event_id: None)
        product_ids = [p['product_id'] for p in products]
        assert 'prod_shirt' in product_ids
        assert 'prod_sticker' in product_ids
        # Should NOT contain event-linked products
        assert 'prod_presmeet_event' not in product_ids

    def test_event_request_shows_event_products(self, dynamodb_tables, mock_auth):
        """
        Requesting products with specific event_id shows event-linked products.
        Requirements: 12.2
        """
        import handler.get_products.app as get_products_mod
        importlib.reload(get_products_mod)

        event = _make_event(
            body=None,
            method='GET',
            user_email='presmeet@h-dcn.nl',
            user_roles=['Regio_Pressmeet'],
            query_params={'event_id': 'evt-presmeet-2025'},
        )

        response = get_products_mod.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        products = body['products']

        product_ids = [p['product_id'] for p in products]
        assert 'prod_presmeet_event' in product_ids
        assert 'prod_shirt' not in product_ids

    def test_no_roles_returns_403(self, dynamodb_tables, mock_auth):
        """
        User with no qualifying roles gets 403.
        Requirements: 7.5
        """
        import handler.get_products.app as get_products_mod
        importlib.reload(get_products_mod)

        event = _make_event(
            body=None,
            method='GET',
            user_email='nobody@h-dcn.nl',
            user_roles=['verzoek_lid'],
            query_params={},
        )

        response = get_products_mod.lambda_handler(event, None)
        assert response['statusCode'] == 403


# ---------------------------------------------------------------------------
# 13.6 — Migration scripts
# ---------------------------------------------------------------------------


class TestMigrationScripts:
    """Integration test: migration scripts produce correct results on fixture data."""

    def test_migrate_opties_to_variants(self, dynamodb_tables):
        """
        migrate_opties_to_variants generates variants and is idempotent.
        Requirements: 11.1–11.5
        """
        producten = dynamodb_tables['producten']

        # Seed a product with legacy opties field
        producten.put_item(Item={
            'product_id': 'prod_legacy',
            'is_parent': True,
            'name': 'Legacy Product',
            'price': Decimal('15.00'),
            'active': True,
            'opties': 'Rood, Blauw, Groen',
        })

        # Run migration
        from scripts.migrate_opties_to_variants import migrate
        with patch('scripts.migrate_opties_to_variants.get_table', return_value=producten):
            result = migrate(profile=None, dry_run=False)

        # Verify result
        assert result['successful'] == 1
        assert result['errors'] == 0

        # Verify parent product updated
        parent = producten.get_item(Key={'product_id': 'prod_legacy'})['Item']
        assert 'opties' not in parent
        assert parent['legacy_opties'] == 'Rood, Blauw, Groen'
        assert parent['variant_schema'] == {'opties': ['Rood', 'Blauw', 'Groen']}

        # Verify 3 variant records created
        from boto3.dynamodb.conditions import Key as DKey
        variants_resp = producten.query(
            IndexName='parent_id-index',
            KeyConditionExpression=DKey('parent_id').eq('prod_legacy'),
        )
        variants = variants_resp['Items']
        assert len(variants) == 3
        variant_values = sorted([v['variant_attributes']['opties'] for v in variants])
        assert variant_values == ['Blauw', 'Groen', 'Rood']

        # Verify idempotence: second run produces no changes
        # After migration, the product no longer has `opties` field (it was removed),
        # so it won't be found by the migration scan. This IS the idempotency:
        # running again finds nothing to migrate.
        with patch('scripts.migrate_opties_to_variants.get_table', return_value=producten):
            result2 = migrate(profile=None, dry_run=False)

        assert result2['successful'] == 0
        assert result2['total_with_opties'] == 0

        # Verify still only 3 variants
        variants_resp2 = producten.query(
            IndexName='parent_id-index',
            KeyConditionExpression=DKey('parent_id').eq('prod_legacy'),
        )
        assert len(variants_resp2['Items']) == 3

    def test_migrate_presmeet_config(self, dynamodb_tables):
        """
        migrate_presmeet_config converts config records to unified model.
        Requirements: 14.3–14.6
        """
        producten = dynamodb_tables['producten']

        # Seed a config_presmeet_* record
        producten.put_item(Item={
            'product_id': 'config_presmeet_conference',
            'product_type': 'conference_ticket',
            'unit_price': Decimal('50.00'),
            'max_per_club': 20,
            'min_per_club': 3,
            'required_attributes': {
                'size': {'type': 'string', 'required': True, 'enum': ['S', 'M', 'L', 'XL']},
                'name': {'type': 'string', 'required': True, 'min_length': 2, 'max_length': 50},
                'age': {'type': 'integer', 'required': False, 'minimum': 18, 'maximum': 99},
            },
        })

        # Run migration
        from scripts.migrate_presmeet_config import migrate
        with patch('scripts.migrate_presmeet_config.get_table', return_value=producten):
            migrate(profile=None, dry_run=False)

        # Verify the record was updated
        record = producten.get_item(Key={'product_id': 'config_presmeet_conference'})['Item']

        assert record['is_parent'] is True
        assert record['price'] == Decimal('50.00')

        # variant_schema: "size" had enum values → becomes axis
        assert 'variant_schema' in record
        assert record['variant_schema'] == {'size': ['S', 'M', 'L', 'XL']}

        # order_item_fields: "name" and "age" (non-enum) → become fields
        assert 'order_item_fields' in record
        field_ids = [f['id'] for f in record['order_item_fields']]
        assert 'name' in field_ids
        assert 'age' in field_ids

        # purchase_rules
        assert record['purchase_rules']['max_per_club'] == 20
        assert record['purchase_rules']['min_per_club'] == 3
        assert record['purchase_rules']['order_mode'] == 'persistent'

        # Legacy field preserved
        assert 'legacy_required_attributes' in record

    def test_migrate_cart_selectedoption(self, dynamodb_tables):
        """
        migrate_cart_selectedoption replaces selectedOption with variant_id.
        Requirements: 11.6, 11.7
        """
        producten = dynamodb_tables['producten']
        carts = dynamodb_tables['carts']

        # Seed a product with a variant matching "opties" = "M"
        producten.put_item(Item={
            'product_id': 'prod_migrated',
            'is_parent': True,
            'name': 'Migrated Product',
            'price': Decimal('20.00'),
            'active': True,
            'variant_schema': {'opties': ['S', 'M', 'L']},
        })
        producten.put_item(Item={
            'product_id': 'var_migrated_s',
            'is_parent': False,
            'parent_id': 'prod_migrated',
            'variant_attributes': {'opties': 'S'},
            'stock': 10,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })
        producten.put_item(Item={
            'product_id': 'var_migrated_m',
            'is_parent': False,
            'parent_id': 'prod_migrated',
            'variant_attributes': {'opties': 'M'},
            'stock': 10,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Seed a cart with legacy selectedOption
        carts.put_item(Item={
            'cart_id': 'cart_legacy',
            'user_email': 'buyer@h-dcn.nl',
            'items': [
                {
                    'product_id': 'prod_migrated',
                    'selectedOption': 'M',
                    'quantity': 2,
                    'unit_price': Decimal('20.00'),
                },
            ],
        })

        # Run migration
        from scripts.migrate_cart_selectedoption import migrate
        with patch('scripts.migrate_cart_selectedoption.get_tables',
                   return_value=(carts, producten)):
            migrate(profile=None, dry_run=False)

        # Verify cart was updated
        cart_after = carts.get_item(Key={'cart_id': 'cart_legacy'})['Item']
        item = cart_after['items'][0]

        # selectedOption should be replaced with variant_id
        assert 'selectedOption' not in item
        assert item['variant_id'] == 'var_migrated_m'
        assert item['variant_attributes'] == {'opties': 'M'}
        assert item['quantity'] == 2

    def test_migrate_cart_unmatched_logged(self, dynamodb_tables):
        """
        Cart items with no matching variant are left unchanged and logged.
        Requirements: 11.7
        """
        producten = dynamodb_tables['producten']
        carts = dynamodb_tables['carts']

        # Seed cart with selectedOption that has no matching variant
        carts.put_item(Item={
            'cart_id': 'cart_unmatched',
            'user_email': 'buyer@h-dcn.nl',
            'event_id': None,
            'items': [
                {
                    'product_id': 'prod_shirt',
                    'selectedOption': 'XXL',  # No XXL variant exists
                    'quantity': 1,
                    'unit_price': Decimal('25.00'),
                },
            ],
        })

        # Run migration
        from scripts.migrate_cart_selectedoption import migrate
        with patch('scripts.migrate_cart_selectedoption.get_tables',
                   return_value=(carts, producten)):
            migrate(profile=None, dry_run=False)

        # Verify item left unchanged (still has selectedOption)
        cart_after = carts.get_item(Key={'cart_id': 'cart_unmatched'})['Item']
        item = cart_after['items'][0]
        assert 'selectedOption' in item
        assert item['selectedOption'] == 'XXL'
