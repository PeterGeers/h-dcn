"""
Item fields validation module for order_item_fields data.

Validates that submitted Item_Fields_Data conforms to the product's
order_item_fields definition at order creation time. Checks:
- Count of item_fields_data entries matches the ordered quantity
- Required fields have non-empty values (type-specific rules)
- Field values satisfy validation constraints (min_length, max_length,
  minimum, maximum, pattern, options, email format)

Returns structured errors with item_index, field_id, and constraint
description for frontend display.
"""

import re
from typing import Any, Dict, List, Optional


def validate_item_fields(
    order_item_fields: List[Dict[str, Any]],
    item_fields_data: Optional[List[Dict[str, Any]]],
    quantity: int,
) -> List[Dict[str, Any]]:
    """
    Validate submitted item_fields_data against the product's order_item_fields
    definition. Returns ALL validation errors (not just the first).

    This is the primary validation entry point used by submit_order and
    update_order_items handlers.

    Checks:
    1. item_fields_data count matches quantity
    2. Each required field in each entry has a non-empty value
    3. Type-specific validation (email pattern, number min/max, select options,
       date format)

    Args:
        order_item_fields: The product's order_item_fields definition array.
            Each entry: {id, label, type, required, options?, validation?}
        item_fields_data: List of field data entries, one per item unit.
            Each entry: {field_values: {field_id: value, ...}} or direct dict.
        quantity: The ordered quantity for this line item.

    Returns:
        List of error dicts. Empty list if validation passes.
        Each error: {"item_index": int, "field_id": str, "message": str}
    """
    errors: List[Dict[str, Any]] = []

    # Check if item_fields_data is missing entirely
    if item_fields_data is None:
        errors.append({
            "item_index": 0,
            "field_id": "item_fields_data",
            "message": f"Expected {quantity} entries, got 0",
        })
        return errors

    # Check count matches quantity
    actual_count = len(item_fields_data)
    if actual_count != quantity:
        errors.append({
            "item_index": 0,
            "field_id": "item_fields_data",
            "message": f"Expected {quantity} entries, got {actual_count}",
        })
        return errors

    # Validate each entry against field definitions
    for item_index, entry in enumerate(item_fields_data):
        # Support both {"field_values": {...}} wrapper and direct dict
        if isinstance(entry, dict) and "field_values" in entry:
            field_values = entry["field_values"]
        else:
            field_values = entry if isinstance(entry, dict) else {}

        for field_def in order_item_fields:
            field_id = field_def.get("id", "")
            if not field_id:
                continue

            value = field_values.get(field_id)
            field_type = field_def.get("type", "text")
            required = field_def.get("required", False)
            label = field_def.get("label", field_id)

            # Check required constraint
            if required and _is_empty_for_type(value, field_type):
                errors.append({
                    "item_index": item_index,
                    "field_id": field_id,
                    "message": f"Required field is empty",
                })
                continue

            # Skip further validation if value is empty and not required
            if _is_empty_for_type(value, field_type):
                continue

            # Type-specific validation
            type_error = _validate_field_for_type(value, field_def)
            if type_error:
                errors.append({
                    "item_index": item_index,
                    "field_id": field_id,
                    "message": type_error,
                })

    return errors


def _validate_field_for_type(value: Any, field_def: Dict[str, Any]) -> Optional[str]:
    """
    Type-specific validation returning a human-readable error message or None.

    Delegates to type-specific validators for email, number, select, date.
    """
    field_type = field_def.get("type", "text")
    validation = field_def.get("validation", {}) or {}
    options = field_def.get("options", [])

    if field_type == "email":
        if not isinstance(value, str):
            return "Invalid email format"
        email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            return "Invalid email format"

    elif field_type == "number":
        numeric_value = _to_numeric(value)
        if numeric_value is None:
            return "Invalid number"
        minimum = validation.get("minimum") or validation.get("min")
        if minimum is not None:
            try:
                if numeric_value < float(minimum):
                    return f"Value must be at least {minimum}"
            except (TypeError, ValueError):
                pass
        maximum = validation.get("maximum") or validation.get("max")
        if maximum is not None:
            try:
                if numeric_value > float(maximum):
                    return f"Value must be at most {maximum}"
            except (TypeError, ValueError):
                pass

    elif field_type == "select":
        if options and value not in options:
            return f"Value must be one of: {', '.join(str(o) for o in options)}"

    elif field_type == "date":
        if not isinstance(value, str) or not value.strip():
            return "Invalid date format"
        # Basic date format validation (YYYY-MM-DD)
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, value.strip()):
            return "Invalid date format"

    # text type: no type-specific validation beyond required check
    return None


