"""
Price field validation module.

Provides a shared helper to validate and coerce price values to Decimal
before storing in DynamoDB as Number type.
"""

from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional


def validate_price_field(
    value, field_name: str = 'price'
) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Validate and coerce a price value to Decimal.

    Returns (decimal_value, None) on success, or (None, error_message) on failure.
    Accepts: int, float, str representation of a number, Decimal.
    Rejects: non-numeric strings, lists, dicts, empty strings, booleans.
    None input returns (None, None) — field is optional.

    The returned Decimal is always finite (never NaN or Infinity).
    """
    if value is None:
        return None, None

    # bool must be checked before int (bool is subclass of int in Python)
    if isinstance(value, bool):
        return None, f'{field_name} must be a numeric value'

    if isinstance(value, (int, float, Decimal)):
        result = Decimal(str(value))
        if not result.is_finite():
            return None, f'{field_name} must be a numeric value'
        return result, None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None, f'{field_name} must be a numeric value'
        try:
            result = Decimal(value)
            if not result.is_finite():
                return None, f'{field_name} must be a numeric value'
            return result, None
        except InvalidOperation:
            return None, f'{field_name} must be a numeric value'

    return None, f'{field_name} must be a numeric value'
