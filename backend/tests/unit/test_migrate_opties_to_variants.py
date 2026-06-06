"""
Unit tests for the opties-to-variants migration script.

Tests the pure logic functions: parsing, variant generation,
idempotency detection, and schema building.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws
import boto3

# Add scripts directory to path so we can import the migration module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from migrate_opties_to_variants import (
    parse_opties,
    build_variant_schema,
    generate_variant_records,
    is_already_migrated,
    has_opties_field,
    create_log_entry,
)


class TestParseOpties:
    """Tests for parse_opties function."""

    def test_simple_csv(self):
        result = parse_opties("S, M, L")
        assert result == ["S", "M", "L"]

    def test_no_spaces(self):
        result = parse_opties("S,M,L")
        assert result == ["S", "M", "L"]

    def test_extra_spaces(self):
        result = parse_opties("  S ,  M  ,  L  ")
        assert result == ["S", "M", "L"]

    def test_single_value(self):
        result = parse_opties("OneSize")
        assert result == ["OneSize"]

    def test_empty_string(self):
        result = parse_opties("")
        assert result == []

    def test_none(self):
        result = parse_opties(None)
        assert result == []

    def test_whitespace_only(self):
        result = parse_opties("   ")
        assert result == []

    def test_trailing_comma(self):
        result = parse_opties("S, M, L,")
        assert result == ["S", "M", "L"]

    def test_double_comma(self):
        result = parse_opties("S,,M,L")
        assert result == ["S", "M", "L"]

    def test_real_product_opties(self):
        """Test with realistic H-DCN product opties."""
        result = parse_opties("S, M, L, XL, XXL")
        assert result == ["S", "M", "L", "XL", "XXL"]

    def test_dutch_options(self):
        result = parse_opties("Rood, Blauw, Groen")
        assert result == ["Rood", "Blauw", "Groen"]


class TestBuildVariantSchema:
    """Tests for build_variant_schema function."""

    def test_creates_single_axis(self):
        result = build_variant_schema(["S", "M", "L"])
        assert result == {"opties": ["S", "M", "L"]}

    def test_preserves_order(self):
        result = build_variant_schema(["XL", "S", "M"])
        assert result == {"opties": ["XL", "S", "M"]}

    def test_single_value(self):
        result = build_variant_schema(["OneSize"])
        assert result == {"opties": ["OneSize"]}


class TestGenerateVariantRecords:
    """Tests for generate_variant_records function."""

    def test_generates_correct_count(self):
        variants = generate_variant_records(
            "prod_abc", "h-dcn", ["S", "M", "L"], "2024-01-01T00:00:00+00:00"
        )
        assert len(variants) == 3

    def test_variant_structure(self):
        variants = generate_variant_records(
            "prod_abc", "h-dcn", ["S"], "2024-01-01T00:00:00+00:00"
        )
        v = variants[0]
        assert v["product_id"] == "var_prod_abc_s"
        assert v["is_parent"] is False
        assert v["parent_id"] == "prod_abc"
        assert v["tenant"] == "h-dcn"
        assert v["variant_attributes"] == {"opties": "S"}
        assert v["stock"] == 0
        assert v["sold_count"] == 0
        assert v["allow_oversell"] is True
        assert v["active"] is True
        assert v["source"] == "opties_migration"

    def test_variant_ids_are_sanitized(self):
        variants = generate_variant_records(
            "prod_abc", "h-dcn", ["XL", "XXL"], "2024-01-01T00:00:00+00:00"
        )
        assert variants[0]["product_id"] == "var_prod_abc_xl"
        assert variants[1]["product_id"] == "var_prod_abc_xxl"

    def test_variant_ids_handle_spaces(self):
        variants = generate_variant_records(
            "prod_abc", "h-dcn", ["Extra Large"], "2024-01-01T00:00:00+00:00"
        )
        assert variants[0]["product_id"] == "var_prod_abc_extra_large"

    def test_inherits_tenant(self):
        variants = generate_variant_records(
            "prod_abc", "presmeet", ["A", "B"], "2024-01-01T00:00:00+00:00"
        )
        assert all(v["tenant"] == "presmeet" for v in variants)


class TestIsAlreadyMigrated:
    """Tests for is_already_migrated function."""

    def test_not_migrated(self):
        product = {"product_id": "prod_1", "opties": "S,M,L"}
        all_items = [product]
        migrated, reason = is_already_migrated(product, all_items)
        assert migrated is False
        assert reason == ""

    def test_has_legacy_opties(self):
        product = {"product_id": "prod_1", "legacy_opties": "S,M,L"}
        all_items = [product]
        migrated, reason = is_already_migrated(product, all_items)
        assert migrated is True
        assert "legacy_opties" in reason

    def test_has_existing_variants(self):
        product = {"product_id": "prod_1", "opties": "S,M,L"}
        variant = {
            "product_id": "var_prod_1_s",
            "parent_id": "prod_1",
            "is_parent": False,
        }
        all_items = [product, variant]
        migrated, reason = is_already_migrated(product, all_items)
        assert migrated is True
        assert "variant records" in reason

    def test_variant_for_different_parent_doesnt_count(self):
        product = {"product_id": "prod_1", "opties": "S,M,L"}
        variant = {
            "product_id": "var_prod_2_s",
            "parent_id": "prod_2",
            "is_parent": False,
        }
        all_items = [product, variant]
        migrated, reason = is_already_migrated(product, all_items)
        assert migrated is False


class TestHasOptiesField:
    """Tests for has_opties_field function."""

    def test_has_opties(self):
        assert has_opties_field({"product_id": "p1", "opties": "S,M,L"}) is True

    def test_no_opties(self):
        assert has_opties_field({"product_id": "p1"}) is False

    def test_none_opties(self):
        assert has_opties_field({"product_id": "p1", "opties": None}) is False

    def test_empty_opties(self):
        assert has_opties_field({"product_id": "p1", "opties": ""}) is False

    def test_whitespace_opties(self):
        assert has_opties_field({"product_id": "p1", "opties": "   "}) is False


class TestCreateLogEntry:
    """Tests for create_log_entry function."""

    def test_success_entry(self):
        entry = create_log_entry("prod_1", "S,M,L", 3, "success")
        assert entry["product_id"] == "prod_1"
        assert entry["original_opties"] == "S,M,L"
        assert entry["variant_count"] == 3
        assert entry["status"] == "success"
        assert "timestamp" in entry
        assert "reason" not in entry

    def test_skipped_entry_with_reason(self):
        entry = create_log_entry("prod_1", "S,M,L", 0, "skipped", "has legacy_opties field")
        assert entry["status"] == "skipped"
        assert entry["reason"] == "has legacy_opties field"


class TestMigrateIntegration:
    """Integration test using moto to mock DynamoDB."""

    @pytest.fixture
    def producten_table(self):
        """Create a mocked Producten table."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"},
                    {"AttributeName": "parent_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "parent_id-index",
                        "KeySchema": [{"AttributeName": "parent_id", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.meta.client.get_waiter("table_exists").wait(TableName="Producten")
            yield table

    def test_full_migration_flow(self, producten_table):
        """Test complete migration: scan → parse → create variants → update parent."""
        # Seed a product with opties
        producten_table.put_item(
            Item={
                "product_id": "prod_shirt",
                "is_parent": True,
                "tenant": "h-dcn",
                "name": "Club T-shirt",
                "opties": "S, M, L, XL",
                "active": True,
            }
        )

        # Patch get_table to return our mock table
        with patch(
            "migrate_opties_to_variants.get_table", return_value=producten_table
        ):
            from migrate_opties_to_variants import migrate

            result = migrate(profile=None, dry_run=False)

        assert result["successful"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0

        # Verify parent was updated
        parent = producten_table.get_item(Key={"product_id": "prod_shirt"})["Item"]
        assert parent["variant_schema"] == {"opties": ["S", "M", "L", "XL"]}
        assert parent["legacy_opties"] == "S, M, L, XL"
        assert "opties" not in parent

        # Verify variants were created
        for size in ["s", "m", "l", "xl"]:
            variant_id = f"var_prod_shirt_{size}"
            resp = producten_table.get_item(Key={"product_id": variant_id})
            assert "Item" in resp
            variant = resp["Item"]
            assert variant["parent_id"] == "prod_shirt"
            assert variant["stock"] == 0
            assert variant["allow_oversell"] is True

    def test_idempotent_second_run(self, producten_table):
        """Test that running migration twice skips already-migrated products."""
        # Seed a product that was already migrated
        producten_table.put_item(
            Item={
                "product_id": "prod_migrated",
                "is_parent": True,
                "tenant": "h-dcn",
                "name": "Already Migrated",
                "opties": "S, M, L",
                "legacy_opties": "S, M, L",
                "variant_schema": {"opties": ["S", "M", "L"]},
                "active": True,
            }
        )

        with patch(
            "migrate_opties_to_variants.get_table", return_value=producten_table
        ):
            from migrate_opties_to_variants import migrate

            result = migrate(profile=None, dry_run=False)

        # Should skip because legacy_opties already present
        assert result["successful"] == 0
        assert result["skipped"] == 1

    def test_skips_product_with_existing_variants(self, producten_table):
        """Test that products with existing variant records are skipped."""
        producten_table.put_item(
            Item={
                "product_id": "prod_has_variants",
                "is_parent": True,
                "tenant": "h-dcn",
                "opties": "S, M",
                "active": True,
            }
        )
        producten_table.put_item(
            Item={
                "product_id": "var_prod_has_variants_s",
                "parent_id": "prod_has_variants",
                "is_parent": False,
                "tenant": "h-dcn",
                "variant_attributes": {"opties": "S"},
            }
        )

        with patch(
            "migrate_opties_to_variants.get_table", return_value=producten_table
        ):
            from migrate_opties_to_variants import migrate

            result = migrate(profile=None, dry_run=False)

        assert result["successful"] == 0
        assert result["skipped"] == 1
