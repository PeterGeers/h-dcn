"""
Unit Tests for analyze_poster Lambda Handler.

Tests the poster analysis endpoint:
- Returns 400 when body is missing
- Returns 400 when neither image_data nor s3_key is provided
- Returns 200 with extracted event data on successful Gemini response
- Returns 502 when Gemini API fails
- Returns 502 when Gemini returns invalid JSON
- Handles S3 key input correctly
- Handles OPTIONS preflight request
"""

import base64
import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['GEMINI_API_KEY_PARAMETER'] = '/h-dcn/gemini-api-key'
os.environ['DATA_BUCKET'] = 'h-dcn-data-506221081911'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'analyze_poster', 'app.py')
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

FAKE_API_KEY = 'fake-gemini-api-key-12345'

SAMPLE_IMAGE_BASE64 = base64.b64encode(b'\x89PNG\r\n\x1a\nfake-image-data').decode('utf-8')

GEMINI_SUCCESS_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": json.dumps({
                            "name": "Toerweekend 2027",
                            "start_date": "2027-06-14",
                            "end_date": "2027-06-15",
                            "location": "Holysloot, Amsterdam",
                            "info": "Annual touring weekend organized by H-DCN Noord"
                        })
                    }
                ]
            }
        }
    ]
}

GEMINI_RESPONSE_WITH_CODE_FENCES = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": '```json\n{"name": "ALV 2027", "start_date": "2027-03-15", "end_date": "2027-03-15", "location": "Utrecht", "info": "Algemene Ledenvergadering"}\n```'
                    }
                ]
            }
        }
    ]
}


def _make_event(body: dict | None = None, method: str = 'POST') -> dict:
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'queryStringParameters': None,
        'pathParameters': None,
        'body': json.dumps(body) if body else None,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def handler():
    """Load the handler with mocked SSM and requests."""
    # Mock SSM client before loading the handler
    mock_ssm = MagicMock()
    mock_ssm.get_parameter.return_value = {
        'Parameter': {'Value': FAKE_API_KEY}
    }

    mock_s3 = MagicMock()

    with patch('boto3.client') as mock_boto3_client:
        def client_factory(service_name: str, **kwargs):
            if service_name == 'ssm':
                return mock_ssm
            elif service_name == 's3':
                return mock_s3
            return MagicMock()

        mock_boto3_client.side_effect = client_factory

        # Clear cached API key between tests
        module = _load_handler()
        module._cached_api_key = None

        yield module, mock_ssm, mock_s3


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAnalyzePoster:
    """Tests for the analyze_poster endpoint."""

    def test_options_request(self, handler):
        """CORS preflight returns 200."""
        module, _, _ = handler
        event = _make_event(method='OPTIONS')
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_missing_body_returns_400(self, handler):
        """Returns 400 when request body is missing."""
        module, _, _ = handler
        event = _make_event(body=None)
        event['body'] = None
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'body is required' in body['error'].lower()

    def test_invalid_json_body_returns_400(self, handler):
        """Returns 400 when body is not valid JSON."""
        module, _, _ = handler
        event = _make_event()
        event['body'] = 'not-valid-json{'
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'invalid json' in body['error'].lower()

    def test_missing_image_and_s3_key_returns_400(self, handler):
        """Returns 400 when neither image_data nor s3_key is provided."""
        module, _, _ = handler
        event = _make_event(body={'mime_type': 'image/png'})
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'image_data' in body['error'].lower() or 's3_key' in body['error'].lower()

    @patch('requests.post')
    def test_successful_analysis_with_base64(self, mock_post, handler):
        """Returns extracted event data on successful Gemini response."""
        module, _, _ = handler

        # Mock successful Gemini response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = GEMINI_SUCCESS_RESPONSE
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['name'] == 'Toerweekend 2027'
        assert body['start_date'] == '2027-06-14'
        assert body['end_date'] == '2027-06-15'
        assert body['location'] == 'Holysloot, Amsterdam'
        assert body['info'] == 'Annual touring weekend organized by H-DCN Noord'

    @patch('requests.post')
    def test_handles_code_fences_in_gemini_response(self, mock_post, handler):
        """Strips markdown code fences from Gemini's response."""
        module, _, _ = handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = GEMINI_RESPONSE_WITH_CODE_FENCES
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['name'] == 'ALV 2027'
        assert body['start_date'] == '2027-03-15'
        assert body['location'] == 'Utrecht'

    @patch('requests.post')
    def test_gemini_api_failure_returns_502(self, mock_post, handler):
        """Returns 502 when Gemini API returns non-200 status."""
        module, _, _ = handler

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert 'poster analysis failed' in body['error'].lower()

    @patch('requests.post')
    def test_gemini_connection_error_returns_502(self, mock_post, handler):
        """Returns 502 when connection to Gemini API fails."""
        module, _, _ = handler
        import requests as req_lib
        mock_post.side_effect = req_lib.ConnectionError("Connection refused")

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert 'failed' in body['error'].lower()

    @patch('requests.post')
    def test_gemini_invalid_json_response_returns_502(self, mock_post, handler):
        """Returns 502 when Gemini returns unparseable text."""
        module, _, _ = handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "This is not valid JSON at all"}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert 'invalid json' in body['error'].lower()

    @patch('requests.post')
    def test_s3_key_input(self, mock_post, handler):
        """Fetches image from S3 when s3_key is provided."""
        module, _, mock_s3 = handler

        # Mock S3 get_object response
        fake_image_bytes = b'\x89PNG\r\n\x1a\nfake-s3-image'
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=MagicMock(return_value=fake_image_bytes)),
            'ContentType': 'image/png',
        }

        # Mock successful Gemini response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = GEMINI_SUCCESS_RESPONSE
        mock_post.return_value = mock_response

        event = _make_event(body={
            's3_key': 'event-posters/test-poster.png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify S3 was called with correct params
        mock_s3.get_object.assert_called_once_with(
            Bucket='h-dcn-data-506221081911',
            Key='event-posters/test-poster.png',
        )

        body = json.loads(response['body'])
        assert body['name'] == 'Toerweekend 2027'

    def test_s3_key_not_found_returns_400(self, handler):
        """Returns 400 when S3 key does not exist."""
        module, _, mock_s3 = handler

        mock_s3.get_object.side_effect = Exception("NoSuchKey: The specified key does not exist")

        event = _make_event(body={
            's3_key': 'event-posters/nonexistent.png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'failed to retrieve' in body['error'].lower()

    @patch('requests.post')
    def test_default_mime_type_is_jpeg(self, mock_post, handler):
        """Uses image/jpeg as default mime type when not specified."""
        module, _, _ = handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = GEMINI_SUCCESS_RESPONSE
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            # No mime_type specified
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

        # Verify the call to Gemini used image/jpeg
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get('json') or call_kwargs[1].get('json')
        inline_data = payload['contents'][0]['parts'][1]['inline_data']
        assert inline_data['mime_type'] == 'image/jpeg'

    @patch('requests.post')
    def test_missing_fields_default_to_empty_string(self, mock_post, handler):
        """Missing fields in Gemini response default to empty string."""
        module, _, _ = handler

        # Gemini returns partial data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "name": "Some Event",
                                    "start_date": "2027-09-01",
                                    # end_date, location, info missing
                                })
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        event = _make_event(body={
            'image_data': SAMPLE_IMAGE_BASE64,
            'mime_type': 'image/png',
        })
        response = module.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['name'] == 'Some Event'
        assert body['start_date'] == '2027-09-01'
        assert body['end_date'] == ''
        assert body['location'] == ''
        assert body['info'] == ''
