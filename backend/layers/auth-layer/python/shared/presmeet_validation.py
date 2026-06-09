"""
PresMeet v3 validation module for event registration orders.

Provides schema-driven validation for order submissions:
- validate_item_fields: validates each item's fields against the product's
  order_item_fields definition (required fields, type constraints, options)
- validate_purchase_rules: enforces per-club min/max limits from product
  purchase_rules
- validate_submission: orchestrates field + purchase_rules + event_constraints
  validation, returning ALL errors (not just first)

Error format:
    Each error is a dict with:
    - item_index (int or None): zero-based index of the item causing the error
    - field (str or None): the field_id that failed, or product_id for rule errors
    - message (str): human-readable description of the violation
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from shared.event_constraints import validate_event_constraints


def validate_item_fields(
    items: List[Dict[str, Any]],
    products: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Validate each item's field data against its product's order_item_fields.

    For each item, looks up the product by product_id and validates:
    - All required fields are present and non-empty
    - Text fields are strings
    - Select fields have a value from the allowed options list
    - Number fields are numeric and within min/max bounds
    - Date fields are non-empty strings

    Args:
        items: The order's items array. Each item has product_id and
            item_fields_data (dict of field_id -> value).
        products: Dict mapping product_id -> product record. Each product
            has an order_item_fields array of field definitions.

    Returns:
        List of error dicts. Empty list if all fields are valid.
    """
    errors = []

    for item_index, item in enumerate(items):
        product_id = item.get("product_id")
        if not product_id:
            errors.append({
                "item_index": item_index,
                "field": "product_id",
                "message": "Item ontbreekt een product_id",
            })
            continue

        product = products.get(product_id)
        if not product:
            errors.append({
                "item_index": item_index,
                "field": "product_id",
                "message": f"Onbekend product: {product_id}",
            })
            continue

        field_definitions = product.get("order_item_fields", [])
        if not field_definitions:
            continue

        fields_data = item.get("item_fields_data", {}) or {}

        for field_def in field_definitions:
            field_id = field_def.get("id")
            if not field_id:
                continue

            value = fields_data.get(field_id)
            field_type = field_def.get("type", "text")
            required = field_def.get("required", False)
            label = field_def.get("label", field_id)

            # Check required
            if required and _is_empty(value, field_type):
                errors.append({
                    "item_index": item_index,
                    "field": field_id,
                    "message": f"Veld '{label}' is verplicht",
                })
                continue

            # Skip further validation if value is empty and not required
            if _is_empty(value, field_type):
                continue

            # Type-specific validation
            field_error = _validate_field_type(value, field_def)
            if field_error:
                errors.append({
                    "item_index": item_index,
                    "field": field_id,
                    "message": field_error,
                })

    return errors


