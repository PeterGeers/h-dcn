"""
Unit tests for the product model unification migration script.

Tests the pure logic functions: parse_opties, create_slug, slugify,
is_legacy_product detection, variant generation, and full migration flow.
"""

import sys
import os
import uuid
import pytest
from unittest.mock import patch
from moto import mock_aws
import boto3

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

from migrate_products import (
    parse_opties,
    create_slug,
    slugify,
    is_legacy_product,
    generate_variants,
    create_variant_record,
    migrate_single_product,
    migrate_products,
    MigrationSummary,
)


class TestSlugify:
    """Tests for slugify function."""

    def test_simple_text(self):
        assert slugify("T-shirt") == "t-shirt"

    def test_spaces_become_dashes(self):
        assert slugify("Club T Shirt") == "club-t-shirt"

    def test_special_chars_removed(self):
        assert slugify("Club (Special)!") == "club-special"

    def test_multiple_dashes_collapsed(self):
        assert slugify("a---b") == "a-b"

    def test_leading_trailing_stripped(self):
        assert slugify("  hello  ") == "hello"


class TestCreateSlug:
    """Tests for create_slug function."""

    def test_basic_slug(self):
        assert create_slug("G5", "T-shirt") == "G5-t-shirt"

    def test_with_spaces_in_name(self):
        assert create_slug("G10", "Club Polo") == "G10-club-polo"

    def test_empty_name(self):
        assert create_slug("G5", "") == "G5"

    def test_none_name(self):
        # name could be empty string from .get() with default
        assert create_slug("G5", "") == "G5"


class TestParseOpties:
    """Tests for parse_opties function."""

    def test_comma_separated(self):
        result = parse_opties("S,M,L,XL")
        assert result == {"Maat": ["S", "M", "L", "XL"]}

    def test_comma_separated_with_spaces(self):
        result = parse_opties("S, M, L, XL")
        assert result == {"Maat": ["S", "M", "L", "XL"]}

    def test_extra_whitespace(self):
        result = parse_opties("  S ,  M  ,  L  ")
        assert result == {"Maat": ["S", "M", "L"]}

    def test_one_size_returns_none(self):
        assert parse_opties("One Size") is None

    def test_one_size_case_insensitive(self):
        assert parse_opties("one size") is None
        assert parse_opties("ONE SIZE") is None

    def test_empty_string_returns_none(self):
        assert parse_opties("") is None

    def test_none_returns_none(self):
        assert parse_opties(None) is None

    def test_whitespace_only_returns_none(self):
        assert parse_opties("   ") is None

    def test_trailing_comma_filtered(self):
        result = parse_opties("S, M, L,")
        assert result == {"Maat": ["S", "M", "L"]}

    def test_double_comma_filtered(self):
        result = parse_opties("S,,M,L")
        assert result == {"Maat": ["S", "M", "L"]}

    def test_single_value(self):
        result = parse_opties("XL")
        assert result == {"Maat": ["XL"]}


class TestGenerateVariants:
    """Tests for generate_variants function."""

    def test_with_variant_schema(self):
        schema = {"Maat": ["S", "M", "L"]}
        parent_id = "test-uuid"
        variants = generate_variants(parent_id, schema)

        assert len(variants) == 3
        for v in variants:
            assert v["is_parent"] is False
            assert v["parent_id"] == parent_id
            assert v["stock"] == 0
            assert v["allow_oversell"] is True
            # product_id should be a valid UUID
            uuid.UUID(v["product_id"])

    def test_variant_attributes_correct(self):
        schema = {"Maat": ["S", "M"]}
        variants = generate_variants("parent-1", schema)

        attrs = [v["variant_attributes"] for v in variants]
        assert {"Maat": "S"} in attrs
        assert {"Maat": "M"} in attrs

    def test_none_schema_creates_default_variant(self):
        variants = generate_variants("parent-1", None)

        assert len(variants) == 1
        assert variants[0]["variant_attributes"] == {}
        assert variants[0]["is_parent"] is False
        assert variants[0]["parent_id"] == "parent-1"

    def test_each_variant_has_unique_uuid(self):
        schema = {"Maat": ["S", "M", "L", "XL"]}
        variants = generate_variants("parent-1", schema)
        ids = [v["product_id"] for v in variants]
        assert len(ids) == len(set(ids))


