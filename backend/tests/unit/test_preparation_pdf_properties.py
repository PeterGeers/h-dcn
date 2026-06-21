"""
Property-Based Tests for Preparation PDF Sorting (Property 23).

Tests preparation PDF sorting logic:
- Property 23: Preparation PDF Sorting

The sorting logic is tested as pure functions. The generate_preparation_pdf
handler (task 7.3) should use these same sort key functions.

File: backend/tests/unit/test_preparation_pdf_properties.py

**Validates: Requirements 15.5**
"""

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st


# =============================================================================
# Pure sorting functions (to be used by generate_preparation_pdf handler)
# =============================================================================

def sort_key_by_order(order: dict) -> tuple:
    """
    Sort key for by-order mode: case-insensitive alphabetical by club name,
    with secondary sort by delegate name.

    Returns a tuple (club_name_lower, delegate_name_lower) for sorting.
    """
    club_name = order.get('club_name', '') or ''
    delegate_name = order.get('delegate_name', '') or ''
    return (club_name.lower(), delegate_name.lower())


def sort_key_by_guest(person: dict) -> tuple:
    """
    Sort key for by-guest mode: case-insensitive alphabetical by last word
    of person name, with secondary sort by first name (remaining words).

    The "last word" is the last space-separated token in the name.
    The "first name" is everything before the last word.

    Returns a tuple (last_word_lower, first_name_lower) for sorting.
    """
    name = person.get('name', '') or ''
    parts = name.split()
    if not parts:
        return ('', '')
    if len(parts) == 1:
        return (parts[0].lower(), '')
    last_word = parts[-1]
    first_name = ' '.join(parts[:-1])
    return (last_word.lower(), first_name.lower())


def sort_orders_by_club(orders: list[dict]) -> list[dict]:
    """Sort orders for by-order mode preparation PDF."""
    return sorted(orders, key=sort_key_by_order)


def sort_persons_by_guest(persons: list[dict]) -> list[dict]:
    """Sort persons for by-guest mode preparation PDF."""
    return sorted(persons, key=sort_key_by_guest)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Club names: mixed case, varying lengths, including unicode
club_name_strategy = st.text(
    alphabet=st.characters(
        categories=('L', 'N', 'P', 'Zs'),
        exclude_characters='\x00\n\r',
    ),
    min_size=1, max_size=60,
).filter(lambda s: len(s.strip()) >= 1)

# Person names with multiple words (to exercise last-word splitting)
first_name_strategy = st.text(
    alphabet=st.characters(categories=('L',)),
    min_size=1, max_size=20,
).filter(lambda s: len(s.strip()) >= 1)

last_name_strategy = st.text(
    alphabet=st.characters(categories=('L',)),
    min_size=1, max_size=20,
).filter(lambda s: len(s.strip()) >= 1)

# Full person name: first + optional middle + last
person_name_strategy = st.one_of(
    # Single word name
    first_name_strategy,
    # Two-word name (first + last)
    st.tuples(first_name_strategy, last_name_strategy).map(
        lambda t: f"{t[0]} {t[1]}"
    ),
    # Three-word name (first + middle + last)
    st.tuples(first_name_strategy, first_name_strategy, last_name_strategy).map(
        lambda t: f"{t[0]} {t[1]} {t[2]}"
    ),
)

# Delegate name strategy (same as person name)
delegate_name_strategy = person_name_strategy

# Order dict for by-order mode
order_strategy = st.fixed_dictionaries({
    'club_name': club_name_strategy,
    'delegate_name': delegate_name_strategy,
})

# Person dict for by-guest mode
person_strategy = st.fixed_dictionaries({
    'name': person_name_strategy,
})


# =============================================================================
# Property 23: Preparation PDF Sorting
# =============================================================================

