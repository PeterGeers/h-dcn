/**
 * Locale resolution logic for the H-DCN portal.
 *
 * Determines the active locale using priority:
 * 1. Stored user preference (preferred_language from Member_Profile)
 * 2. Browser language (navigator.language primary subtag)
 * 3. Dutch (nl) default
 */

import { SUPPORTED_LOCALES, DEFAULT_LOCALE, SupportedLocale } from './constants';

/**
 * Minimal member profile shape needed for locale resolution.
 * Uses the preferred_language attribute from the Members DynamoDB table.
 */
export interface MemberProfile {
  preferred_language?: string | null;
}

/**
 * Validates whether a locale string is in the set of supported locales.
 */
export function isValidLocale(locale: string): locale is SupportedLocale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(locale);
}

/**
 * Extracts the primary language subtag from a browser locale string.
 *
 * Examples:
 *   "en-US" → "en"
 *   "fr"    → "fr"
 *   ""      → null
 *   "xyz"   → "xyz" (validation happens separately)
 *
 * Returns null for empty/undefined/non-string input.
 */
export function parseBrowserLocale(navigatorLanguage: string | undefined | null): string | null {
  if (!navigatorLanguage || typeof navigatorLanguage !== 'string') {
    return null;
  }

  const trimmed = navigatorLanguage.trim();
  if (trimmed.length === 0) {
    return null;
  }

  // Extract primary subtag (before the first hyphen or underscore)
  const primary = trimmed.split(/[-_]/)[0].toLowerCase();
  return primary.length > 0 ? primary : null;
}

/**
 * Resolves the active locale based on priority:
 * 1. Stored preference from member profile (if valid)
 * 2. Browser locale primary subtag (if supported)
 * 3. Dutch default
 */
export function resolveLocale(memberProfile: MemberProfile | null): SupportedLocale {
  // Priority 1: stored user preference
  if (memberProfile?.preferred_language) {
    const stored = memberProfile.preferred_language.toLowerCase();
    if (isValidLocale(stored)) {
      return stored;
    }
  }

  // Priority 2: browser locale
  const browserLang = parseBrowserLocale(
    typeof navigator !== 'undefined' ? navigator.language : undefined
  );
  if (browserLang && isValidLocale(browserLang)) {
    return browserLang;
  }

  // Priority 3: Dutch default
  return DEFAULT_LOCALE;
}
