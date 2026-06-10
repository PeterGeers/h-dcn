"""
Property-Based Test for Seed Data Validity

Feature: test-staging-environment, Property 4: Seed data validity

For any item produced by the seed data generation function, the item SHALL contain
all mandatory attributes defined for its table schema, all identifier fields SHALL
contain a `test-` or `SEED-` prefix, and each table's seed set SHALL contain at
least 5 items with at least 2 distinct status values (where the table has a status field).

**Validates: Requirements 6.1, 6.4**
"""

import os
import sys
import importlib.util

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Add the scripts/ directory to sys.path so we can import the seed data module
_scripts_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')
)
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

# Import with a hyphenated filename requires importlib
_seed_module_path = os.path.join(_scripts_path, 'seed-test-data.py')
_spec = importlib.util.spec_from_file_location('seed_test_data', _seed_module_path)
seed_test_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_test_data)

generate_seed_data = seed_test_data.generate_seed_data
TEST_TABLES = seed_test_data.TEST_TABLES

# Tables that have a status field (determined from seed data structure)
TABLES_WITH_STATUS = {
    "Members-Test",
    "Producten-Test",
    "Orders-Test",
    "Payments-Test",
    "Events-Test",
    "Memberships-Test",
    "Carts-Test",
}

# Counters-Test is special: only ≥2 items required, no status field
COUNTERS_TABLE = "Counters-Test"

# Minimum items per table (Counters-Test needs ≥2, all others ≥5)
MIN_ITEMS_DEFAULT = 5
MIN_ITEMS_COUNTERS = 2


class TestProperty4SeedDataValidity:
    """
    Feature: test-staging-environment, Property 4: Seed data validity

    **Validates: Requirements 6.1, 6.4**
    """

    @given(
        table_index=st.sampled_from(range(len(TEST_TABLES)))
    )
    @settings(max_examples=100)
    def test_all_mandatory_attributes_present(self, table_index):
        """
        For any generated seed item, the partition key (mandatory attribute)
        must be present in every item of the table.
        """
        table_name, partition_key = TEST_TABLES[table_index]
        data = generate_seed_data()

        assert table_name in data, f"Table '{table_name}' missing from seed data"
        items = data[table_name]

        for i, item in enumerate(items):
            assert partition_key in item, (
                f"Table '{table_name}', item {i}: "
                f"missing mandatory partition key '{partition_key}'. "
                f"Item keys: {list(item.keys())}"
            )
            # Partition key must not be empty
            assert item[partition_key], (
                f"Table '{table_name}', item {i}: "
                f"partition key '{partition_key}' is empty/falsy"
            )

    @given(
        table_index=st.sampled_from(range(len(TEST_TABLES)))
    )
    @settings(max_examples=100)
    def test_all_ids_contain_seed_or_test_prefix(self, table_index):
        """
        For any generated seed item, all identifier fields (partition key and
        any field ending in '_id') must contain 'SEED-' or 'test-' prefix.
        """
        table_name, partition_key = TEST_TABLES[table_index]
        data = generate_seed_data()
        items = data[table_name]

        for i, item in enumerate(items):
            # Check partition key has correct prefix
            pk_value = str(item[partition_key])
            assert pk_value.startswith("SEED-") or pk_value.startswith("test-"), (
                f"Table '{table_name}', item {i}: "
                f"partition key '{partition_key}' value '{pk_value}' "
                f"does not start with 'SEED-' or 'test-'"
            )

            # Check all other *_id fields (string-valued) for correct prefix
            for key, value in item.items():
                if key == partition_key:
                    continue  # Already checked
                if key.endswith("_id") and isinstance(value, str):
                    assert value.startswith("SEED-") or value.startswith("test-"), (
                        f"Table '{table_name}', item {i}: "
                        f"ID field '{key}' value '{value}' "
                        f"does not start with 'SEED-' or 'test-'"
                    )

    @given(
        table_index=st.sampled_from(range(len(TEST_TABLES)))
    )
    @settings(max_examples=100)
    def test_tables_have_minimum_item_count(self, table_index):
        """
        Each table has at least 5 items (except Counters-Test which has ≥2).
        """
        table_name, _ = TEST_TABLES[table_index]
        data = generate_seed_data()
        items = data[table_name]

        if table_name == COUNTERS_TABLE:
            min_items = MIN_ITEMS_COUNTERS
        else:
            min_items = MIN_ITEMS_DEFAULT

        assert len(items) >= min_items, (
            f"Table '{table_name}' has {len(items)} items, "
            f"expected at least {min_items}"
        )

    @given(
        table_name=st.sampled_from(sorted(TABLES_WITH_STATUS))
    )
    @settings(max_examples=100)
    def test_tables_with_status_have_at_least_2_distinct_values(self, table_name):
        """
        Each table that has a status field contains at least 2 distinct
        status values across its seed items.
        """
        data = generate_seed_data()
        items = data[table_name]

        statuses = {item["status"] for item in items if "status" in item}

        assert len(statuses) >= 2, (
            f"Table '{table_name}' has only {len(statuses)} distinct status "
            f"value(s): {statuses}. Expected at least 2."
        )
