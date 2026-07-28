"""
Unit tests for the bulk_transition_members handler.

Tests:
- Bulk success (all members transition successfully)
- Partial failure (one member in wrong state for transition)
- Batch size limit exceeded (>25) → 400
- Non-existent member in batch → that member fails, others still processed
- Empty member_ids array → 400
- Missing event field → 400
"""

import json
import os
import sys
import importlib.util
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

# Set environment before importing handler
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['COGNITO_USER_POOL_ID'] = 'eu-west-1_test123'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'bulk_transition_members', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']

    # Remove stale shared.* modules
    stale_keys = [k for k in sys.modules if k.startswith('shared.')]
    for key in stale_keys:
        del sys.modules[key]

    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event(body: dict) -> dict:
    """Create a mock API Gateway event for POST /members/bulk-transition."""
    return {
        'httpMethod': 'POST',
        'body': json.dumps(body),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Members_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'},
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Members_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _create_members_table(dynamodb):
    """Create a mocked Members DynamoDB table."""
    return dynamodb.create_table(
        TableName='Members',
        KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


def _register_mock_actions(handler_module):
    """Register mock actions with the handler's dispatcher for testing.

    The real actions interact with Cognito/SES/DynamoDB in complex ways.
    For handler-level tests we override with simple no-ops.
    """
    dispatcher = handler_module.dispatcher
    for action_name in [
        'activate_member', 'deactivate_member', 'suspend_member',
        'flag_welcome_pack', 'mark_invoice_paid', 'audit_log',
        'send_application_received', 'send_payment_request',
        'send_welcome_email', 'send_cancellation_email',
        'send_suspension_notice', 'notify_admin',
    ]:
        dispatcher.register(action_name, lambda ctx: None)


@pytest.fixture
def setup_handler():
    """Fixture that creates DynamoDB table and loads the handler inside mock_aws."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = _create_members_table(dynamodb)
        handler_module = _load_handler()
        # Point handler's table reference to the mocked table
        handler_module.table = table
        _register_mock_actions(handler_module)
        yield table, handler_module


class TestBulkSuccess:
    """Test that all members in a batch transition successfully."""

    def test_all_members_approve_success(self, setup_handler):
        """3 members all in wachtRegio, APPROVE → all succeed with new_status=wachtBetaling."""
        table, handler = setup_handler

        # Create 3 members in wachtRegio (pending) state with regio assigned
        for i in range(1, 4):
            table.put_item(Item={
                'member_id': f'member-{i:03d}',
                'status': 'wachtRegio',
                'voornaam': f'Member{i}',
                'achternaam': 'Test',
                'email': f'member{i}@example.nl',
                'regio': '1',
            })

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': ['member-001', 'member-002', 'member-003'],
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['total'] == 3
        assert body['succeeded'] == 3
        assert body['failed'] == 0

        # Verify each result
        for result in body['results']:
            assert result['success'] is True
            assert result['new_status'] == 'wachtBetaling'

        # Verify DynamoDB was updated for all members
        for i in range(1, 4):
            item = table.get_item(Key={'member_id': f'member-{i:03d}'})['Item']
            assert item['status'] == 'wachtBetaling'
            assert 'status_history' in item
            assert item['status_history'][0]['event'] == 'APPROVE'


class TestPartialFailure:
    """Test that one failure does not stop the rest of the batch."""

    def test_one_member_in_wrong_state_others_succeed(self, setup_handler):
        """3 members, one in wrong state for APPROVE → 2 succeed, 1 fails."""
        table, handler = setup_handler

        # Two members in wachtRegio (can be APPROVE'd)
        table.put_item(Item={
            'member_id': 'member-001',
            'status': 'wachtRegio',
            'voornaam': 'Jan',
            'achternaam': 'Test',
            'email': 'jan@example.nl',
            'regio': '1',
        })
        table.put_item(Item={
            'member_id': 'member-002',
            'status': 'wachtRegio',
            'voornaam': 'Piet',
            'achternaam': 'Test',
            'email': 'piet@example.nl',
            'regio': '2',
        })
        # Third member already Actief (cannot be APPROVE'd)
        table.put_item(Item={
            'member_id': 'member-003',
            'status': 'Actief',
            'voornaam': 'Kees',
            'achternaam': 'Test',
            'email': 'kees@example.nl',
            'regio': '3',
        })

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': ['member-001', 'member-002', 'member-003'],
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['total'] == 3
        assert body['succeeded'] == 2
        assert body['failed'] == 1

        # Check individual results
        results_by_id = {r['member_id']: r for r in body['results']}
        assert results_by_id['member-001']['success'] is True
        assert results_by_id['member-001']['new_status'] == 'wachtBetaling'
        assert results_by_id['member-002']['success'] is True
        assert results_by_id['member-002']['new_status'] == 'wachtBetaling'
        assert results_by_id['member-003']['success'] is False
        assert 'error' in results_by_id['member-003']


class TestBatchSizeLimit:
    """Test that batch size is enforced at max 25 members."""

    def test_exceeds_batch_size_returns_400(self, setup_handler):
        """Batch with >25 member IDs → 400 error."""
        table, handler = setup_handler

        # Create a batch of 26 member IDs
        member_ids = [f'member-{i:03d}' for i in range(1, 27)]

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': member_ids,
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert '25' in body['error']

    def test_exactly_25_members_allowed(self, setup_handler):
        """Batch with exactly 25 members should be accepted (not rejected)."""
        table, handler = setup_handler

        # Create 25 members in wachtRegio
        member_ids = []
        for i in range(1, 26):
            mid = f'member-{i:03d}'
            member_ids.append(mid)
            table.put_item(Item={
                'member_id': mid,
                'status': 'wachtRegio',
                'voornaam': f'Member{i}',
                'achternaam': 'Test',
                'email': f'member{i}@example.nl',
                'regio': '1',
            })

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': member_ids,
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['total'] == 25
        assert body['succeeded'] == 25


class TestNonExistentMember:
    """Test that a non-existent member fails without blocking others."""

    def test_nonexistent_member_fails_others_succeed(self, setup_handler):
        """One member doesn't exist in DB → fails, other members still processed."""
        table, handler = setup_handler

        # Two valid members
        table.put_item(Item={
            'member_id': 'member-001',
            'status': 'wachtRegio',
            'voornaam': 'Jan',
            'achternaam': 'Test',
            'email': 'jan@example.nl',
            'regio': '1',
        })
        table.put_item(Item={
            'member_id': 'member-002',
            'status': 'wachtRegio',
            'voornaam': 'Piet',
            'achternaam': 'Test',
            'email': 'piet@example.nl',
            'regio': '2',
        })
        # member-003 does NOT exist in the database

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': ['member-001', 'member-002', 'member-003'],
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['total'] == 3
        assert body['succeeded'] == 2
        assert body['failed'] == 1

        # Check that the non-existent member has appropriate error
        results_by_id = {r['member_id']: r for r in body['results']}
        assert results_by_id['member-001']['success'] is True
        assert results_by_id['member-002']['success'] is True
        assert results_by_id['member-003']['success'] is False
        assert 'not found' in results_by_id['member-003']['error'].lower()


class TestRequestValidation:
    """Test request body validation edge cases."""

    def test_empty_member_ids_returns_400(self, setup_handler):
        """Empty member_ids array → 400 error."""
        table, handler = setup_handler

        event = _make_event({
            'event': 'APPROVE',
            'member_ids': [],
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

    def test_missing_event_field_returns_400(self, setup_handler):
        """Request without 'event' field → 400 error."""
        table, handler = setup_handler

        event = _make_event({
            'member_ids': ['member-001', 'member-002'],
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'event' in body['error'].lower()

    def test_missing_member_ids_field_returns_400(self, setup_handler):
        """Request without 'member_ids' field → 400 error."""
        table, handler = setup_handler

        event = _make_event({
            'event': 'APPROVE',
            'context': {},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
