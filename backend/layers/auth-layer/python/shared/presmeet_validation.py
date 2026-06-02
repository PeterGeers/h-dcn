"""
Shared validation utilities for PresMeet event registration module.
Provides schema-driven product attribute validation, pricing calculations,
and order submission validation.
"""

import re
from decimal import Decimal


# Allowed product types
VALID_PRODUCT_TYPES = {"meeting_ticket", "party_ticket", "tshirt", "airport_transfer"}

# Pricing rules (per item)
PRICING = {
    "meeting_ticket": Decimal("50.00"),
    "party_ticket": Decimal("99.50"),
    "tshirt": Decimal("25.00"),
    "airport_transfer": Decimal("5.00"),  # per person
}

# Default attribute schemas (used when no config is provided)
DEFAULT_ATTRIBUTE_SCHEMAS = {
    "meeting_ticket": {
        "name": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
        "role": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
    },
    "party_ticket": {
        "name": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
        "person_type": {
            "type": "string",
            "required": True,
            "enum": ["delegate", "guest"],
        },
    },
    "tshirt": {
        "name": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
        "gender": {
            "type": "string",
            "required": True,
            "enum": ["male", "female"],
        },
        "size": {
            "type": "string",
            "required": True,
            "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
        },
    },
    "airport_transfer": {
        "direction": {
            "type": "string",
            "required": True,
            "enum": ["pickup", "dropoff"],
        },
        "airport": {
            "type": "string",
            "required": True,
            "enum": ["AMS", "RTM", "EIN"],
        },
        "flight": {
            "type": "string",
            "required": True,
            "min_length": 2,
            "max_length": 10,
        },
        "date": {
            "type": "string",
            "required": True,
        },
        "time": {
            "type": "string",
            "required": True,
        },
        "persons": {
            "type": "integer",
            "required": True,
            "minimum": 1,
            "maximum": 50,
        },
    },
}


def validate_product_type(product_type: str) -> tuple:
    """
    Validate product_type is in the allowed set.

    Args:
        product_type: The product type string to validate.

    Returns:
        tuple: (is_valid: bool, error_message: str | None)
    """
    if product_type in VALID_PRODUCT_TYPES:
        return (True, None)
    return (False, f"Invalid product_type '{product_type}'. Allowed values: {sorted(VALID_PRODUCT_TYPES)}")


def validate_attributes(product_type: str, attributes: dict, config: dict) -> list:
    """
    Validate attributes against the product_type schema defined in config.

    The config should contain a 'required_attributes' key with the schema definition.
    If config is empty or missing 'required_attributes', falls back to DEFAULT_ATTRIBUTE_SCHEMAS.

    Args:
        product_type: The product type for which to validate attributes.
        attributes: The attributes dict to validate.
        config: The product type config dict containing 'required_attributes' schema.

    Returns:
        list: List of error dicts, each with 'field', 'message', and 'constraint' keys.
              Empty list if validation passes.
    """
    errors = []

    # Get the schema from config or fall back to defaults
    schema = None
    if config and "required_attributes" in config:
        schema = config["required_attributes"]
    elif product_type in DEFAULT_ATTRIBUTE_SCHEMAS:
        schema = DEFAULT_ATTRIBUTE_SCHEMAS[product_type]

    if schema is None:
        return errors

    # Ensure attributes is a dict
    if not isinstance(attributes, dict):
        errors.append({
            "field": "_attributes",
            "message": "Attributes must be a JSON object",
            "constraint": "type",
        })
        return errors

    # Validate each field in the schema
    for field_name, field_schema in schema.items():
        is_required = field_schema.get("required", False)
        field_type = field_schema.get("type")
        value = attributes.get(field_name)

        # Check required
        if is_required and (value is None or (isinstance(value, str) and field_name not in attributes)):
            if field_name not in attributes:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' is required",
                    "constraint": "required",
                })
                continue

        # Skip further validation if field is not present and not required
        if field_name not in attributes:
            continue

        value = attributes[field_name]

        # Check if value is None for a required field
        if value is None and is_required:
            errors.append({
                "field": field_name,
                "message": f"Field '{field_name}' is required",
                "constraint": "required",
            })
            continue

        if value is None:
            continue

        # Type validation
        if field_type == "string":
            if not isinstance(value, str):
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be a string, got {type(value).__name__}",
                    "constraint": "type",
                })
                continue
        elif field_type == "integer":
            # Accept int or Decimal (DynamoDB stores all numbers as Decimal)
            if isinstance(value, Decimal):
                # Convert Decimal to int if it's a whole number
                if value == int(value):
                    value = int(value)
                    attributes[field_name] = value  # Update in place for downstream checks
                else:
                    errors.append({
                        "field": field_name,
                        "message": f"Field '{field_name}' must be an integer, got decimal with fractional part",
                        "constraint": "type",
                    })
                    continue
            elif not isinstance(value, int) or isinstance(value, bool):
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be an integer, got {type(value).__name__}",
                    "constraint": "type",
                })
                continue

        # Enum validation
        if "enum" in field_schema:
            allowed = field_schema["enum"]
            if value not in allowed:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be one of {allowed}, got '{value}'",
                    "constraint": "enum",
                })

        # String length validations
        if field_type == "string" and isinstance(value, str):
            if "min_length" in field_schema and len(value) < field_schema["min_length"]:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be at least {field_schema['min_length']} characters, got {len(value)}",
                    "constraint": "min_length",
                })
            if "max_length" in field_schema and len(value) > field_schema["max_length"]:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be at most {field_schema['max_length']} characters, got {len(value)}",
                    "constraint": "max_length",
                })

        # Integer range validations
        if field_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in field_schema and value < field_schema["minimum"]:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be at least {field_schema['minimum']}, got {value}",
                    "constraint": "minimum",
                })
            if "maximum" in field_schema and value > field_schema["maximum"]:
                errors.append({
                    "field": field_name,
                    "message": f"Field '{field_name}' must be at most {field_schema['maximum']}, got {value}",
                    "constraint": "maximum",
                })

    return errors


