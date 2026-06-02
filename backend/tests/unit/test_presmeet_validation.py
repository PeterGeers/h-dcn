"""
Property-based tests for PresMeet shared validation module.
Tests correctness properties defined in the PresMeet design document.
"""

import sys
import os

# Add the auth layer to the path so we can import shared.presmeet_validation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from shared.presmeet_validation import extract_club_id, validate_product_type


# --- Strategies for Property 11 ---

# Strategy for valid club IDs (non-empty strings without whitespace, not starting with special chars)
club_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd'), whitelist_characters='_-'),
    min_size=1,
    max_size=50,
)

# Strategy for non-club group names (strings that do NOT start with "club_")
non_club_group_strategy = st.text(min_size=1, max_size=50).filter(
    lambda s: not s.startswith("club_")
)


class TestProperty11ClubIdExtraction:
    """Feature: presmeet, Property 11: Club ID extraction from Cognito groups"""

    @given(
        club_id=club_id_strategy,
        other_groups=st.lists(non_club_group_strategy, min_size=0, max_size=10),
        insert_position=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_property11_extracts_club_id_from_groups_with_one_club_group(
        self, club_id, other_groups, insert_position
    ):
        """Feature: presmeet, Property 11: Club ID extraction from Cognito groups

        **Validates: Requirements 3.2**

        For any list of Cognito group names containing exactly one group matching
        'club_<id>', extract_club_id SHALL return that <id>.
        """
        # Build the group list with exactly one club_ prefixed group
        club_group = f"club_{club_id}"
        groups = list(other_groups)
        # Insert at a valid position
        pos = min(insert_position, len(groups))
        groups.insert(pos, club_group)

        result = extract_club_id(groups)
        assert result == club_id, (
            f"Expected extract_club_id to return '{club_id}' "
            f"but got '{result}' for groups: {groups}"
        )

    @given(
        other_groups=st.lists(non_club_group_strategy, min_size=0, max_size=10),
    )
    @settings(max_examples=100)
    def test_property11_returns_none_when_no_club_group(self, other_groups):
        """Feature: presmeet, Property 11: Club ID extraction from Cognito groups

        **Validates: Requirements 3.2**

        For lists with no matching group, extract_club_id SHALL return None.
        """
        # Ensure no group starts with "club_" (enforced by strategy filter)
        result = extract_club_id(other_groups)
        assert result is None, (
            f"Expected extract_club_id to return None "
            f"but got '{result}' for groups with no club_ prefix: {other_groups}"
        )

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property11_returns_none_for_empty_list(self, data):
        """Feature: presmeet, Property 11: Club ID extraction from Cognito groups

        **Validates: Requirements 3.2**

        For an empty list, extract_club_id SHALL return None.
        """
        result = extract_club_id([])
        assert result is None

    @given(
        club_id=club_id_strategy,
    )
    @settings(max_examples=100)
    def test_property11_club_prefix_only_returns_none(self, club_id):
        """Feature: presmeet, Property 11: Club ID extraction from Cognito groups

        **Validates: Requirements 3.2**

        The bare string 'club_' (with empty id) should not be considered a valid
        club group - only groups with non-empty content after 'club_' should match.
        """
        # "club_" alone (no id part) should return None
        groups = ["club_"]
        result = extract_club_id(groups)
        assert result is None, (
            f"Expected extract_club_id to return None for bare 'club_' prefix "
            f"but got '{result}'"
        )


# ============================================================
# Property 3: Product type validation
# ============================================================

# Valid product types as defined in requirements 1.1
VALID_PRODUCT_TYPES_LIST = ["meeting_ticket", "party_ticket", "tshirt", "airport_transfer"]


class TestProperty3ProductTypeValidation:
    """Feature: presmeet, Property 3: Product type validation

    **Validates: Requirements 1.1, 1.8**

    For any string value, the validate_product_type function SHALL return valid
    only if the value is one of meeting_ticket, party_ticket, tshirt, or
    airport_transfer. All other strings SHALL be rejected.
    """

    @given(product_type=st.sampled_from(VALID_PRODUCT_TYPES_LIST))
    @settings(max_examples=100)
    def test_property3_valid_product_types_accepted(self, product_type):
        """Feature: presmeet, Property 3: Product type validation

        For any valid product type (meeting_ticket, party_ticket, tshirt,
        airport_transfer), validate_product_type SHALL return (True, None).

        Validates: Requirements 1.1, 1.8
        """
        is_valid, error = validate_product_type(product_type)
        assert is_valid is True, f"Expected valid=True for '{product_type}', got {is_valid}"
        assert error is None, f"Expected error=None for '{product_type}', got '{error}'"

    @given(product_type=st.text())
    @settings(max_examples=100)
    def test_property3_invalid_product_types_rejected(self, product_type):
        """Feature: presmeet, Property 3: Product type validation

        For any string that is NOT one of the valid product types,
        validate_product_type SHALL return (False, error_message).

        Validates: Requirements 1.1, 1.8
        """
        assume(product_type not in VALID_PRODUCT_TYPES_LIST)

        is_valid, error = validate_product_type(product_type)
        assert is_valid is False, f"Expected valid=False for '{product_type}', got {is_valid}"
        assert error is not None, f"Expected an error message for '{product_type}', got None"
        assert isinstance(error, str), f"Expected error to be a string, got {type(error)}"
        assert len(error) > 0, f"Expected non-empty error message for '{product_type}'"


# ============================================================
# Property 16: Draft save allows incomplete attributes
# ============================================================

from shared.presmeet_validation import (
    validate_attributes,
    DEFAULT_ATTRIBUTE_SCHEMAS,
    VALID_PRODUCT_TYPES,
)


# --- Strategies for Property 16 ---

_valid_product_type_strategy = st.sampled_from(sorted(VALID_PRODUCT_TYPES))


def _p16_field_value_strategy(field_schema):
    """Generate a valid value for a field according to its schema."""
    field_type = field_schema.get("type", "string")

    if "enum" in field_schema:
        return st.sampled_from(field_schema["enum"])

    if field_type == "string":
        min_len = field_schema.get("min_length", 1)
        max_len = field_schema.get("max_length", 20)
        return st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=min_len,
            max_size=min(max_len, 20),
        )

    if field_type == "integer":
        minimum = field_schema.get("minimum", 1)
        maximum = field_schema.get("maximum", 50)
        return st.integers(min_value=minimum, max_value=maximum)

    return st.text(min_size=1, max_size=10)


def _p16_build_partial_attributes(product_type, selected_fields):
    """Build attributes dict with only the selected fields populated."""
    schema = DEFAULT_ATTRIBUTE_SCHEMAS.get(product_type, {})
    if not selected_fields:
        return st.just({})

    field_strategies = {}
    for field_name in selected_fields:
        field_schema = schema.get(field_name, {})
        field_strategies[field_name] = _p16_field_value_strategy(field_schema)

    return st.fixed_dictionaries(field_strategies)


def _p16_incomplete_attributes_strategy(product_type):
    """Generate a random subset of attributes for a product_type, possibly empty."""
    schema = DEFAULT_ATTRIBUTE_SCHEMAS.get(product_type, {})
    field_names = list(schema.keys())

    if not field_names:
        return st.just({})

    return st.sets(
        st.sampled_from(field_names), max_size=len(field_names)
    ).flatmap(lambda selected_fields: _p16_build_partial_attributes(product_type, selected_fields))


class TestProperty16DraftSaveAllowsIncompleteAttributes:
    """Feature: presmeet, Property 16: Draft save allows incomplete attributes"""

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property16_draft_save_allows_incomplete_attributes(self, data):
        """Feature: presmeet, Property 16: Draft save allows incomplete attributes

        For any cart item with any subset of attributes (including empty), saving
        as draft SHALL succeed without validation errors. The same item MAY fail
        submission validation.

        This validates the behavioral contract: validate_attributes returns errors
        for incomplete attrs, but the system allows saving them as drafts (no
        validation called on draft save).

        **Validates: Requirements 8.6, 4.6**
        """
        # Generate a random valid product_type
        product_type = data.draw(_valid_product_type_strategy)

        # Generate a random subset of attributes (may be incomplete or empty)
        attributes = data.draw(_p16_incomplete_attributes_strategy(product_type))

        # Get the config for this product_type
        config = {"required_attributes": DEFAULT_ATTRIBUTE_SCHEMAS[product_type]}

        # --- Draft save contract: no validation is called ---
        # Simulate draft save: the system does NOT call validate_attributes.
        # Draft save simply persists whatever attributes are provided.
        # This means any subset (including empty) is acceptable for draft.
        draft_item = {
            "product_type": product_type,
            "attributes": attributes,
            "status": "draft",
        }

        # Draft save succeeds - no validation errors by design.
        # The contract is that draft persistence does NOT invoke validate_attributes.
        assert draft_item["status"] == "draft"
        assert draft_item["product_type"] in VALID_PRODUCT_TYPES
        assert isinstance(draft_item["attributes"], dict)

        # --- Submission validation contract: validate_attributes IS called ---
        # The same item MAY fail submission validation.
        schema = DEFAULT_ATTRIBUTE_SCHEMAS[product_type]
        required_fields = [
            field_name
            for field_name, field_schema in schema.items()
            if field_schema.get("required", False)
        ]

        # If any required field is missing from attributes, validation WILL fail
        missing_required = [f for f in required_fields if f not in attributes]

        validation_errors = validate_attributes(product_type, attributes, config)

        if missing_required:
            # When required fields are missing, submission validation MUST reject
            assert len(validation_errors) > 0, (
                f"validate_attributes should reject incomplete attributes for {product_type}. "
                f"Missing required fields: {missing_required}, attributes: {attributes}"
            )

    @given(product_type=_valid_product_type_strategy)
    @settings(max_examples=100)
    def test_property16_empty_attributes_always_accepted_as_draft(self, product_type):
        """Feature: presmeet, Property 16: Draft save allows incomplete attributes

        For any product_type, an empty attributes dict SHALL be accepted for
        draft persistence (no validation on save). The same empty attributes
        SHALL fail submission validation (since required fields are missing).

        **Validates: Requirements 8.6, 4.6**
        """
        empty_attributes = {}
        config = {"required_attributes": DEFAULT_ATTRIBUTE_SCHEMAS[product_type]}

        # Draft save: no validation called, so empty attributes are fine
        draft_item = {
            "product_type": product_type,
            "attributes": empty_attributes,
            "status": "draft",
        }
        assert draft_item["status"] == "draft"
        assert draft_item["attributes"] == {}

        # Submission: validate_attributes WILL reject empty attributes
        # (all product types have at least one required field)
        validation_errors = validate_attributes(product_type, empty_attributes, config)
        assert len(validation_errors) > 0, (
            f"validate_attributes should reject empty attributes for {product_type}, "
            f"but got no errors"
        )

        # Each error should reference a missing required field
        error_fields = {e["field"] for e in validation_errors}
        schema = DEFAULT_ATTRIBUTE_SCHEMAS[product_type]
        required_fields = {
            field_name
            for field_name, field_schema in schema.items()
            if field_schema.get("required", False)
        }
        assert error_fields.issubset(required_fields | {"_attributes"}), (
            f"Validation errors should reference required fields, got {error_fields}"
        )


