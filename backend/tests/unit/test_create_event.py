"""
Unit tests for the create_event handler.

Tests cover:
- Event creation with event_type, constraints, product_ids (11.1)
- Date validation: registration_open < registration_close <= start_date <= end_date (11.3)
- Required field validation (11.4)
- Constraint validation: unique keys, max > 0, valid counting_rule (11.5)
- Event clone: copy event_type, product_ids, constraints, location; clear dates (11.7)

Requirements: 4
"""

import json
import os
import sys
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'create_event')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['DYNAMODB_TABLE'] = 'Events'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _make_event(body):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': 'POST',
        'body': json.dumps(body),
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


def _valid_event_body(**overrides):
    """Return a valid event body with all required fields."""
    body = {
        'name': 'Presidents Meeting 2027',
        'event_type': 'presmeet',
        'linked_regio': 'Regio Noord',
        'location': 'Hotel Amersfoort',
        'start_date': '2027-06-20',
        'end_date': '2027-06-22',
        'registration_open': '2027-01-01',
        'registration_close': '2027-05-01',
        'payment_deadline': '2027-05-15',
        'product_ids': ['prod-meeting', 'prod-party', 'prod-tshirt'],
        'constraints': [
            {
                'key': 'max_meeting_attendees',
                'label': 'Maximum vergaderdeelnemers',
                'max': 150,
                'counting_rule': 'count_items_by_product',
                'product_id': 'prod-meeting',
            },
            {
                'key': 'max_party_guests',
                'label': 'Maximum feestgangers',
                'max': 500,
                'counting_rule': 'count_items_by_product',
                'product_id': 'prod-party',
            },
        ],
    }
    body.update(overrides)
    return body


@pytest.fixture
def events_table():
    """Create a mocked Events DynamoDB table."""
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

        yield table


# ---------------------------------------------------------------------------
# Tests: Basic event creation (11.1)
# ---------------------------------------------------------------------------

class TestCreateEvent:
    """Tests for creating events with event_type, constraints, and product_ids."""

    def test_create_event_success(self, events_table):
        """Create a valid event with all fields."""
        import app as handler_module

        event = _make_event(_valid_event_body())

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        body = json.loads(response['body'])
        assert response['statusCode'] == 201
        assert 'event_id' in body
        assert body['message'] == 'Event created successfully'

        # Verify in DynamoDB
        item = events_table.get_item(Key={'event_id': body['event_id']})['Item']
        assert item['event_type'] == 'presmeet'
        assert item['name'] == 'Presidents Meeting 2027'
        assert item['status'] == 'draft'
        assert len(item['constraints']) == 2
        assert item['product_ids'] == ['prod-meeting', 'prod-party', 'prod-tshirt']
        assert 'created_at' in item
        assert item['created_by'] == 'admin@h-dcn.nl'

    def test_create_event_with_event_type(self, events_table):
        """event_type is stored correctly."""
        import app as handler_module

        for etype in ['presmeet', 'rally', 'ledendag']:
            event = _make_event(_valid_event_body(event_type=etype))
            with _auth_patches():
                response = handler_module.lambda_handler(event, {})
            body = json.loads(response['body'])
            assert response['statusCode'] == 201
            item = events_table.get_item(Key={'event_id': body['event_id']})['Item']
            assert item['event_type'] == etype

    def test_create_event_without_constraints(self, events_table):
        """Event without constraints is valid."""
        import app as handler_module

        body = _valid_event_body()
        del body['constraints']
        event = _make_event(body)

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_create_event_without_product_ids(self, events_table):
        """Event without product_ids is valid."""
        import app as handler_module

        body = _valid_event_body()
        del body['product_ids']
        event = _make_event(body)

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_create_event_initial_status_is_draft(self, events_table):
        """New events always start in draft status."""
        import app as handler_module

        event = _make_event(_valid_event_body())

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        body = json.loads(response['body'])
        item = events_table.get_item(Key={'event_id': body['event_id']})['Item']
        assert item['status'] == 'draft'


# ---------------------------------------------------------------------------
# Tests: Required field validation (11.4)
# ---------------------------------------------------------------------------

