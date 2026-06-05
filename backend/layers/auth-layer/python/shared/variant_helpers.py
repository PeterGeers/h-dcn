"""
Variant generation and management helpers for the webshop management admin.

Provides utilities for:
- Generating all attribute combinations from a product's required_attributes schema
- Creating Default_Variant records for simple products
- Determining when a Default_Variant should be removed (when real variants are added)
"""

import itertools
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_variant_combinations(
    required_attributes: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Generate all possible combinations of attribute values from a
    required_attributes JSON schema.

    The required_attributes schema follows this structure:
    {
        "type": "object",
        "properties": {
            "gender": {"type": "string", "enum": ["male", "female"]},
            "size": {"type": "string", "enum": ["S", "M", "L"]}
        }
    }

    Returns a list of dicts, each representing one unique combination:
    [
        {"gender": "male", "size": "S"},
        {"gender": "male", "size": "M"},
        {"gender": "male", "size": "L"},
        {"gender": "female", "size": "S"},
        ...
    ]

    Returns an empty list if required_attributes is None, empty, or has
    no properties with enum values.
    """
    if not required_attributes:
        return []

    properties = required_attributes.get("properties", {})
    if not properties:
        return []

    # Extract attribute names and their enum values
    attr_names: List[str] = []
    attr_values: List[List[str]] = []

    for attr_name, attr_schema in properties.items():
        enum_values = attr_schema.get("enum", [])
        if enum_values:
            attr_names.append(attr_name)
            attr_values.append(enum_values)

    if not attr_names:
        return []

    # Generate cartesian product of all attribute values
    combinations: List[Dict[str, str]] = []
    for combo in itertools.product(*attr_values):
        combination = dict(zip(attr_names, combo))
        combinations.append(combination)

    return combinations


def create_default_variant(
    parent_product_id: str, tenant: str
) -> Dict[str, Any]:
    """
    Create a Default_Variant record for a newly created product.

    Every product must have at least one variant. Simple products (without
    required_attributes) get a single Default_Variant with empty
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
