"""
Email locale resolution and formatting utilities for H-DCN transactional emails.

Provides helpers to resolve the correct email locale from a member's preferred_language,
resolve template paths with Dutch fallback, and format dates/currency in emails
using locale conventions.
"""

import os
from datetime import datetime

from shared.i18n.locale_resolver import (
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
    is_valid_locale,
)
from shared.i18n.pdf_translations import (
    format_date_for_locale,
    format_currency_for_locale,
)


def resolve_email_locale(preferred_language: str | None) -> str:
    """
    Resolve the email locale from a member's preferred_language attribute.

    Validates the preferred_language against SUPPORTED_LOCALES and returns
    DEFAULT_LOCALE (nl) if the value is None, empty, or unsupported.

    Args:
        preferred_language: The member's preferred_language value from DynamoDB.
            May be None, empty string, or any string value.

    Returns:
        A valid locale string from SUPPORTED_LOCALES.
    """
    if not preferred_language or not isinstance(preferred_language, str):
        return DEFAULT_LOCALE

    locale = preferred_language.strip().lower()

    if is_valid_locale(locale):
        return locale

    return DEFAULT_LOCALE


def get_email_template_path(
    template_name: str, locale: str, templates_base_dir: str | None = None
) -> str:
    """
    Resolve the path to a locale-specific email template with Dutch fallback.

    Checks if the template file exists in the locale-specific directory
    (`templates/{locale}/{template_name}`). If the locale directory or file
    doesn't exist, falls back to `templates/nl/{template_name}`.

    Args:
        template_name: The template filename (e.g., "welcome-user.html").
        locale: The locale code (e.g., "en", "fr").
        templates_base_dir: Optional base directory for templates. If not provided,
            defaults to the standard email-templates/templates/ path.

    Returns:
        The resolved template path string (relative to templates_base_dir
        if provided, otherwise as `templates/{locale}/{template_name}`).
    """
    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if not is_valid_locale(resolved_locale):
        resolved_locale = DEFAULT_LOCALE

    if templates_base_dir:
        # Check if the locale-specific template file exists on disk
        locale_path = os.path.join(templates_base_dir, resolved_locale, template_name)
        if os.path.isfile(locale_path):
            return locale_path

        # Fallback to Dutch template
        nl_path = os.path.join(templates_base_dir, DEFAULT_LOCALE, template_name)
        if os.path.isfile(nl_path):
            return nl_path

        # If neither exists, return the Dutch path anyway (caller handles missing file)
        return nl_path
    else:
        # Return a relative path pattern (for use without filesystem checks)
        return f"templates/{resolved_locale}/{template_name}"


def format_email_date(date: datetime, locale: str) -> str:
    """
    Format a date for email content using locale conventions.

    Delegates to the shared format_date_for_locale function which produces
    locale-appropriate date strings (e.g., "15 januari 2025" for nl,
    "15 January 2025" for en).

    Args:
        date: The datetime object to format.
        locale: The locale code (e.g., "en", "fr", "de").

    Returns:
        A locale-formatted date string. Returns empty string if date is None.
    """
    if date is None:
        return ""

    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if not is_valid_locale(resolved_locale):
        resolved_locale = DEFAULT_LOCALE

    return format_date_for_locale(date, resolved_locale)


def format_email_currency(amount: float, locale: str) -> str:
    """
    Format a EUR currency amount for email content using locale conventions.

    Delegates to the shared format_currency_for_locale function which produces
    locale-appropriate EUR formatted strings (e.g., "€ 1.234,56" for nl,
    "€1,234.56" for en).

    Args:
        amount: The numeric EUR amount to format.
        locale: The locale code (e.g., "en", "fr", "de").

    Returns:
        A locale-formatted EUR currency string. Returns empty string if amount is None.
    """
    if amount is None:
        return ""

    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if not is_valid_locale(resolved_locale):
        resolved_locale = DEFAULT_LOCALE

    return format_currency_for_locale(amount, resolved_locale)