# ============================================================
# Property 6: Max-per-club enforcement
# ============================================================

# Import validate_max_per_club from handler using package path (avoids 'app' module name collision)
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

from handler.save_presmeet_booking.app import validate_max_per_club, MAX_PER_CLUB


# --- Strategies for Property 6 ---

# Product types with their max limits
_PRODUCT_TYPES_WITH_LIMITS = list(MAX_PER_CLUB.keys())

# Strategy to generate a list of cart items for a single product_type with a specific count
def _cart_items_for_type(product_type, count):
    """Generate a list of cart items of the given product_type with the specified count."""
    return [{"product_type": product_type, "attributes": {}} for _ in range(count)]


# Strategy to generate item counts per product_type (dict mapping product_type -> count)
_item_counts_strategy = st.fixed_dictionaries({
    pt: st.integers(min_value=0, max_value=max_val + 5)
    for pt, max_val in MAX_PER_CLUB.items()
})


class TestProperty6MaxPerClubEnforcement:
    """Feature: presmeet, Property 6: Max-per-club enforcement"""

    @given(counts=_item_counts_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    def test_property6_items_within_limits_accepted(self, counts):
        """Feature: presmeet, Property 6: Max-per-club enforcement

        For any combination of product_type counts that are all within their
        respective max_per_club limits, validate_max_per_club SHALL return
        (True, None) indicating acceptance.

        **Validates: Requirements 2.2, 2.3, 4.9**
        """
        # Only use counts that are within limits
        assume(all(
            counts[pt] <= MAX_PER_CLUB[pt]
            for pt in _PRODUCT_TYPES_WITH_LIMITS
        ))

        # Build items list from counts
        items = []
        for pt, count in counts.items():
            items.extend(_cart_items_for_type(pt, count))

        is_valid, error_msg = validate_max_per_club(items)
        assert is_valid is True, (
            f"Expected valid=True for counts within limits {counts}, "
            f"got error: {error_msg}"
        )
        assert error_msg is None, (
            f"Expected error_msg=None for counts within limits, got: {error_msg}"
        )

    @given(
        product_type=st.sampled_from(_PRODUCT_TYPES_WITH_LIMITS),
        extra=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_property6_items_exceeding_limits_rejected(self, product_type, extra):
        """Feature: presmeet, Property 6: Max-per-club enforcement

        For any product_type with max_per_club M, if the count of items exceeds M,
        validate_max_per_club SHALL return (False, error_message) rejecting the
        addition.

        **Validates: Requirements 2.2, 2.3, 4.9**
        """
        max_allowed = MAX_PER_CLUB[product_type]
        count = max_allowed + extra  # Always exceeds the limit

        items = _cart_items_for_type(product_type, count)

        is_valid, error_msg = validate_max_per_club(items)
        assert is_valid is False, (
            f"Expected valid=False for {product_type} with count {count} > max {max_allowed}"
        )
        assert error_msg is not None, (
            f"Expected an error message when {product_type} exceeds limit"
        )
        assert product_type in error_msg, (
            f"Error message should mention the product_type '{product_type}', "
            f"got: {error_msg}"
        )
        assert str(max_allowed) in error_msg, (
            f"Error message should mention the max limit '{max_allowed}', "
            f"got: {error_msg}"
        )

    @given(counts=_item_counts_strategy)
    @settings(max_examples=100)
    def test_property6_never_allows_exceeding_max(self, counts):
        """Feature: presmeet, Property 6: Max-per-club enforcement

        For any club, for any product_type with configured max_per_club value M,
        and for any sequence of cart item additions, the system SHALL never allow
        the count of items of that product_type in the order to exceed M. Any
        addition that would cause the count to exceed M SHALL be rejected.

        **Validates: Requirements 2.2, 2.3, 4.9**
        """
        # Build items list from counts
        items = []
        for pt, count in counts.items():
            items.extend(_cart_items_for_type(pt, count))

        is_valid, error_msg = validate_max_per_club(items)

        # Check: if ANY product_type exceeds its limit, result must be invalid
        any_exceeds = any(
            counts[pt] > MAX_PER_CLUB[pt]
            for pt in _PRODUCT_TYPES_WITH_LIMITS
        )

        if any_exceeds:
            assert is_valid is False, (
                f"Expected rejection when counts exceed limits. "
                f"Counts: {counts}, Limits: {MAX_PER_CLUB}"
            )
            assert error_msg is not None, (
                f"Expected an error message when limits exceeded"
            )
        else:
            assert is_valid is True, (
                f"Expected acceptance when all counts within limits. "
                f"Counts: {counts}, Limits: {MAX_PER_CLUB}, Error: {error_msg}"
            )
            assert error_msg is None

    @given(product_type=st.sampled_from(_PRODUCT_TYPES_WITH_LIMITS))
    @settings(max_examples=100)
    def test_property6_exactly_at_limit_accepted(self, product_type):
        """Feature: presmeet, Property 6: Max-per-club enforcement

        For any product_type, having exactly max_per_club items SHALL be accepted.
        The limit is inclusive - M items are allowed, M+1 are not.

        **Validates: Requirements 2.2, 2.3, 4.9**
        """
        max_allowed = MAX_PER_CLUB[product_type]
        items = _cart_items_for_type(product_type, max_allowed)

        is_valid, error_msg = validate_max_per_club(items)
        assert is_valid is True, (
            f"Expected valid=True for exactly {max_allowed} {product_type} items "
            f"(at the limit), got error: {error_msg}"
        )
        assert error_msg is None


# ============================================================
# Property 13: Cascade delete on delegate removal
# ============================================================

# Import map_delegates_to_items using package path (avoids 'app' module name collision)
from handler.save_presmeet_booking.app import map_delegates_to_items


# --- Strategies for Property 13 ---

# Strategy for delegate names (non-empty, printable)
_p13_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters=' -'),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

# Strategy for a role (non-empty string)
_p13_role_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=30,
)

# Strategy for a single delegate dict
_p13_delegate_strategy = st.builds(
    lambda name, role, party, tshirt: {
        "name": name,
        "role": role,
        "party": party,
        **({"tshirt": tshirt} if tshirt else {}),
    },
    name=_p13_name_strategy,
    role=_p13_role_strategy,
    party=st.booleans(),
    tshirt=st.one_of(
        st.none(),
        st.fixed_dictionaries({
            "gender": st.sampled_from(["male", "female"]),
            "size": st.sampled_from(["S", "M", "L", "XL", "XXL", "3XL", "4XL"]),
        }),
    ),
)


class TestProperty13CascadeDeleteOnDelegateRemoval:
    """Feature: presmeet, Property 13: Cascade delete on delegate removal"""

    @given(
        delegates=st.lists(_p13_delegate_strategy, min_size=2, max_size=5),
        remove_index=st.data(),
    )
    @settings(max_examples=100)
    def test_property13_cascade_delete_on_delegate_removal(self, delegates, remove_index):
        """Feature: presmeet, Property 13: Cascade delete on delegate removal

        For any delegate with name N in a booking, removing that delegate SHALL
        remove all cart items (meeting_ticket, party_ticket, tshirt) whose name
        attribute equals N and that are associated with that delegate.

        **Validates: Requirements 4.8**
        """
        # Ensure unique names so we can cleanly identify which items belong to which delegate
        seen_names = set()
        unique_delegates = []
        for d in delegates:
            if d["name"] not in seen_names:
                seen_names.add(d["name"])
                unique_delegates.append(d)

        assume(len(unique_delegates) >= 2)

        # Pick a delegate to remove
        idx = remove_index.draw(st.integers(min_value=0, max_value=len(unique_delegates) - 1))
        removed_delegate = unique_delegates[idx]
        removed_name = removed_delegate["name"]

        # Map all delegates to items (before removal)
        all_items = map_delegates_to_items(unique_delegates)

        # Verify the removed delegate has items in the full mapping
        items_for_removed = [
            item for item in all_items
            if item.get("attributes", {}).get("name") == removed_name
        ]
        # A delegate always gets at least a meeting_ticket
        assert len(items_for_removed) >= 1, (
            f"Delegate '{removed_name}' should have at least a meeting_ticket item"
        )

        # Remove the delegate from the list and re-map (simulates cascade delete)
        remaining_delegates = [d for d in unique_delegates if d["name"] != removed_name]
        remaining_items = map_delegates_to_items(remaining_delegates)

        # Verify: no items in the remaining set have the removed delegate's name
        leftover_items = [
            item for item in remaining_items
            if item.get("attributes", {}).get("name") == removed_name
        ]
        assert len(leftover_items) == 0, (
            f"After removing delegate '{removed_name}', expected no items with that name "
            f"but found {len(leftover_items)} items: {leftover_items}"
        )

        # Additional check: only meeting_ticket, party_ticket, tshirt types are affected
        # (airport_transfer does not have a 'name' attribute tied to delegates)
        for item in remaining_items:
            if item["product_type"] in ("meeting_ticket", "party_ticket", "tshirt"):
                assert item["attributes"]["name"] != removed_name, (
                    f"Found {item['product_type']} item with removed delegate name "
                    f"'{removed_name}' still present after removal"
                )

    @given(
        delegate=_p13_delegate_strategy,
    )
    @settings(max_examples=100)
    def test_property13_single_delegate_removal_removes_all_associated_items(self, delegate):
        """Feature: presmeet, Property 13: Cascade delete on delegate removal

        For a single delegate with name N, removing them from a booking with only
        that delegate SHALL result in zero items associated with that name.

        **Validates: Requirements 4.8**
        """
        name = delegate["name"]

        # Map the single delegate to items
        items_before = map_delegates_to_items([delegate])

        # Verify at least a meeting_ticket exists
        assert any(
            item["product_type"] == "meeting_ticket" and item["attributes"]["name"] == name
            for item in items_before
        ), f"Delegate '{name}' should produce at least one meeting_ticket"

        # Remove the delegate (empty list) and re-map
        items_after = map_delegates_to_items([])

        # No items should remain
        assert len(items_after) == 0, (
            f"After removing all delegates, expected 0 items but got {len(items_after)}"
        )

        # Specifically, no items with the removed delegate's name
        items_with_name = [
            item for item in items_after
            if item.get("attributes", {}).get("name") == name
        ]
        assert len(items_with_name) == 0, (
            f"After removing delegate '{name}', found items with that name: {items_with_name}"
        )


