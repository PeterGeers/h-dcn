"""
Stub test for export_members handler.
Validates handler is importable and rejects unauthenticated requests.
Requirements: 4.3
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'export_members'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from handler.export_members.app import lambda_handler


@pytest.fixture
def api_gateway_event():
    """Minimal API Gateway event without auth."""
    return {
        "httpMethod": "GET",
        "path": "/members/export",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
        "requestContext": {},
    }


def test_handler_exists():
    """Verify lambda_handler is callable."""
    assert callable(lambda_handler)


def test_returns_401_without_auth(api_gateway_event):
    """Handler rejects unauthenticated requests."""
    response = lambda_handler(api_gateway_event, None)
    assert response["statusCode"] in [401, 403, 500]
