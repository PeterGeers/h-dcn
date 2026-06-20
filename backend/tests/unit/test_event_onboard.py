"""
Unit Tests for event_onboard Lambda Handler.

Tests the atomic onboarding endpoint:
- Session token validation (expired, wrong event_id, invalid)
- Email_restricted mode: email not authorized → 403
- User already holds a claim → 409
- Row already claimed → 409 with masked contact
- Successful onboard for new user (Cognito + Member + claim)
- Successful onboard for existing user (append event access)
- Rollback: Cognito creation fails → claim released
- Rollback: Member creation fails → Cognito user deleted + claim released
- Pending delegate auto-linking

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 16.3, 16.4, 16.6
"""

import importlib.util
import json
import os
import sys
import time
import uuid
from unittest.mock import patch, MagicMock

import boto3
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
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-bucket'
os.environ['JWT_SECRET_BASE'] = 'test-secret-base'
os.environ['COGNITO_USER_POOL_ID'] = 'eu-west-1_testPool'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'event_onboard', 'app.py')
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

TEST_EVENT_ID = 'evt-onboard-1234-5678-abcd'
TEST_ROW_ID = 'club-amsterdam'
TEST_EMAIL = 'hans@example.com'
TEST_NAME = 'Hans de Vries'
TEST_PASSWORD = 'Welkom2027!'


def _generate_session_token(event_id: str = TEST_EVENT_ID, expired: bool = False) -> str:
    """Generate a test session token."""
    now = int(time.time())
    payload = {
        'event_id': event_id,
        'verified_at': now,
        'exp': now - 100 if expired else now + 900,
        'iat': now,
    }
    secret = f"test-secret-base:{event_id}"
    return jwt.encode(payload, secret, algorithm='HS256')


def _make_event(event_id=TEST_EVENT_ID, method='POST', body=None):
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': None,
        'pathParameters': {'event_id': event_id} if event_id else None,
        'body': json.dumps(body) if body else None,
    }


def _default_body(**overrides):
    """Create a default onboard request body."""
    body = {
        'row_id': TEST_ROW_ID,
        'email': TEST_EMAIL,
        'name': TEST_NAME,
        'password': TEST_PASSWORD,
        'session_token': _generate_session_token(),
    }
    body.update(overrides)
    return body


REGISTRY_JSON = json.dumps({
    'version': '1.0',
    'updated_at': '2027-01-01T00:00:00Z',
    'rows': [
        {
            'row_id': 'club-amsterdam',
            'label': 'Amsterdam',
            'allowed_emails': ['hans@example.com', 'piet@example.com'],
            'max_delegates': 2,
            'logo_url': None,
            'metadata': {},
        },
        {
            'row_id': 'club-rotterdam',
            'label': 'Rotterdam',
            'allowed_emails': ['jan@example.com'],
            'max_delegates': 2,
            'logo_url': None,
            'metadata': {},
        },
    ],
}).encode('utf-8')


def _seed_event(events_table, event_id=TEST_EVENT_ID, claim_mode='first_come_first_served',
                registry_claims=None):
    """Seed an event record."""
    item = {
        'event_id': event_id,
        'name': 'Presidents Meeting 2027',
        'event_type': 'presmeet',
        'status': 'open',
        'registry_config': {
            'row_label': 'club',
            'claim_mode': claim_mode,
            's3_path': f'events/{event_id}/registry.json',
            'max_delegates_per_row': 2,
        },
        'registry_claims': registry_claims or {},
    }
    events_table.put_item(Item=item)
    return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and S3, load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create S3 bucket with registry
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        s3.put_object(
            Bucket='test-bucket',
            Key=f'events/{TEST_EVENT_ID}/registry.json',
            Body=REGISTRY_JSON,
        )

        handler_module = _load_handler()
        yield events_table, members_table, orders_table, handler_module


# ---------------------------------------------------------------------------
# Helper to mock Cognito (not covered by moto's mock_aws for all operations)
# ---------------------------------------------------------------------------

