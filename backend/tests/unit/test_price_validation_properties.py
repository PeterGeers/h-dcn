"""
Property-based tests for validate_price_field shared helper.

Tests the core validation logic using hypothesis to generate a wide range
of inputs and verify correctness properties hold across all of them.
"""

import sys
import os
from decimal import Decimal, InvalidOperation

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Add handler/shared to path so we can import price_validation
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'shared')
    ),
)

from price_validation import validate_price_field


# --- Hypothesis strategies ---

# Strategy for integers (valid numeric input)
int_st = st.integers(min_value=-10**9, max_value=10**9)

# Strategy for floats (valid numeric input, exclude NaN/Inf)
float_st = st.floats(
    min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False
)

# Strategy for Decimals (valid numeric input)
decimal_st = st.decimals(
    min_value=Decimal('-1000000000'),
    max_value=Decimal('1000000000'),
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for numeric strings (string representations of valid numbers)
numeric_string_st = st.one_of(
    int_st.map(str),
    float_st.map(lambda f: str(f)),
    decimal_st.map(str),
    st.from_regex(r'-?\d{1,8}(\.\d{1,4})?', fullmatch=True),
)

# Strategy for non-numeric strings (things that cannot be parsed as Decimal)
non_numeric_string_st = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'P', 'S', 'Z'),
        blacklist_characters='0123456789+-.eE',
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != '')

# Strategy for booleans
bool_st = st.booleans()

# Strategy for lists
list_st = st.lists(st.integers(), min_size=0, max_size=5)

# Strategy for dicts
dict_st = st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), min_size=0, max_size=3)


# --- Property 1: Numeric inputs produce equivalent Decimal ---

@settings(max_examples=100, deadline=None)
@given(value=int_st)
def test_property1_int_inputs_produce_equivalent_decimal(value):
    """
    Property 1: Numeric inputs produce equivalent Decimal.

    **Validates: Requirements 2.1, 6.1**

    For any integer input, validate_price_field returns a Decimal equal to the input.
    """
    result, error = validate_price_field(value)
    assert error is None, f"Expected no error for int {value}, got: {error}"
    assert result is not None, f"Expected Decimal for int {value}, got None"
    assert result == Decimal(str(value)), (
        f"Expected Decimal({value}), got {result}"
    )


@settings(max_examples=100, deadline=None)
@given(value=float_st)
def test_property1_float_inputs_produce_equivalent_decimal(value):
    """
    Property 1: Numeric inputs produce equivalent Decimal.

    **Validates: Requirements 2.1, 6.1**

    For any finite float input, validate_price_field returns a Decimal equal to the input.
    """
    result, error = validate_price_field(value)
    assert error is None, f"Expected no error for float {value}, got: {error}"
    assert result is not None, f"Expected Decimal for float {value}, got None"
    assert result == Decimal(str(value)), (
        f"Expected Decimal(str({value}))={Decimal(str(value))}, got {result}"
    )


@settings(max_examples=100, deadline=None)
@given(value=decimal_st)
def test_property1_decimal_inputs_produce_equivalent_decimal(value):
    """
    Property 1: Numeric inputs produce equivalent Decimal.

    **Validates: Requirements 2.1, 6.1**

    For any finite Decimal input, validate_price_field returns the same Decimal value.
    """
    result, error = validate_price_field(value)
    assert error is None, f"Expected no error for Decimal {value}, got: {error}"
    assert result is not None, f"Expected Decimal for input {value}, got None"
    assert result == Decimal(str(value)), (
        f"Expected Decimal(str({value}))={Decimal(str(value))}, got {result}"
    )


@settings(max_examples=100, deadline=None)
@given(value=numeric_string_st)
def test_property1_numeric_string_inputs_produce_equivalent_decimal(value):
    """
    Property 1: Numeric inputs produce equivalent Decimal.

    **Validates: Requirements 2.1, 6.1**

    For any numeric string input, validate_price_field returns a Decimal
    equal to the parsed value.
    """
    # Verify the string is actually parseable as Decimal
    try:
        expected = Decimal(value.strip())
    except InvalidOperation:
        assume(False)
    assume(expected.is_finite())

    result, error = validate_price_field(value)
    assert error is None, f"Expected no error for numeric string '{value}', got: {error}"
    assert result is not None, f"Expected Decimal for numeric string '{value}', got None"
    assert result == expected, (
        f"Expected {expected}, got {result} for input '{value}'"
    )