class TestRequiredFields:
    """Tests for required field validation."""

    @pytest.mark.parametrize('field', [
        'name', 'event_type', 'start_date', 'end_date', 'linked_regio',
    ])
    def test_missing_required_field_rejected(self, events_table, field):
        """Each required field must be present."""
        import app as handler_module

        body = _valid_event_body()
        del body[field]
        event = _make_event(body)

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert field in resp_body['error']

    def test_empty_name_rejected(self, events_table):
        """Empty string for name is treated as missing."""
        import app as handler_module

        event = _make_event(_valid_event_body(name=''))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_name_too_long_rejected(self, events_table):
        """Name exceeding 200 characters is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(name='A' * 201))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_location_too_long_rejected(self, events_table):
        """Location exceeding 300 characters is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(location='B' * 301))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400


# ---------------------------------------------------------------------------
# Tests: Date validation (11.3)
# ---------------------------------------------------------------------------

class TestDateValidation:
    """Tests for date ordering validation."""

    def test_valid_dates_accepted(self, events_table):
        """Correct ordering passes validation."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_open='2027-01-01',
            registration_close='2027-05-01',
            start_date='2027-06-20',
            end_date='2027-06-22',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_registration_open_not_before_close_rejected(self, events_table):
        """registration_open >= registration_close is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_open='2027-06-01',
            registration_close='2027-05-01',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'date' in body['error'].lower() or 'date_errors' in body

    def test_registration_open_equals_close_rejected(self, events_table):
        """registration_open == registration_close is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_open='2027-05-01',
            registration_close='2027-05-01',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_registration_close_after_start_date_rejected(self, events_table):
        """registration_close > start_date is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_close='2027-07-01',
            start_date='2027-06-20',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_registration_close_equals_start_date_accepted(self, events_table):
        """registration_close == start_date is valid (<=)."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_close='2027-06-20',
            start_date='2027-06-20',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_start_date_after_end_date_rejected(self, events_table):
        """start_date > end_date is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            start_date='2027-06-25',
            end_date='2027-06-22',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_start_date_equals_end_date_accepted(self, events_table):
        """start_date == end_date is valid (single-day event)."""
        import app as handler_module

        event = _make_event(_valid_event_body(
            registration_close='2027-06-20',
            start_date='2027-06-20',
            end_date='2027-06-20',
        ))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201


# ---------------------------------------------------------------------------
# Tests: Constraint validation (11.5)
# ---------------------------------------------------------------------------

class TestConstraintValidation:
    """Tests for constraint validation: unique keys, max > 0, valid counting_rule."""

    def test_valid_constraints_accepted(self, events_table):
        """Well-formed constraints pass validation."""
        import app as handler_module

        event = _make_event(_valid_event_body())

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_duplicate_constraint_keys_rejected(self, events_table):
        """Duplicate keys in constraints array are rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'key': 'max_meeting', 'label': 'Max', 'max': 10, 'counting_rule': 'count_items_by_product', 'product_id': 'p1'},
            {'key': 'max_meeting', 'label': 'Dup', 'max': 20, 'counting_rule': 'count_items_by_product', 'product_id': 'p2'},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'constraint_errors' in body

    def test_constraint_max_zero_rejected(self, events_table):
        """max value of 0 is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'key': 'zero_max', 'label': 'Zero', 'max': 0, 'counting_rule': 'count_items_by_product'},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_constraint_negative_max_rejected(self, events_table):
        """Negative max value is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'key': 'neg_max', 'label': 'Neg', 'max': -5, 'counting_rule': 'count_items_by_product'},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_constraint_invalid_counting_rule_rejected(self, events_table):
        """Invalid counting_rule value is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'key': 'bad_rule', 'label': 'Bad', 'max': 10, 'counting_rule': 'invalid_rule'},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'constraint_errors' in body
        assert 'invalid_rule' in str(body['constraint_errors'])

    def test_constraint_missing_key_rejected(self, events_table):
        """Constraint without key is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'label': 'No key', 'max': 10, 'counting_rule': 'count_items_by_product'},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_constraint_missing_counting_rule_rejected(self, events_table):
        """Constraint without counting_rule is rejected."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints=[
            {'key': 'no_rule', 'label': 'No rule', 'max': 10},
        ]))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_all_valid_counting_rules_accepted(self, events_table):
        """All three valid counting rules are accepted."""
        import app as handler_module

        constraints = [
            {'key': 'c1', 'label': 'L1', 'max': 10, 'counting_rule': 'count_items_by_product', 'product_id': 'p1'},
            {'key': 'c2', 'label': 'L2', 'max': 50, 'counting_rule': 'count_distinct_clubs'},
            {'key': 'c3', 'label': 'L3', 'max': 100, 'counting_rule': 'sum_field', 'field_name': 'persons'},
        ]
        event = _make_event(_valid_event_body(constraints=constraints))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 201

    def test_constraints_not_array_rejected(self, events_table):
        """constraints must be an array."""
        import app as handler_module

        event = _make_event(_valid_event_body(constraints={'key': 'val'}))

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400


