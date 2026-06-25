"""
Property-Based Tests for Migration: Remove event_id from Products (Properties 4 & 5).

**Validates: Requirements 8.1, 8.2, 8.4**

Property 4: Migration dry-run preserves all data.
For any set of product records in DynamoDB (some with event_id/event_ids, some without),
running the migration script with --dry-run SHALL leave all records completely unchanged.

Property 5: Migration removes event_id and event_ids from all records.
For any set of product records in DynamoDB that contain event_id and/or event_ids attributes,
running the migration script (without --dry-run) SHALL result in zero records containing
either attribute, regardless of table size or pagination boundaries.
"""

import importlib.util
import os
import sys
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# =============================================================================
# Load the migration script using importlib.util
# =============================================================================

_script_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'scripts',
        'migrate_remove_event_id_from_products.py'
    )
)


def _load_migration_module():
    """Load migration script module by file path, bypassing sys.path."""
    module_name = 'migrate_remove_event_id_from_products'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _script_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for product IDs
product_id_strategy = st.from_regex(r'prod_[a-z0-9]{8,16}', fullmatch=True)

# Strategy for event IDs (used as values in event_id field)
event_id_strategy = st.from_regex(r'evt_[a-z0-9]{8,12}', fullmatch=True)

# Strategy for event_ids list values
event_ids_strategy = st.lists(
    event_id_strategy,
    min_size=1,
    max_size=5,
    unique=True,
)

# Strategy for product names
product_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), max_codepoint=127),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != '')

# Strategy for a product record with event_id only
product_with_event_id = st.fixed_dictionaries({
    'product_id': product_id_strategy,
    'naam': product_name_strategy,
    'event_id': event_id_strategy,
})

# Strategy for a product record with event_ids only
product_with_event_ids = st.fixed_dictionaries({
    'product_id': product_id_strategy,
    'naam': product_name_strategy,
    'event_ids': event_ids_strategy,
})

# Strategy for a product record with both event_id and event_ids
product_with_both = st.fixed_dictionaries({
    'product_id': product_id_strategy,
    'naam': product_name_strategy,
    'event_id': event_id_strategy,
    'event_ids': event_ids_strategy,
})

# Strategy for a product record with neither event_id nor event_ids
product_without_event = st.fixed_dictionaries({
    'product_id': product_id_strategy,
    'naam': product_name_strategy,
})

# Combined strategy: a mix of all product types
any_product_record = st.one_of(
    product_with_event_id,
    product_with_event_ids,
    product_with_both,
    product_without_event,
)


