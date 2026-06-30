"""
Unit Tests for cognito_post_authentication Lambda Handler.

Security-critical: This handler runs after every successful login and handles
role assignment for Google SSO users who bypass post-confirmation.

Tests cover:
1. Normal login: user with existing roles — no changes made
2. First-time login (no groups): assigns hdcnLeden if member is approved
3. Google SSO login: federated-only groups trigger role assignment
4. Error handling: handler never blocks authentication
5. Event format: correct Cognito trigger event structure handled
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
os.environ['ORGANIZATION_NAME'] = 'Harley-Davidson Club Nederland'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'cognito_post_authentication', 'app.py')
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
TEST_USERNAME = 'testuser@h-dcn.nl'
TEST_EMAIL = 'testuser@h-dcn.nl'


def _make_post_auth_event(trigger_source='PostAuthentication_Authentication',
                           email=TEST_EMAIL,
                           given_name='Jan',
                           family_name='de Vries',
                           username=None):
    """Create a Cognito post-authentication trigger event."""
    return {
        'version': '1',
        'triggerSource': trigger_source,
        'region': 'eu-west-1',
        'userPoolId': TEST_USER_POOL_ID,
        'userName': username or email,
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-unknown-unknown',
            'clientId': 'test-client-id',
        },
        'request': {
            'userAttributes': {
                'sub': 'sub-12345-abcde',
                'email': email,
                'email_verified': 'true',
                'given_name': given_name,
                'family_name': family_name,
            },
        },
        'response': {},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_cognito_and_members():
    """Create mocked DynamoDB Members table and load handler inside mock_aws context.
    
    Note: We only mock DynamoDB here. Cognito client calls are patched individually
    in each test (admin_list_groups_for_user, admin_add_user_to_group) so we don't
    need moto's cognitoidp backend (which requires the 'joserfc' dependency).
    """
    with mock_aws():
        # Create Members table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        handler_module = _load_handler()
        yield members_table, handler_module


# ---------------------------------------------------------------------------
# Tests: Normal login — user already has roles
# ---------------------------------------------------------------------------

class TestNormalLogin:
    """Tests for normal login where user already has appropriate roles."""

    def test_user_with_hdcnleden_group_skips_assignment(self, setup_cognito_and_members):
        """User already in hdcnLeden group — no role assignment happens."""
        members_table, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        # User already has hdcnLeden group
        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'hdcnLeden'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_user_with_verzoek_lid_group_skips_assignment(self, setup_cognito_and_members):
        """User in verzoek_lid group — no role assignment happens."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'verzoek_lid'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_user_with_admin_group_skips_assignment(self, setup_cognito_and_members):
        """User with admin roles — no additional assignment needed."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'hdcnLeden'}, {'GroupName': 'Admin'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_always_returns_event_on_success(self, setup_cognito_and_members):
        """Handler must always return the original event to Cognito."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'hdcnLeden'}]
        }):
            result = handler.lambda_handler(event, None)

        assert result is event


# ---------------------------------------------------------------------------
# Tests: First-time login — no groups assigned yet
# ---------------------------------------------------------------------------

class TestFirstTimeLogin:
    """Tests for first-time login where user has no groups."""

    def test_approved_member_gets_hdcnleden(self, setup_cognito_and_members):
        """User with no groups + approved member status → assigned hdcnLeden."""
        members_table, handler = setup_cognito_and_members

        # Seed approved member
        members_table.put_item(Item={
            'member_id': 'mem-001',
            'email': TEST_EMAIL,
            'status': 'active',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': []
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username=TEST_EMAIL,
            GroupName='hdcnLeden',
        )

    def test_active_status_triggers_role_assignment(self, setup_cognito_and_members):
        """Member with 'active' status gets assigned hdcnLeden."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-002',
            'email': TEST_EMAIL,
            'status': 'active',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                handler.lambda_handler(event, None)

        mock_add.assert_called_once()

    def test_approved_status_triggers_role_assignment(self, setup_cognito_and_members):
        """Member with 'approved' status gets assigned hdcnLeden."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-003',
            'email': TEST_EMAIL,
            'status': 'approved',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                handler.lambda_handler(event, None)

        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username=TEST_EMAIL,
            GroupName='hdcnLeden',
        )

    def test_pending_member_gets_no_group(self, setup_cognito_and_members):
        """User with pending member status — no role assigned."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-004',
            'email': TEST_EMAIL,
            'status': 'pending',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_unknown_user_gets_no_group(self, setup_cognito_and_members):
        """User not in Members table — no role assigned."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Google SSO login — federated-only groups
# ---------------------------------------------------------------------------

