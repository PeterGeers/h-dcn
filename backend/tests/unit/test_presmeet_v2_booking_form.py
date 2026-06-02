"""
Property-Based Tests for PresMeet v2 Booking Form Mapping

Tests the form-to-cart-item mapping functions in save_presmeet_booking using Hypothesis
to verify correctness across arbitrary delegate/guest/transfer form inputs.

This file covers:
- Property 14: Booking form to cart item mapping

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
"""

import os
import sys
from decimal import Decimal

import pytest
from hypothesis import given, settings, note, assume
from hypothesis import strategies as st

# Ensure the auth layer path takes priority
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
)


# --- Strategies ---

# Strategy for person names (non-empty text)
name_strategy = st.text(
    min_size=1, max_size=50,
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))
)

# Strategy for role strings
role_strategy = st.text(
    min_size=1, max_size=30,
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))
)

# Strategy for t-shirt gender
gender_strategy = st.sampled_from(["male", "female", "unisex"])

# Strategy for t-shirt size
size_strategy = st.sampled_from(["XS", "S", "M", "L", "XL", "XXL", "3XL"])

# Strategy for t-shirt data (dict with gender and size)
tshirt_strategy = st.fixed_dictionaries({
    "gender": gender_strategy,
    "size": size_strategy,
})

# Strategy for a delegate form entry
delegate_strategy = st.fixed_dictionaries({
    "name": name_strategy,
    "role": role_strategy,
    "party": st.booleans(),
    "tshirt": st.one_of(st.none(), tshirt_strategy),
})

# Strategy for a guest form entry
guest_strategy = st.fixed_dictionaries({
    "name": name_strategy,
    "tshirt": st.one_of(st.none(), tshirt_strategy),
})

# Strategy for transfer direction
direction_strategy = st.sampled_from(["arrival", "departure"])

# Strategy for airport names
airport_strategy = st.sampled_from(["AMS", "RTM", "EIN", "BRU", "DUS"])

# Strategy for flight numbers
flight_strategy = st.from_regex(r"[A-Z]{2}[0-9]{3,4}", fullmatch=True)

# Strategy for date strings (YYYY-MM-DD)
date_strategy = st.dates().map(lambda d: d.isoformat())

# Strategy for time strings (HH:MM)
time_strategy = st.times().map(lambda t: t.strftime("%H:%M"))

# Strategy for number of persons
persons_strategy = st.integers(min_value=1, max_value=10)

# Strategy for a transfer form entry
transfer_strategy = st.fixed_dictionaries({
    "direction": direction_strategy,
    "airport": airport_strategy,
    "flight": flight_strategy,
    "date": date_strategy,
    "time": time_strategy,
    "persons": persons_strategy,
})

# Lists of form entries
delegates_list_strategy = st.lists(delegate_strategy, min_size=1, max_size=5)
guests_list_strategy = st.lists(guest_strategy, min_size=1, max_size=5)
transfers_list_strategy = st.lists(transfer_strategy, min_size=1, max_size=5)


# =============================================================================
# Property 14: Booking form to cart item mapping
# =============================================================================