class TestIsLegacyProduct:
    """Tests for is_legacy_product function."""

    def test_legacy_product_detected(self):
        item = {"product_id": "G5", "opties": "S,M,L", "naam": "T-shirt"}
        assert is_legacy_product(item, [item]) is True

    def test_no_opties_not_legacy(self):
        item = {"product_id": "uuid-1", "name": "New Product"}
        assert is_legacy_product(item, [item]) is False

    def test_has_legacy_opties_skipped(self):
        item = {"product_id": "G5", "opties": "S,M,L", "legacy_opties": "S,M,L"}
        assert is_legacy_product(item, [item]) is False

    def test_has_legacy_id_skipped(self):
        item = {"product_id": "uuid-1", "opties": "S,M,L", "legacy_id": "G5"}
        assert is_legacy_product(item, [item]) is False

    def test_has_existing_variants_skipped(self):
        parent = {"product_id": "G5", "opties": "S,M,L"}
        variant = {"product_id": "var-1", "parent_id": "G5", "is_parent": False}
        assert is_legacy_product(parent, [parent, variant]) is False

    def test_variant_for_different_parent_not_blocking(self):
        parent = {"product_id": "G5", "opties": "S,M,L"}
        variant = {"product_id": "var-1", "parent_id": "G10", "is_parent": False}
        assert is_legacy_product(parent, [parent, variant]) is True


