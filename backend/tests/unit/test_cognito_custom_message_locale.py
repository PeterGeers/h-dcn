"""
Unit tests for Cognito Custom Message Lambda locale handling.

Tests that the handler correctly:
- Extracts clientMetadata.locale from the event
- Resolves valid locales for template rendering
- Falls back to Dutch for missing/invalid locales
- Passes the resolved locale to all message handler functions

Requirements: 7.1, 7.2, 7.4, 11.4, 11.5
"""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# Add handler path so we can import the cognito_custom_message app
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'cognito_custom_message')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Remove any cached 'app' module from other test files (e.g., generate_order_pdf)
# to ensure we import the correct cognito_custom_message handler
if 'app' in sys.modules:
    del sys.modules['app']
if 'template_service' in sys.modules:
    del sys.modules['template_service']


def _make_cognito_event(trigger_source, locale=None, include_metadata=True):
    """
    Helper to build a Cognito Custom Message trigger event.

    Args:
        trigger_source: The triggerSource value (e.g., 'CustomMessage_AdminCreateUser')
        locale: The locale to include in clientMetadata, or None to omit
        include_metadata: Whether to include clientMetadata at all
    """
    client_metadata = {}
    if include_metadata and locale is not None:
        client_metadata = {'locale': locale}
    elif not include_metadata:
        client_metadata = None

    event = {
        'version': '1',
        'triggerSource': trigger_source,
        'region': 'eu-west-1',
        'userPoolId': 'eu-west-1_test',
        'userName': 'testuser',
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-js-3.0.0',
            'clientId': 'test-client-id'
        },
        'request': {
            'userAttributes': {
                'email': 'test@h-dcn.nl',
                'given_name': 'Jan',
                'family_name': 'de Tester'
            },
            'codeParameter': '{####}',
            'tempPassword': 'TempPass123!',
            'clientMetadata': client_metadata,
        },
        'response': {
            'emailMessage': None,
            'emailSubject': None,
        }
    }
    return event


@pytest.fixture(autouse=True)
def _clean_app_module():
    """Ensure cognito_custom_message app is loaded fresh for this test module."""
    # Remove any cached 'app' module from other test files (e.g., generate_order_pdf)
    if 'app' in sys.modules:
        del sys.modules['app']
    if 'template_service' in sys.modules:
        del sys.modules['template_service']
    # Ensure cognito handler path is at front of sys.path
    if _handler_path in sys.path:
        sys.path.remove(_handler_path)
    sys.path.insert(0, _handler_path)
    yield
    # Cleanup after tests in this module — remove handler path and clear modules
    if _handler_path in sys.path:
        sys.path.remove(_handler_path)
    if 'app' in sys.modules:
        del sys.modules['app']
    if 'template_service' in sys.modules:
        del sys.modules['template_service']


@pytest.fixture
def import_handler():
    """Import the handler module with mocked template_service."""
    # Need to mock boto3 before importing to avoid S3 client creation
    with patch('template_service.boto3'):
        import app
        yield app


@pytest.fixture
def mock_template_service(import_handler):
    """Mock the template_service to avoid S3 calls.

    Depends on import_handler to ensure app is imported first.
    """
    with patch.object(import_handler, 'template_service') as mock_ts:
        mock_ts.render_template = MagicMock(
            return_value=('Test Subject', 'Test email body')
        )
        yield mock_ts