class TestGoogleSSOLogin:
    """Tests for Google SSO users who bypass post-confirmation trigger."""

    def test_google_federated_group_only_triggers_assignment(self, setup_cognito_and_members):
        """User with only Google federated group → needs role check."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-google-001',
            'email': TEST_EMAIL,
            'status': 'active',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'eu-west-1_fcUkvwjH5_Google'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username=TEST_EMAIL,
            GroupName='hdcnLeden',
        )

    def test_google_plus_hdcnleden_skips_assignment(self, setup_cognito_and_members):
        """User with Google group + hdcnLeden → no additional assignment."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [
                {'GroupName': 'eu-west-1_fcUkvwjH5_Google'},
                {'GroupName': 'hdcnLeden'},
            ]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_facebook_federated_group_triggers_assignment(self, setup_cognito_and_members):
        """User with only Facebook federated group (edge case) → needs role check."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-fb-001',
            'email': TEST_EMAIL,
            'status': 'active',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'eu-west-1_fcUkvwjH5_Facebook'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                handler.lambda_handler(event, None)

        mock_add.assert_called_once()

    def test_google_user_not_in_members_gets_no_group(self, setup_cognito_and_members):
        """Google SSO user not in Members table — no role assigned."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'eu-west-1_fcUkvwjH5_Google'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()

    def test_google_user_with_unapproved_status_gets_no_group(self, setup_cognito_and_members):
        """Google SSO user with 'rejected' member status — no role assigned."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-google-rej',
            'email': TEST_EMAIL,
            'status': 'rejected',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'eu-west-1_fcUkvwjH5_Google'}]
        }):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Error handling — handler must never block login
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling — handler should never block authentication."""

    def test_returns_event_when_group_lookup_fails(self, setup_cognito_and_members):
        """If admin_list_groups_for_user fails, handler returns event (doesn't block login)."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user',
                          side_effect=Exception("Cognito service error")):
            result = handler.lambda_handler(event, None)

        # Must still return the event — never block authentication
        assert result == event

    def test_returns_event_when_dynamodb_fails(self, setup_cognito_and_members):
        """If DynamoDB scan fails, handler returns event (doesn't block login)."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.dynamodb, 'Table', side_effect=Exception("DynamoDB error")):
                result = handler.lambda_handler(event, None)

        assert result == event

    def test_returns_event_when_add_to_group_fails(self, setup_cognito_and_members):
        """If admin_add_user_to_group fails, handler returns event (doesn't block login)."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-err-001',
            'email': TEST_EMAIL,
            'status': 'active',
        })

        event = _make_post_auth_event()

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group',
                              side_effect=Exception("Group not found")):
                result = handler.lambda_handler(event, None)

        # Must still return event even though add_to_group raised
        assert result == event

    def test_returns_event_on_malformed_event(self, setup_cognito_and_members):
        """Malformed event (missing fields) — handler returns event without crashing."""
        _, handler = setup_cognito_and_members

        # Minimal event with missing fields
        event = {
            'version': '1',
            'triggerSource': 'PostAuthentication_Authentication',
            'userPoolId': TEST_USER_POOL_ID,
            'userName': '',
            'request': {},
            'response': {},
        }

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            result = handler.lambda_handler(event, None)

        assert result == event

    def test_returns_event_on_completely_empty_event(self, setup_cognito_and_members):
        """Completely empty event dict — handler returns event without crashing."""
        _, handler = setup_cognito_and_members

        event = {}
        result = handler.lambda_handler(event, None)
        assert result == event


# ---------------------------------------------------------------------------
# Tests: Event format — correct Cognito trigger structure handling
# ---------------------------------------------------------------------------

class TestEventFormat:
    """Tests verifying correct Cognito trigger event format handling."""

    def test_handles_post_authentication_trigger_source(self, setup_cognito_and_members):
        """PostAuthentication_Authentication trigger is handled."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event(trigger_source='PostAuthentication_Authentication')

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={
            'Groups': [{'GroupName': 'hdcnLeden'}]
        }):
            result = handler.lambda_handler(event, None)

        assert result == event

    def test_unhandled_trigger_source_returns_event(self, setup_cognito_and_members):
        """Unknown trigger source — returns event without processing."""
        _, handler = setup_cognito_and_members

        event = _make_post_auth_event(trigger_source='PostAuthentication_SomeOther')

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user') as mock_list:
            with patch.object(handler.cognito_client, 'admin_add_user_to_group') as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        # Should not even look up groups for unhandled trigger
        mock_list.assert_not_called()
        mock_add.assert_not_called()

    def test_uses_email_from_user_attributes(self, setup_cognito_and_members):
        """Email is extracted from request.userAttributes.email."""
        members_table, handler = setup_cognito_and_members

        # Add member with specific email
        members_table.put_item(Item={
            'member_id': 'mem-attr-001',
            'email': 'attr-user@h-dcn.nl',
            'status': 'active',
        })

        event = _make_post_auth_event(email='attr-user@h-dcn.nl')

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                handler.lambda_handler(event, None)

        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username='attr-user@h-dcn.nl',
            GroupName='hdcnLeden',
        )

    def test_falls_back_to_username_if_no_email(self, setup_cognito_and_members):
        """If email is missing from userAttributes, use userName as email."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-nomail-001',
            'email': 'fallback@h-dcn.nl',
            'status': 'active',
        })

        event = {
            'version': '1',
            'triggerSource': 'PostAuthentication_Authentication',
            'region': 'eu-west-1',
            'userPoolId': TEST_USER_POOL_ID,
            'userName': 'fallback@h-dcn.nl',
            'callerContext': {'awsSdkVersion': 'aws-sdk-unknown', 'clientId': 'test'},
            'request': {
                'userAttributes': {
                    'sub': 'sub-fallback',
                    # No 'email' attribute
                },
            },
            'response': {},
        }

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username='fallback@h-dcn.nl',
            GroupName='hdcnLeden',
        )

    def test_google_sso_username_format(self, setup_cognito_and_members):
        """Google SSO users have username like 'Google_123456789' — email from attributes."""
        members_table, handler = setup_cognito_and_members

        members_table.put_item(Item={
            'member_id': 'mem-google-fmt',
            'email': 'google-user@gmail.com',
            'status': 'active',
        })

        # Google SSO users often have a different username format
        event = _make_post_auth_event(
            email='google-user@gmail.com',
            username='Google_112233445566778899',
        )

        with patch.object(handler.cognito_client, 'admin_list_groups_for_user', return_value={'Groups': []}):
            with patch.object(handler.cognito_client, 'admin_add_user_to_group', return_value={}) as mock_add:
                result = handler.lambda_handler(event, None)

        assert result == event
        # Should use the userName (which is the Cognito username), not the email for group assignment
        mock_add.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Username='Google_112233445566778899',
            GroupName='hdcnLeden',
        )
