/**
 * Property-based tests for translation fallback chain.
 *
 * Validates: Requirements 1.5, 1.6
 *
 * Property 2: Translation fallback chain
 * - For any translation key and any non-Dutch locale:
 *   1. If the key is absent or empty in that locale → falls back to Dutch (nl) translation
 *   2. If the key is also absent in Dutch → returns the key string itself
 *   3. Empty string values are treated as missing (requirement 10.6)
 */

import * as fc from 'fast-check';
import i18next, { i18n as I18nInstance } from 'i18next';
import { SUPPORTED_LOCALES, DEFAULT_LOCALE } from '../../i18n/constants';

// ---------- Helpers ----------

/** Non-Dutch supported locales for testing fallback behavior */
const NON_DUTCH_LOCALES = SUPPORTED_LOCALES.filter((l) => l !== DEFAULT_LOCALE);

/**
 * Creates a fresh i18next instance configured identically to the production
 * setup (matching frontend/src/i18n/index.ts) but using in-memory resources
 * instead of HTTP backend, so tests run synchronously.
 */
async function createTestI18n(resources: Record<string, Record<string, Record<string, string>>>): Promise<I18nInstance> {
  const instance = i18next.createInstance();
  await instance.init({
    // Language settings — match production config
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...SUPPORTED_LOCALES],
    lng: DEFAULT_LOCALE,

    // Namespace settings
    ns: ['test'],
    defaultNS: 'test',

    // In-memory resources (replaces HttpBackend for testing)
    resources,

    // React integration off for unit tests
    react: { useSuspense: false },

    // Interpolation settings — match production
    interpolation: { escapeValue: false },

    // Empty string handling: treat empty values as missing (requirement 10.6)
    returnEmptyString: false,

    // Missing key handling: return key as visible text (requirement 1.6)
    parseMissingKeyHandler: (key: string) => key,

    // Disable loading to use in-memory resources only
    initImmediate: false,
  });
  return instance;
}

// ---------- Arbitraries ----------

/** Generates a valid translation key (lowercase, dots, underscores) */
const translationKeyArb = fc
  .tuple(
    fc.stringOf(fc.constantFrom('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p'), { minLength: 1, maxLength: 5 }),
    fc.stringOf(fc.constantFrom('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','_','.'), { minLength: 0, maxLength: 8 }),
    fc.stringOf(fc.constantFrom('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','0','1','2','3'), { minLength: 1, maxLength: 3 })
  )
  .map(([start, mid, end]) => `${start}${mid}${end}`);

/** Generates a non-empty translation value */
const translationValueArb = fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0);

/** Generates a non-Dutch locale */
const nonDutchLocaleArb = fc.constantFrom(...NON_DUTCH_LOCALES);

// ---------- Tests ----------

describe('Translation Fallback Chain - Property Tests', () => {
  /**
   * **Validates: Requirements 1.5**
   *
   * Property: For any non-Dutch locale where a key is absent (not present at all),
   * the system returns the Dutch translation for that key.
   */
  it('falls back to Dutch when key is absent in non-Dutch locale', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        translationValueArb,
        nonDutchLocaleArb,
        async (key, dutchValue, locale) => {
          // Set up resources: key exists in Dutch but NOT in the target locale
          const resources = {
            nl: { test: { [key]: dutchValue } },
            [locale]: { test: {} }, // key is absent
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result === dutchValue;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 1.5, 10.6**
   *
   * Property: For any non-Dutch locale where a key has an empty string value,
   * the system treats it as missing and returns the Dutch translation.
   */
  it('falls back to Dutch when key has empty string value in non-Dutch locale', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        translationValueArb,
        nonDutchLocaleArb,
        async (key, dutchValue, locale) => {
          // Set up resources: key is empty string in locale, has value in Dutch
          const resources = {
            nl: { test: { [key]: dutchValue } },
            [locale]: { test: { [key]: '' } }, // empty string = treated as missing
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result === dutchValue;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 1.6**
   *
   * Property: For any key that is absent in both the target locale AND Dutch,
   * the system returns the key string itself.
   */
  it('returns key string when key is absent in both locale and Dutch', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        nonDutchLocaleArb,
        async (key, locale) => {
          // Set up resources: key exists in neither locale
          const resources = {
            nl: { test: {} },
            [locale]: { test: {} },
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result === key;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 1.6, 10.6**
   *
   * Property: For any key that has empty string value in both the target locale
   * AND Dutch, the system returns the key string itself (empty treated as missing).
   */
  it('returns key string when key is empty string in both locale and Dutch', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        nonDutchLocaleArb,
        async (key, locale) => {
          // Set up resources: key is empty in both locales
          const resources = {
            nl: { test: { [key]: '' } },
            [locale]: { test: { [key]: '' } },
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result === key;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 1.5, 1.6**
   *
   * Property: When a key exists with a non-empty value in the target locale,
   * the system returns that locale's value (no fallback occurs).
   */
  it('returns locale-specific value when key exists and is non-empty', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        translationValueArb,
        translationValueArb,
        nonDutchLocaleArb,
        async (key, localeValue, dutchValue, locale) => {
          // Set up resources: key exists in both locales with different values
          const resources = {
            nl: { test: { [key]: dutchValue } },
            [locale]: { test: { [key]: localeValue } },
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result === localeValue;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 1.5, 1.6**
   *
   * Property: The fallback chain always produces a non-empty result when
   * a Dutch translation exists for the key.
   */
  it('fallback chain always produces non-empty result when Dutch value exists', async () => {
    await fc.assert(
      fc.asyncProperty(
        translationKeyArb,
        translationValueArb,
        nonDutchLocaleArb,
        fc.constantFrom('', undefined as unknown as string), // locale value is empty or absent
        async (key, dutchValue, locale, localeValue) => {
          const localeTranslations: Record<string, string> = {};
          if (localeValue !== undefined) {
            localeTranslations[key] = localeValue; // empty string
          }
          // If undefined, key is simply absent

          const resources = {
            nl: { test: { [key]: dutchValue } },
            [locale]: { test: localeTranslations },
          };

          const instance = await createTestI18n(resources);
          await instance.changeLanguage(locale);

          const result = instance.t(key);
          return result.length > 0;
        }
      ),
      { numRuns: 20 }
    );
  });
});
