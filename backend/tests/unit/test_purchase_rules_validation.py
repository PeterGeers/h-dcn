"""
Property-based tests for the purchase rules validator module.

Uses Hypothesis to verify that purchase rule enforcement correctly accepts
or rejects purchases based on limit comparisons.

Feature: order-pipeline-improvements
"""

import sys
import os

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.purchase_rules_validator import validate_purchase_rules


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Limits between 1 and 100 (a product always has at least 1 as a sensible limit)
limit_strategy = st.integers(min_value=1, max_value=100)

# Existing count: 0 to 50 (items already purchased)
existing_count_strategy = st.integers(min_value=0, max_value=50)

# New quantity: 1 to 50 (must buy at least 1)
new_quantity_strategy = st.integers(min_value=1, max_value=50)


# ---------------------------------------------------------------------------
# Property 12: Purchase rules enforcement
# Feature: order-pipeline-improvements, Property 12: Purchase rules enforcement
# Validates: Requirements 5.1, 5.2, 5.3, 5.5
# ---------------------------------------------------------------------------


class TestProperty12MaxPerOrder:
    """Property 12 - max_per_order rule enforcement."""

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_order_rejects_when_total_exceeds_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity > max_per_order,
        the validator SHALL reject the purchase."""
        assume(existing_count + new_quantity > limit)

        purchase_rules = {"max_per_order": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is not None, (
            f"Expected rejection: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} > limit={limit}"
        )
        assert result["rule"] == "max_per_order"
        assert result["limit"] == limit
        assert result["status_code"] == 400

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_order_accepts_when_total_within_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity <= max_per_order,
        the validator SHALL accept the purchase."""
        assume(existing_count + new_quantity <= limit)

        purchase_rules = {"max_per_order": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is None, (
            f"Expected acceptance: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} <= limit={limit}, but got error: {result}"
        )


class TestProperty12MaxPerMember:
    """Property 12 - max_per_member rule enforcement."""

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_member_rejects_when_total_exceeds_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity > max_per_member,
        the validator SHALL reject the purchase."""
        assume(existing_count + new_quantity > limit)

        purchase_rules = {"max_per_member": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is not None, (
            f"Expected rejection: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} > limit={limit}"
        )
        assert result["rule"] == "max_per_member"
        assert result["limit"] == limit
        assert result["status_code"] == 400

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_member_accepts_when_total_within_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity <= max_per_member,
        the validator SHALL accept the purchase."""
        assume(existing_count + new_quantity <= limit)

        purchase_rules = {"max_per_member": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is None, (
            f"Expected acceptance: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} <= limit={limit}, but got error: {result}"
        )


class TestProperty12MaxPerClub:
    """Property 12 - max_per_club rule enforcement."""

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_club_rejects_when_total_exceeds_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity > max_per_club,
        the validator SHALL reject the purchase."""
        assume(existing_count + new_quantity > limit)

        purchase_rules = {"max_per_club": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is not None, (
            f"Expected rejection: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} > limit={limit}"
        )
        assert result["rule"] == "max_per_club"
        assert result["limit"] == limit
        assert result["status_code"] == 400

    @given(
        limit=limit_strategy,
        existing_count=existing_count_strategy,
        new_quantity=new_quantity_strategy,
    )
    @settings(max_examples=200)
    def test_max_per_club_accepts_when_total_within_limit(self, limit, existing_count, new_quantity):
        """For any (existing_count, new_quantity) where existing_count + new_quantity <= max_per_club,
        the validator SHALL accept the purchase."""
        assume(existing_count + new_quantity <= limit)

        purchase_rules = {"max_per_club": limit}
        result = validate_purchase_rules(
            purchase_rules=purchase_rules,
            existing_count=existing_count,
            new_quantity=new_quantity,
            is_member=True,
        )

        assert result is None, (
            f"Expected acceptance: existing={existing_count} + new={new_quantity} = "
            f"{existing_count + new_quantity} <= limit={limit}, but got error: {result}"
        )
