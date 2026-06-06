"""
Mollie API client for unified payment processing.

Provides functions to create payments, fetch payment status, and verify
webhook signatures via the Mollie REST API (v2).

Used by both H-DCN webshop and PresMeet order flows.
"""

import os
import hmac
import hashlib
import json
import requests


MOLLIE_API_BASE = "https://api.mollie.com/v2/payments"
MOLLIE_API_KEY = os.environ.get("MOLLIE_API_KEY", "")

# Supported payment methods
SUPPORTED_METHODS = ("ideal", "creditcard")


class MollieError(Exception):
    """Raised when the Mollie API returns an error or is unreachable."""

    def __init__(self, reason: str, status_code: int | None = None):
        self.reason = reason
        self.status_code = status_code
        super().__init__(reason)

    def to_error_response(self) -> dict:
        """Return structured error dict matching the design spec."""
        return {
            "error": "payment_provider_error",
            "details": {
                "provider": "mollie",
                "reason": self.reason,
            },
        }


def _get_api_key() -> str:
    """Return the Mollie API key, reading from env at call time."""
    key = os.environ.get("MOLLIE_API_KEY", "")
    if not key:
        raise MollieError("MOLLIE_API_KEY environment variable is not configured")
    return key


def _auth_headers() -> dict:
    """Return standard Mollie authorization headers."""
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def create_payment(
    amount: str,
    description: str,
    redirect_url: str,
    webhook_url: str | None = None,
    method: str | None = None,
) -> dict:
    """
    Create a Mollie payment and return the checkout URL.

    Args:
        amount: Payment amount as string with 2 decimal places (e.g. "25.00").
        description: Human-readable payment description.
        redirect_url: URL to redirect the buyer after payment.
        webhook_url: URL Mollie calls with payment status updates.
        method: Payment method ("ideal" or "creditcard"). None lets Mollie show selection.

    Returns:
        dict with keys:
            - mollie_payment_id: str (e.g. "tr_xxxxx")
            - checkout_url: str (Mollie-hosted payment page URL)
            - status: str (initial Mollie status, typically "open")

    Raises:
        MollieError: When the API call fails or returns an error.
    """
    if method and method not in SUPPORTED_METHODS:
        raise MollieError(f"Unsupported payment method: {method}. Supported: {', '.join(SUPPORTED_METHODS)}")

    payload = {
        "amount": {
            "currency": "EUR",
            "value": amount,
        },
        "description": description,
        "redirectUrl": redirect_url,
    }

    if webhook_url:
        payload["webhookUrl"] = webhook_url

    if method:
        payload["method"] = method

    try:
        response = requests.post(
            MOLLIE_API_BASE,
            json=payload,
            headers=_auth_headers(),
            timeout=10,
        )
    except requests.exceptions.Timeout:
        raise MollieError("Mollie API request timed out")
    except requests.exceptions.ConnectionError:
        raise MollieError("Unable to connect to Mollie API")
    except requests.exceptions.RequestException as e:
        raise MollieError(f"Mollie API request failed: {str(e)}")

    if response.status_code not in (200, 201):
        error_detail = _parse_mollie_error(response)
        raise MollieError(error_detail, status_code=response.status_code)

    data = response.json()
    checkout_url = data.get("_links", {}).get("checkout", {}).get("href")
    mollie_payment_id = data.get("id")

    if not mollie_payment_id:
        raise MollieError("Mollie response missing payment ID")

    if not checkout_url:
        raise MollieError("Mollie response missing checkout URL")

    return {
        "mollie_payment_id": mollie_payment_id,
        "checkout_url": checkout_url,
        "status": data.get("status", "open"),
    }


def get_payment(payment_id: str) -> dict:
    """
    Fetch payment details from Mollie.

    Args:
        payment_id: Mollie payment ID (e.g. "tr_xxxxx").

    Returns:
        dict with keys:
            - id: str (Mollie payment ID)
            - status: str ("open", "pending", "paid", "failed", "expired", "cancelled")
            - amount: dict with "currency" and "value"
            - description: str
            - metadata: dict (if set during creation)

    Raises:
        MollieError: When the API call fails or returns an error.
    """
    if not payment_id:
        raise MollieError("payment_id is required")

    url = f"{MOLLIE_API_BASE}/{payment_id}"

    try:
        response = requests.get(url, headers=_auth_headers(), timeout=10)
    except requests.exceptions.Timeout:
        raise MollieError("Mollie API request timed out")
    except requests.exceptions.ConnectionError:
        raise MollieError("Unable to connect to Mollie API")
    except requests.exceptions.RequestException as e:
        raise MollieError(f"Mollie API request failed: {str(e)}")

    if response.status_code == 404:
        raise MollieError(f"Payment {payment_id} not found", status_code=404)

    if response.status_code != 200:
        error_detail = _parse_mollie_error(response)
        raise MollieError(error_detail, status_code=response.status_code)

    data = response.json()
    return {
        "id": data.get("id"),
        "status": data.get("status"),
        "amount": data.get("amount"),
        "description": data.get("description"),
        "metadata": data.get("metadata"),
    }


def verify_webhook_signature(request_body: str, signature: str) -> bool:
    """
    Verify a Mollie webhook signature using HMAC-SHA256.

    Mollie signs webhook requests when a webhook secret is configured.
    The signature is sent in the `X-Mollie-Signature` header.

    Args:
        request_body: The raw request body string.
        signature: The signature value from the X-Mollie-Signature header.

    Returns:
        True if the signature is valid, False otherwise.

    Note:
        If MOLLIE_WEBHOOK_SECRET is not configured, this returns True
        (signature verification is optional in Mollie — the recommended
        approach is to always fetch payment status from the API).
    """
    webhook_secret = os.environ.get("MOLLIE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        # No secret configured — skip verification.
        # Mollie recommends fetching payment status from API as primary
        # verification, which the webhook handler already does.
        return True

    if not signature:
        return False

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        msg=request_body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def _parse_mollie_error(response: requests.Response) -> str:
    """
    Extract a human-readable error message from a Mollie error response.

    Args:
        response: The HTTP response from Mollie.

    Returns:
        str: Error description.
    """
    try:
        data = response.json()
        title = data.get("title", "Unknown error")
        detail = data.get("detail", "")
        if detail:
            return f"{title}: {detail}"
        return title
    except (json.JSONDecodeError, ValueError):
        return f"Mollie API returned HTTP {response.status_code}"