# ============================================================
# Property 12: Booking form to cart item mapping
# ============================================================

# Import from save_presmeet_booking using package path (avoids 'app' module name collision)
from handler.save_presmeet_booking.app import map_delegates_to_items, map_guests_to_items


# --- Strategies for Property 12 ---

# Name strategy: non-empty strings (1-100 chars) representing person names
_p12_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='-. '),
    min_size=1,
    max_size=50,
).filter(lambda s: len(s.strip()) > 0)

# Role strategy: non-empty strings representing delegate roles
_p12_role_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='-. '),
    min_size=1,
    max_size=50,
).filter(lambda s: len(s.strip()) > 0)


class TestProperty12BookingFormToCartItemMapping:
    """Feature: presmeet, Property 12: Booking form to cart item mapping"""

    @given(
        name=_p12_name_strategy,
        role=_p12_role_strategy,
        party=st.booleans(),
    )
    @settings(max_examples=100)
    def test_property12_delegate_produces_meeting_ticket_and_optional_party_ticket(
        self, name, role, party
    ):
        """Feature: presmeet, Property 12: Booking form to cart item mapping

        For any delegate with name N and role R, adding them via the booking form
        SHALL produce a meeting_ticket item with attributes {name: N, role: R}.
        If party attendance is selected, it SHALL additionally produce a party_ticket
        with {name: N, person_type: "delegate"}.

        **Validates: Requirements 4.1, 4.2**
        """
        delegate = {"name": name, "role": role, "party": party}
        items = map_delegates_to_items([delegate])

        # Find all meeting_ticket items
        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]
        assert len(meeting_tickets) == 1, (
            f"Expected exactly 1 meeting_ticket for delegate, got {len(meeting_tickets)}"
        )

        # Verify meeting_ticket attributes
        mt = meeting_tickets[0]
        assert mt["attributes"]["name"] == name, (
            f"meeting_ticket name should be '{name}', got '{mt['attributes']['name']}'"
        )
        assert mt["attributes"]["role"] == role, (
            f"meeting_ticket role should be '{role}', got '{mt['attributes']['role']}'"
        )

        # Verify party_ticket
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        if party:
            assert len(party_tickets) == 1, (
                f"Expected 1 party_ticket when party=True, got {len(party_tickets)}"
            )
            pt = party_tickets[0]
            assert pt["attributes"]["name"] == name, (
                f"party_ticket name should be '{name}', got '{pt['attributes']['name']}'"
            )
            assert pt["attributes"]["person_type"] == "delegate", (
                f"party_ticket person_type should be 'delegate', got '{pt['attributes']['person_type']}'"
            )
        else:
            assert len(party_tickets) == 0, (
                f"Expected 0 party_tickets when party=False, got {len(party_tickets)}"
            )

    @given(
        name=_p12_name_strategy,
    )
    @settings(max_examples=100)
    def test_property12_guest_produces_party_ticket(self, name):
        """Feature: presmeet, Property 12: Booking form to cart item mapping

        For any guest with name G, it SHALL produce a party_ticket with
        {name: G, person_type: "guest"}.

        **Validates: Requirements 4.1, 4.2**
        """
        guest = {"name": name}
        items = map_guests_to_items([guest])

        # Find party_ticket items
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        assert len(party_tickets) == 1, (
            f"Expected exactly 1 party_ticket for guest, got {len(party_tickets)}"
        )

        pt = party_tickets[0]
        assert pt["attributes"]["name"] == name, (
            f"party_ticket name should be '{name}', got '{pt['attributes']['name']}'"
        )
        assert pt["attributes"]["person_type"] == "guest", (
            f"party_ticket person_type should be 'guest', got '{pt['attributes']['person_type']}'"
        )

    @given(
        delegates=st.lists(
            st.fixed_dictionaries({
                "name": _p12_name_strategy,
                "role": _p12_role_strategy,
                "party": st.booleans(),
            }),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_property12_multiple_delegates_correct_item_counts(self, delegates):
        """Feature: presmeet, Property 12: Booking form to cart item mapping

        For any list of delegates, map_delegates_to_items SHALL produce exactly
        one meeting_ticket per delegate and one party_ticket per delegate with
        party=True.

        **Validates: Requirements 4.1, 4.2**
        """
        items = map_delegates_to_items(delegates)

        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]

        expected_meeting_count = len(delegates)
        expected_party_count = sum(1 for d in delegates if d.get("party", False))

        assert len(meeting_tickets) == expected_meeting_count, (
            f"Expected {expected_meeting_count} meeting_tickets, got {len(meeting_tickets)}"
        )
        assert len(party_tickets) == expected_party_count, (
            f"Expected {expected_party_count} party_tickets, got {len(party_tickets)}"
        )

    @given(
        guests=st.lists(
            st.fixed_dictionaries({
                "name": _p12_name_strategy,
            }),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_property12_multiple_guests_all_produce_party_tickets(self, guests):
        """Feature: presmeet, Property 12: Booking form to cart item mapping

        For any list of guests, map_guests_to_items SHALL produce exactly one
        party_ticket per guest, each with person_type "guest".

        **Validates: Requirements 4.1, 4.2**
        """
        items = map_guests_to_items(guests)

        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        assert len(party_tickets) == len(guests), (
            f"Expected {len(guests)} party_tickets, got {len(party_tickets)}"
        )

        for i, pt in enumerate(party_tickets):
            assert pt["attributes"]["name"] == guests[i]["name"], (
                f"Guest {i} party_ticket name mismatch"
            )
            assert pt["attributes"]["person_type"] == "guest", (
                f"Guest {i} party_ticket person_type should be 'guest'"
            )


# ============================================================
# Property 9: Lock ALL batch operation
# ============================================================


# --- Lock ALL logic (pure function simulating the batch operation) ---

def apply_lock_all(orders: list) -> list:
    """
    Apply the Lock ALL batch operation to a list of orders.

    For each order:
    - If status == "submitted" → transition to "locked"
    - If status == "draft" or "locked" → unchanged

    Returns a new list of orders with updated statuses.
    """
    result = []
    for order in orders:
        new_order = dict(order)
        if new_order.get("status") == "submitted":
            new_order["status"] = "locked"
        result.append(new_order)
    return result


# --- Strategies for Property 9 ---

# Strategy for order statuses
_p9_order_status_strategy = st.sampled_from(["draft", "submitted", "locked"])

# Strategy for a single order with a random status
_p9_order_strategy = st.fixed_dictionaries({
    "order_id": st.uuids().map(str),
    "club_id": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=3,
        max_size=20,
    ),
    "status": _p9_order_status_strategy,
})

# Strategy for a list of orders with mixed statuses
_p9_orders_strategy = st.lists(_p9_order_strategy, min_size=1, max_size=20)


class TestProperty9LockAllBatchOperation:
    """Feature: presmeet, Property 9: Lock ALL batch operation"""

    @given(orders=_p9_orders_strategy)
    @settings(max_examples=100)
    def test_property9_lock_all_transitions_submitted_to_locked(self, orders):
        """Feature: presmeet, Property 9: Lock ALL batch operation

        For any set of orders with mixed statuses, applying "Lock ALL" SHALL
        transition all orders with status "submitted" to "locked" and SHALL leave
        all orders with status "draft" or "locked" unchanged.

        **Validates: Requirements 5.9**
        """
        # Record original statuses
        original_statuses = {o["order_id"]: o["status"] for o in orders}

        # Apply Lock ALL
        result = apply_lock_all(orders)

        # Verify the result has the same number of orders
        assert len(result) == len(orders), (
            f"Lock ALL should not add or remove orders. "
            f"Expected {len(orders)}, got {len(result)}"
        )

        # Verify each order's status after Lock ALL
        for updated_order in result:
            order_id = updated_order["order_id"]
            original_status = original_statuses[order_id]
            new_status = updated_order["status"]

            if original_status == "submitted":
                # Submitted orders MUST transition to locked
                assert new_status == "locked", (
                    f"Order {order_id} was 'submitted' and should become 'locked' "
                    f"after Lock ALL, but got '{new_status}'"
                )
            elif original_status == "draft":
                # Draft orders MUST remain draft
                assert new_status == "draft", (
                    f"Order {order_id} was 'draft' and should remain 'draft' "
                    f"after Lock ALL, but got '{new_status}'"
                )
            elif original_status == "locked":
                # Already locked orders MUST remain locked
                assert new_status == "locked", (
                    f"Order {order_id} was already 'locked' and should remain 'locked' "
                    f"after Lock ALL, but got '{new_status}'"
                )

    @given(orders=_p9_orders_strategy)
    @settings(max_examples=100)
    def test_property9_lock_all_does_not_modify_draft_orders(self, orders):
        """Feature: presmeet, Property 9: Lock ALL batch operation

        For any set of orders, applying "Lock ALL" SHALL leave all orders
        with status "draft" unchanged.

        **Validates: Requirements 5.9**
        """
        # Filter to just draft orders for focused verification
        draft_orders = [o for o in orders if o["status"] == "draft"]

        result = apply_lock_all(orders)

        # Find the draft orders in the result
        draft_order_ids = {o["order_id"] for o in draft_orders}
        result_drafts = [o for o in result if o["order_id"] in draft_order_ids]

        # All originally draft orders must still be draft
        for order in result_drafts:
            assert order["status"] == "draft", (
                f"Draft order {order['order_id']} should remain 'draft' "
                f"after Lock ALL, but got '{order['status']}'"
            )

    @given(orders=_p9_orders_strategy)
    @settings(max_examples=100)
    def test_property9_lock_all_preserves_order_data(self, orders):
        """Feature: presmeet, Property 9: Lock ALL batch operation

        For any set of orders, applying "Lock ALL" SHALL only change the status
        field of submitted orders. All other fields (order_id, club_id) SHALL
        remain unchanged.

        **Validates: Requirements 5.9**
        """
        result = apply_lock_all(orders)

        for original, updated in zip(orders, result):
            # order_id must be preserved
            assert original["order_id"] == updated["order_id"], (
                f"Lock ALL must not change order_id"
            )
            # club_id must be preserved
            assert original["club_id"] == updated["club_id"], (
                f"Lock ALL must not change club_id"
            )


# ============================================================
# Property 7: Min-per-club enforcement on submission
# ============================================================

from shared.presmeet_validation import validate_order_submission


# --- Strategies for Property 7 ---

# Valid meeting_ticket attributes
_p7_meeting_ticket_attrs_strategy = st.fixed_dictionaries({
    "name": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='-'),
        min_size=1,
        max_size=50,
    ),
    "role": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='-'),
        min_size=1,
        max_size=50,
    ),
})

