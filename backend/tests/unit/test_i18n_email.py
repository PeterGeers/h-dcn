"""
Unit tests for email template selection and Cognito locale handling.

Validates:
- Template path resolution per locale (Req 7.1, 7.4)
- Fallback to Dutch templates for missing/invalid locales (Req 7.2)
- Cognito custom message reads clientMetadata.locale correctly (Req 11.4, 11.5)

Requirements: 7.1, 7.2, 7.4, 11.4, 11.5
"""

import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from shared.i18n.email_utils import (
    resolve_email_locale,
    get_email_template_path,
)
from shared.i18n.locale_resolver import SUPPORTED_LOCALES, DEFAULT_LOCALE

# Add handler path for cognito_custom_message imports
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cognito_event(trigger_source, locale=None, include_metadata=True):
    """Build a Cognito Custom Message trigger event for testing."""
    client_metadata = {}
    if include_metadata and locale is not None:
        client_metadata = {'locale': locale}
    elif not include_metadata:
        client_metadata = None

    return {
        'version': '1',
        'triggerSource': trigger_source,
        'region': 'eu-west-1',
        'userPoolId': 'eu-west-1_test',
        'userName': 'testuser',
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-js-3.0.0',
            'clientId': 'test-client-id',
        },
        'request': {
            'userAttributes': {
                'email': 'lid@h-dcn.nl',
                'given_name': 'Piet',
                'family_name': 'Ansen',
            },
            'codeParameter': '{####}',
            'tempPassword': 'Welkom123!',
            'clientMetadata': client_metadata,
        },
        'response': {
            'emailMessage': None,
            'emailSubject': None,
        },
    }


# ---------------------------------------------------------------------------
# Template path resolution per locale (Req 7.1, 7.4)
# ---------------------------------------------------------------------------