class TestProperty14DelegateMapping:
    """
    **Validates: Requirements 7.1, 7.2**

    Property 14a: Each delegate produces exactly 1 meeting_ticket.
    Each delegate with party=True additionally produces 1 party_ticket with person_type="delegate".
    Each delegate with tshirt produces 1 tshirt item with correct gender/size.
    All items have unique item_ids and correct product_types.
    """

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_each_delegate_produces_exactly_one_meeting_ticket(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1**

        For any list of delegates, the number of meeting_ticket items must equal
        the number of delegates.
        """
        items = map_delegates_to_items(delegates)
        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]

        note(f"Delegates: {len(delegates)}, Meeting tickets: {len(meeting_tickets)}")
        assert len(meeting_tickets) == len(delegates)

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_meeting_ticket_has_correct_attributes(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1**

        Each meeting_ticket must contain the delegate's name and role as attributes.
        """
        items = map_delegates_to_items(delegates)
        meeting_tickets = [i for i in items if i["product_type"] == "meeting_ticket"]

        for delegate, ticket in zip(delegates, meeting_tickets):
            assert ticket["attributes"]["name"] == delegate["name"]
            assert ticket["attributes"]["role"] == delegate["role"]

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_party_delegate_produces_party_ticket(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.2**

        Each delegate with party=True produces exactly 1 party_ticket with
        person_type="delegate" and the delegate's name.
        """
        items = map_delegates_to_items(delegates)
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]
        party_delegates = [d for d in delegates if d.get("party", False)]

        note(f"Party delegates: {len(party_delegates)}, Party tickets: {len(party_tickets)}")
        assert len(party_tickets) == len(party_delegates)

        for ticket in party_tickets:
            assert ticket["attributes"]["person_type"] == "delegate"
            assert "name" in ticket["attributes"]

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_delegate_tshirt_produces_tshirt_item(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1**

        Each delegate with a tshirt dict produces exactly 1 tshirt item with
        the correct name, gender, and size attributes.
        """
        items = map_delegates_to_items(delegates)
        tshirt_items = [i for i in items if i["product_type"] == "tshirt"]
        delegates_with_tshirt = [d for d in delegates if d.get("tshirt") and isinstance(d["tshirt"], dict)]

        note(f"Delegates with tshirt: {len(delegates_with_tshirt)}, Tshirt items: {len(tshirt_items)}")
        assert len(tshirt_items) == len(delegates_with_tshirt)

        for delegate, tshirt_item in zip(delegates_with_tshirt, tshirt_items):
            assert tshirt_item["attributes"]["name"] == delegate["name"]
            assert tshirt_item["attributes"]["gender"] == delegate["tshirt"]["gender"]
            assert tshirt_item["attributes"]["size"] == delegate["tshirt"]["size"]

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_all_delegate_items_have_unique_ids(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2**

        All items produced from delegates must have unique item_id values.
        """
        items = map_delegates_to_items(delegates)
        item_ids = [i["item_id"] for i in items]
        assert len(item_ids) == len(set(item_ids)), "Duplicate item_ids found"

    @given(delegates=delegates_list_strategy)
    @settings(max_examples=100)
    def test_delegate_item_count_matches_expected(self, delegates):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2**

        Total items = delegates (meeting_ticket) + party delegates (party_ticket)
        + delegates with tshirt (tshirt).
        """
        items = map_delegates_to_items(delegates)
        expected_count = len(delegates)  # meeting_tickets
        expected_count += sum(1 for d in delegates if d.get("party", False))  # party_tickets
        expected_count += sum(1 for d in delegates if d.get("tshirt") and isinstance(d["tshirt"], dict))  # tshirts

        assert len(items) == expected_count


class TestProperty14GuestMapping:
    """
    **Validates: Requirements 7.3**

    Property 14b: Each guest produces exactly 1 party_ticket with person_type="guest".
    Each guest with tshirt produces 1 tshirt item.
    All items have unique item_ids.
    """

    @given(guests=guests_list_strategy)
    @settings(max_examples=100)
    def test_each_guest_produces_exactly_one_party_ticket(self, guests):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.3**

        For any list of guests, the number of party_ticket items must equal
        the number of guests.
        """
        items = map_guests_to_items(guests)
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]

        note(f"Guests: {len(guests)}, Party tickets: {len(party_tickets)}")
        assert len(party_tickets) == len(guests)

    @given(guests=guests_list_strategy)
    @settings(max_examples=100)
    def test_guest_party_ticket_has_correct_attributes(self, guests):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.3**

        Each guest's party_ticket must have person_type="guest" and the guest's name.
        """
        items = map_guests_to_items(guests)
        party_tickets = [i for i in items if i["product_type"] == "party_ticket"]

        for guest, ticket in zip(guests, party_tickets):
            assert ticket["attributes"]["person_type"] == "guest"
            assert ticket["attributes"]["name"] == guest["name"]

    @given(guests=guests_list_strategy)
    @settings(max_examples=100)
    def test_guest_tshirt_produces_tshirt_item(self, guests):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.3**

        Each guest with a tshirt dict produces exactly 1 tshirt item with
        the correct name, gender, and size attributes.
        """
        items = map_guests_to_items(guests)
        tshirt_items = [i for i in items if i["product_type"] == "tshirt"]
        guests_with_tshirt = [g for g in guests if g.get("tshirt") and isinstance(g["tshirt"], dict)]

        assert len(tshirt_items) == len(guests_with_tshirt)

        for guest, tshirt_item in zip(guests_with_tshirt, tshirt_items):
            assert tshirt_item["attributes"]["name"] == guest["name"]
            assert tshirt_item["attributes"]["gender"] == guest["tshirt"]["gender"]
            assert tshirt_item["attributes"]["size"] == guest["tshirt"]["size"]

    @given(guests=guests_list_strategy)
    @settings(max_examples=100)
    def test_all_guest_items_have_unique_ids(self, guests):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.3**

        All items produced from guests must have unique item_id values.
        """
        items = map_guests_to_items(guests)
        item_ids = [i["item_id"] for i in items]
        assert len(item_ids) == len(set(item_ids)), "Duplicate item_ids found"


class TestProperty14TransferMapping:
    """
    **Validates: Requirements 7.4, 7.5**

    Property 14c: Each transfer produces exactly 1 airport_transfer item with correct
    direction, airport, flight, date, time, and persons attributes.
    All items have unique item_ids.
    """

    @given(transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_each_transfer_produces_exactly_one_airport_transfer(self, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.4, 7.5**

        For any list of transfers, the number of airport_transfer items must equal
        the number of transfers.
        """
        items = map_transfers_to_items(transfers)

        note(f"Transfers: {len(transfers)}, Items: {len(items)}")
        assert len(items) == len(transfers)
        assert all(i["product_type"] == "airport_transfer" for i in items)

    @given(transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_transfer_has_correct_attributes(self, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.5**

        Each airport_transfer item must contain the correct direction, airport,
        flight number, date, time, and number of persons.
        """
        items = map_transfers_to_items(transfers)

        for transfer, item in zip(transfers, items):
            attrs = item["attributes"]
            assert attrs["direction"] == transfer["direction"]
            assert attrs["airport"] == transfer["airport"]
            assert attrs["flight"] == transfer["flight"]
            assert attrs["date"] == transfer["date"]
            assert attrs["time"] == transfer["time"]
            assert attrs["persons"] == transfer["persons"]

    @given(transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_all_transfer_items_have_unique_ids(self, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.4, 7.5**

        All items produced from transfers must have unique item_id values.
        """
        items = map_transfers_to_items(transfers)
        item_ids = [i["item_id"] for i in items]
        assert len(item_ids) == len(set(item_ids)), "Duplicate item_ids found"


class TestProperty14AllProductTypes:
    """
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

    Property 14d: Combined property — verifying that all mapping functions produce
    items with valid product_types and populated attributes.
    """

    @given(delegates=delegates_list_strategy, guests=guests_list_strategy, transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_all_items_have_valid_product_types(self, delegates, guests, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

        All produced items must have a product_type from the known set.
        """
        valid_types = {"meeting_ticket", "party_ticket", "tshirt", "airport_transfer"}

        all_items = (
            map_delegates_to_items(delegates)
            + map_guests_to_items(guests)
            + map_transfers_to_items(transfers)
        )

        for item in all_items:
            assert item["product_type"] in valid_types, f"Invalid product_type: {item['product_type']}"

    @given(delegates=delegates_list_strategy, guests=guests_list_strategy, transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_all_items_have_populated_attributes(self, delegates, guests, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

        All produced items must have a non-empty attributes dict.
        """
        all_items = (
            map_delegates_to_items(delegates)
            + map_guests_to_items(guests)
            + map_transfers_to_items(transfers)
        )

        for item in all_items:
            assert isinstance(item["attributes"], dict)
            assert len(item["attributes"]) > 0, f"Empty attributes for {item['product_type']}"

    @given(delegates=delegates_list_strategy, guests=guests_list_strategy, transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_all_items_have_unique_ids_across_functions(self, delegates, guests, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

        All items across all mapping functions must have globally unique item_ids.
        """
        all_items = (
            map_delegates_to_items(delegates)
            + map_guests_to_items(guests)
            + map_transfers_to_items(transfers)
        )

        item_ids = [i["item_id"] for i in all_items]
        assert len(item_ids) == len(set(item_ids)), "Duplicate item_ids across mapping functions"

    @given(delegates=delegates_list_strategy, guests=guests_list_strategy, transfers=transfers_list_strategy)
    @settings(max_examples=100)
    def test_all_items_have_item_id_and_unit_price(self, delegates, guests, transfers):
        """Feature: presmeet-v2, Property 14: Booking form to cart item mapping

        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

        All produced items must have an item_id (non-empty string) and a unit_price (Decimal).
        """
        all_items = (
            map_delegates_to_items(delegates)
            + map_guests_to_items(guests)
            + map_transfers_to_items(transfers)
        )

        for item in all_items:
            assert isinstance(item["item_id"], str) and len(item["item_id"]) > 0
            assert isinstance(item["unit_price"], Decimal)
            assert item["unit_price"] > 0


# =============================================================================
# Property 15: Cascade delete on delegate removal
# =============================================================================


# --- Strategies for Property 15 ---

# Strategy for delegate names (non-empty, printable, unique-friendly)
_p15_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), whitelist_characters=' -'),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != "")

# Strategy for a role
_p15_role_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=30,
)

# Strategy for a single delegate dict (Property 15)
_p15_delegate_strategy = st.builds(
    lambda name, role, party, tshirt: {
        "name": name,
        "role": role,
        "party": party,
        **({"tshirt": tshirt} if tshirt else {}),
    },
    name=_p15_name_strategy,
    role=_p15_role_strategy,
    party=st.booleans(),
    tshirt=st.one_of(
        st.none(),
        st.fixed_dictionaries({
            "gender": st.sampled_from(["male", "female"]),
            "size": st.sampled_from(["S", "M", "L", "XL", "XXL", "3XL", "4XL"]),
        }),
    ),
)


def _item_signature(item):
    """
    Create a comparable signature for an item, ignoring item_id (UUID).
    Uses (product_type, frozenset of attributes) as identity.
    """
    return (
        item["product_type"],
        frozenset(item.get("attributes", {}).items()),
    )


def _items_to_signature_multiset(items):
    """
    Convert a list of items to a multiset (dict of signature -> count).
    This allows set-difference comparison ignoring item_ids.
    """
    multiset = {}
    for item in items:
        sig = _item_signature(item)
        multiset[sig] = multiset.get(sig, 0) + 1
    return multiset


def _multiset_subtract(a, b):
    """Subtract multiset b from multiset a (non-negative results only)."""
    result = dict(a)
    for key, count in b.items():
        if key in result:
            result[key] = max(0, result[key] - count)
            if result[key] == 0:
                del result[key]
    return result


class TestProperty15CascadeDeleteOnDelegateRemoval:
    """Feature: presmeet-v2, Property 15: Cascade delete on delegate removal

    **Validates: Requirements 7.8**
    """

    @given(
        delegates=st.lists(_p15_delegate_strategy, min_size=2, max_size=6),
        remove_index=st.data(),
    )
    @settings(max_examples=100)
    def test_set_difference_invariant(self, delegates, remove_index):
        """Feature: presmeet-v2, Property 15: Cascade delete on delegate removal

        When a delegate is removed, the resulting item set equals the items
        generated from the remaining delegates. Formally:
        map_delegates_to_items(all) - map_delegates_to_items([removed]) == map_delegates_to_items(remaining)

        Comparison is by product_type and attributes, not by item_id.

        **Validates: Requirements 7.8**
        """
        # Ensure unique names so removal is unambiguous
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

        # Compute item sets
        all_items = map_delegates_to_items(unique_delegates)
        removed_items = map_delegates_to_items([removed_delegate])
        remaining_delegates = [d for d in unique_delegates if d["name"] != removed_delegate["name"]]
        remaining_items = map_delegates_to_items(remaining_delegates)

        # Convert to multisets for comparison (ignoring item_ids)
        all_multiset = _items_to_signature_multiset(all_items)
        removed_multiset = _items_to_signature_multiset(removed_items)
        remaining_multiset = _items_to_signature_multiset(remaining_items)

        # The invariant: all - removed == remaining
        computed_remaining = _multiset_subtract(all_multiset, removed_multiset)
        assert computed_remaining == remaining_multiset, (
            f"Set difference invariant violated.\n"
            f"all - removed = {computed_remaining}\n"
            f"remaining     = {remaining_multiset}"
        )

    @given(
        delegates=st.lists(_p15_delegate_strategy, min_size=2, max_size=6),
        remove_index=st.data(),
    )
    @settings(max_examples=100)
    def test_other_delegates_items_unchanged(self, delegates, remove_index):
        """Feature: presmeet-v2, Property 15: Cascade delete on delegate removal

        Items from other delegates (different names) are unchanged after removal.
        For each non-removed delegate, their items in the remaining set are identical
        to their items in the full set.

        **Validates: Requirements 7.8**
        """
        # Ensure unique names
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

        # Compute item sets
        all_items = map_delegates_to_items(unique_delegates)
        remaining_delegates = [d for d in unique_delegates if d["name"] != removed_name]
        remaining_items = map_delegates_to_items(remaining_delegates)

        # For each non-removed delegate, check items match
        for other_delegate in remaining_delegates:
            other_name = other_delegate["name"]

            # Items for this delegate in the full set
            items_in_all = [
                _item_signature(i) for i in all_items
                if i.get("attributes", {}).get("name") == other_name
            ]
            # Items for this delegate in the remaining set
            items_in_remaining = [
                _item_signature(i) for i in remaining_items
                if i.get("attributes", {}).get("name") == other_name
            ]

            assert sorted(items_in_all) == sorted(items_in_remaining), (
                f"Items for delegate '{other_name}' changed after removing '{removed_name}'.\n"
                f"Before: {sorted(items_in_all)}\n"
                f"After:  {sorted(items_in_remaining)}"
            )

    @given(
        delegates=st.lists(_p15_delegate_strategy, min_size=2, max_size=6),
        remove_index=st.data(),
    )
    @settings(max_examples=100)
    def test_removal_removes_meeting_party_tshirt(self, delegates, remove_index):
        """Feature: presmeet-v2, Property 15: Cascade delete on delegate removal

        Removing a delegate removes meeting_ticket + party_ticket + tshirt
        associated with that delegate's name. The number of removed items equals
        what map_delegates_to_items produces for that single delegate.

        **Validates: Requirements 7.8**
        """
        # Ensure unique names
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

        # Compute items for the removed delegate only
        removed_items = map_delegates_to_items([removed_delegate])

        # Every removed item must be meeting_ticket, party_ticket, or tshirt
        for item in removed_items:
            assert item["product_type"] in ("meeting_ticket", "party_ticket", "tshirt"), (
                f"Unexpected product_type '{item['product_type']}' for delegate item"
            )
            assert item["attributes"]["name"] == removed_name, (
                f"Item name attribute '{item['attributes']['name']}' doesn't match "
                f"removed delegate name '{removed_name}'"
            )

        # After removal, no items with the removed name should exist
        remaining_delegates = [d for d in unique_delegates if d["name"] != removed_name]
        remaining_items = map_delegates_to_items(remaining_delegates)

        leftover = [
            i for i in remaining_items
            if i.get("attributes", {}).get("name") == removed_name
        ]
        assert len(leftover) == 0, (
            f"After removing delegate '{removed_name}', found {len(leftover)} "
            f"leftover items with that name"
        )