def calculate_cart_total(items: list) -> Decimal:
    """
    Calculate the cart total from a list of cart items using pricing rules.

    Pricing:
    - meeting_ticket: €50.00 per item
    - party_ticket: €99.50 per item
    - tshirt: €25.00 per item
    - airport_transfer: persons × €5.00 per item

    Args:
        items: List of cart item dicts, each with 'product_type' and 'attributes'.

    Returns:
        Decimal: The total amount.
    """
    total = Decimal("0.00")

    for item in items:
        product_type = item.get("product_type")
        if product_type not in PRICING:
            continue

        if product_type == "airport_transfer":
            # Price is per person for airport transfers
            attributes = item.get("attributes", {})
            persons = attributes.get("persons", 1)
            if isinstance(persons, int) and persons > 0:
                total += PRICING["airport_transfer"] * Decimal(str(persons))
            else:
                # Default to 1 person if invalid
                total += PRICING["airport_transfer"]
        else:
            total += PRICING[product_type]

    return total


def calculate_outstanding_balance(order_total: Decimal, payments: list) -> Decimal:
    """
    Calculate the outstanding balance for an order.

    Returns max(0, order_total - sum(payment amounts)).

    Args:
        order_total: The total order amount (Decimal).
        payments: List of payment dicts, each with an 'amount' field.

    Returns:
        Decimal: The outstanding balance (minimum €0.00).
    """
    total_paid = Decimal("0.00")
    for payment in payments:
        amount = payment.get("amount", 0)
        if isinstance(amount, (int, float)):
            total_paid += Decimal(str(amount))
        elif isinstance(amount, Decimal):
            total_paid += amount

    balance = order_total - total_paid
    return max(Decimal("0.00"), balance)


def validate_order_submission(order: dict, config: dict, event: dict) -> list:
    """
    Full submission validation for a PresMeet order.

    Validates:
    - Attribute schemas for all items
    - Min/max per club counts per product_type
    - Airport transfer date ranges (within event dates)

    Args:
        order: The order dict containing 'items' list.
        config: Dict mapping product_type to config (with required_attributes,
                max_per_club, min_per_club).
        event: Event dict with 'start_date' and 'end_date' (ISO format strings).

    Returns:
        list: List of error dicts. Empty if submission is valid.
    """
    errors = []
    items = order.get("items", [])

    # Count items per product_type
    type_counts = {}
    for item in items:
        pt = item.get("product_type")
        if pt:
            type_counts[pt] = type_counts.get(pt, 0) + 1

    # Validate each item's attributes against schema
    for i, item in enumerate(items):
        product_type = item.get("product_type")
        attributes = item.get("attributes", {})
        item_id = item.get("item_id", f"item_{i}")

        if not product_type:
            errors.append({
                "item_id": item_id,
                "field": "product_type",
                "message": "Product type is required",
                "constraint": "required",
            })
            continue

        # Validate product_type
        is_valid, error_msg = validate_product_type(product_type)
        if not is_valid:
            errors.append({
                "item_id": item_id,
                "field": "product_type",
                "message": error_msg,
                "constraint": "enum",
            })
            continue

        # Get config for this product_type
        type_config = config.get(product_type, {})
        attr_errors = validate_attributes(product_type, attributes, type_config)
        for err in attr_errors:
            err["item_id"] = item_id
            errors.append(err)

        # Validate airport_transfer date within event range
        if product_type == "airport_transfer" and event:
            transfer_date = attributes.get("date")
            start_date = event.get("start_date")
            end_date = event.get("end_date")

            if transfer_date and start_date and end_date:
                if transfer_date < start_date or transfer_date > end_date:
                    errors.append({
                        "item_id": item_id,
                        "field": "date",
                        "message": f"Transfer date '{transfer_date}' must be within event dates ({start_date} to {end_date})",
                        "constraint": "date_range",
                    })

    # Validate min/max per club counts
    for product_type, type_config in config.items():
        count = type_counts.get(product_type, 0)

        # Max per club
        max_per_club = type_config.get("max_per_club")
        if max_per_club is not None and count > max_per_club:
            errors.append({
                "field": "product_type",
                "product_type": product_type,
                "message": f"Maximum {max_per_club} {product_type} items allowed per club, got {count}",
                "constraint": "max_per_club",
            })

        # Min per club
        min_per_club = type_config.get("min_per_club")
        if min_per_club is not None and min_per_club > 0 and count < min_per_club:
            errors.append({
                "field": "product_type",
                "product_type": product_type,
                "message": f"Minimum {min_per_club} {product_type} items required per club, got {count}",
                "constraint": "min_per_club",
            })

    return errors


def extract_club_id(user_roles: list) -> str | None:
    """
    Extract club_id from Cognito group list.

    Looks for the first group matching the pattern 'club_*' and returns
    the part after the 'club_' prefix.

    Args:
        user_roles: List of Cognito group names.

    Returns:
        str | None: The club_id (without 'club_' prefix) or None if not found.
    """
    if not user_roles:
        return None

    for role in user_roles:
        if isinstance(role, str) and role.startswith("club_"):
            # Extract the club_id part after 'club_'
            club_id = role[5:]  # len("club_") == 5
            if club_id:  # Ensure there's something after the prefix
                return club_id

    return None
