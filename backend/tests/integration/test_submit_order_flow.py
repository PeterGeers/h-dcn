"""
Integration tests for the submit order flow.

Tests the full pipeline: create order → add items with item_fields → submit →
verify order_number, validation, and status transitions.

Uses moto for DynamoDB mocking and unittest.mock for auth layer.

Requirements validated: 1.2, 3.1, 5.5, 6.3
"""

import json
import os
import sys
import importlib
import re
from decimal import Decimal
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# Fixtures
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
    os.environ['COUNTERS_TABLE_NAME'] = 'Counters'
    os.environ['MEMBERSHIPS_TABLE_NAME'] = 'Memberships'
    os.environ['MEMBERS_TABLE_NAME'] = 'Members'


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mocked DynamoDB tables with test data."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Orders table
        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Producten table
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

        # Counters table
        counters = dynamodb.create_table(
            TableName='Counters',
            KeySchema=[{'AttributeName': 'counter_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'counter_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Memberships table
        memberships = dynamodb.create_table(
            TableName='Memberships',
            KeySchema=[{'AttributeName': 'membership_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'membership_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # --- Seed test data ---

        # Member
        members.put_item(Item={
            'member_id': 'mem_test',
            'email': 'test@h-dcn.nl',
            'club_id': 'NL001',
            'status': 'active',
        })

        # Active membership
        memberships.put_item(Item={
            'membership_id': 'ms_test',
            'member_id': 'mem_test',
            'status': 'active',
        })

        # Product with item_fields and purchase_rules
        producten.put_item(Item={
            'product_id': 'prod_event_ticket',
            'is_parent': True,
            'name': 'Event Ticket',
            'price': Decimal('50.00'),
            'active': True,
            'order_item_fields': [
                {'id': 'naam', 'label': 'Naam deelnemer', 'type': 'text',
                 'required': True, 'validation': {'min_length': 2}},
                {'id': 'email', 'label': 'E-mail', 'type': 'email',
                 'required': True},
            ],
            'purchase_rules': {
                'max_per_order': 3,
                'max_per_member': 5,
            },
        })

        # Variant for the product
        producten.put_item(Item={
            'product_id': 'var_event_standard',
            'is_parent': False,
            'parent_id': 'prod_event_ticket',
            'name': 'Event Ticket - Standard',
            'variant_attributes': {'Type': 'Standard'},
            'price': Decimal('50.00'),
            'stock': 100,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Simple product (no rules, no item_fields)
        producten.put_item(Item={
            'product_id': 'prod_simple',
            'is_parent': True,
            'name': 'Simple Sticker',
            'price': Decimal('5.00'),
            'active': True,
        })

        yield {
            'dynamodb': dynamodb,
            'orders': orders,
            'producten': producten,
            'counters': counters,
            'members': members,
            'memberships': memberships,
        }


@pytest.fixture
def mock_auth():
    """Mock auth utilities for the submit_order handler."""
    with patch('shared.auth_utils.extract_user_credentials') as mock_extract, \
         patch('shared.auth_utils.validate_permissions_with_regions') as mock_validate, \
         patch('shared.auth_utils.log_successful_access'):

        def extract_side_effect(event):
            return (
                event.get('_test_user_email', 'test@h-dcn.nl'),
                event.get('_test_user_roles', ['hdcnLeden']),
                None,
            )

        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = (False, None, None)

        yield mock_extract, mock_validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(path_params=None, body=None, method='POST',
                user_email='test@h-dcn.nl', user_roles=None):
    """Build a Lambda event dict for testing."""
    if user_roles is None:
        user_roles = ['hdcnLeden']
    event = {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer mock-token'},
        'body': json.dumps(body) if body else None,
        'pathParameters': path_params,
        '_test_user_email': user_email,
        '_test_user_roles': user_roles,
    }
    return event


def _create_draft_order(orders_table, items, member_id='mem_test',
                        user_email='test@h-dcn.nl', club_id='NL001'):
    """Insert a draft order directly into DynamoDB and return order_id."""
    import uuid
    from datetime import datetime, timezone

    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    order = {
        'order_id': order_id,
        'status': 'draft',
        'payment_status': 'unpaid',
        'member_id': member_id,
        'user_email': user_email,
        'club_id': club_id,
        'items': items,
        'total_amount': Decimal('0'),
        'total_paid': Decimal('0'),
        'version': 1,
        'created_at': now,
        'updated_at': now,
    }

    orders_table.put_item(Item=order)
    return order_id


# ---------------------------------------------------------------------------
# Test: Happy path — submit draft order successfully
# ---------------------------------------------------------------------------


class TestSubmitOrderHappyPath:
    """
    Happy path: create draft order → submit → verify status='submitted',
    order_number assigned in H-YYMMDD-NNN format, submitted_at set.

    Validates: Requirements 1.2, 3.1
    """

    def test_submit_draft_order_success(self, dynamodb_tables, mock_auth):
        """
        Submitting a valid draft order transitions to 'submitted',
        assigns an order_number in H-YYMMDD-NNN format, and sets submitted_at.
        """
        orders_table = dynamodb_tables['orders']

        # Create a draft order with valid item_fields_data
        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 2,
            'item_fields_data': [
                {'field_values': {'naam': 'Jan Jansen', 'email': 'jan@test.nl'}},
                {'field_values': {'naam': 'Piet de Vries', 'email': 'piet@test.nl'}},
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        # Import and invoke submit_order handler
        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # Verify order_number format H-YYMMDD-NNN
        assert 'order_number' in body
        order_number = body['order_number']
        assert re.match(r'^H-\d{6}-\d{3}$', order_number), \
            f"order_number '{order_number}' doesn't match H-YYMMDD-NNN format"

        # Verify status is 'submitted'
        assert body['status'] == 'submitted'

        # Verify submitted_at is set
        assert 'submitted_at' in body
        assert body['submitted_at'] is not None

        # Verify persisted state in DynamoDB
        stored_order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert stored_order['status'] == 'submitted'
        assert stored_order['order_number'] == order_number
        assert 'submitted_at' in stored_order

    def test_submit_order_without_item_fields_product(self, dynamodb_tables, mock_auth):
        """
        Submitting a draft order for a product without order_item_fields
        succeeds without item_fields_data validation.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_simple',
            'quantity': 1,
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert re.match(r'^H-\d{6}-\d{3}$', body['order_number'])

    def test_sequential_order_numbers(self, dynamodb_tables, mock_auth):
        """
        Submitting multiple orders produces sequential order numbers.
        """
        orders_table = dynamodb_tables['orders']

        # Create two draft orders
        items = [{'product_id': 'prod_simple', 'quantity': 1}]
        order_id_1 = _create_draft_order(orders_table, items)
        order_id_2 = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        # Submit first
        resp1 = submit_mod.lambda_handler(
            _make_event(path_params={'id': order_id_1}), None)
        num1 = json.loads(resp1['body'])['order_number']

        # Submit second
        resp2 = submit_mod.lambda_handler(
            _make_event(path_params={'id': order_id_2}), None)
        num2 = json.loads(resp2['body'])['order_number']

        # Both should have the same date prefix, but sequential numbers
        assert num1 != num2
        # Extract sequence numbers
        seq1 = int(num1.split('-')[2])
        seq2 = int(num2.split('-')[2])
        assert seq2 == seq1 + 1


# ---------------------------------------------------------------------------
# Test: Validation — missing required item_fields
# ---------------------------------------------------------------------------


class TestSubmitOrderItemFieldsValidation:
    """
    Validation: submit order with missing required item_fields → verify
    rejection with structured errors.

    Validates: Requirements 6.3
    """

    def test_missing_item_fields_data_rejected(self, dynamodb_tables, mock_auth):
        """
        Submitting an order with a product that requires item_fields but
        item_fields_data is missing returns 400 with structured errors.
        """
        orders_table = dynamodb_tables['orders']

        # item_fields_data is missing entirely
        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 2,
            # No item_fields_data
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Validation failed'
        assert 'errors' in body
        assert len(body['errors']) > 0

    def test_empty_required_field_rejected(self, dynamodb_tables, mock_auth):
        """
        Submitting an order where a required field has empty value returns
        400 with error identifying the field.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 1,
            'item_fields_data': [
                {'field_values': {'naam': '', 'email': 'valid@test.nl'}},
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Validation failed'
        errors = body['errors']
        # Should have an error for the 'naam' field
        naam_errors = [e for e in errors if e.get('field') == 'naam']
        assert len(naam_errors) > 0

    def test_wrong_count_item_fields_data_rejected(self, dynamodb_tables, mock_auth):
        """
        Submitting an order where item_fields_data count != quantity returns
        400 with error.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 3,
            'item_fields_data': [
                {'field_values': {'naam': 'Jan', 'email': 'jan@test.nl'}},
                {'field_values': {'naam': 'Piet', 'email': 'piet@test.nl'}},
                # Missing third entry — count mismatch
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Validation failed'
        assert len(body['errors']) > 0

    def test_invalid_email_format_rejected(self, dynamodb_tables, mock_auth):
        """
        Submitting an order with an invalid email in a required email field
        returns 400 with error.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 1,
            'item_fields_data': [
                {'field_values': {'naam': 'Jan Jansen', 'email': 'not-an-email'}},
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Validation failed'
        errors = body['errors']
        email_errors = [e for e in errors if e.get('field') == 'email']
        assert len(email_errors) > 0


# ---------------------------------------------------------------------------
# Test: Purchase rules — max_per_order exceeded
# ---------------------------------------------------------------------------


class TestSubmitOrderPurchaseRules:
    """
    Purchase rules: submit order exceeding max_per_order → verify rejection.

    Validates: Requirements 5.5
    """

    def test_max_per_order_exceeded_rejected(self, dynamodb_tables, mock_auth):
        """
        Submitting an order with quantity exceeding max_per_order (3) is rejected.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 4,  # max_per_order is 3
            'item_fields_data': [
                {'field_values': {'naam': 'A Naam', 'email': 'a@test.nl'}},
                {'field_values': {'naam': 'B Naam', 'email': 'b@test.nl'}},
                {'field_values': {'naam': 'C Naam', 'email': 'c@test.nl'}},
                {'field_values': {'naam': 'D Naam', 'email': 'd@test.nl'}},
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Validation failed'
        errors = body['errors']
        rule_errors = [e for e in errors if e.get('field') == 'purchase_rules']
        assert len(rule_errors) > 0
        assert 'max_per_order' in rule_errors[0]['message']

    def test_within_limits_accepted(self, dynamodb_tables, mock_auth):
        """
        Submitting an order within max_per_order limit succeeds.
        """
        orders_table = dynamodb_tables['orders']

        items = [{
            'product_id': 'prod_event_ticket',
            'variant_id': 'var_event_standard',
            'quantity': 3,  # exactly at max_per_order limit
            'item_fields_data': [
                {'field_values': {'naam': 'Jan Jansen', 'email': 'jan@test.nl'}},
                {'field_values': {'naam': 'Piet de Vries', 'email': 'piet@test.nl'}},
                {'field_values': {'naam': 'Klaas Vaak', 'email': 'klaas@test.nl'}},
            ],
        }]
        order_id = _create_draft_order(orders_table, items)

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'


# ---------------------------------------------------------------------------
# Test: State machine — submit already-submitted order rejected
# ---------------------------------------------------------------------------


class TestSubmitOrderStateMachine:
    """
    State machine: attempt to submit an already-submitted order → verify rejection.

    Validates: Requirements 1.2
    """

    def test_submit_already_submitted_rejected(self, dynamodb_tables, mock_auth):
        """
        Attempting to submit an order that is already 'submitted' returns 400
        with InvalidTransitionError details.
        """
        orders_table = dynamodb_tables['orders']

        # Create an order that's already submitted
        import uuid
        from datetime import datetime, timezone

        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        orders_table.put_item(Item={
            'order_id': order_id,
            'status': 'submitted',
            'payment_status': 'unpaid',
            'order_number': 'H-250101-001',
            'member_id': 'mem_test',
            'user_email': 'test@h-dcn.nl',
            'club_id': 'NL001',
            'items': [{'product_id': 'prod_simple', 'quantity': 1}],
            'total_amount': Decimal('5.00'),
            'version': 1,
            'submitted_at': now,
            'created_at': now,
            'updated_at': now,
        })

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid transition' in body.get('error', '')
        assert body.get('current') == 'submitted'
        assert body.get('target') == 'submitted'

    def test_submit_confirmed_order_rejected(self, dynamodb_tables, mock_auth):
        """
        Attempting to submit a 'confirmed' order is rejected.
        """
        orders_table = dynamodb_tables['orders']

        import uuid
        from datetime import datetime, timezone

        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        orders_table.put_item(Item={
            'order_id': order_id,
            'status': 'confirmed',
            'payment_status': 'paid',
            'order_number': 'H-250101-002',
            'member_id': 'mem_test',
            'user_email': 'test@h-dcn.nl',
            'club_id': 'NL001',
            'items': [{'product_id': 'prod_simple', 'quantity': 1}],
            'total_amount': Decimal('5.00'),
            'version': 1,
            'submitted_at': now,
            'created_at': now,
            'updated_at': now,
        })

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid transition' in body.get('error', '')
        assert body.get('current') == 'confirmed'

    def test_submit_cancelled_order_rejected(self, dynamodb_tables, mock_auth):
        """
        Attempting to submit a 'cancelled' order is rejected.
        """
        orders_table = dynamodb_tables['orders']

        import uuid
        from datetime import datetime, timezone

        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        orders_table.put_item(Item={
            'order_id': order_id,
            'status': 'cancelled',
            'payment_status': 'unpaid',
            'member_id': 'mem_test',
            'user_email': 'test@h-dcn.nl',
            'club_id': 'NL001',
            'items': [{'product_id': 'prod_simple', 'quantity': 1}],
            'total_amount': Decimal('5.00'),
            'version': 1,
            'created_at': now,
            'updated_at': now,
        })

        import handler.submit_order.app as submit_mod
        importlib.reload(submit_mod)

        event = _make_event(path_params={'id': order_id})
        response = submit_mod.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid transition' in body.get('error', '')
        assert body.get('current') == 'cancelled'
