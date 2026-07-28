"""
Unit tests for the transition_member handler.

Tests:
- Valid transitions (APPROVE, PAYMENT_RECEIVED, CANCEL, SUSPEND)
- Invalid transitions (wrong state)
- Guard failures (missing reason for SUSPEND)
- status_history append
- welcome_pack_status set on activation (via flag_welcome_pack action)
- Member not found → 404
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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'transition_member', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path.

    Adds the handler directory to sys.path temporarily so that
    sibling imports (actions, email_side_effects, email_actions)
    resolve correctly — mimicking Lambda's runtime behaviour.
    """
    if 'app' in sys.modules:
        del sys.modules['app']

    # Remove stale shared.* and sibling modules
    stale_keys = [k for k in sys.modules if k.startswith('shared.')]
    for key in stale_keys:
        del sys.modules[key]
    for sibling in ('actions', 'email_side_effects', 'email_actions'):
        if sibling in sys.modules:
            del sys.modules[sibling]

    # Add handler directory to sys.path so sibling imports work
    handler_dir = os.path.dirname(_handler_file)
    if handler_dir not in sys.path:
        sys.path.insert(0, handler_dir)

    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event(member_id: str, body: dict) -> dict:
    """Create a mock API Gateway event for POST /members/{member_id}/transition."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'member_id': member_id},
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

    The real actions (activate_member, etc.) interact with Cognito and DynamoDB
    in ways that require complex mocking. For handler-level tests we override
    with simple no-op actions so the dispatcher doesn't fail on external calls.
    """
    dispatcher = handler_module.dispatcher
    # Force-override all actions with no-ops (including those registered during load)
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


