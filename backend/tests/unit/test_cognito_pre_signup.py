"""
Unit Tests for cognito_pre_signup Lambda Handler (SECURITY-CRITICAL).

This handler links federated (Google) identities to existing native Cognito users.
It is a Pre Sign-Up trigger that prevents duplicate accounts and handles identity
provider linking.

Scenarios tested:
1. External provider (Google) sign-up — links to existing native user
2. External provider (Google) sign-up — no existing native user (new account)
3. Non-external-provider sign-up — passthrough
4. Edge cases: missing email, unparseable federated username, already-linked provider
5. Error handling — handler must never block sign-up
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'cognito_pre_signup', 'app.py')
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
# Test data helpers
# ---------------------------------------------------------------------------

TEST_USER_POOL_ID = 'eu-west-1_testPool'
TEST_EMAIL = 'member@h-dcn.nl'
TEST_NATIVE_USERNAME = '550e8400-e29b-41d4-a716-446655440000'
TEST_GOOGLE_USER_ID = '112283382738141445724'
TEST_GOOGLE_USERNAME = f'Google_{TEST_GOOGLE_USER_ID}'


def _make_pre_signup_event(
    trigger_source: str = 'PreSignUp_ExternalProvider',
    email: str = TEST_EMAIL,
    username: str = TEST_GOOGLE_USERNAME,
    user_pool_id: str = TEST_USER_POOL_ID,
) -> dict:
    """Create a Cognito Pre Sign-Up trigger event."""
    return {
        'version': '1',
        'triggerSource': trigger_source,
        'region': 'eu-west-1',
        'userPoolId': user_pool_id,
        'userName': username,
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-unknown-unknown',
            'clientId': 'test-client-id',
        },
        'request': {
            'userAttributes': {
                'email': email,
            },
        },
        'response': {
            'autoConfirmUser': False,
            'autoVerifyEmail': False,
            'autoVerifyPhone': False,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def handler():
    """Load handler module with mocked cognito_client."""
    module = _load_handler()
    yield module


# ---------------------------------------------------------------------------
# Tests: External Provider Sign-Up — Existing Native User (Linking)
# ---------------------------------------------------------------------------

class TestExternalProviderLinking:
    """Tests for Google SSO sign-up when a native user with the same email exists."""

    def test_links_google_identity_to_native_user(self, handler):
        """When a native user exists with same email, link Google identity to it."""
        event = _make_pre_signup_event()

        # Mock list_users to return a native user
        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # Verify linking was called correctly
        mock_link.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            DestinationUser={
                'ProviderName': 'Cognito',
                'ProviderAttributeValue': TEST_NATIVE_USERNAME,
            },
            SourceUser={
                'ProviderName': 'Google',
                'ProviderAttributeName': 'Cognito_Subject',
                'ProviderAttributeValue': TEST_GOOGLE_USER_ID,
            },
        )

        # Verify auto-confirm and auto-verify are set
        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True

    def test_auto_confirms_and_verifies_external_provider(self, handler):
        """External provider users are always auto-confirmed with verified email."""
        event = _make_pre_signup_event()

        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}):
                result = handler.lambda_handler(event, None)

        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True

    def test_skips_federated_users_when_searching(self, handler):
        """When searching for native user, skip federated users (Google_, Facebook_)."""
        event = _make_pre_signup_event()

        # Return both a federated user and a native user
        mock_list_users_response = {
            'Users': [
                {
                    'Username': 'Google_999999999999',
                    'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                    'UserStatus': 'EXTERNAL_PROVIDER',
                },
                {
                    'Username': TEST_NATIVE_USERNAME,
                    'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                    'UserStatus': 'CONFIRMED',
                },
            ]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # Should link to the native user, not the federated one
        mock_link.assert_called_once()
        call_kwargs = mock_link.call_args[1]
        assert call_kwargs['DestinationUser']['ProviderAttributeValue'] == TEST_NATIVE_USERNAME

    def test_handles_already_linked_provider(self, handler):
        """If provider is already linked (InvalidParameterException), doesn't raise."""
        event = _make_pre_signup_event()

        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        error_response = {
            'Error': {
                'Code': 'InvalidParameterException',
                'Message': 'User is already linked',
            }
        }
        link_error = ClientError(error_response, 'AdminLinkProviderForUser')

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', side_effect=link_error):
                result = handler.lambda_handler(event, None)

        # Should not raise — still returns event with auto-confirm
        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True


