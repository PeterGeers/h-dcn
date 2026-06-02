"""
Property-Based Tests for PresMeet v2 CSV Export Completeness

Tests that the CSV export from generate_csv contains exactly one row per
cart item across matching orders, with correct filtering by order status.

This file covers:
- Property 16: CSV export completeness

**Validates: Requirements 9.6**
"""

import sys
import os
import csv
import io
from decimal import Decimal

import pytest
from hypothesis import given, settings, note, assume
from hypothesis import strategies as st

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_presmeet_report')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

from app import generate_csv


# --- Strategies ---

# Strategy for club names
_club_name_strategy = st.text(
    min_size=1, max_size=40,
    alphabet=st.characters(whitelist_categories=('L', 'Nd', 'Zs'))
)

# Strategy for product types used in PresMeet
_product_type_strategy = st.sampled_from([
    'meeting_ticket', 'party_ticket', 'tshirt', 'airport_transfer'
])

# Strategy for order statuses
_status_strategy = st.sampled_from(['draft', 'submitted', 'locked'])

# Strategy for attribute key-value pairs (simple string values, no commas/semicolons to avoid CSV issues)
_attr_key_strategy = st.text(
    min_size=1, max_size=15,
    alphabet=st.characters(whitelist_categories=('L',))
)
_attr_value_strategy = st.text(
    min_size=1, max_size=20,
    alphabet=st.characters(whitelist_categories=('L', 'Nd', 'Zs'))
)

_attributes_strategy = st.dictionaries(
    keys=_attr_key_strategy,
    values=_attr_value_strategy,
    min_size=0,
    max_size=4,
)

# Strategy for a single cart item within an order
_cart_item_strategy = st.fixed_dictionaries({
    'item_id': st.uuids().map(str),
    'product_type': _product_type_strategy,
    'unit_price': st.decimals(min_value=Decimal('0.01'), max_value=Decimal('500.00'), places=2, allow_nan=False, allow_infinity=False),
    'attributes': _attributes_strategy,
})

# Strategy for a complete order record (as returned from DynamoDB)
_order_strategy = st.fixed_dictionaries({
    'order_id': st.uuids().map(str),
    'source': st.just('presmeet'),
    'tenant': st.just('presmeet'),
    'club_id': st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=('L', 'Nd'))),
    'club_name': _club_name_strategy,
    'status': _status_strategy,
    'items': st.lists(_cart_item_strategy, min_size=1, max_size=8),
    'total_amount': st.decimals(min_value=Decimal('0'), max_value=Decimal('10000'), places=2, allow_nan=False, allow_infinity=False),
    'created_at': st.just('2025-01-15T10:00:00+00:00'),
    'updated_at': st.just('2025-01-15T12:00:00+00:00'),
})

# Strategy for a list of orders
_orders_list_strategy = st.lists(_order_strategy, min_size=0, max_size=10)


def _parse_csv_rows(csv_string):
    """Parse CSV string and return list of data rows (excluding header)."""
    reader = csv.reader(io.StringIO(csv_string))
    rows = list(reader)
    if not rows:
        return [], None
    header = rows[0]
    data_rows = rows[1:]
    return data_rows, header


# =============================================================================
# Property 16: CSV export completeness
# =============================================================================

