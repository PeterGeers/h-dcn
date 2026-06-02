"""
Unit tests for the unlock_presmeet_order Lambda handler.
Tests admin authentication, order status verification, and unlock transition.
"""

import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

# Ensure the auth layer path takes priority over backend/shared/
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "layers", "auth-layer", "python")
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Remove cached 'shared' module so Python re-resolves from the layers path
for key in list(sys.modules.keys()):
    if key == "shared" or key.startswith("shared."):
        del sys.modules[key]

# Ensure handler path is available
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

from handler.unlock_presmeet_order.app import lambda_handler


class TestUnlockPresmeetOrder:
    """Unit tests for the unlock_presmeet_order lambda_handler."""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Set up mocked DynamoDB tables for each test."""
        with mock_aws():
            os.environ["AWS_ACCESS_KEY_ID"] = "testing"
            os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
            os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"
            os.environ["ORDERS_TABLE_NAME"] = "Orders"

            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

            # Create Orders table
            self.orders_table = dynamodb.create_table(
                TableName="Orders",
                KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "order_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            dynamodb.meta.client.get_waiter("table_exists").wait(
                TableName="Orders"
            )

            # Patch the table in the handler module
            with patch(
                "handler.unlock_presmeet_order.app.orders_table", self.orders_table
            ):
                yield

    def _create_order(self, order_id="test-order-123", status="locked", source="presmeet"):
        """Helper to create an order in DynamoDB."""
        order = {
            "order_id": order_id,
            "source": source,
            "club_id": "amsterdam",
            "status": status,
            "payment_status": "unpaid",
            "items": [
                {
                    "item_id": "item-1",
                    "product_type": "meeting_ticket",
                    "attributes": {"name": "Jan de Vries", "role": "President"},
                },
            ],
            "total_amount": Decimal("50.00"),
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "submitted_at": "2025-01-02T00:00:00+00:00",
            "created_by": "user@club.nl",
        }
        self.orders_table.put_item(Item=order)
        return order

    def _make_event(self, order_id="test-order-123", method="POST"):
        return {
            "httpMethod": method,
            "body": None,
            "headers": {"Authorization": "Bearer mock-token"},
            "queryStringParameters": None,
            "pathParameters": {"order_id": order_id},
        }

    def _mock_admin_auth(self, user_email="admin@h-dcn.nl"):
        """Mock auth for an admin user with webmaster role."""
        user_roles = ["hdcnLeden", "webmaster"]
        return (
            patch(
                "handler.unlock_presmeet_order.app.extract_user_credentials",
                return_value=(user_email, user_roles, None),
            ),
            patch(
                "handler.unlock_presmeet_order.app.validate_permissions_with_regions",
                return_value=(True, None, {}),
            ),
            patch("handler.unlock_presmeet_order.app.log_successful_access"),
        )

    def _mock_non_admin_auth(self, user_email="user@club.nl"):
        """Mock auth for a regular club user (no webmaster role)."""
        user_roles = ["hdcnLeden", "club_amsterdam"]
        return (
            patch(
                "handler.unlock_presmeet_order.app.extract_user_credentials",
                return_value=(user_email, user_roles, None),
            ),
            patch(
                "handler.unlock_presmeet_order.app.validate_permissions_with_regions",
                return_value=(True, None, {}),
            ),
            patch("handler.unlock_presmeet_order.app.log_successful_access"),
        )

    def test_successful_unlock(self):
        """Admin can unlock a locked order, transitioning it to submitted."""
        self._create_order(status="locked")

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 200
        result = json.loads(response["body"])
        assert result["status"] == "submitted"
        assert result["order_id"] == "test-order-123"

    def test_order_persisted_with_submitted_status(self):
        """After successful unlock, the order in DynamoDB has status 'submitted'."""
        self._create_order(status="locked")

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            lambda_handler(self._make_event(), None)

        # Verify in DynamoDB
        db_order = self.orders_table.get_item(Key={"order_id": "test-order-123"})["Item"]
        assert db_order["status"] == "submitted"

    def test_non_admin_returns_403(self):
        """Non-admin user cannot unlock an order."""
        self._create_order(status="locked")

        auth_patches = self._mock_non_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 403
        result = json.loads(response["body"])
        assert "admin" in result["error"].lower()

    def test_order_not_found_returns_404(self):
        """Unlocking a non-existent order returns 404."""
        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(order_id="nonexistent"), None)

        assert response["statusCode"] == 404
        result = json.loads(response["body"])
        assert "not found" in result["error"].lower()

    def test_draft_order_returns_409(self):
        """Cannot unlock an order that is in draft status."""
        self._create_order(status="draft")

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 409
        result = json.loads(response["body"])
        assert "draft" in result["error"].lower()

    def test_submitted_order_returns_409(self):
        """Cannot unlock an order that is already in submitted status."""
        self._create_order(status="submitted")

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 409
        result = json.loads(response["body"])
        assert "submitted" in result["error"].lower()

    def test_non_presmeet_order_returns_404(self):
        """Attempting to unlock a non-presmeet order returns 404."""
        self._create_order(source="webshop")

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 404

    def test_options_request(self):
        """OPTIONS request gets 200 (CORS preflight)."""
        response = lambda_handler(
            {
                "httpMethod": "OPTIONS",
                "body": None,
                "headers": {},
                "queryStringParameters": None,
                "pathParameters": None,
            },
            None,
        )
        assert response["statusCode"] == 200

    def test_missing_path_parameter(self):
        """Request without order_id path parameter returns 400."""
        event = {
            "httpMethod": "POST",
            "body": None,
            "headers": {"Authorization": "Bearer mock-token"},
            "queryStringParameters": None,
            "pathParameters": None,
        }

        auth_patches = self._mock_admin_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(event, None)

        assert response["statusCode"] == 400
