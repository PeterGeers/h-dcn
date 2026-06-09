"""
Unit tests for the update_event handler.

Tests cover:
- Extending update_event with event_type, constraints, product_ids (11.2)
- Date validation on partial updates (11.3)
- Constraint validation on updates (11.5)
- Manual status override transitions: draft→open, open→closed, closed→open (11.6)

Requirements: 4
"""

import json
import os
import sys
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws
from datetime import datetime

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_event')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['DYNAMODB_TABLE'] = 'Events'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _make_event(body, event_id='test-event-1'):
    """Create a mock API Gateway event for update."""
    return {
        'httpMethod': 'PUT',
        'body': json.dumps(body),
        'pathParameters': {'event_id': event_id},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Events_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'},
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Events_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _seed_event(table, event_id='test-event-1', **overrides):
    """Insert a test event into the table."""
    item = {
        'event_id': event_id,
        'name': 'Presidents Meeting 2027',
        'event_type': 'presmeet',
        'location': 'Hotel Amersfoort',
        'status': 'draft',
        'start_date': '2027-06-20',
        'end_date': '2027-06-22',
        'registration_open': '2027-01-01',
        'registration_close': '2027-05-01',
        'payment_deadline': '2027-05-15',
        'product_ids': ['prod-meeting', 'prod-party'],
        'constraints': [
            {
                'key': 'max_meeting',
                'label': 'Max meeting',
                'max': 150,
                'counting_rule': 'count_items_by_product',
                'product_id': 'prod-meeting',
            },
        ],
        'created_at': '2026-12-01T08:00:00',
        'created_by': 'admin@h-dcn.nl',
    }
    item.update(overrides)
    table.put_item(Item=item)
    return item


@pytest.fixture
def events_table():
    """Create a mocked Events DynamoDB table with a seeded event."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        if sys.path[0] != _handler_path:
            if _handler_path in sys.path:
                sys.path.remove(_handler_path)
            sys.path.insert(0, _handler_path)

        if 'app' in sys.modules:
            del sys.modules['app']

        import app as handler_module
        handler_module.table = table

        # Seed a default test event
        _seed_event(table)

        yield table


# ---------------------------------------------------------------------------
# Tests: Update event fields (11.2)
# ---------------------------------------------------------------------------

class TestUpdateEventFields:
    """Tests for updating event_type, constraints, and product_ids."""

    def test_update_event_type(self, events_table):
        """Update event_type field."""
        import app as handler_module

        event = _make_event({'event_type': 'rally'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['event_type'] == 'rally'

    def test_update_product_ids(self, events_table):
        """Update product_ids array."""
        import app as handler_module

        new_products = ['prod-a', 'prod-b', 'prod-c']
        event = _make_event({'product_ids': new_products})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['product_ids'] == new_products

    def test_update_constraints(self, events_table):
        """Update constraints array."""
        import app as handler_module

        new_constraints = [
            {'key': 'new_constraint', 'label': 'New', 'max': 50, 'counting_rule': 'count_distinct_clubs'},
        ]
        event = _make_event({'constraints': new_constraints})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert len(item['constraints']) == 1
        assert item['constraints'][0]['key'] == 'new_constraint'

    def test_update_name(self, events_table):
        """Update event name."""
        import app as handler_module

        event = _make_event({'name': 'Rally 2027'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['name'] == 'Rally 2027'

    def test_update_location(self, events_table):
        """Update event location."""
        import app as handler_module

        event = _make_event({'location': 'Hotel Utrecht'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['location'] == 'Hotel Utrecht'

    def test_update_multiple_fields(self, events_table):
        """Update multiple fields at once."""
        import app as handler_module

        event = _make_event({
            'name': 'Ledendag 2027',
            'event_type': 'ledendag',
            'location': 'Zandvoort',
            'product_ids': ['prod-x'],
        })

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'name' in body['updated_fields']
        assert 'event_type' in body['updated_fields']
        assert 'location' in body['updated_fields']
        assert 'product_ids' in body['updated_fields']

    def test_update_nonexistent_event_returns_404(self, events_table):
        """Updating a non-existent event returns 404."""
        import app as handler_module

        event = _make_event({'name': 'New name'}, event_id='nonexistent-id')

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 404

    def test_update_sets_updated_at(self, events_table):
        """Update sets the updated_at timestamp."""
        import app as handler_module

        event = _make_event({'name': 'Updated Name'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert 'updated_at' in item


# ---------------------------------------------------------------------------
# Tests: Date validation on update (11.3)
# ---------------------------------------------------------------------------

class TestUpdateDateValidation:
    """Tests for date ordering validation during partial updates."""

    def test_valid_date_update_accepted(self, events_table):
        """Changing a date to a valid value passes."""
        import app as handler_module

        event = _make_event({'registration_close': '2027-04-01'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200

    def test_date_update_that_violates_ordering_rejected(self, events_table):
        """Changing registration_close to after start_date is rejected."""
        import app as handler_module

        # Current start_date is 2027-06-20, moving close to after that
        event = _make_event({'registration_close': '2027-07-01'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'date_errors' in body

    def test_start_date_update_validates_against_existing_end_date(self, events_table):
        """Moving start_date past end_date is rejected."""
        import app as handler_module

        # Current end_date is 2027-06-22
        event = _make_event({'start_date': '2027-07-01'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_registration_open_update_validates_against_existing_close(self, events_table):
        """Moving registration_open past registration_close is rejected."""
        import app as handler_module

        # Current registration_close is 2027-05-01
        event = _make_event({'registration_open': '2027-06-01'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400


# ---------------------------------------------------------------------------
# Tests: Constraint validation on update (11.5)
# ---------------------------------------------------------------------------

class TestUpdateConstraintValidation:
    """Tests for constraint validation during updates."""

    def test_valid_constraint_update_accepted(self, events_table):
        """Updating with valid constraints passes."""
        import app as handler_module

        event = _make_event({'constraints': [
            {'key': 'new_key', 'label': 'New', 'max': 100, 'counting_rule': 'sum_field', 'field_name': 'persons'},
        ]})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200

    def test_constraint_duplicate_keys_rejected(self, events_table):
        """Duplicate keys in updated constraints are rejected."""
        import app as handler_module

        event = _make_event({'constraints': [
            {'key': 'same', 'label': 'A', 'max': 10, 'counting_rule': 'count_items_by_product'},
            {'key': 'same', 'label': 'B', 'max': 20, 'counting_rule': 'count_items_by_product'},
        ]})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_constraint_max_zero_rejected(self, events_table):
        """max of 0 is rejected on update."""
        import app as handler_module

        event = _make_event({'constraints': [
            {'key': 'c1', 'label': 'C', 'max': 0, 'counting_rule': 'count_items_by_product'},
        ]})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_constraint_invalid_rule_rejected(self, events_table):
        """Invalid counting_rule is rejected on update."""
        import app as handler_module

        event = _make_event({'constraints': [
            {'key': 'c1', 'label': 'C', 'max': 10, 'counting_rule': 'bad_rule'},
        ]})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400


# ---------------------------------------------------------------------------
# Tests: Manual status override (11.6)
# ---------------------------------------------------------------------------

class TestStatusOverride:
    """Tests for manual status override transitions."""

    def test_draft_to_open(self, events_table):
        """Admin can transition draft → open."""
        import app as handler_module

        event = _make_event({'status': 'open'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['previous_status'] == 'draft'
        assert body['new_status'] == 'open'

        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['status'] == 'open'

    def test_open_to_closed(self, events_table):
        """Admin can transition open → closed."""
        import app as handler_module

        # Set event to open first
        events_table.update_item(
            Key={'event_id': 'test-event-1'},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'open'},
        )

        event = _make_event({'status': 'closed'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['previous_status'] == 'open'
        assert body['new_status'] == 'closed'

    def test_closed_to_open_reopen(self, events_table):
        """Admin can re-open: closed → open."""
        import app as handler_module

        # Set event to closed first
        events_table.update_item(
            Key={'event_id': 'test-event-1'},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'closed'},
        )

        event = _make_event({'status': 'open'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['previous_status'] == 'closed'
        assert body['new_status'] == 'open'

    def test_invalid_transition_draft_to_closed_rejected(self, events_table):
        """Invalid transition draft → closed is rejected."""
        import app as handler_module

        event = _make_event({'status': 'closed'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid status transition' in body['error']

    def test_invalid_transition_open_to_draft_rejected(self, events_table):
        """Invalid transition open → draft is rejected."""
        import app as handler_module

        events_table.update_item(
            Key={'event_id': 'test-event-1'},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'open'},
        )

        event = _make_event({'status': 'draft'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_invalid_status_value_rejected(self, events_table):
        """Completely invalid status value is rejected."""
        import app as handler_module

        event = _make_event({'status': 'invalid_status'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_status_override_records_metadata(self, events_table):
        """Status override records who changed it and when."""
        import app as handler_module

        event = _make_event({'status': 'open'})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 200
        item = events_table.get_item(Key={'event_id': 'test-event-1'})['Item']
        assert item['status_changed_by'] == 'admin@h-dcn.nl'
        assert 'status_changed_at' in item

    def test_status_override_nonexistent_event_returns_404(self, events_table):
        """Status override on non-existent event returns 404."""
        import app as handler_module

        event = _make_event({'status': 'open'}, event_id='nonexistent-id')

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 404


# ---------------------------------------------------------------------------
# Tests: Auth and validation edge cases
# ---------------------------------------------------------------------------

class TestAuthAndEdgeCases:
    """Tests for authentication and edge cases."""

    def test_unauthenticated_request_rejected(self, events_table):
        """Request without auth is rejected."""
        import app as handler_module

        event = {
            'httpMethod': 'PUT',
            'body': json.dumps({'name': 'New'}),
            'pathParameters': {'event_id': 'test-event-1'},
            'headers': {},
            'requestContext': {},
        }

        response = handler_module.lambda_handler(event, {})
        assert response['statusCode'] in [401, 403, 500]

    def test_invalid_json_body_rejected(self, events_table):
        """Malformed JSON body returns 400."""
        import app as handler_module

        event = {
            'httpMethod': 'PUT',
            'body': 'not valid json{{{',
            'pathParameters': {'event_id': 'test-event-1'},
            'headers': {'Authorization': 'Bearer mock-token'},
            'requestContext': {},
        }

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_name_too_long_rejected(self, events_table):
        """Name exceeding 200 chars on update is rejected."""
        import app as handler_module

        event = _make_event({'name': 'A' * 201})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_location_too_long_rejected(self, events_table):
        """Location exceeding 300 chars on update is rejected."""
        import app as handler_module

        event = _make_event({'location': 'B' * 301})

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_options_request_handled(self, events_table):
        """OPTIONS request returns CORS preflight response."""
        import app as handler_module

        event = {'httpMethod': 'OPTIONS'}

        response = handler_module.lambda_handler(event, {})
        assert response['statusCode'] == 200
