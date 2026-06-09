"""
Property-Based Tests for Migration Identification (Property 2)

**Validates: Requirements 1.1, 1.10, 1.11**

Property 2: Migration identification correctly selects legacy products.

For any set of product records in the Producten table, the migration
identification logic SHALL select only records that:
- Have an `opties` field
- Do NOT have a `legacy_opties` field (not already migrated)
- Do NOT have a `legacy_id` field (not already migrated)
- Do NOT have existing variant records (records where parent_id == product's product_id)

All other records must be excluded.
"""

import os
import sys
import uuid

import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st

# Add scripts directory to path so we can import migrate_products
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_scripts_path = os.path.join(_project_root, "scripts")
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

from migrate_products import is_legacy_product


# =============================================================================
# Hypothesis Strategies
# =============================================================================


def _product_id() -> st.SearchStrategy[str]:
    """Generate a product id (either legacy short id or UUID)."""
    return st.one_of(
        # Legacy short IDs like "G5", "P12", "T1"
        st.from_regex(r"[A-Z][0-9]{1,3}", fullmatch=True),
        # UUID-style IDs
        st.uuids().map(str),
    )


def _product_name() -> st.SearchStrategy[str]:
    """Generate a product name."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip() != "")


def _opties_value() -> st.SearchStrategy[str]:
    """Generate a plausible opties value (comma-separated sizes or One Size)."""
    return st.one_of(
        # Comma-separated sizes
        st.lists(
            st.sampled_from(["XS", "S", "M", "L", "XL", "XXL", "One Size"]),
            min_size=1,
            max_size=6,
        ).map(lambda vs: ",".join(vs)),
        # Simple single values
        st.sampled_from(["One Size", "", "S,M,L", "S,M,L,XL", "M,L,XL,XXL"]),
    )


@st.composite
def legacy_product_strategy(draw) -> dict:
    """Generate a legacy product: has `opties`, no `legacy_opties`, no `legacy_id`."""
    product_id = draw(_product_id())
    return {
        "product_id": product_id,
        "naam": draw(_product_name()),
        "prijs": draw(st.integers(min_value=5, max_value=200)),
        "opties": draw(_opties_value()),
    }


@st.composite
def already_migrated_product_strategy(draw) -> dict:
    """Generate an already-migrated product: has `legacy_opties` and/or `legacy_id`."""
    product_id = str(draw(st.uuids()))
    has_legacy_opties = draw(st.booleans())
    has_legacy_id = draw(st.booleans())
    # At least one of the two markers must be present
    assume(has_legacy_opties or has_legacy_id)

    item = {
        "product_id": product_id,
        "name": draw(_product_name()),
        "price": draw(st.integers(min_value=5, max_value=200)),
        "is_parent": True,
        "active": True,
    }
    if has_legacy_opties:
        item["legacy_opties"] = draw(_opties_value())
    if has_legacy_id:
        item["legacy_id"] = draw(_product_id())
    # Some migrated products might still have opties (edge case to test)
    if draw(st.booleans()):
        item["opties"] = draw(_opties_value())
    return item


@st.composite
def uuid_parent_product_strategy(draw) -> dict:
    """Generate a pre-existing UUID parent product (new model, no opties)."""
    return {
        "product_id": str(draw(st.uuids())),
        "name": draw(_product_name()),
        "price": draw(st.integers(min_value=5, max_value=200)),
        "is_parent": True,
        "active": True,
        "variant_schema": {"Maat": ["S", "M", "L"]},
    }


@st.composite
def variant_record_strategy(draw, parent_id: str | None = None) -> dict:
    """Generate a variant record (child of a parent product)."""
    pid = parent_id or str(draw(st.uuids()))
    return {
        "product_id": str(draw(st.uuids())),
        "is_parent": False,
        "parent_id": pid,
        "variant_attributes": {"Maat": draw(st.sampled_from(["S", "M", "L", "XL"]))},
        "stock": draw(st.integers(min_value=0, max_value=100)),
        "allow_oversell": draw(st.booleans()),
        "active": True,
    }


@st.composite
def legacy_product_with_existing_variants_strategy(draw) -> tuple[dict, list[dict]]:
    """Generate a legacy product that already has variant records in the table.

    This tests the edge case where a product has `opties` but variant records
    already exist for it — it should NOT be identified as needing migration.
    """
    product_id = draw(_product_id())
    product = {
        "product_id": product_id,
        "naam": draw(_product_name()),
        "prijs": draw(st.integers(min_value=5, max_value=200)),
        "opties": draw(_opties_value()),
    }
    # Generate 1-4 variant records pointing to this product
    num_variants = draw(st.integers(min_value=1, max_value=4))
    variants = []
    for _ in range(num_variants):
        variant = draw(variant_record_strategy(parent_id=product_id))
        variants.append(variant)
    return product, variants


@st.composite
def mixed_table_state(draw) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Generate a mixed table state with all four product types.

    Returns:
        Tuple of (legacy_products, migrated_products, uuid_products, variant_records)
        where legacy_products are the ones that SHOULD be selected for migration.
    """
    # Generate 0-5 of each type
    legacy_products = draw(
        st.lists(legacy_product_strategy(), min_size=0, max_size=5)
    )
    migrated_products = draw(
        st.lists(already_migrated_product_strategy(), min_size=0, max_size=5)
    )
    uuid_products = draw(
        st.lists(uuid_parent_product_strategy(), min_size=0, max_size=5)
    )

    # Generate variant records for some UUID products
    variant_records = []
    for product in uuid_products:
        if draw(st.booleans()):
            num_vars = draw(st.integers(min_value=1, max_value=3))
            for _ in range(num_vars):
                variant = draw(
                    variant_record_strategy(parent_id=product["product_id"])
                )
                variant_records.append(variant)

    return legacy_products, migrated_products, uuid_products, variant_records


