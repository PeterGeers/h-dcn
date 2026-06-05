"""
Unit tests for the email locale resolution utility module.

Tests resolve_email_locale, get_email_template_path, format_email_date,
and format_email_currency functions.
"""

import os
import tempfile
from datetime import datetime

import pytest

from shared.i18n.email_utils import (
    resolve_email_locale,
    get_email_template_path,
    format_email_date,
    format_email_currency,
)
from shared.i18n.locale_resolver import SUPPORTED_LOCALES, DEFAULT_LOCALE


class TestResolveEmailLocale:
    """Tests for resolve_email_locale function."""

    @pytest.mark.parametrize("locale", list(SUPPORTED_LOCALES))
    def test_valid_locale_returns_same(self, locale):
        assert resolve_email_locale(locale) == locale

    def test_none_returns_default(self):
        assert resolve_email_locale(None) == DEFAULT_LOCALE

    def test_empty_string_returns_default(self):
        assert resolve_email_locale("") == DEFAULT_LOCALE

    def test_unsupported_locale_returns_default(self):
        assert resolve_email_locale("pt") == DEFAULT_LOCALE
        assert resolve_email_locale("ja") == DEFAULT_LOCALE
        assert resolve_email_locale("zh") == DEFAULT_LOCALE

    def test_case_insensitive(self):
        assert resolve_email_locale("EN") == "en"
        assert resolve_email_locale("Fr") == "fr"
        assert resolve_email_locale("NL") == "nl"

    def test_whitespace_handling(self):
        assert resolve_email_locale("  en  ") == "en"
        assert resolve_email_locale(" fr") == "fr"

    def test_non_string_returns_default(self):
        assert resolve_email_locale(123) == DEFAULT_LOCALE
        assert resolve_email_locale([]) == DEFAULT_LOCALE


class TestGetEmailTemplatePath:
    """Tests for get_email_template_path function."""

    def test_returns_locale_path_without_base_dir(self):
        path = get_email_template_path("welcome-user.html", "en")
        assert path == "templates/en/welcome-user.html"

    def test_returns_nl_path_for_default_locale(self):
        path = get_email_template_path("welcome-user.html", "nl")
        assert path == "templates/nl/welcome-user.html"

    def test_invalid_locale_falls_back_to_nl_without_base_dir(self):
        path = get_email_template_path("welcome-user.html", "xx")
        assert path == "templates/nl/welcome-user.html"

    def test_empty_locale_falls_back_to_nl(self):
        path = get_email_template_path("welcome-user.html", "")
        assert path == "templates/nl/welcome-user.html"

    def test_none_locale_falls_back_to_nl(self):
        path = get_email_template_path("welcome-user.html", None)
        assert path == "templates/nl/welcome-user.html"

    def test_with_base_dir_locale_file_exists(self):
        """When the locale-specific file exists, return that path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create locale directory with template
            en_dir = os.path.join(tmpdir, "en")
            os.makedirs(en_dir)
            template_path = os.path.join(en_dir, "welcome-user.html")
            with open(template_path, "w") as f:
                f.write("<html>English</html>")

            result = get_email_template_path("welcome-user.html", "en", tmpdir)
            assert result == template_path

    def test_with_base_dir_falls_back_to_nl(self):
        """When the locale file doesn't exist, fall back to nl."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only create nl directory with template
            nl_dir = os.path.join(tmpdir, "nl")
            os.makedirs(nl_dir)
            nl_template_path = os.path.join(nl_dir, "welcome-user.html")
            with open(nl_template_path, "w") as f:
                f.write("<html>Dutch</html>")

            result = get_email_template_path("welcome-user.html", "fr", tmpdir)
            assert result == nl_template_path

    def test_with_base_dir_neither_exists_returns_nl_path(self):
        """When neither locale nor nl file exists, return nl path anyway."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_email_template_path("welcome-user.html", "en", tmpdir)
            expected = os.path.join(tmpdir, "nl", "welcome-user.html")
            assert result == expected


class TestFormatEmailDate:
    """Tests for format_email_date function."""

    def test_dutch_format(self):
        date = datetime(2025, 1, 15)
        result = format_email_date(date, "nl")
        assert result == "15 januari 2025"

    def test_english_format(self):
        date = datetime(2025, 1, 15)
        result = format_email_date(date, "en")
        assert result == "15 January 2025"

    def test_german_format(self):
        date = datetime(2025, 1, 15)
        result = format_email_date(date, "de")
        assert result == "15. Januar 2025"

    def test_spanish_format(self):
        date = datetime(2025, 1, 15)
        result = format_email_date(date, "es")
        assert result == "15 de enero de 2025"

    def test_none_date_returns_empty(self):
        assert format_email_date(None, "en") == ""

    def test_invalid_locale_uses_nl(self):
        date = datetime(2025, 6, 20)
        result = format_email_date(date, "xx")
        assert result == "20 juni 2025"

    def test_case_insensitive_locale(self):
        date = datetime(2025, 3, 10)
        result = format_email_date(date, "EN")
        assert result == "10 March 2025"


class TestFormatEmailCurrency:
    """Tests for format_email_currency function."""

    def test_dutch_format(self):
        result = format_email_currency(1234.56, "nl")
        assert "€" in result
        assert "1.234,56" in result

    def test_english_format(self):
        result = format_email_currency(1234.56, "en")
        assert "€" in result
        assert "1,234.56" in result

    def test_french_format(self):
        result = format_email_currency(1234.56, "fr")
        assert "€" in result
        assert "1" in result
        assert "234,56" in result

    def test_none_amount_returns_empty(self):
        assert format_email_currency(None, "en") == ""

    def test_zero_amount(self):
        result = format_email_currency(0.00, "nl")
        assert "€" in result
        assert "0,00" in result

    def test_invalid_locale_uses_nl(self):
        result = format_email_currency(99.99, "xx")
        assert "€" in result
        assert "99,99" in result

    def test_case_insensitive_locale(self):
        result = format_email_currency(50.00, "EN")
        assert "€" in result
        assert "50.00" in result
