"""
Unit tests for shared.mollie_client module.

Tests create_payment(), get_payment(), verify_webhook_signature(), and
error handling using mocked HTTP responses.
"""

import json
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

# Set env before import
os.environ["MOLLIE_API_KEY"] = "test_api_key_xxx"

from shared.mollie_client import (
    create_payment,
    get_payment,
    verify_webhook_signature,
    MollieError,
    SUPPORTED_METHODS,
)


class TestCreatePayment:
    """Tests for create_payment()."""

    @patch("shared.mollie_client.requests.post")
    def test_successful_payment_creation(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "tr_12345",
            "status": "open",
            "_links": {
                "checkout": {"href": "https://www.mollie.com/checkout/test"}
            },
        }
        mock_post.return_value = mock_response

        result = create_payment(
            amount="25.00",
            description="Test payment",
            redirect_url="https://portal.h-dcn.nl/return",
            webhook_url="https://api.h-dcn.nl/mollie-webhook",
            method="ideal",
        )

        assert result["mollie_payment_id"] == "tr_12345"
        assert result["checkout_url"] == "https://www.mollie.com/checkout/test"
        assert result["status"] == "open"

        # Verify the request payload
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["amount"] == {"currency": "EUR", "value": "25.00"}
        assert payload["description"] == "Test payment"
        assert payload["redirectUrl"] == "https://portal.h-dcn.nl/return"
        assert payload["webhookUrl"] == "https://api.h-dcn.nl/mollie-webhook"
        assert payload["method"] == "ideal"

    @patch("shared.mollie_client.requests.post")
    def test_payment_without_method(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "tr_99999",
            "status": "open",
            "_links": {"checkout": {"href": "https://www.mollie.com/checkout/abc"}},
        }
        mock_post.return_value = mock_response

        result = create_payment(
            amount="10.00",
            description="No method",
            redirect_url="https://portal.h-dcn.nl/return",
        )

        assert result["mollie_payment_id"] == "tr_99999"
        payload = mock_post.call_args.kwargs["json"]
        assert "method" not in payload
        assert "webhookUrl" not in payload

    @patch("shared.mollie_client.requests.post")
    def test_payment_with_creditcard(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "tr_cc001",
            "status": "open",
            "_links": {"checkout": {"href": "https://www.mollie.com/checkout/cc"}},
        }
        mock_post.return_value = mock_response

        result = create_payment(
            amount="50.00",
            description="Credit card test",
            redirect_url="https://portal.h-dcn.nl/return",
            method="creditcard",
        )

        assert result["mollie_payment_id"] == "tr_cc001"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["method"] == "creditcard"

    def test_unsupported_method_raises_error(self):
        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="10.00",
                description="Bad method",
                redirect_url="https://example.com",
                method="paypal",
            )
        assert "Unsupported payment method" in str(exc_info.value)

    @patch("shared.mollie_client.requests.post")
    def test_mollie_api_error_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "title": "Unprocessable Entity",
            "detail": "The amount is invalid",
        }
        mock_post.return_value = mock_response

        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="0.00",
                description="Invalid amount",
                redirect_url="https://example.com",
            )
        assert "Unprocessable Entity" in str(exc_info.value)
        assert exc_info.value.status_code == 422

    @patch("shared.mollie_client.requests.post")
    def test_timeout_raises_mollie_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.Timeout("Connection timed out")

        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="10.00",
                description="Timeout test",
                redirect_url="https://example.com",
            )
        assert "timed out" in str(exc_info.value)

    @patch("shared.mollie_client.requests.post")
    def test_connection_error_raises_mollie_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("DNS failure")

        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="10.00",
                description="Connection test",
                redirect_url="https://example.com",
            )
        assert "Unable to connect" in str(exc_info.value)

    @patch("shared.mollie_client.requests.post")
    def test_missing_checkout_url_raises_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "tr_nourl",
            "status": "open",
            "_links": {},
        }
        mock_post.return_value = mock_response

        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="10.00",
                description="Missing URL",
                redirect_url="https://example.com",
            )
        assert "checkout URL" in str(exc_info.value)