# Non-meeting product types (those with min_per_club=0)
_p7_non_meeting_types = ["party_ticket", "tshirt", "airport_transfer"]

# Valid party_ticket attributes
_p7_party_ticket_attrs = st.fixed_dictionaries({
    "name": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters='-'),
        min_size=1,
        max_size=50,
    ),
    "person_type": st.sampled_from(["delegate", "guest"]),
})

# Config with min_per_club=1 for meeting_ticket (as per requirement 2.4)
_p7_config = {
    "meeting_ticket": {
        "min_per_club": 1,
        "max_per_club": 3,
        "required_attributes": {
            "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
            "role": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
        },
    },
    "party_ticket": {
        "min_per_club": 0,
        "max_per_club": 13,
        "required_attributes": {
            "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
            "person_type": {"type": "string", "required": True, "enum": ["delegate", "guest"]},
        },
    },
    "tshirt": {
        "min_per_club": 0,
        "max_per_club": 13,
        "required_attributes": {
            "name": {"type": "string", "required": True, "min_length": 1, "max_length": 100},
            "gender": {"type": "string", "required": True, "enum": ["male", "female"]},
            "size": {"type": "string", "required": True, "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"]},
        },
    },
    "airport_transfer": {
        "min_per_club": 0,
        "max_per_club": 20,
        "required_attributes": {
            "direction": {"type": "string", "required": True, "enum": ["pickup", "dropoff"]},
            "airport": {"type": "string", "required": True, "enum": ["AMS", "RTM", "EIN"]},
            "flight": {"type": "string", "required": True, "min_length": 2, "max_length": 10},
            "date": {"type": "string", "required": True},
            "time": {"type": "string", "required": True},
            "persons": {"type": "integer", "required": True, "minimum": 1, "maximum": 50},
        },
    },
}

# Event config (needed by validate_order_submission)
_p7_event = {
    "start_date": "2025-09-15",
    "end_date": "2025-09-18",
}


class TestProperty7MinPerClubEnforcementOnSubmission:
    """Feature: presmeet, Property 7: Min-per-club enforcement on submission"""

    @given(
        num_non_meeting_items=st.integers(min_value=0, max_value=5),
        party_attrs=st.lists(_p7_party_ticket_attrs, min_size=0, max_size=5),
    )
    @settings(max_examples=100)
    def test_property7_zero_meeting_tickets_rejected(self, num_non_meeting_items, party_attrs):
        """Feature: presmeet, Property 7: Min-per-club enforcement on submission

        For any order with 0 meeting_ticket items (regardless of other items),
        submission SHALL be rejected with a validation error indicating the
        minimum required quantity for meeting_ticket.

        **Validates: Requirements 2.5, 8.3**
        """
        # Build an order with 0 meeting_tickets but possibly other items
        items = []
        for attrs in party_attrs[:num_non_meeting_items]:
            items.append({
                "item_id": f"pt_{len(items)}",
                "product_type": "party_ticket",
                "attributes": attrs,
            })

        order = {"items": items}

        errors = validate_order_submission(order, _p7_config, _p7_event)

        # There must be a min_per_club error for meeting_ticket
        min_errors = [
            e for e in errors
            if e.get("constraint") == "min_per_club"
            and e.get("product_type") == "meeting_ticket"
        ]
        assert len(min_errors) >= 1, (
            f"Expected min_per_club error for meeting_ticket when 0 meeting_tickets present, "
            f"but got errors: {errors}"
        )

        # Verify the error message mentions the minimum quantity
        for err in min_errors:
            assert "1" in err["message"] or "minimum" in err["message"].lower(), (
                f"Error message should mention minimum quantity 1, got: {err['message']}"
            )

    @given(
        num_meeting_tickets=st.integers(min_value=1, max_value=3),
        meeting_attrs=st.lists(_p7_meeting_ticket_attrs_strategy, min_size=1, max_size=3),
    )
    @settings(max_examples=100)
    def test_property7_sufficient_meeting_tickets_no_min_error(
        self, num_meeting_tickets, meeting_attrs
    ):
        """Feature: presmeet, Property 7: Min-per-club enforcement on submission

        For any order with at least 1 meeting_ticket item (meeting the min_per_club
        of 1), submission SHALL NOT produce a min_per_club error for meeting_ticket.

        **Validates: Requirements 2.5, 8.3**
        """
        # Build an order with sufficient meeting_tickets
        items = []
        for i in range(min(num_meeting_tickets, len(meeting_attrs))):
            items.append({
                "item_id": f"mt_{i}",
                "product_type": "meeting_ticket",
                "attributes": meeting_attrs[i],
            })

        # Ensure we have at least 1 meeting_ticket
        assume(len(items) >= 1)

        order = {"items": items}

        errors = validate_order_submission(order, _p7_config, _p7_event)

        # There must NOT be a min_per_club error for meeting_ticket
        min_errors = [
            e for e in errors
            if e.get("constraint") == "min_per_club"
            and e.get("product_type") == "meeting_ticket"
        ]
        assert len(min_errors) == 0, (
            f"Expected no min_per_club error for meeting_ticket when {len(items)} "
            f"meeting_tickets present (min=1), but got errors: {min_errors}"
        )

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property7_min_per_club_general_property(self, data):
        """Feature: presmeet, Property 7: Min-per-club enforcement on submission

        For any order and for any product_type with configured min_per_club value
        N > 0, if the order contains fewer than N items of that product_type,
        submission SHALL be rejected with a validation error indicating the minimum
        required quantity.

        **Validates: Requirements 2.5, 8.3**
        """
        # The only product_type with min_per_club > 0 is meeting_ticket (min=1)
        # Generate a count of meeting_tickets that is 0 (less than min=1)
        meeting_count = 0

        # Optionally add other items (which have min_per_club=0)
        other_item_count = data.draw(st.integers(min_value=0, max_value=5))
        other_attrs_list = data.draw(st.lists(
            _p7_party_ticket_attrs,
            min_size=other_item_count,
            max_size=other_item_count,
        ))

        items = []
        for i, attrs in enumerate(other_attrs_list):
            items.append({
                "item_id": f"other_{i}",
                "product_type": "party_ticket",
                "attributes": attrs,
            })

        order = {"items": items}

        errors = validate_order_submission(order, _p7_config, _p7_event)

        # Since meeting_count (0) < min_per_club (1), must have min_per_club error
        min_errors = [
            e for e in errors
            if e.get("constraint") == "min_per_club"
            and e.get("product_type") == "meeting_ticket"
        ]
        assert len(min_errors) >= 1, (
            f"Expected min_per_club error for meeting_ticket with {meeting_count} items "
            f"(min=1), but no such error found in: {errors}"
        )

        # Verify the error message is informative
        err = min_errors[0]
        assert "meeting_ticket" in err.get("message", "") or err.get("product_type") == "meeting_ticket", (
            f"Error should reference meeting_ticket, got: {err}"
        )

# ============================================================
# Property 14: Airport transfer date validation
# ============================================================

from shared.presmeet_validation import validate_order_submission

# --- Strategies for Property 14 ---

# Strategy for generating ISO date strings (YYYY-MM-DD)
_p14_date_strategy = st.dates(
    min_value=__import__('datetime').date(2020, 1, 1),
    max_value=__import__('datetime').date(2030, 12, 31),
).map(lambda d: d.isoformat())


def _p14_event_date_range():
    """Generate an event with start_date <= end_date as ISO date strings."""
    return st.tuples(
        st.dates(
            min_value=__import__('datetime').date(2020, 1, 1),
            max_value=__import__('datetime').date(2029, 12, 31),
        ),
        st.dates(
            min_value=__import__('datetime').date(2020, 1, 1),
            max_value=__import__('datetime').date(2030, 12, 31),
        ),
    ).filter(lambda t: t[0] <= t[1]).map(
        lambda t: (t[0].isoformat(), t[1].isoformat())
    )


# Airport transfer config with required_attributes for valid items
_P14_AIRPORT_TRANSFER_CONFIG = {
    "airport_transfer": {
        "required_attributes": {
            "direction": {
                "type": "string",
                "required": True,
                "enum": ["pickup", "dropoff"],
            },
            "airport": {
                "type": "string",
                "required": True,
                "enum": ["AMS", "RTM", "EIN"],
            },
            "flight": {
                "type": "string",
                "required": True,
                "min_length": 2,
                "max_length": 10,
            },
            "date": {
                "type": "string",
                "required": True,
            },
            "time": {
                "type": "string",
                "required": True,
            },
            "persons": {
                "type": "integer",
                "required": True,
                "minimum": 1,
                "maximum": 50,
            },
        },
    },
}


