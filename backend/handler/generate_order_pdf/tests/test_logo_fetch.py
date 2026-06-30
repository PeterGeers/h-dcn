"""Unit tests for fetch_logo_as_data_uri function."""
import base64
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

import sys
import os

# Add the handler directory to the path so we can import the function directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the shared auth layer before importing app
sys.modules['shared'] = MagicMock()
sys.modules['shared.auth_utils'] = MagicMock()
sys.modules['shared.maintenance_fallback'] = MagicMock()

from app import fetch_logo_as_data_uri


class TestFetchLogoAsDataUri:
    """Tests for the fetch_logo_as_data_uri function."""

    @patch('app.boto3.client')
    def test_successful_fetch_returns_data_uri(self, mock_boto_client):
        """Test that a successful S3 fetch returns a properly formatted data URI."""
        # Arrange
        test_bytes = b'\x89PNG\r\n\x1a\n fake png data'
        expected_b64 = base64.b64encode(test_bytes).decode('utf-8')

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_body = MagicMock()
        mock_body.read.return_value = test_bytes
        mock_s3.get_object.return_value = {
            'ContentType': 'image/png',
            'Body': mock_body
        }

        # Act
        result = fetch_logo_as_data_uri('my-hdcn-bucket', 'imagesWebsite/hdcnFavico.png')

        # Assert
        assert result == f"data:image/png;base64,{expected_b64}"
        mock_s3.get_object.assert_called_once_with(
            Bucket='my-hdcn-bucket',
            Key='imagesWebsite/hdcnFavico.png'
        )

    @patch('app.boto3.client')
    def test_client_error_returns_none(self, mock_boto_client):
        """Test that a ClientError (e.g. NoSuchKey) returns None."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'GetObject'
        )

        result = fetch_logo_as_data_uri('my-hdcn-bucket', 'imagesWebsite/hdcnFavico.png')

        assert result is None

    @patch('app.boto3.client')
    def test_access_denied_returns_none(self, mock_boto_client):
        """Test that an AccessDenied error returns None."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GetObject'
        )

        result = fetch_logo_as_data_uri('my-hdcn-bucket', 'imagesWebsite/hdcnFavico.png')

        assert result is None

    @patch('app.boto3.client')
    def test_botocore_error_returns_none(self, mock_boto_client):
        """Test that a BotoCoreError (e.g. timeout) returns None."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.side_effect = BotoCoreError()

        result = fetch_logo_as_data_uri('my-hdcn-bucket', 'imagesWebsite/hdcnFavico.png')

        assert result is None

    @patch('app.boto3.client')
    def test_unexpected_exception_returns_none(self, mock_boto_client):
        """Test that any unexpected exception returns None."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.side_effect = RuntimeError("Something unexpected")

        result = fetch_logo_as_data_uri('my-hdcn-bucket', 'imagesWebsite/hdcnFavico.png')

        assert result is None

    @patch('app.boto3.client')
    def test_custom_timeout_passed_to_config(self, mock_boto_client):
        """Test that the timeout parameter is passed to the boto3 Config."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_body = MagicMock()
        mock_body.read.return_value = b'test'
        mock_s3.get_object.return_value = {
            'ContentType': 'image/jpeg',
            'Body': mock_body
        }

        fetch_logo_as_data_uri('bucket', 'key', timeout=10)

        # Verify boto3.client was called with a config that has the right timeout
        call_kwargs = mock_boto_client.call_args
        config = call_kwargs[1]['config']
        assert config.read_timeout == 10
        assert config.connect_timeout == 10

    @patch('app.boto3.client')
    def test_different_content_types(self, mock_boto_client):
        """Test that different content types are correctly included in the data URI."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_body = MagicMock()
        mock_body.read.return_value = b'jpeg data'
        mock_s3.get_object.return_value = {
            'ContentType': 'image/jpeg',
            'Body': mock_body
        }

        result = fetch_logo_as_data_uri('bucket', 'key.jpg')

        expected_b64 = base64.b64encode(b'jpeg data').decode('utf-8')
        assert result == f"data:image/jpeg;base64,{expected_b64}"
