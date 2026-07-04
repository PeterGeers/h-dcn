"""
Unit tests for get_event_registry handler.

Tests the registry merge, email masking, sorting, and auth logic.
"""

import json
import os
import sys
import importlib.util
import time
import pytest
import boto3
import jwt
from moto import mock_aws
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Set environment variables before importing
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-registry-bucket'
os.environ['JWT_SECRET_BASE'] = 'test-secret-key'

# Handler file path
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_event_registry', 'app.py')
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


def _create_session_token(event_id: str, secret: str = 'test-secret-key', expired: bool = False) -> str:
    """Create a valid session token for testing. Uses jwt.encode like verify_event_password."""
    exp = int(time.time()) - 100 if expired else int(time.time()) + 900
    payload = {
        'event_id': event_id,
        'verified_at': int(time.time()),
        'exp': exp,
        'iat': int(time.time()),
    }
    # Per-event secret: base_secret:event_id (matches handler's _get_event_signing_secret)
    per_event_secret = f"{secret}:{event_id}"
    return jwt.encode(payload, per_event_secret, algorithm='HS256')


def _make_event(event_id: str, headers: dict = None, path_params: dict = None):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': 'GET',
        'headers': headers or {},
        'pathParameters': path_params or {'event_id': event_id},
        'queryStringParameters': None,
        'body': None,
    }


SAMPLE_REGISTRY_JSON = json.dumps({
    'version': '1.0',
    'updated_at': '2026-01-01T00:00:00Z',
    'rows': [
        {'row_id': 'club-1', 'label': 'Zwolle Chapter', 'logo_url': 'https://example.com/zwolle.png', 'allowed_emails': [], 'max_delegates': 2, 'metadata': {}},
        {'row_id': 'club-2', 'label': 'Amsterdam Chapter', 'logo_url': None, 'allowed_emails': ['alice@example.com'], 'max_delegates': 2, 'metadata': {}},
        {'row_id': 'club-3', 'label': 'Breda Chapter', 'logo_url': 'https://example.com/breda.png', 'allowed_emails': [], 'max_delegates': 1, 'metadata': {}},
    ]
})

SAMPLE_CLAIMS = {
    'club-1': {
        'member_id': 'member-1',
        'email': 'hans@example.com',
        'name': 'Hans de Vries',
        'claimed_at': '2026-01-15T10:00:00Z',
    }
}

SAMPLE_EVENT = {
    'event_id': 'evt-001',
    'name': 'Test Event',
    'registry_config': {
        's3_path': 'events/evt-001/invitee_registry.json',
        'row_label': 'club',
        'claim_mode': 'first_come_first_served',
        'max_delegates_per_row': 2,
    },
    'registry_claims': SAMPLE_CLAIMS,
}


@pytest.fixture
def setup_mocked_aws():
    """Set up mock AWS resources (DynamoDB + S3) and load the handler."""
    with mock_aws():
        # Create Events table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create S3 bucket and upload registry
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='test-registry-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        s3.put_object(
            Bucket='test-registry-bucket',
            Key='events/evt-001/invitee_registry.json',
            Body=SAMPLE_REGISTRY_JSON.encode('utf-8'),
        )

        # Insert event record
        events_table.put_item(Item=SAMPLE_EVENT)

        # Insert member record (for Cognito auth path)
        members_table.put_item(Item={
            'member_id': 'member-1',
            'email': 'hans@example.com',
            'name': 'Hans de Vries',
            'allowed_events': ['evt-001'],
        })

        # Load handler inside mock context
        handler = _load_handler()
        yield handler, events_table, members_table, s3


