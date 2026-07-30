# Feature: risk-management
"""
Unit tests for WIF credential builder in sync_google_calendar handler.

Tests:
- _build_wif_credentials() returns correct audience and subject_token_type
- Lambda returns 500 with error message when WIF fails
- No fallback to SSM parameter read on WIF failure

Requirements: 2.1, 2.5
"""

import importlib.util
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Set required env vars before loading handler
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-west-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events-Test')
os.environ.setdefault('WIF_AUDIENCE', '//iam.googleapis.com/projects/1081576340476/locations/global/workloadIdentityPools/h-dcn-aws-pool/providers/aws-lambda-provider')
os.environ.setdefault('WIF_SERVICE_ACCOUNT_EMAIL', 'hdcn-portal@hdcn-portal.iam.gserviceaccount.com')

# Remove GOOGLE_CREDENTIALS_PARAMETER to ensure no SSM fallback
os.environ.pop('GOOGLE_CREDENTIALS_PARAMETER', None)

_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'sync_google_calendar', 'app.py')
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


class TestBuildWifCredentials:
    """Test _build_wif_credentials() configuration."""

    def _call_build_wif_credentials(self):
        """Helper: load handler and call _build_wif_credentials with mocked aws module."""
        with patch('boto3.client'), patch('boto3.resource'):
            app = _load_handler()

        mock_google_auth_aws = MagicMock()
        mock_credentials_instance = MagicMock()
        mock_google_auth_aws.Credentials.return_value = mock_credentials_instance

        # Patch at the google.auth.aws level so the handler's
        # `from google.auth import aws as google_auth_aws` resolves to our mock
        mock_google_auth = MagicMock()
        mock_google_auth.aws = mock_google_auth_aws

        with patch.dict('sys.modules', {
            'google': MagicMock(),
            'google.auth': mock_google_auth,
            'google.auth.aws': mock_google_auth_aws,
        }):
            result = app._build_wif_credentials()

        return mock_google_auth_aws, result

    def test_returns_correct_audience(self):
        """WIF credentials should have the correct audience for h-dcn-aws-pool."""
        mock_idp, _ = self._call_build_wif_credentials()
        call_kwargs = mock_idp.Credentials.call_args[1]
        assert call_kwargs['audience'] == '//iam.googleapis.com/projects/1081576340476/locations/global/workloadIdentityPools/h-dcn-aws-pool/providers/aws-lambda-provider'

    def test_returns_correct_subject_token_type(self):
        """WIF credentials should use aws4_request subject token type."""
        mock_idp, _ = self._call_build_wif_credentials()
        call_kwargs = mock_idp.Credentials.call_args[1]
        assert call_kwargs['subject_token_type'] == 'urn:ietf:params:aws:token-type:aws4_request'

    def test_uses_correct_service_account_impersonation(self):
        """WIF credentials should impersonate the correct service account."""
        mock_idp, _ = self._call_build_wif_credentials()
        call_kwargs = mock_idp.Credentials.call_args[1]
        assert 'hdcn-portal@hdcn-portal.iam.gserviceaccount.com' in call_kwargs['service_account_impersonation_url']

    def test_uses_calendar_scope(self):
        """WIF credentials should request calendar scope."""
        mock_idp, _ = self._call_build_wif_credentials()
        call_kwargs = mock_idp.Credentials.call_args[1]
        assert 'https://www.googleapis.com/auth/calendar' in call_kwargs['scopes']


class TestWifFailureHandling:
    """Test that WIF failure returns 500 with no SSM fallback."""

    def test_sync_returns_500_on_wif_failure(self):
        """Lambda returns HTTP 500 when WIF authentication fails."""
        with patch('boto3.client') as mock_client, patch('boto3.resource'):
            app = _load_handler()

        # Mock WIF to raise an exception
        mock_google_auth_aws = MagicMock()
        mock_google_auth_aws.Credentials.side_effect = Exception("WIF token exchange failed: invalid audience")

        request_body = json.dumps({
            'event_id': 'test-123',
            'action': 'sync',
            'event_data': {
                'name': 'Test Event',
                'start_date': '2026-08-01',
                'end_date': '2026-08-02',
            }
        })

        event = {
            'httpMethod': 'POST',
            'body': request_body,
            'headers': {'Authorization': 'Bearer test'},
        }

        with patch.dict('sys.modules', {'google.auth.aws': mock_google_auth_aws, 'google.auth': MagicMock()}):
            with patch.object(app, 'handle_options_request'), \
                 patch.object(app, 'cors_headers', return_value={}):
                response = app.lambda_handler(event, None)

        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'Google authentication failed' in body.get('message', body.get('error', ''))

    def test_no_ssm_fallback_on_wif_failure(self):
        """Verify no SSM GetParameter is called when WIF fails."""
        mock_ssm = MagicMock()
        with patch('boto3.client', return_value=mock_ssm), patch('boto3.resource'):
            app = _load_handler()

        mock_google_auth_aws = MagicMock()
        mock_google_auth_aws.Credentials.side_effect = Exception("WIF failed")

        request_body = json.dumps({
            'event_id': 'test-456',
            'action': 'sync',
            'event_data': {
                'name': 'Test Event',
                'start_date': '2026-08-01',
                'end_date': '2026-08-02',
            }
        })

        event = {
            'httpMethod': 'POST',
            'body': request_body,
            'headers': {'Authorization': 'Bearer test'},
        }

        with patch.dict('sys.modules', {'google.auth.aws': mock_google_auth_aws, 'google.auth': MagicMock()}):
            app.lambda_handler(event, None)

        # SSM get_parameter should never be called (no fallback)
        mock_ssm.get_parameter.assert_not_called()
