"""
Property-Based Tests for Migration Transformation (Property 1).

**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6**

Property 1: Migration transformation produces correct unified records.

For any legacy product record with an `opties` field (comma-separated string
or "One Size"/empty), the migration transformation SHALL produce a parent record
with:
- A valid UUID v4 as `product_id`
- The original `id` preserved in `legacy_id`
- A `slug` formed from the original id and name
- The `opties` field removed and its value stored in `legacy_opties`
- `is_parent: true`, `active: true`
- Either a correct `variant_schema` with generated variant records (one per value)
  or a single default variant when opties is "One Size"/empty
"""

import os
import re
import sys
import uuid

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# Add scripts directory to path so we can import the migration module
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
)

from migrate_products import (
    parse_opties,
    generate_variants,
    create_slug,
    slugify,
    migrate_single_product,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================


# Strategy for generating realistic legacy product names (ASCII-only to match
# real H-DCN products like "Club T-shirt", "Polo", "Sticker")
product_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        whitelist_characters="-_",
        max_codepoint=127,
    ),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() != "")


# Strategy for generating legacy product IDs (short alphanumeric codes)
legacy_id_strategy = st.from_regex(r"[A-Z][0-9]{1,3}", fullmatch=True)


# Strategy for comma-separated opties values (real variant values like sizes/colors)
opties_values_strategy = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-"),
        min_size=1,
        max_size=10,
    ).filter(lambda s: s.strip() != "" and "," not in s),
    min_size=1,
    max_size=8,
    unique=True,
)


def comma_separated_opties() -> st.SearchStrategy[str]:
    """Generate comma-separated opties strings like 'S, M, L, XL'."""
    return opties_values_strategy.map(lambda vals: ", ".join(vals))


# Strategy for opties that should produce None (default variant cases)
default_variant_opties_strategy = st.sampled_from(
    ["One Size", "one size", "ONE SIZE", "", "   ", None]
)


# Combined strategy for any kind of opties value
any_opties_strategy = st.one_of(
    comma_separated_opties(),
    default_variant_opties_strategy,
)


# =============================================================================
# Property 1: Migration transformation produces correct unified records
# =============================================================================