class TestProperty16CsvExportCompleteness:
    """
    **Validates: Requirements 9.6**

    Property 16: CSV export completeness

    The CSV export produced by generate_csv must contain exactly one row per
    cart item across all orders that pass the status filter.
    - For filter_statuses=None (export_all), ALL items from ALL orders appear
    - For filter_statuses={'submitted'}, only items from submitted orders appear
    - Each CSV row corresponds to exactly one cart item
    """

    # -------------------------------------------------------------------------
    # Sub-property 16a: CSV data row count equals total items across all
    # matching orders when filter_statuses=None (export all)
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=300)
    def test_csv_all_row_count_equals_total_items(self, orders):
        """
        When filter_statuses=None (export_all), the number of CSV data rows
        must equal the total number of items across ALL orders.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses=None)
        data_rows, header = _parse_csv_rows(csv_output)

        # Total items across all orders
        expected_count = sum(len(order.get('items', [])) for order in orders)

        note(f"Orders: {len(orders)}, Total items: {expected_count}, CSV rows: {len(data_rows)}")

        assert len(data_rows) == expected_count, (
            f"Expected {expected_count} CSV data rows (one per item), "
            f"got {len(data_rows)}. Orders: {len(orders)}"
        )

    # -------------------------------------------------------------------------
    # Sub-property 16b: CSV data row count equals total items from submitted
    # orders only when filter_statuses={'submitted'}
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=300)
    def test_csv_submitted_row_count_equals_submitted_items(self, orders):
        """
        When filter_statuses={'submitted'}, the number of CSV data rows must
        equal the total number of items across orders with status='submitted'.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses={'submitted'})
        data_rows, header = _parse_csv_rows(csv_output)

        # Count items only in submitted orders
        expected_count = sum(
            len(order.get('items', []))
            for order in orders
            if order.get('status') == 'submitted'
        )

        note(f"Orders: {len(orders)}, Submitted items: {expected_count}, CSV rows: {len(data_rows)}")

        assert len(data_rows) == expected_count, (
            f"Expected {expected_count} CSV rows for submitted orders, "
            f"got {len(data_rows)}"
        )

    # -------------------------------------------------------------------------
    # Sub-property 16c: For filter_statuses=None, ALL items from ALL orders
    # appear in the CSV (completeness check via product_type and club_name)
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=300)
    def test_csv_all_contains_every_item(self, orders):
        """
        When filter_statuses=None, every item from every order must have a
        corresponding row in the CSV with matching club_name and product_type.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses=None)
        data_rows, header = _parse_csv_rows(csv_output)

        # Build expected list of (club_name, product_type) tuples
        expected_items = []
        for order in orders:
            club_name = order.get('club_name', order.get('club_id', ''))
            for item in order.get('items', []):
                expected_items.append((club_name, item.get('product_type', '')))

        # Build actual list from CSV rows
        # CSV columns: club_name, order_status, product_type, quantity, unit_price, attributes
        actual_items = [(row[0], row[2]) for row in data_rows]

        # Sort both for comparison (order may differ)
        assert sorted(actual_items) == sorted(expected_items), (
            f"CSV items don't match expected items. "
            f"Expected {len(expected_items)} items, got {len(actual_items)} in CSV"
        )

    # -------------------------------------------------------------------------
    # Sub-property 16d: For filter_statuses={'submitted'}, ONLY items from
    # submitted orders appear in the CSV
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=300)
    def test_csv_submitted_only_contains_submitted_items(self, orders):
        """
        When filter_statuses={'submitted'}, only items from submitted orders
        appear. Draft and locked order items must NOT appear.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses={'submitted'})
        data_rows, header = _parse_csv_rows(csv_output)

        # All rows should have order_status == 'submitted'
        for i, row in enumerate(data_rows):
            assert row[1] == 'submitted', (
                f"Row {i} has order_status='{row[1]}' but filter was {{'submitted'}}. "
                f"Only submitted order items should appear."
            )

    # -------------------------------------------------------------------------
    # Sub-property 16e: Each CSV row has exactly one item (quantity=1)
    # confirming one-row-per-cart-item mapping
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=300)
    def test_csv_each_row_has_quantity_one(self, orders):
        """
        Each CSV row corresponds to exactly one cart item, confirmed by
        the quantity column being '1' for every data row.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses=None)
        data_rows, header = _parse_csv_rows(csv_output)

        # CSV columns: club_name, order_status, product_type, quantity, unit_price, attributes
        for i, row in enumerate(data_rows):
            assert row[3] == '1', (
                f"Row {i} has quantity='{row[3]}' but expected '1'. "
                f"Each CSV row must represent exactly one cart item."
            )

    # -------------------------------------------------------------------------
    # Sub-property 16f: CSV header is always present (even with no data)
    # and has the expected columns
    # -------------------------------------------------------------------------

    @given(orders=_orders_list_strategy)
    @settings(max_examples=100)
    def test_csv_always_has_correct_header(self, orders):
        """
        The CSV output always starts with the expected header row regardless
        of the number of orders or items.

        **Validates: Requirements 9.6**
        """
        csv_output = generate_csv(orders, filter_statuses=None)
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        # There should always be at least the header row
        assert len(rows) >= 1, "CSV must always contain at least a header row"

        expected_header = ['club_name', 'order_status', 'product_type', 'quantity', 'unit_price', 'attributes']
        assert rows[0] == expected_header, (
            f"CSV header mismatch. Expected {expected_header}, got {rows[0]}"
        )
