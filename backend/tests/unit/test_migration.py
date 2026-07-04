"""
Unit tests for scripts/migrate_club_to_registry_row.py

Tests: dry-run, idempotency, skip logic, pagination, validate, remove-old-fields,
producten migration, events migration.

Requirements: 11.1, 11.2, 11.4, 11.5, 11.6, 11.7, 11.8
"""

import json
import os
import sys
import pytest
import boto3
from decimal import Decimal
from unittest.mock import patch, MagicMock
from moto import mock_aws

# Ensure AWS env vars are set before any boto3 usage
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Add scripts directory so we can import the migration module
# When running from backend/, scripts/ is at ../../scripts relative to this file
_scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))
sys.path.insert(0, _scripts_path)

from migrate_club_to_registry_row import (
    migrate_orders,
    migrate_members,
    migrate_payments,
    migrate_producten,
    migrate_events,
    validate_table,
    run_validation,
    remove_old_fields_from_table,
    run_remove_old_fields,
    scan_all,
    load_registry_from_s3,
)

REGION = "eu-west-1"


# --- Test Registry Data ---

SAMPLE_REGISTRY: dict = {
    "100": {"club_id": "100", "club_name": "Riders Amsterdam", "logo_url": "https://s3.example.com/logo100.png"},
    "200": {"club_id": "200", "club_name": "Thunder Rotterdam", "logo_url": None},
    "300": {"club_id": "300", "club_name": "Eagles Den Haag", "logo_url": "https://s3.example.com/logo300.png"},
}


# --- Fixtures ---

