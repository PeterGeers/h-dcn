/**
 * Property-based tests for backend error_key coverage in frontend common namespace.
 *
 * Feature: i18n-error-messages
 * Property 6: Backend error_key coverage in frontend common namespace
 * Test location: frontend/src/__tests__/i18n/backendErrorKeys.property.test.ts
 */

import * as fc from 'fast-check';
import * as path from 'path';
import * as fs from 'fs';

// ---------- Constants ----------

const LOCALES_DIR = path.resolve(__dirname, '../../locales');
const LOCALES = ['nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv'];

/** All 15 backend error keys from shared.i18n.error_messages */
const BACKEND_ERROR_KEYS = [
  'authorization_required',
  'forbidden',
  'not_found',
  'validation_error',
  'internal_error',
  'member_not_found',
  'member_already_exists',
  'invalid_input',
  'payment_failed',
  'order_not_found',
  'product_not_found',
  'cart_empty',
  'insufficient_stock',
  'email_already_exists',
  'invalid_membership',
];

// ---------- Helpers ----------

/** Load and parse common.json for a given locale */
function loadCommonJson(locale: string): Record<string, any> {
  const filePath = path.join(LOCALES_DIR, locale, 'common.json');
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

// ---------- Property 6: Backend error_key coverage in frontend common namespace ----------

describe('Backend error_key coverage - Property 6: All backend error keys present in common namespace', () => {
  /**
   * **Validates: Requirements 6a.1, 6a.4**
   *
   * Property 6: Backend error_key coverage in frontend common namespace
   *
   * For any combination of error_key × locale, the common.json file SHALL
   * contain an `api_errors` section with a matching entry that is a non-empty string.
   */
  it('every backend error_key has a non-empty api_errors entry in every locale', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...BACKEND_ERROR_KEYS),
        fc.constantFrom(...LOCALES),
        (errorKey, locale) => {
          const common = loadCommonJson(locale);

          // common.json must have an api_errors section
          if (!common.api_errors || typeof common.api_errors !== 'object') {
            return false;
          }

          // The api_errors section must contain the error_key
          const value = common.api_errors[errorKey];
          if (value === undefined || value === null) {
            return false;
          }

          // The value must be a non-empty string
          return typeof value === 'string' && value.trim().length > 0;
        }
      ),
      { numRuns: 200 }
    );
  });
});
