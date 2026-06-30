/**
 * Property-based tests for locale file structure and translation completeness.
 *
 * Feature: i18n-error-messages, Property 5: Translation completeness
 *
 * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
 *
 * Iterates all 5 domain namespaces × 8 locales, verifying:
 * - The locale file exists
 * - The JSON has a `validation` section (object)
 * - All required validation keys are present with non-empty string values
 * - Keys requiring interpolation contain the correct {{variable}} placeholders
 *
 * Test location: frontend/src/__tests__/i18n/localeStructure.property.test.ts
 */

import * as fc from 'fast-check';
import * as fs from 'fs';
import * as path from 'path';

// ---------- Constants ----------

const NAMESPACES = ['products', 'members', 'eventBooking', 'webshop', 'events'] as const;
const LOCALES = ['nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv'] as const;
const REQUIRED_VALIDATION_KEYS = [
  'required', 'email', 'min_length', 'max_length',
  'min', 'max', 'pattern', 'invalid_number', 'invalid_option'
] as const;

// Keys that must contain specific interpolation placeholders
const INTERPOLATION_REQUIREMENTS: Record<string, string[]> = {
  required: ['{{field}}'],
  min_length: ['{{count}}'],
  max_length: ['{{count}}'],
  min: ['{{value}}'],
  max: ['{{value}}'],
};

// ---------- Helpers ----------

function getLocaleFilePath(locale: string, namespace: string): string {
  return path.resolve(__dirname, '../../locales', locale, `${namespace}.json`);
}

function loadLocaleJson(locale: string, namespace: string): Record<string, any> | null {
  const filePath = getLocaleFilePath(locale, namespace);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

// ---------- Arbitraries ----------

const namespaceArb = fc.constantFrom(...NAMESPACES);
const localeArb = fc.constantFrom(...LOCALES);

// ---------- Property 5: Translation completeness across all domain namespaces and locales ----------

describe('Locale Structure - Property 5: Translation completeness across all domain namespaces and locales', () => {
  /**
   * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
   *
   * For any namespace × locale combination, the locale file must exist,
   * have a `validation` section with all required keys as non-empty strings.
   */
  it('every namespace/locale has a validation section with all required keys', () => {
    fc.assert(
      fc.property(namespaceArb, localeArb, (namespace, locale) => {
        const filePath = getLocaleFilePath(locale, namespace);

        // File must exist
        expect(fs.existsSync(filePath)).toBe(true);

        const data = loadLocaleJson(locale, namespace);
        expect(data).not.toBeNull();

        // Must have a validation section that is an object
        expect(data!.validation).toBeDefined();
        expect(typeof data!.validation).toBe('object');
        expect(data!.validation).not.toBeNull();

        // Must contain all required keys with non-empty string values
        for (const key of REQUIRED_VALIDATION_KEYS) {
          const value = data!.validation[key];
          expect(value).toBeDefined();
          expect(typeof value).toBe('string');
          expect(value.length).toBeGreaterThan(0);
        }

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
   *
   * For any namespace × locale combination, keys that require interpolation
   * must contain the expected {{variable}} placeholders.
   */
  it('interpolation placeholders are present in keys that need them', () => {
    fc.assert(
      fc.property(namespaceArb, localeArb, (namespace, locale) => {
        const data = loadLocaleJson(locale, namespace);
        expect(data).not.toBeNull();
        expect(data!.validation).toBeDefined();

        for (const [key, placeholders] of Object.entries(INTERPOLATION_REQUIREMENTS)) {
          const value = data!.validation[key];
          expect(typeof value).toBe('string');

          for (const placeholder of placeholders) {
            expect(value).toContain(placeholder);
          }
        }

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.4**
   *
   * The `events` namespace has additional poster-specific validation keys
   * that are not required in other namespaces.
   */
  it('events namespace has poster-specific validation keys in all locales', () => {
    fc.assert(
      fc.property(localeArb, (locale) => {
        const data = loadLocaleJson(locale, 'events');
        expect(data).not.toBeNull();
        expect(data!.validation).toBeDefined();

        // Events-specific keys
        expect(data!.validation.poster_invalid_type).toBeDefined();
        expect(typeof data!.validation.poster_invalid_type).toBe('string');
        expect(data!.validation.poster_invalid_type.length).toBeGreaterThan(0);

        expect(data!.validation.poster_file_too_large).toBeDefined();
        expect(typeof data!.validation.poster_file_too_large).toBe('string');
        expect(data!.validation.poster_file_too_large.length).toBeGreaterThan(0);

        return true;
      }),
      { numRuns: 20 }
    );
  });
});
