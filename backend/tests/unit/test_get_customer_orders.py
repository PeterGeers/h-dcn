"""
Unit tests for get_customer_orders handler.
Validates the GET /orders/my endpoint returns authenticated user's orders.
Requirements: 7.14, 7.15
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_customer_orders'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))


@pytest.fixture
def api_gateway_event():
    """Minimal API Gateway event without auth."""
    return {
        "httpMethod": "GET",
        "path": "/orders/my",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
        "requestContext": {},
    }


@pytest.fixture
def authenticated_event():
    """API Gateway event with valid JWT auth header."""
    import base64
    payload = json.dumps({
        "email": "member@h-dcn.nl",
        "cognito:groups": ["hdcnLeden"],
    })
    encoded_payload = base64.urlsafe_b64encode(payload.encode()).rstrip(b'=').decode()
    fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{encoded_payload}.fake_signature"
    return {
        "httpMethod": "GET",
        "path": "/orders/my",
        "headers": {
            "Authorization": f"Bearer {fake_jwt}",
        },
        "queryStringParameters": None,
        "body": None,
        "requestContext": {},
    }


def test_handler_exists():
    """Verify lambda_handler is callable."""
    from handler.get_customer_orders.app import lambda_handler
    assert callable(lambda_handler)


def test_returns_401_without_auth(api_gateway_event):
    """Handler rejects unauthenticated requests."""
    from handler.get_customer_orders.app import lambda_handler
    response = lambda_handler(api_gateway_event, None)
    assert response["statusCode"] == 401


def test_handles_options_request():
    """Handler returns 200 for OPTIONS (CORS preflight)."""
    from handler.get_customer_orders.app import lambda_handler
    event = {
        "httpMethod": "OPTIONS",
        "path": "/orders/my",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
        "requestContext": {},
    }
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200


@patch('handler.get_customer_orders.app.members_table')
@patch('handler.get_customer_orders.app.orders_table')
def test_returns_orders_for_authenticated_user(mock_orders_table, mock_members_table, authenticated_event):
    """Handler returns orders belonging to the authenticated user."""
    from handler.get_customer_orders.app import lambda_handler

    # Mock member lookup
    mock_members_table.scan.return_value = {
        'Items': [{'member_id': 'mem-123'}]
    }

    # Mock orders scan
    mock_orders_table.scan.return_value = {
        'Items': [
            {
                'order_id': 'order-1',
                'member_id': 'mem-123',
                'event_id': None,
                'status': 'paid',
                'payment_status': 'paid',
                'items': [{'product_id': 'prod-1', 'quantity': 2, 'unit_price': Decimal('25'), 'line_total': Decimal('50')}],
                'total_amount': Decimal('50'),
                'total_paid': Decimal('50'),
                'created_at': '2025-01-15T10:00:00Z',
                'updated_at': '2025-01-15T10:00:00Z',
            },
            {
                'order_id': 'order-2',
                'member_id': 'mem-123',
                'event_id': 'event-abc',
                'status': 'submitted',
                'payment_status': 'unpaid',
                'items': [{'product_id': 'prod-2', 'quantity': 1, 'unit_price': Decimal('100'), 'line_total': Decimal('100')}],
                'total_amount': Decimal('100'),
                'total_paid': Decimal('0'),
                'created_at': '2025-01-20T12:00:00Z',
                'updated_at': '2025-01-20T12:00:00Z',
            },
        ]
    }

    response = lambda_handler(authenticated_event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["total_count"] == 2
    assert len(body["orders"]) == 2

    # Newest first
    assert body["orders"][0]["order_id"] == "order-2"
    assert body["orders"][1]["order_id"] == "order-1"

    # Verify fields are present
    order = body["orders"][0]
    assert "order_id" in order
    assert "event_id" in order
    assert "status" in order
    assert "payment_status" in order
    assert "items" in order
    assert "total_amount" in order
    assert "total_paid" in order
    assert "created_at" in order
    assert "updated_at" in order


@patch('handler.get_customer_orders.app.members_table')
@patch('handler.get_customer_orders.app.orders_table')
def test_returns_empty_list_when_no_orders(mock_orders_table, mock_members_table, authenticated_event):
    """Handler returns empty list when user has no orders."""
    from handler.get_customer_orders.app import lambda_handler

    mock_members_table.scan.return_value = {
        'Items': [{'member_id': 'mem-456'}]
    }
    mock_orders_table.scan.return_value = {'Items': []}

    response = lambda_handler(authenticated_event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["total_count"] == 0
    assert body["orders"] == []


@patch('handler.get_customer_orders.app.members_table')
def test_returns_404_when_member_not_found(mock_members_table, authenticated_event):
    """Handler returns 404 if user has no member record."""
    from handler.get_customer_orders.app import lambda_handler

    mock_members_table.scan.return_value = {'Items': []}

    response = lambda_handler(authenticated_event, None)
    assert response["statusCode"] == 404