def validate_purchase_rules(
    items: List[Dict[str, Any]],
    products: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Validate item counts per product against purchase_rules (min/max per club).

    Counts items per product_id in the order, then checks against each
    product's purchase_rules.min_per_club and purchase_rules.max_per_club.

    Args:
        items: The order's items array.
        products: Dict mapping product_id -> product record with purchase_rules.

    Returns:
        List of error dicts. Empty list if all purchase rules pass.
    """
    errors = []

    # Count items per product_id
    counts: Dict[str, int] = {}
    for item in items:
        product_id = item.get("product_id")
        if product_id:
            counts[product_id] = counts.get(product_id, 0) + 1

    # Check each product's rules
    for product_id, product in products.items():
        purchase_rules = product.get("purchase_rules") or {}
        count = counts.get(product_id, 0)
        product_name = product.get("name", product_id)

        # max_per_club check
        max_per_club = purchase_rules.get("max_per_club")
        if max_per_club is not None:
            max_val = _to_int(max_per_club)
            if max_val is not None and count > max_val:
                errors.append({
                    "item_index": None,
                    "field": product_id,
                    "message": (
                        f"Maximum {max_val} items toegestaan voor "
                        f"'{product_name}', maar {count} gevonden"
                    ),
                })

        # min_per_club check
        min_per_club = purchase_rules.get("min_per_club")
        if min_per_club is not None:
            min_val = _to_int(min_per_club)
            if min_val is not None and min_val > 0 and count < min_val:
                errors.append({
                    "item_index": None,
                    "field": product_id,
                    "message": (
                        f"Minimaal {min_val} items vereist voor "
                        f"'{product_name}', maar {count} gevonden"
                    ),
                })

    return errors


def validate_submission(
    order: Dict[str, Any],
    event: Dict[str, Any],
    products: Dict[str, Dict[str, Any]],
    all_event_orders: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Orchestrate full submission validation: fields + purchase_rules + event constraints.

    Runs all three validation checks and returns ALL errors combined.

    Args:
        order: The order being submitted, with items array and club_id.
        event: The event record with constraints array.
        products: Dict mapping product_id -> product record.
        all_event_orders: All orders for this event (any status).

    Returns:
        List of all validation error dicts. Empty list means submission is valid.
    """
    items = order.get("items", [])
    club_id = order.get("club_id")
    all_errors = []

    # 1. Validate item fields
    field_errors = validate_item_fields(items, products)
    all_errors.extend(field_errors)

    # 2. Validate purchase rules
    rule_errors = validate_purchase_rules(items, products)
    all_errors.extend(rule_errors)

    # 3. Validate event constraints
    event_constraints = event.get("constraints", [])
    if event_constraints:
        constraint_errors = validate_event_constraints(
            order_items=items,
            event_constraints=event_constraints,
            all_event_orders=all_event_orders,
            current_club_id=club_id,
        )
        # Convert constraint errors to our standard format
        for ce in constraint_errors:
            all_errors.append({
                "item_index": None,
                "field": ce.get("constraint_key"),
                "message": ce.get("message", "Capaciteitslimiet overschreden"),
            })

    return all_errors


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_empty(value: Any, field_type: str) -> bool:
    """Check if a value is considered empty for a given field type."""
    if value is None:
        return True

    if field_type in ("text", "select", "date"):
        if isinstance(value, str):
            return value.strip() == ""
        return True

    if field_type == "number":
        if isinstance(value, (int, float, Decimal)):
            return False
        if isinstance(value, str):
            try:
                float(value)
                return False
            except (ValueError, TypeError):
                return True
        return True

    return value is None or value == ""


def _validate_field_type(value: Any, field_def: Dict[str, Any]) -> Optional[str]:
    """
    Validate a field value against its type constraints.

    Returns None if valid, or an error message string.
    """
    field_type = field_def.get("type", "text")
    label = field_def.get("label", field_def.get("id", "?"))

    if field_type == "text":
        if not isinstance(value, str):
            return f"Veld '{label}' moet tekst zijn"
        return None

    elif field_type == "select":
        options = field_def.get("options", [])
        if not isinstance(value, str):
            return f"Veld '{label}' moet tekst zijn"
        if options and value not in options:
            return (
                f"Veld '{label}': ongeldige keuze '{value}'. "
                f"Toegestane waarden: {', '.join(options)}"
            )
        return None

    elif field_type == "number":
        numeric_value = _to_numeric(value)
        if numeric_value is None:
            return f"Veld '{label}' moet een getal zijn"

        min_val = field_def.get("min")
        if min_val is not None:
            min_numeric = _to_numeric(min_val)
            if min_numeric is not None and numeric_value < min_numeric:
                return f"Veld '{label}' moet minimaal {min_val} zijn"

        max_val = field_def.get("max")
        if max_val is not None:
            max_numeric = _to_numeric(max_val)
            if max_numeric is not None and numeric_value > max_numeric:
                return f"Veld '{label}' mag maximaal {max_val} zijn"

        return None

    elif field_type == "date":
        if not isinstance(value, str):
            return f"Veld '{label}' moet een datum zijn"
        if value.strip() == "":
            return f"Veld '{label}' is verplicht"
        return None

    return None


def _to_int(value: Any) -> Optional[int]:
    """Convert a value to int, handling Decimal from DynamoDB."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return None


def _to_numeric(value: Any) -> Optional[float]:
    """Convert a value to float for numeric comparisons."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None
