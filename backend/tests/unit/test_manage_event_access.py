"""
Unit Tests for manage_event_access Lambda Handler.

Tests the admin event access management endpoints:
- POST /admin/events/{event_id}/access  → grant or revoke event access
- GET  /admin/events/{event_id}/access  → list members with access

Test cases:
- POST grant: adds event_id to allowed_events
- POST grant bulk: works with multiple member_ids
- POST revoke: removes event_id from allowed_events
- POST: returns 403 for non-admin
- POST: returns 400 for invalid action
- GET: returns list of members with access
- GET: returns empty list when no members have access
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'manage_event_access', 'app.py')
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

TEST_EVENT_ID = 'evt-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
TEST_ADMIN_EMAIL = 'admin@h-dcn.nl'
TEST_NON_ADMIN_EMAIL = 'user@h-dcn.nl'


def _make_post_event(event_id, action, member_ids):
    """Create API Gateway event for POST /admin/events/{event_id}/access."""
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': {'event_id': event_id},
        'body': json.dumps({'action': action, 'member_ids': member_ids}),
    }


def _make_get_event(event_id):
    """Create API Gateway event for GET /admin/events/{event_id}/access."""
    return {
        'httpMethod': 'GET',
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': {'event_id': event_id},
        'body': None,
    }


# ---------------------------------------------------------------------------
# Auth patches
# ---------------------------------------------------------------------------

def _admin_auth_patches():
    """Return patch.multiple for admin user (events_crud permission)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_ADMIN_EMAIL, ['hdcnLeden', 'Events_CRUD', 'System_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_admin_auth_patches():
    """Return patch.multiple for non-admin user (no events_crud or system_crud)."""
    def _validate_no_admin(roles, perms, email, region):
        if 'events_crud' in perms or 'system_crud' in perms:
            return (False, {'statusCode': 403, 'body': json.dumps({'error': 'Access denied'})}, {})
        return (True, None, {})

    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_NON_ADMIN_EMAIL, ['hdcnLeden'], None),
        validate_permissions_with_regions=_validate_no_admin,
        log_successful_access=lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'members': members_table,
            'handler': handler,
        }


# ---------------------------------------------------------------------------
# Helper to seed members
# ---------------------------------------------------------------------------

