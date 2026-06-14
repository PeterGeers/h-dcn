"""
Unit Tests for cognito_post_confirmation Lambda Handler.

Tests both paths:
1. Event landing page signup: creates event_participant member, adds to event_participant group
2. Regular signup: existing flow — checks member status, assigns hdcnLeden if approved
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['DEFAULT_MEMBER_GROUP'] = 'hdcnLeden'
os.environ['ORGANIZATION_SHORT_NAME'] = 'H-DCN'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'cognito_post_confirmation', 'app.py')
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

TEST_USER_POOL_ID = 'eu-west-1_testPool'
TEST_USERNAME = 'testuser@example.com'
TEST_EMAIL = 'testuser@example.com'
TEST_EVENT_ID = 'evt-landing-1234-5678-abcd'


def _make_cognito_event(trigger_source='PostConfirmation_ConfirmSignUp',
                         email=TEST_EMAIL,
                         given_name='Jan',
                         family_name='de Vries',
                         client_metadata=None):
    """Create a Cognito post-confirmation trigger event."""
    event = {
        'version': '1',
        'triggerSource': trigger_source,
        'region': 'eu-west-1',
        'userPoolId': TEST_USER_POOL_ID,
        'userName': email,
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-unknown-unknown',
            'clientId': 'test-client-id',
        },
        'request': {
            'userAttributes': {
                'sub': 'sub-12345',
                'email': email,
                'email_verified': 'true',
                'given_name': given_name,
                'family_name': family_name,
            },
        },
        'response': {},
    }
    if client_metadata:
        event['request']['clientMetadata'] = client_metadata
    return event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB Members table and load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Also mock cognito-idp client
        handler_module = _load_handler()
        yield members_table, handler_module


# ---------------------------------------------------------------------------
# Tests: Event Landing Page Signup Path
# ---------------------------------------------------------------------------

class TestEventLandingSignup:
    """Tests for event landing page signup (source='event_landing')."""

    def test_creates_event_participant_member(self, setup_tables):
        """Creates a Members record with member_type='event_participant'."""
        members_table, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'event_id': TEST_EVENT_ID, 'source': 'event_landing'}
        )

        # Mock the cognito add_user_to_group call
        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}):
            result = handler.lambda_handler(event, None)

        # Should return the event unchanged
        assert result == event

        # Check that a member record was created
        response = members_table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': TEST_EMAIL}
        )
        items = response['Items']
        assert len(items) == 1

        member = items[0]
        assert member['member_type'] == 'event_participant'
        assert member['email'] == TEST_EMAIL
        assert member['given_name'] == 'Jan'
        assert member['family_name'] == 'de Vries'
        assert member['status'] == 'active'
        assert TEST_EVENT_ID in member['allowed_events']
        assert member['created_via'] == 'event_landing'
        assert 'member_id' in member
        assert 'created_at' in member

    def test_adds_user_to_event_participant_group(self, setup_tables):
        """Adds user to event_participant Cognito group (NOT hdcnLeden)."""
        members_table, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'event_id': TEST_EVENT_ID, 'source': 'event_landing'}
        )

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            handler.lambda_handler(event, None)

        # Verify called with event_participant group
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username=TEST_EMAIL,
            GroupName='event_participant',
        )

    def test_does_not_add_to_hdcnleden(self, setup_tables):
        """Does NOT add event landing users to hdcnLeden group."""
        members_table, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'event_id': TEST_EVENT_ID, 'source': 'event_landing'}
        )

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            handler.lambda_handler(event, None)

        # Should only be called with event_participant, never hdcnLeden
        for call in mock_add.call_args_list:
            assert call[1].get('GroupName', call[0][0] if call[0] else '') != 'hdcnLeden'


# ---------------------------------------------------------------------------
# Tests: Regular Signup Path (no event context)
# ---------------------------------------------------------------------------

class TestRegularSignup:
    """Tests for regular signup (no clientMetadata or different source)."""

    def test_approved_member_gets_hdcnleden(self, setup_tables):
        """Existing approved member gets added to hdcnLeden group."""
        members_table, handler = setup_tables

        # Seed an existing approved member
        members_table.put_item(Item={
            'member_id': 'existing-mem-001',
            'email': TEST_EMAIL,
            'status': 'active',
            'member_type': 'hdcn_member',
        })

        event = _make_cognito_event()  # No clientMetadata = regular signup

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username=TEST_EMAIL,
            GroupName='hdcnLeden',
        )

    def test_unapproved_member_gets_no_group(self, setup_tables):
        """Existing unapproved member gets no group assignment."""
        members_table, handler = setup_tables

        # Seed an existing pending member
        members_table.put_item(Item={
            'member_id': 'existing-mem-002',
            'email': TEST_EMAIL,
            'status': 'pending',
            'member_type': 'hdcn_member',
        })

        event = _make_cognito_event()

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_new_applicant_gets_no_group(self, setup_tables):
        """New user not in Members table gets no group assignment."""
        members_table, handler = setup_tables

        event = _make_cognito_event()  # No existing member record

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_no_member_created_for_regular_signup(self, setup_tables):
        """Regular signup does NOT auto-create a Members record."""
        members_table, handler = setup_tables

        event = _make_cognito_event()

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}):
            handler.lambda_handler(event, None)

        # Should not have created any new records
        response = members_table.scan()
        assert len(response['Items']) == 0

    def test_empty_client_metadata_is_regular_flow(self, setup_tables):
        """Empty clientMetadata (no source/event_id) triggers regular flow."""
        members_table, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'some_other_key': 'value'}
        )

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            handler.lambda_handler(event, None)

        # No member created, no group added (new user not in members)
        response = members_table.scan()
        assert len(response['Items']) == 0
        mock_add.assert_not_called()

    def test_source_not_event_landing_is_regular_flow(self, setup_tables):
        """clientMetadata with source != 'event_landing' triggers regular flow."""
        members_table, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'event_id': TEST_EVENT_ID, 'source': 'admin_portal'}
        )

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            handler.lambda_handler(event, None)

        # Regular flow — no member created
        response = members_table.scan()
        assert len(response['Items']) == 0


# ---------------------------------------------------------------------------
# Tests: Password Recovery (unchanged)
# ---------------------------------------------------------------------------

class TestPasswordRecovery:
    """Tests for password recovery confirmation (unchanged behavior)."""

    def test_password_recovery_returns_event(self, setup_tables):
        """Password recovery just logs and returns the event."""
        _, handler = setup_tables

        event = _make_cognito_event(trigger_source='PostConfirmation_ConfirmForgotPassword')

        with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
            result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling — handler should never block user confirmation."""

    def test_handler_returns_event_on_error(self, setup_tables):
        """Even if an error occurs, the handler returns the event (doesn't block confirmation)."""
        _, handler = setup_tables

        event = _make_cognito_event(
            client_metadata={'event_id': TEST_EVENT_ID, 'source': 'event_landing'}
        )

        # Make DynamoDB put fail
        with patch.object(handler.dynamodb, 'Table', side_effect=Exception("DB connection error")):
            result = handler.lambda_handler(event, None)

        # Should still return the event (never block user confirmation)
        assert result == event
