"""
Unit tests for shared.event_constraints module.

Tests validate_event_constraints() covering all three counting rules:
- count_items_by_product
- count_distinct_clubs
- sum_field

Also tests edge cases: empty constraints, empty orders, Decimal handling,
and current_club_id exclusion for resubmission scenarios.
"""

import sys
import os
from decimal import Decimal

import pytest

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.event_constraints import validate_event_constraints, COUNTABLE_STATUSES


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_order(club_id, status, items):
    """Helper to build a minimal order dict."""
    return {
        "club_id": club_id,
        "status": status,
        "items": items,
    }


def _make_item(product_id, fields_data=None):
    """Helper to build an order item."""
    item = {"product_id": product_id}
    if fields_data:
        item["item_fields_data"] = fields_data
    return item


# ---------------------------------------------------------------------------
# Tests: count_items_by_product
# ---------------------------------------------------------------------------

class TestCountItemsByProduct:
    """Tests for the count_items_by_product counting rule."""

    def test_under_limit_passes(self):
        """Adding items that stay under the max should return no errors."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 10,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []

    def test_at_limit_passes(self):
        """Exactly at the max should pass (not exceed)."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []

    def test_exceeds_limit_fails(self):
        """Exceeding the max should return a structured error."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert len(errors) == 1
        err = errors[0]
        assert err["constraint_key"] == "max_meeting"
        assert err["label"] == "Maximum vergaderdeelnemers"
        assert err["current_count"] == 4
        assert err["new_count"] == 6
        assert err["max"] == 5

    def test_draft_orders_not_counted(self):
        """Only submitted/locked orders count toward constraints."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 3,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "draft", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
            _make_order("club-B", "submitted", [
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-C")
        assert errors == []

    def test_locked_orders_counted(self):
        """Locked orders count toward the constraint."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 3,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "locked", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert len(errors) == 1
        assert errors[0]["new_count"] == 4

    def test_current_club_excluded_on_resubmit(self):
        """Current club's existing order is excluded to prevent double-counting."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            # Club B's existing submitted order (should be excluded)
            _make_order("club-B", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
            # Club A's order (should count)
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        # Club B resubmits with 3 items
        new_items = [
            _make_item("prod-meeting"),
            _make_item("prod-meeting"),
            _make_item("prod-meeting"),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        # current_count = 2 (club-A), new_count = 2 + 3 = 5, max = 5 → passes
        assert errors == []

    def test_other_products_not_counted(self):
        """Items for different products don't count toward a product constraint."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 2,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-party"),
                _make_item("prod-party"),
                _make_item("prod-party"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []

    def test_decimal_max_value_handled(self):
        """DynamoDB returns Decimal for numeric values — should work fine."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": Decimal("5"),
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: count_distinct_clubs
# ---------------------------------------------------------------------------

class TestCountDistinctClubs:
    """Tests for the count_distinct_clubs counting rule."""

    def test_under_limit_passes(self):
        """Adding a new club when under the max should pass."""
        constraints = [{
            "key": "max_clubs",
            "label": "Maximum deelnemende clubs",
            "max": 50,
            "counting_rule": "count_distinct_clubs",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [_make_item("prod-meeting")]),
            _make_order("club-B", "locked", [_make_item("prod-meeting")]),
        ]
        new_items = [_make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-C")
        assert errors == []

    def test_at_limit_fails(self):
        """Adding one more club when at the max should fail."""
        constraints = [{
            "key": "max_clubs",
            "label": "Maximum clubs",
            "max": 2,
            "counting_rule": "count_distinct_clubs",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [_make_item("prod-meeting")]),
            _make_order("club-B", "submitted", [_make_item("prod-meeting")]),
        ]
        new_items = [_make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-C")
        assert len(errors) == 1
        assert errors[0]["constraint_key"] == "max_clubs"
        assert errors[0]["current_count"] == 2
        assert errors[0]["new_count"] == 3
        assert errors[0]["max"] == 2

    def test_resubmit_same_club_no_double_count(self):
        """Resubmitting from the same club should not double-count the club."""
        constraints = [{
            "key": "max_clubs",
            "label": "Maximum clubs",
            "max": 2,
            "counting_rule": "count_distinct_clubs",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [_make_item("prod-meeting")]),
            _make_order("club-B", "submitted", [_make_item("prod-meeting")]),
        ]
        new_items = [_make_item("prod-meeting")]

        # Club B resubmits — should not exceed because B is excluded then re-added
        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        # current_count = 1 (only club-A), new = 1 + 1 = 2, max = 2 → passes
        assert errors == []

    def test_draft_clubs_not_counted(self):
        """Clubs with only draft orders are not counted."""
        constraints = [{
            "key": "max_clubs",
            "label": "Maximum clubs",
            "max": 2,
            "counting_rule": "count_distinct_clubs",
        }]
        existing_orders = [
            _make_order("club-A", "draft", [_make_item("prod-meeting")]),
            _make_order("club-B", "submitted", [_make_item("prod-meeting")]),
        ]
        new_items = [_make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-C")
        # current_count = 1 (club-B only), new = 1 + 1 = 2, max = 2 → passes
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: sum_field
# ---------------------------------------------------------------------------

class TestSumField:
    """Tests for the sum_field counting rule."""

    def test_under_limit_passes(self):
        """Summing a field that stays under max should pass."""
        constraints = [{
            "key": "max_transfer_persons",
            "label": "Maximum transferpersonen",
            "max": 100,
            "counting_rule": "sum_field",
            "field_name": "persons",
            "product_id": "prod-transfer",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {"persons": 5}),
                _make_item("prod-transfer", {"persons": 3}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": 4}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []

    def test_exceeds_limit_fails(self):
        """Exceeding the sum limit should return an error."""
        constraints = [{
            "key": "max_transfer_persons",
            "label": "Maximum transferpersonen",
            "max": 10,
            "counting_rule": "sum_field",
            "field_name": "persons",
            "product_id": "prod-transfer",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {"persons": 5}),
                _make_item("prod-transfer", {"persons": 3}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": 4}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert len(errors) == 1
        err = errors[0]
        assert err["constraint_key"] == "max_transfer_persons"
        assert err["current_count"] == 8
        assert err["new_count"] == 12
        assert err["max"] == 10

    def test_decimal_field_values_handled(self):
        """DynamoDB stores numbers as Decimal — should sum correctly."""
        constraints = [{
            "key": "max_persons",
            "label": "Max persons",
            "max": 20,
            "counting_rule": "sum_field",
            "field_name": "persons",
            "product_id": "prod-transfer",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {"persons": Decimal("8")}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": Decimal("5")}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert errors == []

    def test_only_matching_product_summed(self):
        """Only items matching the constraint's product_id are summed."""
        constraints = [{
            "key": "max_transfer_persons",
            "label": "Max transfer",
            "max": 5,
            "counting_rule": "sum_field",
            "field_name": "persons",
            "product_id": "prod-transfer",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {"persons": 3}),
                _make_item("prod-other", {"persons": 99}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": 2}),
            _make_item("prod-other", {"persons": 50}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        # Only prod-transfer counted: 3 + 2 = 5 <= 5 → passes
        assert errors == []

    def test_sum_field_without_product_id_sums_all(self):
        """When no product_id on constraint, sum field across all items."""
        constraints = [{
            "key": "max_persons_total",
            "label": "Max persons total",
            "max": 10,
            "counting_rule": "sum_field",
            "field_name": "persons",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {"persons": 3}),
                _make_item("prod-other", {"persons": 4}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": 2}),
            _make_item("prod-other", {"persons": 2}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        # 3 + 4 + 2 + 2 = 11 > 10 → fails
        assert len(errors) == 1
        assert errors[0]["new_count"] == 11

    def test_missing_field_defaults_to_zero(self):
        """Items missing the summed field should contribute 0."""
        constraints = [{
            "key": "max_persons",
            "label": "Max",
            "max": 10,
            "counting_rule": "sum_field",
            "field_name": "persons",
            "product_id": "prod-transfer",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-transfer", {}),  # no persons field
                _make_item("prod-transfer", {"persons": 5}),
            ]),
        ]
        new_items = [
            _make_item("prod-transfer", {"persons": 3}),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        # 0 + 5 + 3 = 8 <= 10 → passes
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Edge cases and general behavior
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and general validation behavior."""

    def test_empty_constraints_returns_no_errors(self):
        """No constraints means nothing to validate."""
        errors = validate_event_constraints(
            [_make_item("prod-meeting")],
            [],
            [_make_order("club-A", "submitted", [_make_item("prod-meeting")])],
            "club-B",
        )
        assert errors == []

    def test_none_constraints_returns_no_errors(self):
        """None constraints should also pass (defensive)."""
        errors = validate_event_constraints(
            [_make_item("prod-meeting")],
            None,
            [],
            "club-B",
        )
        assert errors == []

    def test_empty_orders_with_new_items_under_max(self):
        """First order for an event — no existing orders."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, [], "club-A")
        assert errors == []

    def test_multiple_constraints_all_checked(self):
        """All constraints are evaluated — multiple errors can be returned."""
        constraints = [
            {
                "key": "max_meeting",
                "label": "Max meeting",
                "max": 2,
                "counting_rule": "count_items_by_product",
                "product_id": "prod-meeting",
            },
            {
                "key": "max_party",
                "label": "Max party",
                "max": 3,
                "counting_rule": "count_items_by_product",
                "product_id": "prod-party",
            },
        ]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-party"),
                _make_item("prod-party"),
                _make_item("prod-party"),
            ]),
        ]
        new_items = [
            _make_item("prod-meeting"),
            _make_item("prod-party"),
        ]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert len(errors) == 2
        keys = {e["constraint_key"] for e in errors}
        assert keys == {"max_meeting", "max_party"}

    def test_constraint_without_max_is_skipped(self):
        """Constraints with no max value are ignored."""
        constraints = [{
            "key": "no_limit",
            "label": "No limit",
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        new_items = [_make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, [], "club-A")
        assert errors == []

    def test_unknown_counting_rule_treated_as_zero(self):
        """Unknown counting rules should not crash — count as 0."""
        constraints = [{
            "key": "unknown_rule",
            "label": "Unknown",
            "max": 1,
            "counting_rule": "some_future_rule",
            "product_id": "prod-x",
        }]
        new_items = [_make_item("prod-x")]

        errors = validate_event_constraints(new_items, constraints, [], "club-A")
        assert errors == []

    def test_no_current_club_id_counts_all_orders(self):
        """When current_club_id is None, all countable orders are included."""
        constraints = [{
            "key": "max_meeting",
            "label": "Max meeting",
            "max": 3,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
            _make_order("club-B", "submitted", [
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting")]

        # No club exclusion — all 3 existing + 1 new = 4 > 3
        errors = validate_event_constraints(new_items, constraints, existing_orders, None)
        assert len(errors) == 1
        assert errors[0]["current_count"] == 3
        assert errors[0]["new_count"] == 4

    def test_error_message_contains_useful_info(self):
        """Error message should include counts and label."""
        constraints = [{
            "key": "max_meeting",
            "label": "Maximum vergaderdeelnemers",
            "max": 5,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-meeting",
        }]
        existing_orders = [
            _make_order("club-A", "submitted", [
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
                _make_item("prod-meeting"),
            ]),
        ]
        new_items = [_make_item("prod-meeting"), _make_item("prod-meeting")]

        errors = validate_event_constraints(new_items, constraints, existing_orders, "club-B")
        assert len(errors) == 1
        msg = errors[0]["message"]
        assert "Maximum vergaderdeelnemers" in msg
        assert "5" in msg

    def test_countable_statuses_constant(self):
        """Verify the COUNTABLE_STATUSES constant has expected values."""
        assert COUNTABLE_STATUSES == {"submitted", "locked"}