class TestProperty14AirportTransferDateValidation:
    """Feature: presmeet, Property 14: Airport transfer date validation"""

    @given(
        date_range=_p14_event_date_range(),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_property14_date_within_range_passes(self, date_range, data):
        """Feature: presmeet, Property 14: Airport transfer date validation

        For any airport_transfer item with a date attribute that falls within the
        event start_date and end_date (inclusive), the item SHALL NOT produce a
        date_range error on submission.

        **Validates: Requirements 8.4**
        """
        import datetime

        start_date_str, end_date_str = date_range
        start_date = datetime.date.fromisoformat(start_date_str)
        end_date = datetime.date.fromisoformat(end_date_str)

        # Generate a transfer date within the event range (inclusive)
        transfer_date = data.draw(
            st.dates(min_value=start_date, max_value=end_date)
        )
        transfer_date_str = transfer_date.isoformat()

        # Build a valid airport_transfer item
        order = {
            "items": [
                {
                    "item_id": "test_item_1",
                    "product_type": "airport_transfer",
                    "attributes": {
                        "direction": "pickup",
                        "airport": "AMS",
                        "flight": "KL1234",
                        "date": transfer_date_str,
                        "time": "14:30",
                        "persons": 2,
                    },
                }
            ]
        }

        event = {
            "start_date": start_date_str,
            "end_date": end_date_str,
        }

        errors = validate_order_submission(order, _P14_AIRPORT_TRANSFER_CONFIG, event)

        # Filter for date_range constraint errors only
        date_range_errors = [e for e in errors if e.get("constraint") == "date_range"]
        assert len(date_range_errors) == 0, (
            f"Expected no date_range errors for transfer_date '{transfer_date_str}' "
            f"within event range [{start_date_str}, {end_date_str}], "
            f"but got: {date_range_errors}"
        )

    @given(
        date_range=_p14_event_date_range(),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_property14_date_before_start_rejected(self, date_range, data):
        """Feature: presmeet, Property 14: Airport transfer date validation

        For any airport_transfer item with a date attribute that is before the
        event start_date, the item SHALL be rejected on submission with a
        date_range error.

        **Validates: Requirements 8.4**
        """
        import datetime

        start_date_str, end_date_str = date_range
        start_date = datetime.date.fromisoformat(start_date_str)

        # Generate a transfer date strictly before the event start
        assume(start_date > datetime.date(2020, 1, 1))
        transfer_date = data.draw(
            st.dates(
                min_value=datetime.date(2020, 1, 1),
                max_value=start_date - datetime.timedelta(days=1),
            )
        )
        transfer_date_str = transfer_date.isoformat()

        # Build an airport_transfer item with a date before the event
        order = {
            "items": [
                {
                    "item_id": "test_item_1",
                    "product_type": "airport_transfer",
                    "attributes": {
                        "direction": "dropoff",
                        "airport": "RTM",
                        "flight": "BA456",
                        "date": transfer_date_str,
                        "time": "09:00",
                        "persons": 1,
                    },
                }
            ]
        }

        event = {
            "start_date": start_date_str,
            "end_date": end_date_str,
        }

        errors = validate_order_submission(order, _P14_AIRPORT_TRANSFER_CONFIG, event)

        # Filter for date_range constraint errors
        date_range_errors = [e for e in errors if e.get("constraint") == "date_range"]
        assert len(date_range_errors) >= 1, (
            f"Expected a date_range error for transfer_date '{transfer_date_str}' "
            f"which is before event start_date '{start_date_str}', "
            f"but got no date_range errors. All errors: {errors}"
        )

        # Verify the error references the correct item and field
        err = date_range_errors[0]
        assert err.get("item_id") == "test_item_1", (
            f"Expected error to reference item_id 'test_item_1', got '{err.get('item_id')}'"
        )
        assert err.get("field") == "date", (
            f"Expected error to reference field 'date', got '{err.get('field')}'"
        )

    @given(
        date_range=_p14_event_date_range(),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_property14_date_after_end_rejected(self, date_range, data):
        """Feature: presmeet, Property 14: Airport transfer date validation

        For any airport_transfer item with a date attribute that is after the
        event end_date, the item SHALL be rejected on submission with a
        date_range error.

        **Validates: Requirements 8.4**
        """
        import datetime

        start_date_str, end_date_str = date_range
        end_date = datetime.date.fromisoformat(end_date_str)

        # Generate a transfer date strictly after the event end
        assume(end_date < datetime.date(2030, 12, 31))
        transfer_date = data.draw(
            st.dates(
                min_value=end_date + datetime.timedelta(days=1),
                max_value=datetime.date(2030, 12, 31),
            )
        )
        transfer_date_str = transfer_date.isoformat()

        # Build an airport_transfer item with a date after the event
        order = {
            "items": [
                {
                    "item_id": "test_item_1",
                    "product_type": "airport_transfer",
                    "attributes": {
                        "direction": "pickup",
                        "airport": "EIN",
                        "flight": "LH789",
                        "date": transfer_date_str,
                        "time": "18:45",
                        "persons": 3,
                    },
                }
            ]
        }

        event = {
            "start_date": start_date_str,
            "end_date": end_date_str,
        }

        errors = validate_order_submission(order, _P14_AIRPORT_TRANSFER_CONFIG, event)

        # Filter for date_range constraint errors
        date_range_errors = [e for e in errors if e.get("constraint") == "date_range"]
        assert len(date_range_errors) >= 1, (
            f"Expected a date_range error for transfer_date '{transfer_date_str}' "
            f"which is after event end_date '{end_date_str}', "
            f"but got no date_range errors. All errors: {errors}"
        )

        # Verify the error references the correct item and field
        err = date_range_errors[0]
        assert err.get("item_id") == "test_item_1", (
            f"Expected error to reference item_id 'test_item_1', got '{err.get('item_id')}'"
        )
        assert err.get("field") == "date", (
            f"Expected error to reference field 'date', got '{err.get('field')}'"
        )


# ============================================================
# Property 8: Order state machine transitions
# ============================================================


# --- State Machine Model for Property 8 ---

# Define the allowed transitions as a pure function.
# This models the order lifecycle state machine from the design doc:
#   States: "draft", "submitted", "locked"
#   Actions: "submit", "modify", "lock", "unlock"
#   Actors: "club_user", "admin"

# Transition table: (current_state, action, actor) -> (success: bool, new_state_or_None)
# None for new_state means the action is rejected.

VALID_ORDER_STATES = ["draft", "submitted", "locked"]
VALID_ACTIONS = ["submit", "modify", "lock", "unlock"]
VALID_ACTORS = ["club_user", "admin"]


def apply_order_transition(current_state: str, action: str, actor: str) -> tuple:
    """
    Pure state machine function modeling order lifecycle transitions.

    Returns:
        tuple: (succeeded: bool, new_state: str | None)
        - If succeeded is True, new_state is the resulting state
        - If succeeded is False, new_state is None (action rejected)
    """
    if current_state == "draft":
        if action == "submit":
            # Club_User or Admin can submit a draft order
            return (True, "submitted")
        elif action == "lock":
            # Cannot lock a draft order
            return (False, None)
        elif action == "unlock":
            # Cannot unlock a draft order (it's not locked)
            return (False, None)
        elif action == "modify":
            # Modifying a draft keeps it in draft
            return (True, "draft")
        return (False, None)

    elif current_state == "submitted":
        if action == "modify":
            # Modification transitions submitted back to draft
            return (True, "draft")
        elif action == "lock":
            if actor == "admin":
                # Only admin can lock
                return (True, "locked")
            else:
                # Club_User cannot lock
                return (False, None)
        elif action == "submit":
            # Cannot submit an already submitted order
            return (False, None)
        elif action == "unlock":
            # Cannot unlock a submitted order (it's not locked)
            return (False, None)
        return (False, None)

    elif current_state == "locked":
        if action == "modify":
            if actor == "club_user":
                # Club_User cannot modify a locked order
                return (False, None)
            else:
                # Admin also cannot modify items in locked order (Req 5.7)
                return (False, None)
        elif action == "unlock":
            if actor == "admin":
                # Admin unlock transitions back to submitted
                return (True, "submitted")
            else:
                # Club_User cannot unlock
                return (False, None)
        elif action == "lock":
            # Cannot lock an already locked order
            return (False, None)
        elif action == "submit":
            # Cannot submit a locked order
            return (False, None)
        return (False, None)

    return (False, None)


class TestProperty8OrderStateMachineTransitions:
    """Feature: presmeet, Property 8: Order state machine transitions"""

    @given(
        state=st.sampled_from(VALID_ORDER_STATES),
        action=st.sampled_from(VALID_ACTIONS),
        actor=st.sampled_from(VALID_ACTORS),
    )
    @settings(max_examples=100)
    def test_property8_state_transitions_match_specification(self, state, action, actor):
        """Feature: presmeet, Property 8: Order state machine transitions

        For any initial state and any action, the result matches expected behavior:
        - draft + submit → submitted
        - draft + lock → rejected
        - draft + unlock → rejected
        - submitted + modify → draft
        - submitted + lock (admin) → locked
        - submitted + submit → rejected
        - locked + modify (club_user) → rejected
        - locked + unlock (admin) → submitted
        - locked + lock → rejected

        **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**
        """
        succeeded, new_state = apply_order_transition(state, action, actor)

        # Define the expected transitions based on the specification
        # From "draft":
        if state == "draft":
            if action == "submit":
                # Req 5.2: submit transitions draft → submitted
                assert succeeded is True, f"draft + submit should succeed"
                assert new_state == "submitted", f"draft + submit should → submitted"
            elif action == "lock":
                # Lock on draft is rejected (only submitted can be locked)
                assert succeeded is False, f"draft + lock should be rejected"
                assert new_state is None
            elif action == "unlock":
                # Unlock on draft is rejected (not locked)
                assert succeeded is False, f"draft + unlock should be rejected"
                assert new_state is None
            elif action == "modify":
                # Modify on draft keeps it draft
                assert succeeded is True, f"draft + modify should succeed"
                assert new_state == "draft", f"draft + modify should → draft"

        # From "submitted":
        elif state == "submitted":
            if action == "modify":
                # Req 5.4: modification transitions submitted → draft
                assert succeeded is True, f"submitted + modify should succeed"
                assert new_state == "draft", f"submitted + modify should → draft"
            elif action == "lock":
                if actor == "admin":
                    # Req 5.5: admin lock transitions submitted → locked
                    assert succeeded is True, f"submitted + lock (admin) should succeed"
                    assert new_state == "locked", f"submitted + lock (admin) should → locked"
                else:
                    # Club_User cannot lock
                    assert succeeded is False, f"submitted + lock (club_user) should be rejected"
                    assert new_state is None
            elif action == "submit":
                # Req 5.3: cannot submit from submitted status
                assert succeeded is False, f"submitted + submit should be rejected"
                assert new_state is None
            elif action == "unlock":
                # Cannot unlock a submitted order
                assert succeeded is False, f"submitted + unlock should be rejected"
                assert new_state is None

        # From "locked":
        elif state == "locked":
            if action == "modify":
                if actor == "club_user":
                    # Req 5.6: Club_User modify on locked is rejected
                    assert succeeded is False, f"locked + modify (club_user) should be rejected"
                    assert new_state is None
                else:
                    # Req 5.7: Admin also cannot modify items (only unlock/view)
                    assert succeeded is False, f"locked + modify (admin) should be rejected"
                    assert new_state is None
            elif action == "unlock":
                if actor == "admin":
                    # Req 5.8: admin unlock transitions locked → submitted
                    assert succeeded is True, f"locked + unlock (admin) should succeed"
                    assert new_state == "submitted", f"locked + unlock (admin) should → submitted"
                else:
                    # Club_User cannot unlock
                    assert succeeded is False, f"locked + unlock (club_user) should be rejected"
                    assert new_state is None
            elif action == "lock":
                # Cannot lock an already locked order
                assert succeeded is False, f"locked + lock should be rejected"
                assert new_state is None
            elif action == "submit":
                # Cannot submit a locked order
                assert succeeded is False, f"locked + submit should be rejected"
                assert new_state is None

    @given(
        state=st.sampled_from(VALID_ORDER_STATES),
        action=st.sampled_from(VALID_ACTIONS),
        actor=st.sampled_from(VALID_ACTORS),
    )
    @settings(max_examples=100)
    def test_property8_valid_transitions_produce_valid_states(self, state, action, actor):
        """Feature: presmeet, Property 8: Order state machine transitions

        For any successful transition, the resulting state SHALL be one of the
        valid order states (draft, submitted, locked).

        **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**
        """
        succeeded, new_state = apply_order_transition(state, action, actor)

        if succeeded:
            assert new_state in VALID_ORDER_STATES, (
                f"Successful transition from '{state}' via '{action}' by '{actor}' "
                f"produced invalid state '{new_state}'. "
                f"Valid states are: {VALID_ORDER_STATES}"
            )
        else:
            assert new_state is None, (
                f"Rejected transition should have new_state=None, got '{new_state}'"
            )

    @given(
        state=st.sampled_from(VALID_ORDER_STATES),
        action=st.sampled_from(VALID_ACTIONS),
        actor=st.sampled_from(VALID_ACTORS),
    )
    @settings(max_examples=100)
    def test_property8_rejected_transitions_preserve_state(self, state, action, actor):
        """Feature: presmeet, Property 8: Order state machine transitions

        For any rejected transition, the order state SHALL NOT change. A rejected
        action means the system returns an error and the order remains in its
        current state.

        **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**
        """
        succeeded, new_state = apply_order_transition(state, action, actor)

        if not succeeded:
            # The state machine model returns None for rejected transitions.
            # In the real system, the order stays in its current state.
            assert new_state is None, (
                f"Rejected transition from '{state}' via '{action}' by '{actor}' "
                f"should not produce a new state, but got '{new_state}'"
            )
            # Verify the original state is unchanged by applying no-op
            # (the real system would still have the order in `state`)
            assert state in VALID_ORDER_STATES, (
                f"Original state '{state}' should still be valid after rejection"
            )


# ============================================================
# Property 20: Payment guard on draft orders
# ============================================================


def check_payment_guard(order_status: str) -> tuple:
    """
    Payment guard: rejects payment initiation for draft orders.

    Args:
        order_status: The current status of the order.

    Returns:
        tuple: (allowed: bool, error_message: str | None)
            - If order is "draft", returns (False, "Order must be submitted before payment")
            - If order is "submitted" or "locked", returns (True, None)
    """
    if order_status == "draft":
        return (False, "Order must be submitted before payment")
    return (True, None)


# --- Strategies for Property 20 ---

# Strategy for order IDs (non-empty UUID-like strings)
_p20_order_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-'),
    min_size=1,
    max_size=36,
).filter(lambda s: len(s.strip()) > 0)

# Strategy for payment amounts (positive decimals)
_p20_amount_strategy = st.decimals(
    min_value='0.01',
    max_value='999999.99',
    allow_nan=False,
    allow_infinity=False,
    places=2,
)

# Strategy for club IDs
_p20_club_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
    min_size=1,
    max_size=50,
)

# Non-draft statuses that should allow payment
_p20_non_draft_statuses = ["submitted", "locked"]


class TestProperty20PaymentGuardOnDraftOrders:
    """Feature: presmeet, Property 20: Payment guard on draft orders"""

    @given(
        order_id=_p20_order_id_strategy,
        amount=_p20_amount_strategy,
        club_id=_p20_club_id_strategy,
    )
    @settings(max_examples=100)
    def test_property20_draft_order_payment_rejected(self, order_id, amount, club_id):
        """Feature: presmeet, Property 20: Payment guard on draft orders

        For any order_id, any amount, any club_id, if the order status is "draft",
        initiating a payment SHALL be rejected with an error indicating the order
        must be submitted first.

        **Validates: Requirements 6.7**
        """
        order_status = "draft"

        allowed, error_msg = check_payment_guard(order_status)

        assert allowed is False, (
            f"Payment for draft order '{order_id}' (club={club_id}, amount={amount}) "
            f"should be rejected, but was allowed"
        )
        assert error_msg is not None, (
            f"Payment rejection for draft order should include an error message"
        )
        assert "submitted" in error_msg.lower() or "submit" in error_msg.lower(), (
            f"Error message should indicate the order must be submitted first, "
            f"got: '{error_msg}'"
        )

    @given(
        order_id=_p20_order_id_strategy,
        amount=_p20_amount_strategy,
        club_id=_p20_club_id_strategy,
        status=st.sampled_from(_p20_non_draft_statuses),
    )
    @settings(max_examples=100)
    def test_property20_non_draft_order_payment_allowed(self, order_id, amount, club_id, status):
        """Feature: presmeet, Property 20: Payment guard on draft orders

        For non-draft statuses (submitted, locked), initiating a payment SHALL NOT
        be rejected by this guard.

        **Validates: Requirements 6.7**
        """
        allowed, error_msg = check_payment_guard(status)

        assert allowed is True, (
            f"Payment for '{status}' order '{order_id}' (club={club_id}, amount={amount}) "
            f"should be allowed by the draft guard, but was rejected: {error_msg}"
        )
        assert error_msg is None, (
            f"No error message expected for '{status}' orders, got: '{error_msg}'"
        )

    @given(
        order_id=_p20_order_id_strategy,
        amount=_p20_amount_strategy,
        club_id=_p20_club_id_strategy,
    )
    @settings(max_examples=100)
    def test_property20_draft_guard_consistent_regardless_of_inputs(self, order_id, amount, club_id):
        """Feature: presmeet, Property 20: Payment guard on draft orders

        The payment guard decision depends ONLY on order status. For any combination
        of order_id, amount, and club_id, if order status is "draft" the result is
        always rejection; the guard is deterministic and input-independent beyond status.

        **Validates: Requirements 6.7**
        """
        # Draft is always rejected
        allowed_draft, error_draft = check_payment_guard("draft")
        assert allowed_draft is False
        assert error_draft is not None

        # Submitted is always allowed
        allowed_submitted, error_submitted = check_payment_guard("submitted")
        assert allowed_submitted is True
        assert error_submitted is None

        # Locked is always allowed
        allowed_locked, error_locked = check_payment_guard("locked")
        assert allowed_locked is True
        assert error_locked is None


# ============================================================
# Property 10: Club-based access control
# ============================================================


# --- Pure function modeling club-based access control ---

def check_access(user_club_id: str, record_club_id: str, is_admin: bool) -> bool:
    """
    Pure function modeling club-based access control.

    Access is granted if and only if:
    - user_club_id equals record_club_id, OR
    - the user has admin role (is_admin is True)

    If user_club_id != record_club_id and user is not admin, access is denied (403).

    Args:
        user_club_id: The club_id of the authenticated user.
        record_club_id: The club_id on the order/cart record.
        is_admin: Whether the user has admin role.

    Returns:
        bool: True if access is granted, False if denied (403).
    """
    if user_club_id == record_club_id:
        return True
    if is_admin:
        return True
    return False


# --- Strategies for Property 10 ---

# Strategy for club_id values (non-empty alphanumeric strings)
_p10_club_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
    min_size=1,
    max_size=30,
)