class TestGetEventRegistry:
    """Tests for the get_event_registry handler."""

    def test_options_request(self, setup_mocked_aws):
        """OPTIONS requests should return 200 with CORS headers."""
        handler, *_ = setup_mocked_aws
        event = {'httpMethod': 'OPTIONS', 'headers': {}, 'pathParameters': {}}
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_missing_event_id(self, setup_mocked_aws):
        """Should return 400 if event_id is missing."""
        handler, *_ = setup_mocked_aws
        event = _make_event('', headers={'X-Session-Token': _create_session_token('evt-001')})
        event['pathParameters'] = {}
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_valid_session_token_returns_registry(self, setup_mocked_aws):
        """Valid session token should grant access and return merged registry."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['row_label'] == 'club'
        assert body['claim_mode'] == 'first_come_first_served'
        assert len(body['rows']) == 3

    def test_expired_session_token_rejected(self, setup_mocked_aws):
        """Expired session token should be rejected."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001', expired=True)
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_wrong_event_id_in_token_rejected(self, setup_mocked_aws):
        """Session token with wrong event_id should be rejected."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-999')  # wrong event_id
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_rows_sorted_alphabetically_case_insensitive(self, setup_mocked_aws):
        """Rows should be sorted alphabetically case-insensitive by label."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        labels = [row['label'] for row in body['rows']]
        # Amsterdam, Breda, Zwolle (alphabetical)
        assert labels == ['Amsterdam Chapter', 'Breda Chapter', 'Zwolle Chapter']

    def test_claimed_row_marked_unavailable(self, setup_mocked_aws):
        """Claimed rows should have available=False and masked email."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        # Find Zwolle Chapter (club-1, claimed)
        zwolle = next(r for r in body['rows'] if r['row_id'] == 'club-1')
        assert zwolle['available'] is False
        assert zwolle['claimed_contact'] == 'ha***@example.com'

    def test_unclaimed_row_marked_available(self, setup_mocked_aws):
        """Unclaimed rows should have available=True and no claimed_contact."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        amsterdam = next(r for r in body['rows'] if r['row_id'] == 'club-2')
        assert amsterdam['available'] is True
        assert amsterdam['claimed_contact'] is None

    def test_email_masking(self, setup_mocked_aws):
        """Email masking should show first 2 chars + *** + @domain."""
        handler, *_ = setup_mocked_aws
        # Test via the mask_email function directly
        assert handler.mask_email('hans@example.com') == 'ha***@example.com'
        assert handler.mask_email('alice.bob@domain.nl') == 'al***@domain.nl'
        assert handler.mask_email('a@short.io') == 'a***@short.io'
        assert handler.mask_email('') == '***@unknown'

    def test_email_restricted_mode_includes_allowed_emails(self, setup_mocked_aws):
        """In email_restricted mode, rows should include allowed_emails."""
        handler, events_table, _, _ = setup_mocked_aws

        # Update event to email_restricted mode
        events_table.update_item(
            Key={'event_id': 'evt-001'},
            UpdateExpression='SET registry_config.claim_mode = :mode',
            ExpressionAttributeValues={':mode': 'email_restricted'},
        )

        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert body['claim_mode'] == 'email_restricted'
        amsterdam = next(r for r in body['rows'] if r['row_id'] == 'club-2')
        assert 'allowed_emails' in amsterdam
        assert amsterdam['allowed_emails'] == ['alice@example.com']

    def test_first_come_mode_excludes_allowed_emails(self, setup_mocked_aws):
        """In first_come_first_served mode, rows should NOT include allowed_emails."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-001')
        event = _make_event('evt-001', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        amsterdam = next(r for r in body['rows'] if r['row_id'] == 'club-2')
        assert 'allowed_emails' not in amsterdam

    def test_event_not_found(self, setup_mocked_aws):
        """Should return 404 for non-existent event."""
        handler, *_ = setup_mocked_aws
        token = _create_session_token('evt-999')
        event = _make_event('evt-999', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 404

    def test_no_registry_configured(self, setup_mocked_aws):
        """Should return 404 if registry_config has no s3_path."""
        handler, events_table, _, _ = setup_mocked_aws

        # Add an event without s3_path
        events_table.put_item(Item={
            'event_id': 'evt-no-reg',
            'name': 'No Registry Event',
            'registry_config': {'row_label': 'team', 'claim_mode': 'first_come_first_served'},
            'registry_claims': {},
        })

        token = _create_session_token('evt-no-reg')
        event = _make_event('evt-no-reg', headers={'X-Session-Token': token})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 404

    def test_authenticated_user_with_event_access(self, setup_mocked_aws):
        """Authenticated users with event in allowed_events should have access."""
        handler, *_ = setup_mocked_aws

        # Simulate Cognito auth via patching extract_user_credentials
        with patch.object(handler, 'extract_user_credentials', return_value=('hans@example.com', ['event_participant'], None)):
            event = _make_event('evt-001', headers={
                'Authorization': 'Bearer fake.jwt.token',
            })
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_no_auth_returns_401(self, setup_mocked_aws):
        """Request without session token or valid auth should return 401."""
        handler, *_ = setup_mocked_aws
        event = _make_event('evt-001', headers={})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 401
