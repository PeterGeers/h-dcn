"""
Unit Tests for manage_delegates Lambda Handler.

Tests the delegate management endpoint:
- POST /booking/{id}/delegates
- DELETE /booking/{id}/delegates

Test cases:
- Returns 400 when order is not club-scoped (no delegates field)
- Returns 403 when requester is not primary delegate or admin
- Successfully adds secondary delegate
- Successfully removes secondary delegate
- Returns 400 when target member doesn't exist
- Returns 400 when target member has different club_id
- Invite: validates email, rejects self-invitation, enforces max_delegates_per_row
- Invite: stores pending_secondary_email lowercased
- Revoke: only allowed when order status is draft
- Revoke: clears pending invitation or linked secondary
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
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['EVENTS_TABLE_NAME'] = 'Events'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'manage_delegates', 'app.py')
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

TEST_PRIMARY_MEMBER_ID = 'mem-primary-001'
TEST_SECONDARY_MEMBER_ID = 'mem-secondary-002'
TEST_TARGET_MEMBER_ID = 'mem-target-003'
TEST_OTHER_CLUB_MEMBER_ID = 'mem-other-club-004'
TEST_ADMIN_EMAIL = 'admin@h-dcn.nl'
TEST_PRIMARY_EMAIL = 'primary@h-dcn.nl'
TEST_NON_DELEGATE_EMAIL = 'outsider@h-dcn.nl'
TEST_CLUB_ID = 'club-abc-123'
TEST_ORDER_ID = 'order-001'
TEST_EVENT_ID = 'evt-test-event-uuid'
TEST_INVITE_EMAIL = 'invited@example.com'


def _make_event(order_id=TEST_ORDER_ID, body=None, method='POST'):
    """Create API Gateway event for POST /booking/{id}/delegates."""
    return {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': None,
        'pathParameters': {'id': order_id} if order_id else None,
        'body': json.dumps(body) if body else None,
    }


# ---------------------------------------------------------------------------
# Auth patches
# ---------------------------------------------------------------------------

def _primary_delegate_auth():
    """Return patch.multiple for primary delegate user."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_PRIMARY_EMAIL, ['hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (
            (False, {'statusCode': 403, 'body': json.dumps({'error': 'Access denied'})}, {})
            if 'events_crud' in perms
            else (True, None, {})
        ),
        log_successful_access=lambda *a, **kw: None,
    )