# =============================================================================
# Property 2: Migration identification correctly selects legacy products
# =============================================================================


class TestProperty2MigrationIdentification:
    """
    **Validates: Requirements 1.1, 1.10, 1.11**

    For any set of product records in the Producten table, the migration
    identification logic SHALL select only records that have an `opties` field
    AND do not have a `legacy_opties` field AND do not have a `legacy_id` field
    AND do not have existing variant records (records where `parent_id` equals
    the product's `product_id`), excluding all other records.
    """

    @given(data=mixed_table_state())
    @settings(max_examples=100)
    def test_only_legacy_products_are_selected(self, data):
        """Only genuine legacy products (with opties, not migrated, no variants) are selected."""
        legacy_products, migrated_products, uuid_products, variant_records = data

        # Build the full table state
        all_items = legacy_products + migrated_products + uuid_products + variant_records

        # Identify which items should be flagged as legacy
        for item in legacy_products:
            result = is_legacy_product(item, all_items)
            note(f"Legacy product {item.get('product_id')}: is_legacy={result}")
            assert result is True, (
                f"Expected legacy product {item.get('product_id')} to be identified "
                f"as legacy, but it was not. Item: {item}"
            )

    @given(data=mixed_table_state())
    @settings(max_examples=100)
    def test_migrated_products_are_excluded(self, data):
        """Products with legacy_opties or legacy_id should NOT be selected."""
        legacy_products, migrated_products, uuid_products, variant_records = data
        assume(len(migrated_products) > 0)

        all_items = legacy_products + migrated_products + uuid_products + variant_records

        for item in migrated_products:
            result = is_legacy_product(item, all_items)
            note(f"Migrated product {item.get('product_id')}: is_legacy={result}")
            assert result is False, (
                f"Expected migrated product {item.get('product_id')} to be excluded, "
                f"but it was selected. Item: {item}"
            )

    @given(data=mixed_table_state())
    @settings(max_examples=100)
    def test_uuid_products_without_opties_are_excluded(self, data):
        """New-model UUID products without opties should NOT be selected."""
        legacy_products, migrated_products, uuid_products, variant_records = data
        assume(len(uuid_products) > 0)

        all_items = legacy_products + migrated_products + uuid_products + variant_records

        for item in uuid_products:
            result = is_legacy_product(item, all_items)
            note(f"UUID product {item.get('product_id')}: is_legacy={result}")
            assert result is False, (
                f"Expected UUID product {item.get('product_id')} to be excluded, "
                f"but it was selected. Item: {item}"
            )

    @given(data=mixed_table_state())
    @settings(max_examples=100)
    def test_variant_records_are_excluded(self, data):
        """Variant records (is_parent=False, have parent_id) should NOT be selected."""
        legacy_products, migrated_products, uuid_products, variant_records = data
        assume(len(variant_records) > 0)

        all_items = legacy_products + migrated_products + uuid_products + variant_records

        for item in variant_records:
            result = is_legacy_product(item, all_items)
            note(f"Variant record {item.get('product_id')}: is_legacy={result}")
            assert result is False, (
                f"Expected variant record {item.get('product_id')} to be excluded, "
                f"but it was selected. Item: {item}"
            )

    @given(product_and_variants=legacy_product_with_existing_variants_strategy())
    @settings(max_examples=100)
    def test_legacy_product_with_existing_variants_excluded(self, product_and_variants):
        """A product with opties but already having variant children should NOT be selected."""
        product, variants = product_and_variants

        # Build all_items including the product and its variants
        all_items = [product] + variants

        result = is_legacy_product(product, all_items)
        note(
            f"Product {product.get('product_id')} with {len(variants)} existing "
            f"variants: is_legacy={result}"
        )
        assert result is False, (
            f"Expected product with existing variants to be excluded, "
            f"but it was selected. Product: {product}, Variants: {len(variants)}"
        )

    @given(item=legacy_product_strategy())
    @settings(max_examples=100)
    def test_product_without_opties_not_selected(self, item):
        """A product without opties field should never be selected."""
        # Remove the opties field
        item_without_opties = {k: v for k, v in item.items() if k != "opties"}
        all_items = [item_without_opties]

        result = is_legacy_product(item_without_opties, all_items)
        assert result is False, (
            f"Product without opties should never be selected. Item: {item_without_opties}"
        )