def _create_producten_table(dynamodb):
    """Create the Producten DynamoDB table for testing."""
    return dynamodb.create_table(
        TableName='Producten',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'product_id', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _seed_table(table, records: list[dict]) -> None:
    """Insert product records into the table."""
    for record in records:
        table.put_item(Item=record)


def _scan_all_items(table) -> list[dict]:
    """Scan all items from a DynamoDB table, handling pagination."""
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    return items


def _run_migration(dry_run: bool) -> None:
    """Load and run the migration script's main() with mocked args."""
    module = _load_migration_module()

    # Patch argparse to supply our args and patch boto3.Session to use moto
    test_args = ['migrate_remove_event_id_from_products.py']
    if dry_run:
        test_args.append('--dry-run')

    with patch.object(sys, 'argv', test_args):
        with patch('migrate_remove_event_id_from_products.boto3.Session') as mock_session_cls:
            # Make the session return a moto-backed dynamodb resource
            mock_session = mock_session_cls.return_value
            mock_session.resource.return_value = boto3.resource('dynamodb', region_name='eu-west-1')
            module.main()


# =============================================================================
# Property 4: Migration dry-run preserves all data
# =============================================================================


class TestProperty4MigrationDryRunPreservesData:
    """
    # Feature: remove-event-id-from-products, Property 4: Migration dry-run preserves all data

    **Validates: Requirements 8.1**

    For any set of product records in DynamoDB (some with event_id/event_ids, some without),
    running the migration script with --dry-run SHALL leave all records completely unchanged.
    """

    @given(
        records=st.lists(any_product_record, min_size=1, max_size=15, unique_by=lambda r: r['product_id'])
    )
    @settings(max_examples=50, deadline=None)
    def test_dry_run_leaves_all_records_unchanged(self, records: list[dict]):
        """
        **Validates: Requirements 8.1**

        After a dry-run migration, every record in the table is identical to
        what was inserted — including event_id and event_ids fields.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = _create_producten_table(dynamodb)
            _seed_table(table, records)

            # Snapshot before migration
            before_items = _scan_all_items(table)
            before_map = {item['product_id']: item for item in before_items}

            # Run migration in dry-run mode
            _run_migration(dry_run=True)

            # Snapshot after migration
            after_items = _scan_all_items(table)
            after_map = {item['product_id']: item for item in after_items}

            # Same number of records
            assert len(after_map) == len(before_map), (
                f"Record count changed: {len(before_map)} → {len(after_map)}"
            )

            # Every record unchanged
            for pid, before_record in before_map.items():
                assert pid in after_map, f"Record {pid} disappeared after dry-run"
                after_record = after_map[pid]
                note(f"Checking record {pid}")
                assert before_record == after_record, (
                    f"Record {pid} was modified during dry-run.\n"
                    f"Before: {before_record}\n"
                    f"After:  {after_record}"
                )


# =============================================================================
# Property 5: Migration removes event_id and event_ids from all records
# =============================================================================


class TestProperty5MigrationRemovesEventIdFromAllRecords:
    """
    # Feature: remove-event-id-from-products, Property 5: Migration removes event_id and event_ids from all records

    **Validates: Requirements 8.2, 8.4**

    For any set of product records in DynamoDB that contain event_id and/or event_ids
    attributes, running the migration script (without --dry-run) SHALL result in zero
    records containing either attribute.
    """

    @given(
        records=st.lists(any_product_record, min_size=1, max_size=15, unique_by=lambda r: r['product_id'])
    )
    @settings(max_examples=50, deadline=None)
    def test_migration_removes_event_id_and_event_ids(self, records: list[dict]):
        """
        **Validates: Requirements 8.2, 8.4**

        After running migration (non-dry-run), no record in the table
        contains event_id or event_ids attributes.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = _create_producten_table(dynamodb)
            _seed_table(table, records)

            # Run migration (non-dry-run)
            _run_migration(dry_run=False)

            # Verify no record has event_id or event_ids
            after_items = _scan_all_items(table)
            for item in after_items:
                note(f"Checking record {item['product_id']}")
                assert 'event_id' not in item, (
                    f"Record {item['product_id']} still has event_id after migration"
                )
                assert 'event_ids' not in item, (
                    f"Record {item['product_id']} still has event_ids after migration"
                )

    @given(
        records=st.lists(any_product_record, min_size=1, max_size=15, unique_by=lambda r: r['product_id'])
    )
    @settings(max_examples=50, deadline=None)
    def test_migration_preserves_non_event_attributes(self, records: list[dict]):
        """
        **Validates: Requirements 8.2, 8.4**

        After running migration, all non-event attributes (product_id, naam, etc.)
        are preserved exactly as they were.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = _create_producten_table(dynamodb)
            _seed_table(table, records)

            # Snapshot before — strip event_id/event_ids for comparison
            before_map = {}
            for record in records:
                clean = {k: v for k, v in record.items() if k not in ('event_id', 'event_ids')}
                before_map[record['product_id']] = clean

            # Run migration (non-dry-run)
            _run_migration(dry_run=False)

            # Verify non-event attributes are unchanged
            after_items = _scan_all_items(table)
            after_map = {item['product_id']: item for item in after_items}

            assert len(after_map) == len(before_map), (
                f"Record count changed: {len(before_map)} → {len(after_map)}"
            )

            for pid, expected in before_map.items():
                assert pid in after_map, f"Record {pid} disappeared after migration"
                actual = {k: v for k, v in after_map[pid].items() if k not in ('event_id', 'event_ids')}
                assert actual == expected, (
                    f"Non-event attributes changed for {pid}.\n"
                    f"Expected: {expected}\n"
                    f"Actual:   {actual}"
                )

    @given(
        records_with_events=st.lists(
            st.one_of(product_with_event_id, product_with_event_ids, product_with_both),
            min_size=1,
            max_size=10,
            unique_by=lambda r: r['product_id'],
        ),
        records_without_events=st.lists(
            product_without_event,
            min_size=1,
            max_size=5,
            unique_by=lambda r: r['product_id'],
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_migration_handles_mixed_records(self, records_with_events: list[dict], records_without_events: list[dict]):
        """
        **Validates: Requirements 8.2, 8.4**

        Migration correctly handles a mix of records — those with event_id/event_ids
        have the fields removed, those without remain untouched.
        """
        # Ensure no duplicate product_ids across the two lists
        with_ids = {r['product_id'] for r in records_with_events}
        without_ids = {r['product_id'] for r in records_without_events}
        assume(with_ids.isdisjoint(without_ids))

        all_records = records_with_events + records_without_events

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = _create_producten_table(dynamodb)
            _seed_table(table, all_records)

            # Run migration
            _run_migration(dry_run=False)

            # Verify: no records have event_id or event_ids
            after_items = _scan_all_items(table)
            assert len(after_items) == len(all_records)

            for item in after_items:
                assert 'event_id' not in item
                assert 'event_ids' not in item

            # Records without events should be completely unchanged
            after_map = {item['product_id']: item for item in after_items}
            for record in records_without_events:
                assert after_map[record['product_id']] == record
