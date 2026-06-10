"""
Property-Based Test for Seed Data Determinism (Idempotency)

Feature: test-staging-environment, Property 2: Seed data determinism

For any table's seed data config, calling the generation function multiple times
produces identical item sets (same keys, same attribute values) on every invocation,
ensuring that repeated script runs overwrite rather than duplicate.

**Validates: Requirements 6.3**
"""

import os
import sys

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
import importlib.util

_seed_module_path = os.path.join(_scripts_path, 'seed-test-data.py')
_spec = importlib.util.spec_from_file_location('seed_test_data', _seed_module_path)
seed_test_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_test_data)

generate_seed_data = seed_test_data.generate_seed_data


class TestProperty2SeedDataDeterminism:
    """
    Feature: test-staging-environment, Property 2: Seed data determinism

    **Validates: Requirements 6.3**
    """

    @given(num_invocations=st.integers(min_value=2, max_value=10))
    @settings(max_examples=100)
    def test_generate_seed_data_produces_identical_output_on_repeated_calls(
        self, num_invocations
    ):
        """
        For any number of invocations (2-10), calling generate_seed_data()
        multiple times always produces deeply equal results, proving idempotency.
        """
        results = [generate_seed_data() for _ in range(num_invocations)]

        # All results must be identical to the first
        first = results[0]
        for i in range(1, num_invocations):
            assert results[i] == first, (
                f"Invocation {i+1} produced different output than invocation 1. "
                f"Tables with differences: "
                f"{[t for t in first if first[t] != results[i].get(t)]}"
            )

    @given(num_invocations=st.integers(min_value=2, max_value=10))
    @settings(max_examples=100)
    def test_seed_data_table_keys_are_stable(self, num_invocations):
        """
        For any number of invocations, the set of table names returned by
        generate_seed_data() is always identical.
        """
        results = [generate_seed_data() for _ in range(num_invocations)]

        first_tables = set(results[0].keys())
        for i in range(1, num_invocations):
            assert set(results[i].keys()) == first_tables, (
                f"Invocation {i+1} returned different table names. "
                f"Expected: {first_tables}, Got: {set(results[i].keys())}"
            )

    @given(num_invocations=st.integers(min_value=2, max_value=10))
    @settings(max_examples=100)
    def test_seed_data_item_count_per_table_is_stable(self, num_invocations):
        """
        For any number of invocations, each table always contains the same
        number of items.
        """
        results = [generate_seed_data() for _ in range(num_invocations)]

        first = results[0]
        for table_name, items in first.items():
            for i in range(1, num_invocations):
                assert len(results[i][table_name]) == len(items), (
                    f"Table '{table_name}': invocation {i+1} has "
                    f"{len(results[i][table_name])} items, expected {len(items)}"
                )
