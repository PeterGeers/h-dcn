"""
Product validation module for the webshop management admin.

Provides validation for product payloads (min/max per club constraints,
required_attributes schema validity) and variant attribute conformance
against parent enum definitions.

Also provides validation for the unified product model fields:
- variant_schema: axis-based variant generation schema
- order_item_fields: per-item data collection definitions
- purchase_rules: business constraints on purchasing
"""

import json
import re
from functools import reduce
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


# --- New unified model validation functions ---

_MAX_AXES = 5
_MAX_VALUES_PER_AXIS = 20
_MAX_VARIANT_COMBINATIONS = 100
_MAX_AXIS_NAME_LENGTH = 50
_MAX_AXIS_VALUE_LENGTH = 100

_MAX_ORDER_ITEM_FIELDS = 20
_MAX_FIELD_ID_LENGTH = 50
_MAX_FIELD_LABEL_LENGTH = 200
_VALID_FIELD_TYPES = {'text', 'select', 'date', 'number', 'email'}
_MAX_SELECT_OPTIONS = 50
_MAX_LENGTH_LIMIT = 1000
_MAX_PATTERN_LENGTH = 500

_MAX_PURCHASE_RULE_VALUE = 9999
_VALID_ORDER_MODES = {'single', 'persistent'}


def validate_variant_schema(
    schema: Any,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate a variant_schema object.

    Expected structure:
    {
        "Maat": ["S", "M", "L", "XL"],
        "Gender": ["Male", "Female"]
    }

    Checks:
    - schema is a dict
    - max 5 axes
    - axis names are non-empty strings, 1-50 chars, unique
    - values per axis are non-empty arrays with 1-20 items
    - each value is a non-empty string of 1-100 chars
    - values are unique within each axis
    - total combinations (product of all axis value counts) <= 100

    Returns:
        Tuple of (is_valid, errors) where errors is a list of structured
        error dicts with 'field' and 'message' keys.
    """
    errors: List[Dict[str, Any]] = []

    if not isinstance(schema, dict):
        errors.append({
            'field': 'variant_schema',
            'message': 'variant_schema must be an object'
        })
        return (False, errors)

    if len(schema) == 0:
        errors.append({
            'field': 'variant_schema',
            'message': 'variant_schema must have at least one axis'
        })
        return (False, errors)

    if len(schema) > _MAX_AXES:
        errors.append({
            'field': 'variant_schema',
            'message': f'variant_schema exceeds maximum of {_MAX_AXES} axes '
                       f'(has {len(schema)})'
        })
        return (False, errors)

    # Track axis names for uniqueness (case-sensitive)
    seen_axis_names: List[str] = []
    value_counts: List[int] = []

    for axis_name, axis_values in schema.items():
        # Axis name validation
        if not isinstance(axis_name, str) or len(axis_name.strip()) == 0:
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': 'axis name must be a non-empty string'
            })
            continue

        if len(axis_name) > _MAX_AXIS_NAME_LENGTH:
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': f'axis name exceeds maximum length of '
                           f'{_MAX_AXIS_NAME_LENGTH} characters'
            })

        if axis_name in seen_axis_names:
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': f'duplicate axis name "{axis_name}"'
            })
        else:
            seen_axis_names.append(axis_name)

        # Values validation
        if not isinstance(axis_values, list):
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': 'axis values must be an array'
            })
            continue

        if len(axis_values) == 0:
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': 'axis must have at least one value'
            })
            continue

        if len(axis_values) > _MAX_VALUES_PER_AXIS:
            errors.append({
                'field': f'variant_schema.{axis_name}',
                'message': f'axis exceeds maximum of {_MAX_VALUES_PER_AXIS} '
                           f'values (has {len(axis_values)})'
            })

        seen_values: set = set()
        for idx, value in enumerate(axis_values):
            if not isinstance(value, str) or len(value.strip()) == 0:
                errors.append({
                    'field': f'variant_schema.{axis_name}[{idx}]',
                    'message': 'value must be a non-empty string'
                })
                continue

            if len(value) > _MAX_AXIS_VALUE_LENGTH:
                errors.append({
                    'field': f'variant_schema.{axis_name}[{idx}]',
                    'message': f'value exceeds maximum length of '
                               f'{_MAX_AXIS_VALUE_LENGTH} characters'
                })

            if value in seen_values:
                errors.append({
                    'field': f'variant_schema.{axis_name}[{idx}]',
                    'message': f'duplicate value "{value}" in axis '
                               f'"{axis_name}"'
                })
            else:
                seen_values.add(value)

        value_counts.append(len(axis_values))

    # Check total combinations
    if value_counts and not errors:
        total_combos = reduce(lambda a, b: a * b, value_counts, 1)
        if total_combos > _MAX_VARIANT_COMBINATIONS:
            errors.append({
                'field': 'variant_schema',
                'message': f'total combinations ({total_combos}) exceeds '
                           f'maximum of {_MAX_VARIANT_COMBINATIONS}'
            })

    is_valid = len(errors) == 0
    return (is_valid, errors)


def validate_order_item_fields(
    fields: Any,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate an order_item_fields array.

    Expected structure:
    [
        {
            "id": "attendee_name",
            "label": "Naam deelnemer",
            "type": "text",
            "required": True,
            "validation": {"min_length": 2, "max_length": 100}
        },
        {
            "id": "dietary",
            "label": "Dieetwensen",
            "type": "select",
            "required": False,
            "options": ["Geen", "Vegetarisch", "Veganistisch"]
        }
    ]

    Checks:
    - fields is a list
    - max 20 field definitions
    - each field has id, label, type, required
    - id: alphanumeric + underscores, max 50 chars, unique
    - label: max 200 chars
    - type: one of text, select, date, number, email
    - select type must have options array (1-50 items)
    - validation constraints: min_length/max_length 1-1000 for text/email,
      minimum/maximum for number, pattern max 500 chars for text/email

    Returns:
        Tuple of (is_valid, errors) where errors is a list of structured
        error dicts with 'field' and 'message' keys.
    """
    errors: List[Dict[str, Any]] = []

    if not isinstance(fields, list):
        errors.append({
            'field': 'order_item_fields',
            'message': 'order_item_fields must be an array'
        })
        return (False, errors)

    if len(fields) == 0:
        errors.append({
            'field': 'order_item_fields',
            'message': 'order_item_fields must have at least one field '
                       'definition'
        })
        return (False, errors)

    if len(fields) > _MAX_ORDER_ITEM_FIELDS:
        errors.append({
            'field': 'order_item_fields',
            'message': f'order_item_fields exceeds maximum of '
                       f'{_MAX_ORDER_ITEM_FIELDS} definitions '
                       f'(has {len(fields)})'
        })
        return (False, errors)

    seen_ids: set = set()
    _field_id_pattern = re.compile(r'^[a-zA-Z0-9_]+$')

    for idx, field_def in enumerate(fields):
        field_prefix = f'order_item_fields[{idx}]'

        if not isinstance(field_def, dict):
            errors.append({
                'field': field_prefix,
                'message': 'field definition must be an object'
            })
            continue

        # Validate id
        field_id = field_def.get('id')
        if field_id is None or not isinstance(field_id, str):
            errors.append({
                'field': f'{field_prefix}.id',
                'message': 'id is required and must be a string'
            })
        elif len(field_id) == 0:
            errors.append({
                'field': f'{field_prefix}.id',
                'message': 'id must be non-empty'
            })
        elif len(field_id) > _MAX_FIELD_ID_LENGTH:
            errors.append({
                'field': f'{field_prefix}.id',
                'message': f'id exceeds maximum length of '
                           f'{_MAX_FIELD_ID_LENGTH} characters'
            })
        elif not _field_id_pattern.match(field_id):
            errors.append({
                'field': f'{field_prefix}.id',
                'message': 'id must contain only alphanumeric characters '
                           'and underscores'
            })
        else:
            if field_id in seen_ids:
                errors.append({
                    'field': f'{field_prefix}.id',
                    'message': f'duplicate field id "{field_id}"'
                })
            else:
                seen_ids.add(field_id)

        # Validate label
        label = field_def.get('label')
        if label is None or not isinstance(label, str):
            errors.append({
                'field': f'{field_prefix}.label',
                'message': 'label is required and must be a string'
            })
        elif len(label) == 0:
            errors.append({
                'field': f'{field_prefix}.label',
                'message': 'label must be non-empty'
            })
        elif len(label) > _MAX_FIELD_LABEL_LENGTH:
            errors.append({
                'field': f'{field_prefix}.label',
                'message': f'label exceeds maximum length of '
                           f'{_MAX_FIELD_LABEL_LENGTH} characters'
            })

        # Validate type
        field_type = field_def.get('type')
        if field_type is None or not isinstance(field_type, str):
            errors.append({
                'field': f'{field_prefix}.type',
                'message': 'type is required and must be a string'
            })
            field_type = None
        elif field_type not in _VALID_FIELD_TYPES:
            errors.append({
                'field': f'{field_prefix}.type',
                'message': f'type must be one of: '
                           f'{", ".join(sorted(_VALID_FIELD_TYPES))}'
            })
            field_type = None

        # Validate required flag
        required = field_def.get('required')
        if required is not None and not isinstance(required, bool):
            errors.append({
                'field': f'{field_prefix}.required',
                'message': 'required must be a boolean'
            })

        # Validate select options
        if field_type == 'select':
            options = field_def.get('options')
            if options is None or not isinstance(options, list):
                errors.append({
                    'field': f'{field_prefix}.options',
                    'message': 'select type field must have an options array'
                })
            elif len(options) == 0:
                errors.append({
                    'field': f'{field_prefix}.options',
                    'message': 'select options array must not be empty'
                })
            elif len(options) > _MAX_SELECT_OPTIONS:
                errors.append({
                    'field': f'{field_prefix}.options',
                    'message': f'select options exceeds maximum of '
                               f'{_MAX_SELECT_OPTIONS} items'
                })

        # Validate validation constraints
        validation = field_def.get('validation')
        if validation is not None:
            if not isinstance(validation, dict):
                errors.append({
                    'field': f'{field_prefix}.validation',
                    'message': 'validation must be an object'
                })
            else:
                _validate_field_constraints(
                    validation, field_type, field_prefix, errors
                )

    is_valid = len(errors) == 0
    return (is_valid, errors)


def _validate_field_constraints(
    validation: Dict[str, Any],
    field_type: Optional[str],
    field_prefix: str,
    errors: List[Dict[str, Any]],
) -> None:
    """Validate validation constraints for a field definition."""

    # min_length / max_length: valid for text and email types
    min_length = validation.get('min_length')
    max_length = validation.get('max_length')

    if min_length is not None:
        if field_type not in ('text', 'email'):
            errors.append({
                'field': f'{field_prefix}.validation.min_length',
                'message': 'min_length is only valid for text and email types'
            })
        elif not isinstance(min_length, int) or min_length < 1 \
                or min_length > _MAX_LENGTH_LIMIT:
            errors.append({
                'field': f'{field_prefix}.validation.min_length',
                'message': f'min_length must be an integer between 1 and '
                           f'{_MAX_LENGTH_LIMIT}'
            })

    if max_length is not None:
        if field_type not in ('text', 'email'):
            errors.append({
                'field': f'{field_prefix}.validation.max_length',
                'message': 'max_length is only valid for text and email types'
            })
        elif not isinstance(max_length, int) or max_length < 1 \
                or max_length > _MAX_LENGTH_LIMIT:
            errors.append({
                'field': f'{field_prefix}.validation.max_length',
                'message': f'max_length must be an integer between 1 and '
                           f'{_MAX_LENGTH_LIMIT}'
            })

    if (min_length is not None and max_length is not None
            and isinstance(min_length, int) and isinstance(max_length, int)
            and min_length >= 1 and max_length >= 1):
        if min_length > max_length:
            errors.append({
                'field': f'{field_prefix}.validation',
                'message': f'min_length ({min_length}) must not exceed '
                           f'max_length ({max_length})'
            })

    # minimum / maximum: valid for number type
    minimum = validation.get('minimum')
    maximum = validation.get('maximum')

    if minimum is not None:
        if field_type != 'number':
            errors.append({
                'field': f'{field_prefix}.validation.minimum',
                'message': 'minimum is only valid for number type'
            })
        elif not isinstance(minimum, (int, float)):
            errors.append({
                'field': f'{field_prefix}.validation.minimum',
                'message': 'minimum must be a number'
            })

    if maximum is not None:
        if field_type != 'number':
            errors.append({
                'field': f'{field_prefix}.validation.maximum',
                'message': 'maximum is only valid for number type'
            })
        elif not isinstance(maximum, (int, float)):
            errors.append({
                'field': f'{field_prefix}.validation.maximum',
                'message': 'maximum must be a number'
            })

    if (minimum is not None and maximum is not None
            and isinstance(minimum, (int, float))
            and isinstance(maximum, (int, float))):
        if minimum > maximum:
            errors.append({
                'field': f'{field_prefix}.validation',
                'message': f'minimum ({minimum}) must not exceed '
                           f'maximum ({maximum})'
            })

    # pattern: valid for text and email types
    pattern = validation.get('pattern')
    if pattern is not None:
        if field_type not in ('text', 'email'):
            errors.append({
                'field': f'{field_prefix}.validation.pattern',
                'message': 'pattern is only valid for text and email types'
            })
        elif not isinstance(pattern, str):
            errors.append({
                'field': f'{field_prefix}.validation.pattern',
                'message': 'pattern must be a string'
            })
        elif len(pattern) > _MAX_PATTERN_LENGTH:
            errors.append({
                'field': f'{field_prefix}.validation.pattern',
                'message': f'pattern exceeds maximum length of '
                           f'{_MAX_PATTERN_LENGTH} characters'
            })
        else:
            # Validate that pattern is a valid regex
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append({
                    'field': f'{field_prefix}.validation.pattern',
                    'message': f'pattern is not a valid regex: {e}'
                })


def validate_purchase_rules(
    rules: Any,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate a purchase_rules object.

    Expected structure:
    {
        "max_per_order": 5,
        "max_per_member": 2,
        "max_per_club": 20,
        "min_per_club": 5,
        "requires_membership": True,
        "order_mode": "single"
    }

    Checks:
    - rules is a dict
    - numeric fields: positive integers 1-9999
    - min_per_club <= max_per_club when both defined
    - requires_membership is a boolean
    - order_mode is "single" or "persistent"

    Returns:
        Tuple of (is_valid, errors) where errors is a list of structured
        error dicts with 'field' and 'message' keys.
    """
    errors: List[Dict[str, Any]] = []

    if not isinstance(rules, dict):
        errors.append({
            'field': 'purchase_rules',
            'message': 'purchase_rules must be an object'
        })
        return (False, errors)

    # Validate numeric fields
    numeric_fields = [
        'max_per_order', 'max_per_member', 'max_per_club', 'min_per_club'
    ]

    for field_name in numeric_fields:
        value = rules.get(field_name)
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append({
                    'field': f'purchase_rules.{field_name}',
                    'message': f'{field_name} must be an integer'
                })
            elif value < 1 or value > _MAX_PURCHASE_RULE_VALUE:
                errors.append({
                    'field': f'purchase_rules.{field_name}',
                    'message': f'{field_name} must be between 1 and '
                               f'{_MAX_PURCHASE_RULE_VALUE}'
                })

    # Validate min_per_club <= max_per_club
    min_per_club = rules.get('min_per_club')
    max_per_club = rules.get('max_per_club')

    if (min_per_club is not None and max_per_club is not None
            and isinstance(min_per_club, int)
            and not isinstance(min_per_club, bool)
            and isinstance(max_per_club, int)
            and not isinstance(max_per_club, bool)
            and min_per_club >= 1 and max_per_club >= 1):
        if min_per_club > max_per_club:
            errors.append({
                'field': 'purchase_rules',
                'message': f'min_per_club ({min_per_club}) must not exceed '
                           f'max_per_club ({max_per_club})'
            })

    # Validate requires_membership
    requires_membership = rules.get('requires_membership')
    if requires_membership is not None:
        if not isinstance(requires_membership, bool):
            errors.append({
                'field': 'purchase_rules.requires_membership',
                'message': 'requires_membership must be a boolean'
            })

    # Validate order_mode
    order_mode = rules.get('order_mode')
    if order_mode is not None:
        if not isinstance(order_mode, str):
            errors.append({
                'field': 'purchase_rules.order_mode',
                'message': 'order_mode must be a string'
            })
        elif order_mode not in _VALID_ORDER_MODES:
            errors.append({
                'field': 'purchase_rules.order_mode',
                'message': f'order_mode must be one of: '
                           f'{", ".join(sorted(_VALID_ORDER_MODES))}'
            })

    is_valid = len(errors) == 0
    return (is_valid, errors)