class TestProperty23PreparationPDFSorting:
    """
    # Feature: closed-community-booking, Property 23: Preparation PDF Sorting

    **Validates: Requirements 15.5**

    For any list of orders/persons, the preparation PDF pages SHALL be sorted:
    in by-order mode, case-insensitive alphabetical by club name with secondary
    sort by delegate name; in by-guest mode, case-insensitive alphabetical by
    last word of person name with secondary sort by first name.
    """

    # -------------------------------------------------------------------------
    # by-order mode: sorted case-insensitive by club name
    # -------------------------------------------------------------------------

    @given(orders=st.lists(order_strategy, min_size=2, max_size=20))
    @settings(max_examples=100, deadline=None)
    def test_by_order_sorted_case_insensitive_by_club_name(self, orders: list[dict]):
        """
        **Validates: Requirements 15.5**

        In by-order mode, the result SHALL be sorted case-insensitive
        alphabetically by club name (primary key).
        """
        sorted_orders = sort_orders_by_club(orders)

        # Verify: for each consecutive pair, club_name.lower() is non-decreasing
        for i in range(len(sorted_orders) - 1):
            current_key = sort_key_by_order(sorted_orders[i])
            next_key = sort_key_by_order(sorted_orders[i + 1])
            assert current_key <= next_key, (
                f"Orders not sorted correctly at index {i}: "
                f"{current_key} should be <= {next_key}"
            )

    @given(orders=st.lists(order_strategy, min_size=2, max_size=20))
    @settings(max_examples=100, deadline=None)
    def test_by_order_secondary_sort_by_delegate_name(self, orders: list[dict]):
        """
        **Validates: Requirements 15.5**

        In by-order mode, when club names are equal (case-insensitive),
        orders SHALL be sorted by delegate name (case-insensitive).
        """
        sorted_orders = sort_orders_by_club(orders)

        # Check that within groups of same club_name, delegate_name is sorted
        for i in range(len(sorted_orders) - 1):
            current = sorted_orders[i]
            next_item = sorted_orders[i + 1]

            current_club = (current.get('club_name', '') or '').lower()
            next_club = (next_item.get('club_name', '') or '').lower()

            if current_club == next_club:
                current_delegate = (current.get('delegate_name', '') or '').lower()
                next_delegate = (next_item.get('delegate_name', '') or '').lower()
                assert current_delegate <= next_delegate, (
                    f"Within same club '{current_club}', delegate names not sorted: "
                    f"'{current_delegate}' should be <= '{next_delegate}'"
                )

    @given(orders=st.lists(order_strategy, min_size=0, max_size=20))
    @settings(max_examples=50, deadline=None)
    def test_by_order_preserves_all_elements(self, orders: list[dict]):
        """
        **Validates: Requirements 15.5**

        Sorting SHALL not add, remove, or modify any orders — only reorder.
        """
        sorted_orders = sort_orders_by_club(orders)
        assert len(sorted_orders) == len(orders)
        # All original orders are present (by value)
        for order in orders:
            assert order in sorted_orders

    @given(
        club_name=st.text(
            alphabet=st.characters(categories=('L',), max_codepoint=127),
            min_size=1, max_size=30,
        ),
        delegate_name=st.text(
            alphabet=st.characters(categories=('L',), max_codepoint=127),
            min_size=1, max_size=20,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_by_order_case_insensitivity(self, club_name: str, delegate_name: str):
        """
        **Validates: Requirements 15.5**

        Sorting SHALL be case-insensitive: 'abc' and 'ABC' and 'Abc' are
        treated as equal for sorting purposes.
        """
        orders = [
            {'club_name': club_name.upper(), 'delegate_name': delegate_name},
            {'club_name': club_name.lower(), 'delegate_name': delegate_name},
            {'club_name': club_name.title(), 'delegate_name': delegate_name},
        ]
        sorted_orders = sort_orders_by_club(orders)

        # All three variants should be grouped together (same sort key)
        keys = [sort_key_by_order(o) for o in sorted_orders]
        # All keys should be equal since club_name differs only in case
        assert keys[0] == keys[1] == keys[2], (
            f"Case variants of '{club_name}' should produce equal sort keys, "
            f"got: {keys}"
        )

    # -------------------------------------------------------------------------
    # by-guest mode: sorted case-insensitive by last word of name
    # -------------------------------------------------------------------------

    @given(persons=st.lists(person_strategy, min_size=2, max_size=20))
    @settings(max_examples=100, deadline=None)
    def test_by_guest_sorted_by_last_word_of_name(self, persons: list[dict]):
        """
        **Validates: Requirements 15.5**

        In by-guest mode, the result SHALL be sorted case-insensitive
        alphabetically by the last word of the person name (primary key).
        """
        sorted_persons = sort_persons_by_guest(persons)

        # Verify: for each consecutive pair, sort key is non-decreasing
        for i in range(len(sorted_persons) - 1):
            current_key = sort_key_by_guest(sorted_persons[i])
            next_key = sort_key_by_guest(sorted_persons[i + 1])
            assert current_key <= next_key, (
                f"Persons not sorted correctly at index {i}: "
                f"{current_key} should be <= {next_key}"
            )

    @given(persons=st.lists(person_strategy, min_size=2, max_size=20))
    @settings(max_examples=100, deadline=None)
    def test_by_guest_secondary_sort_by_first_name(self, persons: list[dict]):
        """
        **Validates: Requirements 15.5**

        In by-guest mode, when last words are equal (case-insensitive),
        persons SHALL be sorted by first name (remaining words before
        the last word, case-insensitive).
        """
        sorted_persons = sort_persons_by_guest(persons)

        for i in range(len(sorted_persons) - 1):
            current_key = sort_key_by_guest(sorted_persons[i])
            next_key = sort_key_by_guest(sorted_persons[i + 1])

            # Same last word => check secondary (first name) sort
            if current_key[0] == next_key[0]:
                assert current_key[1] <= next_key[1], (
                    f"Within same last word '{current_key[0]}', first names not sorted: "
                    f"'{current_key[1]}' should be <= '{next_key[1]}'"
                )

    @given(persons=st.lists(person_strategy, min_size=0, max_size=20))
    @settings(max_examples=50, deadline=None)
    def test_by_guest_preserves_all_elements(self, persons: list[dict]):
        """
        **Validates: Requirements 15.5**

        Sorting SHALL not add, remove, or modify any persons — only reorder.
        """
        sorted_persons = sort_persons_by_guest(persons)
        assert len(sorted_persons) == len(persons)
        for person in persons:
            assert person in sorted_persons

    @given(name=person_name_strategy)
    @settings(max_examples=50, deadline=None)
    def test_by_guest_last_word_extraction(self, name: str):
        """
        **Validates: Requirements 15.5**

        The last word SHALL be the last space-separated token in the name.
        For single-word names, the last word IS the name.
        """
        person = {'name': name}
        key = sort_key_by_guest(person)

        parts = name.split()
        expected_last = parts[-1].lower() if parts else ''
        expected_first = ' '.join(parts[:-1]).lower() if len(parts) > 1 else ''

        assert key[0] == expected_last, (
            f"For name '{name}', expected last word '{expected_last}', got '{key[0]}'"
        )
        assert key[1] == expected_first, (
            f"For name '{name}', expected first name '{expected_first}', got '{key[1]}'"
        )

    @given(
        last_name=st.text(
            alphabet=st.characters(categories=('L',), max_codepoint=127),
            min_size=1, max_size=20,
        ),
        first_name=st.text(
            alphabet=st.characters(categories=('L',), max_codepoint=127),
            min_size=1, max_size=20,
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_by_guest_case_insensitivity(self, last_name: str, first_name: str):
        """
        **Validates: Requirements 15.5**

        Sorting SHALL be case-insensitive: 'Vries' and 'VRIES' and 'vries'
        are treated as equal for sorting purposes.
        """
        persons = [
            {'name': f"{first_name} {last_name.upper()}"},
            {'name': f"{first_name} {last_name.lower()}"},
            {'name': f"{first_name} {last_name.title()}"},
        ]
        sorted_persons = sort_persons_by_guest(persons)

        # All three variants should have equal sort keys
        keys = [sort_key_by_guest(p) for p in sorted_persons]
        assert keys[0] == keys[1] == keys[2], (
            f"Case variants of last name '{last_name}' should produce "
            f"equal sort keys, got: {keys}"
        )

    # -------------------------------------------------------------------------
    # Edge cases
    # -------------------------------------------------------------------------

    def test_by_order_empty_list(self):
        """
        **Validates: Requirements 15.5**

        Sorting an empty list SHALL return an empty list.
        """
        assert sort_orders_by_club([]) == []

    def test_by_guest_empty_list(self):
        """
        **Validates: Requirements 15.5**

        Sorting an empty list SHALL return an empty list.
        """
        assert sort_persons_by_guest([]) == []

    def test_by_order_known_example(self):
        """
        **Validates: Requirements 15.5**

        Known example: 'Zebra Club', 'alfa Club', 'BETA Club' should sort
        as alfa, BETA, Zebra (case-insensitive).
        """
        orders = [
            {'club_name': 'Zebra Club', 'delegate_name': 'Alice'},
            {'club_name': 'alfa Club', 'delegate_name': 'Bob'},
            {'club_name': 'BETA Club', 'delegate_name': 'Charlie'},
        ]
        result = sort_orders_by_club(orders)
        assert result[0]['club_name'] == 'alfa Club'
        assert result[1]['club_name'] == 'BETA Club'
        assert result[2]['club_name'] == 'Zebra Club'

    def test_by_guest_known_example(self):
        """
        **Validates: Requirements 15.5**

        Known example: 'Jan de Vries', 'Anna Bakker', 'Pieter de Vries'
        should sort by last word: Bakker, de Vries (Jan), de Vries (Pieter).
        """
        persons = [
            {'name': 'Jan de Vries'},
            {'name': 'Anna Bakker'},
            {'name': 'Pieter de Vries'},
        ]
        result = sort_persons_by_guest(persons)
        assert result[0]['name'] == 'Anna Bakker'
        # 'Jan de Vries' and 'Pieter de Vries' both have last word 'Vries'
        # Secondary sort by first name: 'Jan de' < 'Pieter de'
        assert result[1]['name'] == 'Jan de Vries'
        assert result[2]['name'] == 'Pieter de Vries'

    def test_by_order_secondary_sort_known_example(self):
        """
        **Validates: Requirements 15.5**

        When club names are equal, secondary sort by delegate name.
        """
        orders = [
            {'club_name': 'Amsterdam', 'delegate_name': 'Zara'},
            {'club_name': 'Amsterdam', 'delegate_name': 'Alice'},
            {'club_name': 'Amsterdam', 'delegate_name': 'Bob'},
        ]
        result = sort_orders_by_club(orders)
        assert result[0]['delegate_name'] == 'Alice'
        assert result[1]['delegate_name'] == 'Bob'
        assert result[2]['delegate_name'] == 'Zara'
