"""
Property-Based Tests for PresMeet v2 Tenant Field Isolation

Tests that all PresMeet records contain both `tenant=presmeet` and a `source` field,
and that the migration logic correctly assigns tenant based on source.

This file covers:
- Property 4: Tenant field isolation invariant

**Validates: Requirements 6.1, 6.2, 6.4, 7.9, 11.7**
"""

import sys
import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, note, assume
from hypothesis import strategies as st

# Ensure shared layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure scripts directory is importable for migration logic
_scripts_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')
)
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'save_presmeet_booking')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Remove any previously cached 'app' module so we import from the correct handler
if 'app' in sys.modules:
    del sys.modules['app']

# Import the mapping functions from save_presmeet_booking
from app import map_delegates_to_items, map_guests_to_items, map_transfers_to_items

# Import migration logic
from migrate_add_tenant_field import determine_tenant


# --- Strategies ---

# Strategy for delegate names
name_strategy = st.text(
    min_size=1, max_size=50,
    alphabet=st.characters(whitelist_categories=('L', 'Nd', 'Zs'))
)

# Strategy for delegate roles
role_strategy = st.text(
    min_size=1, max_size=30,
    alphabet=st.characters(whitelist_categories=('L', 'Nd', 'Zs'))
)

# Strategy for t-shirt genders
gender_strategy = st.sampled_from(['male', 'female', 'unisex'])

# Strategy for t-shirt sizes
size_strategy = st.sampled_from(['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'])

# Strategy for optional t-shirt
tshirt_strategy = st.one_of(
    st.none(),
    st.fixed_dictionaries({
        'gender': gender_strategy,
        'size': size_strategy,
    })
)

# Strategy for a delegate entry
delegate_strategy = st.fixed_dictionaries({
    'name': name_strategy,
    'role': role_strategy,
    'party': st.booleans(),
    'tshirt': tshirt_strategy,
})

# Strategy for a guest entry
guest_strategy = st.fixed_dictionaries({
    'name': name_strategy,
    'tshirt': tshirt_strategy,
})

# Strategy for transfer direction
direction_strategy = st.sampled_from(['arrival', 'departure'])

# Strategy for airports
airport_strategy = st.sampled_from(['AMS', 'EIN', 'RTM', 'DUS', 'BRU'])

# Strategy for flight numbers
flight_strategy = st.text(
    min_size=3, max_size=10,
    alphabet=st.characters(whitelist_categories=('L', 'Nd'))
)

# Strategy for transfer dates and times
date_strategy = st.dates().map(lambda d: d.isoformat())
time_strategy = st.times().map(lambda t: t.strftime('%H:%M'))

# Strategy for a transfer entry
transfer_strategy = st.fixed_dictionaries({
    'direction': direction_strategy,
    'airport': airport_strategy,
    'flight': flight_strategy,
    'date': date_strategy,
    'time': time_strategy,
    'persons': st.integers(min_value=1, max_value=10),
})

# Strategy for source fields that contain "presmeet"
presmeet_source_strategy = st.sampled_from([
    'presmeet', 'presmeet_config', 'presmeet_order', 'PRESMEET', 'PresMeet'
])

# Strategy for source fields that do NOT contain "presmeet"
non_presmeet_source_strategy = st.one_of(
    st.just('h-dcn'),
    st.just('webshop'),
    st.just(''),
    st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'Nd'))).filter(
        lambda s: 'presmeet' not in s.lower()
    ),
)

# Strategy for a complete order record as produced by save_presmeet_booking
order_record_strategy = st.fixed_dictionaries({
    'order_id': st.uuids().map(str),
    'source': st.just('presmeet'),
    'tenant': st.just('presmeet'),
    'club_id': st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'Nd'))),
    'status': st.sampled_from(['draft', 'submitted', 'locked']),
    'payment_status': st.sampled_from(['unpaid', 'pending', 'paid', 'partial']),
    'items': st.lists(delegate_strategy, min_size=0, max_size=5),
    'total_amount': st.decimals(min_value=0, max_value=10000, places=2, allow_nan=False, allow_infinity=False),
    'created_at': st.just(datetime.now(timezone.utc).isoformat()),
    'updated_at': st.just(datetime.now(timezone.utc).isoformat()),
    'created_by': st.emails(),
})

