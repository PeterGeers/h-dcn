"""
Unit tests for the mollie_webhook handler.

Tests cover:
- Extraction of payment ID from form-encoded and JSON bodies
- Legacy webshop flow: paid status updates order, triggers stock reservation
- Legacy webshop flow: failed/expired/cancelled updates to payment_failed
- PresMeet flow: paid status updates payment record + recalculates order totals
- PresMeet flow: partial payment handling
- PresMeet flow: failed status updates payment record
- Idempotency: duplicate webhooks don't duplicate stock reservations
- Forward-only transitions: paid orders never go back to failed
- Always returns 200 (Mollie requirement)
"""

import json
import os
import sys
import pytest
import boto3
from decimal import Decimal
from unittest.mock import patch, MagicMock
from moto import mock_aws

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))


@pytest.fixture
def aws_env():
    """Set up mocked AWS credentials and env vars."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    os.environ['ORDERS_TABLE_NAME'] = 'Orders'
    os.environ['PAYMENTS_TABLE_NAME'] = 'Payments'
    os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
    os.environ['MOLLIE_API_KEY'] = 'test_xxx'


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mocked Orders, Payments, and Producten DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        payments = dynamodb.create_table(
            TableName='Payments',
            KeySchema=[{'AttributeName': 'payment_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'payment_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        yield {'orders': orders, 'payments': payments, 'producten': producten}


def _create_order(orders_table, order_id, mollie_payment_id=None, payment_status='pending',
                  items=None, stock_reserved=False, total_amount=50, total_paid=0):
    """Helper to insert an order record."""
    order = {
        'order_id': order_id,
        'payment_status': payment_status,
        'user_email': 'test@h-dcn.nl',
        'total_amount': Decimal(str(total_amount)),
        'total_paid': Decimal(str(total_paid)),
        'items': items or [
            {'variant_id': 'var_001', 'quantity': 2, 'product_id': 'prod_001'}
        ],
    }
    if mollie_payment_id:
        order['mollie_payment_id'] = mollie_payment_id
    if stock_reserved:
        order['stock_reserved'] = True
    orders_table.put_item(Item=order)


def _create_payment_record(payments_table, payment_id, order_id, mollie_payment_id,
                           amount=50, status='pending'):
    """Helper to insert a payment record in the Payments table."""
    payments_table.put_item(Item={
        'payment_id': payment_id,
        'order_id': order_id,
        'mollie_payment_id': mollie_payment_id,
        'amount': Decimal(str(amount)),
        'status': status,
        'provider': 'mollie',
        'method': 'ideal',
        'created_at': '2027-01-15T10:00:00+00:00',
    })


def _create_variant(producten_table, variant_id, stock=10, sold_count=0):
    """Helper to insert a variant record."""
    producten_table.put_item(Item={
        'product_id': variant_id,
        'is_parent': False,
        'parent_id': 'prod_001',
        'stock': stock,
        'sold_count': sold_count,
        'allow_oversell': False,
        'active': True,
    })


def _make_event(mollie_payment_id, form_encoded=True, base64_encoded=False):
    """Create a mock API Gateway event for Mollie webhook."""
    if form_encoded:
        body = f"id={mollie_payment_id}"
    else:
        body = json.dumps({"id": mollie_payment_id})

    if base64_encoded:
        import base64
        body = base64.b64encode(body.encode()).decode()

    return {
        'httpMethod': 'POST',
        'body': body,
        'isBase64Encoded': base64_encoded,
        'headers': {},
    }


class TestPaymentIdExtraction:
    """Tests for extracting payment ID from various body formats."""

    @patch('shared.mollie_client.get_payment')
    def test_extracts_from_form_encoded_body(self, mock_get_payment, dynamodb_tables):
        """Mollie sends form-encoded body: id=tr_xxx"""
        mock_get_payment.return_value = {'id': 'tr_test123', 'status': 'open'}
        _create_order(dynamodb_tables['orders'], 'ord_001', 'tr_test123')

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_test123', form_encoded=True)
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_get_payment.assert_called_once_with('tr_test123')

    @patch('shared.mollie_client.get_payment')
    def test_extracts_from_json_body(self, mock_get_payment, dynamodb_tables):
        """Fallback: JSON body {"id": "tr_xxx"}"""
        mock_get_payment.return_value = {'id': 'tr_json', 'status': 'open'}
        _create_order(dynamodb_tables['orders'], 'ord_002', 'tr_json')

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_json', form_encoded=False)
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_get_payment.assert_called_once_with('tr_json')

    def test_returns_200_when_no_payment_id(self, dynamodb_tables):
        """No payment ID in body still returns 200."""
        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = {'httpMethod': 'POST', 'body': '', 'isBase64Encoded': False, 'headers': {}}
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'ignored'


class TestLegacyWebshopPaidStatus:
    """Tests for handling Mollie 'paid' status in the legacy webshop flow."""

    @patch('shared.mollie_client.get_payment')
    def test_paid_updates_order_and_reserves_stock(self, mock_get_payment, dynamodb_tables):
        """When Mollie reports paid, order transitions to paid and stock is reserved."""
        mock_get_payment.return_value = {'id': 'tr_paid001', 'status': 'paid'}
        _create_order(dynamodb_tables['orders'], 'ord_paid', 'tr_paid001', payment_status='pending')
        _create_variant(dynamodb_tables['producten'], 'var_001', stock=10, sold_count=0)

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_paid001')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify order updated
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_paid'})['Item']
        assert order['payment_status'] == 'paid'
        assert order['stock_reserved'] == True

        # Verify stock was decremented
        variant = dynamodb_tables['producten'].get_item(Key={'product_id': 'var_001'})['Item']
        assert variant['stock'] == 8  # 10 - 2
        assert variant['sold_count'] == 2


class TestLegacyWebshopFailedStatus:
    """Tests for handling Mollie failed/expired/cancelled statuses in webshop flow."""

    @pytest.mark.parametrize('mollie_status', ['failed', 'expired', 'cancelled'])
    @patch('shared.mollie_client.get_payment')
    def test_failed_updates_order_to_payment_failed(self, mock_get_payment, mollie_status, dynamodb_tables):
        """When Mollie reports failed/expired/cancelled, order goes to payment_failed."""
        mock_get_payment.return_value = {'id': 'tr_fail', 'status': mollie_status}
        _create_order(dynamodb_tables['orders'], 'ord_fail', 'tr_fail', payment_status='pending')

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_fail')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_fail'})['Item']
        assert order['payment_status'] == 'payment_failed'

    @patch('shared.mollie_client.get_payment')
    def test_failed_does_not_reserve_stock(self, mock_get_payment, dynamodb_tables):
        """Failed payments should never trigger stock reservation."""
        mock_get_payment.return_value = {'id': 'tr_nores', 'status': 'failed'}
        _create_order(dynamodb_tables['orders'], 'ord_nores', 'tr_nores', payment_status='pending')
        _create_variant(dynamodb_tables['producten'], 'var_001', stock=10, sold_count=0)

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_nores')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Stock unchanged
        variant = dynamodb_tables['producten'].get_item(Key={'product_id': 'var_001'})['Item']
        assert variant['stock'] == 10
        assert variant['sold_count'] == 0


class TestPresMeetPaidFlow:
    """Tests for the PresMeet payment flow (Payments table lookup)."""

    @patch('shared.mollie_client.get_payment')
    def test_paid_updates_payment_record_and_order(self, mock_get_payment, dynamodb_tables):
        """
        PresMeet flow: paid webhook updates payment record status to 'paid',
        recalculates order total_paid, and sets payment_status.
        """
        mock_get_payment.return_value = {'id': 'tr_pm001', 'status': 'paid'}

        # Create order with total_amount=100, total_paid=0
        _create_order(
            dynamodb_tables['orders'], 'ord_pm1', total_amount=100, total_paid=0,
            payment_status='unpaid'
        )
        # Create payment record in Payments table
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_001', 'ord_pm1', 'tr_pm001', amount=100
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pm001')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['flow'] == 'presmeet'

        # Payment record updated to "paid"
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_001'})['Item']
        assert payment['status'] == 'paid'

        # Order total_paid and payment_status updated
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pm1'})['Item']
        assert order['total_paid'] == Decimal('100')
        assert order['payment_status'] == 'paid'

    @patch('shared.mollie_client.get_payment')
    def test_partial_payment_sets_partial_status(self, mock_get_payment, dynamodb_tables):
        """
        PresMeet flow: when paid amount < total_amount, payment_status becomes 'partial'.
        """
        mock_get_payment.return_value = {'id': 'tr_pm002', 'status': 'paid'}

        # Order total = 200, payment of 100 (partial)
        _create_order(
            dynamodb_tables['orders'], 'ord_pm2', total_amount=200, total_paid=0,
            payment_status='unpaid'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_002', 'ord_pm2', 'tr_pm002', amount=100
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pm002')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Order payment_status should be "partial"
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pm2'})['Item']
        assert order['total_paid'] == Decimal('100')
        assert order['payment_status'] == 'partial'

    @patch('shared.mollie_client.get_payment')
    def test_second_payment_completes_order(self, mock_get_payment, dynamodb_tables):
        """
        PresMeet flow: second payment brings total_paid >= total_amount → "paid".
        """
        mock_get_payment.return_value = {'id': 'tr_pm003b', 'status': 'paid'}

        # Order total = 200, already has one paid payment of 100
        _create_order(
            dynamodb_tables['orders'], 'ord_pm3', total_amount=200, total_paid=100,
            payment_status='partial'
        )
        # First payment already paid
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_003a', 'ord_pm3', 'tr_pm003a',
            amount=100, status='paid'
        )
        # Second payment just arrived
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_003b', 'ord_pm3', 'tr_pm003b',
            amount=100, status='pending'
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pm003b')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Payment record updated
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_003b'})['Item']
        assert payment['status'] == 'paid'

        # Order now fully paid
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pm3'})['Item']
        assert order['total_paid'] == Decimal('200')
        assert order['payment_status'] == 'paid'


class TestPresMeetFailedFlow:
    """Tests for PresMeet payment failure handling."""

    @pytest.mark.parametrize('mollie_status', ['failed', 'expired', 'cancelled'])
    @patch('shared.mollie_client.get_payment')
    def test_failed_updates_payment_record_not_order_status(
        self, mock_get_payment, mollie_status, dynamodb_tables
    ):
        """
        PresMeet flow: failed webhook updates payment record to 'failed',
        order stays at current payment_status (unpaid since no paid payments).
        """
        mock_get_payment.return_value = {'id': 'tr_pmfail', 'status': mollie_status}

        _create_order(
            dynamodb_tables['orders'], 'ord_pmfail', total_amount=100, total_paid=0,
            payment_status='unpaid'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_fail', 'ord_pmfail', 'tr_pmfail', amount=100
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pmfail')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Payment record updated to "failed"
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_fail'})['Item']
        assert payment['status'] == 'failed'

        # Order total_paid stays 0, payment_status is "unpaid"
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pmfail'})['Item']
        assert order['total_paid'] == Decimal('0')
        assert order['payment_status'] == 'unpaid'

    @patch('shared.mollie_client.get_payment')
    def test_failed_payment_with_existing_paid_keeps_partial(
        self, mock_get_payment, dynamodb_tables
    ):
        """
        PresMeet flow: if one payment is paid and a second fails,
        order stays partial (not unpaid).
        """
        mock_get_payment.return_value = {'id': 'tr_pmfail2', 'status': 'failed'}

        # Order total = 200, one payment already paid (100)
        _create_order(
            dynamodb_tables['orders'], 'ord_pmpartial', total_amount=200, total_paid=100,
            payment_status='partial'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_ok', 'ord_pmpartial', 'tr_pmok',
            amount=100, status='paid'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_fail2', 'ord_pmpartial', 'tr_pmfail2',
            amount=100, status='pending'
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pmfail2')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Failed payment record updated
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_fail2'})['Item']
        assert payment['status'] == 'failed'

        # Order still partial (100 paid out of 200)
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pmpartial'})['Item']
        assert order['total_paid'] == Decimal('100')
        assert order['payment_status'] == 'partial'


class TestPresMeetIntermediateStatus:
    """Tests for intermediate (non-terminal) Mollie statuses in PresMeet flow."""

    @patch('shared.mollie_client.get_payment')
    def test_open_status_does_not_update_payment_record(self, mock_get_payment, dynamodb_tables):
        """Intermediate statuses (open, pending) don't change anything."""
        mock_get_payment.return_value = {'id': 'tr_pmopen', 'status': 'open'}

        _create_order(
            dynamodb_tables['orders'], 'ord_pmopen', total_amount=100, total_paid=0,
            payment_status='unpaid'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_open', 'ord_pmopen', 'tr_pmopen', amount=100
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_pmopen')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Payment record still pending
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_open'})['Item']
        assert payment['status'] == 'pending'

        # Order unchanged
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_pmopen'})['Item']
        assert order['payment_status'] == 'unpaid'


class TestIdempotency:
    """Tests for idempotent webhook processing."""

    @patch('shared.mollie_client.get_payment')
    def test_duplicate_paid_webhook_does_not_double_reserve(self, mock_get_payment, dynamodb_tables):
        """Processing the same paid webhook twice doesn't decrement stock twice."""
        mock_get_payment.return_value = {'id': 'tr_idem', 'status': 'paid'}
        _create_order(dynamodb_tables['orders'], 'ord_idem', 'tr_idem', payment_status='pending')
        _create_variant(dynamodb_tables['producten'], 'var_001', stock=10, sold_count=0)

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_idem')

        # First call
        response1 = webhook_module.lambda_handler(event, None)
        assert response1['statusCode'] == 200

        # Second call (duplicate webhook)
        response2 = webhook_module.lambda_handler(event, None)
        assert response2['statusCode'] == 200

        # Stock only decremented once
        variant = dynamodb_tables['producten'].get_item(Key={'product_id': 'var_001'})['Item']
        assert variant['stock'] == 8  # 10 - 2 (not 10 - 4)
        assert variant['sold_count'] == 2


class TestForwardOnlyTransitions:
    """Tests for forward-only state transitions."""

    @patch('shared.mollie_client.get_payment')
    def test_paid_order_never_transitions_to_failed(self, mock_get_payment, dynamodb_tables):
        """Once paid, a failed webhook should not change the order status."""
        mock_get_payment.return_value = {'id': 'tr_nofail', 'status': 'failed'}
        _create_order(
            dynamodb_tables['orders'], 'ord_nofail', 'tr_nofail',
            payment_status='paid', stock_reserved=True
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_nofail')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Order remains paid
        order = dynamodb_tables['orders'].get_item(Key={'order_id': 'ord_nofail'})['Item']
        assert order['payment_status'] == 'paid'


class TestAlwaysReturns200:
    """Mollie requires 200 for all webhook calls."""

    @patch('shared.mollie_client.get_payment')
    def test_returns_200_when_order_not_found(self, mock_get_payment, dynamodb_tables):
        """Unknown mollie_payment_id still returns 200."""
        mock_get_payment.return_value = {'id': 'tr_unknown', 'status': 'paid'}

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_unknown')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['reason'] == 'order not found'

    @patch('shared.mollie_client.get_payment')
    def test_returns_200_on_mollie_api_error(self, mock_get_payment, dynamodb_tables):
        """Mollie API errors still return 200."""
        from shared.mollie_client import MollieError
        mock_get_payment.side_effect = MollieError("API timeout")

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_apierr')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_returns_200_on_options_request(self, dynamodb_tables):
        """OPTIONS request returns 200."""
        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = {'httpMethod': 'OPTIONS'}
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200


class TestPresMeetPriorityOverWebshop:
    """Tests ensuring Payments table lookup takes priority."""

    @patch('shared.mollie_client.get_payment')
    def test_payments_table_checked_first(self, mock_get_payment, dynamodb_tables):
        """
        If a mollie_payment_id exists in BOTH Payments table and Orders table,
        the Payments table (PresMeet flow) takes priority.
        """
        mock_get_payment.return_value = {'id': 'tr_both', 'status': 'paid'}

        # Create in both tables with same mollie_payment_id
        _create_order(
            dynamodb_tables['orders'], 'ord_both', mollie_payment_id='tr_both',
            total_amount=100, total_paid=0, payment_status='unpaid'
        )
        _create_payment_record(
            dynamodb_tables['payments'], 'pay_both', 'ord_both', 'tr_both', amount=100
        )

        import importlib
        import handler.mollie_webhook.app as webhook_module
        importlib.reload(webhook_module)

        event = _make_event('tr_both')
        response = webhook_module.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['flow'] == 'presmeet'

        # Payment record should be updated
        payment = dynamodb_tables['payments'].get_item(Key={'payment_id': 'pay_both'})['Item']
        assert payment['status'] == 'paid'
