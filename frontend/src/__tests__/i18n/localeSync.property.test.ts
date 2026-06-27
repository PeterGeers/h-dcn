/**
 * Property-based test for locale file synchronization between src/ and public/.
 *
 * Feature: i18n-error-messages
 * Property 8: Locale file synchronization between src/ and public/
 * Test location: frontend/src/__tests__/i18n/localeSync.property.test.ts
 *
 * **Validates: Requirements 10.6**
 *
 * For every namespace file in `src/locales/{lang}/{ns}.json`, verifies that
 * an identical file exists at `public/locales/{lang}/{ns}.json`.
 */

import * as fc from 'fast-check';
import * as path from 'path';
import * as fs from 'fs';

const SRC_LOCALES_DIR = path.resolve(__dirname, '../../locales');
const PUBLIC_LOCALES_DIR = path.resolve(__dirname, '../../../public/locales');

const LOCALES = ['nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv'];
const NAMESPACES = ['common', 'products', 'members', 'eventBooking', 'webshop', 'events', 'auth', 'dashboard'];

describe('Locale File Synchronization - Property 8: src/ and public/ locales are identical', () => {
  /**
   * **Validates: Requirements 10.6**
   *
   * Property 8: Locale file synchronization between src/ and public/
   *
   * For every combination of locale × namespace, both src/locales/{lang}/{ns}.json
   * and public/locales/{lang}/{ns}.json SHALL exist and contain identical content.
   */
  it('every src/locales/{lang}/{ns}.json has an identical counterpart in public/locales/{lang}/{ns}.json', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LOCALES),
        fc.constantFrom(...NAMESPACES),
        (locale, namespace) => {
          const srcFile = path.join(SRC_LOCALES_DIR, locale, `${namespace}.json`);
          const publicFile = path.join(PUBLIC_LOCALES_DIR, locale, `${namespace}.json`);

          // Both files must exist
          const srcExists = fs.existsSync(srcFile);
          const publicExists = fs.existsSync(publicFile);

          if (!srcExists) {
            // If src file doesn't exist, skip this combination
            // (not all namespaces may be present for all locales)
            return true;
          }

          if (!publicExists) {
            throw new Error(
              `Missing public locale file: public/locales/${locale}/${namespace}.json ` +
              `(exists in src/locales/${locale}/${namespace}.json but not in public/locales/)`
            );
          }

          // Read and compare content
          const srcContent = fs.readFileSync(srcFile, 'utf-8');
          const publicContent = fs.readFileSync(publicFile, 'utf-8');

          // Parse JSON to compare structure (ignores formatting differences)
          const srcJson = JSON.parse(srcContent);
          const publicJson = JSON.parse(publicContent);

          const srcSerialized = JSON.stringify(srcJson, null, 2);
          const publicSerialized = JSON.stringify(publicJson, null, 2);

          if (srcSerialized !== publicSerialized) {
            throw new Error(
              `Locale file out of sync: public/locales/${locale}/${namespace}.json ` +
              `does not match src/locales/${locale}/${namespace}.json. ` +
              `The files must have identical content.`
            );
          }

          return true;
        }
      ),
      { numRuns: 200 }
    );
  });
});
