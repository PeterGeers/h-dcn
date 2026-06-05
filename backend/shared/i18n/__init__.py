"""
Shared internationalization (i18n) module for H-DCN Lambda functions.
Provides locale resolution, error message localization, PDF translations,
and email locale utilities across all backend functions.

Supported locales: nl, en, fr, de, sv, da, it, es
Default/fallback locale: nl (Dutch)
"""

from shared.i18n.locale_resolver import (
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
    resolve_request_locale,
    resolve_member_locale,
    is_valid_locale,
)
from shared.i18n.error_messages import (
    ERROR_MESSAGES,
    get_error_message,
)
from shared.i18n.pdf_translations import (
    PDF_TRANSLATIONS,
    get_pdf_text,
    format_date_for_locale,
    format_currency_for_locale,
)
from shared.i18n.email_utils import (
    resolve_email_locale,
    get_email_template_path,
    format_email_date,
    format_email_currency,
)

__all__ = [
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "resolve_request_locale",
    "resolve_member_locale",
    "is_valid_locale",
    "ERROR_MESSAGES",
    "get_error_message",
    "PDF_TRANSLATIONS",
    "get_pdf_text",
    "format_date_for_locale",
    "format_currency_for_locale",
    "resolve_email_locale",
    "get_email_template_path",
    "format_email_date",
    "format_email_currency",
]
