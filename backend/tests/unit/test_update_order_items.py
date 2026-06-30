"""
Unit tests for update_order_items handler.

Tests the unified update_order_items handler that:
- Updates items on a draft order with optimistic locking
- Rejects stale versions with 409 Conflict
- Fetches prices from Producten table
- Validates variant parent_id matches product_id
- Accepts incomplete item data (draft mode)
- Increments version on success
- Accepts persons array structure with per-person product lines
- Syncs item_fields_data.name when person name is updated
- Removes all product lines when a person is removed

Requirements: 5.5, 6.4, 6.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.3, 10.9, 12.21
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

# Used by conftest.py to ensure correct handler path during full-suite runs
_handler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_order_items'))


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


class TestPersonsStructure:
    """Tests for persons array structure (Requirements 6.4, 6.5, 5.5, 8.3)."""

    def test_accepts_persons_array(self, mock_dynamodb, mock_auth):
        """Handler accepts persons array instead of items array."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('25.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {
                    'name': 'Jan de Vries',
                    'items': [{'product_id': 'prod-1', 'quantity': 1}],
                },
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['person_count'] == 1
        assert body['item_count'] == 1
        assert body['total_amount'] == 25.0

    def test_syncs_name_to_item_fields_data(self, mock_dynamodb, mock_auth):
        """Person name is synced to item_fields_data.name on product lines (Req 6.4)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('10.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {
                    'name': 'Maria Janssen',
                    'items': [
                        {'product_id': 'prod-1', 'quantity': 1, 'item_fields_data': {'name': 'old name'}},
                    ],
                },
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify the update_item call contains synced name
        call_kwargs = mock_dynamodb['orders'].update_item.call_args[1]
        items = call_kwargs['ExpressionAttributeValues'][':items']
        assert items[0]['item_fields_data']['name'] == 'Maria Janssen'

    def test_syncs_name_when_no_item_fields_data(self, mock_dynamodb, mock_auth):
        """Name is synced even when item_fields_data is initially absent (Req 6.4)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('10.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {
                    'name': 'Pieter Bakker',
                    'items': [
                        {'product_id': 'prod-1', 'quantity': 1},  # no item_fields_data
                    ],
                },
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        call_kwargs = mock_dynamodb['orders'].update_item.call_args[1]
        items = call_kwargs['ExpressionAttributeValues'][':items']
        assert items[0]['item_fields_data']['name'] == 'Pieter Bakker'

    def test_person_removal_removes_product_lines(self, mock_dynamodb, mock_auth):
        """Removing a person removes all their product lines (Req 6.5)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('20.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        # Send only person 0 — person 1 was "removed"
        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {
                    'name': 'Jan',
                    'items': [{'product_id': 'prod-1', 'quantity': 1}],
                },
                # Person 1 removed (not present)
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['person_count'] == 1
        assert body['item_count'] == 1

    def test_multiple_persons_with_multiple_items(self, mock_dynamodb, mock_auth):
        """Multiple persons each with multiple product lines."""
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
            'persons': [
                {
                    'name': 'Alice',
                    'items': [
                        {'product_id': 'prod-1', 'quantity': 2},
                        {'product_id': 'prod-1', 'quantity': 1},
                    ],
                },
                {
                    'name': 'Bob',
                    'items': [
                        {'product_id': 'prod-1', 'quantity': 3},
                    ],
                },
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['person_count'] == 2
        assert body['item_count'] == 3
        # Total: (2*15) + (1*15) + (3*15) = 90
        assert body['total_amount'] == 90.0

    def test_persons_stores_persons_metadata(self, mock_dynamodb, mock_auth):
        """Persons metadata is stored alongside items."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {'name': 'Jan', 'items': []},
                {'name': 'Piet', 'items': []},
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify persons data is stored
        call_kwargs = mock_dynamodb['orders'].update_item.call_args[1]
        assert ':persons' in call_kwargs['ExpressionAttributeValues']
        persons_stored = call_kwargs['ExpressionAttributeValues'][':persons']
        assert len(persons_stored) == 2
        assert persons_stored[0]['name'] == 'Jan'
        assert persons_stored[1]['name'] == 'Piet'

    def test_accepts_empty_persons_array(self, mock_dynamodb, mock_auth):
        """Empty persons array is valid (all persons removed)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['person_count'] == 0
        assert body['item_count'] == 0

    def test_rejects_invalid_person_type(self, mock_dynamodb, mock_auth):
        """Rejects non-object entries in persons array."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }

        event = _make_event('order-1', {
            'version': 1,
            'persons': ['not-an-object'],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'must be an object' in body['error'].lower()

    def test_persons_with_empty_name_accepted_in_draft(self, mock_dynamodb, mock_auth):
        """Draft orders accept persons with empty names (validation at submit)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {'name': '', 'items': []},
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_person_index_stored_on_items(self, mock_dynamodb, mock_auth):
        """Each processed item has person_index for association."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('10.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [
                {'name': 'Person A', 'items': [{'product_id': 'prod-1', 'quantity': 1}]},
                {'name': 'Person B', 'items': [{'product_id': 'prod-1', 'quantity': 1}]},
            ],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

        call_kwargs = mock_dynamodb['orders'].update_item.call_args[1]
        items = call_kwargs['ExpressionAttributeValues'][':items']
        assert items[0]['person_index'] == 0
        assert items[1]['person_index'] == 1


class TestPersonsOptimisticLocking:
    """Tests for optimistic locking with persons structure (Req 5.5, 8.3)."""

    def test_version_conflict_with_persons(self, mock_dynamodb, mock_auth):
        """409 Conflict when version doesn't match (persons path)."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=5)
        }

        event = _make_event('order-1', {
            'version': 3,  # stale
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body.get('current_version') == 5

    def test_version_increments_on_persons_save(self, mock_dynamodb, mock_auth):
        """Version increments when saving with persons structure."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=3)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 3,
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['version'] == 4

    def test_conditional_check_failure_with_persons(self, mock_dynamodb, mock_auth):
        """409 on DynamoDB race condition with persons path."""
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
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 409


class TestDelegateAccess:
    """Tests for delegate access to event orders (Req 5.5)."""

    def test_allows_primary_delegate_access(self, mock_dynamodb, mock_auth):
        """Primary delegate can update the order."""
        from app import lambda_handler

        order = _draft_order(version=1, user_email='owner@test.nl')
        order['delegates'] = {
            'primary': 'user@test.nl',
            'primary_member_id': 'member-1',
        }
        mock_dynamodb['orders'].get_item.return_value = {'Item': order}
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_allows_secondary_delegate_access(self, mock_dynamodb, mock_auth):
        """Secondary delegate can update the order."""
        from app import lambda_handler

        order = _draft_order(version=1, user_email='owner@test.nl')
        order['delegates'] = {
            'primary': 'owner@test.nl',
            'secondary': 'user@test.nl',
            'primary_member_id': 'member-owner',
            'secondary_member_id': 'member-1',
        }
        mock_dynamodb['orders'].get_item.return_value = {'Item': order}
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_rejects_non_delegate(self, mock_dynamodb, mock_auth):
        """Non-delegate cannot update event order."""
        from app import lambda_handler

        order = _draft_order(version=1, user_email='owner@test.nl')
        order['delegates'] = {
            'primary': 'other@test.nl',
            'secondary': 'another@test.nl',
            'primary_member_id': 'member-other',
            'secondary_member_id': 'member-another',
        }
        mock_dynamodb['orders'].get_item.return_value = {'Item': order}

        event = _make_event('order-1', {
            'version': 1,
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with flat items array."""

    def test_items_still_works(self, mock_dynamodb, mock_auth):
        """Flat items array still works for webshop orders."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['producten'].get_item.return_value = {
            'Item': {'product_id': 'prod-1', 'price': Decimal('10.00')}
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 2}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'person_count' not in body  # No persons in flat items mode
        assert body['item_count'] == 1

    def test_persons_takes_precedence_over_items(self, mock_dynamodb, mock_auth):
        """When both persons and items are provided, persons is used."""
        from app import lambda_handler

        mock_dynamodb['orders'].get_item.return_value = {
            'Item': _draft_order(version=1)
        }
        mock_dynamodb['orders'].update_item.return_value = {}

        event = _make_event('order-1', {
            'version': 1,
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
            'persons': [{'name': 'Jan', 'items': []}],
        })
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['person_count'] == 1  # Persons was used

    def test_rejects_neither_items_nor_persons(self, mock_dynamodb, mock_auth):
        """Rejects request with neither items nor persons."""
        from app import lambda_handler

        event = _make_event('order-1', {'version': 1})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'items or persons' in body['error'].lower()