class TestGetPayment:
    """Tests for get_payment()."""

    @patch("shared.mollie_client.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "tr_12345",
            "status": "paid",
            "amount": {"currency": "EUR", "value": "25.00"},
            "description": "Test order",
            "metadata": {"order_id": "abc-123"},
        }
        mock_get.return_value = mock_response

        result = get_payment("tr_12345")

        assert result["id"] == "tr_12345"
        assert result["status"] == "paid"
        assert result["amount"] == {"currency": "EUR", "value": "25.00"}
        assert result["description"] == "Test order"
        assert result["metadata"] == {"order_id": "abc-123"}

    @patch("shared.mollie_client.requests.get")
    def test_payment_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "title": "Not Found",
            "detail": "The payment was not found",
        }
        mock_get.return_value = mock_response

        with pytest.raises(MollieError) as exc_info:
            get_payment("tr_nonexistent")
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value).lower()

    def test_empty_payment_id_raises_error(self):
        with pytest.raises(MollieError) as exc_info:
            get_payment("")
        assert "required" in str(exc_info.value)

    @patch("shared.mollie_client.requests.get")
    def test_timeout_raises_mollie_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()

        with pytest.raises(MollieError) as exc_info:
            get_payment("tr_timeout")
        assert "timed out" in str(exc_info.value)


class TestVerifyWebhookSignature:
    """Tests for verify_webhook_signature()."""

    def test_no_secret_configured_returns_true(self):
        """When no webhook secret is set, verification is skipped."""
        with patch.dict(os.environ, {"MOLLIE_WEBHOOK_SECRET": ""}):
            assert verify_webhook_signature("body", "any_signature") is True

    def test_valid_signature_returns_true(self):
        import hmac
        import hashlib

        secret = "test_webhook_secret_123"
        body = '{"id": "tr_12345"}'
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            msg=body.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        with patch.dict(os.environ, {"MOLLIE_WEBHOOK_SECRET": secret}):
            assert verify_webhook_signature(body, expected_sig) is True

    def test_invalid_signature_returns_false(self):
        secret = "test_webhook_secret_123"
        body = '{"id": "tr_12345"}'

        with patch.dict(os.environ, {"MOLLIE_WEBHOOK_SECRET": secret}):
            assert verify_webhook_signature(body, "invalid_signature") is False

    def test_empty_signature_with_secret_returns_false(self):
        with patch.dict(os.environ, {"MOLLIE_WEBHOOK_SECRET": "some_secret"}):
            assert verify_webhook_signature("body", "") is False


class TestMollieError:
    """Tests for MollieError structured error response."""

    def test_to_error_response_format(self):
        error = MollieError("Something went wrong", status_code=502)
        response = error.to_error_response()

        assert response == {
            "error": "payment_provider_error",
            "details": {
                "provider": "mollie",
                "reason": "Something went wrong",
            },
        }

    def test_error_preserves_status_code(self):
        error = MollieError("Auth failed", status_code=401)
        assert error.status_code == 401
        assert str(error) == "Auth failed"

    def test_error_without_status_code(self):
        error = MollieError("Generic error")
        assert error.status_code is None


class TestMissingApiKey:
    """Tests for missing MOLLIE_API_KEY."""

    @patch.dict(os.environ, {"MOLLIE_API_KEY": ""})
    def test_create_payment_raises_when_no_key(self):
        with pytest.raises(MollieError) as exc_info:
            create_payment(
                amount="10.00",
                description="No key",
                redirect_url="https://example.com",
            )
        assert "MOLLIE_API_KEY" in str(exc_info.value)

    @patch.dict(os.environ, {"MOLLIE_API_KEY": ""})
    def test_get_payment_raises_when_no_key(self):
        with pytest.raises(MollieError) as exc_info:
            get_payment("tr_12345")
        assert "MOLLIE_API_KEY" in str(exc_info.value)
