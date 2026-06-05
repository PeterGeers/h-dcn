/**
 * Property-based tests for locale resolution logic.
 *
 * Validates: Requirements 2.1, 2.3, 2.4, 2.5
 *
 * Property 1: Locale resolution priority
 * - stored preference → browser language → Dutch default
 */

import * as fc from 'fast-check';
import {
  isValidLocale,
  parseBrowserLocale,
  resolveLocale,
  MemberProfile,
} from '../../i18n/localeResolver';
import { SUPPORTED_LOCALES, DEFAULT_LOCALE } from '../../i18n/constants';

// ---------- Arbitraries ----------

/** Generates a valid supported locale */
const supportedLocaleArb = fc.constantFrom(...SUPPORTED_LOCALES);

/** Generates a string that is NOT a supported locale */
const unsupportedLocaleArb = fc
  .string({ minLength: 1, maxLength: 10 })
  .filter((s) => !(SUPPORTED_LOCALES as readonly string[]).includes(s.toLowerCase()));

/** Generates a browser locale string with a hyphen (e.g., "en-US", "fr-BE") */
const browserLocaleWithSubtagArb = fc.tuple(
  fc.constantFrom(...SUPPORTED_LOCALES),
  fc.stringOf(fc.constantFrom('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'), { minLength: 2, maxLength: 4 })
).map(([lang, region]) => `${lang}-${region}`);

/** Generates a browser locale string with underscore separator */
const browserLocaleWithUnderscoreArb = fc.tuple(
  fc.constantFrom(...SUPPORTED_LOCALES),
  fc.stringOf(fc.constantFrom('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'), { minLength: 2, maxLength: 4 })
).map(([lang, region]) => `${lang}_${region}`);

/** Generates a malformed/unsupported browser locale */
const malformedBrowserLocaleArb = fc.oneof(
  fc.constant(''),
  fc.constant(null),
  fc.constant(undefined),
  unsupportedLocaleArb.map((s) => `${s}-XX`)
);

// ---------- Helper ----------

function setNavigatorLanguage(value: string | undefined | null): void {
  Object.defineProperty(navigator, 'language', {
    value,
    configurable: true,
    writable: true,
  });
}

// ---------- Tests ----------

describe('Locale Resolution - Property Tests', () => {
  const originalLanguage = navigator.language;

  afterEach(() => {
    // Restore original navigator.language
    Object.defineProperty(navigator, 'language', {
      value: originalLanguage,
      configurable: true,
      writable: true,
    });
  });

  /**
   * **Validates: Requirements 2.1, 2.5**
   *
   * Property: For any valid supported locale stored as preferred_language,
   * resolveLocale returns that locale regardless of browser language.
   */
  it('returns stored preference when it is a valid supported locale', () => {
    fc.assert(
      fc.property(
        supportedLocaleArb,
        fc.oneof(supportedLocaleArb, unsupportedLocaleArb, fc.constant(undefined)),
        (storedLocale, browserLang) => {
          setNavigatorLanguage(browserLang ?? 'xx');
          const profile: MemberProfile = { preferred_language: storedLocale };
          const result = resolveLocale(profile);
          return result === storedLocale;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.5**
   *
   * Property: For any invalid stored preference + valid supported browser locale,
   * resolveLocale returns the browser locale.
   */
  it('falls through to browser locale when stored preference is invalid', () => {
    fc.assert(
      fc.property(
        unsupportedLocaleArb,
        supportedLocaleArb,
        (invalidStored, browserLocale) => {
          setNavigatorLanguage(browserLocale);
          const profile: MemberProfile = { preferred_language: invalidStored };
          const result = resolveLocale(profile);
          return result === browserLocale;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.3**
   *
   * Property: For null stored preference + valid supported browser locale,
   * resolveLocale returns the browser locale.
   */
  it('falls through to browser locale when stored preference is null/absent', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, ''),
        supportedLocaleArb,
        (nullishStored, browserLocale) => {
          setNavigatorLanguage(browserLocale);
          const profile: MemberProfile = { preferred_language: nullishStored };
          const result = resolveLocale(profile);
          return result === browserLocale;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.3**
   *
   * Property: For null profile + valid supported browser locale,
   * resolveLocale returns the browser locale.
   */
  it('falls through to browser locale when profile is null', () => {
    fc.assert(
      fc.property(supportedLocaleArb, (browserLocale) => {
        setNavigatorLanguage(browserLocale);
        const result = resolveLocale(null);
        return result === browserLocale;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.4**
   *
   * Property: For any invalid/null stored preference + unsupported/malformed
   * browser locale, resolveLocale returns the Dutch default.
   */
  it('returns Dutch default when both stored preference and browser locale are invalid', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, '', 'xyz', 'zz', '!!invalid'),
        malformedBrowserLocaleArb,
        (invalidStored, malformedBrowser) => {
          setNavigatorLanguage(malformedBrowser as string | undefined);
          const profile: MemberProfile = { preferred_language: invalidStored };
          const result = resolveLocale(profile);
          return result === DEFAULT_LOCALE;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.3**
   *
   * Property: parseBrowserLocale extracts primary subtag correctly for
   * any locale string with hyphens.
   */
  it('parseBrowserLocale extracts primary subtag from hyphenated locale strings', () => {
    fc.assert(
      fc.property(browserLocaleWithSubtagArb, (browserLocale) => {
        const result = parseBrowserLocale(browserLocale);
        const expected = browserLocale.split('-')[0].toLowerCase();
        return result === expected;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.3**
   *
   * Property: parseBrowserLocale extracts primary subtag correctly for
   * any locale string with underscores.
   */
  it('parseBrowserLocale extracts primary subtag from underscore-separated locale strings', () => {
    fc.assert(
      fc.property(browserLocaleWithUnderscoreArb, (browserLocale) => {
        const result = parseBrowserLocale(browserLocale);
        const expected = browserLocale.split('_')[0].toLowerCase();
        return result === expected;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.3**
   *
   * Property: parseBrowserLocale returns null for null/undefined/empty input.
   */
  it('parseBrowserLocale returns null for empty/null/undefined input', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, '', '   '),
        (input) => {
          const result = parseBrowserLocale(input);
          return result === null;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.5**
   *
   * Property: isValidLocale returns true only for supported locales.
   */
  it('isValidLocale returns true only for supported locales', () => {
    fc.assert(
      fc.property(supportedLocaleArb, (locale) => {
        return isValidLocale(locale) === true;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.5**
   *
   * Property: isValidLocale returns false for any string not in SUPPORTED_LOCALES.
   */
  it('isValidLocale returns false for unsupported locale strings', () => {
    fc.assert(
      fc.property(unsupportedLocaleArb, (locale) => {
        return isValidLocale(locale) === false;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.3, 2.4, 2.5**
   *
   * Property: resolveLocale ALWAYS returns a value from SUPPORTED_LOCALES
   * regardless of input combination.
   */
  it('resolveLocale always returns a supported locale for any input', () => {
    fc.assert(
      fc.property(
        fc.option(fc.oneof(supportedLocaleArb, unsupportedLocaleArb, fc.constant('')), { nil: null }),
        fc.option(fc.oneof(supportedLocaleArb, unsupportedLocaleArb, fc.constant('')), { nil: undefined }),
        (storedPref, browserLang) => {
          setNavigatorLanguage(browserLang);
          const profile: MemberProfile | null = storedPref !== null
            ? { preferred_language: storedPref }
            : null;
          const result = resolveLocale(profile);
          return (SUPPORTED_LOCALES as readonly string[]).includes(result);
        }
      ),
      { numRuns: 20 }
    );
  });
});
