"""
Unit tests for shared.presmeet_validation module (PresMeet v3).

Tests the three main validation functions:
- validate_item_fields: field presence, types, options, min/max
- validate_purchase_rules: min_per_club, max_per_club enforcement
- validate_submission: orchestration of all validations

Requirements covered: 3.1, 3.2, 3.6, 5.2, 6.1, 6.2, 6.3
"""

import sys
import os
from decimal import Decimal

import pytest

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.presmeet_validation import (
    validate_item_fields,
    validate_purchase_rules,
    validate_submission,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(product_id, name, order_item_fields=None, purchase_rules=None):
    """Build a product dict."""
    product = {
        "product_id": product_id,
        "name": name,
    }
    if order_item_fields is not None:
        product["order_item_fields"] = order_item_fields
    if purchase_rules is not None:
        product["purchase_rules"] = purchase_rules
    return product


def _make_item(product_id, fields_data=None):
    """Build an order item dict."""
    item = {"product_id": product_id}
    if fields_data is not None:
        item["item_fields_data"] = fields_data
    return item


def _make_order(club_id, items, status="draft"):
    """Build an order dict."""
    return {
        "club_id": club_id,
        "items": items,
        "status": status,
    }


def _make_event(constraints=None):
    """Build a minimal event dict."""
    return {
        "event_id": "evt-1",
        "constraints": constraints or [],
    }


# ---------------------------------------------------------------------------
# Products used across tests
# ---------------------------------------------------------------------------

MEETING_PRODUCT = _make_product(
    "prod-meeting", "Meeting Ticket",
    order_item_fields=[
        {"id": "name", "label": "Naam", "type": "text", "required": True},
        {"id": "role", "label": "Functie", "type": "text", "required": True},
        {"id": "attend_party", "label": "Feest bijwonen", "type": "select", "required": True, "options": ["yes", "no"]},
    ],
    purchase_rules={"min_per_club": 1, "max_per_club": 3, "order_mode": "persistent"},
)

PARTY_PRODUCT = _make_product(
    "prod-party", "Party Ticket",
    order_item_fields=[
        {"id": "name", "label": "Naam", "type": "text", "required": True},
        {"id": "person_type", "label": "Type persoon", "type": "select", "required": True, "options": ["delegate", "guest"]},
    ],
    purchase_rules={"max_per_club": 13, "order_mode": "persistent"},
)

TRANSFER_PRODUCT = _make_product(
    "prod-transfer", "Airport Transfer",
    order_item_fields=[
        {"id": "flight_number", "label": "Vluchtnummer", "type": "text", "required": True},
        {"id": "date", "label": "Datum", "type": "date", "required": True},
        {"id": "time", "label": "Tijd", "type": "text", "required": True},
        {"id": "persons", "label": "Personen", "type": "number", "required": True, "min": 1, "max": 20},
    ],
    purchase_rules={"max_per_club": 20, "order_mode": "persistent"},
)

TSHIRT_PRODUCT = _make_product(
    "prod-tshirt", "T-Shirt",
    order_item_fields=[
        {"id": "person_name", "label": "Naam persoon", "type": "text", "required": True},
    ],
    purchase_rules={"max_per_club": 13, "order_mode": "persistent"},
)

ALL_PRODUCTS = {
    "prod-meeting": MEETING_PRODUCT,
    "prod-party": PARTY_PRODUCT,
    "prod-transfer": TRANSFER_PRODUCT,
    "prod-tshirt": TSHIRT_PRODUCT,
}


# ===========================================================================
# Tests: validate_item_fields
# ===========================================================================

class TestValidateItemFields:
    """Tests for validate_item_fields (Req 3.1, 5.2)."""

    def test_valid_items_no_errors(self):
        """All fields valid and present → no errors."""
        items = [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "Secretary", "attend_party": "no"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_missing_required_text_field(self):
        """Missing a required text field → error with item_index and field."""
        items = [
            _make_item("prod-meeting", {"name": "Jan", "attend_party": "yes"}),  # role missing
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["item_index"] == 0
        assert errors[0]["field"] == "role"

    def test_empty_required_text_field(self):
        """Empty string for required text field → error."""
        items = [
            _make_item("prod-meeting", {"name": "", "role": "President", "attend_party": "yes"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["item_index"] == 0
        assert errors[0]["field"] == "name"

    def test_whitespace_only_required_text_field(self):
        """Whitespace-only string for required text field → error."""
        items = [
            _make_item("prod-meeting", {"name": "   ", "role": "President", "attend_party": "yes"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "name"

    def test_invalid_select_option(self):
        """Value not in options list → error."""
        items = [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "maybe"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["item_index"] == 0
        assert errors[0]["field"] == "attend_party"
        assert "maybe" in errors[0]["message"]

    def test_valid_select_option(self):
        """Value in options list → no error."""
        items = [
            _make_item("prod-party", {"name": "Jan", "person_type": "delegate"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_number_field_valid(self):
        """Number within min/max → no error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": 5}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_number_field_below_min(self):
        """Number below minimum → error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": 0}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "persons"
        assert "minimaal" in errors[0]["message"].lower() or "min" in errors[0]["message"].lower()

    def test_number_field_above_max(self):
        """Number above maximum → error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": 25}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "persons"
        assert "maximaal" in errors[0]["message"].lower() or "max" in errors[0]["message"].lower()

    def test_number_field_at_boundaries(self):
        """Number exactly at min and max → no error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": 1}),
            _make_item("prod-transfer", {"flight_number": "BA456", "date": "2027-06-21", "time": "09:00", "persons": 20}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_number_field_non_numeric_value(self):
        """Non-numeric value for number field → error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": "abc"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "persons"

    def test_number_field_decimal_value(self):
        """Decimal value (from DynamoDB) for number field → valid."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": Decimal("5")}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_date_field_valid(self):
        """Non-empty string date field → no error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "date": "2027-06-20", "time": "14:00", "persons": 3}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert errors == []

    def test_date_field_missing_required(self):
        """Missing required date field → error."""
        items = [
            _make_item("prod-transfer", {"flight_number": "KL123", "time": "14:00", "persons": 3}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert any(e["field"] == "date" for e in errors)

    def test_unknown_product_id(self):
        """Item with unknown product_id → error."""
        items = [
            _make_item("prod-unknown", {"name": "Jan"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "product_id"
        assert "Onbekend" in errors[0]["message"] or "onbekend" in errors[0]["message"]

    def test_missing_product_id(self):
        """Item without product_id → error."""
        items = [{"item_fields_data": {"name": "Jan"}}]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "product_id"

    def test_multiple_errors_returned(self):
        """All errors returned, not just first (Req 3.6)."""
        items = [
            _make_item("prod-meeting", {}),  # all 3 required fields missing
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 3
        field_names = {e["field"] for e in errors}
        assert field_names == {"name", "role", "attend_party"}

    def test_multiple_items_errors_indexed_correctly(self):
        """Errors from multiple items have correct item_index (Req 3.6)."""
        items = [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "", "role": "", "attend_party": "yes"}),
        ]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert all(e["item_index"] == 1 for e in errors)

    def test_no_order_item_fields_defined(self):
        """Product without order_item_fields → skip validation for that item."""
        products = {"prod-simple": _make_product("prod-simple", "Simple", order_item_fields=[])}
        items = [_make_item("prod-simple", {"anything": "value"})]
        errors = validate_item_fields(items, products)
        assert errors == []

    def test_optional_field_empty_is_ok(self):
        """Non-required field left empty → no error."""
        product = _make_product("prod-opt", "Optional Test", order_item_fields=[
            {"id": "notes", "label": "Opmerkingen", "type": "text", "required": False},
        ])
        items = [_make_item("prod-opt", {"notes": ""})]
        errors = validate_item_fields(items, {"prod-opt": product})
        assert errors == []

    def test_optional_field_absent_is_ok(self):
        """Non-required field completely absent → no error."""
        product = _make_product("prod-opt", "Optional Test", order_item_fields=[
            {"id": "notes", "label": "Opmerkingen", "type": "text", "required": False},
        ])
        items = [_make_item("prod-opt", {})]
        errors = validate_item_fields(items, {"prod-opt": product})
        assert errors == []

    def test_none_item_fields_data(self):
        """item_fields_data is None → required field errors raised."""
        items = [_make_item("prod-tshirt", None)]
        errors = validate_item_fields(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "person_name"


# ===========================================================================
# Tests: validate_purchase_rules
# ===========================================================================

class TestValidatePurchaseRules:
    """Tests for validate_purchase_rules (Req 3.2, 6.1, 6.2)."""

    def test_within_limits_no_errors(self):
        """Item counts within min/max → no errors."""
        items = [
            _make_item("prod-meeting"),
            _make_item("prod-meeting"),
        ]
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        assert errors == []

    def test_exactly_at_max_no_errors(self):
        """Exactly at max_per_club → no error (inclusive limit)."""
        items = [_make_item("prod-meeting") for _ in range(3)]  # max is 3
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        assert errors == []

    def test_exceeds_max_per_club(self):
        """Exceeding max_per_club → error (Req 6.1)."""
        items = [_make_item("prod-meeting") for _ in range(4)]  # max is 3
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        assert len(errors) == 1
        assert errors[0]["field"] == "prod-meeting"
        assert "Maximum" in errors[0]["message"] or "maximum" in errors[0]["message"]

    def test_below_min_per_club(self):
        """Below min_per_club → error (Req 6.2)."""
        # prod-meeting has min_per_club=1; submitting 0 meeting items
        items = [_make_item("prod-party")]  # no meeting items
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        assert any(e["field"] == "prod-meeting" for e in errors)
        meeting_err = next(e for e in errors if e["field"] == "prod-meeting")
        assert "Minimaal" in meeting_err["message"] or "minimaal" in meeting_err["message"]

    def test_exactly_at_min_no_errors(self):
        """Exactly at min_per_club → no error."""
        items = [_make_item("prod-meeting")]  # min is 1
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        # Filter to only prod-meeting errors
        meeting_errors = [e for e in errors if e["field"] == "prod-meeting"]
        assert meeting_errors == []

    def test_no_purchase_rules_no_errors(self):
        """Product without purchase_rules → no enforcement."""
        product = _make_product("prod-free", "Free Product", purchase_rules=None)
        items = [_make_item("prod-free") for _ in range(100)]
        errors = validate_purchase_rules(items, {"prod-free": product})
        assert errors == []

    def test_multiple_products_exceeded(self):
        """Multiple products exceeding limits → all errors returned (Req 3.6)."""
        items = (
            [_make_item("prod-meeting") for _ in range(5)] +   # max 3
            [_make_item("prod-party") for _ in range(15)]      # max 13
        )
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        fields_with_errors = {e["field"] for e in errors}
        assert "prod-meeting" in fields_with_errors
        assert "prod-party" in fields_with_errors

    def test_item_index_is_none_for_purchase_rules(self):
        """Purchase rule errors have item_index=None (product-level, not item-level)."""
        items = [_make_item("prod-meeting") for _ in range(5)]
        errors = validate_purchase_rules(items, ALL_PRODUCTS)
        assert all(e["item_index"] is None for e in errors)

    def test_decimal_max_per_club(self):
        """Handles Decimal values from DynamoDB for max_per_club."""
        product = _make_product("prod-dec", "Decimal Test",
                                purchase_rules={"max_per_club": Decimal("2")})
        items = [_make_item("prod-dec") for _ in range(3)]
        errors = validate_purchase_rules(items, {"prod-dec": product})
        assert len(errors) == 1

    def test_zero_items_for_product_without_min(self):
        """Zero items for a product with no min_per_club → no error."""
        items = []  # no party tickets at all
        products = {"prod-party": PARTY_PRODUCT}  # no min_per_club
        errors = validate_purchase_rules(items, products)
        assert errors == []


# ===========================================================================
# Tests: validate_submission (orchestration)
# ===========================================================================

class TestValidateSubmission:
    """Tests for validate_submission (Req 3.1-3.6, 6.1-6.3)."""

    def test_valid_submission_no_errors(self):
        """Fully valid submission → empty error list."""
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "Secretary", "attend_party": "no"}),
        ])
        event = _make_event()
        errors = validate_submission(order, event, ALL_PRODUCTS, [])
        assert errors == []

    def test_combines_field_and_rule_errors(self):
        """Returns both field errors and purchase rule errors together."""
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "", "role": "", "attend_party": "yes"}),  # 2 field errors
            _make_item("prod-meeting", {"name": "A", "role": "B", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "C", "role": "D", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "E", "role": "F", "attend_party": "yes"}),  # 4th: max=3 exceeded
        ])
        event = _make_event()
        errors = validate_submission(order, event, ALL_PRODUCTS, [])
        # Should have field errors (name, role empty in item 0) + purchase rule error
        field_errors = [e for e in errors if e["item_index"] is not None]
        rule_errors = [e for e in errors if e["item_index"] is None and e["field"] == "prod-meeting"]
        assert len(field_errors) >= 2
        assert len(rule_errors) >= 1

    def test_includes_event_constraint_errors(self):
        """Returns event constraint errors integrated with others."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        # Existing orders already at 4
        existing_orders = [{
            "club_id": "club-B",
            "status": "submitted",
            "items": [_make_item("prod-meeting") for _ in range(4)],
        }]
        # New order trying to add 2 more → 6 > max 5
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "Secretary", "attend_party": "no"}),
        ])
        event = _make_event(constraints)
        errors = validate_submission(order, event, ALL_PRODUCTS, existing_orders)
        constraint_errors = [e for e in errors if e["field"] == "max_meeting"]
        assert len(constraint_errors) == 1

    def test_excludes_current_club_from_constraint_count(self):
        """Current club's existing order excluded from constraint count (resubmit)."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            {
                "club_id": "club-A",  # same club, should be excluded
                "status": "submitted",
                "items": [_make_item("prod-meeting") for _ in range(3)],
            },
            {
                "club_id": "club-B",
                "status": "submitted",
                "items": [_make_item("prod-meeting") for _ in range(2)],
            },
        ]
        # club-A resubmitting with 3 items: 2 (from club-B) + 3 (new) = 5 ≤ 5
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "Jan", "role": "President", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "Secretary", "attend_party": "no"}),
            _make_item("prod-meeting", {"name": "Kees", "role": "Treasurer", "attend_party": "yes"}),
        ])
        event = _make_event(constraints)
        errors = validate_submission(order, event, ALL_PRODUCTS, existing_orders)
        constraint_errors = [e for e in errors if e["field"] == "max_meeting"]
        assert constraint_errors == []

    def test_no_constraints_still_validates_fields_and_rules(self):
        """Event without constraints → still validates fields and rules."""
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "", "role": "President", "attend_party": "yes"}),
        ])
        event = _make_event()
        errors = validate_submission(order, event, ALL_PRODUCTS, [])
        assert len(errors) >= 1
        assert errors[0]["field"] == "name"

    def test_empty_items_only_min_per_club_error(self):
        """Empty items array with min_per_club defined → min error."""
        order = _make_order("club-A", [])
        event = _make_event()
        errors = validate_submission(order, event, ALL_PRODUCTS, [])
        # prod-meeting has min_per_club=1 so should fail
        min_errors = [e for e in errors if "Minimaal" in e.get("message", "") or "minimaal" in e.get("message", "")]
        assert len(min_errors) >= 1

    def test_all_error_types_combined(self):
        """Demonstrate all three error types returned together."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max Meeting",
            "max": 2,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [{
            "club_id": "club-B",
            "status": "locked",
            "items": [_make_item("prod-meeting"), _make_item("prod-meeting")],
        }]
        # club-A: 4 meeting items (max_per_club=3 exceeded), missing fields, constraint exceeded
        order = _make_order("club-A", [
            _make_item("prod-meeting", {}),  # field errors
            _make_item("prod-meeting", {"name": "Jan", "role": "P", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "S", "attend_party": "no"}),
            _make_item("prod-meeting", {"name": "Kees", "role": "T", "attend_party": "yes"}),
        ])
        event = _make_event(constraints)
        errors = validate_submission(order, event, ALL_PRODUCTS, existing_orders)

        # Should have field errors (item 0), purchase rule error (4 > max 3), constraint error (4 > max 2)
        field_errors = [e for e in errors if e["item_index"] is not None]
        rule_errors = [e for e in errors if e["item_index"] is None and "Maximum" in e.get("message", "")]
        constraint_errors = [e for e in errors if e["field"] == "max_meeting"]

        assert len(field_errors) >= 1
        assert len(rule_errors) >= 1
        assert len(constraint_errors) >= 1

    def test_draft_orders_not_counted_for_constraints(self):
        """Only submitted/locked orders count toward constraints."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max Meeting",
            "max": 3,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            {
                "club_id": "club-B",
                "status": "draft",  # draft → not counted
                "items": [_make_item("prod-meeting") for _ in range(3)],
            },
        ]
        order = _make_order("club-A", [
            _make_item("prod-meeting", {"name": "Jan", "role": "P", "attend_party": "yes"}),
            _make_item("prod-meeting", {"name": "Piet", "role": "S", "attend_party": "no"}),
            _make_item("prod-meeting", {"name": "Kees", "role": "T", "attend_party": "yes"}),
        ])
        event = _make_event(constraints)
        errors = validate_submission(order, event, ALL_PRODUCTS, existing_orders)
        constraint_errors = [e for e in errors if e["field"] == "max_meeting"]
        assert constraint_errors == []