# ---------------------------------------------------------------------------
# Tests: Event clone (11.7)
# ---------------------------------------------------------------------------

class TestEventClone:
    """Tests for event cloning."""

    def test_clone_event_copies_fields(self, events_table):
        """Clone copies event_type, product_ids, constraints, location."""
        import app as handler_module

        # First create a source event
        source_body = _valid_event_body()
        create_event = _make_event(source_body)
        with _auth_patches():
            create_response = handler_module.lambda_handler(create_event, {})
        source_id = json.loads(create_response['body'])['event_id']

        # Clone it
        clone_event = _make_event({'clone_from': source_id})
        with _auth_patches():
            clone_response = handler_module.lambda_handler(clone_event, {})

        assert clone_response['statusCode'] == 201
        clone_body = json.loads(clone_response['body'])
        assert clone_body['cloned_from'] == source_id
        assert clone_body['event_id'] != source_id

        # Verify cloned event in DB
        cloned = events_table.get_item(Key={'event_id': clone_body['event_id']})['Item']
        assert cloned['event_type'] == 'presmeet'
        assert cloned['location'] == 'Hotel Amersfoort'
        assert cloned['product_ids'] == source_body['product_ids']
        assert len(cloned['constraints']) == 2
        assert cloned['status'] == 'draft'
        assert cloned['created_by'] == 'admin@h-dcn.nl'

    def test_clone_event_clears_dates(self, events_table):
        """Cloned event does not have date fields set."""
        import app as handler_module

        # Create source
        create_event = _make_event(_valid_event_body())
        with _auth_patches():
            create_response = handler_module.lambda_handler(create_event, {})
        source_id = json.loads(create_response['body'])['event_id']

        # Clone it
        clone_event = _make_event({'clone_from': source_id})
        with _auth_patches():
            clone_response = handler_module.lambda_handler(clone_event, {})

        clone_body = json.loads(clone_response['body'])
        cloned = events_table.get_item(Key={'event_id': clone_body['event_id']})['Item']

        # Date fields should not be present
        assert 'start_date' not in cloned
        assert 'end_date' not in cloned
        assert 'registration_open' not in cloned
        assert 'registration_close' not in cloned
        assert 'payment_deadline' not in cloned

    def test_clone_nonexistent_event_returns_404(self, events_table):
        """Cloning a non-existent event returns 404."""
        import app as handler_module

        clone_event = _make_event({'clone_from': 'nonexistent-id'})
        with _auth_patches():
            response = handler_module.lambda_handler(clone_event, {})

        assert response['statusCode'] == 404


# ---------------------------------------------------------------------------
# Tests: Auth and error handling
# ---------------------------------------------------------------------------

class TestAuthAndErrors:
    """Tests for authentication and error handling."""

    def test_unauthenticated_request_rejected(self, events_table):
        """Request without auth is rejected."""
        import app as handler_module

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(_valid_event_body()),
            'headers': {},
            'requestContext': {},
        }

        response = handler_module.lambda_handler(event, {})
        assert response['statusCode'] in [401, 403, 500]

    def test_invalid_json_body_rejected(self, events_table):
        """Malformed JSON body returns 400."""
        import app as handler_module

        event = {
            'httpMethod': 'POST',
            'body': 'not valid json{{{',
            'headers': {'Authorization': 'Bearer mock-token'},
            'requestContext': {},
        }

        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        assert response['statusCode'] == 400

    def test_options_request_handled(self, events_table):
        """OPTIONS request returns CORS preflight response."""
        import app as handler_module

        event = {'httpMethod': 'OPTIONS'}

        response = handler_module.lambda_handler(event, {})
        assert response['statusCode'] == 200