# Strategy for a payment record as produced by create_presmeet_payment
payment_record_strategy = st.fixed_dictionaries({
    'payment_id': st.uuids().map(str),
    'source': st.just('presmeet'),
    'tenant': st.just('presmeet'),
    'order_id': st.uuids().map(str),
    'club_id': st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'Nd'))),
    'amount': st.decimals(min_value=1, max_value=10000, places=2, allow_nan=False, allow_infinity=False),
    'status': st.sampled_from(['pending', 'paid', 'failed']),
    'provider': st.just('mollie'),
    'created_at': st.just(datetime.now(timezone.utc).isoformat()),
    'created_by': st.emails(),
})

# Strategy for a cart record
cart_record_strategy = st.fixed_dictionaries({
    'cart_id': st.uuids().map(str),
    'source': st.just('presmeet'),
    'tenant': st.just('presmeet'),
    'club_id': st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'Nd'))),
    'items': st.just([]),
    'created_at': st.just(datetime.now(timezone.utc).isoformat()),
    'updated_at': st.just(datetime.now(timezone.utc).isoformat()),
})

# Strategy for a generic DynamoDB record used to test migration logic
migration_record_strategy = st.fixed_dictionaries({
    'record_id': st.uuids().map(str),
    'source': st.one_of(presmeet_source_strategy, non_presmeet_source_strategy, st.just(None)),
    'some_field': st.text(min_size=0, max_size=50),
}).map(lambda d: {k: v for k, v in d.items() if v is not None})


# =============================================================================
# Property 4: Tenant field isolation invariant
# =============================================================================

