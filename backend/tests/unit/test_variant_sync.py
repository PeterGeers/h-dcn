"""
Property-based tests for the variant sync module.

Uses Hypothesis to verify universal properties across randomized
variant schemas and variant records.

Feature: order-pipeline-improvements
"""

import pytest
import boto3
from decimal import Decimal
from functools import reduce
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from shared.variant_sync import (
    sync_schema_to_variants,
    sync_variant_to_schema,
    _compute_combinations,
    SyncResult,
    MaxCombinationsExceeded,
    MAX_COMBINATIONS,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Axis name strategy: simple ASCII alphabetic strings to avoid sanitization collisions
axis_name_st = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    min_size=1,
    max_size=8,
)

# Axis value strategy: ASCII alphanumeric strings
axis_value_st = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    min_size=1,
    max_size=6,
)

# A single axis: unique list of 1-5 values (unique after lowercasing to avoid ID collisions)
axis_values_st = st.lists(
    axis_value_st, min_size=1, max_size=5, unique_by=str.lower
)


@st.composite
def variant_schema_st(draw):
    """Generate a valid variant_schema with 1-3 axes, each with 1-5 unique values.
    Ensures the total combinations stay within MAX_COMBINATIONS (100)."""
    num_axes = draw(st.integers(min_value=1, max_value=3))
    # Generate unique axis names
    names = draw(
        st.lists(axis_name_st, min_size=num_axes, max_size=num_axes, unique=True)
    )
    schema = {}
    for name in names:
        values = draw(axis_values_st)
        schema[name] = values

    # Filter to ensure total combinations <= MAX_COMBINATIONS
    total = reduce(lambda a, b: a * b, (len(v) for v in schema.values()), 1)
    assume(total <= MAX_COMBINATIONS)
    assume(total > 0)

    return schema


@st.composite
def variant_attributes_st(draw, schema):
    """Generate a single variant_attributes dict from a given schema,
    picking one value per axis."""
    attrs = {}
    for axis, values in schema.items():
        attrs[axis] = draw(st.sampled_from(values))
    return attrs


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------

