"""
Unit Tests for presmeet_create_payment Lambda Handler.

Tests the presmeet_create_payment handler:
- Authentication and authorization flows
- Delegate access validation (primary/secondary)
- Order not found → 404
- No outstanding balance → 400
- Successful Mollie payment creation → stores record, returns checkout_url
- Mollie API error → 502 without creating payment record
- Supported payment methods (iDEAL, banktransfer)
- Unsupported method → 400

Requirements: 7
"""

import json
import pytest
import base64
from unittest.mock import patch, MagicMock, call
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
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('PAYMENTS_TABLE_NAME', 'Payments')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')
os.environ.setdefault('MOLLIE_API_KEY', 'test_api_key_xxx')
os.environ.setdefault('PAYMENT_REDIRECT_URL', 'https://portal.h-dcn.nl/presmeet')
os.environ.setdefault('MOLLIE_WEBHOOK_URL', 'https://api.h-dcn.nl/mollie-webhook')

import handler.presmeet_create_payment.app as app
from handler.presmeet_create_payment.app import lambda_handler
from shared.mollie_client import MollieError


def create_jwt_token(email="delegate@club.nl", groups=None):
    """Helper to create JWT tokens for testing."""
    if groups is None:
        groups = ["hdcnLeden", "Regio_Pressmeet"]

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
    club_id='club-123',
    total_amount=Decimal('450.00'),
    total_paid=Decimal('0.00'),
    status='submitted',
    primary_delegate='delegate@club.nl',
    secondary_delegate=None,
):
    """Helper to create a mock order record."""
    return {
        'order_id': order_id,
        'club_id': club_id,
        'event_id': 'evt-1',
        'event_type': 'presmeet',
        'channel': 'presmeet',
        'status': status,
        'payment_status': 'unpaid',
        'total_amount': total_amount,
        'total_paid': total_paid,
        'items': [
            {
                'product_id': 'prod-meeting',
                'variant_id': None,
                'item_fields_data': {'name': 'Jan', 'role': 'President'},
                'unit_price': Decimal('150.00'),
                'line_total': Decimal('150.00'),
            }
        ],
        'delegates': {
            'primary': primary_delegate,
            'secondary': secondary_delegate,
        },
        'version': 2,
        'status_history': [],
        'created_at': '2027-01-10T08:00:00+00:00',
        'updated_at': '2027-01-15T10:30:00+00:00',
        'created_by': primary_delegate,
    }


class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_auth_header_returns_401(self):
        event = make_event(path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_no_presmeet_access_returns_403(self):
        """User without Regio_Pressmeet or Regio_All should be rejected."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'PresMeet access required' in body['error']


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

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=None)
    def test_order_not_found_returns_404(self, mock_get_order, mock_club):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'nonexistent'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestNoOutstandingBalance:
    """Test when order has no outstanding balance."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_fully_paid_returns_400(self, mock_get_order, mock_club):
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('450.00'))
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_overpaid_returns_400(self, mock_get_order, mock_club):
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('500.00'))
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_zero_total_returns_400(self, mock_get_order, mock_club):
        order = make_order(total_amount=Decimal('0.00'), total_paid=Decimal('0.00'))
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'outstanding' in body['error'].lower()


class TestSuccessfulPayment:
    """Test successful payment creation."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_creates_payment_and_returns_checkout_url(
        self, mock_put, mock_mollie, mock_get_order, mock_club
    ):
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('0.00'))
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
        assert body['amount'] == 450.00
        assert body['method'] == 'ideal'
        assert 'payment_id' in body

        # Verify Mollie was called with correct amount
        mock_mollie.assert_called_once()
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '450.00'
        assert call_kwargs.kwargs['method'] == 'ideal'

        # Verify payment record was stored
        mock_put.assert_called_once()
        put_item = mock_put.call_args.kwargs['Item']
        assert put_item['order_id'] == 'ord-123'
        assert put_item['club_id'] == 'club-123'
        assert put_item['amount'] == Decimal('450.00')
        assert put_item['status'] == 'pending'
        assert put_item['provider'] == 'mollie'
        assert put_item['method'] == 'ideal'
        assert put_item['mollie_payment_id'] == 'tr_abc123'

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_partial_payment_calculates_outstanding(
        self, mock_put, mock_mollie, mock_get_order, mock_club
    ):
        """When order is partially paid, only outstanding balance is charged."""
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('200.00'))
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
        assert body['amount'] == 250.00

        # Verify Mollie was called with outstanding amount
        mock_mollie.assert_called_once()
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '250.00'

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_banktransfer_method(self, mock_put, mock_mollie, mock_get_order, mock_club):
        """Bank transfer method is supported."""
        order = make_order(total_amount=Decimal('100.00'), total_paid=Decimal('0.00'))
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_bank',
            'checkout_url': 'https://www.mollie.com/checkout/bank',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(
            token=token,
            path_params={'id': 'ord-123'},
            body={'method': 'banktransfer'},
        )
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['method'] == 'banktransfer'

        # Verify payment record stored with banktransfer method
        put_item = mock_put.call_args.kwargs['Item']
        assert put_item['method'] == 'banktransfer'


class TestUnsupportedMethod:
    """Test unsupported payment method."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_unsupported_method_returns_400(self, mock_get_order, mock_club):
        order = make_order()
        mock_get_order.return_value = order

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

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_mollie_error_returns_502_no_payment_stored(
        self, mock_put, mock_mollie, mock_get_order, mock_club
    ):
        """Mollie error → 502, payment record NOT created."""
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('0.00'))
        mock_get_order.return_value = order
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

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_mollie_422_returns_502(self, mock_put, mock_mollie, mock_get_order, mock_club):
        """Mollie 422 error → 502, no payment record."""
        order = make_order(total_amount=Decimal('450.00'), total_paid=Decimal('0.00'))
        mock_get_order.return_value = order
        mock_mollie.side_effect = MollieError("Unprocessable Entity: Invalid amount", status_code=422)

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 502
        mock_put.assert_not_called()