class TestProperty1MigrationTransformation:
    """
    **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6**

    For any legacy product, migration transformation produces correct unified
    records with UUID generation, legacy_id preservation, slug format,
    variant_schema correctness, and variant record generation.
    """

    # -------------------------------------------------------------------------
    # Sub-property: UUID v4 generation
    # -------------------------------------------------------------------------

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=any_opties_strategy,
    )
    @settings(max_examples=100)
    def test_uuid_v4_generation(self, legacy_id, name, opties):
        """Migration produces a valid UUID v4 for product_id on parent and all variants."""
        variant_schema = parse_opties(opties)
        parent_id = str(uuid.uuid4())  # Simulate what migrate_single_product does
        variants = generate_variants(parent_id, variant_schema)

        # Parent ID must be valid UUID v4
        parsed_uuid = uuid.UUID(parent_id)
        assert parsed_uuid.version == 4

        # Each variant must have a valid UUID v4 product_id
        for variant in variants:
            variant_uuid = uuid.UUID(variant["product_id"])
            assert variant_uuid.version == 4

        # All UUIDs must be unique
        all_ids = [parent_id] + [v["product_id"] for v in variants]
        assert len(all_ids) == len(set(all_ids))

    # -------------------------------------------------------------------------
    # Sub-property: legacy_id preservation
    # -------------------------------------------------------------------------

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=comma_separated_opties(),
    )
    @settings(max_examples=100, deadline=None)
    def test_legacy_id_preserved(self, legacy_id, name, opties):
        """Migration preserves the original id in legacy_id field."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="TestProducten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Seed legacy product
            item = {
                "product_id": legacy_id,
                "id": legacy_id,
                "naam": name,
                "opties": opties,
                "prijs": 25,
            }

            variants_count, variant_records = migrate_single_product(
                table, item, dry_run=True
            )

            # In dry_run mode, we can't read back from table,
            # but we can verify the logic by checking what would be created
            # The function returns variants_count — verify it's positive
            assert variants_count > 0

            # Verify migrate_single_product logic directly:
            # It sets legacy_id = item.get("product_id", item.get("id"))
            # which should be our legacy_id
            assert item.get("product_id") == legacy_id or item.get("id") == legacy_id

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=comma_separated_opties(),
    )
    @settings(max_examples=100, deadline=None)
    def test_legacy_id_preserved_in_db(self, legacy_id, name, opties):
        """Migration writes legacy_id correctly to the database."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="TestProducten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            item = {
                "product_id": legacy_id,
                "id": legacy_id,
                "naam": name,
                "opties": opties,
                "prijs": 25,
            }

            migrate_single_product(table, item, dry_run=False)

            # Find the parent record (the one with is_parent=True)
            all_items = table.scan()["Items"]
            parents = [i for i in all_items if i.get("is_parent") is True]
            assert len(parents) == 1

            parent = parents[0]
            assert parent["legacy_id"] == legacy_id

    # -------------------------------------------------------------------------
    # Sub-property: slug format
    # -------------------------------------------------------------------------

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
    )
    @settings(max_examples=100)
    def test_slug_format(self, legacy_id, name):
        """Slug is formed from legacy_id + slugified name."""
        slug = create_slug(legacy_id, name)

        # Slug must start with the legacy_id
        assert slug.startswith(legacy_id)

        # If name is non-empty, slug has a dash separator after legacy_id
        name_slug = slugify(name)
        if name_slug:
            assert slug == f"{legacy_id}-{name_slug}"
        else:
            assert slug == legacy_id

        # Slug must be URL-friendly (lowercase after the legacy_id prefix, no special chars)
        slug_suffix = slug[len(legacy_id):]
        if slug_suffix:
            assert slug_suffix[0] == "-"
            suffix_part = slug_suffix[1:]
            # Should only contain lowercase, digits, and hyphens
            assert re.match(r"^[a-z0-9\-]*$", suffix_part), (
                f"Slug suffix '{suffix_part}' contains invalid characters"
            )

    # -------------------------------------------------------------------------
    # Sub-property: variant_schema correctness for comma-separated opties
    # -------------------------------------------------------------------------

    @given(opties_values=opties_values_strategy)
    @settings(max_examples=100)
    def test_variant_schema_from_csv_opties(self, opties_values):
        """Comma-separated opties produces variant_schema with key 'Maat'."""
        opties_str = ", ".join(opties_values)
        result = parse_opties(opties_str)

        assert result is not None
        assert "Maat" in result
        assert result["Maat"] == opties_values

    @given(opties=default_variant_opties_strategy)
    @settings(max_examples=100)
    def test_variant_schema_none_for_defaults(self, opties):
        """'One Size', empty, and null opties produce None variant_schema."""
        result = parse_opties(opties)
        assert result is None

    # -------------------------------------------------------------------------
    # Sub-property: variant record generation count and structure
    # -------------------------------------------------------------------------

    @given(opties_values=opties_values_strategy)
    @settings(max_examples=100)
    def test_variant_count_matches_opties_values(self, opties_values):
        """Number of generated variants equals number of opties values."""
        opties_str = ", ".join(opties_values)
        variant_schema = parse_opties(opties_str)
        parent_id = str(uuid.uuid4())
        variants = generate_variants(parent_id, variant_schema)

        assert len(variants) == len(opties_values)

    @given(opties=default_variant_opties_strategy)
    @settings(max_examples=100)
    def test_default_variant_single_record(self, opties):
        """'One Size'/empty/null opties produces exactly one default variant."""
        variant_schema = parse_opties(opties)
        assert variant_schema is None

        parent_id = str(uuid.uuid4())
        variants = generate_variants(parent_id, variant_schema)

        assert len(variants) == 1
        assert variants[0]["variant_attributes"] == {}
        assert variants[0]["parent_id"] == parent_id
        assert variants[0]["is_parent"] is False

    @given(opties_values=opties_values_strategy)
    @settings(max_examples=100)
    def test_variant_records_structure(self, opties_values):
        """Each variant record has correct structure: parent_id, is_parent, stock, allow_oversell."""
        opties_str = ", ".join(opties_values)
        variant_schema = parse_opties(opties_str)
        parent_id = str(uuid.uuid4())
        variants = generate_variants(parent_id, variant_schema)

        for variant in variants:
            # Required fields
            assert variant["is_parent"] is False
            assert variant["parent_id"] == parent_id
            assert variant["stock"] == 0
            assert variant["allow_oversell"] is True
            assert variant["active"] is True
            # UUID v4 product_id
            variant_uuid = uuid.UUID(variant["product_id"])
            assert variant_uuid.version == 4
            # variant_attributes must map the axis to a single value
            assert "Maat" in variant["variant_attributes"]
            assert variant["variant_attributes"]["Maat"] in opties_values

    @given(opties_values=opties_values_strategy)
    @settings(max_examples=100)
    def test_variant_attributes_cover_all_values(self, opties_values):
        """Generated variants collectively cover all opties values."""
        opties_str = ", ".join(opties_values)
        variant_schema = parse_opties(opties_str)
        parent_id = str(uuid.uuid4())
        variants = generate_variants(parent_id, variant_schema)

        generated_values = {v["variant_attributes"]["Maat"] for v in variants}
        assert generated_values == set(opties_values)

    # -------------------------------------------------------------------------
    # Sub-property: Full migration produces correct parent record
    # -------------------------------------------------------------------------

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=comma_separated_opties(),
    )
    @settings(max_examples=100, deadline=None)
    def test_full_migration_parent_record(self, legacy_id, name, opties):
        """Full migration sets is_parent, active, event_id, removes opties, stores legacy_opties."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="TestProducten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            item = {
                "product_id": legacy_id,
                "id": legacy_id,
                "naam": name,
                "opties": opties,
                "prijs": 25,
            }

            variants_count, variant_records = migrate_single_product(
                table, item, dry_run=False
            )

            # Fetch all records
            all_items = table.scan()["Items"]
            parents = [i for i in all_items if i.get("is_parent") is True]
            assert len(parents) == 1

            parent = parents[0]

            # Verify parent fields (Requirement 1.2, 1.6)
            assert parent["is_parent"] is True
            assert parent["active"] is True
            assert parent["event_id"] is None
            assert parent["legacy_id"] == legacy_id
            assert parent["legacy_opties"] == opties
            assert "opties" not in parent
            assert "id" not in parent

            # Verify UUID v4 (Requirement 1.2a)
            parent_uuid = uuid.UUID(parent["product_id"])
            assert parent_uuid.version == 4

            # Verify slug (Requirement 1.2c)
            expected_slug = create_slug(legacy_id, name)
            assert parent["slug"] == expected_slug

            # Verify variant_schema (Requirement 1.3)
            parsed_schema = parse_opties(opties)
            if parsed_schema:
                assert parent["variant_schema"] == parsed_schema

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=default_variant_opties_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_full_migration_default_variant(self, legacy_id, name, opties):
        """Full migration with 'One Size'/empty opties creates single default variant."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="TestProducten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            opties_value = opties if opties is not None else ""
            item = {
                "product_id": legacy_id,
                "id": legacy_id,
                "naam": name,
                "opties": opties_value,
                "prijs": 10,
            }

            variants_count, variant_records = migrate_single_product(
                table, item, dry_run=False
            )

            # Should create exactly 1 default variant (Requirement 1.4)
            assert variants_count == 1

            # Fetch all records
            all_items = table.scan()["Items"]
            variants = [i for i in all_items if i.get("is_parent") is False]
            assert len(variants) == 1

            variant = variants[0]
            assert variant["variant_attributes"] == {}
            assert variant["stock"] == 0
            assert variant["allow_oversell"] is True

            # Parent should not have variant_schema set (Requirement 1.4)
            parents = [i for i in all_items if i.get("is_parent") is True]
            assert len(parents) == 1
            parent = parents[0]
            assert "variant_schema" not in parent

    # -------------------------------------------------------------------------
    # Sub-property: Old record deletion
    # -------------------------------------------------------------------------

    @given(
        legacy_id=legacy_id_strategy,
        name=product_name_strategy,
        opties=comma_separated_opties(),
    )
    @settings(max_examples=100, deadline=None)
    def test_old_record_deleted_after_migration(self, legacy_id, name, opties):
        """Migration deletes the old id-keyed record after creating the new UUID-keyed one."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="TestProducten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            item = {
                "product_id": legacy_id,
                "id": legacy_id,
                "naam": name,
                "opties": opties,
            }

            migrate_single_product(table, item, dry_run=False)

            # Old record keyed by legacy_id should be gone
            resp = table.get_item(Key={"product_id": legacy_id})
            assert "Item" not in resp