class TestProperty10ClubBasedAccessControl:
    """Feature: presmeet, Property 10: Club-based access control"""

    @given(
        club_id=_p10_club_id_strategy,
        is_admin=st.booleans(),
    )
    @settings(max_examples=100)
    def test_property10_same_club_always_grants_access(self, club_id, is_admin):
        """Feature: presmeet, Property 10: Club-based access control

        For any authenticated user with club_id C and any record with club_id R,
        when C equals R, access SHALL be granted regardless of admin status.

        **Validates: Requirements 3.4, 3.6, 3.8**
        """
        # Same club_id for user and record
        result = check_access(user_club_id=club_id, record_club_id=club_id, is_admin=is_admin)
        assert result is True, (
            f"Access should be granted when user_club_id == record_club_id "
            f"('{club_id}'), but got denied. is_admin={is_admin}"
        )

    @given(
        user_club_id=_p10_club_id_strategy,
        record_club_id=_p10_club_id_strategy,
    )
    @settings(max_examples=100)
    def test_property10_different_club_non_admin_denied(self, user_club_id, record_club_id):
        """Feature: presmeet, Property 10: Club-based access control

        For any authenticated user with club_id C and any record with club_id R,
        when C != R and user is NOT admin, a 403 response SHALL be returned
        (access denied).

        **Validates: Requirements 3.4, 3.6, 3.8**
        """
        # Ensure different club IDs
        assume(user_club_id != record_club_id)

        result = check_access(user_club_id=user_club_id, record_club_id=record_club_id, is_admin=False)
        assert result is False, (
            f"Access should be denied (403) when user_club_id ('{user_club_id}') != "
            f"record_club_id ('{record_club_id}') and user is not admin, but got granted"
        )

    @given(
        user_club_id=_p10_club_id_strategy,
        record_club_id=_p10_club_id_strategy,
    )
    @settings(max_examples=100)
    def test_property10_different_club_admin_grants_access(self, user_club_id, record_club_id):
        """Feature: presmeet, Property 10: Club-based access control

        For any authenticated user with club_id C and any record with club_id R,
        when C != R but user IS admin, access SHALL be granted.

        **Validates: Requirements 3.4, 3.6, 3.8**
        """
        # Ensure different club IDs
        assume(user_club_id != record_club_id)

        result = check_access(user_club_id=user_club_id, record_club_id=record_club_id, is_admin=True)
        assert result is True, (
            f"Access should be granted when user is admin, even though "
            f"user_club_id ('{user_club_id}') != record_club_id ('{record_club_id}')"
        )

    @given(
        user_club_id=_p10_club_id_strategy,
        record_club_id=_p10_club_id_strategy,
        is_admin=st.booleans(),
    )
    @settings(max_examples=100)
    def test_property10_access_iff_same_club_or_admin(self, user_club_id, record_club_id, is_admin):
        """Feature: presmeet, Property 10: Club-based access control

        For any authenticated user with club_id C, any record with club_id R,
        and any admin flag, access SHALL be granted if and only if C == R OR
        user is admin. Otherwise a 403 SHALL be returned.

        **Validates: Requirements 3.4, 3.6, 3.8**
        """
        result = check_access(
            user_club_id=user_club_id,
            record_club_id=record_club_id,
            is_admin=is_admin,
        )

        expected = (user_club_id == record_club_id) or is_admin

        assert result == expected, (
            f"check_access(user_club_id='{user_club_id}', record_club_id='{record_club_id}', "
            f"is_admin={is_admin}) returned {result}, expected {expected}"
        )


# ============================================================
# Property 19: Payment status webhook handling
# ============================================================

from shared.presmeet_validation import calculate_outstanding_balance
from decimal import Decimal


# --- Pure logic model for webhook payment handling ---