def _admin_auth():
    """Return patch.multiple for admin user (events_crud permission)."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_ADMIN_EMAIL, ['hdcnLeden', 'Events_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_delegate_auth():
    """Return patch.multiple for a user who is neither primary delegate nor admin."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (TEST_NON_DELEGATE_EMAIL, ['hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (
            (False, {'statusCode': 403, 'body': json.dumps({'error': 'Access denied'})}, {})
            if 'events_crud' in perms
            else (True, None, {})
        ),
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

        # Orders table
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
                {'AttributeName': 'source_id', 'AttributeType': 'S'},
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'event-member-index',
                    'KeySchema': [
                        {'AttributeName': 'source_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'member_id', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed event with registry_config
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Test Event',
            'registry_config': {
                'max_delegates_per_row': 2,
                'row_label': 'club',
                'claim_mode': 'first_come_first_served',
            },
        })

        # Seed members
        members_table.put_item(Item={
            'member_id': TEST_PRIMARY_MEMBER_ID,
            'email': TEST_PRIMARY_EMAIL,
            'club_id': TEST_CLUB_ID,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID, 'evt-member-event-uuid'],
        })
        members_table.put_item(Item={
            'member_id': TEST_TARGET_MEMBER_ID,
            'email': 'target@h-dcn.nl',
            'club_id': TEST_CLUB_ID,
            'registry_row_id': TEST_CLUB_ID,
            'member_type': 'hdcn_member',
            'allowed_events': [],
        })
        members_table.put_item(Item={
            'member_id': TEST_OTHER_CLUB_MEMBER_ID,
            'email': 'otherclub@h-dcn.nl',
            'club_id': 'club-different-999',
            'registry_row_id': 'club-different-999',
            'member_type': 'hdcn_member',
            'allowed_events': [],
        })
        members_table.put_item(Item={
            'member_id': 'mem-non-delegate-005',
            'email': TEST_NON_DELEGATE_EMAIL,
            'club_id': TEST_CLUB_ID,
            'member_type': 'hdcn_member',
            'allowed_events': [],
        })
        members_table.put_item(Item={
            'member_id': 'mem-admin-006',
            'email': TEST_ADMIN_EMAIL,
            'club_id': TEST_CLUB_ID,
            'member_type': 'hdcn_member',
            'allowed_events': [],
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'members': members_table,
            'events': events_table,
            'handler': handler,
        }


def _seed_club_order(orders_table, order_id=TEST_ORDER_ID, primary_member_id=TEST_PRIMARY_MEMBER_ID,
                     secondary_member_id=None, club_id=TEST_CLUB_ID, status='draft',
                     pending_secondary_email=None):
    """Seed a club-scoped order with delegates."""
    delegates = {
        'primary_member_id': primary_member_id,
        'primary': TEST_PRIMARY_EMAIL,
    }
    if secondary_member_id:
        delegates['secondary_member_id'] = secondary_member_id
        delegates['secondary'] = 'secondary@h-dcn.nl'
    if pending_secondary_email:
        delegates['pending_secondary_email'] = pending_secondary_email

    orders_table.put_item(Item={
        'order_id': order_id,
        'source_id': TEST_EVENT_ID,
        'event_id': TEST_EVENT_ID,
        'member_id': primary_member_id,
        'club_id': club_id,
        'registry_row_id': club_id,
        'status': status,
        'items': [],
        'delegates': delegates,
        'version': 1,
        'created_at': '2025-01-10T08:00:00+00:00',
        'updated_at': '2025-01-15T10:30:00+00:00',
    })


def _seed_member_order(orders_table, order_id='order-member-001'):
    """Seed a member-scoped order (no delegates field)."""
    orders_table.put_item(Item={
        'order_id': order_id,
        'source_id': 'evt-member-event-uuid',
        'member_id': TEST_PRIMARY_MEMBER_ID,
        'status': 'draft',
        'items': [],
        'version': 1,
        'created_at': '2025-01-10T08:00:00+00:00',
        'updated_at': '2025-01-15T10:30:00+00:00',
    })


# ---------------------------------------------------------------------------
# Tests: Order not club-scoped
# ---------------------------------------------------------------------------

class TestNotClubScoped:
    """Tests that non-club-scoped orders cannot use delegate management."""

    def test_returns_400_when_order_has_no_delegates(self, setup_tables):
        """Member-scoped order (no delegates field) returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_member_order(orders_table, order_id='order-member-001')

        with _primary_delegate_auth():
            event = _make_event(
                order_id='order-member-001',
                body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID}
            )
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'row-scoped' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    """Tests for delegate management access control."""

    def test_returns_403_when_requester_is_not_primary_or_admin(self, setup_tables):
        """Non-primary, non-admin user cannot manage delegates (Req 16.5, 16.7)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _non_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        # May return "Insufficient event access" (Req 16.7) or "primary delegate" depending on
        # whether the user fails event access check first or delegate check.
        error_msg = body.get('error', '').lower()
        assert ('primary delegate' in error_msg or 'admin' in error_msg
                or 'insufficient event access' in error_msg)

    def test_admin_can_manage_delegates(self, setup_tables):
        """Admin (events_crud) can manage delegates even if not primary."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _admin_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['delegates']['secondary_member_id'] == TEST_TARGET_MEMBER_ID


# ---------------------------------------------------------------------------
# Tests: Add secondary delegate
# ---------------------------------------------------------------------------

class TestAddDelegate:
    """Tests for adding a secondary delegate."""

    def test_successfully_adds_secondary_delegate(self, setup_tables):
        """Primary delegate can add a secondary delegate from the same club."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['delegates']['secondary_member_id'] == TEST_TARGET_MEMBER_ID
        assert 'added' in body['message'].lower()

    def test_returns_400_when_target_member_not_found(self, setup_tables):
        """Cannot add a member that doesn't exist."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': 'nonexistent-member-id'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'not found' in body.get('error', '').lower()

    def test_returns_400_when_target_member_has_different_club(self, setup_tables):
        """Cannot add a member from a different club."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_OTHER_CLUB_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'registry row' in body.get('error', '').lower()

    def test_returns_400_when_adding_primary_as_secondary(self, setup_tables):
        """Cannot add the primary delegate as secondary."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_PRIMARY_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'primary' in body.get('error', '').lower()

    def test_returns_400_when_target_already_secondary(self, setup_tables):
        """Cannot add a member who is already the secondary delegate."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, secondary_member_id=TEST_TARGET_MEMBER_ID)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'already' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Remove secondary delegate
# ---------------------------------------------------------------------------

class TestRemoveDelegate:
    """Tests for removing a secondary delegate."""

    def test_successfully_removes_secondary_delegate(self, setup_tables):
        """Primary delegate can remove the secondary delegate."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, secondary_member_id=TEST_SECONDARY_MEMBER_ID)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'remove'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'secondary_member_id' not in body['order'].get('delegates', {})
        assert 'removed' in body['message'].lower()

    def test_returns_400_when_no_secondary_to_remove(self, setup_tables):
        """Cannot remove secondary when none exists."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)  # no secondary

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'remove'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no secondary' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Tests for request body validation."""

    def test_invalid_action_returns_400(self, setup_tables):
        """Invalid action value returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invalid_action', 'member_id': 'x'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'action' in body.get('error', '').lower()

    def test_add_without_member_id_returns_400(self, setup_tables):
        """Add action without member_id returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'member_id' in body.get('error', '').lower()

    def test_invalid_json_returns_400(self, setup_tables):
        """Invalid JSON body returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = {
                'httpMethod': 'POST',
                'headers': {'Authorization': 'Bearer test-token'},
                'queryStringParameters': None,
                'pathParameters': {'id': TEST_ORDER_ID},
                'body': 'not valid json {{{',
            }
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'json' in body.get('error', '').lower()

    def test_order_not_found_returns_404(self, setup_tables):
        """Non-existent order returns 404."""
        handler = setup_tables['handler']

        with _primary_delegate_auth():
            event = _make_event(
                order_id='nonexistent-order',
                body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID}
            )
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 404


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


# ---------------------------------------------------------------------------
# Tests: Invite secondary delegate (Req 5.1, 5.2, 5.3)
# ---------------------------------------------------------------------------

class TestInviteDelegate:
    """Tests for inviting a secondary delegate by email."""

    def test_invite_stores_pending_email_lowercased(self, setup_tables):
        """Invite action stores pending_secondary_email lowercased (Req 5.3)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': 'Invited@Example.COM'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        delegates = body['order']['delegates']
        assert delegates['pending_secondary_email'] == 'invited@example.com'

    def test_invite_rejects_self_invitation(self, setup_tables):
        """Self-invitation is rejected (Req 5.2)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_PRIMARY_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'self-invitation' in body.get('error', '').lower()

    def test_invite_rejects_self_invitation_case_insensitive(self, setup_tables):
        """Self-invitation check is case-insensitive."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': 'PRIMARY@H-DCN.NL'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'self-invitation' in body.get('error', '').lower()

    def test_invite_rejects_invalid_email(self, setup_tables):
        """Invalid email format returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': 'not-an-email'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'email' in body.get('error', '').lower()

    def test_invite_rejects_empty_email(self, setup_tables):
        """Empty email returns 400."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': ''})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400

    def test_invite_enforces_max_delegates_per_row(self, setup_tables):
        """Cannot invite when max_delegates_per_row is already reached (Req 5.1)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        events_table = setup_tables['events']

        # Set max_delegates_per_row to 1 (only primary allowed)
        events_table.update_item(
            Key={'event_id': TEST_EVENT_ID},
            UpdateExpression='SET registry_config.max_delegates_per_row = :val',
            ExpressionAttributeValues={':val': 1},
        )

        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_INVITE_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'maximum' in body.get('error', '').lower()

    def test_invite_allowed_within_limit(self, setup_tables):
        """Invite succeeds when within max_delegates_per_row limit (Req 5.1)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        events_table = setup_tables['events']

        # Set max_delegates_per_row to 3 (plenty of room)
        events_table.update_item(
            Key={'event_id': TEST_EVENT_ID},
            UpdateExpression='SET registry_config.max_delegates_per_row = :val',
            ExpressionAttributeValues={':val': 3},
        )

        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_INVITE_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_invite_rejects_when_secondary_already_linked(self, setup_tables):
        """Cannot invite when a secondary delegate is already linked."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, secondary_member_id=TEST_SECONDARY_MEMBER_ID)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_INVITE_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'already linked' in body.get('error', '').lower()

    def test_invite_rejects_when_invitation_already_pending(self, setup_tables):
        """Cannot invite when a pending invitation already exists."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, pending_secondary_email='other@example.com')

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_INVITE_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'pending' in body.get('error', '').lower()

    def test_invite_increments_version(self, setup_tables):
        """Invite action increments the order version."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'invite', 'email': TEST_INVITE_EMAIL})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['version'] == 2


# ---------------------------------------------------------------------------
# Tests: Revoke delegation (Req 5.7)
# ---------------------------------------------------------------------------

class TestRevokeDelegate:
    """Tests for revoking a pending invitation or removing a linked secondary."""

    def test_revoke_clears_pending_invitation(self, setup_tables):
        """Revoke action clears pending_secondary_email in draft status (Req 5.7)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, pending_secondary_email='pending@example.com')

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        delegates = body['order']['delegates']
        assert 'pending_secondary_email' not in delegates
        assert 'pending' in body['message'].lower() or 'revoked' in body['message'].lower()

    def test_revoke_removes_linked_secondary_delegate(self, setup_tables):
        """Revoke action removes linked secondary delegate in draft status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, secondary_member_id=TEST_SECONDARY_MEMBER_ID)

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        delegates = body['order']['delegates']
        assert 'secondary_member_id' not in delegates
        assert 'secondary' not in delegates

    def test_revoke_rejected_in_submitted_status(self, setup_tables):
        """Revoke is rejected when order is not in draft status (Req 5.7)."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(
            orders_table,
            status='submitted',
            pending_secondary_email='pending@example.com'
        )

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'draft' in body.get('error', '').lower()

    def test_revoke_rejected_in_locked_status(self, setup_tables):
        """Revoke is rejected when order is locked."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(
            orders_table,
            status='locked',
            secondary_member_id=TEST_SECONDARY_MEMBER_ID,
        )

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'draft' in body.get('error', '').lower()

    def test_revoke_returns_400_when_nothing_to_revoke(self, setup_tables):
        """Revoke returns 400 when no secondary delegate or pending invitation exists."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table)  # No secondary, no pending

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'no secondary' in body.get('error', '').lower() or 'no' in body.get('error', '').lower()

    def test_revoke_increments_version(self, setup_tables):
        """Revoke action increments the order version."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, pending_secondary_email='pending@example.com')

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'revoke'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['version'] == 2


# ---------------------------------------------------------------------------
# Tests: DELETE method (alternative to revoke)
# ---------------------------------------------------------------------------

class TestDeleteMethod:
    """Tests for DELETE /booking/{id}/delegates endpoint."""

    def test_delete_method_revokes_pending_invitation(self, setup_tables):
        """DELETE method revokes a pending invitation in draft status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, pending_secondary_email='pending@example.com')

        with _primary_delegate_auth():
            event = _make_event(body=None, method='DELETE')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'pending_secondary_email' not in body['order']['delegates']

    def test_delete_method_rejected_when_not_draft(self, setup_tables):
        """DELETE method is rejected when order is not in draft status."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(
            orders_table,
            status='submitted',
            secondary_member_id=TEST_SECONDARY_MEMBER_ID,
        )

        with _primary_delegate_auth():
            event = _make_event(body=None, method='DELETE')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400

    def test_delete_method_requires_authorization(self, setup_tables):
        """DELETE method requires primary delegate or admin."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        _seed_club_order(orders_table, pending_secondary_email='pending@example.com')

        with _non_delegate_auth():
            event = _make_event(body=None, method='DELETE')
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403


