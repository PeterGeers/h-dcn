"""
Unit tests for localized error response integration.

Validates that create_error_response() produces responses containing both
a stable error_key for programmatic use and a localized message for display,
and that key handlers resolve locale from Accept-Language and pass it through.

Requirements validated: 6.2, 6.3, 6.4
"""

import json
import sys
import os

# Add layers to path for shared module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from shared.auth_utils import create_error_response
from shared.i18n.locale_resolver import resolve_request_locale


class TestCreateErrorResponseLocalization:
    """Test create_error_response with error_key and locale parameters."""

    def test_includes_error_key_in_body(self):
        """Error response includes error_key field when provided."""
        response = create_error_response(400, 'Bad request', error_key='validation_error', locale='en')
        body = json.loads(response['body'])
        assert 'error_key' in body
        assert body['error_key'] == 'validation_error'

    def test_includes_localized_message_in_body(self):
        """Error response includes localized message when error_key and locale provided."""
        response = create_error_response(403, 'Access denied', error_key='forbidden', locale='en')
        body = json.loads(response['body'])
        assert 'message' in body
        assert body['message'] == 'Access denied'

    def test_dutch_fallback_for_invalid_locale(self):
        """Error response falls back to Dutch for invalid locale."""
        response = create_error_response(403, 'Fallback', error_key='forbidden', locale='xx')
        body = json.loads(response['body'])
        assert body['message'] == 'Toegang geweigerd'

    def test_dutch_fallback_for_missing_locale(self):
        """Error response falls back to Dutch when locale is None."""
        response = create_error_response(403, 'Fallback', error_key='forbidden', locale=None)
        body = json.loads(response['body'])
        assert body['message'] == 'Toegang geweigerd'

    def test_french_localization(self):
        """Error response returns French message for locale='fr'."""
        response = create_error_response(500, 'Error', error_key='internal_error', locale='fr')
        body = json.loads(response['body'])
        assert body['message'] == 'Erreur interne du serveur'

    def test_german_localization(self):
        """Error response returns German message for locale='de'."""
        response = create_error_response(404, 'Not found', error_key='not_found', locale='de')
        body = json.loads(response['body'])
        assert body['message'] == 'Nicht gefunden'

    def test_backward_compatible_without_error_key(self):
        """Error response works without error_key (backward compatible)."""
        response = create_error_response(500, 'Something went wrong')
        body = json.loads(response['body'])
        assert body['error'] == 'Something went wrong'
        assert 'error_key' not in body
        assert 'message' not in body

    def test_details_included_in_response(self):
        """Error response includes details alongside error_key and message."""
        response = create_error_response(400, 'Bad', details={'field': 'email'},
                                         error_key='validation_error', locale='en')
        body = json.loads(response['body'])
        assert body['error_key'] == 'validation_error'
        assert body['message'] == 'Validation error'
        assert body['field'] == 'email'

    def test_status_code_preserved(self):
        """Error response preserves the HTTP status code."""
        response = create_error_response(422, 'Unprocessable', error_key='validation_error', locale='en')
        assert response['statusCode'] == 422

    def test_cors_headers_present(self):
        """Error response includes CORS headers."""
        response = create_error_response(500, 'Error', error_key='internal_error', locale='en')
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert 'Accept-Language' in response['headers']['Access-Control-Allow-Headers']


class TestLocaleResolutionInHandlers:
    """Test that resolve_request_locale correctly extracts locale from events."""

    def test_resolves_from_accept_language_header(self):
        """Resolves locale from Accept-Language header."""
        event = {'headers': {'Accept-Language': 'en'}}
        assert resolve_request_locale(event) == 'en'

    def test_resolves_from_accept_language_with_region(self):
        """Resolves locale from Accept-Language with region subtag."""
        event = {'headers': {'Accept-Language': 'fr-FR'}}
        assert resolve_request_locale(event) == 'fr'

    def test_falls_back_to_dutch_for_unsupported(self):
        """Falls back to Dutch for unsupported locale."""
        event = {'headers': {'Accept-Language': 'zh-CN'}}
        assert resolve_request_locale(event) == 'nl'

    def test_falls_back_to_dutch_for_missing_header(self):
        """Falls back to Dutch when Accept-Language header is missing."""
        event = {'headers': {}}
        assert resolve_request_locale(event) == 'nl'

    def test_falls_back_to_dutch_for_empty_header(self):
        """Falls back to Dutch when Accept-Language header is empty."""
        event = {'headers': {'Accept-Language': ''}}
        assert resolve_request_locale(event) == 'nl'

    def test_handles_quality_values(self):
        """Resolves highest quality locale from Accept-Language with q-values."""
        event = {'headers': {'Accept-Language': 'zh;q=0.9,de;q=0.8,en;q=1.0'}}
        assert resolve_request_locale(event) == 'en'

    def test_case_insensitive_header_key(self):
        """Resolves locale from lowercase accept-language header."""
        event = {'headers': {'accept-language': 'sv'}}
        assert resolve_request_locale(event) == 'sv'
