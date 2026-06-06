"""
Variant generation and management helpers for the webshop.

Provides utilities for:
- Generating variant records from a product's variant_schema
- Creating Default_Variant records for simple products
- Determining when a Default_Variant should be removed (when real variants are added)
"""

import itertools
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _sanitize_for_id(value: str) -> str:
    """
    Sanitize a value for use in a variant product_id.

    Lowercases, replaces spaces/special chars with underscores, and strips
    leading/trailing underscores.
    """
    sanitized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return sanitized.strip("_")


def generate_variant_combinations(
    variant_schema: Optional[Dict[str, List[str]]],
    parent_product_id: str,
    tenant: str,
) -> List[Dict[str, Any]]:
    """
    Generate variant records from a variant_schema definition.

    The variant_schema is an object where keys are axis names (1-50 chars)
    and values are arrays of allowed string values (each 1-100 chars):
    {
        "Maat": ["S", "M", "L", "XL"],
        "Gender": ["Male", "Female"]
    }

    Returns a list of variant record dicts ready for DynamoDB insertion.
    Each record contains:
    - product_id: "var_{parent_id}_{axis1_value}_{axis2_value}_..."
    - is_parent: False
    - parent_id: reference to parent product
    - tenant: inherited from parent
    - variant_attributes: mapping of axis name to selected value
    - stock: 0
    - sold_count: 0
    - allow_oversell: False
    - active: True

    Constraints enforced by product_validation.py (not here):
    - Max 5 axes
    - Max 20 values per axis
    - Max 100 total combinations (C₁ × C₂ × ... × Cₙ ≤ 100)

    Returns an empty list if variant_schema is None or empty.

    Args:
        variant_schema: Dict mapping axis names to lists of allowed values.
        parent_product_id: The product_id of the parent product.
        tenant: The tenant identifier (e.g., "h-dcn", "presmeet").

    Returns:
        A list of variant record dicts for DynamoDB insertion.
    """
    if not variant_schema:
        return []

    # Extract axis names and their values in consistent order
    axis_names: List[str] = list(variant_schema.keys())
    axis_values: List[List[str]] = [variant_schema[name] for name in axis_names]

    # Filter out axes with no values
    filtered_axes: List[str] = []
    filtered_values: List[List[str]] = []
    for name, values in zip(axis_names, axis_values):
        if values:
            filtered_axes.append(name)
            filtered_values.append(values)

    if not filtered_axes:
        return []

    now = datetime.now(timezone.utc).isoformat()

    # Generate cartesian product of all axis values
    variants: List[Dict[str, Any]] = []
    for combo in itertools.product(*filtered_values):
        # Build variant_attributes mapping
        variant_attributes = dict(zip(filtered_axes, combo))

        # Build product_id from axis values
        id_parts = [_sanitize_for_id(v) for v in combo]
        variant_id = f"var_{parent_product_id}_{'_'.join(id_parts)}"

        variant_record: Dict[str, Any] = {
            "product_id": variant_id,
            "is_parent": False,
            "parent_id": parent_product_id,
            "tenant": tenant,
            "variant_attributes": variant_attributes,
            "stock": 0,
            "sold_count": 0,
            "allow_oversell": False,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        variants.append(variant_record)

    return variants


def create_default_variant(
    parent_product_id: str, tenant: str
) -> Dict[str, Any]:
    """
    Create a Default_Variant record for a newly created product.

    Every product must have at least one variant. Simple products (without
    variant_schema) get a single Default_Variant with empty
    variant_attributes. Stock is tracked exclusively at the variant level.

    Args:
        parent_product_id: The product_id of the parent product.
        tenant: The tenant identifier (e.g., "presmeet", "h-dcn").

    Returns:
        A dict representing the Default_Variant DynamoDB record.
    """
    now = datetime.now(timezone.utc).isoformat()

    return {
        "product_id": f"var_{parent_product_id}_default",
        "parent_id": parent_product_id,
        "tenant": tenant,
        "name": "Default Variant",
        "is_parent": False,
        "variant_attributes": {},
        "price": None,
        "stock": 0,
        "sold_count": 0,
        "allow_oversell": False,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }


def should_remove_default_variant(
    existing_variants: List[Dict[str, Any]],
    new_variants: List[Dict[str, Any]],
) -> bool:
    """
    Determine whether the Default_Variant should be removed.

    Returns True when:
    - The existing variants contain ONLY a Default_Variant
      (variant_attributes == {})
    - AND the new variants include at least one attribute-based variant
      (variant_attributes != {})

    This implements the design rule: when adding real variants to a product
    that only has the default, the Default_Variant should be removed.

    Args:
        existing_variants: Current variant records for the product.
        new_variants: New variant records being added.

    Returns:
        True if the Default_Variant should be removed, False otherwise.
    """
    if not existing_variants or not new_variants:
        return False

    # Check if all existing variants are Default_Variants (empty attributes)
    all_existing_are_default = all(
        variant.get("variant_attributes", {}) == {}
        for variant in existing_variants
    )

    if not all_existing_are_default:
        return False

    # Check if any new variant has actual attribute values
    any_new_has_attributes = any(
        variant.get("variant_attributes", {}) != {}
        for variant in new_variants
    )

    return any_new_has_attributes
