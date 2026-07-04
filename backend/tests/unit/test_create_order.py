"""
Unit tests for create_order handler (unified draft order flow).

Tests the unified create_order handler that:
- Creates draft orders for webshop (event_id=null) and event orders (event_id set)
- For event orders: returns existing order for same club_id + event_id
- Rejects items with null/empty/zero price
- Sets version=1, status="draft", payment_status="unpaid"

Requirements: 7.1, 7.4, 7.5, 7.6, 7.7, 7.8, 7.13, 7.16, 10.8
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'create_order'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB tables."""
    with patch('handler.create_order.app.orders_table') as mock_orders, \
         patch('handler.create_order.app.producten_table') as mock_producten, \
         patch('handler.create_order.app.members_table') as mock_members:
        yield {
            'orders': mock_orders,
            'producten': mock_producten,
            'members': mock_members,
        }


@pytest.fixture
def mock_auth():
    """Mock auth layer functions."""
    with patch('handler.create_order.app.extract_user_credentials') as mock_extract, \
         patch('handler.create_order.app.validate_permissions_with_regions') as mock_validate, \
         patch('handler.create_order.app.log_successful_access') as mock_log, \
         patch('handler.create_order.app.get_registry_row_id') as mock_registry_row:
        mock_extract.return_value = ('user@test.nl', ['hdcnLeden'], None)
        mock_validate.return_value = (False, None, None)
        mock_registry_row.return_value = 'club-123'
        yield {
            'extract': mock_extract,
            'validate': mock_validate,
            'log': mock_log,
            'get_registry_row_id': mock_registry_row,
        }


def _make_event(body):
    """Create a minimal API Gateway event with the given body."""
    return {
        "httpMethod": "POST",
        "path": "/orders",
        "headers": {"Authorization": "Bearer test-token"},
        "queryStringParameters": None,
        "body": json.dumps(body),
        "requestContext": {"apiId": "test", "stage": "Prod"},
    }


class TestHandlerBasics:
    """Basic handler tests."""

    def test_handler_exists(self):
        """Verify lambda_handler is callable."""
        from handler.create_order.app import lambda_handler
        assert callable(lambda_handler)

    def test_returns_error_without_auth(self):
        """Handler rejects unauthenticated requests."""
        from handler.create_order.app import lambda_handler
        event = _make_event({})
        event['headers'] = {}
        response = lambda_handler(event, None)
        assert response["statusCode"] in [401, 403, 500]

    def test_handles_options_request(self):
        """Handler responds to OPTIONS preflight."""
        from handler.create_order.app import lambda_handler
        with patch('handler.create_order.app.handle_options_request', return_value={'statusCode': 200}):
            event = {"httpMethod": "OPTIONS"}
            response = lambda_handler(event, None)
            assert response["statusCode"] == 200


class TestWebshopOrderCreation:
    """Tests for webshop orders (event_id=null)."""

    def test_creates_draft_order_for_webshop(self, mock_dynamodb, mock_auth):
        """Webshop order creates a new draft with correct fields."""
        from handler.create_order.app import lambda_handler

        # Mock member lookup
        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }

        # Mock product fetch
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('25.00'), 'name': 'T-shirt'}
        }

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'variant_id': 'var-1', 'quantity': 2}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        order = body.get('data', body)

        assert order['status'] == 'draft'
        assert order['payment_status'] == 'unpaid'
        assert order['version'] == 1
        assert order.get('event_id') is None
        assert order['member_id'] == 'member-1'
        assert order['total_paid'] == 0

    def test_webshop_always_creates_new_order(self, mock_dynamodb, mock_auth):
        """Webshop orders never check for existing — always create new."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('10.00')}
        }

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        # Verify no scan was done on orders table for deduplication
        mock_dynamodb['orders'].scan.assert_not_called()

    def test_creates_empty_draft_without_items(self, mock_dynamodb, mock_auth):
        """Webshop draft can be created with no items."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }

        event = _make_event({'event_id': None})

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        order = body.get('data', body)
        assert order['items'] == []
        assert order['total_amount'] == 0


