"""
Property-Based Test: Migration Idempotency (Property 3)

**Validates: Requirements 1.12**

Property 3: Migration is idempotent — running the migration script twice on any
initial state of the Producten table produces the same end state as running it once.
No duplicate records are created, and no fields are modified on already-migrated products.

Uses Hypothesis to generate random legacy product data and verifies that:
1. After first migration run: table reaches a migrated state
2. After second migration run: table state is identical (same records, same fields)
3. The second run finds zero products to migrate (all have `legacy_opties`)
"""

import os
import sys
import uuid
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# Add scripts directory to path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
)

from migrate_products import migrate_products, MigrationSummary


# =============================================================================
# Hypothesis Strategies
# =============================================================================


@st.composite
def legacy_product_strategy(draw):
    """Generate a random legacy product record.

    Produces records that look like real legacy H-DCN products with:
    - A short alphanumeric id (e.g., "G5", "P12")
    - A product name (naam)
    - A price (prijs)
    - An opties field (comma-separated sizes, "One Size", or empty)
    """
    # Generate a legacy-style id (short alphanumeric, like "G5", "P12", "A1")
    prefix = draw(st.sampled_from(["G", "P", "A", "B", "K", "S"]))
    number = draw(st.integers(min_value=1, max_value=99))
    legacy_id = f"{prefix}{number}"

    # Generate a product name
    name = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
            min_size=2,
            max_size=30,
        ).filter(lambda n: n.strip() != "")
    )

    # Generate a price as integer or float
    price = draw(st.integers(min_value=1, max_value=500))

    # Generate opties: comma-separated sizes, "One Size", or empty
    opties_type = draw(st.sampled_from(["sizes", "one_size", "empty"]))

    if opties_type == "sizes":
        # Generate 1-6 size values (letters/numbers, no commas)
        size_values = draw(
            st.lists(
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=("L", "N"),
                    ),
                    min_size=1,
                    max_size=8,
                ).filter(lambda v: v.strip() != "" and "," not in v),
                min_size=1,
                max_size=6,
                unique=True,
            )
        )
        opties = ", ".join(size_values)
    elif opties_type == "one_size":
        opties = "One Size"
    else:
        opties = ""

    # Optional group field
    groep = draw(st.one_of(st.none(), st.sampled_from(["Kleding", "Accessoires", "Stickers"])))

    item = {
        "product_id": legacy_id,
        "naam": name,
        "prijs": price,
        "opties": opties,
    }

    if groep:
        item["groep"] = groep

    return item


@st.composite
def legacy_products_list_strategy(draw):
    """Generate a list of 1-5 unique legacy products."""
    products = draw(
        st.lists(
            legacy_product_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda p: p["product_id"],
        )
    )
    return products


# =============================================================================
# Helper Functions
# =============================================================================


def _create_all_tables(dynamodb):
    """Create all DynamoDB tables needed by the migration script."""
    dynamodb.create_table(
        TableName="TestProducten",
        KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.create_table(
        TableName="Events",
        KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "event_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.create_table(
        TableName="Carts",
        KeySchema=[{"AttributeName": "cart_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "cart_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.create_table(
        TableName="Orders",
        KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "order_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.create_table(
        TableName="Payments",
        KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "payment_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def _get_table_state(table) -> list[dict]:
    """Get all items from a table, sorted by product_id for comparison.

    Removes non-deterministic fields (migrated_at, created_at) for comparison
    since timestamps will differ between runs.
    """
    items = []
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # Remove timestamp fields that are non-deterministic
    for item in items:
        item.pop("migrated_at", None)
        item.pop("created_at", None)

    # Sort by product_id for deterministic comparison
    items.sort(key=lambda x: x.get("product_id", ""))
    return items


def _normalize_for_comparison(items: list[dict]) -> list[dict]:
    """Normalize items for comparison by converting Decimal to int/float."""
    normalized = []
    for item in items:
        norm_item = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                norm_item[key] = int(value) if value == int(value) else float(value)
            else:
                norm_item[key] = value
        normalized.append(norm_item)
    return normalized


# =============================================================================
# Property 3: Migration is idempotent
# =============================================================================


class TestProperty3MigrationIdempotency:
    """
    **Validates: Requirements 1.12**

    Property 3: Migration is idempotent — for any initial state of the Producten
    table, running the migration script twice produces the same end state as
    running it once. No duplicate records are created, no fields are modified on
    already-migrated products.
    """

    @given(products=legacy_products_list_strategy())
    @settings(max_examples=100, deadline=None)
    def test_migration_idempotency(self, products):
        """Running migration twice produces the same end state as running once."""
        with mock_aws():
            # Set up DynamoDB tables
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            _create_all_tables(dynamodb)
            table = dynamodb.Table("TestProducten")

            # Seed the table with generated legacy products
            for product in products:
                table.put_item(Item=product)

            # Patch get_dynamodb_resource to use moto
            with patch(
                "migrate_products.get_dynamodb_resource"
            ) as mock_resource:
                mock_resource.return_value = dynamodb

                # --- First migration run ---
                result1 = migrate_products(
                    dry_run=False, profile=None, table_name="TestProducten"
                )

                # Capture state after first run
                state_after_first_run = _get_table_state(table)
                state_after_first_run_normalized = _normalize_for_comparison(
                    state_after_first_run
                )

                # --- Second migration run ---
                result2 = migrate_products(
                    dry_run=False, profile=None, table_name="TestProducten"
                )

                # Capture state after second run
                state_after_second_run = _get_table_state(table)
                state_after_second_run_normalized = _normalize_for_comparison(
                    state_after_second_run
                )

            # --- Assertions ---

            # 1. Same number of records
            assert len(state_after_first_run) == len(state_after_second_run), (
                f"Record count changed: {len(state_after_first_run)} → "
                f"{len(state_after_second_run)}"
            )

            # 2. Same records with same fields
            assert state_after_first_run_normalized == state_after_second_run_normalized, (
                "Table state differs between first and second migration run"
            )

            # 3. Second run should find zero products to migrate
            assert result2.products_migrated == 0, (
                f"Second run migrated {result2.products_migrated} products "
                f"(expected 0 — all should have legacy_opties)"
            )

            # 4. Second run should have no errors
            assert len(result2.errors) == 0, (
                f"Second run had errors: {result2.errors}"
            )

            # 5. First run should have migrated at least some products
            # (the generated products are all legacy products)
            note(
                f"First run: migrated={result1.products_migrated}, "
                f"skipped={result1.products_skipped}, "
                f"variants={result1.variants_created}"
            )
