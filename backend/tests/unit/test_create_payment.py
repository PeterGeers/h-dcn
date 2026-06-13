"""
Unit Tests for create_payment Lambda Handler.

Tests the unified create_payment handler:
- Missing order_id → 400
- Order not found → 404
- Not owner → 403
- Order status not "submitted" → 409
- No outstanding balance → 400
- Successful payment creation → stores record, returns checkout_url
- Mollie API error → 502 without creating payment record
- Supported payment methods (iDEAL, creditcard, banktransfer)
- Unsupported method → 400
"""

import json
import pytest
import base64
from unittest.mock import patch, MagicMock
from decimal import Decimal
import sys
import os

# Ensure the layers path and backend root are on sys.path
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear any previously cached shared modules
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env vars before importing
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-west-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('PAYMENTS_TABLE_NAME', 'Payments')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')
os.environ.setdefault('PRODUCTEN_TABLE_NAME', 'Producten')
os.environ.setdefault('MOLLIE_API_KEY', 'test_api_key_xxx')
os.environ.setdefault('PAYMENT_REDIRECT_URL', 'https://portal.h-dcn.nl/booking')
os.environ.setdefault('MOLLIE_WEBHOOK_URL', 'https://api.h-dcn.nl/mollie-webhook')

import handler.create_payment.app as app
from handler.create_payment.app import lambda_handler
from shared.mollie_client import MollieError


def create_jwt_token(email="user@h-dcn.nl", groups=None):
    """Helper to create JWT tokens for testing."""
    if groups is None:
        groups = ["hdcnLeden"]

    payload = {
        "email": email,
        "cognito:groups": groups,
        "exp": 9999999999,
        "iat": 1000000000,
    }

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')
    signature = "test_signature"

    return f"{header}.{payload_encoded}.{signature}"


def make_event(token=None, path_params=None, body=None, method='POST'):
    """Helper to create an API Gateway event."""
    event = {
        'httpMethod': method,
        'headers': {},
        'pathParameters': path_params,
        'body': json.dumps(body) if body else None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


def make_order(
    order_id='ord-123',
    source_id='evt-abc-123',
    member_id='member-001',
    status='submitted',
    items=None,
    total_paid=Decimal('0.00'),
    club_id=None,
    delegates=None,
):
    """Helper to create a mock order record."""
    if items is None:
        items = [
            {
                'product_id': 'prod-001',
                'unit_price': Decimal('150.00'),
                'quantity': 2,
                'line_total': Decimal('300.00'),
            },
            {
                'product_id': 'prod-002',
                'unit_price': Decimal('50.00'),
                'quantity': 1,
                'line_total': Decimal('50.00'),
            },
        ]

    order = {
        'order_id': order_id,
        'source_id': source_id,
        'member_id': member_id,
        'status': status,
        'items': items,
        'total_paid': total_paid,
        'version': 2,
        'created_at': '2027-01-10T08:00:00+00:00',
        'updated_at': '2027-01-15T10:30:00+00:00',
    }

    if club_id:
        order['club_id'] = club_id
    if delegates:
        order['delegates'] = delegates

    return order


def make_member(member_id='member-001', email='user@h-dcn.nl', club_id=None):
    """Helper to create a mock member record."""
    member = {
        'member_id': member_id,
        'email': email,
        'member_type': 'hdcn_member',
        'allowed_events': [],
    }
    if club_id:
        member['club_id'] = club_id
    return member


class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestMissingOrderId:
    """Test missing order ID in path."""

    def test_missing_order_id_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params={})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'order' in body['error'].lower()

    def test_null_path_params_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params=None)
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestOrderNotFound:
    """Test when order does not exist."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order', return_value=None)
    def test_order_not_found_returns_404(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'nonexistent'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestOwnership:
    """Test ownership verification (403 when not owner)."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_non_owner_returns_403(self, mock_get_order, mock_resolve):
        """User who doesn't own the order and is not admin/delegate gets 403."""
        mock_resolve.return_value = (make_member(member_id='different-member'), None)
        mock_get_order.return_value = make_order(member_id='member-001')

        token = create_jwt_token(email="other@h-dcn.nl")
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'owner' in body['error'].lower() or 'denied' in body['error'].lower()

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_delegate_can_access(self, mock_get_order, mock_resolve):
        """Delegate of a club-scoped order can initiate payment."""
        mock_resolve.return_value = (make_member(member_id='delegate-member'), None)
        mock_get_order.return_value = make_order(
            member_id='primary-member',
            delegates={
                'primary_member_id': 'primary-member',
                'secondary_member_id': 'delegate-member',
            },
            status='submitted',
        )

        # Mock Mollie and payments table for successful path
        with patch('handler.create_payment.app.create_payment') as mock_mollie, \
             patch.object(app.payments_table, 'put_item'):
            mock_mollie.return_value = {
                'mollie_payment_id': 'tr_delegate',
                'checkout_url': 'https://www.mollie.com/checkout/delegate',
                'status': 'open',
            }

            token = create_jwt_token(email="delegate@h-dcn.nl")
            event = make_event(token=token, path_params={'id': 'ord-123'})
            response = lambda_handler(event, None)
            assert response['statusCode'] == 201