class TestEventOrderCreation:
    """Tests for event orders (event_id set)."""

    def test_creates_new_event_order(self, mock_dynamodb, mock_auth):
        """Event order creates new draft when no existing order found."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        # No existing order found
        mock_dynamodb['orders'].scan.return_value = {'Items': []}
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('50.00')}
        }

        event = _make_event({
            'event_id': 'event-abc',
            'club_id': 'club-123',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        order = body.get('data', body)
        assert order['event_id'] == 'event-abc'
        assert order['status'] == 'draft'
        assert order['version'] == 1

    def test_returns_existing_event_order(self, mock_dynamodb, mock_auth):
        """Event order returns existing order for same registry_row_id + event_id."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }

        existing_order = {
            'order_id': 'existing-order-id',
            'event_id': 'event-abc',
            'club_id': 'club-123',
            'status': 'draft',
            'payment_status': 'unpaid',
            'items': [],
            'total_amount': Decimal('0'),
            'total_paid': Decimal('0'),
            'version': 3,
            'created_at': '2024-01-01T00:00:00+00:00',
            'updated_at': '2024-01-01T00:00:00+00:00',
        }
        mock_dynamodb['orders'].scan.return_value = {'Items': [existing_order]}

        event = _make_event({
            'event_id': 'event-abc',
            'club_id': 'club-123',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        order = body.get('data', body)
        assert order['order_id'] == 'existing-order-id'
        assert order['version'] == 3

    def test_does_not_return_cancelled_order(self, mock_dynamodb, mock_auth):
        """Cancelled orders are not returned as existing."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        # Scan returns empty because filter excludes cancelled
        mock_dynamodb['orders'].scan.return_value = {'Items': []}
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('25.00')}
        }

        event = _make_event({
            'event_id': 'event-abc',
            'club_id': 'club-123',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        # Creates new since no non-cancelled order found
        assert response['statusCode'] == 201

    def test_rejects_event_order_without_club_id(self, mock_dynamodb, mock_auth):
        """Event order returns 400 when registry_row_id is null/empty (Req 18.3)."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        # get_registry_row_id returns None (no registry_row_id resolvable)
        mock_auth['get_registry_row_id'].return_value = None

        event = _make_event({
            'event_id': 'event-abc',
            'club_id': None,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

        body = json.loads(response['body'])
        assert 'club_id' in body.get('error', body.get('message', ''))

    def test_rejects_event_order_with_empty_club_id(self, mock_dynamodb, mock_auth):
        """Event order returns 400 when registry_row_id is empty string (Req 18.3)."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        # get_registry_row_id also returns empty string
        mock_auth['get_registry_row_id'].return_value = ''

        event = _make_event({
            'event_id': 'event-abc',
            'club_id': '',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

        body = json.loads(response['body'])
        assert 'club_id' in body.get('error', body.get('message', ''))


class TestPriceValidation:
    """Tests for product price fetching and validation."""

    def test_rejects_product_with_zero_price(self, mock_dynamodb, mock_auth):
        """Items with zero price are rejected."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('0')}
        }

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'price' in body.get('message', '').lower() or 'price' in json.dumps(body).lower()

    def test_rejects_product_with_null_price(self, mock_dynamodb, mock_auth):
        """Items with null price are rejected."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': None}
        }

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_rejects_product_not_found(self, mock_dynamodb, mock_auth):
        """Items referencing nonexistent products are rejected."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }
        mock_dynamodb['producten'].get_item.return_value = {}

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'nonexistent', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 404

    def test_uses_variant_price_override(self, mock_dynamodb, mock_auth):
        """Variant price override is used when available."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }

        # First call for product, second for variant
        mock_dynamodb['producten'].get_item.side_effect = [
            {'Item': {'product_id': 'prod-1', 'price': Decimal('25.00')}},
            {'Item': {'product_id': 'var-1', 'parent_id': 'prod-1', 'price': Decimal('30.00')}},
        ]

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'variant_id': 'var-1', 'quantity': 1}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        order = body.get('data', body)
        # Price should come from variant (30.00)
        assert order['items'][0]['unit_price'] == 30
        assert order['total_amount'] == 30

    def test_falls_back_to_parent_price(self, mock_dynamodb, mock_auth):
        """Falls back to parent product price when variant has no price."""
        from handler.create_order.app import lambda_handler

        mock_dynamodb['members'].scan.return_value = {
            'Items': [{'member_id': 'member-1'}]
        }

        # First call for product, second for variant (no price override)
        mock_dynamodb['producten'].get_item.side_effect = [
            {'Item': {'product_id': 'prod-1', 'price': Decimal('25.00')}},
            {'Item': {'product_id': 'var-1', 'parent_id': 'prod-1'}},  # no price field
        ]

        event = _make_event({
            'event_id': None,
            'items': [{'product_id': 'prod-1', 'variant_id': 'var-1', 'quantity': 2}],
        })

        response = lambda_handler(event, None)
        assert response['statusCode'] == 201

        body = json.loads(response['body'])
        order = body.get('data', body)
        assert order['items'][0]['unit_price'] == 25
        assert order['total_amount'] == 50


class TestAccessControl:
    """Tests for access control."""

    def test_rejects_unauthorized_user(self, mock_dynamodb):
        """Users without proper roles are rejected."""
        from handler.create_order.app import lambda_handler

        with patch('handler.create_order.app.extract_user_credentials') as mock_extract, \
             patch('handler.create_order.app.validate_permissions_with_regions') as mock_validate:
            mock_extract.return_value = ('user@test.nl', ['some_other_role'], None)
            mock_validate.return_value = (False, None, None)

            event = _make_event({'event_id': None})
            response = lambda_handler(event, None)
            assert response['statusCode'] == 403
