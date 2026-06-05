"""
Product validation module for the webshop management admin.

Provides validation for product payloads (min/max per club constraints,
required_attributes schema validity) and variant attribute conformance
against parent enum definitions.
"""

import json
from typing import Any, Dict, List, Optional, Tuple


def validate_product(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a product payload before saving.

    Checks:
    - If both min_per_club and max_per_club are set, min_per_club <= max_per_club
    - required_attributes schema is valid JSON with proper structure

    Returns:
        Tuple of (is_valid, errors) where errors is a list of error messages.
    """
    errors: List[str] = []

    # Validate min_per_club <= max_per_club
    min_per_club = payload.get('min_per_club')
    max_per_club = payload.get('max_per_club')

    if min_per_club is not None and max_per_club is not None:
        if not isinstance(min_per_club, (int, float)):
            errors.append('min_per_club must be a number')
        elif not isinstance(max_per_club, (int, float)):
            errors.append('max_per_club must be a number')
        elif min_per_club > max_per_club:
            errors.append(
                f'min_per_club ({min_per_club}) must not exceed '
                f'max_per_club ({max_per_club})'
            )

    # Validate required_attributes schema
    required_attributes = payload.get('required_attributes')
    if required_attributes is not None:
        schema_errors = _validate_required_attributes_schema(required_attributes)
        errors.extend(schema_errors)

    is_valid = len(errors) == 0
    return (is_valid, errors)


def validate_variant_attributes(
    variant_attrs: Dict[str, str],
    parent_required_attributes: Optional[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Validate that variant attribute values conform to the parent's
    required_attributes enum definitions.

    For example, if the parent defines:
        {"type": "object", "properties": {"size": {"type": "string", "enum": ["S", "M", "L"]}}}
    then variant_attrs {"size": "XL"} would be invalid.

    Args:
        variant_attrs: The variant's attribute values (e.g., {"gender": "male", "size": "XL"})
        parent_required_attributes: The parent product's required_attributes schema

    Returns:
        Tuple of (is_valid, errors) where errors is a list of error messages.
    """
    errors: List[str] = []

    # If parent has no required_attributes, variant should have empty attributes
    if parent_required_attributes is None:
        if variant_attrs:
            errors.append(
                'Parent product has no required_attributes; '
                'variant should have empty attributes'
            )
        return (len(errors) == 0, errors)

    # Extract properties from the schema
    properties = parent_required_attributes.get('properties', {})

    if not properties:
        if variant_attrs:
            errors.append(
                'Parent required_attributes has no properties defined; '
                'variant should have empty attributes'
            )
        return (len(errors) == 0, errors)

    # Check each attribute in the variant
    for attr_name, attr_value in variant_attrs.items():
        if attr_name not in properties:
            errors.append(
                f'Attribute "{attr_name}" is not defined in parent '
                f'required_attributes'
            )
            continue

        prop_schema = properties[attr_name]
        allowed_values = prop_schema.get('enum')

        if allowed_values is not None:
            if attr_value not in allowed_values:
                errors.append(
                    f'Attribute "{attr_name}" value "{attr_value}" is not '
                    f'in allowed values: {allowed_values}'
                )

    # Check that all required properties have values
    for prop_name in properties:
        if prop_name not in variant_attrs:
            errors.append(
                f'Missing required attribute "{prop_name}" in variant'
            )

    is_valid = len(errors) == 0
    return (is_valid, errors)


def _validate_required_attributes_schema(
    schema: Any,
) -> List[str]:
    """
    Validate that a required_attributes value is a valid schema.

    Expected structure:
    {
        "type": "object",
        "properties": {
            "<attribute_name>": {
                "type": "string",
                "enum": [<allowed_values>]
            }
        }
    }
    """
    errors: List[str] = []

    # If it's a string, try to parse it as JSON
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except (json.JSONDecodeError, TypeError):
            errors.append('required_attributes is not valid JSON')
            return errors

    # Must be a dict
    if not isinstance(schema, dict):
        errors.append('required_attributes must be a JSON object')
        return errors

    # Must have type: "object"
    schema_type = schema.get('type')
    if schema_type != 'object':
        errors.append(
            f'required_attributes must have "type": "object", '
            f'got "{schema_type}"'
        )

    # Must have properties field
    properties = schema.get('properties')
    if properties is None:
        errors.append('required_attributes must have a "properties" field')
        return errors

    if not isinstance(properties, dict):
        errors.append('required_attributes "properties" must be a JSON object')
        return errors

    # Validate each property definition
    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            errors.append(
                f'Property "{prop_name}" definition must be a JSON object'
            )
            continue

        # Each property should have a type
        prop_type = prop_def.get('type')
        if prop_type is None:
            errors.append(f'Property "{prop_name}" must have a "type" field')

        # If enum is defined, validate it
        enum_values = prop_def.get('enum')
        if enum_values is not None:
            if not isinstance(enum_values, list):
                errors.append(
                    f'Property "{prop_name}" enum must be a list'
                )
            elif len(enum_values) == 0:
                errors.append(
                    f'Property "{prop_name}" enum must not be empty'
                )
            else:
                # Check for duplicate enum values
                seen = set()
                for val in enum_values:
                    if val in seen:
                        errors.append(
                            f'Property "{prop_name}" enum contains '
                            f'duplicate value: "{val}"'
                        )
                    seen.add(val)

    return errors
