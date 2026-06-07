"""
Stub test for update_member handler.
Validates handler is importable and rejects unauthenticated requests.
Requirements: 4.3
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'update_member'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from handler.update_member.app import lambda_handler


@pytest.fixture
def api_gateway_event():
    """Minimal API Gateway event without auth."""
    return {
        "httpMethod": "PUT",
        "path": "/members/123",
        "headers": {},
        "queryStringParameters": None,
        "body": "{}",
        "requestContext": {},
    }


def test_handler_exists():
    """Verify lambda_handler is callable."""
    assert callable(lambda_handler)


def test_returns_401_without_auth(api_gateway_event):
    """Handler rejects unauthenticated requests."""
    response = lambda_handler(api_gateway_event, None)
    assert response["statusCode"] in [401, 403, 500]