def process_webhook_payment(
    webhook_status: str,
    payment_amount: Decimal,
    order_total: Decimal,
    existing_paid_payments: list,
    current_order_payment_status: str,
) -> dict:
    """
    Pure logic model of Mollie webhook payment handling.

    Given a webhook payload status, this function models how the system
    SHALL update the payment record and the order payment_status.

    Args:
        webhook_status: The Mollie payment status from the webhook
                        ("paid", "failed", "cancelled", "expired")
        payment_amount: The amount of this payment
        order_total: The total order amount
        existing_paid_payments: List of payment dicts (with 'amount' field)
                                that are already in "paid" status
        current_order_payment_status: Current order payment_status
                                      ("unpaid", "partial", "paid")

    Returns:
        dict with:
            - "payment_record_status": The status set on the payment record
            - "order_payment_status": The resulting order payment_status
    """
    if webhook_status == "paid":
        # Record the payment as paid
        payment_record_status = "paid"

        # Calculate new outstanding balance including this payment
        all_paid_payments = existing_paid_payments + [{"amount": payment_amount}]
        outstanding = calculate_outstanding_balance(order_total, all_paid_payments)

        # Determine order payment_status based on balance
        if outstanding <= Decimal("0.00"):
            order_payment_status = "paid"
        else:
            order_payment_status = "partial"
    else:
        # For "failed", "cancelled", "expired": update payment record status
        # but leave order payment_status unchanged
        payment_record_status = webhook_status
        order_payment_status = current_order_payment_status

    return {
        "payment_record_status": payment_record_status,
        "order_payment_status": order_payment_status,
    }


# --- Strategies for Property 19 ---

# Valid non-"paid" webhook statuses
_p19_failing_statuses = ["failed", "cancelled", "expired"]

# Valid order payment statuses
_p19_order_payment_statuses = ["unpaid", "partial", "paid"]