class TestOrderStatusValidation:
    """Test that only submitted orders can be paid."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_draft_order_returns_409(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)
        mock_get_order.return_value = make_order(status='draft')

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'draft' in body['error'].lower()

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_locked_order_returns_409(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)
        mock_get_order.return_value = make_order(status='locked')

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'locked' in body['error'].lower()


class TestSuccessfulPayment:
    """Test successful payment creation."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    @patch('handler.create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_creates_payment_and_returns_checkout_url(
        self, mock_put, mock_mollie, mock_get_order, mock_resolve
    ):
        mock_resolve.return_value = (make_member(), None)
        order = make_order(source_id='evt-abc-123')
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_abc123',
            'checkout_url': 'https://www.mollie.com/checkout/test',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['checkout_url'] == 'https://www.mollie.com/checkout/test'
        assert body['mollie_payment_id'] == 'tr_abc123'
        assert body['amount'] == 350.00  # 300 + 50
        assert body['method'] == 'ideal'
        assert 'payment_id' in body

        # Verify Mollie was called with correct amount
        mock_mollie.assert_called_once()
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '350.00'
        assert call_kwargs.kwargs['method'] == 'ideal'

        # Verify payment record was stored with source_id
        mock_put.assert_called_once()
        put_item = mock_put.call_args.kwargs['Item']
        assert put_item['order_id'] == 'ord-123'
        assert put_item['source_id'] == 'evt-abc-123'
        assert put_item['member_id'] == 'member-001'
        assert put_item['amount'] == Decimal('350')
        assert put_item['status'] == 'pending'
        assert put_item['provider'] == 'mollie'
        assert put_item['method'] == 'ideal'
        assert put_item['mollie_payment_id'] == 'tr_abc123'

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    @patch('handler.create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_partial_payment_calculates_outstanding(
        self, mock_put, mock_mollie, mock_get_order, mock_resolve
    ):
        """When order is partially paid, only outstanding balance is charged."""
        mock_resolve.return_value = (make_member(), None)
        order = make_order(total_paid=Decimal('200.00'))
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_partial',
            'checkout_url': 'https://www.mollie.com/checkout/partial',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['amount'] == 150.00  # 350 total - 200 paid

        # Verify Mollie was called with outstanding amount
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '150.00'

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    @patch('handler.create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_webshop_order_payment(self, mock_put, mock_mollie, mock_get_order, mock_resolve):
        """Webshop orders use 'webshop' as source_id in payment record."""
        mock_resolve.return_value = (make_member(), None)
        order = make_order(source_id='webshop')
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_webshop',
            'checkout_url': 'https://www.mollie.com/checkout/webshop',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201

        # Verify payment record has source_id = 'webshop'
        put_item = mock_put.call_args.kwargs['Item']
        assert put_item['source_id'] == 'webshop'


class TestNoOutstandingBalance:
    """Test when order has no outstanding balance."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_fully_paid_returns_400(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)
        order = make_order(
            items=[{'product_id': 'p1', 'line_total': Decimal('100.00')}],
            total_paid=Decimal('100.00'),
        )
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_overpaid_returns_400(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)
        order = make_order(
            items=[{'product_id': 'p1', 'line_total': Decimal('100.00')}],
            total_paid=Decimal('150.00'),
        )
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    def test_zero_items_returns_400(self, mock_get_order, mock_resolve):
        mock_resolve.return_value = (make_member(), None)
        order = make_order(items=[])
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()


class TestUnsupportedMethod:
    """Test unsupported payment method."""

    def test_unsupported_method_returns_400(self):
        token = create_jwt_token()
        event = make_event(
            token=token,
            path_params={'id': 'ord-123'},
            body={'method': 'paypal'},
        )
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'unsupported' in body['error'].lower()


class TestMollieApiError:
    """Test Mollie API error handling."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    @patch('handler.create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_mollie_error_returns_502_no_payment_stored(
        self, mock_put, mock_mollie, mock_get_order, mock_resolve
    ):
        """Mollie error → 502, payment record NOT created."""
        mock_resolve.return_value = (make_member(), None)
        mock_get_order.return_value = make_order()
        mock_mollie.side_effect = MollieError("Connection timed out")

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert 'payment provider' in body['error'].lower()
        assert body['details']['provider'] == 'mollie'

        # Payment record must NOT be stored
        mock_put.assert_not_called()


class TestPaymentRecordStorage:
    """Test that payment records are correctly stored in the Payments table."""

    @patch.object(app, '_resolve_member_id')
    @patch.object(app, '_get_order')
    @patch('handler.create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_stores_payment_with_all_required_fields(
        self, mock_put, mock_mollie, mock_get_order, mock_resolve
    ):
        mock_resolve.return_value = (make_member(member_id='member-001'), None)
        mock_get_order.return_value = make_order(source_id='evt-xyz')
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_store_test',
            'checkout_url': 'https://www.mollie.com/checkout/store',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201

        # Verify all required fields in payment record
        mock_put.assert_called_once()
        record = mock_put.call_args.kwargs['Item']
        assert 'payment_id' in record
        assert record['order_id'] == 'ord-123'
        assert record['source_id'] == 'evt-xyz'
        assert record['member_id'] == 'member-001'
        assert record['amount'] == Decimal('350')
        assert record['status'] == 'pending'
        assert record['mollie_payment_id'] == 'tr_store_test'
        assert 'created_at' in record
