"""
Unit Tests for submit_order Lambda Handler.

Tests the unified submit_order handler:
- Authentication and authorization
- Rejection when order is not in draft status
- Rejection when order has no items
- Validation of product_id existence
- Validation of variant_id → parent_id linkage
- Validation of item_fields_data against order_item_fields
- Successful submission sets status to "submitted" and submitted_at

Requirements: 7.1, 7.10, 10.8, 10.9
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
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('PRODUCTEN_TABLE_NAME', 'Producten')

import handler.submit_order.app as app
from handler.submit_order.app import lambda_handler


def create_jwt_token(email="user@example.nl", groups=None):
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


def make_event(token=None, path_params=None, method='POST', body=None):
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


# Sample data fixtures
SAMPLE_PRODUCT = {
    'product_id': 'prod-001',
    'name': 'Club T-shirt',
    'price': Decimal('25.00'),
    'is_parent': True,
    'active': True,
    'variant_schema': {'Maat': ['S', 'M', 'L', 'XL']},
}

SAMPLE_PRODUCT_WITH_FIELDS = {
    'product_id': 'prod-002',
    'name': 'Meeting Ticket',
    'price': Decimal('50.00'),
    'is_parent': True,
    'active': True,
    'order_item_fields': [
        {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
        {'id': 'role', 'label': 'Functie', 'type': 'text', 'required': True},
    ],
}

SAMPLE_VARIANT = {
    'product_id': 'var-001',
    'parent_id': 'prod-001',
    'is_parent': False,
    'variant_attributes': {'Maat': 'L'},
    'stock': 10,
    'allow_oversell': False,
}

SAMPLE_VARIANT_WRONG_PARENT = {
    'product_id': 'var-bad',
    'parent_id': 'prod-other',
    'is_parent': False,
    'variant_attributes': {'Maat': 'M'},
}

SAMPLE_DRAFT_ORDER = {
    'order_id': 'ord-100',
    'status': 'draft',
    'member_id': 'mem-1',
    'user_email': 'user@example.nl',
    'items': [
        {
            'product_id': 'prod-001',
            'variant_id': 'var-001',
            'quantity': 1,
            'unit_price': Decimal('25.00'),
            'line_total': Decimal('25.00'),
        },
    ],
    'total_amount': Decimal('25.00'),
    'total_paid': Decimal('0'),
    'version': 1,
    'created_at': '2025-01-01T00:00:00+00:00',
    'updated_at': '2025-01-01T00:00:00+00:00',
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
        event = make_event(path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_no_member_access_returns_403(self):
        """User without hdcnLeden/Regio_Pressmeet/Regio_All should be rejected."""
        token = create_jwt_token(groups=["some_other_group"])
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403


class TestMissingOrderId:
    """Test missing order ID in path."""

    def test_missing_order_id_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params={})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_null_path_params_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params=None)
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestOrderNotFound:
    """Test order not found."""

    @patch.object(app, '_get_order', return_value=None)
    def test_order_not_found_returns_404(self, mock_order):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'nonexistent'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestOrderStatus:
    """Test that only draft orders can be submitted."""

    @patch.object(app, '_get_order')
    def test_submitted_order_rejected(self, mock_order):
        mock_order.return_value = {**SAMPLE_DRAFT_ORDER, 'status': 'submitted'}
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'submitted' in body['error'].lower()

    @patch.object(app, '_get_order')
    def test_locked_order_rejected(self, mock_order):
        mock_order.return_value = {**SAMPLE_DRAFT_ORDER, 'status': 'locked'}
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'locked' in body['error'].lower()

    @patch.object(app, '_get_order')
    def test_paid_order_rejected(self, mock_order):
        mock_order.return_value = {**SAMPLE_DRAFT_ORDER, 'status': 'paid'}
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'paid' in body['error'].lower()

    @patch.object(app, '_get_order')
    def test_empty_items_rejected(self, mock_order):
        mock_order.return_value = {**SAMPLE_DRAFT_ORDER, 'items': []}
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no items' in body['error'].lower()


class TestProductValidation:
    """Test product_id validation."""

    @patch.object(app, '_get_order', return_value=SAMPLE_DRAFT_ORDER)
    @patch.object(app, '_get_product', return_value=None)
    def test_product_not_found_returns_error(self, mock_product, mock_order):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'errors' in body
        assert body['errors'][0]['field'] == 'product_id'
        assert 'not found' in body['errors'][0]['message'].lower()


class TestVariantValidation:
    """Test variant_id → parent_id linkage validation."""

    @patch.object(app, '_get_order', return_value=SAMPLE_DRAFT_ORDER)
    @patch.object(app, '_get_product')
    def test_variant_not_found_returns_error(self, mock_product, mock_order):
        """If variant_id doesn't resolve to a record, return error."""
        def side_effect(pid):
            if pid == 'prod-001':
                return SAMPLE_PRODUCT
            return None  # variant not found

        mock_product.side_effect = side_effect
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['errors'][0]['field'] == 'variant_id'
        assert 'not found' in body['errors'][0]['message'].lower()

    @patch.object(app, '_get_order', return_value=SAMPLE_DRAFT_ORDER)
    @patch.object(app, '_get_product')
    def test_variant_parent_mismatch_returns_error(self, mock_product, mock_order):
        """If variant.parent_id != item.product_id, return error."""
        def side_effect(pid):
            if pid == 'prod-001':
                return SAMPLE_PRODUCT
            if pid == 'var-001':
                return SAMPLE_VARIANT_WRONG_PARENT
            return None

        mock_product.side_effect = side_effect
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['errors'][0]['field'] == 'variant_id'
        assert 'does not belong' in body['errors'][0]['message'].lower()


