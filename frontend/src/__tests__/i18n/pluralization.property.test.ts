/**
 * Property-based tests for plural form selection.
 *
 * **Validates: Requirements 4.4**
 *
 * Property 4: Plural form selection follows CLDR rules
 * - For any supported locale and any non-negative integer count value,
 *   the i18n system SHALL select the correct plural form suffix according
 *   to that locale's CLDR plural rules.
 *
 * CLDR rules for our supported locales:
 * - nl, en, de, sv, da, it, es: count=1 → _one, count!=1 → _other
 * - fr: count=0 or count=1 → _one, count>=2 → _other
 */

import * as fc from 'fast-check';
import i18next, { i18n as I18nInstance } from 'i18next';
import { SUPPORTED_LOCALES, DEFAULT_LOCALE } from '../../i18n/constants';

// ---------- Helpers ----------

/**
 * Locales that follow standard Germanic/Romance CLDR plural rules:
 * count=1 → _one, count!=1 → _other
 */
const STANDARD_PLURAL_LOCALES = ['nl', 'en', 'de', 'sv', 'da', 'it', 'es'] as const;

/**
 * French has special plural rules:
 * count=0 or count=1 → _one, count>=2 → _other
 */
const FRENCH_LOCALE = 'fr' as const;

/** Translation resources with plural forms for all supported locales */
function createPluralResources(): Record<string, Record<string, Record<string, string>>> {
  const resources: Record<string, Record<string, Record<string, string>>> = {};

  for (const locale of SUPPORTED_LOCALES) {
    resources[locale] = {
      test: {
        item_one: `${locale}:{{count}} item`,
        item_other: `${locale}:{{count}} items`,
      },
    };
  }

  return resources;
}

/**
 * Creates a fresh i18next instance with inline plural translation resources.
 */
async function createTestI18n(): Promise<I18nInstance> {
  const instance = i18next.createInstance();
  await instance.init({
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...SUPPORTED_LOCALES],
    lng: DEFAULT_LOCALE,
    ns: ['test'],
    defaultNS: 'test',
    resources: createPluralResources(),
    react: { useSuspense: false },
    interpolation: { escapeValue: false },
    returnEmptyString: false,
    parseMissingKeyHandler: (key: string) => key,
    initImmediate: false,
  });
  return instance;
}

// ---------- Arbitraries ----------

/** Generates a non-negative integer count value (0 to 10000) */
const countArb = fc.nat({ max: 10000 });

/** Generates a count that equals 1 */
const countOneArb = fc.constant(1);

/** Generates a count that is NOT 1 (0 or 2+) */
const countNotOneArb = fc.nat({ max: 10000 }).filter((n) => n !== 1);

/** Generates a count >= 2 */
const countTwoOrMoreArb = fc.integer({ min: 2, max: 10000 });

/** Generates a count of 0 or 1 (French _one rule) */
const countZeroOrOneArb = fc.constantFrom(0, 1);

/** Generates a standard plural locale (not French) */
const standardLocaleArb = fc.constantFrom(...STANDARD_PLURAL_LOCALES);

// ---------- Tests ----------

describe('Plural Form Selection - Property Tests', () => {
  let i18n: I18nInstance;

  beforeAll(async () => {
    i18n = await createTestI18n();
  });

  /**
   * **Validates: Requirements 4.4**
   *
   * Property: For count=1, standard CLDR locales (nl, en, de, sv, da, it, es)
   * select the _one plural form.
   */
  it('selects _one form for count=1 in standard locales (nl, en, de, sv, da, it, es)', async () => {
    await fc.assert(
      fc.asyncProperty(standardLocaleArb, countOneArb, async (locale, count) => {
        await i18n.changeLanguage(locale);
        const result = i18n.t('item', { count });
        // Should use the _one form: "{locale}:{count} item"
        return result === `${locale}:${count} item`;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.4**
   *
   * Property: For count!=1, standard CLDR locales (nl, en, de, sv, da, it, es)
   * select the _other plural form.
   */
  it('selects _other form for count!=1 in standard locales (nl, en, de, sv, da, it, es)', async () => {
    await fc.assert(
      fc.asyncProperty(standardLocaleArb, countNotOneArb, async (locale, count) => {
        await i18n.changeLanguage(locale);
        const result = i18n.t('item', { count });
        // Should use the _other form: "{locale}:{count} items"
        return result === `${locale}:${count} items`;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.4**
   *
   * Property: For French, count=0 or count=1 selects the _one form.
   */
  it('selects _one form for count=0 or count=1 in French', async () => {
    await fc.assert(
      fc.asyncProperty(countZeroOrOneArb, async (count) => {
        await i18n.changeLanguage(FRENCH_LOCALE);
        const result = i18n.t('item', { count });
        // French: 0 and 1 use _one form
        return result === `fr:${count} item`;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.4**
   *
   * Property: For French, count>=2 selects the _other form.
   */
  it('selects _other form for count>=2 in French', async () => {
    await fc.assert(
      fc.asyncProperty(countTwoOrMoreArb, async (count) => {
        await i18n.changeLanguage(FRENCH_LOCALE);
        const result = i18n.t('item', { count });
        // French: 2+ uses _other form
        return result === `fr:${count} items`;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.4**
   *
   * Property: The system always returns a non-empty string (never a raw key or empty)
   * for any supported locale and any non-negative integer count value.
   */
  it('always returns a non-empty string for any locale and count', async () => {
    const anyLocaleArb = fc.constantFrom(...SUPPORTED_LOCALES);

    await fc.assert(
      fc.asyncProperty(anyLocaleArb, countArb, async (locale, count) => {
        await i18n.changeLanguage(locale);
        const result = i18n.t('item', { count });
        // Must be non-empty and must not be the raw key "item"
        return result.length > 0 && result !== 'item';
      }),
      { numRuns: 20 }
    );
  });
});