@pytest.fixture
def orders_table():
    """Create a mocked Orders table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName="Orders-Test",
            KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def members_table():
    """Create a mocked Members table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName="Members-Test",
            KeySchema=[{"AttributeName": "member_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "member_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def payments_table():
    """Create a mocked Payments table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName="Payments-Test",
            KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "payment_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def producten_table():
    """Create a mocked Producten table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName="Producten-Test",
            KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "product_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def events_table():
    """Create a mocked Events table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName="Events-Test",
            KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


# --- Test: Dry-Run No Writes (Req 11.2) ---

class TestDryRunNoWrites:
    """Dry-run mode should log changes but not write to DynamoDB."""

    def test_dry_run_orders_no_writes(self, orders_table):
        """Put records with club_id, run migration with dry_run=True, verify records unchanged."""
        orders_table.put_item(Item={"order_id": "ord-1", "club_id": "100", "status": "draft"})
        orders_table.put_item(Item={"order_id": "ord-2", "club_id": "200", "status": "draft"})

        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=True)

        assert stats["scanned"] == 2
        assert stats["converted"] == 2

        # Verify records are unchanged — no registry_row_id added
        item1 = orders_table.get_item(Key={"order_id": "ord-1"})["Item"]
        item2 = orders_table.get_item(Key={"order_id": "ord-2"})["Item"]
        assert "registry_row_id" not in item1
        assert "registry_row_id" not in item2
        assert item1["club_id"] == "100"
        assert item2["club_id"] == "200"

    def test_dry_run_members_no_writes(self, members_table):
        """Members table should also not be modified during dry-run."""
        members_table.put_item(Item={"member_id": "mem-1", "club_id": "100"})

        stats = migrate_members(members_table, SAMPLE_REGISTRY, dry_run=True)

        assert stats["converted"] == 1
        item = members_table.get_item(Key={"member_id": "mem-1"})["Item"]
        assert "registry_row_id" not in item
        assert item["club_id"] == "100"


# --- Test: Idempotency (Req 11.5) ---

class TestIdempotency:
    """Records already having registry_row_id should not be modified on re-run."""

    def test_idempotency_orders(self, orders_table):
        """Records with registry_row_id are skipped without modification."""
        orders_table.put_item(Item={
            "order_id": "ord-already",
            "registry_row_id": "100",
            "registry_row_label": "Riders Amsterdam",
            "registry_row_logo_url": "https://s3.example.com/logo100.png",
            "club_id": "100",  # old field still present
        })

        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 1
        assert stats["skipped"] == 1
        assert stats["converted"] == 0

        # Verify nothing changed
        item = orders_table.get_item(Key={"order_id": "ord-already"})["Item"]
        assert item["registry_row_id"] == "100"
        assert item["registry_row_label"] == "Riders Amsterdam"

    def test_idempotency_members(self, members_table):
        """Members with registry_row_id are skipped."""
        members_table.put_item(Item={
            "member_id": "mem-done",
            "registry_row_id": "200",
            "club_id": "200",
        })

        stats = migrate_members(members_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 1
        assert stats["skipped"] == 1
        assert stats["converted"] == 0


# --- Test: Skip Missing S3 Entries (Req 11.4) ---

class TestSkipMissingS3Entries:
    """Records with club_id not found in registry should be migrated with fallback label."""

    def test_skip_missing_s3_entries_orders(self, orders_table):
        """club_id '999' is not in SAMPLE_REGISTRY → record is still migrated with fallback."""
        orders_table.put_item(Item={"order_id": "ord-unknown", "club_id": "999"})

        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 1
        assert stats["skipped"] == 0
        assert stats["converted"] == 1

        # Record should be migrated with club_id as label fallback
        item = orders_table.get_item(Key={"order_id": "ord-unknown"})["Item"]
        assert item["registry_row_id"] == "999"
        assert item["registry_row_label"] == "999"
        assert "club_id" not in item

    def test_skip_missing_s3_entries_payments(self, payments_table):
        """Payments with unknown club_id are still migrated with fallback."""
        payments_table.put_item(Item={"payment_id": "pay-1", "club_id": "888"})

        stats = migrate_payments(payments_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 1
        assert stats["skipped"] == 0
        assert stats["converted"] == 1


# --- Test: Pagination Handling (Req 11.6) ---

class TestPaginationHandling:
    """Ensure all records are processed even with pagination."""

    def test_pagination_handling(self, orders_table):
        """
        Mock LastEvaluatedKey to simulate pagination.
        We patch table.scan to return paginated results.
        """
        # Insert 5 records
        for i in range(5):
            orders_table.put_item(Item={
                "order_id": f"ord-page-{i}",
                "club_id": "100",
            })

        # Run migration — scan_all inside migrate_orders handles pagination natively
        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 5
        assert stats["converted"] == 5

        # Verify all records were migrated
        for i in range(5):
            item = orders_table.get_item(Key={"order_id": f"ord-page-{i}"})["Item"]
            assert item["registry_row_id"] == "100"
            assert item["registry_row_label"] == "Riders Amsterdam"

    def test_pagination_with_mocked_last_evaluated_key(self, orders_table):
        """
        Verify that the migration function handles LastEvaluatedKey by patching
        the table.scan method to simulate paginated responses.
        """
        # We patch table.scan to return two pages
        page1_items = [{"order_id": "ord-p1", "club_id": "100"}]
        page2_items = [{"order_id": "ord-p2", "club_id": "200"}]

        original_scan = orders_table.scan
        call_count = [0]

        def mock_scan(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "Items": page1_items,
                    "LastEvaluatedKey": {"order_id": "ord-p1"},
                }
            else:
                return {"Items": page2_items}

        with patch.object(orders_table, "scan", side_effect=mock_scan):
            stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["scanned"] == 2
        assert stats["converted"] == 2
        assert call_count[0] == 2


# --- Test: Validate Mode (Req 11.7) ---

class TestValidateMode:
    """Test --validate mode reports pass/fail correctly."""

    def test_validate_mode_pass(self, orders_table):
        """All records migrated → validation passes."""
        orders_table.put_item(Item={
            "order_id": "ord-ok-1",
            "registry_row_id": "100",
            "registry_row_label": "Riders Amsterdam",
        })
        orders_table.put_item(Item={
            "order_id": "ord-ok-2",
            "registry_row_id": "200",
            "registry_row_label": "Thunder Rotterdam",
        })

        result = validate_table(orders_table, "order_id", "Orders")

        assert result["passed"] is True
        assert result["total_checked"] == 2
        assert result["non_compliant"] == []

    def test_validate_mode_fail_missing_registry_row_id(self, orders_table):
        """Records without registry_row_id → validation fails."""
        orders_table.put_item(Item={"order_id": "ord-bad", "club_id": "100"})

        result = validate_table(orders_table, "order_id", "Orders")

        assert result["passed"] is False
        assert result["total_checked"] == 1
        assert len(result["non_compliant"]) == 1
        assert "ord-bad" in result["non_compliant"][0]

    def test_validate_mode_fail_has_club_id(self, orders_table):
        """Records with both registry_row_id and club_id → validation fails."""
        orders_table.put_item(Item={
            "order_id": "ord-both",
            "registry_row_id": "100",
            "club_id": "100",  # should have been removed
        })

        result = validate_table(orders_table, "order_id", "Orders")

        assert result["passed"] is False
        assert "still has club_id" in result["non_compliant"][0]


    def test_run_validation_all_tables(self):
        """Integration: run_validation across Orders, Members, Payments."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name=REGION)

            # Create all three tables
            orders = dynamodb.create_table(
                TableName="Orders-Test",
                KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            members = dynamodb.create_table(
                TableName="Members-Test",
                KeySchema=[{"AttributeName": "member_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "member_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            payments = dynamodb.create_table(
                TableName="Payments-Test",
                KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "payment_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )

            # All records have registry_row_id and no club_id
            orders.put_item(Item={"order_id": "o1", "registry_row_id": "100"})
            members.put_item(Item={"member_id": "m1", "registry_row_id": "100"})
            payments.put_item(Item={"payment_id": "p1", "registry_row_id": "100"})

            table_names = {
                "orders": "Orders-Test",
                "members": "Members-Test",
                "payments": "Payments-Test",
            }

            result = run_validation(dynamodb, table_names)
            assert result is True


# --- Test: Remove Old Fields (Req 11.8) ---

class TestRemoveOldFields:
    """After validation passes, old club_id fields are removed."""

    def test_remove_old_fields(self, orders_table):
        """club_id is removed from records that have it."""
        orders_table.put_item(Item={
            "order_id": "ord-cleanup",
            "registry_row_id": "100",
            "club_id": "100",
        })

        stats = remove_old_fields_from_table(orders_table, "order_id", "Orders", dry_run=False)

        assert stats["scanned"] == 1
        assert stats["converted"] == 1

        item = orders_table.get_item(Key={"order_id": "ord-cleanup"})["Item"]
        assert "club_id" not in item
        assert item["registry_row_id"] == "100"

    def test_remove_old_fields_skips_clean_records(self, orders_table):
        """Records without club_id are skipped."""
        orders_table.put_item(Item={
            "order_id": "ord-clean",
            "registry_row_id": "200",
        })

        stats = remove_old_fields_from_table(orders_table, "order_id", "Orders", dry_run=False)

        assert stats["scanned"] == 1
        assert stats["skipped"] == 1
        assert stats["converted"] == 0

    def test_remove_old_fields_dry_run(self, orders_table):
        """Dry-run mode does not actually remove fields."""
        orders_table.put_item(Item={
            "order_id": "ord-dryremove",
            "registry_row_id": "100",
            "club_id": "100",
        })

        stats = remove_old_fields_from_table(orders_table, "order_id", "Orders", dry_run=True)

        assert stats["converted"] == 1
        item = orders_table.get_item(Key={"order_id": "ord-dryremove"})["Item"]
        assert "club_id" in item  # still present


    def test_run_remove_old_fields_requires_validation(self):
        """run_remove_old_fields fails if validation does not pass first."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name=REGION)

            orders = dynamodb.create_table(
                TableName="Orders-Test",
                KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            members = dynamodb.create_table(
                TableName="Members-Test",
                KeySchema=[{"AttributeName": "member_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "member_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            payments = dynamodb.create_table(
                TableName="Payments-Test",
                KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "payment_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )

            # One record still has club_id and no registry_row_id → validation fails
            orders.put_item(Item={"order_id": "o1", "club_id": "100"})

            table_names = {
                "orders": "Orders-Test",
                "members": "Members-Test",
                "payments": "Payments-Test",
            }

            result = run_remove_old_fields(dynamodb, table_names, dry_run=False)
            assert result is False


# --- Test: Producten Migration (Req 5.6) ---

class TestProductenMigration:
    """purchase_rules.max_per_club → max_per_order, min_per_club → min_per_order."""

    def test_producten_migration_renames_fields(self, producten_table):
        """max_per_club and min_per_club are renamed to max_per_order and min_per_order."""
        producten_table.put_item(Item={
            "product_id": "prod-1",
            "purchase_rules": {
                "max_per_club": 5,
                "min_per_club": 1,
                "max_per_event": 50,
            },
        })

        stats = migrate_producten(producten_table, dry_run=False)

        assert stats["scanned"] == 1
        assert stats["converted"] == 1

        item = producten_table.get_item(Key={"product_id": "prod-1"})["Item"]
        rules = item["purchase_rules"]
        assert "max_per_order" in rules
        assert "min_per_order" in rules
        assert "max_per_club" not in rules
        assert "min_per_club" not in rules
        assert rules["max_per_order"] == 5
        assert rules["min_per_order"] == 1
        assert rules["max_per_event"] == 50

    def test_producten_migration_skips_already_migrated(self, producten_table):
        """Products without max_per_club/min_per_club are skipped."""
        producten_table.put_item(Item={
            "product_id": "prod-done",
            "purchase_rules": {
                "max_per_order": 10,
                "min_per_order": 2,
            },
        })

        stats = migrate_producten(producten_table, dry_run=False)

        assert stats["skipped"] == 1
        assert stats["converted"] == 0


    def test_producten_max_per_order_takes_precedence(self, producten_table):
        """If both max_per_club and max_per_order exist, max_per_order wins (Req 5.8)."""
        producten_table.put_item(Item={
            "product_id": "prod-both",
            "purchase_rules": {
                "max_per_club": 5,
                "max_per_order": 10,  # already has new field
            },
        })

        stats = migrate_producten(producten_table, dry_run=False)

        assert stats["converted"] == 1
        item = producten_table.get_item(Key={"product_id": "prod-both"})["Item"]
        rules = item["purchase_rules"]
        assert rules["max_per_order"] == 10  # preserved, not overwritten by max_per_club
        assert "max_per_club" not in rules

    def test_producten_no_purchase_rules(self, producten_table):
        """Products without purchase_rules are skipped."""
        producten_table.put_item(Item={"product_id": "prod-nope", "name": "Simple"})

        stats = migrate_producten(producten_table, dry_run=False)

        assert stats["skipped"] == 1
        assert stats["converted"] == 0

    def test_producten_dry_run(self, producten_table):
        """Dry-run does not modify producten records."""
        producten_table.put_item(Item={
            "product_id": "prod-dry",
            "purchase_rules": {"max_per_club": 3},
        })

        stats = migrate_producten(producten_table, dry_run=True)

        assert stats["converted"] == 1
        item = producten_table.get_item(Key={"product_id": "prod-dry"})["Item"]
        assert "max_per_club" in item["purchase_rules"]
        assert "max_per_order" not in item["purchase_rules"]


# --- Test: Events Migration ---

class TestEventsMigration:
    """order_scope removed, counting_rule renamed."""

    def test_events_remove_order_scope(self, events_table):
        """order_scope field is removed from events."""
        events_table.put_item(Item={
            "event_id": "evt-1",
            "order_scope": "club",
            "title": "Test Event",
        })

        stats = migrate_events(events_table, dry_run=False)

        assert stats["converted"] == 1
        item = events_table.get_item(Key={"event_id": "evt-1"})["Item"]
        assert "order_scope" not in item
        assert item["title"] == "Test Event"

    def test_events_rename_counting_rule(self, events_table):
        """counting_rule 'count_distinct_clubs' → 'count_distinct_rows'."""
        events_table.put_item(Item={
            "event_id": "evt-2",
            "constraints": [
                {"counting_rule": "count_distinct_clubs", "max_value": 10},
                {"counting_rule": "count_items_by_product", "max_value": 5},
            ],
        })

        stats = migrate_events(events_table, dry_run=False)

        assert stats["converted"] == 1
        item = events_table.get_item(Key={"event_id": "evt-2"})["Item"]
        constraints = item["constraints"]
        assert constraints[0]["counting_rule"] == "count_distinct_rows"
        assert constraints[1]["counting_rule"] == "count_items_by_product"

    def test_events_both_changes(self, events_table):
        """Event with both order_scope and counting_rule change."""
        events_table.put_item(Item={
            "event_id": "evt-3",
            "order_scope": "club",
            "constraints": [
                {"counting_rule": "count_distinct_clubs", "max_value": 3},
            ],
        })

        stats = migrate_events(events_table, dry_run=False)

        assert stats["converted"] == 1
        item = events_table.get_item(Key={"event_id": "evt-3"})["Item"]
        assert "order_scope" not in item
        assert item["constraints"][0]["counting_rule"] == "count_distinct_rows"


    def test_events_skip_clean_records(self, events_table):
        """Events without order_scope or old counting_rule are skipped."""
        events_table.put_item(Item={
            "event_id": "evt-clean",
            "title": "Clean Event",
            "constraints": [
                {"counting_rule": "count_items_by_product", "max_value": 5},
            ],
        })

        stats = migrate_events(events_table, dry_run=False)

        assert stats["skipped"] == 1
        assert stats["converted"] == 0

    def test_events_dry_run(self, events_table):
        """Dry-run does not modify event records."""
        events_table.put_item(Item={
            "event_id": "evt-dry",
            "order_scope": "club",
        })

        stats = migrate_events(events_table, dry_run=True)

        assert stats["converted"] == 1
        item = events_table.get_item(Key={"event_id": "evt-dry"})["Item"]
        assert "order_scope" in item  # still present


# --- Test: Full Migration Flow ---

class TestFullMigrationFlow:
    """End-to-end: actual writes, verify registry data is resolved."""

    def test_orders_migration_resolves_label_and_logo(self, orders_table):
        """Migrated orders get registry_row_id, label, and logo_url from registry."""
        orders_table.put_item(Item={"order_id": "ord-full", "club_id": "100"})

        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["converted"] == 1
        item = orders_table.get_item(Key={"order_id": "ord-full"})["Item"]
        assert item["registry_row_id"] == "100"
        assert item["registry_row_label"] == "Riders Amsterdam"
        assert item["registry_row_logo_url"] == "https://s3.example.com/logo100.png"


    def test_orders_migration_null_logo(self, orders_table):
        """When registry entry has logo_url=None, order stores None."""
        orders_table.put_item(Item={"order_id": "ord-nologo", "club_id": "200"})

        stats = migrate_orders(orders_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["converted"] == 1
        item = orders_table.get_item(Key={"order_id": "ord-nologo"})["Item"]
        assert item["registry_row_id"] == "200"
        assert item["registry_row_label"] == "Thunder Rotterdam"
        # DynamoDB doesn't store None values — the field is absent
        assert item.get("registry_row_logo_url") is None

    def test_members_migration_only_id(self, members_table):
        """Members get only registry_row_id — no label or logo."""
        members_table.put_item(Item={"member_id": "mem-full", "club_id": "300"})

        stats = migrate_members(members_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["converted"] == 1
        item = members_table.get_item(Key={"member_id": "mem-full"})["Item"]
        assert item["registry_row_id"] == "300"
        assert "registry_row_label" not in item
        assert "registry_row_logo_url" not in item

    def test_payments_migration_resolves_label_and_logo(self, payments_table):
        """Payments get registry_row_id, label, and logo_url."""
        payments_table.put_item(Item={"payment_id": "pay-full", "club_id": "300"})

        stats = migrate_payments(payments_table, SAMPLE_REGISTRY, dry_run=False)

        assert stats["converted"] == 1
        item = payments_table.get_item(Key={"payment_id": "pay-full"})["Item"]
        assert item["registry_row_id"] == "300"
        assert item["registry_row_label"] == "Eagles Den Haag"
        assert item["registry_row_logo_url"] == "https://s3.example.com/logo300.png"
