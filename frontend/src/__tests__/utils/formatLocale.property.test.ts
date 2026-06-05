/**
 * Property-based tests for locale-aware formatting utilities.
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
 *
 * Property 5: Locale-aware formatting produces valid output
 * Property 6: Invalid format input returns empty string
 */

import * as fc from 'fast-check';
import { formatDate, formatCurrency, formatNumber } from '../../utils/formatLocale';
import { SUPPORTED_LOCALES } from '../../i18n/constants';

// ---------- Arbitraries ----------

/** Generates a valid supported locale */
const supportedLocaleArb = fc.constantFrom(...SUPPORTED_LOCALES);

/** Generates a valid Date object (between 1970 and 2100) */
const validDateArb = fc.date({
  min: new Date('1970-01-01T00:00:00.000Z'),
  max: new Date('2100-12-31T23:59:59.999Z'),
});

/** Generates a valid finite float for currency/number formatting */
const validNumberArb = fc.double({
  min: -1_000_000_000,
  max: 1_000_000_000,
  noNaN: true,
  noDefaultInfinity: true,
});

/** Generates invalid date strings that are not parseable */
const invalidDateStringArb = fc.constantFrom(
  'not-a-date',
  'abc123',
  '99-99-9999',
  'hello world',
  '2024-13-45',
  '',
  'undefined',
  'null',
  'NaN'
);

// ---------- Tests ----------

describe('Format Utilities - Property Tests', () => {
  /**
   * **Validates: Requirements 5.1**
   *
   * Property 5: For any valid Date and any supported locale,
   * formatDate produces a non-empty string matching Intl.DateTimeFormat output.
   */
  it('formatDate produces non-empty output matching Intl.DateTimeFormat for valid dates', () => {
    fc.assert(
      fc.property(
        validDateArb,
        supportedLocaleArb,
        fc.constantFrom('short' as const, 'long' as const),
        (date, locale, style) => {
          const result = formatDate(date, style, locale);

          // Must be non-empty
          if (result === '') return false;

          // Must match direct Intl.DateTimeFormat output
          const expected = new Intl.DateTimeFormat(locale, { dateStyle: style }).format(date);
          return result === expected;
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 5.2**
   *
   * Property 5: For any valid number and any supported locale,
   * formatCurrency produces a non-empty string containing '€'.
   */
  it('formatCurrency produces non-empty output containing € for valid numbers', () => {
    fc.assert(
      fc.property(validNumberArb, supportedLocaleArb, (amount, locale) => {
        const result = formatCurrency(amount, locale);

        // Must be non-empty
        if (result === '') return false;

        // Must contain the Euro symbol
        return result.includes('€');
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 5.3**
   *
   * Property 5: For any valid number and any supported locale,
   * formatNumber produces a non-empty string.
   */
  it('formatNumber produces non-empty output for valid numbers', () => {
    fc.assert(
      fc.property(validNumberArb, supportedLocaleArb, (value, locale) => {
        const result = formatNumber(value, locale);

        // Must be non-empty
        return result !== '';
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 5.5**
   *
   * Property 6: For null/undefined/NaN inputs, all format functions return empty string.
   */
  it('all format functions return empty string for null/undefined/NaN inputs', () => {
    fc.assert(
      fc.property(supportedLocaleArb, (locale) => {
        // formatDate with null/undefined
        if (formatDate(null, 'short', locale) !== '') return false;
        if (formatDate(undefined, 'short', locale) !== '') return false;
        if (formatDate(null, 'long', locale) !== '') return false;
        if (formatDate(undefined, 'long', locale) !== '') return false;

        // formatCurrency with null/undefined/NaN
        if (formatCurrency(null, locale) !== '') return false;
        if (formatCurrency(undefined, locale) !== '') return false;
        if (formatCurrency(NaN, locale) !== '') return false;

        // formatNumber with null/undefined/NaN
        if (formatNumber(null, locale) !== '') return false;
        if (formatNumber(undefined, locale) !== '') return false;
        if (formatNumber(NaN, locale) !== '') return false;

        return true;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 5.5**
   *
   * Property 6: For invalid date strings, formatDate returns empty string.
   */
  it('formatDate returns empty string for invalid date strings', () => {
    fc.assert(
      fc.property(
        invalidDateStringArb,
        supportedLocaleArb,
        fc.constantFrom('short' as const, 'long' as const),
        (invalidDate, locale, style) => {
          return formatDate(invalidDate, style, locale) === '';
        }
      ),
      { numRuns: 20 }
    );
  });
});
