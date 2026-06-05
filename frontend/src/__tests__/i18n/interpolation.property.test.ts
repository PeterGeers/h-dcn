/**
 * Property-based tests for i18next interpolation.
 *
 * **Validates: Requirements 4.3**
 *
 * Property 3: Interpolation preserves dynamic values
 * - For any translated string containing {{variable}} placeholders and any set
 *   of interpolation values, the rendered output SHALL contain all provided
 *   interpolation values as substrings.
 */

import * as fc from 'fast-check';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// ---------- Test i18next instance ----------

/**
 * Create a dedicated i18next instance for testing interpolation.
 * Uses inline resources (no HTTP backend needed).
 */
const testI18n = i18n.createInstance();

beforeAll(async () => {
  await testI18n.use(initReactI18next).init({
    lng: 'en',
    fallbackLng: 'nl',
    interpolation: {
      escapeValue: false,
    },
    resources: {
      en: {
        translation: {
          single_var: 'Hello {{name}}',
          two_vars: '{{greeting}} {{name}}',
          three_vars: '{{a}} and {{b}} and {{c}}',
          surrounded: 'Before {{value}} after',
          only_var: '{{value}}',
          repeated_var: '{{name}} likes {{name}}',
        },
      },
    },
  });
});

// ---------- Arbitraries ----------

/** Generates alphanumeric variable names (valid i18next interpolation keys) */
const varNameArb = fc
  .stringOf(
    fc.constantFrom(
      ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('')
    ),
    { minLength: 1, maxLength: 20 }
  )
  .filter((s) => /^[a-zA-Z]/.test(s)); // must start with letter

/** Generates arbitrary string values for interpolation */
const interpolationValueArb = fc.string({ minLength: 0, maxLength: 100 });

// ---------- Tests ----------

describe('Interpolation - Property Tests', () => {
  /**
   * **Validates: Requirements 4.3**
   *
   * Property: For any string value used as interpolation for a single variable,
   * the rendered output contains that value as a substring.
   */
  it('single interpolation value appears in rendered output', () => {
    fc.assert(
      fc.property(interpolationValueArb, (value) => {
        const result = testI18n.t('single_var', { name: value });
        return result.includes(value);
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.3**
   *
   * Property: For any two string values used as interpolation for two variables,
   * both values appear in the rendered output.
   */
  it('multiple interpolation values all appear in rendered output', () => {
    fc.assert(
      fc.property(
        interpolationValueArb,
        interpolationValueArb,
        (greeting, name) => {
          const result = testI18n.t('two_vars', { greeting, name });
          return result.includes(greeting) && result.includes(name);
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.3**
   *
   * Property: For three interpolation variables, all three values appear
   * in the rendered output.
   */
  it('three interpolation values all appear in rendered output', () => {
    fc.assert(
      fc.property(
        interpolationValueArb,
        interpolationValueArb,
        interpolationValueArb,
        (a, b, c) => {
          const result = testI18n.t('three_vars', { a, b, c });
          return result.includes(a) && result.includes(b) && result.includes(c);
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.3**
   *
   * Property: Empty string interpolation values produce valid output
   * (the placeholder is replaced, not left as {{variable}} syntax).
   */
  it('empty string values replace placeholders without leaving template syntax', () => {
    fc.assert(
      fc.property(fc.constant(''), (value) => {
        const result = testI18n.t('single_var', { name: value });
        // The placeholder syntax should not remain in output
        return !result.includes('{{') && !result.includes('}}');
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.3**
   *
   * Property: For a template containing only a variable placeholder,
   * the output equals exactly the interpolation value.
   */
  it('template with only a variable placeholder renders exactly the value', () => {
    fc.assert(
      fc.property(interpolationValueArb, (value) => {
        const result = testI18n.t('only_var', { value });
        return result === value;
      }),
      { numRuns: 20 }
    );
  });

  /**
   * **Validates: Requirements 4.3**
   *
   * Property: Interpolation with dynamically generated variable names and values
   * always produces output containing the provided value. This tests that for
   * any valid variable name and any value, the i18next interpolation mechanism
   * correctly substitutes the value.
   */
  it('dynamically constructed templates interpolate correctly', () => {
    fc.assert(
      fc.property(varNameArb, interpolationValueArb, (varName, value) => {
        // Add a dynamic resource with the generated variable name
        testI18n.addResource('en', 'translation', `dynamic_${varName}`, `prefix {{${varName}}} suffix`);
        const result = testI18n.t(`dynamic_${varName}`, { [varName]: value });
        return result.includes(value);
      }),
      { numRuns: 20 }
    );
  });
});