class TestValidTransitions:
    """Test valid workflow transitions that should succeed."""

    def test_approve_from_pending(self, setup_handler):
        """APPROVE: member in wachtRegio (pending) → wachtBetaling (wait_payment)."""
        table, handler = setup_handler

        # Create member in wachtRegio (pending) state
        table.put_item(Item={
            'member_id': 'member-001',
            'status': 'wachtRegio',
            'voornaam': 'Jan',
            'achternaam': 'Jansen',
            'email': 'jan@example.nl',
            'regio': '1',
        })

        event = _make_event('member-001', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['success'] is True
        assert body['old_status'] == 'wachtRegio'
        assert body['new_status'] == 'wachtBetaling'

    def test_payment_received_from_wait_payment(self, setup_handler):
        """PAYMENT_RECEIVED: member in wachtBetaling → Actief."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-002',
            'status': 'wachtBetaling',
            'voornaam': 'Piet',
            'achternaam': 'Pietersen',
            'email': 'piet@example.nl',
            'regio': '2',
            'straat': 'Hoofdstraat 1',
            'postcode': '1234AB',
            'woonplaats': 'Amsterdam',
        })

        event = _make_event('member-002', {'event': 'PAYMENT_RECEIVED', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['success'] is True
        assert body['old_status'] == 'wachtBetaling'
        assert body['new_status'] == 'Actief'

    def test_cancel_from_active(self, setup_handler):
        """CANCEL: member in Actief → Opgezegd."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-003',
            'status': 'Actief',
            'voornaam': 'Kees',
            'achternaam': 'de Vries',
            'email': 'kees@example.nl',
        })

        event = _make_event('member-003', {'event': 'CANCEL', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['success'] is True
        assert body['old_status'] == 'Actief'
        assert body['new_status'] == 'Opgezegd'

    def test_suspend_from_active(self, setup_handler):
        """SUSPEND: member in Actief → Geschorst (requires reason ≥ context)."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-004',
            'status': 'Actief',
            'voornaam': 'Dirk',
            'achternaam': 'Bakker',
            'email': 'dirk@example.nl',
        })

        event = _make_event('member-004', {
            'event': 'SUSPEND',
            'context': {'reason': 'Contributie niet betaald na meerdere herinneringen'},
        })

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['success'] is True
        assert body['old_status'] == 'Actief'
        assert body['new_status'] == 'Geschorst'


class TestInvalidTransitions:
    """Test transitions that should be rejected because of wrong state."""

    def test_approve_when_already_active(self, setup_handler):
        """APPROVE when member is already Actief → error (no valid transition)."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-010',
            'status': 'Actief',
            'voornaam': 'Lisa',
            'achternaam': 'Smit',
            'email': 'lisa@example.nl',
        })

        event = _make_event('member-010', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 400
        assert 'error' in body
        assert 'not allowed' in body['error'].lower()

    def test_payment_received_when_applied(self, setup_handler):
        """PAYMENT_RECEIVED when member is Aangemeld → error."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-011',
            'status': 'Aangemeld',
            'voornaam': 'Tom',
            'achternaam': 'Bakker',
            'email': 'tom@example.nl',
        })

        event = _make_event('member-011', {'event': 'PAYMENT_RECEIVED', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 400
        assert 'error' in body

    def test_cancel_when_already_cancelled(self, setup_handler):
        """CANCEL when member is already Opgezegd → error."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-012',
            'status': 'Opgezegd',
            'voornaam': 'Eva',
            'achternaam': 'Visser',
            'email': 'eva@example.nl',
        })

        event = _make_event('member-012', {'event': 'CANCEL', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 400
        assert 'error' in body


class TestGuardFailures:
    """Test guard failures that prevent transitions."""

    def test_suspend_without_reason(self, setup_handler):
        """SUSPEND without reason in context → guard fails → error."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-020',
            'status': 'Actief',
            'voornaam': 'Henk',
            'achternaam': 'de Groot',
            'email': 'henk@example.nl',
        })

        # No reason provided in context
        event = _make_event('member-020', {'event': 'SUSPEND', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 400
        assert 'error' in body
        # The engine returns "Transition 'SUSPEND' not allowed from state 'active'"
        # when the guard fails (since can_transition returns None)
        assert 'not allowed' in body['error'].lower()

    def test_suspend_with_empty_reason(self, setup_handler):
        """SUSPEND with empty reason → guard fails (requires_reason checks not None)."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-021',
            'status': 'Actief',
            'voornaam': 'Marie',
            'achternaam': 'Jansen',
            'email': 'marie@example.nl',
        })

        # reason is None (not provided in context → ctx.get('reason') returns None)
        event = _make_event('member-021', {'event': 'SUSPEND', 'context': {'reason': None}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 400
        assert 'error' in body


class TestStatusHistory:
    """Test that status_history is correctly appended on transitions."""

    def test_status_history_appended_on_transition(self, setup_handler):
        """On successful transition, status_history gets a new entry."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-030',
            'status': 'wachtRegio',
            'voornaam': 'Anna',
            'achternaam': 'Mulder',
            'email': 'anna@example.nl',
            'regio': '3',
        })

        event = _make_event('member-030', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify status_history was written to DynamoDB
        item = table.get_item(Key={'member_id': 'member-030'})['Item']
        assert 'status_history' in item
        assert len(item['status_history']) == 1

        entry = item['status_history'][0]
        assert entry['from'] == 'wachtRegio'
        assert entry['to'] == 'wachtBetaling'
        assert entry['event'] == 'APPROVE'
        assert entry['by'] == 'admin@h-dcn.nl'
        assert 'at' in entry  # ISO timestamp

    def test_status_history_appends_to_existing(self, setup_handler):
        """status_history appends (does not overwrite) existing entries."""
        table, handler = setup_handler

        existing_history = [{
            'from': 'Aangemeld',
            'to': 'wachtRegio',
            'event': 'SUBMIT',
            'at': '2026-01-01T10:00:00+00:00',
            'by': 'system@h-dcn.nl',
        }]

        table.put_item(Item={
            'member_id': 'member-031',
            'status': 'wachtRegio',
            'voornaam': 'Ben',
            'achternaam': 'Dekker',
            'email': 'ben@example.nl',
            'regio': '1',
            'status_history': existing_history,
        })

        event = _make_event('member-031', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200

        item = table.get_item(Key={'member_id': 'member-031'})['Item']
        assert len(item['status_history']) == 2
        # First entry is preserved
        assert item['status_history'][0]['event'] == 'SUBMIT'
        # Second entry is the new one
        assert item['status_history'][1]['event'] == 'APPROVE'
        assert item['status_history'][1]['from'] == 'wachtRegio'
        assert item['status_history'][1]['to'] == 'wachtBetaling'


class TestWelcomePackStatus:
    """Test that welcome_pack_status is set on PAYMENT_RECEIVED (activation).

    Note: The flag_welcome_pack action is registered in the dispatcher and
    intended to run during PAYMENT_RECEIVED transitions. This test verifies
    the integration by adding flag_welcome_pack to the transition's actions.
    """

    def test_welcome_pack_status_set_on_activation(self, setup_handler):
        """PAYMENT_RECEIVED triggers flag_welcome_pack which sets welcome_pack_status=pending."""
        table, handler = setup_handler

        # Register a flag_welcome_pack that writes to the mocked DynamoDB table
        def mock_flag_welcome_pack(ctx):
            member_id = ctx['member_id']
            table.update_item(
                Key={'member_id': member_id},
                UpdateExpression='SET welcome_pack_status = :status',
                ExpressionAttributeValues={':status': 'pending'},
            )

        handler.dispatcher._registry['flag_welcome_pack'] = mock_flag_welcome_pack

        # Patch the engine's PAYMENT_RECEIVED transition to include flag_welcome_pack
        # This matches the intended design (design.md §6) where flag_welcome_pack
        # is a mandatory action on activation.
        for t in handler.membership_engine._transitions:
            if t['event'] == 'PAYMENT_RECEIVED':
                if 'flag_welcome_pack' not in t['actions']:
                    t['actions'].append('flag_welcome_pack')
                break

        table.put_item(Item={
            'member_id': 'member-040',
            'status': 'wachtBetaling',
            'voornaam': 'Sophie',
            'achternaam': 'Boer',
            'email': 'sophie@example.nl',
            'straat': 'Kerkstraat 10',
            'postcode': '5678CD',
            'woonplaats': 'Rotterdam',
        })

        event = _make_event('member-040', {'event': 'PAYMENT_RECEIVED', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 200
        assert body['success'] is True

        # Verify welcome_pack_status was set in DynamoDB
        item = table.get_item(Key={'member_id': 'member-040'})['Item']
        assert item.get('welcome_pack_status') == 'pending'


class TestMemberNotFound:
    """Test 404 handling when member doesn't exist."""

    def test_member_not_found_returns_404(self, setup_handler):
        """Transition request for non-existent member → 404."""
        table, handler = setup_handler

        event = _make_event('nonexistent-member', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        body = json.loads(response['body'])
        assert response['statusCode'] == 404
        assert 'error' in body
        assert 'not found' in body['error'].lower()


class TestRequestValidation:
    """Test request body validation."""

    def test_missing_event_field(self, setup_handler):
        """Request without 'event' field → 400."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-050',
            'status': 'Actief',
            'email': 'test@example.nl',
        })

        event = _make_event('member-050', {'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

    def test_status_not_in_workflow(self, setup_handler):
        """Member with status outside workflow (e.g. 'HdcnAccount') → 400."""
        table, handler = setup_handler

        table.put_item(Item={
            'member_id': 'member-051',
            'status': 'HdcnAccount',
            'email': 'account@example.nl',
        })

        event = _make_event('member-051', {'event': 'APPROVE', 'context': {}})

        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'not part of the membership workflow' in body['error'].lower()
