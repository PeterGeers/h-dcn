"""
Variant sync module for bidirectional synchronization between
variant_schema (parent product) and variant records (children).

Provides two sync directions:
- Top-down: Admin edits variant_schema → regenerate variant records
- Bottom-up: Admin adds/removes variant → update parent's variant_schema

Uses DynamoDB parent_id-index GSI to query existing variants for a parent.
"""

import itertools
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from boto3.dynamodb.conditions import Key


logger = logging.getLogger(__name__)

# Maximum allowed combinations from cartesian product of schema axes
MAX_COMBINATIONS = 100


class MaxCombinationsExceeded(Exception):
    """Raised when variant_schema produces more than MAX_COMBINATIONS variants.

    The cartesian product of all axis values exceeds the allowed limit.
    """

    def __init__(self, count: int):
        self.count = count
        self.max = MAX_COMBINATIONS
        super().__init__(
            f"Too many variant combinations: {count} exceeds maximum of {MAX_COMBINATIONS}"
        )


@dataclass
class SyncResult:
    """Result of a top-down schema-to-variants sync operation.

    Attributes:
        created: Number of new variant records created.
        preserved: Number of existing variants that matched and were kept unchanged.
        deactivated: Number of variants that no longer match the schema and were set to active=false.
    """

    created: int
    preserved: int
    deactivated: int


def _sanitize_for_id(value: str) -> str:
    """Sanitize a value for use in a variant product_id.

    Lowercases, replaces spaces/special chars with underscores, and strips
    leading/trailing underscores.
    """
    sanitized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return sanitized.strip("_")


def _build_variant_id(parent_id: str, combination: tuple) -> str:
    """Build a deterministic variant product_id from parent_id and attribute values."""
    id_parts = [_sanitize_for_id(v) for v in combination]
    return f"var_{parent_id}_{'_'.join(id_parts)}"


def _build_variant_name(parent_name: str, combination: tuple) -> str:
    """Build a display name for a variant like 'T-shirt - S / Male'."""
    if not combination:
        return parent_name
    return f"{parent_name} - {' / '.join(combination)}"


