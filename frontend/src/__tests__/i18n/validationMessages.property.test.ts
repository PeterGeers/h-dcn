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
