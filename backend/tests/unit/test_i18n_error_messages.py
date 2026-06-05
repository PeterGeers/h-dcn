"""
Property-based tests for the i18n error messages module.

**Validates: Requirements 6.2, 6.3, 6.4**

Property 7: Backend error message localization with fallback
- For any error key present in ERROR_MESSAGES and any valid locale,
  get_error_message returns a non-empty localized message.
- For any error key and any invalid/empty locale, get_error_message
  returns the Dutch (nl) message.
- For any unknown error_key, get_error_message returns a non-empty fallback string.
- The returned message is always a non-empty string (never None, never empty).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shared.i18n.error_messages import ERROR_MESSAGES, get_error_message
from shared.i18n.locale_resolver import SUPPORTED_LOCALES, DEFAULT_LOCALE


# Strategies
valid_locales_st = st.sampled_from(sorted(SUPPORTED_LOCALES))
valid_error_keys_st = st.sampled_from(sorted(ERROR_MESSAGES.keys()))

# Invalid locales: strings that are NOT in SUPPORTED_LOCALES
invalid_locale_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
    min_size=0,
    max_size=20,
).filter(lambda s: s.strip().lower() not in SUPPORTED_LOCALES)

# Unknown error keys: strings that are NOT in ERROR_MESSAGES
unknown_error_key_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P')),
    min_size=1,
    max_size=50,
).filter(lambda s: s not in ERROR_MESSAGES)


class TestErrorMessageLocalizationProperty:
    """
    Property 7: Backend error message localization with fallback.

    **Validates: Requirements 6.2, 6.3, 6.4**
    """

    @given(error_key=valid_error_keys_st, locale=valid_locales_st)
    @settings(max_examples=20)
    def test_valid_key_valid_locale_returns_non_empty_string(self, error_key, locale):
        """
        For any error key in ERROR_MESSAGES and any valid locale in SUPPORTED_LOCALES,
        get_error_message returns a non-empty string.

        **Validates: Requirements 6.2**
        """
        result = get_error_message(error_key, locale)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(error_key=valid_error_keys_st, locale=invalid_locale_st)
    @settings(max_examples=20)
    def test_valid_key_invalid_locale_returns_dutch_message(self, error_key, locale):
        """
        For any error key and any invalid/empty locale (not in SUPPORTED_LOCALES),
        get_error_message returns the Dutch (nl) message for that key.

        **Validates: Requirements 6.3, 6.4**
        """
        result = get_error_message(error_key, locale)
        expected_nl = ERROR_MESSAGES[error_key][DEFAULT_LOCALE]
        assert result == expected_nl

    @given(error_key=unknown_error_key_st, locale=valid_locales_st)
    @settings(max_examples=20)
    def test_unknown_key_returns_non_empty_fallback(self, error_key, locale):
        """
        For any unknown error_key (not in ERROR_MESSAGES),
        get_error_message returns a non-empty fallback string.

        **Validates: Requirements 6.4**
        """
        result = get_error_message(error_key, locale)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(
        error_key=st.one_of(valid_error_keys_st, unknown_error_key_st),
        locale=st.one_of(valid_locales_st, invalid_locale_st),
    )
    @settings(max_examples=20)
    def test_return_value_always_non_empty_string(self, error_key, locale):
        """
        The returned message is always a non-empty string (never None, never empty),
        regardless of input combination.

        **Validates: Requirements 6.2, 6.3, 6.4**
        """
        result = get_error_message(error_key, locale)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