class TestDelegateAccess:
    """Test delegate-based access control."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_secondary_delegate_can_pay(self, mock_put, mock_mollie, mock_get_order, mock_club):
        order = make_order(
            total_amount=Decimal('100.00'),
            total_paid=Decimal('0.00'),
            primary_delegate='jan@club.nl',
            secondary_delegate='piet@club.nl',
        )
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_sec',
            'checkout_url': 'https://www.mollie.com/checkout/sec',
            'status': 'open',
        }

        token = create_jwt_token(email="piet@club.nl")
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_non_delegate_gets_403(self, mock_get_order, mock_club):
        order = make_order(
            primary_delegate='jan@club.nl',
            secondary_delegate='piet@club.nl',
        )
        mock_get_order.return_value = order

        token = create_jwt_token(email="intruder@club.nl")
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'delegate' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-999')
    @patch.object(app, '_get_order')
    def test_wrong_club_gets_403(self, mock_get_order, mock_club):
        """User from different club cannot pay."""
        order = make_order(club_id='club-123')
        mock_get_order.return_value = order

        token = create_jwt_token(email="delegate@other.nl")
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'different club' in body['error'].lower()


class TestAdminAccess:
    """Test admin access patterns."""

    @patch.object(app, 'is_presmeet_admin', return_value=True)
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_admin_can_initiate_payment_for_any_club(
        self, mock_put, mock_mollie, mock_get_order, mock_admin
    ):
        order = make_order(
            club_id='club-456',
            total_amount=Decimal('300.00'),
            total_paid=Decimal('0.00'),
            primary_delegate='someone@club.nl',
        )
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_admin',
            'checkout_url': 'https://www.mollie.com/checkout/admin',
            'status': 'open',
        }

        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['checkout_url'] == 'https://www.mollie.com/checkout/admin'


class TestMissingClubId:
    """Test user without club_id assignment."""

    @patch.object(app, 'get_club_id', return_value=None)
    @patch.object(app, '_get_order')
    def test_no_club_id_returns_403(self, mock_get_order, mock_club):
        order = make_order()
        mock_get_order.return_value = order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'club' in body['error'].lower()


class TestAmountFormatting:
    """Test Mollie amount string formatting (2 decimal places)."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_amount_formatted_with_two_decimals(
        self, mock_put, mock_mollie, mock_get_order, mock_club
    ):
        """Amount like 123.5 should be sent as '123.50'."""
        order = make_order(total_amount=Decimal('123.50'), total_paid=Decimal('0.00'))
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_fmt',
            'checkout_url': 'https://www.mollie.com/checkout/fmt',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '123.50'

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch('handler.presmeet_create_payment.app.create_payment')
    @patch.object(app.payments_table, 'put_item')
    def test_whole_number_amount_has_two_decimals(
        self, mock_put, mock_mollie, mock_get_order, mock_club
    ):
        """Amount like 200 should be sent as '200.00'."""
        order = make_order(total_amount=Decimal('200'), total_paid=Decimal('0'))
        mock_get_order.return_value = order
        mock_mollie.return_value = {
            'mollie_payment_id': 'tr_whole',
            'checkout_url': 'https://www.mollie.com/checkout/whole',
            'status': 'open',
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-123'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        call_kwargs = mock_mollie.call_args
        assert call_kwargs.kwargs['amount'] == '200.00'
