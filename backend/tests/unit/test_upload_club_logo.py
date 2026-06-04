"""
Unit tests for the upload_club_logo Lambda handler.

Tests happy path, edge cases, auth flows, and error conditions.
Requirements validated: 4.1, 4.2, 4.7, 4.8, 5.2, 5.3, 5.5, 5.6
"""

import base64
import io
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

# Add handler path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'upload_club_logo'))

# Set environment variables before importing handler
os.environ['FRONTEND_BUCKET_NAME'] = 'h-dcn-frontend-506221081911'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['COGNITO_USER_POOL_ID'] = 'eu-west-1_test'


# --- Helpers ---

def _create_test_image(width=100, height=100, fmt='JPEG') -> bytes:
    """Create a real image of given dimensions and format, return raw bytes."""
    img = Image.new('RGB', (width, height), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return buffer.getvalue()


def _make_event(body: dict, user_email='user@club.nl') -> dict:
    """Build a Lambda API Gateway event with given body."""
    return {
        'httpMethod': 'POST',
        'headers': {'Authorization': 'Bearer mock-token'},
        'body': json.dumps(body),
        'queryStringParameters': None,
        'pathParameters': None,
    }


def _encode_image(image_bytes: bytes) -> str:
    """Base64-encode image bytes."""
    return base64.b64encode(image_bytes).decode('utf-8')


def _mock_auth(user_email='user@club.nl', user_roles=None):
    """Patch extract_user_credentials to return given email and roles."""
    if user_roles is None:
        user_roles = ['hdcnLeden', 'Regio_Pressmeet']
    return patch(
        'app.extract_user_credentials',
        return_value=(user_email, user_roles, None),
    )


def _mock_club_id(club_id='club-123'):
    """Patch get_club_id to return a specific club_id."""
    return patch('app.get_club_id', return_value=club_id)


def _mock_s3():
    """Patch the s3_client.put_object to a MagicMock."""
    mock = MagicMock()
    return patch('app.s3_client', mock), mock


def _mock_log():
    """Patch log_successful_access."""
    return patch('app.log_successful_access')


# --- Tests ---

class TestUploadClubLogoHappyPath:
    """Happy path: valid image upload → resized PNG in S3, correct response."""

    def test_valid_jpeg_upload_returns_200_with_logo_url(self):
        """Validates: Requirements 4.1, 4.2"""
        from app import lambda_handler

        image_bytes = _create_test_image(400, 300, 'JPEG')
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('club-123'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        resp_body = json.loads(response['body'])
        assert resp_body['message'] == 'Logo uploaded successfully'
        assert 'assets/presmeet/logos/club-123.png?t=' in resp_body['logo_url']

        # Verify S3 was called with correct params
        s3_mock.put_object.assert_called_once()
        call_kwargs = s3_mock.put_object.call_args[1]
        assert call_kwargs['Bucket'] == 'h-dcn-frontend-506221081911'
        assert call_kwargs['Key'] == 'assets/presmeet/logos/club-123.png'
        assert call_kwargs['ContentType'] == 'image/png'
        assert call_kwargs['CacheControl'] == 'max-age=0, must-revalidate'

        # Verify uploaded bytes are valid PNG
        uploaded_bytes = call_kwargs['Body']
        assert uploaded_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_valid_png_upload_returns_200(self):
        """PNG input is also accepted and re-saved as PNG."""
        from app import lambda_handler

        image_bytes = _create_test_image(150, 150, 'PNG')
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': 'my-club',
            'content_type': 'image/png',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('my-club'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_resized_image_fits_within_200x200(self):
        """Validates: Requirements 4.1 — output fits within 200×200 bounding box."""
        from app import lambda_handler

        # Create a large image (800x400) that needs significant downscaling
        image_bytes = _create_test_image(800, 400, 'JPEG')
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('club-123'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200

        # Verify the uploaded PNG dimensions
        uploaded_bytes = s3_mock.put_object.call_args[1]['Body']
        result_img = Image.open(io.BytesIO(uploaded_bytes))
        assert result_img.width <= 200
        assert result_img.height <= 200
        assert result_img.width == 200 or result_img.height == 200


class TestUploadClubLogoSizeEdgeCases:
    """Edge cases for the 5MB size limit."""

    def test_exactly_5mb_file_is_accepted(self):
        """Validates: Requirements 4.8 — exactly 5MB decoded payload is accepted."""
        from app import lambda_handler, MAX_IMAGE_SIZE

        # Create image bytes padded to exactly 5MB
        # We need the decoded bytes to be exactly MAX_IMAGE_SIZE
        # Use a real small image + pad with zeros in a valid way
        # Actually, we create a small valid image, then test that the size check
        # accepts exactly MAX_IMAGE_SIZE bytes
        small_image = _create_test_image(50, 50, 'JPEG')

        # Pad to exactly 5MB (append after JPEG data - the handler decodes base64
        # then checks size before Pillow opens it, so the size check happens on raw bytes)
        padded = small_image + b'\x00' * (MAX_IMAGE_SIZE - len(small_image))
        assert len(padded) == MAX_IMAGE_SIZE

        body = {
            'image_data': _encode_image(padded),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('club-123'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        # Size check passes (not 413), but Pillow may fail on the padded data
        # The important thing is it's NOT a 413
        assert response['statusCode'] != 413

    def test_5mb_plus_one_byte_is_rejected_with_413(self):
        """Validates: Requirements 4.8 — 5MB + 1 byte returns 413."""
        from app import lambda_handler, MAX_IMAGE_SIZE

        # Create payload that is exactly 1 byte over the limit
        oversized = b'\x00' * (MAX_IMAGE_SIZE + 1)

        body = {
            'image_data': _encode_image(oversized),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('club-123'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 413
        resp_body = json.loads(response['body'])
        assert 'Image too large' in resp_body['error']
        # Verify S3 was NOT called
        s3_mock.put_object.assert_not_called()


class TestUploadClubLogoSpecialCharacters:
    """Edge case: club_id with special characters."""

    def test_club_id_with_special_characters_in_s3_key(self):
        """Club IDs with hyphens, underscores, and dots are stored correctly."""
        from app import lambda_handler

        image_bytes = _create_test_image(100, 100, 'JPEG')
        club_id = 'club-xyz_123.test'
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': club_id,
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id(club_id), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        call_kwargs = s3_mock.put_object.call_args[1]
        assert call_kwargs['Key'] == f'assets/presmeet/logos/{club_id}.png'

        resp_body = json.loads(response['body'])
        assert club_id in resp_body['logo_url']


class TestUploadClubLogoAuth:
    """Auth flow tests with mocked Cognito/DynamoDB."""

    def test_missing_auth_token_returns_401(self):
        """Validates: Requirements 5.2 — no auth returns 401."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        # Mock extract_user_credentials to return auth error
        auth_error = {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Authorization header required'}),
        }
        with patch('app.extract_user_credentials', return_value=(None, None, auth_error)), \
             _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 401

    def test_user_with_no_club_id_returns_403(self):
        """Validates: Requirements 5.3 — no club_id assigned returns 403."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        # get_club_id returns None (user has no club assigned)
        with _mock_auth(), patch('app.get_club_id', return_value=None), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        resp_body = json.loads(response['body'])
        assert 'No club assignment found' in resp_body['error']

    def test_club_id_mismatch_non_admin_returns_403(self):
        """Validates: Requirements 5.5 — non-admin cannot upload for other club."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'club_id': 'other-club',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        # User belongs to 'club-123' but tries to upload for 'other-club'
        with _mock_auth(user_roles=['hdcnLeden']), \
             _mock_club_id('club-123'), \
             _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        resp_body = json.loads(response['body'])
        assert 'Not authorized' in resp_body['error']

    def test_admin_override_allows_any_club_id(self):
        """Validates: Requirements 5.6 — Products_CRUD can upload for any club."""
        from app import lambda_handler

        image_bytes = _create_test_image(100, 100, 'JPEG')
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': 'other-club',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        # User belongs to 'club-123' but has Products_CRUD admin role
        with _mock_auth(user_roles=['hdcnLeden', 'Products_CRUD']), \
             _mock_club_id('club-123'), \
             s3_patch, \
             _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_webshop_management_admin_override(self):
        """Validates: Requirements 5.6 — Webshop_Management can upload for any club."""
        from app import lambda_handler

        image_bytes = _create_test_image(100, 100, 'JPEG')
        body = {
            'image_data': _encode_image(image_bytes),
            'club_id': 'other-club',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(user_roles=['Webshop_Management']), \
             _mock_club_id('club-123'), \
             s3_patch, \
             _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200


class TestUploadClubLogoValidation:
    """Test missing fields and invalid content_type."""

    def test_missing_image_data_returns_400(self):
        """Validates: Requirements 4.7 — missing required field."""
        from app import lambda_handler

        body = {
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'image_data' in resp_body['error']

    def test_missing_club_id_returns_400(self):
        """Missing club_id returns 400."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'club_id' in resp_body['error']

    def test_missing_content_type_returns_400(self):
        """Missing content_type returns 400."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'club_id': 'club-123',
        }
        event = _make_event(body)

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'content_type' in resp_body['error']

    def test_invalid_content_type_returns_400(self):
        """Validates: Requirements 4.7 — unsupported content type is rejected."""
        from app import lambda_handler

        body = {
            'image_data': _encode_image(_create_test_image()),
            'club_id': 'club-123',
            'content_type': 'application/pdf',
        }
        event = _make_event(body)

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'Invalid content type' in resp_body['error']

    def test_invalid_base64_returns_400(self):
        """Invalid base64 encoding returns 400."""
        from app import lambda_handler

        body = {
            'image_data': '!!!not-valid-base64!!!',
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'base64' in resp_body['error'].lower() or 'Invalid' in resp_body['error']

    def test_non_image_data_returns_400(self):
        """Validates: Requirements 4.2, 4.7 — random bytes (not an image) returns 400."""
        from app import lambda_handler

        # Random bytes that are not a valid image
        random_bytes = b'This is not an image file at all. Just random text data.'
        body = {
            'image_data': _encode_image(random_bytes),
            'club_id': 'club-123',
            'content_type': 'image/jpeg',
        }
        event = _make_event(body)

        s3_patch, s3_mock = _mock_s3()
        with _mock_auth(), _mock_club_id('club-123'), s3_patch, _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        resp_body = json.loads(response['body'])
        assert 'Invalid image file' in resp_body['error']
        # Verify S3 was NOT called
        s3_mock.put_object.assert_not_called()

    def test_empty_body_returns_400(self):
        """Empty/no body returns 400 for missing fields."""
        from app import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'Authorization': 'Bearer mock-token'},
            'body': None,
            'queryStringParameters': None,
            'pathParameters': None,
        }

        with _mock_auth(), _mock_club_id('club-123'), _mock_log():
            response = lambda_handler(event, None)

        assert response['statusCode'] == 400