def _to_numeric(value: Any) -> Optional[float]:
    """Convert a value to a float, returning None if not possible."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    # Support Decimal
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_item_fields_data(
    item_fields_data: Optional[List[Dict[str, Any]]],
    order_item_fields_definition: List[Dict[str, Any]],
    quantity: int,
    line_item_index: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Validate submitted item_fields_data against the product's
    order_item_fields definition.

    Checks:
    1. item_fields_data is present (not None/missing)
    2. Count of entries equals the ordered quantity
    3. Each entry's field values pass validation

    Args:
        item_fields_data: List of field_values dicts, one per item unit.
            Each entry is a dict like {"field_values": {"name": "Jan", ...}}
            or directly a dict of field_id -> value.
        order_item_fields_definition: The product's order_item_fields array
            of field definitions.
        quantity: The ordered quantity for this line item.
        line_item_index: Zero-based index of the line item in the order.

    Returns:
        None if validation passes, or a structured error dict if it fails.
    """
    # Check if item_fields_data is missing entirely
    if item_fields_data is None:
        return {
            "error": "item_fields_count_mismatch",
            "details": {
                "line_item_index": line_item_index,
                "expected": quantity,
                "actual": 0,
            },
        }

    # Check count matches quantity
    actual_count = len(item_fields_data)
    if actual_count != quantity:
        return {
            "error": "item_fields_count_mismatch",
            "details": {
                "line_item_index": line_item_index,
                "expected": quantity,
                "actual": actual_count,
            },
        }

    # Validate each entry against field definitions
    for item_index, entry in enumerate(item_fields_data):
        # Support both {"field_values": {...}} wrapper and direct dict
        if isinstance(entry, dict) and "field_values" in entry:
            field_values = entry["field_values"]
        else:
            field_values = entry if isinstance(entry, dict) else {}

        for field_def in order_item_fields_definition:
            field_id = field_def["id"]
            value = field_values.get(field_id)

            error = validate_field_value(value, field_def)
            if error is not None:
                return {
                    "error": "item_fields_validation_error",
                    "details": {
                        "item_index": item_index,
                        "field_id": field_id,
                        "constraint": error,
                    },
                }

    return None


def validate_field_value(
    value: Any,
    field_def: Dict[str, Any],
) -> Optional[str]:
    """
    Validate a single field value against its field definition.

    Checks:
    - Required: value must be non-empty per type-specific rules
    - min_length / max_length: for text and email types
    - minimum / maximum: for number type
    - pattern: regex match for text and email types
    - options: value must be in allowed options list (select type)
    - email format: basic email validation for email type

    Args:
        value: The submitted value (may be None, empty string, etc.)
        field_def: The field definition containing type, required,
            validation constraints, and options.

    Returns:
        None if valid, or a string describing the constraint violation.
    """
    field_type = field_def.get("type", "text")
    required = field_def.get("required", False)
    validation = field_def.get("validation", {}) or {}
    options = field_def.get("options", [])

    # Check required constraint first
    if required:
        if _is_empty_for_type(value, field_type):
            return "required"

    # If value is empty/None and not required, skip further validation
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "" and field_type in ("text", "email"):
        return None

    # Type-specific validation
    if field_type == "text":
        return _validate_text(value, validation)
    elif field_type == "email":
        return _validate_email(value, validation)
    elif field_type == "select":
        return _validate_select(value, options)
    elif field_type == "number":
        return _validate_number(value, validation)
    elif field_type == "date":
        # Date just needs to be present (handled by required check)
        return None

    return None


def _is_empty_for_type(value: Any, field_type: str) -> bool:
    """
    Determine if a value is considered "empty" for required-field purposes.

    Rules per type:
    - text, email: trimmed string must have at least 1 character
    - select: must match one of the defined options (handled separately,
      but None/empty string = empty)
    - number: must have a numeric value present (not None)
    - date: must have a value present (not None, not empty string)
    """
    if value is None:
        return True

    if field_type in ("text", "email"):
        if not isinstance(value, str):
            return True
        return value.strip() == ""

    if field_type == "select":
        if not isinstance(value, str):
            return True
        return value.strip() == ""

    if field_type == "number":
        # None is empty; 0 is a valid value
        if isinstance(value, (int, float)):
            return False
        # Try parsing string as number
        if isinstance(value, str):
            try:
                float(value)
                return False
            except (ValueError, TypeError):
                return True
        return True

    if field_type == "date":
        if isinstance(value, str):
            return value.strip() == ""
        return True

    return value is None or value == ""


def _validate_text(value: Any, validation: Dict[str, Any]) -> Optional[str]:
    """Validate a text field value against constraints."""
    if not isinstance(value, str):
        return "invalid_type"

    text = value

    min_length = validation.get("min_length")
    if min_length is not None and len(text) < min_length:
        return f"min_length:{min_length}"

    max_length = validation.get("max_length")
    if max_length is not None and len(text) > max_length:
        return f"max_length:{max_length}"

    pattern = validation.get("pattern")
    if pattern is not None:
        try:
            if not re.fullmatch(pattern, text):
                return f"pattern:{pattern}"
        except re.error:
            # Invalid regex pattern in definition - skip check
            pass

    return None


def _validate_email(value: Any, validation: Dict[str, Any]) -> Optional[str]:
    """Validate an email field value against constraints."""
    if not isinstance(value, str):
        return "invalid_type"

    email = value

    # Basic email format check
    email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return "email_format"

    # min_length / max_length constraints
    min_length = validation.get("min_length")
    if min_length is not None and len(email) < min_length:
        return f"min_length:{min_length}"

    max_length = validation.get("max_length")
    if max_length is not None and len(email) > max_length:
        return f"max_length:{max_length}"

    # pattern constraint
    pattern = validation.get("pattern")
    if pattern is not None:
        try:
            if not re.fullmatch(pattern, email):
                return f"pattern:{pattern}"
        except re.error:
            pass

    return None


def _validate_select(value: Any, options: List[str]) -> Optional[str]:
    """Validate a select field value against allowed options."""
    if not isinstance(value, str):
        return "invalid_type"

    if not options:
        return None

    if value not in options:
        return "options"

    return None


def _validate_number(value: Any, validation: Dict[str, Any]) -> Optional[str]:
    """Validate a number field value against constraints."""
    # Convert string to number if needed
    numeric_value = None
    if isinstance(value, (int, float)):
        numeric_value = value
    elif isinstance(value, str):
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return "invalid_type"
    else:
        return "invalid_type"

    minimum = validation.get("minimum")
    if minimum is not None and numeric_value < minimum:
        return f"minimum:{minimum}"

    maximum = validation.get("maximum")
    if maximum is not None and numeric_value > maximum:
        return f"maximum:{maximum}"

    return None