# --- Property 2: Non-numeric inputs are always rejected ---

@settings(max_examples=100, deadline=None)
@given(value=non_numeric_string_st)
def test_property2_non_numeric_strings_are_rejected(value):
    """
    Property 2: Non-numeric inputs are always rejected.

    **Validates: Requirements 2.2, 6.2**

    For any non-numeric string, validate_price_field returns (None, error_message).
    """
    result, error = validate_price_field(value)
    assert result is None, f"Expected None for non-numeric string '{value}', got: {result}"
    assert error is not None, f"Expected error message for non-numeric string '{value}'"
    assert 'numeric' in error.lower(), f"Error message should mention 'numeric': {error}"


@settings(max_examples=100, deadline=None)
@given(value=bool_st)
def test_property2_booleans_are_rejected(value):
    """
    Property 2: Non-numeric inputs are always rejected.

    **Validates: Requirements 2.2, 6.2**

    Booleans (True/False) are rejected even though bool is subclass of int.
    """
    result, error = validate_price_field(value)
    assert result is None, f"Expected None for bool {value}, got: {result}"
    assert error is not None, f"Expected error message for bool {value}"


@settings(max_examples=100, deadline=None)
@given(value=list_st)
def test_property2_lists_are_rejected(value):
    """
    Property 2: Non-numeric inputs are always rejected.

    **Validates: Requirements 2.2, 6.2**

    Lists are always rejected regardless of content.
    """
    result, error = validate_price_field(value)
    assert result is None, f"Expected None for list {value}, got: {result}"
    assert error is not None, f"Expected error message for list {value}"


@settings(max_examples=100, deadline=None)
@given(value=dict_st)
def test_property2_dicts_are_rejected(value):
    """
    Property 2: Non-numeric inputs are always rejected.

    **Validates: Requirements 2.2, 6.2**

    Dicts are always rejected regardless of content.
    """
    result, error = validate_price_field(value)
    assert result is None, f"Expected None for dict {value}, got: {result}"
    assert error is not None, f"Expected error message for dict {value}"


# --- Property 3: String-Decimal round-trip consistency ---

@settings(max_examples=100, deadline=None)
@given(value=st.one_of(int_st, float_st))
def test_property3_string_decimal_round_trip_consistency(value):
    """
    Property 3: String-Decimal round-trip consistency.

    **Validates: Requirements 2.4, 6.3**

    For valid numeric x: validate_price_field(str(Decimal(str(x)))) == validate_price_field(x)
    """
    # Get the direct result
    direct_result, direct_error = validate_price_field(value)
    assert direct_error is None, f"Expected no error for {value}"
    assert direct_result is not None

    # Round-trip: value -> str -> Decimal -> str -> validate
    round_trip_str = str(Decimal(str(value)))
    round_trip_result, round_trip_error = validate_price_field(round_trip_str)

    assert round_trip_error is None, (
        f"Expected no error for round-trip string '{round_trip_str}'"
    )
    assert round_trip_result is not None
    assert direct_result == round_trip_result, (
        f"Round-trip mismatch: validate({value})={direct_result} vs "
        f"validate('{round_trip_str}')={round_trip_result}"
    )


# --- Property 4: Successful validation never returns NaN or Infinity ---

@settings(max_examples=100, deadline=None)
@given(
    value=st.one_of(
        int_st,
        float_st,
        decimal_st,
        numeric_string_st,
        # Include some edge-case strings that might produce special values
        st.sampled_from(['inf', '-inf', 'nan', 'NaN', 'Infinity', '-Infinity', 'INF']),
    )
)
def test_property4_successful_validation_never_returns_nan_or_infinity(value):
    """
    Property 4: Successful validation never returns NaN or Infinity.

    **Validates: Requirements 2.5**

    For any input where result[0] is not None, verify result[0].is_finite().
    """
    result, error = validate_price_field(value)

    if result is not None:
        assert result.is_finite(), (
            f"Expected finite Decimal for input {value!r}, got {result} "
            f"(is_nan={result.is_nan()}, is_infinite={result.is_infinite()})"
        )
