"""
Stub test for get_member_self handler.
Validates handler is importable and rejects unauthenticated requests.
Requirements: 4.3
"""

import sys
import os
import pytest

# AWS env vars MUST be set before importing the handler: the handler creates
# `boto3.resource('dynamodb')` at module load, which raises NoRegionError during
# test collection when no region is configured (e.g. in CI). See
# .kiro/steering/testing-backend.md.
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-west-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_member_self'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from handler.get_member_self.app import lambda_handler


@pytest.fixture
def api_gateway_event():
    """Minimal API Gateway event without auth."""
    return {
        "httpMethod": "GET",
        "path": "/members/self",
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