# ---------------------------------------------------------------------------
# Tests: External Provider Sign-Up — No Existing Native User
# ---------------------------------------------------------------------------

class TestExternalProviderNewUser:
    """Tests for Google SSO sign-up when no native user exists (new account)."""

    def test_allows_new_signup_without_linking(self, handler):
        """When no native user exists, allow sign-up without linking."""
        event = _make_pre_signup_event()

        # No users found
        mock_list_users_response = {'Users': []}

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # Should NOT call link
        mock_link.assert_not_called()

        # Should still auto-confirm (it's an external provider)
        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True

    def test_no_native_user_only_federated_exists(self, handler):
        """If only federated users exist for the email, don't link."""
        event = _make_pre_signup_event()

        # Only a federated user exists
        mock_list_users_response = {
            'Users': [{
                'Username': 'Facebook_123456789',
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'EXTERNAL_PROVIDER',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # No native user to link to
        mock_link.assert_not_called()
        assert result['response']['autoConfirmUser'] is True


# ---------------------------------------------------------------------------
# Tests: Non-External Provider Sign-Up (Passthrough)
# ---------------------------------------------------------------------------

class TestNonExternalProviderSignup:
    """Tests for regular (non-external provider) sign-up triggers."""

    def test_regular_signup_passes_through(self, handler):
        """PreSignUp_SignUp trigger passes through without modification."""
        event = _make_pre_signup_event(
            trigger_source='PreSignUp_SignUp',
            username='newuser@h-dcn.nl',
        )

        with patch.object(handler.cognito_client, 'list_users') as mock_list:
            result = handler.lambda_handler(event, None)

        # Should NOT call list_users — no external provider logic needed
        mock_list.assert_not_called()

        # Response should be unmodified (no autoConfirmUser changes)
        assert result == event

    def test_admin_create_user_passes_through(self, handler):
        """PreSignUp_AdminCreateUser trigger passes through."""
        event = _make_pre_signup_event(
            trigger_source='PreSignUp_AdminCreateUser',
            username='admin-created-user',
        )

        with patch.object(handler.cognito_client, 'list_users') as mock_list:
            result = handler.lambda_handler(event, None)

        mock_list.assert_not_called()
        assert result == event

    def test_unknown_trigger_source_passes_through(self, handler):
        """Unknown trigger source passes through without external provider logic."""
        event = _make_pre_signup_event(
            trigger_source='PreSignUp_SomethingNew',
            username='user@example.com',
        )

        with patch.object(handler.cognito_client, 'list_users') as mock_list:
            result = handler.lambda_handler(event, None)

        mock_list.assert_not_called()
        assert result == event


# ---------------------------------------------------------------------------
# Tests: Email Verification Flags
# ---------------------------------------------------------------------------

class TestEmailVerification:
    """Tests for email verification behavior."""

    def test_external_provider_always_verifies_email(self, handler):
        """External provider sign-ups always set autoVerifyEmail=True."""
        event = _make_pre_signup_event()

        mock_list_users_response = {'Users': []}

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            result = handler.lambda_handler(event, None)

        assert result['response']['autoVerifyEmail'] is True

    def test_external_provider_always_auto_confirms(self, handler):
        """External provider sign-ups always set autoConfirmUser=True."""
        event = _make_pre_signup_event()

        mock_list_users_response = {'Users': []}

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            result = handler.lambda_handler(event, None)

        assert result['response']['autoConfirmUser'] is True

    def test_regular_signup_does_not_auto_verify(self, handler):
        """Regular sign-ups do NOT get auto-verified (must confirm email normally)."""
        event = _make_pre_signup_event(
            trigger_source='PreSignUp_SignUp',
            username='regular@example.com',
        )

        result = handler.lambda_handler(event, None)

        # Passthrough — response unchanged
        assert result['response']['autoConfirmUser'] is False
        assert result['response']['autoVerifyEmail'] is False


# ---------------------------------------------------------------------------
# Tests: Federated Username Parsing
# ---------------------------------------------------------------------------

class TestFederatedUsernameParsing:
    """Tests for parse_federated_username function."""

    def test_parse_google_username(self, handler):
        """Correctly parses Google_<id> format."""
        provider, user_id = handler.parse_federated_username('Google_112283382738141445724')
        assert provider == 'Google'
        assert user_id == '112283382738141445724'

    def test_parse_facebook_username(self, handler):
        """Correctly parses Facebook_<id> format."""
        provider, user_id = handler.parse_federated_username('Facebook_987654321')
        assert provider == 'Facebook'
        assert user_id == '987654321'

    def test_parse_saml_username(self, handler):
        """Correctly parses SAML_<id> format."""
        provider, user_id = handler.parse_federated_username('SAML_user-from-saml-provider')
        assert provider == 'SAML'
        assert user_id == 'user-from-saml-provider'

    def test_parse_login_with_amazon_username(self, handler):
        """Correctly parses LoginWithAmazon_<id> format."""
        provider, user_id = handler.parse_federated_username('LoginWithAmazon_amzn123')
        assert provider == 'LoginWithAmazon'
        assert user_id == 'amzn123'

    def test_parse_unknown_format_returns_none(self, handler):
        """Unknown username format returns (None, None)."""
        provider, user_id = handler.parse_federated_username('regular-username-uuid')
        assert provider is None
        assert user_id is None

    def test_parse_empty_string(self, handler):
        """Empty string returns (None, None)."""
        provider, user_id = handler.parse_federated_username('')
        assert provider is None
        assert user_id is None

    def test_parse_underscore_in_user_id(self, handler):
        """Provider user ID containing underscores is handled correctly."""
        provider, user_id = handler.parse_federated_username('Google_some_user_with_underscores')
        assert provider == 'Google'
        assert user_id == 'some_user_with_underscores'


# ---------------------------------------------------------------------------
# Tests: find_native_user function
# ---------------------------------------------------------------------------

class TestFindNativeUser:
    """Tests for find_native_user function."""

    def test_finds_native_user_by_email(self, handler):
        """Returns native user when one exists with matching email."""
        mock_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is not None
        assert result['Username'] == TEST_NATIVE_USERNAME

    def test_returns_none_when_no_users(self, handler):
        """Returns None when no users exist with that email."""
        mock_response = {'Users': []}

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_skips_google_prefixed_users(self, handler):
        """Skips users with Google_ prefix (federated, not native)."""
        mock_response = {
            'Users': [{
                'Username': 'Google_12345',
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_skips_facebook_prefixed_users(self, handler):
        """Skips users with Facebook_ prefix."""
        mock_response = {
            'Users': [{
                'Username': 'Facebook_99999',
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_skips_saml_prefixed_users(self, handler):
        """Skips users with SAML_ prefix."""
        mock_response = {
            'Users': [{
                'Username': 'SAML_enterprise-user',
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_skips_login_with_amazon_prefixed_users(self, handler):
        """Skips users with LoginWithAmazon_ prefix."""
        mock_response = {
            'Users': [{
                'Username': 'LoginWithAmazon_amzn456',
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_returns_none_on_cognito_error(self, handler):
        """Returns None (doesn't crash) on Cognito API error."""
        with patch.object(handler.cognito_client, 'list_users', side_effect=Exception("Service unavailable")):
            result = handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        assert result is None

    def test_uses_email_filter(self, handler):
        """Calls list_users with correct email filter."""
        mock_response = {'Users': []}

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_response) as mock_list:
            handler.find_native_user(TEST_USER_POOL_ID, TEST_EMAIL)

        mock_list.assert_called_once_with(
            UserPoolId=TEST_USER_POOL_ID,
            Filter=f'email = "{TEST_EMAIL}"',
        )


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for security and robustness."""

    def test_missing_email_passes_through(self, handler):
        """External provider sign-up with no email passes through safely."""
        event = _make_pre_signup_event(email='')

        # No email → don't attempt linking, just return
        with patch.object(handler.cognito_client, 'list_users') as mock_list:
            result = handler.lambda_handler(event, None)

        mock_list.assert_not_called()
        assert result == event

    def test_unparseable_federated_username_no_link(self, handler):
        """If federated username can't be parsed, don't attempt linking."""
        event = _make_pre_signup_event(
            username='unknown-format-username',
        )

        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # Can't parse provider, so don't link
        mock_link.assert_not_called()

        # But still auto-confirm (it's still an external provider trigger)
        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True

    def test_multiple_native_users_links_to_first(self, handler):
        """If multiple native users match email, links to the first one found."""
        event = _make_pre_signup_event()

        mock_list_users_response = {
            'Users': [
                {
                    'Username': 'first-native-user-uuid',
                    'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                    'UserStatus': 'CONFIRMED',
                },
                {
                    'Username': 'second-native-user-uuid',
                    'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                    'UserStatus': 'CONFIRMED',
                },
            ]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        # Links to the first native user found
        call_kwargs = mock_link.call_args[1]
        assert call_kwargs['DestinationUser']['ProviderAttributeValue'] == 'first-native-user-uuid'

    def test_facebook_provider_linking(self, handler):
        """Facebook provider sign-up triggers linking correctly."""
        event = _make_pre_signup_event(username='Facebook_987654321')

        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', return_value={}) as mock_link:
                result = handler.lambda_handler(event, None)

        call_kwargs = mock_link.call_args[1]
        assert call_kwargs['SourceUser']['ProviderName'] == 'Facebook'
        assert call_kwargs['SourceUser']['ProviderAttributeValue'] == '987654321'


# ---------------------------------------------------------------------------
# Tests: Error Handling — CRITICAL (must never block sign-up)
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Error handling — handler must NEVER block sign-up by raising an exception."""

    def test_cognito_error_during_linking_does_not_block_signup(self, handler):
        """Non-InvalidParameterException errors during linking don't crash Lambda.

        The error is re-raised from the inner try/except, but caught by the
        outer handler-level try/except which returns the event to avoid blocking
        sign-up. Since the exception occurs before autoConfirmUser is set, the
        response retains its original False value.
        """
        event = _make_pre_signup_event()

        mock_list_users_response = {
            'Users': [{
                'Username': TEST_NATIVE_USERNAME,
                'Attributes': [{'Name': 'email', 'Value': TEST_EMAIL}],
                'UserStatus': 'CONFIRMED',
            }]
        }

        error_response = {
            'Error': {
                'Code': 'InternalErrorException',
                'Message': 'Service error',
            }
        }
        link_error = ClientError(error_response, 'AdminLinkProviderForUser')

        with patch.object(handler.cognito_client, 'list_users', return_value=mock_list_users_response):
            with patch.object(handler.cognito_client, 'admin_link_provider_for_user', side_effect=link_error):
                result = handler.lambda_handler(event, None)

        # Handler returns event to not block sign-up (never raises)
        assert result is not None
        # autoConfirmUser was NOT set because the error occurred before that line
        assert result['response']['autoConfirmUser'] is False

    def test_list_users_error_returns_event(self, handler):
        """Error in find_native_user doesn't block sign-up."""
        event = _make_pre_signup_event()

        with patch.object(handler.cognito_client, 'list_users', side_effect=Exception("Connection timeout")):
            result = handler.lambda_handler(event, None)

        # Should still return event (find_native_user returns None on error)
        assert result['response']['autoConfirmUser'] is True
        assert result['response']['autoVerifyEmail'] is True

    def test_completely_malformed_event_returns_event(self, handler):
        """Completely malformed event still returns something (doesn't crash Lambda)."""
        # Minimal event that would cause KeyError if not handled
        malformed_event = {
            'triggerSource': 'PreSignUp_ExternalProvider',
            'userName': 'Google_12345',
            'userPoolId': TEST_USER_POOL_ID,
            'request': {},  # Missing userAttributes
            'response': {
                'autoConfirmUser': False,
                'autoVerifyEmail': False,
            },
        }

        # The handler should handle this gracefully due to .get() usage
        result = handler.lambda_handler(malformed_event, None)

        # Should still return the event
        assert result is not None

    def test_missing_response_key_in_event(self, handler):
        """If response key is missing, handler handles gracefully."""
        event = {
            'version': '1',
            'triggerSource': 'PreSignUp_SignUp',
            'region': 'eu-west-1',
            'userPoolId': TEST_USER_POOL_ID,
            'userName': 'user@example.com',
            'request': {
                'userAttributes': {'email': 'user@example.com'},
            },
            'response': {},
        }

        result = handler.lambda_handler(event, None)

        # Non-external provider, so just passes through
        assert result == event
