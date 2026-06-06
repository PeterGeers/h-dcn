"""
Unit tests for the presmeet config migration script.

Tests the pure logic functions: attribute mapping, purchase rules building,
conversion, idempotency detection, and DynamoDB integration with moto.
"""

import sys
import os
import pytest
from unittest.mock import patch
from decimal import Decimal
from moto import mock_aws
import boto3

# Add scripts directory to path so we can import the migration module
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
)

from migrate_presmeet_config import (
    map_required_attributes,
    build_purchase_rules,
    convert_record,
    is_already_migrated,
    scan_presmeet_config_records,
    migrate,
)


class TestMapRequiredAttributes:
    """Tests for map_required_attributes function."""

    def test_enum_attributes_become_variant_schema(self):
        required_attributes = {
            "gender": {
                "type": "string",
                "required": True,
                "enum": ["male", "female"],
            },
            "size": {
                "type": "string",
                "required": True,
                "enum": ["S", "M", "L", "XL"],
            },
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert variant_schema == {
            "gender": ["male", "female"],
            "size": ["S", "M", "L", "XL"],
        }
        assert order_item_fields == []

    def test_text_attributes_become_order_item_fields(self):
        required_attributes = {
            "name": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
            "role": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert variant_schema == {}
        assert len(order_item_fields) == 2

        name_field = next(f for f in order_item_fields if f["id"] == "name")
        assert name_field["label"] == "Name"
        assert name_field["type"] == "text"
        assert name_field["required"] is True
        assert name_field["validation"] == {
            "min_length": 1,
            "max_length": 100,
        }

    def test_integer_attributes_become_number_fields(self):
        required_attributes = {
            "persons": {
                "type": "integer",
                "required": True,
                "minimum": 1,
                "maximum": 50,
            },
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert variant_schema == {}
        assert len(order_item_fields) == 1
        field = order_item_fields[0]
        assert field["id"] == "persons"
        assert field["type"] == "number"
        assert field["validation"] == {"minimum": 1, "maximum": 50}

    def test_mixed_attributes(self):
        """Test the tshirt case: enum + text attributes."""
        required_attributes = {
            "name": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
            "gender": {
                "type": "string",
                "required": True,
                "enum": ["male", "female"],
            },
            "size": {
                "type": "string",
                "required": True,
                "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
            },
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert "gender" in variant_schema
        assert "size" in variant_schema
        assert len(order_item_fields) == 1
        assert order_item_fields[0]["id"] == "name"

    def test_empty_enum_treated_as_text(self):
        required_attributes = {
            "field": {"type": "string", "required": True, "enum": []},
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert variant_schema == {}
        assert len(order_item_fields) == 1

    def test_non_dict_attr_def_is_skipped(self):
        required_attributes = {
            "bad_field": "not a dict",
            "good_field": {"type": "string", "required": True},
        }
        variant_schema, order_item_fields = map_required_attributes(
            required_attributes
        )
        assert variant_schema == {}
        assert len(order_item_fields) == 1
        assert order_item_fields[0]["id"] == "good_field"

    def test_no_validation_when_no_constraints(self):
        required_attributes = {
            "date": {"type": "string", "required": True},
        }
        _, order_item_fields = map_required_attributes(required_attributes)
        assert "validation" not in order_item_fields[0]


class TestBuildPurchaseRules:
    """Tests for build_purchase_rules function."""

    def test_both_min_and_max(self):
        item = {"max_per_club": 13, "min_per_club": 1}
        rules = build_purchase_rules(item)
        assert rules == {
            "max_per_club": 13,
            "min_per_club": 1,
            "order_mode": "persistent",
        }

    def test_zero_min_per_club(self):
        item = {"max_per_club": 20, "min_per_club": 0}
        rules = build_purchase_rules(item)
        assert rules["min_per_club"] == 0
        assert rules["max_per_club"] == 20

    def test_only_max_per_club(self):
        item = {"max_per_club": 5}
        rules = build_purchase_rules(item)
        assert "max_per_club" in rules
        assert "min_per_club" not in rules
        assert rules["order_mode"] == "persistent"

    def test_no_constraints(self):
        item = {}
        rules = build_purchase_rules(item)
        assert rules == {"order_mode": "persistent"}

    def test_decimal_values_converted_to_int(self):
        item = {"max_per_club": Decimal("13"), "min_per_club": Decimal("0")}
        rules = build_purchase_rules(item)
        assert rules["max_per_club"] == 13
        assert isinstance(rules["max_per_club"], int)


class TestIsAlreadyMigrated:
    """Tests for is_already_migrated function."""

    def test_not_migrated(self):
        item = {
            "product_id": "config_presmeet_ticket",
            "source": "presmeet_config",
        }
        assert is_already_migrated(item) is False

    def test_already_has_variant_schema(self):
        item = {
            "product_id": "config_presmeet_ticket",
            "is_parent": True,
            "variant_schema": {"size": ["S", "M"]},
        }
        assert is_already_migrated(item) is True

    def test_already_has_order_item_fields(self):
        item = {
            "product_id": "config_presmeet_ticket",
            "is_parent": True,
            "order_item_fields": [{"id": "name", "type": "text"}],
        }
        assert is_already_migrated(item) is True

    def test_already_has_legacy_required_attributes(self):
        item = {
            "product_id": "config_presmeet_ticket",
            "is_parent": True,
            "legacy_required_attributes": {"name": {"type": "string"}},
        }
        assert is_already_migrated(item) is True

    def test_is_parent_false_not_migrated(self):
        """Even with variant_schema, if is_parent is False it's not migrated."""
        item = {
            "product_id": "config_presmeet_ticket",
            "is_parent": False,
            "variant_schema": {"size": ["S", "M"]},
        }
        assert is_already_migrated(item) is False


class TestConvertRecord:
    """Tests for convert_record function."""

    def test_meeting_ticket_conversion(self):
        """Test the meeting_ticket config from seed data."""
        item = {
            "product_id": "config_presmeet_meeting_ticket",
            "product_type": "meeting_ticket",
            "source": "presmeet_config",
            "max_per_club": 3,
            "min_per_club": 1,
            "unit_price": Decimal("50.00"),
            "required_attributes": {
                "name": {
                    "type": "string",
                    "required": True,
                    "min_length": 1,
                    "max_length": 100,
                },
                "role": {
                    "type": "string",
                    "required": True,
                    "min_length": 1,
                    "max_length": 100,
                },
            },
        }
        update_fields, error = convert_record(item)
        assert error is None
        assert update_fields["is_parent"] is True
        assert update_fields["tenant"] == "presmeet"
        assert update_fields["active"] is True
        assert update_fields["name"] == "Meeting ticket"
        assert update_fields["price"] == Decimal("50.00")
        # No enum attrs → no variant_schema
        assert "variant_schema" not in update_fields
        # Text attrs → order_item_fields
        assert len(update_fields["order_item_fields"]) == 2
        # Purchase rules
        assert update_fields["purchase_rules"]["max_per_club"] == 3
        assert update_fields["purchase_rules"]["min_per_club"] == 1
        assert update_fields["purchase_rules"]["order_mode"] == "persistent"
        # Legacy preservation
        assert update_fields["legacy_required_attributes"] == item[
            "required_attributes"
        ]

    def test_tshirt_conversion(self):
        """Test the tshirt config (has enum attrs → variant_schema)."""
        item = {
            "product_id": "config_presmeet_tshirt",
            "product_type": "tshirt",
            "source": "presmeet_config",
            "max_per_club": 13,
            "min_per_club": 0,
            "unit_price": Decimal("25.00"),
            "required_attributes": {
                "name": {
                    "type": "string",
                    "required": True,
                    "min_length": 1,
                    "max_length": 100,
                },
                "gender": {
                    "type": "string",
                    "required": True,
                    "enum": ["male", "female"],
                },
                "size": {
                    "type": "string",
                    "required": True,
                    "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
                },
            },
        }
        update_fields, error = convert_record(item)
        assert error is None
        assert update_fields["variant_schema"] == {
            "gender": ["male", "female"],
            "size": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
        }
        assert len(update_fields["order_item_fields"]) == 1
        assert update_fields["order_item_fields"][0]["id"] == "name"

    def test_missing_required_attributes(self):
        item = {"product_id": "config_presmeet_bad"}
        update_fields, error = convert_record(item)
        assert update_fields is None
        assert "No required_attributes" in error

    def test_invalid_required_attributes_type(self):
        item = {
            "product_id": "config_presmeet_bad",
            "required_attributes": "not a dict",
        }
        update_fields, error = convert_record(item)
        assert update_fields is None
        assert "not a dict" in error

    def test_too_many_combinations_rejected(self):
        """Config with >100 variant combinations should fail."""
        # 11 values × 11 values = 121 > 100
        item = {
            "product_id": "config_presmeet_huge",
            "required_attributes": {
                "axis1": {
                    "type": "string",
                    "enum": [f"v{i}" for i in range(11)],
                },
                "axis2": {
                    "type": "string",
                    "enum": [f"w{i}" for i in range(11)],
                },
            },
        }
        update_fields, error = convert_record(item)
        assert update_fields is None
        assert "121" in error
        assert "max 100" in error


class TestMigrateIntegration:
    """Integration tests using moto to mock DynamoDB."""

    @pytest.fixture
    def producten_table(self):
        """Create a mocked Producten table."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[
                    {"AttributeName": "product_id", "KeyType": "HASH"}
                ],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.meta.client.get_waiter("table_exists").wait(
                TableName="Producten"
            )
            yield table

    def test_full_migration_flow(self, producten_table):
        """Test complete migration with the meeting_ticket config."""
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_meeting_ticket",
                "product_type": "meeting_ticket",
                "source": "presmeet_config",
                "max_per_club": 3,
                "min_per_club": 1,
                "unit_price": Decimal("50.00"),
                "required_attributes": {
                    "name": {
                        "type": "string",
                        "required": True,
                        "min_length": 1,
                        "max_length": 100,
                    },
                    "role": {
                        "type": "string",
                        "required": True,
                        "min_length": 1,
                        "max_length": 100,
                    },
                },
            }
        )

        with patch(
            "migrate_presmeet_config.get_table",
            return_value=producten_table,
        ):
            migrate(profile=None, dry_run=False)

        # Verify the record was updated
        resp = producten_table.get_item(
            Key={"product_id": "config_presmeet_meeting_ticket"}
        )
        item = resp["Item"]
        assert item["is_parent"] is True
        assert item["tenant"] == "presmeet"
        assert item["active"] is True
        assert item["name"] == "Meeting ticket"
        assert item["price"] == Decimal("50.00")
        # No enum → no variant_schema
        assert "variant_schema" not in item
        # order_item_fields from text attrs
        assert len(item["order_item_fields"]) == 2
        # purchase_rules
        assert item["purchase_rules"]["max_per_club"] == 3
        assert item["purchase_rules"]["min_per_club"] == 1
        assert item["purchase_rules"]["order_mode"] == "persistent"
        # Legacy preserved
        assert "legacy_required_attributes" in item
        assert "name" in item["legacy_required_attributes"]

    def test_idempotent_second_run(self, producten_table):
        """Test that running migration twice skips already-migrated records."""
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_tshirt",
                "product_type": "tshirt",
                "source": "presmeet_config",
                "is_parent": True,
                "max_per_club": 13,
                "min_per_club": 0,
                "legacy_required_attributes": {"gender": {"enum": ["m"]}},
                "variant_schema": {"gender": ["male", "female"]},
                "purchase_rules": {
                    "max_per_club": 13,
                    "order_mode": "persistent",
                },
                "required_attributes": {
                    "name": {"type": "string", "required": True},
                    "gender": {"type": "string", "enum": ["male", "female"]},
                },
            }
        )

        with patch(
            "migrate_presmeet_config.get_table",
            return_value=producten_table,
        ):
            migrate(profile=None, dry_run=False)

        # Record should be unchanged (skipped)
        resp = producten_table.get_item(
            Key={"product_id": "config_presmeet_tshirt"}
        )
        item = resp["Item"]
        # Should still have the original variant_schema (not regenerated)
        assert item["variant_schema"] == {"gender": ["male", "female"]}

    def test_dry_run_does_not_modify(self, producten_table):
        """Test that --dry-run doesn't write to DynamoDB."""
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_ticket",
                "product_type": "ticket",
                "source": "presmeet_config",
                "max_per_club": 5,
                "required_attributes": {
                    "name": {"type": "string", "required": True},
                },
            }
        )

        with patch(
            "migrate_presmeet_config.get_table",
            return_value=producten_table,
        ):
            migrate(profile=None, dry_run=True)

        # Record should NOT have been updated
        resp = producten_table.get_item(
            Key={"product_id": "config_presmeet_ticket"}
        )
        item = resp["Item"]
        assert "is_parent" not in item
        assert "tenant" not in item
        assert "legacy_required_attributes" not in item

    def test_skips_non_presmeet_records(self, producten_table):
        """Non config_presmeet_ records should not be touched."""
        producten_table.put_item(
            Item={
                "product_id": "prod_regular_product",
                "is_parent": True,
                "name": "Regular Product",
            }
        )
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_ticket",
                "product_type": "ticket",
                "source": "presmeet_config",
                "max_per_club": 3,
                "required_attributes": {
                    "name": {"type": "string", "required": True},
                },
            }
        )

        with patch(
            "migrate_presmeet_config.get_table",
            return_value=producten_table,
        ):
            migrate(profile=None, dry_run=False)

        # Regular product untouched
        resp = producten_table.get_item(
            Key={"product_id": "prod_regular_product"}
        )
        item = resp["Item"]
        assert "tenant" not in item
        assert "legacy_required_attributes" not in item

    def test_continues_on_failure(self, producten_table):
        """Script should skip failed records and continue processing."""
        # One bad record (missing required_attributes)
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_bad",
                "product_type": "bad",
                "source": "presmeet_config",
            }
        )
        # One good record
        producten_table.put_item(
            Item={
                "product_id": "config_presmeet_good",
                "product_type": "good",
                "source": "presmeet_config",
                "max_per_club": 5,
                "required_attributes": {
                    "name": {"type": "string", "required": True},
                },
            }
        )

        with patch(
            "migrate_presmeet_config.get_table",
            return_value=producten_table,
        ):
            migrate(profile=None, dry_run=False)

        # Good record should be migrated
        resp = producten_table.get_item(
            Key={"product_id": "config_presmeet_good"}
        )
        item = resp["Item"]
        assert item["is_parent"] is True
        assert item["tenant"] == "presmeet"

        # Bad record should be unchanged
        resp = producten_table.get_item(
            Key={"product_id": "config_presmeet_bad"}
        )
        item = resp["Item"]
        assert "is_parent" not in item
