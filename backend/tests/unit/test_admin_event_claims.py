"""
Unit tests for admin_event_claims handler.

Tests cover:
- GET: list all claims with pagination
- DELETE: release a claim (keeps order)
- POST assign: manually assign a row
- POST reassign_primary: reassign primary delegate
- POST remove_secondary: remove secondary delegate
- POST cancel_invitation: cancel pending invitation
- Auth: only admin roles allowed
- Error cases: row not found, already claimed, etc.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
"""

import importlib.util
import json
import os
import sys
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws

# Environment setup (before handler import)
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-bucket'

_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_event_claims', 'app.py')
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


def _auth_patches():
    """Patch auth utilities for admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD', 'Regio_All'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_admin_patches():
    """Patch auth utilities for non-admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@test.nl', ['hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


REGISTRY_JSON = json.dumps({
    'version': '1.0',
    'updated_at': '2025-01-01T00:00:00Z',
    'rows': [
        {'row_id': 'club-a', 'label': 'Club Alpha', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'club-b', 'label': 'Club Beta', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'club-c', 'label': 'Club Charlie', 'allowed_emails': [], 'logo_url': None},
    ],
}).encode('utf-8')


@pytest.fixture
def setup_tables():
    """Create DynamoDB tables and S3 bucket under moto, load handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        s3_client = boto3.client('s3', region_name='eu-west-1')

        # Create Events table
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

        # Create Orders table
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create S3 bucket with registry
        s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        s3_client.put_object(
            Bucket='test-bucket',
            Key='events/test-event/invitee_registry.json',
            Body=REGISTRY_JSON,
        )

        # Seed event record
        events_table.put_item(Item={
            'event_id': 'test-event',
            'name': 'Test Event',
            'registry_config': {
                's3_path': 'events/test-event/invitee_registry.json',
                'row_label': 'club',
                'claim_mode': 'first_come_first_served',
                'max_delegates_per_row': 2,
            },
            'registry_claims': {
                'club-a': {
                    'member_id': 'member-1',
                    'email': 'alice@club-a.nl',
                    'name': 'Alice',
                    'claimed_at': '2025-01-15T10:00:00Z',
                },
            },
        })

        # Seed member
        members_table.put_item(Item={
            'member_id': 'member-2',
            'email': 'bob@club-b.nl',
            'name': 'Bob Builder',
            'allowed_events': ['test-event'],
        })

        # Seed an order for club-a
        orders_table.put_item(Item={
            'order_id': 'order-1',
            'event_id': 'test-event',
            'club_id': 'club-a',
            'member_id': 'member-1',
            'user_email': 'alice@club-a.nl',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'delegates': {
                'primary': 'alice@club-a.nl',
                'primary_member_id': 'member-1',
                'secondary': 'helper@club-a.nl',
                'secondary_member_id': 'member-helper',
                'pending_secondary_email': None,
            },
            'items': [],
            'total_amount': Decimal('100'),
            'total_paid': Decimal('0'),
            'version': 1,
        })

        handler = _load_handler()
        yield events_table, members_table, orders_table, handler


def _make_event(method, event_id='test-event', row_id=None, body=None, page=None):
    """Build a minimal API Gateway event."""
    path_params = {'event_id': event_id}
    if row_id:
        path_params['row_id'] = row_id

    query_params = {}
    if page:
        query_params['page'] = str(page)

    return {
        'httpMethod': method,
        'pathParameters': path_params,
        'queryStringParameters': query_params or None,
        'body': json.dumps(body) if body else None,
    }


# --- GET: List Claims ---

class TestListClaims:
    def test_list_claims_returns_all_rows(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('GET'), None)
            body = json.loads(result['body'])

            assert result['statusCode'] == 200
            claims = body['claims']
            assert len(claims) == 3  # All 3 rows from S3 registry

            # Should be sorted alphabetically
            assert claims[0]['label'] == 'Club Alpha'
            assert claims[1]['label'] == 'Club Beta'
            assert claims[2]['label'] == 'Club Charlie'

    def test_list_claims_shows_claim_status(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('GET'), None)
            body = json.loads(result['body'])
            claims = body['claims']

            # club-a is claimed
            alpha = next(c for c in claims if c['row_id'] == 'club-a')
            assert alpha['status'] == 'claimed'
            assert alpha['delegate_name'] == 'Alice'
            assert alpha['delegate_email'] == 'alice@club-a.nl'
            assert alpha['claimed_at'] == '2025-01-15T10:00:00Z'

            # club-b and club-c are available
            beta = next(c for c in claims if c['row_id'] == 'club-b')
            assert beta['status'] == 'available'
            assert 'delegate_name' not in beta

    def test_list_claims_pagination(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('GET', page=1), None)
            body = json.loads(result['body'])
            pagination = body['pagination']

            assert pagination['page'] == 1
            assert pagination['page_size'] == 50
            assert pagination['total_items'] == 3
            assert pagination['total_pages'] == 1

    def test_list_claims_returns_row_label(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('GET'), None)
            body = json.loads(result['body'])
            assert body['row_label'] == 'club'

    def test_list_claims_non_admin_forbidden(self, setup_tables):
        _, _, _, handler = setup_tables
        with _non_admin_patches():
            result = handler.lambda_handler(_make_event('GET'), None)
            assert result['statusCode'] == 403


# --- DELETE: Release Claim ---

class TestReleaseClaim:
    def test_release_claim_removes_from_registry(self, setup_tables):
        events_table, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('DELETE', row_id='club-a'), None)
            assert result['statusCode'] == 200

            # Verify claim is removed from DynamoDB
            response = events_table.get_item(Key={'event_id': 'test-event'})
            claims = response['Item']['registry_claims']
            assert 'club-a' not in claims

    def test_release_claim_keeps_order(self, setup_tables):
        _, _, orders_table, handler = setup_tables
        with _auth_patches():
            handler.lambda_handler(_make_event('DELETE', row_id='club-a'), None)

            # Order should still exist
            response = orders_table.get_item(Key={'order_id': 'order-1'})
            assert 'Item' in response
            assert response['Item']['status'] == 'submitted'

    def test_release_unclaimed_row_returns_404(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('DELETE', row_id='club-b'), None)
            assert result['statusCode'] == 404

    def test_release_missing_row_id_returns_400(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('DELETE'), None)
            assert result['statusCode'] == 400


# --- POST: Manual Assign ---

class TestManualAssign:
    def test_assign_row_creates_claim_and_order(self, setup_tables):
        events_table, _, orders_table, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-b', body={'email': 'bob@club-b.nl'}),
                None,
            )
            body = json.loads(result['body'])

            assert result['statusCode'] == 200
            assert body['member_id'] == 'member-2'
            assert body['order_id'] is not None

            # Verify claim in DynamoDB
            response = events_table.get_item(Key={'event_id': 'test-event'})
            claims = response['Item']['registry_claims']
            assert 'club-b' in claims
            assert claims['club-b']['email'] == 'bob@club-b.nl'
            assert claims['club-b']['name'] == 'Bob Builder'

            # Verify order was created
            order_response = orders_table.get_item(Key={'order_id': body['order_id']})
            order = order_response['Item']
            assert order['status'] == 'draft'
            assert order['club_id'] == 'club-b'
            assert order['event_id'] == 'test-event'

    def test_assign_already_claimed_returns_409(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'email': 'bob@club-b.nl'}),
                None,
            )
            assert result['statusCode'] == 409
            body = json.loads(result['body'])
            # Should contain current claimant info
            assert 'current_claimant' in str(body) or 'already claimed' in str(body).lower()

    def test_assign_nonexistent_member_returns_404(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-b', body={'email': 'nobody@nowhere.nl'}),
                None,
            )
            assert result['statusCode'] == 404

    def test_assign_invalid_email_returns_400(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-b', body={'email': 'not-an-email'}),
                None,
            )
            assert result['statusCode'] == 400


# --- POST: Reassign Primary ---

class TestReassignPrimary:
    def test_reassign_primary_updates_order_and_claim(self, setup_tables):
        events_table, members_table, orders_table, handler = setup_tables

        # Add a second member to reassign to
        members_table.put_item(Item={
            'member_id': 'member-3',
            'email': 'charlie@club-a.nl',
            'name': 'Charlie',
        })

        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={
                    'action': 'reassign_primary',
                    'email': 'charlie@club-a.nl',
                }),
                None,
            )
            assert result['statusCode'] == 200

            # Check order updated
            response = orders_table.get_item(Key={'order_id': 'order-1'})
            order = response['Item']
            assert order['delegates']['primary'] == 'charlie@club-a.nl'
            assert order['delegates']['primary_member_id'] == 'member-3'
            assert order['member_id'] == 'member-3'

            # Check claim updated
            response = events_table.get_item(Key={'event_id': 'test-event'})
            claim = response['Item']['registry_claims']['club-a']
            assert claim['email'] == 'charlie@club-a.nl'
            assert claim['member_id'] == 'member-3'


# --- POST: Remove Secondary ---

class TestRemoveSecondary:
    def test_remove_secondary_clears_delegate(self, setup_tables):
        _, _, orders_table, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'action': 'remove_secondary'}),
                None,
            )
            assert result['statusCode'] == 200

            # Check order updated
            response = orders_table.get_item(Key={'order_id': 'order-1'})
            order = response['Item']
            assert order['delegates']['secondary'] is None
            assert order['delegates']['secondary_member_id'] is None

    def test_remove_secondary_no_secondary_returns_400(self, setup_tables):
        _, _, orders_table, handler = setup_tables
        # First remove the secondary so it's empty
        orders_table.update_item(
            Key={'order_id': 'order-1'},
            UpdateExpression='SET delegates.secondary = :null, delegates.secondary_member_id = :null',
            ExpressionAttributeValues={':null': None},
        )
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'action': 'remove_secondary'}),
                None,
            )
            assert result['statusCode'] == 400


# --- POST: Cancel Invitation ---

class TestCancelInvitation:
    def test_cancel_invitation_clears_pending_email(self, setup_tables):
        _, _, orders_table, handler = setup_tables
        # Set a pending invitation
        orders_table.update_item(
            Key={'order_id': 'order-1'},
            UpdateExpression='SET delegates.pending_secondary_email = :email',
            ExpressionAttributeValues={':email': 'pending@test.nl'},
        )
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'action': 'cancel_invitation'}),
                None,
            )
            assert result['statusCode'] == 200

            response = orders_table.get_item(Key={'order_id': 'order-1'})
            order = response['Item']
            assert order['delegates']['pending_secondary_email'] is None

    def test_cancel_invitation_no_pending_returns_400(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'action': 'cancel_invitation'}),
                None,
            )
            assert result['statusCode'] == 400


# --- Auth Tests ---

class TestAuth:
    def test_non_admin_gets_403(self, setup_tables):
        _, _, _, handler = setup_tables
        with _non_admin_patches():
            result = handler.lambda_handler(_make_event('GET'), None)
            assert result['statusCode'] == 403

    def test_options_returns_cors(self, setup_tables):
        _, _, _, handler = setup_tables
        result = handler.lambda_handler({'httpMethod': 'OPTIONS'}, None)
        assert result['statusCode'] == 200


# --- Edge Cases ---

class TestEdgeCases:
    def test_nonexistent_event_returns_404(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('GET', event_id='no-such-event'), None)
            assert result['statusCode'] == 404

    def test_unsupported_method_returns_405(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(_make_event('PUT', row_id='club-a'), None)
            assert result['statusCode'] == 405

    def test_unknown_action_returns_400(self, setup_tables):
        _, _, _, handler = setup_tables
        with _auth_patches():
            result = handler.lambda_handler(
                _make_event('POST', row_id='club-a', body={'action': 'invalid'}),
                None,
            )
            assert result['statusCode'] == 400
