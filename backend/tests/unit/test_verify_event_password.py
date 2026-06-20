"""
Unit Tests for verify_event_password Lambda Handler.

Tests the public password verification endpoint:
- Returns 400 when event_id is missing
- Returns 400 when password is missing
- Returns { valid: false } for non-existent event (no info leak)
- Returns { valid: false } for wrong password
- Returns { valid: true } with session_token for correct password
- Handles 72-byte bcrypt truncation
- Returns generic error structure (no info leak between non-existent event and wrong password)
- Returns 405 for non-POST methods
"""

import importlib.util
import json
import os
import sys
import time

import boto3
import bcrypt
import jwt
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['JWT_SECRET_BASE'] = 'test-secret-base'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'verify_event_password', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_EVENT_ID = 'evt-pwd-1234-5678-abcd'
TEST_PASSWORD = 'geheim2027'
TEST_WRONG_PASSWORD = 'fout-wachtwoord'


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt for test data."""
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def _make_event(event_id=None, method='POST', body=None):
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': None,
        'pathParameters': {'event_id': event_id} if event_id else None,
        'body': json.dumps(body) if body else None,
    }


def _seed_event(events_table, event_id=TEST_EVENT_ID, password=TEST_PASSWORD,
                has_password=True, registry_config=None):
    """Seed an event with optional password hash."""
    item = {
        'event_id': event_id,
        'name': 'Presidents Meeting 2027',
        'event_type': 'presmeet',
        'status': 'open',
        'landing_page_enabled': True,
    }
    if has_password and password:
        item['event_password'] = _hash_password(password)
    if registry_config:
        item['registry_config'] = registry_config
    else:
        item['registry_config'] = {
            'row_label': 'club',
            'claim_mode': 'first_come_first_served',
            'max_delegates_per_row': 2,
            's3_path': 'events/presmeet2027/registry.json',
        }
    events_table.put_item(Item=item)
    return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        handler_module = _load_handler()
        yield events_table, handler_module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVerifyEventPassword:
    """Tests for the password verification endpoint."""

    def test_options_request(self, setup_tables):
        """CORS preflight returns 200."""
        _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID, method='OPTIONS')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_method_not_allowed(self, setup_tables):
        """Non-POST methods return 405."""
        _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID, method='GET')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 405

    def test_missing_event_id_returns_400(self, setup_tables):
        """Returns 400 when no event_id path parameter is provided."""
        _, handler = setup_tables
        event = _make_event(event_id=None, body={'password': TEST_PASSWORD})
        event['pathParameters'] = None
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'event_id' in body['error'].lower()

    def test_missing_password_returns_400(self, setup_tables):
        """Returns 400 when password is not provided in body."""
        _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID, body={})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'password' in body['error'].lower() or 'required' in body['error'].lower()

    def test_nonexistent_event_returns_valid_false(self, setup_tables):
        """Returns { valid: false } for non-existent event (no info leak)."""
        _, handler = setup_tables
        event = _make_event(event_id='nonexistent-event', body={'password': TEST_PASSWORD})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        # Should not contain any event metadata
        assert 'event_name' not in body
        assert 'session_token' not in body

    def test_event_without_password_returns_valid_false(self, setup_tables):
        """Returns { valid: false } for event without password configured."""
        events_table, handler = setup_tables
        _seed_event(events_table, has_password=False)

        event = _make_event(event_id=TEST_EVENT_ID, body={'password': TEST_PASSWORD})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False

    def test_wrong_password_returns_valid_false(self, setup_tables):
        """Returns { valid: false } for incorrect password."""
        events_table, handler = setup_tables
        _seed_event(events_table)

        event = _make_event(event_id=TEST_EVENT_ID, body={'password': TEST_WRONG_PASSWORD})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        # Should not contain any event metadata
        assert 'event_name' not in body
        assert 'session_token' not in body

    def test_correct_password_returns_valid_true_with_token(self, setup_tables):
        """Returns { valid: true } with session token for correct password."""
        events_table, handler = setup_tables
        _seed_event(events_table)

        event = _make_event(event_id=TEST_EVENT_ID, body={'password': TEST_PASSWORD})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is True
        assert body['event_name'] == 'Presidents Meeting 2027'
        assert 'session_token' in body
        assert body['registry_config']['row_label'] == 'club'
        assert body['registry_config']['claim_mode'] == 'first_come_first_served'
        assert body['registry_config']['max_delegates_per_row'] == 2

    def test_session_token_is_valid_jwt(self, setup_tables):
        """Session token is a valid JWT with expected claims."""
        events_table, handler = setup_tables
        _seed_event(events_table)

        event = _make_event(event_id=TEST_EVENT_ID, body={'password': TEST_PASSWORD})
        response = handler.lambda_handler(event, None)
        body = json.loads(response['body'])

        token = body['session_token']
        secret = f"test-secret-base:{TEST_EVENT_ID}"
        payload = jwt.decode(token, secret, algorithms=['HS256'])

        assert payload['event_id'] == TEST_EVENT_ID
        assert 'verified_at' in payload
        assert 'exp' in payload
        # Token should expire in 15 minutes (±5 seconds for test timing)
        expected_exp = payload['verified_at'] + (15 * 60)
        assert abs(payload['exp'] - expected_exp) <= 5

    def test_no_info_leak_same_response_structure(self, setup_tables):
        """Non-existent event and wrong password produce identical response structure."""
        events_table, handler = setup_tables
        _seed_event(events_table)

        # Wrong password response
        event_wrong = _make_event(event_id=TEST_EVENT_ID, body={'password': TEST_WRONG_PASSWORD})
        response_wrong = handler.lambda_handler(event_wrong, None)
        body_wrong = json.loads(response_wrong['body'])

        # Non-existent event response
        event_missing = _make_event(event_id='nonexistent', body={'password': TEST_PASSWORD})
        response_missing = handler.lambda_handler(event_missing, None)
        body_missing = json.loads(response_missing['body'])

        # Both should have identical structure
        assert response_wrong['statusCode'] == response_missing['statusCode']
        assert set(body_wrong.keys()) == set(body_missing.keys())
        assert body_wrong == {'valid': False}
        assert body_missing == {'valid': False}

    def test_72_byte_truncation(self, setup_tables):
        """Passwords differing only after byte 72 produce identical verification results."""
        events_table, handler = setup_tables

        # Create a password that's exactly 72 bytes in UTF-8
        base_password = 'A' * 72
        long_password_a = base_password + 'EXTRA_SUFFIX_A'
        long_password_b = base_password + 'EXTRA_SUFFIX_B'

        # Seed with the base password (only first 72 bytes matter)
        _seed_event(events_table, password=base_password)

        # Both long passwords should verify successfully
        event_a = _make_event(event_id=TEST_EVENT_ID, body={'password': long_password_a})
        response_a = handler.lambda_handler(event_a, None)
        body_a = json.loads(response_a['body'])

        event_b = _make_event(event_id=TEST_EVENT_ID, body={'password': long_password_b})
        response_b = handler.lambda_handler(event_b, None)
        body_b = json.loads(response_b['body'])

        assert body_a['valid'] is True
        assert body_b['valid'] is True

    def test_empty_body_returns_400(self, setup_tables):
        """Returns 400 when body is empty or unparseable."""
        _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID)
        event['body'] = ''
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_invalid_json_body_returns_400(self, setup_tables):
        """Returns 400 when body is not valid JSON."""
        _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID)
        event['body'] = 'not-json'
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400