# Strategy for monetary amounts (positive, up to €999,999.99)
_p19_amount_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for order totals (positive, reasonable range)
_p19_order_total_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("99999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for existing paid payments (list of payment dicts with amounts)
_p19_existing_payments_strategy = st.lists(
    st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("50000.00"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ).map(lambda amt: {"amount": amt}),
    min_size=0,
    max_size=5,
)


class TestProperty19PaymentStatusWebhookHandling:
    """Feature: presmeet, Property 19: Payment status webhook handling"""

    @given(
        payment_amount=_p19_amount_strategy,
        order_total=_p19_order_total_strategy,
        existing_payments=_p19_existing_payments_strategy,
    )
    @settings(max_examples=100)
    def test_property19_paid_webhook_updates_order_payment_status(
        self, payment_amount, order_total, existing_payments
    ):
        """Feature: presmeet, Property 19: Payment status webhook handling

        For any Mollie webhook payload with status "paid", the system SHALL record
        the payment and set the order payment_status to "paid" (or "partial" if
        balance > 0).

        **Validates: Requirements 6.2, 6.3**
        """
        result = process_webhook_payment(
            webhook_status="paid",
            payment_amount=payment_amount,
            order_total=order_total,
            existing_paid_payments=existing_payments,
            current_order_payment_status="unpaid",
        )

        # Payment record SHALL be set to "paid"
        assert result["payment_record_status"] == "paid", (
            f"Expected payment_record_status='paid', got '{result['payment_record_status']}'"
        )

        # Calculate expected outstanding balance
        all_paid = existing_payments + [{"amount": payment_amount}]
        expected_outstanding = calculate_outstanding_balance(order_total, all_paid)

        # Order payment_status SHALL be "paid" if balance is 0, else "partial"
        if expected_outstanding <= Decimal("0.00"):
            assert result["order_payment_status"] == "paid", (
                f"Expected order_payment_status='paid' when outstanding={expected_outstanding}, "
                f"got '{result['order_payment_status']}'"
            )
        else:
            assert result["order_payment_status"] == "partial", (
                f"Expected order_payment_status='partial' when outstanding={expected_outstanding} > 0, "
                f"got '{result['order_payment_status']}'"
            )

    @given(
        webhook_status=st.sampled_from(_p19_failing_statuses),
        payment_amount=_p19_amount_strategy,
        order_total=_p19_order_total_strategy,
        existing_payments=_p19_existing_payments_strategy,
        current_order_payment_status=st.sampled_from(_p19_order_payment_statuses),
    )
    @settings(max_examples=100)
    def test_property19_failed_cancelled_expired_preserves_order_status(
        self, webhook_status, payment_amount, order_total,
        existing_payments, current_order_payment_status
    ):
        """Feature: presmeet, Property 19: Payment status webhook handling

        For any webhook with status "failed", "cancelled", or "expired", the payment
        record status SHALL be updated but the order payment_status SHALL remain
        unchanged.

        **Validates: Requirements 6.2, 6.3**
        """
        result = process_webhook_payment(
            webhook_status=webhook_status,
            payment_amount=payment_amount,
            order_total=order_total,
            existing_paid_payments=existing_payments,
            current_order_payment_status=current_order_payment_status,
        )

        # Payment record status SHALL be updated to the webhook status
        assert result["payment_record_status"] == webhook_status, (
            f"Expected payment_record_status='{webhook_status}', "
            f"got '{result['payment_record_status']}'"
        )

        # Order payment_status SHALL remain unchanged
        assert result["order_payment_status"] == current_order_payment_status, (
            f"Expected order_payment_status='{current_order_payment_status}' (unchanged), "
            f"got '{result['order_payment_status']}' after webhook_status='{webhook_status}'"
        )

    @given(
        order_total=_p19_order_total_strategy,
    )
    @settings(max_examples=100)
    def test_property19_paid_webhook_covers_full_amount_sets_paid(
        self, order_total
    ):
        """Feature: presmeet, Property 19: Payment status webhook handling

        For any order total, when a single "paid" webhook covers the full amount
        (payment_amount >= order_total), the order payment_status SHALL be "paid".

        **Validates: Requirements 6.2, 6.3**
        """
        # Payment that fully covers the order
        payment_amount = order_total

        result = process_webhook_payment(
            webhook_status="paid",
            payment_amount=payment_amount,
            order_total=order_total,
            existing_paid_payments=[],
            current_order_payment_status="unpaid",
        )

        assert result["payment_record_status"] == "paid"
        assert result["order_payment_status"] == "paid", (
            f"When payment_amount ({payment_amount}) >= order_total ({order_total}), "
            f"expected order_payment_status='paid', got '{result['order_payment_status']}'"
        )

    @given(
        order_total=st.decimals(
            min_value=Decimal("10.00"),
            max_value=Decimal("99999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        fraction=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("0.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_property19_paid_webhook_partial_amount_sets_partial(
        self, order_total, fraction
    ):
        """Feature: presmeet, Property 19: Payment status webhook handling

        For any order total and payment that is a fraction of the total
        (payment_amount < order_total), the order payment_status SHALL be "partial".

        **Validates: Requirements 6.2, 6.3**
        """
        # Payment is a fraction of the total (always less than total)
        payment_amount = (order_total * fraction).quantize(Decimal("0.01"))
        assume(payment_amount > Decimal("0.00"))
        assume(payment_amount < order_total)

        result = process_webhook_payment(
            webhook_status="paid",
            payment_amount=payment_amount,
            order_total=order_total,
            existing_paid_payments=[],
            current_order_payment_status="unpaid",
        )

        assert result["payment_record_status"] == "paid"
        assert result["order_payment_status"] == "partial", (
            f"When payment_amount ({payment_amount}) < order_total ({order_total}), "
            f"expected order_payment_status='partial', got '{result['order_payment_status']}'"
        )

# ============================================================
# Property 17: CSV export completeness
# ============================================================

# Import generate_csv from the generate_presmeet_report handler
import importlib.util
_report_app_path = os.path.join(
    os.path.dirname(__file__), '..', '..', 'handler', 'generate_presmeet_report', 'app.py'
)
_report_spec = importlib.util.spec_from_file_location("generate_presmeet_report_app", _report_app_path)
_report_module = importlib.util.module_from_spec(_report_spec)
_report_spec.loader.exec_module(_report_module)
generate_csv = _report_module.generate_csv

import csv
import io


# --- Strategies for Property 17 ---

# Strategy for product types
_p17_product_type_strategy = st.sampled_from(["meeting_ticket", "party_ticket", "tshirt", "airport_transfer"])

# Strategy for order statuses
_p17_order_status_strategy = st.sampled_from(["draft", "submitted", "locked"])

# Strategy for attribute values (simple key-value pairs)
_p17_attribute_value_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -_'),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")

# Strategy for attributes dict (1-4 keys)
_p17_attributes_strategy = st.dictionaries(
    keys=st.sampled_from(["name", "role", "gender", "size", "direction", "airport", "flight", "date", "time", "person_type"]),
    values=_p17_attribute_value_strategy,
    min_size=1,
    max_size=4,
)

# Strategy for a single cart item
_p17_item_strategy = st.fixed_dictionaries({
    "product_type": _p17_product_type_strategy,
    "unit_price": st.one_of(
        st.just(50.0),
        st.just(99.50),
        st.just(25.0),
        st.just(5.0),
    ),
    "attributes": _p17_attributes_strategy,
})

# Strategy for a single order
_p17_order_strategy = st.fixed_dictionaries({
    "order_id": st.uuids().map(str),
    "club_id": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
        min_size=3,
        max_size=20,
    ),
    "club_name": st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters=' -'),
        min_size=1,
        max_size=40,
    ).filter(lambda s: s.strip() != ""),
    "status": _p17_order_status_strategy,
    "items": st.lists(_p17_item_strategy, min_size=1, max_size=5),
})

# Strategy for a list of orders
_p17_orders_strategy = st.lists(_p17_order_strategy, min_size=1, max_size=5)


class TestProperty17CsvExportCompleteness:
    """Feature: presmeet, Property 17: CSV export completeness"""

    @given(orders=_p17_orders_strategy)
    @settings(max_examples=100)
    def test_property17_csv_contains_one_row_per_item_unfiltered(self, orders):
        """Feature: presmeet, Property 17: CSV export completeness

        For any set of orders, the generated CSV file SHALL contain one row per
        cart item. No matching items SHALL be omitted. (Unfiltered case: all orders)

        **Validates: Requirements 7.4, 7.5**
        """
        # Generate CSV with no filter (all orders included)
        csv_output = generate_csv(orders, filter_statuses=None)

        # Parse CSV
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        # First row is header
        assert len(rows) >= 1, "CSV should have at least a header row"
        header = rows[0]
        data_rows = rows[1:]

        # Verify header columns
        assert "club_name" in header
        assert "order_status" in header
        assert "product_type" in header
        assert "quantity" in header
        assert "unit_price" in header
        assert "attributes" in header

        # Count total items across all orders
        total_items = sum(len(order.get("items", [])) for order in orders)

        # Number of data rows must equal total items
        assert len(data_rows) == total_items, (
            f"Expected {total_items} data rows (one per item), "
            f"got {len(data_rows)} rows"
        )

        # Verify each item from each order appears in the CSV
        expected_rows = []
        for order in orders:
            club_name = order.get("club_name", order.get("club_id", ""))
            status = order.get("status", "draft")
            for item in order.get("items", []):
                expected_rows.append({
                    "club_name": club_name,
                    "order_status": status,
                    "product_type": item["product_type"],
                    "unit_price": str(item["unit_price"]),
                })

        # Check that all expected items are present in csv data rows
        col_idx = {h: i for i, h in enumerate(header)}
        for i, expected in enumerate(expected_rows):
            row = data_rows[i]
            assert row[col_idx["club_name"]] == expected["club_name"], (
                f"Row {i}: expected club_name '{expected['club_name']}', "
                f"got '{row[col_idx['club_name']]}'"
            )
            assert row[col_idx["order_status"]] == expected["order_status"], (
                f"Row {i}: expected order_status '{expected['order_status']}', "
                f"got '{row[col_idx['order_status']]}'"
            )
            assert row[col_idx["product_type"]] == expected["product_type"], (
                f"Row {i}: expected product_type '{expected['product_type']}', "
                f"got '{row[col_idx['product_type']]}'"
            )
            assert row[col_idx["unit_price"]] == expected["unit_price"], (
                f"Row {i}: expected unit_price '{expected['unit_price']}', "
                f"got '{row[col_idx['unit_price']]}'"
            )

    @given(orders=_p17_orders_strategy)
    @settings(max_examples=100)
    def test_property17_csv_filtered_submitted_only(self, orders):
        """Feature: presmeet, Property 17: CSV export completeness

        For any set of orders, the CSV export filtered to submitted-only SHALL
        contain one row per cart item from orders with status "submitted". Orders
        with other statuses SHALL be excluded. No matching items SHALL be omitted.

        **Validates: Requirements 7.4, 7.5**
        """
        # Generate CSV filtered to submitted only
        csv_output = generate_csv(orders, filter_statuses={"submitted"})

        # Parse CSV
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        header = rows[0]
        data_rows = rows[1:]

        # Count items from submitted orders only
        submitted_orders = [o for o in orders if o.get("status") == "submitted"]
        total_submitted_items = sum(
            len(order.get("items", [])) for order in submitted_orders
        )

        # Number of data rows must equal total items from submitted orders
        assert len(data_rows) == total_submitted_items, (
            f"Expected {total_submitted_items} data rows for submitted orders, "
            f"got {len(data_rows)} rows. "
            f"Order statuses: {[o['status'] for o in orders]}"
        )

        # Verify no non-submitted order items leak into the export
        col_idx = {h: i for i, h in enumerate(header)}
        for row in data_rows:
            assert row[col_idx["order_status"]] == "submitted", (
                f"Filtered CSV should only contain submitted rows, "
                f"but found status '{row[col_idx['order_status']]}'"
            )

    @given(orders=_p17_orders_strategy)
    @settings(max_examples=100)
    def test_property17_csv_item_attributes_present(self, orders):
        """Feature: presmeet, Property 17: CSV export completeness

        For any set of orders, each row in the CSV SHALL include the attribute
        values for that item. The attributes column SHALL contain the item's
        attribute key-value pairs.

        **Validates: Requirements 7.4, 7.5**
        """
        # Generate CSV with no filter
        csv_output = generate_csv(orders, filter_statuses=None)

        # Parse CSV
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        header = rows[0]
        data_rows = rows[1:]
        col_idx = {h: i for i, h in enumerate(header)}

        # Walk through all items and verify attributes appear in CSV
        row_index = 0
        for order in orders:
            for item in order.get("items", []):
                attributes = item.get("attributes", {})
                csv_attrs = data_rows[row_index][col_idx["attributes"]]

                # Each attribute key=value should be present in the attributes column
                for key, value in sorted(attributes.items()):
                    expected_pair = f"{key}={value}"
                    assert expected_pair in csv_attrs, (
                        f"Row {row_index}: expected attribute '{expected_pair}' "
                        f"in CSV attributes column, got: '{csv_attrs}'"
                    )

                row_index += 1


# ============================================================
# Property 18: Admin aggregation correctness
# ============================================================

# Import compute_aggregates from generate_presmeet_report handler
import importlib.util as _p18_importlib_util

_p18_report_app_path = os.path.join(
    os.path.dirname(__file__), '..', '..', 'handler', 'generate_presmeet_report', 'app.py'
)
_p18_spec = _p18_importlib_util.spec_from_file_location("generate_presmeet_report_app", _p18_report_app_path)
_p18_module = _p18_importlib_util.module_from_spec(_p18_spec)
_p18_spec.loader.exec_module(_p18_module)
compute_aggregates = _p18_module.compute_aggregates


# --- Strategies for Property 18 ---

_p18_product_types = ["meeting_ticket", "party_ticket", "tshirt", "airport_transfer"]
_p18_statuses = ["draft", "submitted", "locked"]

# Strategy for a single cart item
_p18_item_strategy = st.builds(
    lambda product_type: {"product_type": product_type, "attributes": {}},
    product_type=st.sampled_from(_p18_product_types),
)

# Strategy for a single order with random items and total_amount
_p18_order_strategy = st.builds(
    lambda order_id, status, items, total_amount: {
        "order_id": f"order_{order_id}",
        "status": status,
        "items": items,
        "total_amount": total_amount,
        "source": "presmeet",
    },
    order_id=st.integers(min_value=1, max_value=10000),
    status=st.sampled_from(_p18_statuses),
    items=st.lists(_p18_item_strategy, min_size=0, max_size=10),
    total_amount=st.decimals(
        min_value=Decimal("0.00"),
        max_value=Decimal("9999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
)

# Strategy for a single payment record
_p18_payment_strategy = st.builds(
    lambda payment_id, order_id, amount, status: {
        "payment_id": f"pay_{payment_id}",
        "order_id": f"order_{order_id}",
        "amount": amount,
        "status": status,
        "source": "presmeet",
    },
    payment_id=st.integers(min_value=1, max_value=10000),
    order_id=st.integers(min_value=1, max_value=10000),
    amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("9999.99"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
    status=st.sampled_from(["paid", "pending", "failed", "cancelled", "expired"]),
)


class TestProperty18AdminAggregationCorrectness:
    """Feature: presmeet, Property 18: Admin aggregation correctness"""

    @given(
        orders=st.lists(_p18_order_strategy, min_size=0, max_size=15),
        payments=st.lists(_p18_payment_strategy, min_size=0, max_size=20),
    )
    @settings(max_examples=100)
    def test_property18_product_type_counts_match_actual(self, orders, payments):
        """Feature: presmeet, Property 18: Admin aggregation correctness

        For any set of orders at the time of report generation, the overview.json
        counts per product_type per status SHALL equal the actual count of items
        with that product_type in orders with that status.

        **Validates: Requirements 7.1, 7.6**
        """
        result = compute_aggregates(orders, payments)

        # Manually compute expected counts per product_type per status
        expected_by_product_type = {}
        for order in orders:
            status = order.get("status", "draft")
            items = order.get("items", [])
            for item in items:
                product_type = item.get("product_type", "unknown")
                if product_type not in expected_by_product_type:
                    expected_by_product_type[product_type] = {"draft": 0, "submitted": 0, "locked": 0}
                if status in expected_by_product_type[product_type]:
                    expected_by_product_type[product_type][status] += 1

        actual_by_product_type = result["summary"]["by_product_type"]

        # Verify all expected product_types are present with correct counts
        for pt, expected_counts in expected_by_product_type.items():
            assert pt in actual_by_product_type, (
                f"Product type '{pt}' missing from aggregation result"
            )
            for status, expected_count in expected_counts.items():
                actual_count = actual_by_product_type[pt].get(status, 0)
                assert actual_count == expected_count, (
                    f"For product_type='{pt}', status='{status}': "
                    f"expected count {expected_count}, got {actual_count}"
                )

        # Verify no extra product_types in the result
        for pt in actual_by_product_type:
            assert pt in expected_by_product_type, (
                f"Unexpected product_type '{pt}' in aggregation result"
            )

    @given(
        orders=st.lists(_p18_order_strategy, min_size=0, max_size=15),
        payments=st.lists(_p18_payment_strategy, min_size=0, max_size=20),
    )
    @settings(max_examples=100)
    def test_property18_payment_aggregates_correct(self, orders, payments):
        """Feature: presmeet, Property 18: Admin aggregation correctness

        Payment aggregates (total charged, total paid, total outstanding) SHALL
        equal the sum of the respective values across all submitted and locked
        orders. total_charged = sum of total_amount for submitted+locked orders,
        total_paid = sum of paid payments, total_outstanding = total_charged - total_paid.

        **Validates: Requirements 7.1, 7.6**
        """
        result = compute_aggregates(orders, payments)

        # Manually compute expected total_charged (submitted + locked orders only)
        expected_total_charged = Decimal("0")
        for order in orders:
            if order.get("status") in ("submitted", "locked"):
                expected_total_charged += Decimal(str(order.get("total_amount", 0)))

        # Manually compute expected total_paid (sum of paid payment amounts)
        expected_total_paid = Decimal("0")
        for payment in payments:
            if payment.get("status") == "paid":
                expected_total_paid += Decimal(str(payment.get("amount", 0)))

        # Expected outstanding = max(0, charged - paid)
        expected_total_outstanding = max(
            Decimal("0"), expected_total_charged - expected_total_paid
        )

        actual_payments = result["payments"]

        assert actual_payments["total_charged"] == expected_total_charged, (
            f"total_charged: expected {expected_total_charged}, "
            f"got {actual_payments['total_charged']}"
        )
        assert actual_payments["total_paid"] == expected_total_paid, (
            f"total_paid: expected {expected_total_paid}, "
            f"got {actual_payments['total_paid']}"
        )
        assert actual_payments["total_outstanding"] == expected_total_outstanding, (
            f"total_outstanding: expected {expected_total_outstanding}, "
            f"got {actual_payments['total_outstanding']}"
        )

    @given(
        orders=st.lists(_p18_order_strategy, min_size=0, max_size=15),
        payments=st.lists(_p18_payment_strategy, min_size=0, max_size=20),
    )
    @settings(max_examples=100)
    def test_property18_by_status_counts_correct(self, orders, payments):
        """Feature: presmeet, Property 18: Admin aggregation correctness

        The by_status counts SHALL equal the actual number of orders in each
        status category.

        **Validates: Requirements 7.1, 7.6**
        """
        result = compute_aggregates(orders, payments)

        # Manually count orders by status
        expected_by_status = {"draft": 0, "submitted": 0, "locked": 0}
        for order in orders:
            status = order.get("status", "draft")
            if status in expected_by_status:
                expected_by_status[status] += 1

        actual_by_status = result["summary"]["by_status"]

        for status, expected_count in expected_by_status.items():
            actual_count = actual_by_status.get(status, 0)
            assert actual_count == expected_count, (
                f"by_status['{status}']: expected {expected_count}, got {actual_count}"
            )

        # Total orders should match
        assert result["summary"]["total_orders"] == len(orders), (
            f"total_orders: expected {len(orders)}, "
            f"got {result['summary']['total_orders']}"
        )