def _seed_member(members_table, member_id, email='test@example.com',
                 member_type='hdcn_member', club_id=None, allowed_events=None):
    """Seed a member into the Members table."""
    item = {
        'member_id': member_id,
        'email': email,
        'member_type': member_type,
        'allowed_events': allowed_events or [],
    }
    if club_id:
        item['club_id'] = club_id
    members_table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Tests: Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    """Tests for admin permission check."""

    def test_post_returns_403_when_user_is_not_admin(self, setup_tables):
        """Non-admin users cannot manage event access."""
        handler = setup_tables['handler']

        with _non_admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'denied' in body.get('error', '').lower() or 'admin' in body.get('error', '').lower()

    def test_get_returns_403_when_user_is_not_admin(self, setup_tables):
        """Non-admin users cannot list event access."""
        handler = setup_tables['handler']

        with _non_admin_auth_patches():
            event = _make_get_event(TEST_EVENT_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403


# ---------------------------------------------------------------------------
# Tests: POST grant
# ---------------------------------------------------------------------------

class TestGrantAccess:
    """Tests for granting event access."""

    def test_grant_adds_event_id_to_allowed_events(self, setup_tables):
        """Grant adds event_id to member's allowed_events."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        _seed_member(members_table, 'mem-001', email='alice@example.com')

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 1
        assert body['results'][0]['member_id'] == 'mem-001'
        assert body['results'][0]['status'] == 'ok'

        # Verify in DynamoDB
        db_member = members_table.get_item(Key={'member_id': 'mem-001'})['Item']
        assert TEST_EVENT_ID in db_member['allowed_events']

    def test_grant_bulk_works_with_multiple_member_ids(self, setup_tables):
        """Grant works with multiple member_ids in one request."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        _seed_member(members_table, 'mem-001', email='alice@example.com')
        _seed_member(members_table, 'mem-002', email='bob@example.com')
        _seed_member(members_table, 'mem-003', email='charlie@example.com')

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', ['mem-001', 'mem-002', 'mem-003'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['processed'] == 3
        assert all(r['status'] == 'ok' for r in body['results'])

        # Verify all have access
        for mid in ['mem-001', 'mem-002', 'mem-003']:
            db_member = members_table.get_item(Key={'member_id': mid})['Item']
            assert TEST_EVENT_ID in db_member['allowed_events']

    def test_grant_is_idempotent(self, setup_tables):
        """Granting access to a member who already has it returns ok."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        _seed_member(members_table, 'mem-001', email='alice@example.com',
                     allowed_events=[TEST_EVENT_ID])

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['status'] == 'ok'
        assert 'already' in body['results'][0]['message'].lower()

        # Verify no duplicate
        db_member = members_table.get_item(Key={'member_id': 'mem-001'})['Item']
        assert db_member['allowed_events'].count(TEST_EVENT_ID) == 1

    def test_grant_returns_error_for_nonexistent_member(self, setup_tables):
        """Grant returns error result for a member_id that doesn't exist."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', ['nonexistent-member'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['status'] == 'error'
        assert 'not found' in body['results'][0]['message'].lower()


# ---------------------------------------------------------------------------
# Tests: POST revoke
# ---------------------------------------------------------------------------

class TestRevokeAccess:
    """Tests for revoking event access."""

    def test_revoke_removes_event_id_from_allowed_events(self, setup_tables):
        """Revoke removes event_id from member's allowed_events."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        _seed_member(members_table, 'mem-001', email='alice@example.com',
                     allowed_events=[TEST_EVENT_ID, 'other-event-id'])

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'revoke', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['status'] == 'ok'
        assert 'revoked' in body['results'][0]['message'].lower()

        # Verify in DynamoDB
        db_member = members_table.get_item(Key={'member_id': 'mem-001'})['Item']
        assert TEST_EVENT_ID not in db_member['allowed_events']
        assert 'other-event-id' in db_member['allowed_events']

    def test_revoke_is_idempotent(self, setup_tables):
        """Revoking access from a member who doesn't have it returns ok."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        _seed_member(members_table, 'mem-001', email='alice@example.com',
                     allowed_events=['other-event-id'])

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'revoke', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['status'] == 'ok'
        assert 'did not have' in body['results'][0]['message'].lower()

    def test_revoke_returns_error_for_nonexistent_member(self, setup_tables):
        """Revoke returns error result for a member_id that doesn't exist."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'revoke', ['nonexistent-member'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['results'][0]['status'] == 'error'
        assert 'not found' in body['results'][0]['message'].lower()


# ---------------------------------------------------------------------------
# Tests: POST validation
# ---------------------------------------------------------------------------

class TestPostValidation:
    """Tests for POST request validation."""

    def test_returns_400_for_invalid_action(self, setup_tables):
        """POST with action other than grant/revoke returns 400."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'invalid_action', ['mem-001'])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'action' in body.get('error', '').lower()

    def test_returns_400_for_empty_member_ids(self, setup_tables):
        """POST with empty member_ids list returns 400."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = _make_post_event(TEST_EVENT_ID, 'grant', [])
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'member_ids' in body.get('error', '').lower()

    def test_returns_400_for_invalid_json_body(self, setup_tables):
        """POST with invalid JSON body returns 400."""
        handler = setup_tables['handler']

        with _admin_auth_patches():
            event = {
                'httpMethod': 'POST',
                'headers': {'Authorization': 'Bearer test-token'},
                'queryStringParameters': None,
                'pathParameters': {'event_id': TEST_EVENT_ID},
                'body': 'not-valid-json{{{',
            }
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'json' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: GET list members with access
# ---------------------------------------------------------------------------

class TestListMembersWithAccess:
    """Tests for GET endpoint — listing members with access."""

    def test_returns_members_with_access(self, setup_tables):
        """GET returns list of members whose allowed_events contains event_id."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']

        _seed_member(members_table, 'mem-001', email='alice@example.com',
                     member_type='hdcn_member', club_id='club-A',
                     allowed_events=[TEST_EVENT_ID])
        _seed_member(members_table, 'mem-002', email='bob@example.com',
                     member_type='event_participant', club_id='club-B',
                     allowed_events=[TEST_EVENT_ID, 'other-event'])
        _seed_member(members_table, 'mem-003', email='charlie@example.com',
                     member_type='hdcn_member',
                     allowed_events=['other-event-only'])

        with _admin_auth_patches():
            event = _make_get_event(TEST_EVENT_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['event_id'] == TEST_EVENT_ID
        assert len(body['members']) == 2

        member_ids = [m['member_id'] for m in body['members']]
        assert 'mem-001' in member_ids
        assert 'mem-002' in member_ids
        assert 'mem-003' not in member_ids

    def test_returns_empty_list_when_no_members_have_access(self, setup_tables):
        """GET returns empty members list when no one has access."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']

        _seed_member(members_table, 'mem-001', email='alice@example.com',
                     allowed_events=['different-event-id'])

        with _admin_auth_patches():
            event = _make_get_event(TEST_EVENT_ID)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['event_id'] == TEST_EVENT_ID
        assert body['members'] == []


# ---------------------------------------------------------------------------
# Tests: OPTIONS preflight
# ---------------------------------------------------------------------------

class TestCORS:
    """Tests for CORS preflight handling."""

    def test_options_request_returns_200(self, setup_tables):
        """OPTIONS request returns 200 for CORS preflight."""
        handler = setup_tables['handler']
        response = handler.lambda_handler(
            {'httpMethod': 'OPTIONS', 'headers': {}, 'body': None},
            None
        )
        assert response['statusCode'] == 200
