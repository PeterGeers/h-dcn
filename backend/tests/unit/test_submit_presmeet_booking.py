"""
Unit tests for the submit_presmeet_booking Lambda handler.
Tests submission validation, order status transitions, and error handling.
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

from handler.submit_presmeet_booking.app import lambda_handler


class TestSubmitPresmeetBooking:
    """Integration tests for the submit_presmeet_booking lambda_handler."""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Set up mocked DynamoDB tables for each test."""
        with mock_aws():
            os.environ["AWS_ACCESS_KEY_ID"] = "testing"
            os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
            os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"
            os.environ["ORDERS_TABLE_NAME"] = "Orders"
            os.environ["PRODUCTEN_TABLE_NAME"] = "Producten"
            os.environ["EVENTS_TABLE_NAME"] = "Events"

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

            # Create Producten table
            self.producten_table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create Events table
            self.events_table = dynamodb.create_table(
                TableName="Events",
                KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Wait for tables
            for table_name in ["Orders", "Producten", "Events"]:
                dynamodb.meta.client.get_waiter("table_exists").wait(
                    TableName=table_name
                )

            # Seed product type configs
            self._seed_configs()

            # Seed event
            self._seed_event()

            # Patch the tables in the handler module
            with patch(
                "handler.submit_presmeet_booking.app.orders_table", self.orders_table
            ), patch(
                "handler.submit_presmeet_booking.app.producten_table", self.producten_table
            ), patch(
                "handler.submit_presmeet_booking.app.events_table", self.events_table
            ):
                yield

    def _seed_configs(self):
        """Seed Product_Type_Config records."""
        configs = [
            {
                "product_id": "config_presmeet_meeting_ticket",
                "product_type": "meeting_ticket",
                "source": "presmeet_config",
                "max_per_club": Decimal("3"),
                "min_per_club": Decimal("1"),
                "unit_price": Decimal("50.00"),
                "required_attributes": {
                    "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
                    "role": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
                },
            },
            {
                "product_id": "config_presmeet_party_ticket",
                "product_type": "party_ticket",
                "source": "presmeet_config",
                "max_per_club": Decimal("13"),
                "min_per_club": Decimal("0"),
                "unit_price": Decimal("99.50"),
                "required_attributes": {
                    "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
                    "person_type": {"type": "string", "required": True, "enum": ["delegate", "guest"]},
                },
            },
            {
                "product_id": "config_presmeet_tshirt",
                "product_type": "tshirt",
                "source": "presmeet_config",
                "max_per_club": Decimal("13"),
                "min_per_club": Decimal("0"),
                "unit_price": Decimal("25.00"),
                "required_attributes": {
                    "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
                    "gender": {"type": "string", "required": True, "enum": ["male", "female"]},
                    "size": {"type": "string", "required": True, "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"]},
                },
            },
            {
                "product_id": "config_presmeet_airport_transfer",
                "product_type": "airport_transfer",
                "source": "presmeet_config",
                "max_per_club": Decimal("20"),
                "min_per_club": Decimal("0"),
                "unit_price": Decimal("5.00"),
                "required_attributes": {
                    "direction": {"type": "string", "required": True, "enum": ["pickup", "dropoff"]},
                    "airport": {"type": "string", "required": True, "enum": ["AMS", "RTM", "EIN"]},
                    "flight": {"type": "string", "required": True, "min_length": 2, "max_length": 10},
                    "date": {"type": "string", "required": True},
                    "time": {"type": "string", "required": True},
                    "persons": {"type": "integer", "required": True, "minimum": 1, "maximum": 50},
                },
            },
        ]
        for config in configs:
            self.producten_table.put_item(Item=config)

    def _seed_event(self):
        """Seed PresMeet event record."""
        self.events_table.put_item(
            Item={
                "event_id": "presmeet_2025",
                "title": "Presidents' Meeting 2025",
                "start_date": "2025-09-15",
                "end_date": "2025-09-18",
                "source": "presmeet",
            }
        )

    def _create_draft_order(self, club_id="amsterdam", items=None):
        """Helper to create a draft order in DynamoDB."""
        if items is None:
            items = [
                {
                    "item_id": "item-1",
                    "product_type": "meeting_ticket",
                    "attributes": {"name": "Jan de Vries", "role": "President"},
                },
            ]
        order = {
            "order_id": "test-order-123",
            "source": "presmeet",
            "club_id": club_id,
            "status": "draft",
            "payment_status": "unpaid",
            "items": items,
            "total_amount": Decimal("50.00"),
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "submitted_at": None,
            "created_by": "user@club.nl",
        }
        self.orders_table.put_item(Item=order)
        return order

    def _make_event(self, method="POST"):
        return {
            "httpMethod": method,
            "body": None,
            "headers": {"Authorization": "Bearer mock-token"},
            "queryStringParameters": None,
            "pathParameters": None,
        }

    def _mock_auth(self, user_email="user@club.nl", user_roles=None):
        if user_roles is None:
            user_roles = ["hdcnLeden", "club_amsterdam"]
        return (
            patch(
                "handler.submit_presmeet_booking.app.extract_user_credentials",
                return_value=(user_email, user_roles, None),
            ),
            patch(
                "handler.submit_presmeet_booking.app.validate_permissions_with_regions",
                return_value=(True, None, {}),
            ),
            patch("handler.submit_presmeet_booking.app.log_successful_access"),
        )

    def test_successful_submission(self):
        """Valid draft order with valid items transitions to submitted."""
        self._create_draft_order()

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 200
        result = json.loads(response["body"])
        assert result["status"] == "submitted"
        assert result["submitted_at"] is not None
        assert result["order_id"] == "test-order-123"

    def test_no_order_returns_404(self):
        """Submitting when no order exists returns 404."""
        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 404
        result = json.loads(response["body"])
        assert "not found" in result["error"].lower()

    def test_submitted_order_returns_409(self):
        """Cannot submit an already submitted order."""
        self.orders_table.put_item(
            Item={
                "order_id": "submitted-order",
                "source": "presmeet",
                "club_id": "amsterdam",
                "status": "submitted",
                "payment_status": "unpaid",
                "items": [
                    {"item_id": "i1", "product_type": "meeting_ticket", "attributes": {"name": "Jan", "role": "Pres"}},
                ],
                "total_amount": Decimal("50.00"),
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "submitted_at": "2025-01-02T00:00:00+00:00",
                "created_by": "user@club.nl",
            }
        )

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 409
        result = json.loads(response["body"])
        assert "submitted" in result["error"].lower()

    def test_locked_order_returns_409(self):
        """Cannot submit a locked order."""
        self.orders_table.put_item(
            Item={
                "order_id": "locked-order",
                "source": "presmeet",
                "club_id": "amsterdam",
                "status": "locked",
                "payment_status": "unpaid",
                "items": [],
                "total_amount": Decimal("0"),
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "submitted_at": None,
                "created_by": "user@club.nl",
            }
        )

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 409
        result = json.loads(response["body"])
        assert "locked" in result["error"].lower()

    def test_validation_failure_returns_400(self):
        """Order with invalid attributes returns 400 with error list."""
        # Create order with missing required attributes
        items = [
            {
                "item_id": "item-bad",
                "product_type": "meeting_ticket",
                "attributes": {"name": "", "role": ""},  # empty strings below min_length
            },
        ]
        self._create_draft_order(items=items)

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 400
        result = json.loads(response["body"])
        assert result["error"] == "Validation failed"
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_min_per_club_enforcement(self):
        """Order without meeting_ticket fails min_per_club validation."""
        # Create order with only a party_ticket (no meeting_ticket)
        items = [
            {
                "item_id": "item-party",
                "product_type": "party_ticket",
                "attributes": {"name": "Jan", "person_type": "delegate"},
            },
        ]
        self._create_draft_order(items=items)

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 400
        result = json.loads(response["body"])
        assert result["error"] == "Validation failed"
        # Should contain min_per_club error for meeting_ticket
        errors = result["errors"]
        min_errors = [e for e in errors if e.get("constraint") == "min_per_club"]
        assert len(min_errors) > 0

    def test_no_club_assignment_returns_403(self):
        """User without club group gets 403."""
        auth_patches = self._mock_auth(user_roles=["hdcnLeden"])
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 403

    def test_options_request(self):
        """OPTIONS request gets 200 (CORS preflight)."""
        response = lambda_handler(self._make_event(method="OPTIONS"), None)
        assert response["statusCode"] == 200

    def test_order_persisted_with_submitted_status(self):
        """After successful submission, the order in DynamoDB has status 'submitted'."""
        self._create_draft_order()

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            lambda_handler(self._make_event(), None)

        # Verify in DynamoDB
        db_order = self.orders_table.get_item(Key={"order_id": "test-order-123"})["Item"]
        assert db_order["status"] == "submitted"
        assert db_order["submitted_at"] is not None

    def test_airport_transfer_date_outside_event_range(self):
        """Airport transfer with date outside event range fails validation."""
        items = [
            {
                "item_id": "item-mt",
                "product_type": "meeting_ticket",
                "attributes": {"name": "Jan", "role": "President"},
            },
            {
                "item_id": "item-transfer",
                "product_type": "airport_transfer",
                "attributes": {
                    "direction": "pickup",
                    "airport": "AMS",
                    "flight": "KL1234",
                    "date": "2025-09-20",  # After event end_date (2025-09-18)
                    "time": "14:00",
                    "persons": 2,
                },
            },
        ]
        self._create_draft_order(items=items)

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(self._make_event(), None)

        assert response["statusCode"] == 400
        result = json.loads(response["body"])
        assert result["error"] == "Validation failed"
        date_errors = [e for e in result["errors"] if e.get("constraint") == "date_range"]
        assert len(date_errors) > 0