def _compute_combinations(schema: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Compute all variant_attributes combinations from a variant_schema.

    Args:
        schema: Mapping of axis names to lists of values.
                e.g. {"Maat": ["S", "M", "L"], "Gender": ["Male", "Female"]}

    Returns:
        List of variant_attributes dicts, one per combination.
        e.g. [{"Maat": "S", "Gender": "Male"}, {"Maat": "S", "Gender": "Female"}, ...]

    Raises:
        MaxCombinationsExceeded: If total combinations exceed MAX_COMBINATIONS.
    """
    if not schema:
        return []

    # Filter out axes with empty value lists
    axis_names = []
    axis_values = []
    for name, values in schema.items():
        if values:
            axis_names.append(name)
            axis_values.append(values)

    if not axis_names:
        return []

    # Check combination count before computing
    total = 1
    for values in axis_values:
        total *= len(values)
    if total > MAX_COMBINATIONS:
        raise MaxCombinationsExceeded(total)

    # Generate cartesian product
    combinations = []
    for combo in itertools.product(*axis_values):
        combinations.append(dict(zip(axis_names, combo)))

    return combinations


def _query_variants_for_parent(producten_table, parent_id: str) -> List[Dict[str, Any]]:
    """Query all variant records for a given parent_id using the GSI.

    Returns all variants (active and inactive) to allow re-activation.
    """
    variants = []
    query_kwargs = {
        "IndexName": "parent_id-index",
        "KeyConditionExpression": Key("parent_id").eq(parent_id),
    }

    # Handle pagination
    while True:
        response = producten_table.query(**query_kwargs)
        variants.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key

    return variants


def _attributes_match(attrs_a: Dict[str, str], attrs_b: Dict[str, str]) -> bool:
    """Check if two variant_attributes dicts represent the same combination."""
    return attrs_a == attrs_b


def sync_schema_to_variants(
    producten_table,
    parent_id: str,
    new_schema: Dict[str, List[str]],
    parent_price: Decimal,
) -> SyncResult:
    """
    Top-down sync: variant_schema changed → regenerate variants.

    1. Computes desired set of variant_attributes combinations from new_schema
    2. Queries existing variants for parent_id
    3. For each desired combination:
       - If an existing variant matches → preserve (keep stock/price)
       - If no existing variant matches → create new record
    4. For existing active variants not in desired set → deactivate (active=false)

    Args:
        producten_table: boto3 DynamoDB Table resource for the Producten table.
        parent_id: The product_id of the parent product.
        new_schema: The new variant_schema dict (e.g. {"Maat": ["S","M","L"]}).
        parent_price: The parent product's base price, used as default for new variants.

    Returns:
        SyncResult with counts of created, preserved, and deactivated variants.

    Raises:
        MaxCombinationsExceeded: If the schema produces more than 100 combinations.
    """
    # Compute desired combinations
    desired_combinations = _compute_combinations(new_schema)

    # Query existing variants
    existing_variants = _query_variants_for_parent(producten_table, parent_id)

    # Build lookup of existing variants by their attributes (as frozenset for hashable key)
    def _attrs_key(attrs: Dict[str, str]) -> frozenset:
        return frozenset(attrs.items())

    existing_by_attrs: Dict[frozenset, Dict[str, Any]] = {}
    for variant in existing_variants:
        attrs = variant.get("variant_attributes", {})
        key = _attrs_key(attrs)
        existing_by_attrs[key] = variant

    now = datetime.now(timezone.utc).isoformat()
    created_count = 0
    preserved_count = 0
    deactivated_count = 0

    # Track which existing variants are still desired
    matched_keys = set()

    # Process desired combinations
    items_to_write = []

    for combo_attrs in desired_combinations:
        key = _attrs_key(combo_attrs)
        existing = existing_by_attrs.get(key)

        if existing:
            # Variant exists — preserve stock/price, ensure active
            matched_keys.add(key)
            if not existing.get("active", True):
                # Re-activate a previously deactivated variant
                items_to_write.append({
                    **existing,
                    "active": True,
                    "updated_at": now,
                })
                created_count += 1  # Count reactivation as "created" since it's being brought back
            else:
                preserved_count += 1
        else:
            # New combination — create variant record
            combo_values = tuple(combo_attrs[axis] for axis in new_schema.keys() if axis in combo_attrs)
            variant_id = _build_variant_id(parent_id, combo_values)

            new_variant = {
                "product_id": variant_id,
                "parent_id": parent_id,
                "is_parent": False,
                "active": True,
                "variant_attributes": combo_attrs,
                "prijs": parent_price,
                "stock": 0,
                "sold_count": 0,
                "allow_oversell": True,
                "created_at": now,
                "updated_at": now,
            }
            items_to_write.append(new_variant)
            created_count += 1

    # Deactivate existing active variants that are no longer in the desired set
    for key, variant in existing_by_attrs.items():
        if key not in matched_keys and variant.get("active", True):
            # Skip default variants (empty attributes) — they're managed separately
            if not variant.get("variant_attributes"):
                continue
            items_to_write.append({
                **variant,
                "active": False,
                "updated_at": now,
            })
            deactivated_count += 1

    # Batch write all changes
    if items_to_write:
        with producten_table.batch_writer() as batch:
            for item in items_to_write:
                batch.put_item(Item=item)

    logger.info(
        "sync_schema_to_variants for %s: created=%d, preserved=%d, deactivated=%d",
        parent_id,
        created_count,
        preserved_count,
        deactivated_count,
    )

    return SyncResult(
        created=created_count,
        preserved=preserved_count,
        deactivated=deactivated_count,
    )


def sync_variant_to_schema(
    producten_table,
    parent_id: str,
    variant_attributes: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    Bottom-up sync: variant added/removed → update parent variant_schema.

    1. Queries all active variants for parent_id
    2. Includes the new variant_attributes in the computation
    3. Derives variant_schema from union of all variant_attributes values per axis
    4. Updates parent record's variant_schema

    Args:
        producten_table: boto3 DynamoDB Table resource for the Producten table.
        parent_id: The product_id of the parent product.
        variant_attributes: The new variant's attributes (e.g. {"Maat": "XXL", "Gender": "Male"}).

    Returns:
        The updated variant_schema dict (e.g. {"Maat": ["S","M","L","XXL"], "Gender": ["Male","Female"]}).
    """
    # Query all active variants for parent
    all_variants = _query_variants_for_parent(producten_table, parent_id)
    active_variants = [
        v for v in all_variants
        if v.get("active", True) and v.get("variant_attributes")
    ]

    # Collect all unique values per axis from active variants
    schema: Dict[str, List[str]] = {}

    for variant in active_variants:
        attrs = variant.get("variant_attributes", {})
        for axis, value in attrs.items():
            if axis not in schema:
                schema[axis] = []
            if value not in schema[axis]:
                schema[axis].append(value)

    # Include the new variant_attributes in the derived schema
    for axis, value in variant_attributes.items():
        if axis not in schema:
            schema[axis] = []
        if value not in schema[axis]:
            schema[axis].append(value)

    # Update parent record's variant_schema
    now = datetime.now(timezone.utc).isoformat()
    producten_table.update_item(
        Key={"product_id": parent_id},
        UpdateExpression="SET variant_schema = :schema, updated_at = :now",
        ExpressionAttributeValues={
            ":schema": schema,
            ":now": now,
        },
    )

    logger.info(
        "sync_variant_to_schema for %s: derived schema with %d axes",
        parent_id,
        len(schema),
    )

    return schema
