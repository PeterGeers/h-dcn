"""
Locale resolution utilities for H-DCN backend.

Parses Accept-Language headers, validates locale codes against supported locales,
and resolves member language preferences with Dutch (nl) as the default fallback.
"""

SUPPORTED_LOCALES = {'nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es'}
DEFAULT_LOCALE = 'nl'


def resolve_request_locale(event: dict) -> str:
    """
    Extract and validate locale from the Accept-Language header in a Lambda event.

    Parses the Accept-Language header, extracts the primary language subtag,
    and validates it against SUPPORTED_LOCALES. Returns DEFAULT_LOCALE if
    the header is missing, empty, or contains an unsupported locale.

    Args:
        event: Lambda event dict containing 'headers' with 'Accept-Language'.

    Returns:
        A valid locale string from SUPPORTED_LOCALES.
    """
    if not event or not isinstance(event, dict):
        return DEFAULT_LOCALE

    headers = event.get('headers') or {}

    # Header keys may be mixed-case depending on API Gateway configuration
    accept_language = (
        headers.get('Accept-Language')
        or headers.get('accept-language')
        or ''
    )

    if not accept_language or not isinstance(accept_language, str):
        return DEFAULT_LOCALE

    # Parse Accept-Language header value
    # Format examples: "en", "en-GB", "fr-FR,fr;q=0.9,en;q=0.8", "de, en;q=0.5"
    locale = _parse_accept_language(accept_language)
    return locale if locale else DEFAULT_LOCALE


def resolve_member_locale(preferred_language: str | None) -> str:
    """
    Resolve a member's locale from their stored preferred_language attribute.

    Validates the stored preference against SUPPORTED_LOCALES and returns
    DEFAULT_LOCALE if the value is None, empty, or not a supported locale.

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


def is_valid_locale(locale: str) -> bool:
    """
    Check if a locale string is in the set of SUPPORTED_LOCALES.

    Args:
        locale: A locale string to validate.

    Returns:
        True if the locale is supported, False otherwise.
    """
    if not locale or not isinstance(locale, str):
        return False
    return locale.strip().lower() in SUPPORTED_LOCALES


def _parse_accept_language(header_value: str) -> str | None:
    """
    Parse an Accept-Language header and return the best matching supported locale.

    Supports the full Accept-Language format with quality values (q-factors).
    Returns the highest-priority locale that matches a SUPPORTED_LOCALE,
    or None if no match is found.

    Args:
        header_value: The raw Accept-Language header string.

    Returns:
        A supported locale string, or None if no match found.
    """
    # Split by comma to get individual language entries
    entries = header_value.split(',')
    parsed = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Split by semicolon to separate language tag from quality value
        parts = entry.split(';')
        lang_tag = parts[0].strip().lower()

        # Extract quality value (default 1.0)
        quality = 1.0
        for part in parts[1:]:
            part = part.strip()
            if part.startswith('q='):
                try:
                    quality = float(part[2:])
                except (ValueError, IndexError):
                    quality = 0.0

        if lang_tag:
            parsed.append((lang_tag, quality))

    # Sort by quality descending (stable sort preserves order for equal quality)
    parsed.sort(key=lambda x: x[1], reverse=True)

    # Find first matching supported locale
    for lang_tag, _ in parsed:
        # Extract primary language subtag (e.g., "en" from "en-GB")
        primary = lang_tag.split('-')[0]
        if primary in SUPPORTED_LOCALES:
            return primary

    return None
