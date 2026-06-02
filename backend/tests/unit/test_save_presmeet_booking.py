"""
Unit tests for the save_presmeet_booking Lambda handler.
Tests form-to-cart mapping, max_per_club validation, order lifecycle transitions,
and upsert behavior.
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
# We need to clean out any cached 'shared' module and force resolution from the layer path.
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

from handler.save_presmeet_booking.app import (
    map_delegates_to_items,
    map_guests_to_items,
    map_transfers_to_items,
    validate_max_per_club,
    lambda_handler,
)


class TestMapDelegatesToItems:
    """Test delegate form data -> cart items mapping."""

    def test_delegate_produces_meeting_ticket(self):
        delegates = [{"name": "Jan de Vries", "role": "President"}]
        items = map_delegates_to_items(delegates)

        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]
        assert len(meeting_tickets) == 1
        assert meeting_tickets[0]["attributes"]["name"] == "Jan de Vries"
        assert meeting_tickets[0]["attributes"]["role"] == "President"
        assert "item_id" in meeting_tickets[0]

    def test_delegate_with_party_produces_party_ticket(self):
        delegates = [{"name": "Jan", "role": "President", "party": True}]
        items = map_delegates_to_items(delegates)

        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        assert len(party_tickets) == 1
        assert party_tickets[0]["attributes"]["name"] == "Jan"
        assert party_tickets[0]["attributes"]["person_type"] == "delegate"

    def test_delegate_without_party_no_party_ticket(self):
        delegates = [{"name": "Jan", "role": "President", "party": False}]
        items = map_delegates_to_items(delegates)

        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        assert len(party_tickets) == 0

    def test_delegate_with_tshirt(self):
        delegates = [
            {
                "name": "Jan",
                "role": "President",
                "tshirt": {"gender": "male", "size": "XL"},
            }
        ]
        items = map_delegates_to_items(delegates)

        tshirts = [i for i in items if i["product_type"] == "tshirt"]
        assert len(tshirts) == 1
        assert tshirts[0]["attributes"]["name"] == "Jan"
        assert tshirts[0]["attributes"]["gender"] == "male"
        assert tshirts[0]["attributes"]["size"] == "XL"

    def test_delegate_full_produces_three_items(self):
        """Delegate with party and tshirt produces meeting_ticket + party_ticket + tshirt."""
        delegates = [
            {
                "name": "Jan",
                "role": "President",
                "party": True,
                "tshirt": {"gender": "male", "size": "L"},
            }
        ]
        items = map_delegates_to_items(delegates)
        assert len(items) == 3

    def test_multiple_delegates(self):
        delegates = [
            {"name": "A", "role": "President"},
            {"name": "B", "role": "Secretary"},
            {"name": "C", "role": "Treasurer"},
        ]
        items = map_delegates_to_items(delegates)
        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]
        assert len(meeting_tickets) == 3


class TestMapGuestsToItems:
    """Test guest form data -> cart items mapping."""

    def test_guest_produces_party_ticket(self):
        guests = [{"name": "Lisa Bakker"}]
        items = map_guests_to_items(guests)

        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        assert len(party_tickets) == 1
        assert party_tickets[0]["attributes"]["name"] == "Lisa Bakker"
        assert party_tickets[0]["attributes"]["person_type"] == "guest"

    def test_guest_with_tshirt(self):
        guests = [{"name": "Lisa", "tshirt": {"gender": "female", "size": "M"}}]
        items = map_guests_to_items(guests)

        tshirts = [i for i in items if i["product_type"] == "tshirt"]
        assert len(tshirts) == 1
        assert tshirts[0]["attributes"]["name"] == "Lisa"
        assert tshirts[0]["attributes"]["gender"] == "female"
        assert tshirts[0]["attributes"]["size"] == "M"


class TestMapTransfersToItems:
    """Test transfer form data -> cart items mapping."""

    def test_transfer_produces_airport_transfer(self):
        transfers = [
            {
                "direction": "pickup",
                "airport": "AMS",
                "flight": "KL1234",
                "date": "2025-09-15",
                "time": "14:30",
                "persons": 3,
            }
        ]
        items = map_transfers_to_items(transfers)

        assert len(items) == 1
        assert items[0]["product_type"] == "airport_transfer"
        assert items[0]["attributes"]["direction"] == "pickup"
        assert items[0]["attributes"]["airport"] == "AMS"
        assert items[0]["attributes"]["flight"] == "KL1234"
        assert items[0]["attributes"]["date"] == "2025-09-15"
        assert items[0]["attributes"]["time"] == "14:30"
        assert items[0]["attributes"]["persons"] == 3


class TestValidateMaxPerClub:
    """Test max_per_club enforcement."""

    def test_within_limits(self):
        items = [{"product_type": "meeting_ticket"} for _ in range(3)]
        is_valid, error = validate_max_per_club(items)
        assert is_valid is True
        assert error is None

    def test_exceeds_meeting_ticket_limit(self):
        items = [{"product_type": "meeting_ticket"} for _ in range(4)]
        is_valid, error = validate_max_per_club(items)
        assert is_valid is False
        assert "meeting_ticket" in error

    def test_exceeds_party_ticket_limit(self):
        items = [{"product_type": "party_ticket"} for _ in range(14)]
        is_valid, error = validate_max_per_club(items)
        assert is_valid is False
        assert "party_ticket" in error

    def test_exceeds_tshirt_limit(self):
        items = [{"product_type": "tshirt"} for _ in range(14)]
        is_valid, error = validate_max_per_club(items)
        assert is_valid is False
        assert "tshirt" in error

    def test_exceeds_airport_transfer_limit(self):
        items = [{"product_type": "airport_transfer"} for _ in range(21)]
        is_valid, error = validate_max_per_club(items)
        assert is_valid is False
        assert "airport_transfer" in error

    def test_empty_items_valid(self):
        is_valid, error = validate_max_per_club([])
        assert is_valid is True


class TestLambdaHandler:
    """Integration tests for the full lambda_handler using moto."""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self):
        """Set up mocked DynamoDB for each test."""
        with mock_aws():
            os.environ["AWS_ACCESS_KEY_ID"] = "testing"
            os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
            os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"
            os.environ["ORDERS_TABLE_NAME"] = "Orders"

            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            self.table = dynamodb.create_table(
                TableName="Orders",
                KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "order_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self.table.meta.client.get_waiter("table_exists").wait(
                TableName="Orders"
            )

            # Patch the orders_table in the handler module to use our moto table
            with patch(
                "handler.save_presmeet_booking.app.orders_table", self.table
            ):
                yield

    def _make_event(self, body, method="PUT"):
        return {
            "httpMethod": method,
            "body": json.dumps(body) if body else None,
            "headers": {"Authorization": "Bearer mock-token"},
            "queryStringParameters": None,
            "pathParameters": None,
        }

    def _mock_auth(self, user_email="user@club.nl", user_roles=None, club_id="amsterdam"):
        if user_roles is None:
            user_roles = ["hdcnLeden", "Regio_Pressmeet"]
        return (
            patch(
                "handler.save_presmeet_booking.app.extract_user_credentials",
                return_value=(user_email, user_roles, None),
            ),
            patch(
                "handler.save_presmeet_booking.app.validate_permissions_with_regions",
                return_value=(True, None, {}),
            ),
            patch("handler.save_presmeet_booking.app.log_successful_access"),
            patch(
                "handler.save_presmeet_booking.app.has_presmeet_access",
                return_value=("Regio_Pressmeet" in user_roles or "Regio_All" in user_roles),
            ),
            patch(
                "handler.save_presmeet_booking.app.get_club_id",
                return_value=club_id,
            ),
        )

    def test_new_booking_creates_draft_order(self):
        body = {
            "delegates": [{"name": "Jan", "role": "President"}],
            "guests": [],
            "transfers": [],
        }

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        assert response["statusCode"] == 200
        result = json.loads(response["body"])
        assert result["status"] == "draft"
        assert result["payment_status"] == "unpaid"
        assert result["source"] == "presmeet"
        assert result["tenant"] == "presmeet"
        assert result["club_id"] == "amsterdam"
        assert result["created_by"] == "user@club.nl"
        assert len(result["items"]) == 1

    def test_upsert_reuses_existing_order_id(self):
        """Should reuse existing order_id when updating."""
        self.table.put_item(
            Item={
                "order_id": "existing-id-123",
                "source": "presmeet",
                "club_id": "amsterdam",
                "status": "draft",
                "payment_status": "unpaid",
                "items": [],
                "total_amount": Decimal("0"),
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "submitted_at": None,
                "created_by": "user@club.nl",
            }
        )

        body = {
            "delegates": [{"name": "Jan", "role": "President"}],
            "guests": [],
            "transfers": [],
        }

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        result = json.loads(response["body"])
        assert result["order_id"] == "existing-id-123"

    def test_submitted_order_transitions_to_draft(self):
        """Modifying a submitted order transitions it back to draft."""
        self.table.put_item(
            Item={
                "order_id": "submitted-order-id",
                "source": "presmeet",
                "club_id": "amsterdam",
                "status": "submitted",
                "payment_status": "unpaid",
                "items": [],
                "total_amount": Decimal("0"),
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "submitted_at": "2025-01-02T00:00:00+00:00",
                "created_by": "user@club.nl",
            }
        )

        body = {
            "delegates": [{"name": "Jan", "role": "President"}],
            "guests": [],
            "transfers": [],
        }

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        result = json.loads(response["body"])
        assert result["status"] == "draft"
        assert result["order_id"] == "submitted-order-id"

    def test_locked_order_returns_409(self):
        """Attempting to modify a locked order returns 409."""
        self.table.put_item(
            Item={
                "order_id": "locked-order-id",
                "source": "presmeet",
                "club_id": "amsterdam",
                "status": "locked",
                "payment_status": "unpaid",
                "items": [],
                "total_amount": Decimal("0"),
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "submitted_at": "2025-01-02T00:00:00+00:00",
                "created_by": "user@club.nl",
            }
        )

        body = {
            "delegates": [{"name": "Jan", "role": "President"}],
            "guests": [],
            "transfers": [],
        }

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        assert response["statusCode"] == 409
        result = json.loads(response["body"])
        assert "locked" in result["error"].lower()

    def test_total_calculation(self):
        """Total should reflect pricing rules."""
        body = {
            "delegates": [
                {"name": "Jan", "role": "President", "party": True,
                 "tshirt": {"gender": "male", "size": "L"}}
            ],
            "guests": [{"name": "Lisa"}],
            "transfers": [
                {
                    "direction": "pickup",
                    "airport": "AMS",
                    "flight": "KL1",
                    "date": "2025-09-15",
                    "time": "10:00",
                    "persons": 2,
                }
            ],
        }
        # meeting_ticket(50) + party_ticket(99.50) + tshirt(25)
        # + guest party_ticket(99.50) + airport_transfer(2*5=10) = 284.00

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        result = json.loads(response["body"])
        assert result["total_amount"] == 284.0

    def test_no_club_assignment_returns_403(self):
        """User without club_id on Member record gets 403."""
        body = {"delegates": [], "guests": [], "transfers": []}

        auth_patches = self._mock_auth(user_roles=["hdcnLeden", "Regio_Pressmeet"], club_id=None)
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        assert response["statusCode"] == 403

    def test_no_presmeet_access_returns_403(self):
        """User without Regio_Pressmeet gets 403 from access gate."""
        body = {"delegates": [], "guests": [], "transfers": []}

        auth_patches = self._mock_auth(user_roles=["hdcnLeden"])
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        assert response["statusCode"] == 403

    def test_missing_body_returns_400(self):
        """Missing body returns 400."""
        event = self._make_event(None)
        event["body"] = None

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_invalid_json_returns_400(self):
        """Invalid JSON body returns 400."""
        event = self._make_event(None)
        event["body"] = "not json {"

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_options_request(self):
        """OPTIONS request gets 200 (CORS preflight)."""
        response = lambda_handler(self._make_event(None, method="OPTIONS"), None)
        assert response["statusCode"] == 200

    def test_max_per_club_exceeded_returns_400(self):
        """Exceeding max_per_club returns 400."""
        body = {
            "delegates": [
                {"name": f"Delegate {i}", "role": "Member"} for i in range(4)
            ],
            "guests": [],
            "transfers": [],
        }

        auth_patches = self._mock_auth()
        with auth_patches[0], auth_patches[1], auth_patches[2], auth_patches[3], auth_patches[4]:
            response = lambda_handler(self._make_event(body), None)

        assert response["statusCode"] == 400
        result = json.loads(response["body"])
        assert "meeting_ticket" in result["error"]
