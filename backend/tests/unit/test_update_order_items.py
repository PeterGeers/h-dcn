"""
Unit tests for update_order_items handler.

Tests the unified update_order_items handler that:
- Updates items on a draft order with optimistic locking
- Rejects stale versions with 409 Conflict
- Fetches prices from Producten table
- Validates variant parent_id matches product_id
- Accepts incomplete item data (draft mode)
- Increments version on success

Requirements: 7.6, 7.7, 7.8, 7.9, 7.10, 10.9, 12.21
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_order_items'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB tables."""
    with patch('app.orders_table') as mock_orders, \
         patch('app.producten_table') as mock_producten:
        yield {
            'orders': mock_orders,
            'producten': mock_producten,
        }


@pytest.fixture
def mock_auth():
    """Mock auth layer functions."""
    with patch('app.extract_user_credentials') as mock_extract, \
         patch('app.validate_permissions_with_regions') as mock_validate, \
         patch('app.log_successful_access') as mock_log:
        mock_extract.return_value = ('user@test.nl', ['hdcnLeden'], None)
        mock_validate.return_value = (False, None, None)
        yield {
            'extract': mock_extract,
            'validate': mock_validate,
            'log': mock_log,
        }


def _make_event(order_id, body):
    """Create a minimal API Gateway event for PUT /orders/{id}/items."""
    return {
        "httpMethod": "PUT",
        "path": f"/orders/{order_id}/items",
        "pathParameters": {"id": order_id},
        "headers": {"Authorization": "Bearer test-token"},
        "queryStringParameters": None,
        "body": json.dumps(body),
        "requestContext": {"apiId": "test", "stage": "Prod"},
    }


def _draft_order(order_id='order-1', version=1, user_email='user@test.nl'):
    """Create a mock draft order record."""
    return {
        'order_id': order_id,
        'status': 'draft',
        'version': version,
        'user_email': user_email,
        'items': [],
        'total_amount': Decimal('0'),
    }