class TestCognitoLocaleExtraction:
    """Tests that clientMetadata.locale is correctly extracted from the event."""

    def test_valid_locale_extracted_from_client_metadata(self, mock_template_service, import_handler):
        """clientMetadata.locale = 'en' should resolve to 'en'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='en')

        result = import_handler.lambda_handler(event, None)

        # Verify template_service was called with locale='en'
        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='en'
        )

    def test_french_locale_extracted(self, mock_template_service, import_handler):
        """clientMetadata.locale = 'fr' should resolve to 'fr'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='fr')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='fr'
        )

    def test_german_locale_extracted(self, mock_template_service, import_handler):
        """clientMetadata.locale = 'de' should resolve to 'de'."""
        event = _make_cognito_event('CustomMessage_AdminCreateUser', locale='de')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'welcome-user',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'TEMP_PASSWORD': 'TempPass123!'},
            locale='de'
        )

    @pytest.mark.parametrize("locale", ['nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'])
    def test_all_supported_locales_pass_through(self, mock_template_service, import_handler, locale):
        """All 8 supported locales should be passed to template rendering."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale=locale)

        import_handler.lambda_handler(event, None)

        call_kwargs = mock_template_service.render_template.call_args
        assert call_kwargs[1]['locale'] == locale or call_kwargs[0][2] == locale


class TestCognitoLocaleFallback:
    """Tests that invalid/missing locale falls back to Dutch (nl)."""

    def test_missing_locale_falls_back_to_dutch(self, mock_template_service, import_handler):
        """When clientMetadata has no 'locale' key, should use 'nl'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale=None)

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='nl'
        )

    def test_null_client_metadata_falls_back_to_dutch(self, mock_template_service, import_handler):
        """When clientMetadata is None, should use 'nl'."""
        event = _make_cognito_event('CustomMessage_ResendCode', include_metadata=False)

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='nl'
        )

    def test_invalid_locale_falls_back_to_dutch(self, mock_template_service, import_handler):
        """Unsupported locale 'zh' should fall back to 'nl'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='zh')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='nl'
        )

    def test_empty_string_locale_falls_back_to_dutch(self, mock_template_service, import_handler):
        """Empty string locale should fall back to 'nl'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='nl'
        )

    def test_gibberish_locale_falls_back_to_dutch(self, mock_template_service, import_handler):
        """Random gibberish locale should fall back to 'nl'."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='xyz123')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='nl'
        )


class TestCognitoLocalePassedToAllHandlers:
    """Tests that the resolved locale is correctly passed to all message handler functions."""

    def test_admin_create_user_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_AdminCreateUser passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_AdminCreateUser', locale='es')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'welcome-user',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'TEMP_PASSWORD': 'TempPass123!'},
            locale='es'
        )

    def test_resend_code_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_ResendCode passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='sv')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='sv'
        )

    def test_forgot_password_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_ForgotPassword passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_ForgotPassword', locale='da')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'passwordless-recovery',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='da'
        )

    def test_authentication_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_Authentication passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_Authentication', locale='it')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'authentication',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='it'
        )

    def test_update_user_attribute_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_UpdateUserAttribute passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_UpdateUserAttribute', locale='fr')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'update-user-attribute',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='fr'
        )

    def test_verify_user_attribute_receives_locale(self, mock_template_service, import_handler):
        """CustomMessage_VerifyUserAttribute passes locale to template_service."""
        event = _make_cognito_event('CustomMessage_VerifyUserAttribute', locale='en')

        import_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'verify-user-attribute',
            {'DISPLAY_NAME': 'Jan de Tester', 'EMAIL': 'test@h-dcn.nl', 'CODE': '{####}'},
            locale='en'
        )


class TestCognitoResponseStructure:
    """Tests that the handler correctly sets the email response fields."""

    def test_response_contains_email_message(self, mock_template_service, import_handler):
        """Handler should set response emailMessage from template rendering."""
        mock_template_service.render_template.return_value = ('Welcome!', '<p>Welcome body</p>')
        event = _make_cognito_event('CustomMessage_AdminCreateUser', locale='en')

        result = import_handler.lambda_handler(event, None)

        assert result['response']['emailMessage'] == '<p>Welcome body</p>'
        assert result['response']['emailSubject'] == 'Welcome!'

    def test_response_contains_email_subject(self, mock_template_service, import_handler):
        """Handler should set response emailSubject from template rendering."""
        mock_template_service.render_template.return_value = ('Código de verificación', 'Body text')
        event = _make_cognito_event('CustomMessage_ResendCode', locale='es')

        result = import_handler.lambda_handler(event, None)

        assert result['response']['emailSubject'] == 'Código de verificación'

    def test_handler_returns_event_on_error(self, mock_template_service, import_handler):
        """On exception, handler should return the original event to prevent auth failure."""
        mock_template_service.render_template.side_effect = Exception("S3 error")
        event = _make_cognito_event('CustomMessage_ResendCode', locale='en')

        # The handler has a try/except at the top level and inline fallbacks
        # For ResendCode, the template_service failure means the inline fallback won't be
        # triggered because the exception propagates from template_service.render_template
        # which is called directly (no try/except around it in handle_resend_code)
        # But the top-level try/except in lambda_handler catches it
        result = import_handler.lambda_handler(event, None)

        # Should return event without crashing
        assert result is not None
        assert 'response' in result
