"""
Unit tests and property-based tests for the i18n locale resolver module.

Tests cover:
- resolve_request_locale: Accept-Language header parsing and validation
- resolve_member_locale: Member preferred_language resolution
- is_valid_locale: Locale validation against supported set
- _parse_accept_language: Header parsing with quality values

Requirements validated: 6.3, 6.4, 6.5
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from shared.i18n.locale_resolver import (
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
    resolve_request_locale,
    resolve_member_locale,
    is_valid_locale,
    _parse_accept_language,
)


class TestSupportedLocalesAndDefault:
    """Test module-level constants."""

    def test_supported_locales_contains_all_eight(self):
        expected = {'nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'}
        assert SUPPORTED_LOCALES == expected

    def test_default_locale_is_dutch(self):
        assert DEFAULT_LOCALE == 'nl'


class TestIsValidLocale:
    """Test is_valid_locale function."""

    @pytest.mark.parametrize("locale", ['nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'])
    def test_valid_locales(self, locale):
        assert is_valid_locale(locale) is True

    @pytest.mark.parametrize("locale", ['NL', 'EN', 'Fr', 'DE'])
    def test_valid_locales_case_insensitive(self, locale):
        assert is_valid_locale(locale) is True

    @pytest.mark.parametrize("locale", ['pt', 'ja', 'zh', 'ru', 'xx', 'invalid'])
    def test_invalid_locales(self, locale):
        assert is_valid_locale(locale) is False

    def test_empty_string(self):
        assert is_valid_locale('') is False

    def test_none_value(self):
        assert is_valid_locale(None) is False

    def test_numeric_input(self):
        assert is_valid_locale(123) is False

    def test_whitespace_locale(self):
        assert is_valid_locale(' en ') is True


class TestResolveRequestLocale:
    """Test resolve_request_locale with various Lambda event shapes."""

    def test_valid_accept_language_simple(self):
        event = {'headers': {'Accept-Language': 'en'}}
        assert resolve_request_locale(event) == 'en'

    def test_valid_accept_language_with_region(self):
        event = {'headers': {'Accept-Language': 'fr-FR'}}
        assert resolve_request_locale(event) == 'fr'

    def test_accept_language_with_quality_values(self):
        event = {'headers': {'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'}}
        assert resolve_request_locale(event) == 'de'

    def test_accept_language_picks_highest_quality_supported(self):
        # pt has highest quality but is unsupported; en is next
        event = {'headers': {'Accept-Language': 'pt;q=1.0,en;q=0.8,nl;q=0.5'}}
        assert resolve_request_locale(event) == 'en'

    def test_unsupported_locale_falls_back_to_nl(self):
        event = {'headers': {'Accept-Language': 'ja-JP'}}
        assert resolve_request_locale(event) == 'nl'

    def test_missing_header_falls_back_to_nl(self):
        event = {'headers': {}}
        assert resolve_request_locale(event) == 'nl'

    def test_none_headers_falls_back_to_nl(self):
        event = {'headers': None}
        assert resolve_request_locale(event) == 'nl'

    def test_no_headers_key_falls_back_to_nl(self):
        event = {}
        assert resolve_request_locale(event) == 'nl'

    def test_none_event_falls_back_to_nl(self):
        assert resolve_request_locale(None) == 'nl'

    def test_empty_accept_language_falls_back_to_nl(self):
        event = {'headers': {'Accept-Language': ''}}
        assert resolve_request_locale(event) == 'nl'

    def test_lowercase_header_key(self):
        event = {'headers': {'accept-language': 'sv'}}
        assert resolve_request_locale(event) == 'sv'

    def test_wildcard_accept_language_falls_back_to_nl(self):
        event = {'headers': {'Accept-Language': '*'}}
        assert resolve_request_locale(event) == 'nl'

    def test_complex_accept_language_header(self):
        event = {'headers': {'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'}}
        assert resolve_request_locale(event) == 'it'

    def test_non_string_accept_language_falls_back_to_nl(self):
        event = {'headers': {'Accept-Language': 123}}
        assert resolve_request_locale(event) == 'nl'

    def test_non_dict_event_falls_back_to_nl(self):
        assert resolve_request_locale("not a dict") == 'nl'
        assert resolve_request_locale([]) == 'nl'


class TestResolveMemberLocale:
    """Test resolve_member_locale with various stored preference values."""

    @pytest.mark.parametrize("locale", ['nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'])
    def test_valid_preferred_language(self, locale):
        assert resolve_member_locale(locale) == locale

    def test_none_preferred_language(self):
        assert resolve_member_locale(None) == 'nl'

    def test_empty_preferred_language(self):
        assert resolve_member_locale('') == 'nl'

    def test_unsupported_preferred_language(self):
        assert resolve_member_locale('pt') == 'nl'

    def test_invalid_string_preferred_language(self):
        assert resolve_member_locale('not-a-locale') == 'nl'

    def test_uppercase_preferred_language(self):
        assert resolve_member_locale('EN') == 'en'

    def test_whitespace_preferred_language(self):
        assert resolve_member_locale(' fr ') == 'fr'

    def test_non_string_preferred_language(self):
        assert resolve_member_locale(42) == 'nl'


class TestParseAcceptLanguage:
    """Test the internal _parse_accept_language function."""

    def test_simple_locale(self):
        assert _parse_accept_language('en') == 'en'

    def test_locale_with_region(self):
        assert _parse_accept_language('en-GB') == 'en'

    def test_multiple_locales_with_quality(self):
        assert _parse_accept_language('fr;q=0.9,en;q=1.0') == 'en'

    def test_all_unsupported_returns_none(self):
        assert _parse_accept_language('ja,zh;q=0.9') is None

    def test_empty_string_returns_none(self):
        assert _parse_accept_language('') is None

    def test_malformed_quality_value(self):
        # Malformed q= should default to 0.0 quality
        result = _parse_accept_language('en;q=abc,fr;q=0.9')
        assert result == 'fr'

    def test_multiple_supported_picks_highest_quality(self):
        result = _parse_accept_language('da;q=0.5,sv;q=0.9,nl;q=0.7')
        assert result == 'sv'

    def test_equal_quality_preserves_order(self):
        result = _parse_accept_language('es,it')
        assert result == 'es'


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================
# **Validates: Requirements 6.3, 6.4**
# Property 1: Locale resolution priority (backend)
#
# For any combination of Accept-Language header (valid locale, invalid locale,
# missing header, malformed values), resolve_request_locale returns a value
# from SUPPORTED_LOCALES, defaulting to 'nl' for invalid inputs.
#
# For any preferred_language value (valid, invalid, None, empty),
# resolve_member_locale returns a value from SUPPORTED_LOCALES, defaulting to 'nl'.
# =============================================================================


# --- Strategies ---

# Valid supported locale codes
supported_locale_st = st.sampled_from(sorted(SUPPORTED_LOCALES))

# Invalid locale codes: arbitrary text that is NOT in SUPPORTED_LOCALES
invalid_locale_st = st.text(min_size=1, max_size=20).filter(
    lambda s: s.strip().lower() not in SUPPORTED_LOCALES
)

# Preferred language values: valid, invalid, None, or empty
preferred_language_st = st.one_of(
    supported_locale_st,
    invalid_locale_st,
    st.none(),
    st.just(''),
)

# Accept-Language header values: valid locales, with regions, quality values, invalid, empty
accept_language_header_st = st.one_of(
    # Simple supported locale
    supported_locale_st,
    # Supported locale with region subtag (e.g., "en-GB")
    supported_locale_st.map(lambda loc: f"{loc}-{loc.upper()}"),
    # Supported locale with quality value
    supported_locale_st.flatmap(
        lambda loc: st.floats(min_value=0.0, max_value=1.0, allow_nan=False).map(
            lambda q: f"{loc};q={q:.1f}"
        )
    ),
    # Unsupported locale
    st.sampled_from(['ja', 'zh', 'pt', 'ru', 'ko', 'ar', 'hi']),
    # Wildcard
    st.just('*'),
    # Multiple entries with mixed supported/unsupported
    st.tuples(
        st.sampled_from(['ja', 'zh', 'pt', 'ru']),
        supported_locale_st,
    ).map(lambda t: f"{t[0]};q=1.0,{t[1]};q=0.8"),
    # Empty string
    st.just(''),
    # Arbitrary text (malformed)
    st.text(min_size=0, max_size=50),
)


class TestPropertyResolveRequestLocale:
    """
    Property-based tests for resolve_request_locale.

    **Validates: Requirements 6.3, 6.4**

    Property: For any Accept-Language header value (valid, invalid, missing,
    malformed), resolve_request_locale always returns a value from SUPPORTED_LOCALES.
    Missing or invalid headers default to 'nl'.
    """

    @given(header_value=accept_language_header_st)
    @settings(max_examples=20)
    def test_always_returns_supported_locale(self, header_value):
        """resolve_request_locale always returns a locale in SUPPORTED_LOCALES."""
        event = {'headers': {'Accept-Language': header_value}}
        result = resolve_request_locale(event)
        assert result in SUPPORTED_LOCALES

    @given(header_value=accept_language_header_st)
    @settings(max_examples=20)
    def test_missing_header_defaults_to_nl(self, header_value):
        """When headers dict is empty, result is always DEFAULT_LOCALE."""
        event = {'headers': {}}
        result = resolve_request_locale(event)
        assert result == DEFAULT_LOCALE

    @given(locale=supported_locale_st)
    @settings(max_examples=20)
    def test_valid_locale_in_header_is_resolved(self, locale):
        """A valid supported locale in Accept-Language is returned as-is."""
        event = {'headers': {'Accept-Language': locale}}
        result = resolve_request_locale(event)
        assert result == locale

    @given(locale=invalid_locale_st)
    @settings(max_examples=20)
    def test_invalid_locale_in_header_defaults_to_nl(self, locale):
        """An invalid locale that doesn't match any supported locale defaults to nl."""
        # Ensure the locale's primary subtag is also not in SUPPORTED_LOCALES
        primary = locale.strip().lower().split('-')[0]
        assume(primary not in SUPPORTED_LOCALES)
        event = {'headers': {'Accept-Language': locale}}
        result = resolve_request_locale(event)
        assert result == DEFAULT_LOCALE

    @given(data=st.data())
    @settings(max_examples=20)
    def test_none_and_empty_events_default_to_nl(self, data):
        """None events, missing headers, and None headers all default to nl."""
        event = data.draw(st.one_of(
            st.none(),
            st.just({}),
            st.just({'headers': None}),
            st.just({'headers': {}}),
        ))
        result = resolve_request_locale(event)
        assert result == DEFAULT_LOCALE