class TestHandlerBasics:
    """Basic handler tests."""

    def test_handler_exists(self):
        """Verify lambda_handler is callable."""
        from app import lambda_handler
        assert callable(lambda_handler)

    def test_handles_options_request(self):
        """Handler responds to OPTIONS preflight."""
        from app import lambda_handler
        with patch('app.handle_options_request', return_value={'statusCode': 200}):
            event = {"httpMethod": "OPTIONS"}
            response = lambda_handler(event, None)
            assert response["statusCode"] == 200

    def test_rejects_missing_version(self, mock_dynamodb, mock_auth):
        """Handler rejects requests without version field."""
        from app import lambda_handler

        event = _make_event('order-1', {'items': []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'version' in body['error'].lower()

    def test_rejects_missing_items(self, mock_dynamodb, mock_auth):
        """Handler rejects requests without items field."""
        from app import lambda_handler

        event = _make_event('order-1', {'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'items' in body['error'].lower()

    def test_rejects_invalid_json(self, mock_dynamodb, mock_auth):
        """Handler rejects invalid JSON body."""
        from app import lambda_handler

        event = _make_event('order-1', {})
        event['body'] = 'not-json{'
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestOptimisticLocking:
    """Tests for optimistic locking (Requirement 7.9)."""

    def test_rejects_stale_version(self, mock_dynamodb, mock_auth):
        """409 Conflict when provided version doesn't match stored version."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=3)
        }

        event = _make_event('order-1', {
            'version': 2,  # stale version
            'items': [],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body.get('current_version') == 3

    def test_accepts_correct_version(self, mock_dynamodb, mock_auth):
        """Succeeds when provided version matches stored version."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=2)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 2,
            'items': [],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['version'] == 3  # incremented

    def test_handles_conditional_check_failure(self, mock_dynamodb, mock_auth):
        """409 Conflict when DynamoDB ConditionExpression fails (race condition)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Condition not met'}},
            'UpdateItem'
        )

        event = _make_event('order-1', {
            'version': 1,
            'items': [],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409


class TestPriceFetching:
    """Tests for price fetching from Producten table (Requirements 7.6, 7.7, 7.8)."""

    def test_fetches_price_from_product(self, mock_dynamodb, mock_auth):
        """Unit price is read from the Producten table."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('25.00'), 'name': 'T-shirt'}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 2}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_amount'] == 50.0

    def test_rejects_null_price(self, mock_dynamodb, mock_auth):
        """Rejects product with null price."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': None, 'name': 'Bad product'}
        }

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no configured price' in body['error'].lower()

    def test_rejects_zero_price(self, mock_dynamodb, mock_auth):
        """Rejects product with zero price."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': 0, 'name': 'Free product'}
        }

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_rejects_empty_price(self, mock_dynamodb, mock_auth):
        """Rejects product with empty string price."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': '', 'name': 'No price'}
        }

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_product_not_found(self, mock_dynamodb, mock_auth):
        """Returns 404 when product doesn't exist."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {}  # No Item

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'nonexistent', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404


class TestVariantValidation:
    """Tests for variant parent_id validation (Requirement 10.9)."""

    def test_validates_variant_parent_match(self, mock_dynamodb, mock_auth):
        """Succeeds when variant's parent_id matches product_id."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }

        def get_item_side_effect(Key):
            pid = Key['product_id']
            if pid == 'prod-1':
                return {'Item': {'product_id': 'prod-1', 'price': Decimal('10'), 'is_parent': True}}
            elif pid == 'var-1':
                return {'Item': {'product_id': 'var-1', 'parent_id': 'prod-1', 'is_parent': False, 'variant_attributes': {'Maat': 'L'}}}
            return {}

        mock_dynamodb['producten'].get_item.side_effect = get_item_side_effect
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'variant_id': 'var-1', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_rejects_variant_parent_mismatch(self, mock_dynamodb, mock_auth):
        """Returns 400 when variant's parent_id doesn't match product_id."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }

        def get_item_side_effect(Key):
            pid = Key['product_id']
            if pid == 'prod-1':
                return {'Item': {'product_id': 'prod-1', 'price': Decimal('10'), 'is_parent': True}}
            elif pid == 'var-1':
                return {'Item': {'product_id': 'var-1', 'parent_id': 'other-product', 'is_parent': False}}
            return {}

        mock_dynamodb['producten'].get_item.side_effect = get_item_side_effect

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'variant_id': 'var-1', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'does not belong' in body['error'].lower()

    def test_rejects_nonexistent_variant(self, mock_dynamodb, mock_auth):
        """Returns 404 when variant doesn't exist."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }

        def get_item_side_effect(Key):
            pid = Key['product_id']
            if pid == 'prod-1':
                return {'Item': {'product_id': 'prod-1', 'price': Decimal('10'), 'is_parent': True}}
            return {}  # variant not found

        mock_dynamodb['producten'].get_item.side_effect = get_item_side_effect

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'variant_id': 'nonexistent', 'quantity': 1}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404


class TestDraftAcceptsIncomplete:
    """Tests for accepting incomplete data (Requirement 7.10)."""

    def test_accepts_items_without_product_id(self, mock_dynamodb, mock_auth):
        """Draft orders accept items without product_id."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'quantity': 1}],  # no product_id
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_accepts_empty_items_list(self, mock_dynamodb, mock_auth):
        """Draft orders accept empty items list (clearing cart)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total_amount'] == 0.0

    def test_accepts_partial_item_fields_data(self, mock_dynamodb, mock_auth):
        """Draft orders accept partial item_fields_data."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('15.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{
                'product_id': 'prod-1',
                'quantity': 1,
                'item_fields_data': [{'name': 'Jan'}],  # partial data
            }],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestOrderAccess:
    """Tests for order access control."""

    def test_rejects_non_draft_order(self, mock_dynamodb, mock_auth):
        """Cannot update items on non-draft orders."""
        from app import lambda_handler

        order = _draft_order(version=1)
        order['status'] = 'submitted'
        mock_dynamodb['orders'].get_item.return_value = {'Item': order}

        event = _make_event('order-1', {'version': 1, 'items': []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'draft' in body['error'].lower()

    def test_rejects_other_users_order(self, mock_dynamodb, mock_auth):
        """Cannot update another user's order."""
        from app import lambda_handler

        order = _draft_order(user_email='other@test.nl')
        mock_dynamodb['orders'].get_item.return_value = {'Item': order}

        event = _make_event('order-1', {'version': 1, 'items': []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403

    def test_order_not_found(self, mock_dynamodb, mock_auth):
        """Returns 404 when order doesn't exist."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {}  # No Item

        event = _make_event('nonexistent', {'version': 1, 'items': []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