class TestItemFieldsValidation:
    """Test item_fields_data validation at submit time."""

    @patch.object(app, '_get_order')
    @patch.object(app, '_get_product')
    def test_missing_required_fields_returns_error(self, mock_product, mock_order):
        """If product requires item_fields and they're missing, return error."""
        order_with_fields = {
            **SAMPLE_DRAFT_ORDER,
            'items': [{
                'product_id': 'prod-002',
                'variant_id': None,
                'quantity': 1,
                'unit_price': Decimal('50.00'),
                'line_total': Decimal('50.00'),
                'item_fields_data': None,  # Missing!
            }],
        }
        mock_order.return_value = order_with_fields

        def side_effect(pid):
            if pid == 'prod-002':
                return SAMPLE_PRODUCT_WITH_FIELDS
            return None

        mock_product.side_effect = side_effect
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert len(body['errors']) > 0
        assert body['errors'][0]['field'] == 'item_fields_data'


class TestSuccessfulSubmission:
    """Test successful order submission."""

    @patch.object(app, '_get_order', return_value=SAMPLE_DRAFT_ORDER)
    @patch.object(app, '_get_product')
    @patch.object(app.orders_table, 'update_item')
    @patch('handler.submit_order.app.generate_order_number', return_value='H-250115-001')
    def test_successful_submit_returns_200(self, mock_gen, mock_update, mock_product, mock_order):
        def side_effect(pid):
            if pid == 'prod-001':
                return SAMPLE_PRODUCT
            if pid == 'var-001':
                return SAMPLE_VARIANT
            return None

        mock_product.side_effect = side_effect
        mock_update.return_value = {
            'Attributes': {**SAMPLE_DRAFT_ORDER, 'status': 'submitted'}
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert 'submitted_at' in body
        assert body['order_number'] == 'H-250115-001'

    @patch.object(app, '_get_order', return_value=SAMPLE_DRAFT_ORDER)
    @patch.object(app, '_get_product')
    @patch.object(app.orders_table, 'update_item')
    @patch('handler.submit_order.app.generate_order_number', return_value='H-250115-002')
    def test_submit_records_status_history(self, mock_gen, mock_update, mock_product, mock_order):
        def side_effect(pid):
            if pid == 'prod-001':
                return SAMPLE_PRODUCT
            if pid == 'var-001':
                return SAMPLE_VARIANT
            return None

        mock_product.side_effect = side_effect
        mock_update.return_value = {
            'Attributes': {**SAMPLE_DRAFT_ORDER, 'status': 'submitted'}
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        lambda_handler(event, None)

        # Verify the update_item call includes status_history and order_number
        call_kwargs = mock_update.call_args[1]
        expr_values = call_kwargs['ExpressionAttributeValues']
        history_entry = expr_values[':history_entry'][0]
        assert history_entry['from'] == 'draft'
        assert history_entry['to'] == 'submitted'
        assert history_entry['by'] == 'user@example.nl'
        assert expr_values[':order_number'] == 'H-250115-002'

    @patch.object(app, '_get_order')
    @patch.object(app, '_get_product')
    @patch.object(app.orders_table, 'update_item')
    @patch('handler.submit_order.app.generate_order_number', return_value='H-250115-003')
    def test_order_without_variant_id_submits_ok(self, mock_gen, mock_update, mock_product, mock_order):
        """An order item without a variant_id (no variant selection) submits fine."""
        order_no_variant = {
            **SAMPLE_DRAFT_ORDER,
            'items': [{
                'product_id': 'prod-001',
                'variant_id': None,
                'quantity': 1,
                'unit_price': Decimal('25.00'),
                'line_total': Decimal('25.00'),
            }],
        }
        mock_order.return_value = order_no_variant

        def side_effect(pid):
            if pid == 'prod-001':
                return SAMPLE_PRODUCT
            return None

        mock_product.side_effect = side_effect
        mock_update.return_value = {
            'Attributes': {**order_no_variant, 'status': 'submitted'}
        }

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestMultipleErrors:
    """Test that multiple validation errors are collected and returned."""

    @patch.object(app, '_get_order')
    @patch.object(app, '_get_product', return_value=None)
    def test_multiple_items_multiple_errors(self, mock_product, mock_order):
        """All item errors are collected, not just the first one."""
        multi_item_order = {
            **SAMPLE_DRAFT_ORDER,
            'items': [
                {'product_id': 'bad-1', 'variant_id': None, 'quantity': 1,
                 'unit_price': Decimal('10'), 'line_total': Decimal('10')},
                {'product_id': 'bad-2', 'variant_id': None, 'quantity': 1,
                 'unit_price': Decimal('20'), 'line_total': Decimal('20')},
            ],
        }
        mock_order.return_value = multi_item_order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-100'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert len(body['errors']) == 2
        assert body['error_count'] == 2