class TestPropertyResolveMemberLocale:
    """
    Property-based tests for resolve_member_locale.

    **Validates: Requirements 6.3, 6.4**

    Property: For any preferred_language value (valid, invalid, None, empty),
    resolve_member_locale always returns a value from SUPPORTED_LOCALES,
    defaulting to 'nl' for invalid inputs.
    """

    @given(preferred_language=preferred_language_st)
    @settings(max_examples=20)
    def test_always_returns_supported_locale(self, preferred_language):
        """resolve_member_locale always returns a locale in SUPPORTED_LOCALES."""
        result = resolve_member_locale(preferred_language)
        assert result in SUPPORTED_LOCALES

    @given(locale=supported_locale_st)
    @settings(max_examples=20)
    def test_valid_locale_is_returned(self, locale):
        """A valid supported locale is returned as-is."""
        result = resolve_member_locale(locale)
        assert result == locale

    @given(locale=invalid_locale_st)
    @settings(max_examples=20)
    def test_invalid_locale_defaults_to_nl(self, locale):
        """An invalid preferred_language defaults to nl."""
        assume(locale.strip().lower() not in SUPPORTED_LOCALES)
        result = resolve_member_locale(locale)
        assert result == DEFAULT_LOCALE

    @given(value=st.one_of(st.none(), st.just('')))
    @settings(max_examples=20)
    def test_none_and_empty_default_to_nl(self, value):
        """None and empty string default to nl."""
        result = resolve_member_locale(value)
        assert result == DEFAULT_LOCALE

    @given(locale=supported_locale_st)
    @settings(max_examples=20)
    def test_case_insensitive_resolution(self, locale):
        """Uppercase valid locales are resolved correctly."""
        result = resolve_member_locale(locale.upper())
        assert result == locale