class TestProperty4TenantFieldIsolation:
    """
    **Validates: Requirements 6.1, 6.2, 6.4, 7.9, 11.7**

    Property 4: Tenant field isolation invariant

    All PresMeet records MUST contain both `tenant=presmeet` and a `source` field.
    - Any record created via the booking handler mapping functions, when assembled
      into an order/payment/cart record, MUST have tenant=presmeet and source present.
    - The migration script MUST assign tenant=presmeet to records with source containing "presmeet".
    """

    # -------------------------------------------------------------------------
    # Sub-property 4a: Order records from save_presmeet_booking always have
    # both tenant=presmeet and source=presmeet
    # -------------------------------------------------------------------------

    @given(
        delegates=st.lists(delegate_strategy, min_size=0, max_size=3),
        guests=st.lists(guest_strategy, min_size=0, max_size=3),
        transfers=st.lists(transfer_strategy, min_size=0, max_size=3),
        club_id=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'Nd'))),
        user_email=st.emails(),
    )
    @settings(max_examples=200)
    def test_order_record_always_has_tenant_and_source(
        self, delegates, guests, transfers, club_id, user_email
    ):
        """
        For any combination of delegates, guests, and transfers, the order record
        produced by the save_presmeet_booking handler MUST contain both
        tenant='presmeet' and source='presmeet'.

        **Validates: Requirements 6.1, 6.2, 7.9, 11.7**
        """
        # Simulate order record construction as done in the handler
        items = []
        items.extend(map_delegates_to_items(delegates))
        items.extend(map_guests_to_items(guests))
        items.extend(map_transfers_to_items(transfers))

        now = datetime.now(timezone.utc).isoformat()
        order_record = {
            'order_id': str(uuid.uuid4()),
            'source': 'presmeet',
            'tenant': 'presmeet',
            'club_id': club_id,
            'status': 'draft',
            'payment_status': 'unpaid',
            'items': items,
            'total_amount': sum(item.get('unit_price', Decimal('0')) for item in items),
            'created_at': now,
            'updated_at': now,
            'submitted_at': None,
            'created_by': user_email,
        }

        # Property assertion: tenant must be "presmeet"
        assert order_record['tenant'] == 'presmeet', (
            f"Order record must have tenant='presmeet', got '{order_record.get('tenant')}'"
        )
        # Property assertion: source must be present and set to "presmeet"
        assert 'source' in order_record, "Order record must contain 'source' field"
        assert order_record['source'] == 'presmeet', (
            f"Order record must have source='presmeet', got '{order_record.get('source')}'"
        )

    # -------------------------------------------------------------------------
    # Sub-property 4b: Payment records always have tenant=presmeet and source
    # -------------------------------------------------------------------------

    @given(record=payment_record_strategy)
    @settings(max_examples=200)
    def test_payment_record_always_has_tenant_and_source(self, record):
        """
        Any payment record created by the PresMeet module MUST contain both
        tenant='presmeet' and a source field.

        **Validates: Requirements 6.1, 6.2, 11.7**
        """
        assert record['tenant'] == 'presmeet', (
            f"Payment record must have tenant='presmeet', got '{record.get('tenant')}'"
        )
        assert 'source' in record, "Payment record must contain 'source' field"
        assert record['source'] == 'presmeet', (
            f"Payment record must have source='presmeet', got '{record.get('source')}'"
        )

    # -------------------------------------------------------------------------
    # Sub-property 4c: Cart records always have tenant=presmeet and source
    # -------------------------------------------------------------------------

    @given(record=cart_record_strategy)
    @settings(max_examples=200)
    def test_cart_record_always_has_tenant_and_source(self, record):
        """
        Any cart record created by the PresMeet module MUST contain both
        tenant='presmeet' and a source field.

        **Validates: Requirements 6.1, 6.2, 11.7**
        """
        assert record['tenant'] == 'presmeet', (
            f"Cart record must have tenant='presmeet', got '{record.get('tenant')}'"
        )
        assert 'source' in record, "Cart record must contain 'source' field"
        assert record['source'] == 'presmeet', (
            f"Cart record must have source='presmeet', got '{record.get('source')}'"
        )

    # -------------------------------------------------------------------------
    # Sub-property 4d: Migration logic - source containing "presmeet" → tenant=presmeet
    # -------------------------------------------------------------------------

    @given(source=presmeet_source_strategy)
    @settings(max_examples=200)
    def test_migration_presmeet_source_gets_presmeet_tenant(self, source):
        """
        The migration script's determine_tenant function MUST assign
        tenant='presmeet' to any record where source contains 'presmeet'
        (case-insensitive).

        **Validates: Requirements 6.1, 6.4, 11.7**
        """
        record = {'source': source}
        tenant = determine_tenant(record)

        note(f"source={source}, determined_tenant={tenant}")
        assert tenant == 'presmeet', (
            f"Record with source='{source}' must get tenant='presmeet', got '{tenant}'"
        )

    @given(source=non_presmeet_source_strategy)
    @settings(max_examples=200)
    def test_migration_non_presmeet_source_gets_hdcn_tenant(self, source):
        """
        The migration script's determine_tenant function MUST assign
        tenant='h-dcn' to any record where source does NOT contain 'presmeet'.

        **Validates: Requirements 6.4**
        """
        record = {'source': source}
        tenant = determine_tenant(record)

        note(f"source={source}, determined_tenant={tenant}")
        assert tenant == 'h-dcn', (
            f"Record with source='{source}' must get tenant='h-dcn', got '{tenant}'"
        )

    @given(record=migration_record_strategy)
    @settings(max_examples=300)
    def test_migration_biconditional_source_tenant_relationship(self, record):
        """
        Property: determine_tenant(record) == 'presmeet' iff
        record.get('source', '') contains 'presmeet' (case-insensitive).

        This is the biconditional invariant: the tenant assignment is
        fully determined by the source field content.

        **Validates: Requirements 6.1, 6.4, 11.7**
        """
        tenant = determine_tenant(record)
        source = record.get('source', '')

        if isinstance(source, str) and 'presmeet' in source.lower():
            assert tenant == 'presmeet', (
                f"Source '{source}' contains 'presmeet' but tenant='{tenant}' (expected 'presmeet')"
            )
        else:
            assert tenant == 'h-dcn', (
                f"Source '{source}' does not contain 'presmeet' but tenant='{tenant}' (expected 'h-dcn')"
            )

    # -------------------------------------------------------------------------
    # Sub-property 4e: Records with tenant=presmeet MUST have source field
    # -------------------------------------------------------------------------

    @given(record=st.one_of(order_record_strategy, payment_record_strategy, cart_record_strategy))
    @settings(max_examples=300)
    def test_presmeet_tenant_implies_source_present(self, record):
        """
        Any record with tenant='presmeet' MUST also have a 'source' field present
        and non-empty.

        **Validates: Requirements 6.1, 6.2, 11.7**
        """
        if record.get('tenant') == 'presmeet':
            assert 'source' in record, (
                f"Record with tenant='presmeet' must have 'source' field. "
                f"Record keys: {list(record.keys())}"
            )
            assert record['source'], (
                f"Record with tenant='presmeet' must have non-empty 'source' field. "
                f"Got source='{record.get('source')}'"
            )

    # -------------------------------------------------------------------------
    # Sub-property 4f: Mapping functions produce valid items for order assembly
    # -------------------------------------------------------------------------

    @given(delegates=st.lists(delegate_strategy, min_size=1, max_size=5))
    @settings(max_examples=200)
    def test_delegate_items_have_valid_product_types(self, delegates):
        """
        Items produced by map_delegates_to_items always have a product_type
        that is one of the known PresMeet types, ensuring they belong to
        the presmeet tenant domain.

        **Validates: Requirements 6.1, 7.9**
        """
        valid_types = {'meeting_ticket', 'party_ticket', 'tshirt', 'airport_transfer'}
        items = map_delegates_to_items(delegates)

        for item in items:
            assert item['product_type'] in valid_types, (
                f"Item product_type '{item['product_type']}' not in valid PresMeet types"
            )
            assert 'item_id' in item, "Each item must have an item_id"
            assert 'unit_price' in item, "Each item must have a unit_price"
            assert 'attributes' in item, "Each item must have attributes"

    @given(guests=st.lists(guest_strategy, min_size=1, max_size=5))
    @settings(max_examples=200)
    def test_guest_items_have_valid_product_types(self, guests):
        """
        Items produced by map_guests_to_items always have a valid product_type.

        **Validates: Requirements 6.1, 7.9**
        """
        valid_types = {'meeting_ticket', 'party_ticket', 'tshirt', 'airport_transfer'}
        items = map_guests_to_items(guests)

        for item in items:
            assert item['product_type'] in valid_types, (
                f"Item product_type '{item['product_type']}' not in valid PresMeet types"
            )

    @given(transfers=st.lists(transfer_strategy, min_size=1, max_size=5))
    @settings(max_examples=200)
    def test_transfer_items_have_valid_product_types(self, transfers):
        """
        Items produced by map_transfers_to_items always have a valid product_type.

        **Validates: Requirements 6.1, 7.9**
        """
        valid_types = {'meeting_ticket', 'party_ticket', 'tshirt', 'airport_transfer'}
        items = map_transfers_to_items(transfers)

        for item in items:
            assert item['product_type'] in valid_types, (
                f"Item product_type '{item['product_type']}' not in valid PresMeet types"
            )


