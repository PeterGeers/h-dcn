/**
 * Property-based tests for the Validation_Helper (getValidationMessage).
 *
 * Feature: i18n-error-messages
 * Test location: frontend/src/__tests__/i18n/validationMessages.property.test.ts
 */

import * as fc from 'fast-check';
import {
  getValidationMessage,
  ValidationRuleType,
} from '../../utils/validationMessages';
import type { TFunction } from 'i18next';

// ---------- Shared Arbitraries ----------

/** All supported validation rule types */
const allRuleTypes: ValidationRuleType[] = [
  'required',
  'email',
  'phone',
  'iban',
  'min_length',
  'max_length',
  'min',
  'max',
  'pattern',
  'invalid_number',
  'invalid_option',
];

const ruleTypeArb = fc.constantFrom(...allRuleTypes);

/** Arbitrary params with optional fields */
const paramsArb = fc.record(
  {
    field: fc.string({ minLength: 0, maxLength: 50 }),
    count: fc.nat({ max: 1000 }),
    value: fc.integer({ min: -10000, max: 10000 }),
  },
  { withDeletedKeys: true }
);

// ---------- Mock t functions ----------

/**
 * Mock t that simulates a resolved key — returns a translated string.
 * Mimics react-i18next behavior where the key exists in the namespace.
 */
const tResolved = ((key: string, _opts?: any): string => {
  return `Translated: ${key}`;
}) as unknown as TFunction;

/**
 * Mock t that simulates a missing key — returns the defaultValue.
 * Mimics react-i18next behavior where the key is NOT in the namespace
 * and the defaultValue option is used as fallback.
 */
const tMissing = ((_key: string, opts?: any): string => {
  return opts?.defaultValue || '';
}) as unknown as TFunction;

// ---------- Property 1: getValidationMessage always returns a non-empty string ----------

describe('Validation_Helper - Property 1: getValidationMessage always returns a non-empty string', () => {
  /**
   * **Validates: Requirements 1.2, 11.1**
   *
   * Property 1: getValidationMessage always returns a non-empty string
   *
   * For any valid ruleType and any params, when the t function resolves the key
   * successfully, getValidationMessage returns a non-empty string.
   */
  it('returns non-empty string when t resolves the key', () => {
    fc.assert(
      fc.property(ruleTypeArb, paramsArb, (ruleType, params) => {
        const result = getValidationMessage(tResolved, ruleType, params);
        return typeof result === 'string' && result.length > 0;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 1.2, 11.1**
   *
   * Property 1: getValidationMessage always returns a non-empty string
   *
   * For any valid ruleType and any params, when the t function simulates a
   * missing key (returns defaultValue), getValidationMessage still returns a
   * non-empty string via the Dutch fallback.
   */
  it('returns non-empty string when t simulates missing key (uses defaultValue fallback)', () => {
    fc.assert(
      fc.property(ruleTypeArb, paramsArb, (ruleType, params) => {
        const result = getValidationMessage(tMissing, ruleType, params);
        return typeof result === 'string' && result.length > 0;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 1.2, 11.1**
   *
   * Property 1: getValidationMessage always returns a non-empty string
   *
   * For any valid ruleType and undefined params, the function still returns
   * a non-empty string (params are optional).
   */
  it('returns non-empty string when params is undefined', () => {
    fc.assert(
      fc.property(ruleTypeArb, (ruleType) => {
        const resultResolved = getValidationMessage(tResolved, ruleType);
        const resultMissing = getValidationMessage(tMissing, ruleType);
        return (
          typeof resultResolved === 'string' &&
          resultResolved.length > 0 &&
          typeof resultMissing === 'string' &&
          resultMissing.length > 0
        );
      }),
      { numRuns: 100 }
    );
  });
});

// ---------- Property 2: Namespace delegation ----------

describe('Validation_Helper - Property 2: Namespace delegation', () => {
  /**
   * **Validates: Requirements 1.8**
   *
   * Property 2: Namespace delegation — t function determines output
   *
   * For any valid ruleType and for any two distinct mock t functions that return
   * different strings for the same key, getValidationMessage(t1, ruleType) and
   * getValidationMessage(t2, ruleType) SHALL produce different results, proving
   * the helper delegates to the caller's t without hardcoding a namespace.
   */
  it('two distinct t functions producing different strings yield different results', () => {
    // t1 simulates a "products" namespace — returns "PRODUCTS:" + key
    const t1 = ((key: string, _opts?: object) => `PRODUCTS:${key}`) as unknown as TFunction;

    // t2 simulates a "members" namespace — returns "MEMBERS:" + key
    const t2 = ((key: string, _opts?: object) => `MEMBERS:${key}`) as unknown as TFunction;

    fc.assert(
      fc.property(ruleTypeArb, (ruleType) => {
        const result1 = getValidationMessage(t1, ruleType);
        const result2 = getValidationMessage(t2, ruleType);

        // The two results must be different, proving delegation to t
        return result1 !== result2;
      }),
      { numRuns: 100 }
    );
  });
});
