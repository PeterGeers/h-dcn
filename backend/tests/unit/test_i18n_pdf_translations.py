"""
Property-based tests for the i18n PDF translations module.

Properties tested:
- Property 8: PDF translation completeness
- Property 9: Backend locale-aware date and currency formatting

**Validates: Requirements 8.2, 8.3, 8.5, 7.6**

Uses Hypothesis to verify:
1. All PDF keys return non-empty strings for all supported locales
2. Invalid locales fall back to Dutch translation
3. format_date_for_locale produces non-empty date strings for any valid datetime
4. format_currency_for_locale produces strings containing € and exactly 2 decimal places
"""

import re
from datetime import datetime

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from shared.i18n.locale_resolver import SUPPORTED_LOCALES
from shared.i18n.pdf_translations import (
    PDF_TRANSLATIONS,
    get_pdf_text,
    format_date_for_locale,
    format_currency_for_locale,
)


# --- Strategies ---

supported_locale_st = st.sampled_from(sorted(SUPPORTED_LOCALES))

# Dutch reference keys: all keys defined in the 'nl' translation set
dutch_keys_st = st.deferred(lambda: st.sampled_from(sorted(PDF_TRANSLATIONS['nl'].keys())))

# Invalid locales: strings that are NOT in the supported set
invalid_locale_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=10,
).filter(lambda s: s.lower() not in SUPPORTED_LOCALES)

# Valid datetimes for formatting tests
valid_datetime_st = st.datetimes(
    min_value=datetime(1900, 1, 1),
    max_value=datetime(2100, 12, 31),
)

# EUR amounts: reasonable financial values including negatives, zero, and large values
eur_amount_st = st.floats(
    min_value=-1_000_000,
    max_value=1_000_000,
    allow_nan=False,
    allow_infinity=False,
)


# --- Property 8: PDF translation completeness ---

class TestPDFTranslationCompleteness:
    """
    Property 8: PDF translation completeness

    For any supported locale and any PDF text key defined in the Dutch reference set,
    get_pdf_text returns a non-empty translated string.

    **Validates: Requirements 8.2, 8.5**
    """

    @given(locale=supported_locale_st, key=dutch_keys_st)
    @settings(max_examples=20)
    def test_all_keys_return_nonempty_for_supported_locales(self, locale, key):
        """
        Property 8a: For any supported locale and any PDF text key defined in the
        Dutch reference set, get_pdf_text returns a non-empty translated string.
        """
        result = get_pdf_text(key, locale)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result.strip()) > 0, (
            f"get_pdf_text('{key}', '{locale}') returned empty string"
        )

    @given(locale=invalid_locale_st, key=dutch_keys_st)
    @settings(max_examples=20)
    def test_invalid_locales_fall_back_to_dutch(self, locale, key):
        """
        Property 8b: For invalid locales, get_pdf_text falls back to Dutch translation.
        """
        result = get_pdf_text(key, locale)
        dutch_result = get_pdf_text(key, 'nl')
        assert result == dutch_result, (
            f"get_pdf_text('{key}', '{locale}') = '{result}' "
            f"but Dutch fallback = '{dutch_result}'"
        )


# --- Property 9: Backend locale-aware date and currency formatting ---

class TestBackendLocaleFormatting:
    """
    Property 9: Backend locale-aware date and currency formatting

    For any valid datetime and supported locale, format_date_for_locale produces
    a non-empty date string. For any numeric EUR amount and supported locale,
    format_currency_for_locale produces a string containing € and exactly 2 decimals.

    **Validates: Requirements 7.6, 8.3**
    """

    @given(date=valid_datetime_st, locale=supported_locale_st)
    @settings(max_examples=20)
    def test_format_date_produces_nonempty_string(self, date, locale):
        """
        Property 9a: For any valid datetime and any supported locale,
        format_date_for_locale produces a non-empty date string.
        """
        result = format_date_for_locale(date, locale)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result.strip()) > 0, (
            f"format_date_for_locale({date}, '{locale}') returned empty string"
        )

    @given(amount=eur_amount_st, locale=supported_locale_st)
    @settings(max_examples=20)
    def test_format_currency_contains_euro_symbol_and_two_decimals(self, amount, locale):
        """
        Property 9b: For any numeric EUR amount and any supported locale,
        format_currency_for_locale produces a string containing the Euro symbol (€)
        and exactly 2 decimal places.
        """
        result = format_currency_for_locale(amount, locale)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result.strip()) > 0, (
            f"format_currency_for_locale({amount}, '{locale}') returned empty string"
        )
        # Must contain the Euro symbol
        assert '€' in result, (
            f"format_currency_for_locale({amount}, '{locale}') = '{result}' "
            f"does not contain '€'"
        )
        # Must contain exactly 2 decimal places
        # Match a pattern like digits + decimal separator + exactly 2 digits
        # Decimal separator can be '.' or ',' depending on locale
        decimal_pattern = r'[\d][\.,](\d{2})(?!\d)'
        match = re.search(decimal_pattern, result)
        assert match is not None, (
            f"format_currency_for_locale({amount}, '{locale}') = '{result}' "
            f"does not contain exactly 2 decimal places"
        )