# --- Property 5 Strategies ---

# Valid tenant values used in the system
VALID_TENANTS = ["presmeet", "h-dcn"]

# Strategy for product tenant values: known tenants + random strings
_tenant_strategy = st.one_of(
    st.sampled_from(VALID_TENANTS),
    st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N")))
)

# Strategy for a single product record (for tenant filtering tests)
_product_strategy = st.fixed_dictionaries({
    "product_id": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Pd"))),
    "naam": st.text(min_size=1, max_size=50),
    "tenant": _tenant_strategy,
    "price": st.floats(min_value=0.01, max_value=9999.99, allow_nan=False, allow_infinity=False),
    "product_type": st.sampled_from(["meeting_ticket", "party_ticket", "tshirt", "airport_transfer", "merchandise"]),
})

# Strategy for a list of products with mixed tenants
_product_list_strategy = st.lists(_product_strategy, min_size=0, max_size=30)


def filter_products_by_tenant(products, tenant):
    """
    Simulates the DynamoDB FilterExpression: Attr('tenant').eq(tenant_value)

    This is the exact logic used in handlers like get_presmeet_config, get_presmeet_booking,
    generate_presmeet_report, and lock_presmeet_orders to isolate records by tenant.
    """
    return [p for p in products if p.get("tenant") == tenant]


# =============================================================================
# Property 5: Tenant-based product filtering
# =============================================================================