def _cognito_patches(user_exists=False, create_fails=False):
    """Patch Cognito operations on the handler module."""
    existing_user = {
        'Username': TEST_EMAIL.lower(),
        'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL.lower()}],
    } if user_exists else None

    def mock_get_cognito_user(email):
        return existing_user

    def mock_create_cognito_user(email, name, password):
        if create_fails:
            return None, "Cognito creation failed"
        return email.lower(), None

    def mock_delete_cognito_user(username):
        pass

    def mock_add_user_to_group(username, group_name):
        pass

    return patch.multiple(
        'app',
        get_cognito_user=mock_get_cognito_user,
        create_cognito_user=mock_create_cognito_user,
        delete_cognito_user=mock_delete_cognito_user,
        add_user_to_group=mock_add_user_to_group,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEventOnboardValidation:
    """Tests for request validation and session token."""

    def test_options_request(self, setup_tables):
        """CORS preflight returns 200."""
        _, _, _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID, method='OPTIONS')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_method_not_allowed(self, setup_tables):
        """Non-POST methods return 405."""
        _, _, _, handler = setup_tables
        event = _make_event(event_id=TEST_EVENT_ID, method='GET')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 405

    def test_missing_event_id(self, setup_tables):
        """Returns 400 when event_id is missing."""
        _, _, _, handler = setup_tables
        event = _make_event(event_id=None, body=_default_body())
        event['pathParameters'] = None
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_missing_row_id(self, setup_tables):
        """Returns 400 when row_id is missing."""
        _, _, _, handler = setup_tables
        event = _make_event(body=_default_body(row_id=''))
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_missing_email(self, setup_tables):
        """Returns 400 when email is missing or invalid."""
        _, _, _, handler = setup_tables
        event = _make_event(body=_default_body(email='not-an-email'))
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_missing_name(self, setup_tables):
        """Returns 400 when name is missing or whitespace-only."""
        _, _, _, handler = setup_tables
        event = _make_event(body=_default_body(name='   '))
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_expired_session_token(self, setup_tables):
        """Returns 401 for expired session token."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body(session_token=_generate_session_token(expired=True))
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401
        body_resp = json.loads(response['body'])
        assert 'expired' in body_resp['error'].lower()

    def test_wrong_event_id_in_token(self, setup_tables):
        """Returns 401 when token event_id doesn't match path event_id."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        wrong_token = _generate_session_token(event_id='different-event')
        body = _default_body(session_token=wrong_token)
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_invalid_session_token(self, setup_tables):
        """Returns 401 for totally invalid token."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body(session_token='not-a-real-token')
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401


class TestEmailRestricted:
    """Tests for email_restricted claim mode."""

    def test_email_not_authorized_returns_403(self, setup_tables):
        """Returns 403 when email is not in row's allowed_emails."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table, claim_mode='email_restricted')

        # Use an email NOT in allowed_emails for club-amsterdam
        body = _default_body(email='unauthorized@example.com')
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 403
        resp_body = json.loads(response['body'])
        assert 'not authorized' in resp_body['error'].lower()

    def test_email_authorized_case_insensitive(self, setup_tables):
        """Email matching is case-insensitive in email_restricted mode."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table, claim_mode='email_restricted')

        # Use uppercase variant of allowed email
        body = _default_body(email='HANS@EXAMPLE.COM')
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        # Should succeed (200), not 403
        assert response['statusCode'] == 200

    def test_first_come_first_served_skips_email_check(self, setup_tables):
        """In first_come_first_served mode, any email can claim any row."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table, claim_mode='first_come_first_served')

        body = _default_body(email='anyone@example.com')
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestClaimConflicts:
    """Tests for claim conflict scenarios."""

    def test_user_already_holds_claim_returns_409(self, setup_tables):
        """Returns 409 when user already holds a claim for this event."""
        events_table, _, _, handler = setup_tables
        # User already has a claim on club-rotterdam
        _seed_event(events_table, registry_claims={
            'club-rotterdam': {
                'member_id': 'existing-member',
                'email': TEST_EMAIL.lower(),
                'name': TEST_NAME,
                'claimed_at': '2027-01-01T00:00:00Z',
            }
        })

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 409
        resp_body = json.loads(response['body'])
        assert 'already' in resp_body['error'].lower()

    def test_row_already_claimed_returns_409_with_masked_contact(self, setup_tables):
        """Returns 409 with masked contact when row is claimed by another user."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table, registry_claims={
            'club-amsterdam': {
                'member_id': 'other-member',
                'email': 'piet@example.com',
                'name': 'Piet Jansen',
                'claimed_at': '2027-01-01T00:00:00Z',
            }
        })

        body = _default_body(email='newuser@example.com')
        event = _make_event(body=body)
        with _cognito_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 409
        resp_body = json.loads(response['body'])
        assert 'pi***@example.com' in resp_body['error']


class TestSuccessfulOnboard:
    """Tests for successful onboarding flows."""

    def test_new_user_onboard_creates_member(self, setup_tables):
        """Successful onboard for new user creates Member record."""
        events_table, members_table, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches(user_exists=False):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        resp_body = json.loads(response['body'])
        assert resp_body['is_new_user'] is True
        assert 'member_id' in resp_body
        assert resp_body['message'] == 'Successfully onboarded'

        # Verify member was created
        member_id = resp_body['member_id']
        member_resp = members_table.get_item(Key={'member_id': member_id})
        assert 'Item' in member_resp
        member = member_resp['Item']
        assert member['email'] == TEST_EMAIL.lower()
        assert member['name'] == TEST_NAME
        assert member['member_type'] == TEST_EVENT_ID
        assert member['club_id'] == TEST_ROW_ID
        assert TEST_EVENT_ID in member['allowed_events']

    def test_new_user_onboard_creates_claim(self, setup_tables):
        """Successful onboard creates a claim in registry_claims."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches(user_exists=False):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify claim was created
        event_resp = events_table.get_item(Key={'event_id': TEST_EVENT_ID})
        claims = event_resp['Item'].get('registry_claims', {})
        assert TEST_ROW_ID in claims
        claim = claims[TEST_ROW_ID]
        assert claim['email'] == TEST_EMAIL.lower()
        assert claim['name'] == TEST_NAME
        assert 'claimed_at' in claim
        assert 'member_id' in claim

    def test_existing_user_appends_event_access(self, setup_tables):
        """Existing user gets event_id appended to allowed_events."""
        events_table, members_table, _, handler = setup_tables
        _seed_event(events_table)

        # Pre-create member with different event
        existing_member_id = 'existing-member-123'
        members_table.put_item(Item={
            'member_id': existing_member_id,
            'email': TEST_EMAIL.lower(),
            'name': TEST_NAME,
            'member_type': 'other-event',
            'club_id': 'other-club',
            'allowed_events': ['other-event-id'],
        })

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches(user_exists=True):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        resp_body = json.loads(response['body'])
        assert resp_body['is_new_user'] is False
        assert resp_body['member_id'] == existing_member_id

        # Verify event was appended
        member_resp = members_table.get_item(Key={'member_id': existing_member_id})
        member = member_resp['Item']
        assert TEST_EVENT_ID in member['allowed_events']
        # Original fields should remain unchanged
        assert member['member_type'] == 'other-event'
        assert member['club_id'] == 'other-club'

    def test_new_user_without_password_returns_400(self, setup_tables):
        """New user without password returns 400 and releases claim."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body()
        del body['password']
        event = _make_event(body=body)
        with _cognito_patches(user_exists=False):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'password' in resp_body['error'].lower()

        # Verify claim was released (rollback)
        event_resp = events_table.get_item(Key={'event_id': TEST_EVENT_ID})
        claims = event_resp['Item'].get('registry_claims', {})
        assert TEST_ROW_ID not in claims


class TestRollback:
    """Tests for rollback scenarios."""

    def test_cognito_fails_releases_claim(self, setup_tables):
        """If Cognito creation fails, claim is released."""
        events_table, _, _, handler = setup_tables
        _seed_event(events_table)

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches(user_exists=False, create_fails=True):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 500

        # Verify claim was released
        event_resp = events_table.get_item(Key={'event_id': TEST_EVENT_ID})
        claims = event_resp['Item'].get('registry_claims', {})
        assert TEST_ROW_ID not in claims

    def test_member_creation_fails_deletes_cognito_and_releases_claim(self, setup_tables):
        """If Member creation fails, Cognito user is deleted and claim released."""
        events_table, members_table, _, handler = setup_tables
        _seed_event(events_table)

        delete_called = []

        def mock_delete(username):
            delete_called.append(username)

        def mock_create_member_record(member_id, email, name, event_id, row_id):
            return False, "Simulated member creation failure"

        body = _default_body()
        event = _make_event(body=body)
        with patch.multiple(
            'app',
            get_cognito_user=lambda email: None,
            create_cognito_user=lambda email, name, password: (email.lower(), None),
            delete_cognito_user=mock_delete,
            add_user_to_group=lambda username, group: None,
            create_member_record=mock_create_member_record,
        ):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 500

        # Verify Cognito user was deleted (rollback)
        assert len(delete_called) == 1
        assert delete_called[0] == TEST_EMAIL.lower()

        # Verify claim was released
        event_resp = events_table.get_item(Key={'event_id': TEST_EVENT_ID})
        claims = event_resp['Item'].get('registry_claims', {})
        assert TEST_ROW_ID not in claims


class TestDelegateAutoLink:
    """Tests for pending delegate auto-linking."""

    def test_auto_links_pending_delegate(self, setup_tables):
        """Onboard auto-links pending delegate invitation matching by email."""
        events_table, _, orders_table, handler = setup_tables
        _seed_event(events_table)

        # Create an order with a pending invitation for this user
        orders_table.put_item(Item={
            'order_id': 'order-pending-123',
            'event_id': TEST_EVENT_ID,
            'club_id': 'club-rotterdam',
            'status': 'draft',
            'delegates': {
                'primary': 'jan@example.com',
                'primary_member_id': 'jan-member-id',
                'secondary': None,
                'secondary_member_id': None,
                'pending_secondary_email': TEST_EMAIL.lower(),
            },
        })

        body = _default_body()
        event = _make_event(body=body)
        with _cognito_patches(user_exists=False):
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify delegate was linked
        order_resp = orders_table.get_item(Key={'order_id': 'order-pending-123'})
        order = order_resp['Item']
        assert order['delegates']['secondary'] == TEST_EMAIL.lower()
        assert order['delegates']['secondary_member_id'] is not None
        # pending should be cleared (set to None)
        assert order['delegates']['pending_secondary_email'] is None