# ---------------------------------------------------------------------------
# Tests: Registry Row — delegate registry_row_id mismatch rejection
# Requirements: 2.5
# ---------------------------------------------------------------------------

class TestRegistryRowMismatch:
    """Tests for delegate assignment validation with registry_row_id."""

    def test_delegate_mismatch_returns_403_with_error_code(self, setup_tables):
        """
        When target member's registry_row_id differs from order's registry_row_id,
        the assignment is rejected with 403 and error_code DELEGATE_ROW_MISMATCH.
        Validates: Requirements 2.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        members_table = setup_tables['members']

        # Seed order with registry_row_id
        orders_table.put_item(Item={
            'order_id': TEST_ORDER_ID,
            'source_id': TEST_EVENT_ID,
            'event_id': TEST_EVENT_ID,
            'member_id': TEST_PRIMARY_MEMBER_ID,
            'registry_row_id': 'row-amsterdam',
            'status': 'draft',
            'items': [],
            'delegates': {
                'primary_member_id': TEST_PRIMARY_MEMBER_ID,
                'primary': TEST_PRIMARY_EMAIL,
            },
            'version': 1,
        })

        # Create target member with DIFFERENT registry_row_id
        mismatch_member_id = 'mem-mismatch-999'
        members_table.put_item(Item={
            'member_id': mismatch_member_id,
            'email': 'mismatch@h-dcn.nl',
            'registry_row_id': 'row-rotterdam',
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
        })

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': mismatch_member_id})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body.get('error_code') == 'DELEGATE_ROW_MISMATCH'
        assert 'registry row' in body.get('error', '').lower()

    def test_delegate_same_registry_row_succeeds(self, setup_tables):
        """
        When target member's registry_row_id matches order's registry_row_id,
        delegate assignment succeeds.
        Validates: Requirements 2.5
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']
        members_table = setup_tables['members']

        # Seed order with registry_row_id
        orders_table.put_item(Item={
            'order_id': TEST_ORDER_ID,
            'source_id': TEST_EVENT_ID,
            'event_id': TEST_EVENT_ID,
            'member_id': TEST_PRIMARY_MEMBER_ID,
            'registry_row_id': TEST_CLUB_ID,
            'status': 'draft',
            'items': [],
            'delegates': {
                'primary_member_id': TEST_PRIMARY_MEMBER_ID,
                'primary': TEST_PRIMARY_EMAIL,
            },
            'version': 1,
        })

        # Target member with same registry_row_id
        target_member_id = 'mem-same-row-777'
        members_table.put_item(Item={
            'member_id': target_member_id,
            'email': 'samerow@h-dcn.nl',
            'registry_row_id': TEST_CLUB_ID,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
        })

        with _primary_delegate_auth():
            event = _make_event(body={'action': 'add', 'member_id': target_member_id})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order']['delegates']['secondary_member_id'] == target_member_id

    def test_delegate_no_registry_row_on_order_skips_check(self, setup_tables):
        """
        When order has no registry_row_id (member-scoped), the mismatch check
        is skipped and the old club_id check applies instead.
        """
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed a club-scoped order WITHOUT registry_row_id (uses club_id)
        _seed_club_order(orders_table)

        with _primary_delegate_auth():
            # Target member has the same club_id (TEST_CLUB_ID)
            event = _make_event(body={'action': 'add', 'member_id': TEST_TARGET_MEMBER_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