class TestMigrateIntegration:
    """Integration tests using moto to mock DynamoDB."""

    @pytest.fixture
    def producten_table(self):
        """Create a mocked Producten table with product_id as key."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.meta.client.get_waiter("table_exists").wait(TableName="Producten")

            # Also create Events and Carts tables (needed by channel→event_id step)
            dynamodb.create_table(
                TableName="Events",
                KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            dynamodb.create_table(
                TableName="Carts",
                KeySchema=[{"AttributeName": "cart_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "cart_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            dynamodb.create_table(
                TableName="Orders",
                KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "order_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            dynamodb.create_table(
                TableName="Payments",
                KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "payment_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            yield table

    def test_full_migration_of_legacy_product(self, producten_table):
        """Test migrating a legacy product with comma-separated opties."""
        # Seed a legacy product (product_id = legacy "G5")
        producten_table.put_item(
            Item={
                "product_id": "G5",
                "id": "G5",
                "naam": "Club T-shirt",
                "prijs": 25,
                "opties": "S, M, L, XL",
                "groep": "Kleding",
            }
        )

        # Migrate
        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            result = migrate_products(dry_run=False, profile=None, table_name="Producten")

        assert result.products_migrated == 1
        assert result.variants_created == 4
        assert result.products_skipped == 0
        assert len(result.errors) == 0

        # Old record should be deleted
        resp = producten_table.get_item(Key={"product_id": "G5"})
        assert "Item" not in resp

        # Find the new parent record (UUID-keyed)
        all_items = producten_table.scan()["Items"]
        parents = [i for i in all_items if i.get("is_parent") is True]
        assert len(parents) == 1

        parent = parents[0]
        # Verify UUID format
        uuid.UUID(parent["product_id"])
        assert parent["legacy_id"] == "G5"
        assert parent["slug"] == "G5-club-t-shirt"
        assert parent["is_parent"] is True
        assert parent["active"] is True
        assert parent["event_id"] is None
        assert parent["variant_schema"] == {"Maat": ["S", "M", "L", "XL"]}
        assert parent["legacy_opties"] == "S, M, L, XL"
        assert "opties" not in parent

        # Verify variant records
        variants = [i for i in all_items if i.get("is_parent") is False]
        assert len(variants) == 4
        for v in variants:
            assert v["parent_id"] == parent["product_id"]
            assert v["stock"] == 0
            assert v["allow_oversell"] is True

    def test_one_size_creates_default_variant(self, producten_table):
        """Test that 'One Size' opties creates a single Default_Variant."""
        producten_table.put_item(
            Item={
                "product_id": "G8",
                "naam": "Sticker",
                "opties": "One Size",
            }
        )

        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            result = migrate_products(dry_run=False, profile=None, table_name="Producten")

        assert result.products_migrated == 1
        assert result.variants_created == 1

        all_items = producten_table.scan()["Items"]
        variants = [i for i in all_items if i.get("is_parent") is False]
        assert len(variants) == 1
        assert variants[0]["variant_attributes"] == {}

    def test_idempotency_skips_migrated_products(self, producten_table):
        """Test that already-migrated products are skipped."""
        producten_table.put_item(
            Item={
                "product_id": "already-migrated-uuid",
                "legacy_id": "G5",
                "legacy_opties": "S,M,L",
                "is_parent": True,
                "naam": "Already Migrated",
                "variant_schema": {"Maat": ["S", "M", "L"]},
            }
        )

        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            result = migrate_products(dry_run=False, profile=None, table_name="Producten")

        assert result.products_migrated == 0
        assert result.products_skipped == 1

    def test_dry_run_makes_no_changes(self, producten_table):
        """Test that dry_run=True does not modify the table."""
        producten_table.put_item(
            Item={
                "product_id": "G5",
                "naam": "T-shirt",
                "opties": "S, M, L",
            }
        )

        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            result = migrate_products(dry_run=True, profile=None, table_name="Producten")

        assert result.products_migrated == 1
        assert result.variants_created == 3

        # Original record should still exist unchanged
        resp = producten_table.get_item(Key={"product_id": "G5"})
        assert "Item" in resp
        assert resp["Item"]["opties"] == "S, M, L"

    def test_error_handling_continues_processing(self, producten_table):
        """Test that errors on one product don't stop others."""
        # Two legacy products
        producten_table.put_item(
            Item={
                "product_id": "G1",
                "naam": "Product 1",
                "opties": "S, M",
            }
        )
        producten_table.put_item(
            Item={
                "product_id": "G2",
                "naam": "Product 2",
                "opties": "L, XL",
            }
        )

        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            # Patch migrate_single_product to fail on first call only
            original_migrate = migrate_single_product
            call_count = [0]

            def failing_migrate(table, item, dry_run):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise RuntimeError("Simulated DynamoDB error")
                return original_migrate(table, item, dry_run)

            with patch("migrate_products.migrate_single_product", side_effect=failing_migrate):
                result = migrate_products(dry_run=False, profile=None, table_name="Producten")

        assert result.products_migrated == 1
        assert len(result.errors) == 1
        assert "Simulated DynamoDB error" in result.errors[0]["error"]

    def test_skips_products_with_existing_variants(self, producten_table):
        """Products that already have variant children are skipped."""
        producten_table.put_item(
            Item={
                "product_id": "G5",
                "naam": "Has Variants",
                "opties": "S, M",
            }
        )
        producten_table.put_item(
            Item={
                "product_id": "var-existing",
                "parent_id": "G5",
                "is_parent": False,
                "variant_attributes": {"Maat": "S"},
            }
        )

        with patch(
            "migrate_products.get_dynamodb_resource"
        ) as mock_resource:
            mock_dynamo = boto3.resource("dynamodb", region_name="eu-west-1")
            mock_resource.return_value = mock_dynamo

            result = migrate_products(dry_run=False, profile=None, table_name="Producten")

        assert result.products_migrated == 0
        # 2 records scanned, both skipped
        assert result.products_skipped == 2
