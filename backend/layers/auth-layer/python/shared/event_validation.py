"""
Event validation module for order submissions.

Provides schema-driven validation for order submissions (events and webshop):
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
    - Email fields have valid email format
    - Select fields have a value from the allowed options list
    - Number fields are numeric and within min/max bounds
    - Date fields are non-empty strings

    Supports two item_fields_data formats:
    - Dict format (legacy): {'field_id': value, ...}
    - List format (per-unit): [{'field_values': {'field_id': value}}, ...]
      where len(list) must == item quantity.

    Args:
        items: The order's items array. Each item has product_id and
            item_fields_data (dict or list of per-unit field data).
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

        raw_fields_data = item.get("item_fields_data")
        quantity = item.get("quantity", 1)
        if isinstance(quantity, Decimal):
            quantity = int(quantity)

        # Determine format and build list of field_values dicts to validate
        if isinstance(raw_fields_data, list):
            # Per-unit list format: validate count matches quantity
            if len(raw_fields_data) != quantity:
                errors.append({
                    "item_index": item_index,
                    "field": "item_fields_data",
                    "message": (
                        f"Aantal veldgegevens ({len(raw_fields_data)}) "
                        f"komt niet overeen met aantal ({quantity})"
                    ),
                })
                continue

            # Extract field_values from each entry
            fields_data_list = []
            for entry in raw_fields_data:
                if isinstance(entry, dict):
                    fields_data_list.append(entry.get("field_values") or {})
                else:
                    fields_data_list.append({})
        elif isinstance(raw_fields_data, dict):
            # Legacy flat dict format — single set of fields
            fields_data_list = [raw_fields_data]
        elif raw_fields_data is None:
            # Missing item_fields_data — check if any fields are required
            has_required = any(
                fd.get("required", False) for fd in field_definitions
            )
            if has_required:
                errors.append({
                    "item_index": item_index,
                    "field": "item_fields_data",
                    "message": "Veldgegevens zijn verplicht voor dit product",
                })
            continue
        else:
            fields_data_list = [{}]

        # Validate each set of field values
        for unit_index, fields_data in enumerate(fields_data_list):
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
    Validate item counts per product against purchase_rules.

    Counts items per product_id in the order (using quantity), then checks
    against each product's purchase_rules limits:
    - max_per_order: maximum quantity of this product in a single order
      (also checks max_per_club as backward-compatible equivalent)
    - min_per_order: minimum items for row-scoped orders
      (also checks min_per_club as backward-compatible equivalent)

    Args:
        items: The order's items array.
        products: Dict mapping product_id -> product record with purchase_rules.

    Returns:
        List of error dicts. Empty list if all purchase rules pass.
    """
    errors = []

    # Count total quantity per product_id
    counts: Dict[str, int] = {}
    for item in items:
        product_id = item.get("product_id")
        if product_id:
            quantity = item.get("quantity", 1)
            if isinstance(quantity, Decimal):
                quantity = int(quantity)
            counts[product_id] = counts.get(product_id, 0) + quantity

    # Check each product's rules
    for product_id, product in products.items():
        purchase_rules = product.get("purchase_rules") or {}
        count = counts.get(product_id, 0)
        product_name = product.get("name", product_id)

        # max_per_order check (authoritative; fall back to max_per_club per Req 5.8)
        max_per_order = purchase_rules.get("max_per_order")
        if max_per_order is None:
            max_per_order = purchase_rules.get("max_per_club")
        if max_per_order is not None:
            max_val = _to_int(max_per_order)
            if max_val is not None and count > max_val:
                errors.append({
                    "item_index": None,
                    "field": "purchase_rules",
                    "message": (
                        f"max_per_order: maximaal {max_val} toegestaan voor "
                        f"'{product_name}', maar {count} aangevraagd"
                    ),
                })

        # min_per_order check (fall back to min_per_club for backward compat)
        min_per_order = purchase_rules.get("min_per_order")
        if min_per_order is None:
            min_per_order = purchase_rules.get("min_per_club")
        if min_per_order is not None:
            min_val = _to_int(min_per_order)
            if min_val is not None and min_val > 0 and count < min_val:
                errors.append({
                    "item_index": None,
                    "field": "purchase_rules",
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
        order: The order being submitted, with items array and registry_row_id.
        event: The event record with constraints array.
        products: Dict mapping product_id -> product record.
        all_event_orders: All orders for this event (any status).

    Returns:
        List of all validation error dicts. Empty list means submission is valid.
    """
    items = order.get("items", [])
    registry_row_id = order.get("registry_row_id")
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
            current_registry_row_id=registry_row_id,
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
        # Check min_length validation
        validation = field_def.get("validation") or {}
        min_length = validation.get("min_length")
        if min_length is not None:
            min_len = _to_int(min_length)
            if min_len is not None and len(value.strip()) < min_len:
                return f"Veld '{label}' moet minimaal {min_len} tekens bevatten"
        return None

    elif field_type == "email":
        if not isinstance(value, str):
            return f"Veld '{label}' moet tekst zijn"
        # Basic email format check
        import re
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
            return f"Veld '{label}' is geen geldig e-mailadres"
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
