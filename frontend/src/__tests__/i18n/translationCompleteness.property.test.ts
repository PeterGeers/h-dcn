/**
 * Property-based tests for translation completeness across namespaces and locales.
 *
 * Property 5: Translation completeness across all domain namespaces and locales
 *
 * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
 *
 * Feature: i18n-error-messages
 * Test location: frontend/src/__tests__/i18n/translationCompleteness.property.test.ts
 */

import * as fc from 'fast-check';
import * as path from 'path';
import * as fs from 'fs';

// ---------- Constants ----------

const LOCALES_DIR = path.resolve(__dirname, '../../locales');

const DOMAIN_NAMESPACES = ['products', 'members', 'eventBooking', 'webshop', 'events'] as const;

const LOCALES = ['nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv'] as const;

const REQUIRED_VALIDATION_KEYS = [
  'required', 'email', 'min_length', 'max_length',
  'min', 'max', 'pattern', 'invalid_number', 'invalid_option'
];

const INTERPOLATION_REQUIREMENTS: Record<string, string> = {
  'required': '{{field}}',
  'min_length': '{{count}}',
  'max_length': '{{count}}',
  'min': '{{value}}',
  'max': '{{value}}'
};

// ---------- Helpers ----------

function loadLocaleFile(locale: string, namespace: string): Record<string, any> | null {
  const filePath = path.join(LOCALES_DIR, locale, `${namespace}.json`);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

// ---------- Arbitraries ----------

const namespaceArb = fc.constantFrom(...DOMAIN_NAMESPACES);
const localeArb = fc.constantFrom(...LOCALES);

// ---------- Property 5: Translation completeness ----------

describe('Translation Completeness - Property 5: All domain namespaces and locales have complete validation sections', () => {
  /**
   * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
   *
   * Property 5a: Every domain namespace in every locale has a `validation`
   * section containing all required validation keys.
   */
  it('every namespace/locale combination has all required validation keys', () => {
    fc.assert(
      fc.property(namespaceArb, localeArb, (namespace, locale) => {
        const data = loadLocaleFile(locale, namespace);

        // File must exist
        if (data === null) {
          return false;
        }

        // Must have a validation section
        if (!data.validation || typeof data.validation !== 'object') {
          return false;
        }

        // Must contain all required keys
        for (const key of REQUIRED_VALIDATION_KEYS) {
          if (!(key in data.validation)) {
            return false;
          }
          // Each key must be a non-empty string
          if (typeof data.validation[key] !== 'string' || data.validation[key].length === 0) {
            return false;
          }
        }

        return true;
      }),
      { numRuns: 200 }
    );
  });

  /**
   * **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
   *
   * Property 5b: Validation keys that require interpolation placeholders
   * contain the expected `{{variable}}` placeholders in all locales.
   */
  it('interpolation placeholders are present in keys that require them', () => {
    fc.assert(
      fc.property(namespaceArb, localeArb, (namespace, locale) => {
        const data = loadLocaleFile(locale, namespace);

        // File must exist and have validation section
        if (data === null || !data.validation) {
          return false;
        }

        // Check each key that requires interpolation
        for (const [key, placeholder] of Object.entries(INTERPOLATION_REQUIREMENTS)) {
          const value = data.validation[key];
          if (typeof value !== 'string') {
            return false;
          }
          if (!value.includes(placeholder)) {
            return false;
          }
        }

        return true;
      }),
      { numRuns: 200 }
    );
  });
});