def _create_producten_table(dynamodb):
    """Create a mocked Producten table with the parent_id-index GSI."""
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
                "KeySchema": [
                    {"AttributeName": "parent_id", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return table


# ---------------------------------------------------------------------------
# Property 9: Variant generation produces correct count and structure
# Feature: order-pipeline-improvements, Property 9: Variant generation produces correct count and structure
# Validates: Requirements 4.1, 4.6, 4.7
# ---------------------------------------------------------------------------

@given(schema=variant_schema_st())
@settings(max_examples=200)
def test_property_9_variant_generation_correct_count_and_structure(schema):
    """For any valid variant_schema, the number of generated variant records
    SHALL equal the cartesian product of all axis value counts. Each variant
    SHALL have all axis keys and represent a unique combination."""
    # Compute expected count
    expected_count = reduce(lambda a, b: a * b, (len(v) for v in schema.values()), 1)

    # Call _compute_combinations directly
    combinations = _compute_combinations(schema)

    # Assert correct count
    assert len(combinations) == expected_count, (
        f"Expected {expected_count} combinations, got {len(combinations)} "
        f"for schema with axis sizes {[len(v) for v in schema.values()]}"
    )

    # Assert each combination has all axis keys
    axis_names = set(schema.keys())
    for combo in combinations:
        assert set(combo.keys()) == axis_names, (
            f"Combination {combo} missing axes. Expected {axis_names}"
        )

    # Assert each combination is unique
    combo_tuples = [tuple(sorted(c.items())) for c in combinations]
    assert len(set(combo_tuples)) == len(combinations), (
        "Not all combinations are unique"
    )

    # Assert each value in a combination is a valid value for that axis
    for combo in combinations:
        for axis, value in combo.items():
            assert value in schema[axis], (
                f"Value '{value}' not valid for axis '{axis}'. "
                f"Valid values: {schema[axis]}"
            )


# ---------------------------------------------------------------------------
# Property 10: Top-down schema sync preserves unchanged variant data
# Feature: order-pipeline-improvements, Property 10: Top-down schema sync preserves unchanged variant data
# Validates: Requirements 4.2
# ---------------------------------------------------------------------------

@given(schema=variant_schema_st(), stock=st.integers(min_value=1, max_value=999))
@settings(max_examples=200, deadline=None)
def test_property_10_topdown_sync_preserves_unchanged_variants(schema, stock):
    """For any existing set of variants and a new variant_schema, variants whose
    variant_attributes exist as a valid combination in BOTH the old and new schema
    SHALL retain their stock and price values unchanged after sync."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        table = _create_producten_table(dynamodb)

        parent_id = "prod_test_parent"
        parent_price = Decimal("29.99")
        custom_price = Decimal("35.50")

        # Step 1: Initial sync to create variants from schema
        sync_schema_to_variants(table, parent_id, schema, parent_price)

        # Step 2: Query all created variants and update their stock/price
        response = table.query(
            IndexName="parent_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("parent_id").eq(parent_id),
        )
        existing_variants = [
            v for v in response["Items"]
            if v.get("variant_attributes") and v.get("active", True)
        ]

        for variant in existing_variants:
            table.update_item(
                Key={"product_id": variant["product_id"]},
                UpdateExpression="SET stock = :s, price = :p",
                ExpressionAttributeValues={
                    ":s": stock,
                    ":p": custom_price,
                },
            )

        # Record how many variants actually exist (might be fewer than
        # combinations if ID collisions occur due to sanitization)
        num_existing = len(existing_variants)

        # Step 3: Re-sync with the SAME schema (all combinations overlap)
        result = sync_schema_to_variants(table, parent_id, schema, parent_price)

        # Step 4: All existing variants should be preserved (same schema, same attributes)
        assert result.preserved == num_existing, (
            f"Expected {num_existing} preserved, got {result.preserved}. "
            f"Created: {result.created}, Deactivated: {result.deactivated}"
        )

        # Step 5: Verify preserved variants retained their stock and price
        response = table.query(
            IndexName="parent_id-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("parent_id").eq(parent_id),
        )
        active_variants = [
            v for v in response["Items"]
            if v.get("active", True) and v.get("variant_attributes")
        ]

        for variant in active_variants:
            assert variant["stock"] == stock, (
                f"Stock should be {stock}, got {variant['stock']} "
                f"for variant {variant.get('variant_attributes')}"
            )
            assert variant["price"] == custom_price, (
                f"Price should be {custom_price}, got {variant['price']} "
                f"for variant {variant.get('variant_attributes')}"
            )


# ---------------------------------------------------------------------------
# Property 11: Bottom-up schema derivation reflects active variants
# Feature: order-pipeline-improvements, Property 11: Bottom-up schema derivation reflects active variants
# Validates: Requirements 4.3, 4.4
# ---------------------------------------------------------------------------

@given(schema=variant_schema_st())
@settings(max_examples=200, deadline=None)
def test_property_11_bottomup_schema_derivation_reflects_active_variants(schema):
    """For any set of active variant records belonging to a parent product,
    the derived variant_schema SHALL equal the union of all unique values per
    axis from the variant_attributes of those active variants."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        table = _create_producten_table(dynamodb)

        parent_id = "prod_test_parent"
        parent_price = Decimal("19.99")

        # Create the parent product record
        table.put_item(
            Item={
                "product_id": parent_id,
                "name": "Test Product",
                "is_parent": True,
                "active": True,
                "price": parent_price,
                "variant_schema": {},
            }
        )

        # Step 1: Create active variant records from the schema combinations
        combinations = _compute_combinations(schema)
        for i, combo in enumerate(combinations):
            table.put_item(
                Item={
                    "product_id": f"var_{parent_id}_{i}",
                    "parent_id": parent_id,
                    "is_parent": False,
                    "active": True,
                    "variant_attributes": combo,
                    "price": parent_price,
                    "stock": 0,
                    "allow_oversell": True,
                }
            )

        # Step 2: Pick one combination to pass as new variant_attributes
        # Use the first combination (it's already in the set)
        new_attrs = combinations[0]

        # Step 3: Call sync_variant_to_schema
        derived_schema = sync_variant_to_schema(table, parent_id, new_attrs)

        # Step 4: Verify derived schema matches the expected union of all values per axis
        # The expected schema should contain all unique values per axis from all
        # active variants plus the new_attrs (which is already in the set)
        expected_schema = {}
        for combo in combinations:
            for axis, value in combo.items():
                if axis not in expected_schema:
                    expected_schema[axis] = set()
                expected_schema[axis].add(value)
        for axis, value in new_attrs.items():
            if axis not in expected_schema:
                expected_schema[axis] = set()
            expected_schema[axis].add(value)

        # Compare: derived_schema should have same axes with same values (order doesn't matter)
        assert set(derived_schema.keys()) == set(expected_schema.keys()), (
            f"Schema axes mismatch. Expected {set(expected_schema.keys())}, "
            f"got {set(derived_schema.keys())}"
        )

        for axis in expected_schema:
            assert set(derived_schema[axis]) == expected_schema[axis], (
                f"Values mismatch for axis '{axis}'. "
                f"Expected {expected_schema[axis]}, got {set(derived_schema[axis])}"
            )