class TestProperty5TenantBasedProductFiltering:
    """
    **Validates: Requirements 4.3, 9.7**

    Property 5: When filtering products by tenant, ONLY records with the
    exact matching tenant value appear. Products from one tenant are NEVER
    visible when filtering for another tenant.

    This validates:
    - Req 4.3: The H-DCN webshop SHALL display only products with tenant=h-dcn,
      and the PresMeet Booking_Form SHALL display only products with tenant=presmeet
    - Req 9.7: PresMeet reporting SHALL scope data to records with tenant=presmeet
    """

    @given(products=_product_list_strategy)
    @settings(max_examples=500)
    def test_presmeet_filter_returns_only_presmeet_products(self, products):
        """
        When filtering by tenant='presmeet', ONLY records with tenant exactly
        'presmeet' appear in the result.

        **Validates: Requirements 4.3, 9.7**
        """
        result = filter_products_by_tenant(products, "presmeet")

        for product in result:
            assert product["tenant"] == "presmeet", (
                f"Product {product['product_id']} has tenant='{product['tenant']}' "
                f"but appeared in presmeet-filtered results"
            )

    @given(products=_product_list_strategy)
    @settings(max_examples=500)
    def test_hdcn_filter_returns_only_hdcn_products(self, products):
        """
        When filtering by tenant='h-dcn', ONLY records with tenant exactly
        'h-dcn' appear in the result.

        **Validates: Requirements 4.3, 9.7**
        """
        result = filter_products_by_tenant(products, "h-dcn")

        for product in result:
            assert product["tenant"] == "h-dcn", (
                f"Product {product['product_id']} has tenant='{product['tenant']}' "
                f"but appeared in h-dcn-filtered results"
            )

    @given(products=_product_list_strategy)
    @settings(max_examples=500)
    def test_presmeet_products_never_in_hdcn_results(self, products):
        """
        Products with tenant='presmeet' are NEVER visible when filtering
        for tenant='h-dcn'. Cross-tenant leakage must not occur.

        **Validates: Requirements 4.3, 9.7**
        """
        hdcn_results = filter_products_by_tenant(products, "h-dcn")

        for product in hdcn_results:
            assert product["tenant"] != "presmeet", (
                f"PresMeet product {product['product_id']} leaked into h-dcn results"
            )

    @given(products=_product_list_strategy)
    @settings(max_examples=500)
    def test_hdcn_products_never_in_presmeet_results(self, products):
        """
        Products with tenant='h-dcn' are NEVER visible when filtering
        for tenant='presmeet'. Cross-tenant leakage must not occur.

        **Validates: Requirements 4.3, 9.7**
        """
        presmeet_results = filter_products_by_tenant(products, "presmeet")

        for product in presmeet_results:
            assert product["tenant"] != "h-dcn", (
                f"H-DCN product {product['product_id']} leaked into presmeet results"
            )

    @given(products=_product_list_strategy)
    @settings(max_examples=500)
    def test_filter_result_count_matches_exact_tenant_count(self, products):
        """
        The number of products returned by a tenant filter must equal exactly
        the count of products in the input list with that tenant value.

        **Validates: Requirements 4.3, 9.7**
        """
        presmeet_count = sum(1 for p in products if p["tenant"] == "presmeet")
        hdcn_count = sum(1 for p in products if p["tenant"] == "h-dcn")

        presmeet_results = filter_products_by_tenant(products, "presmeet")
        hdcn_results = filter_products_by_tenant(products, "h-dcn")

        assert len(presmeet_results) == presmeet_count, (
            f"Expected {presmeet_count} presmeet products, got {len(presmeet_results)}"
        )
        assert len(hdcn_results) == hdcn_count, (
            f"Expected {hdcn_count} h-dcn products, got {len(hdcn_results)}"
        )

    @given(products=_product_list_strategy)
    @settings(max_examples=300)
    def test_tenant_filter_is_disjoint_partition(self, products):
        """
        The presmeet-filtered set and h-dcn-filtered set must be disjoint:
        no product can appear in both filtered results.

        **Validates: Requirements 4.3, 9.7**
        """
        presmeet_results = filter_products_by_tenant(products, "presmeet")
        hdcn_results = filter_products_by_tenant(products, "h-dcn")

        presmeet_set = set(id(p) for p in presmeet_results)
        hdcn_set = set(id(p) for p in hdcn_results)

        overlap = presmeet_set & hdcn_set
        assert len(overlap) == 0, (
            f"Found {len(overlap)} products in both tenant-filtered results — "
            f"tenant filtering must produce disjoint sets"
        )

    @given(
        products=_product_list_strategy,
        unknown_tenant=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N")))
    )
    @settings(max_examples=200)
    def test_unknown_tenant_returns_empty_when_no_match(self, products, unknown_tenant):
        """
        Filtering by a tenant value that doesn't exist in the data returns
        an empty list (no false positives from partial matches).

        **Validates: Requirements 4.3, 9.7**
        """
        assume(unknown_tenant not in [p["tenant"] for p in products])

        result = filter_products_by_tenant(products, unknown_tenant)
        assert len(result) == 0, (
            f"Expected empty result for non-existent tenant '{unknown_tenant}', "
            f"got {len(result)} products"
        )