class TestTemplatePathResolutionPerLocale:
    """
    Validates Requirement 7.1: Email uses member's preferred_language to select template.
    Validates Requirement 7.4: Falls back to Dutch template when locale template doesn't exist.
    """

    @pytest.mark.parametrize("locale", sorted(SUPPORTED_LOCALES))
    def test_each_supported_locale_resolves_to_locale_path(self, locale):
        """Each supported locale resolves to templates/{locale}/ path."""
        path = get_email_template_path("membership-application-confirmation.html", locale)
        assert path == f"templates/{locale}/membership-application-confirmation.html"

    def test_locale_selects_correct_template_directory(self):
        """Req 7.1 — preferred_language determines the template directory."""
        assert get_email_template_path("welcome-user.html", "en") == "templates/en/welcome-user.html"
        assert get_email_template_path("welcome-user.html", "fr") == "templates/fr/welcome-user.html"
        assert get_email_template_path("welcome-user.html", "de") == "templates/de/welcome-user.html"

    def test_filesystem_lookup_picks_locale_file_when_present(self):
        """When locale template exists on disk, it is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sv_dir = os.path.join(tmpdir, "sv")
            os.makedirs(sv_dir)
            sv_template = os.path.join(sv_dir, "resend-code.html")
            with open(sv_template, "w") as f:
                f.write("<html>Swedish template</html>")

            result = get_email_template_path("resend-code.html", "sv", tmpdir)
            assert result == sv_template

    def test_filesystem_fallback_to_nl_when_locale_template_missing(self):
        """Req 7.4 — falls back to Dutch template when locale template doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nl_dir = os.path.join(tmpdir, "nl")
            os.makedirs(nl_dir)
            nl_template = os.path.join(nl_dir, "passwordless-recovery.html")
            with open(nl_template, "w") as f:
                f.write("<html>Dutch fallback</html>")

            # Italian directory doesn't exist — should fall back to nl
            result = get_email_template_path("passwordless-recovery.html", "it", tmpdir)
            assert result == nl_template

    def test_filesystem_fallback_when_locale_dir_exists_but_file_missing(self):
        """Req 7.4 — falls back to Dutch when locale dir exists but specific template is absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create both locale dirs, but only nl has the template
            da_dir = os.path.join(tmpdir, "da")
            nl_dir = os.path.join(tmpdir, "nl")
            os.makedirs(da_dir)
            os.makedirs(nl_dir)
            nl_template = os.path.join(nl_dir, "welcome-user.html")
            with open(nl_template, "w") as f:
                f.write("<html>Dutch welcome</html>")

            result = get_email_template_path("welcome-user.html", "da", tmpdir)
            assert result == nl_template


# ---------------------------------------------------------------------------
# Fallback to Dutch templates for missing/invalid locales (Req 7.2)
# ---------------------------------------------------------------------------


class TestFallbackToDutchForInvalidLocale:
    """
    Validates Requirement 7.2: Falls back to Dutch when preference is empty/null/invalid.
    """

    def test_none_preferred_language_resolves_to_nl(self):
        """None preferred_language → Dutch."""
        assert resolve_email_locale(None) == "nl"

    def test_empty_string_resolves_to_nl(self):
        """Empty string → Dutch."""
        assert resolve_email_locale("") == "nl"

    def test_whitespace_only_resolves_to_nl(self):
        """Whitespace-only string → Dutch."""
        assert resolve_email_locale("   ") == "nl"

    def test_unsupported_locale_resolves_to_nl(self):
        """Locale not in SUPPORTED_LOCALES → Dutch."""
        assert resolve_email_locale("pt") == "nl"
        assert resolve_email_locale("ja") == "nl"
        assert resolve_email_locale("zh-CN") == "nl"

    def test_numeric_value_resolves_to_nl(self):
        """Non-string value → Dutch."""
        assert resolve_email_locale(42) == "nl"

    def test_invalid_locale_template_path_falls_back_to_nl(self):
        """Invalid locale in template path resolution → templates/nl/."""
        path = get_email_template_path("resend-code.html", "xx")
        assert path == "templates/nl/resend-code.html"

    def test_none_locale_template_path_falls_back_to_nl(self):
        """None locale in template path → templates/nl/."""
        path = get_email_template_path("welcome-user.html", None)
        assert path == "templates/nl/welcome-user.html"

    def test_valid_locale_does_not_fallback(self):
        """Confirm valid locales are not redirected to Dutch."""
        for locale in SUPPORTED_LOCALES:
            assert resolve_email_locale(locale) == locale


# ---------------------------------------------------------------------------
# Cognito custom message reads clientMetadata.locale (Req 11.4, 11.5)
# ---------------------------------------------------------------------------


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
def cognito_handler():
    """Import the cognito_custom_message handler with mocked template_service."""
    with patch('template_service.boto3'):
        import app
        yield app


@pytest.fixture
def mock_template_service(cognito_handler):
    """Mock template_service to avoid S3/file access in tests.

    Depends on cognito_handler to ensure app is imported first.
    """
    with patch.object(cognito_handler, 'template_service') as mock_ts:
        mock_ts.render_template = MagicMock(
            return_value=('Test Subject', '<p>Test body</p>')
        )
        yield mock_ts


class TestCognitoReadsClientMetadataLocale:
    """
    Validates Requirement 11.4: Cognito custom message reads clientMetadata.locale
    for email language.
    """

    def test_locale_from_client_metadata_passed_to_template(
        self, mock_template_service, cognito_handler
    ):
        """Req 11.4 — locale in clientMetadata selects email language."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='en')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='en',
        )

    @pytest.mark.parametrize("locale", sorted(SUPPORTED_LOCALES))
    def test_all_supported_locales_forwarded(
        self, mock_template_service, cognito_handler, locale
    ):
        """Each supported locale in clientMetadata is passed to template rendering."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale=locale)

        cognito_handler.lambda_handler(event, None)

        call_args = mock_template_service.render_template.call_args
        # Check locale keyword or positional third argument
        passed_locale = call_args[1].get('locale') or call_args[0][2]
        assert passed_locale == locale

    def test_admin_create_user_uses_client_metadata_locale(
        self, mock_template_service, cognito_handler
    ):
        """AdminCreateUser trigger also respects clientMetadata.locale."""
        event = _make_cognito_event('CustomMessage_AdminCreateUser', locale='de')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'welcome-user',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'TEMP_PASSWORD': 'Welkom123!'},
            locale='de',
        )

    def test_authentication_trigger_uses_client_metadata_locale(
        self, mock_template_service, cognito_handler
    ):
        """Authentication trigger uses locale from clientMetadata."""
        event = _make_cognito_event('CustomMessage_Authentication', locale='it')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'authentication',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='it',
        )


class TestCognitoFallbackWhenLocaleAbsentOrInvalid:
    """
    Validates Requirement 11.5: Falls back to Dutch when clientMetadata locale
    is absent or invalid.
    """

    def test_missing_locale_key_falls_back_to_dutch(
        self, mock_template_service, cognito_handler
    ):
        """No 'locale' key in clientMetadata → Dutch."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale=None)

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='nl',
        )

    def test_null_client_metadata_falls_back_to_dutch(
        self, mock_template_service, cognito_handler
    ):
        """clientMetadata is None → Dutch."""
        event = _make_cognito_event('CustomMessage_ResendCode', include_metadata=False)

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='nl',
        )

    def test_invalid_locale_falls_back_to_dutch(
        self, mock_template_service, cognito_handler
    ):
        """Unsupported locale value → Dutch."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='zh')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='nl',
        )

    def test_empty_string_locale_falls_back_to_dutch(
        self, mock_template_service, cognito_handler
    ):
        """Empty string locale → Dutch."""
        event = _make_cognito_event('CustomMessage_ResendCode', locale='')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'resend-code',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='nl',
        )

    def test_gibberish_locale_falls_back_to_dutch(
        self, mock_template_service, cognito_handler
    ):
        """Random gibberish locale value → Dutch."""
        event = _make_cognito_event('CustomMessage_Authentication', locale='notareal99')

        cognito_handler.lambda_handler(event, None)

        mock_template_service.render_template.assert_called_once_with(
            'authentication',
            {'DISPLAY_NAME': 'Piet Ansen', 'EMAIL': 'lid@h-dcn.nl', 'CODE': '{####}'},
            locale='nl',
        )

    def test_handler_returns_event_on_unexpected_error(
        self, mock_template_service, cognito_handler
    ):
        """Handler returns event (no crash) even when template_service raises."""
        mock_template_service.render_template.side_effect = Exception("S3 timeout")
        event = _make_cognito_event('CustomMessage_ResendCode', locale='en')

        result = cognito_handler.lambda_handler(event, None)

        assert result is not None
        assert 'response' in result
