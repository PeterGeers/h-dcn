/**
 * Property-based tests for validateRule (fieldRenderers.ts).
 *
 * Feature: i18n-error-messages
 * Property 3: validateRule delegates to Validation_Helper when t is provided
 * Property 4: rule.message override takes priority
 * Test location: frontend/src/__tests__/i18n/validateRule.property.test.ts
 */

import * as fc from 'fast-check';
import { validateRule } from '../../utils/fieldRenderers';
import { getValidationMessage } from '../../utils/validationMessages';
import type { TFunction } from 'i18next';

// ---------- Mock t function ----------

/**
 * A distinctive mock t function that produces a unique, recognizable string
 * so we can verify delegation without ambiguity.
 */
const mockT = ((key: string, opts?: any): string => {
  return 'T:' + key + JSON.stringify(opts || {});
}) as unknown as TFunction;

// ---------- Minimal field definition factory ----------

function makeField(label: string) {
  return {
    key: 'test_field',
    label,
    dataType: 'string' as any,
    inputType: 'text' as any,
    group: 'personal' as any,
    order: 1,
  };
}

// ---------- Property 3: validateRule delegates to Validation_Helper when t is provided ----------

describe('validateRule - Property 3: validateRule delegates to Validation_Helper when t is provided', () => {
  /**
   * **Validates: Requirements 3.1**
   *
   * For any field label, validateRule with a 'required' rule and empty value
   * SHALL produce the same output as getValidationMessage(t, 'required', { field: label }).
   */
  it('required: delegates to getValidationMessage for arbitrary field labels', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'required' };
          const value = '';

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'required', { field: label });

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'email' rule type with an invalid email value, validateRule SHALL
   * produce the same output as getValidationMessage(t, 'email').
   */
  it('email: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'email' };
          const value = 'not-an-email';

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'email');

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'min_length' rule type with a value shorter than the minimum,
   * validateRule SHALL produce the same output as getValidationMessage(t, 'min_length', { count }).
   */
  it('min_length: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'min_length', value: 10 };
          const value = 'a'; // shorter than min_length of 10

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'min_length', { count: 10 });

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'max_length' rule type with a value longer than the maximum,
   * validateRule SHALL produce the same output as getValidationMessage(t, 'max_length', { count }).
   */
  it('max_length: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'max_length', value: 3 };
          const value = 'this is definitely longer than 3 characters';

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'max_length', { count: 3 });

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'min' rule type with a numeric value below the minimum,
   * validateRule SHALL produce the same output as getValidationMessage(t, 'min', { value }).
   */
  it('min: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'min', value: 5 };
          const value = 0; // less than min of 5

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'min', { value: 5 });

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'max' rule type with a numeric value above the maximum,
   * validateRule SHALL produce the same output as getValidationMessage(t, 'max', { value }).
   */
  it('max: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'max', value: 10 };
          const value = 100; // greater than max of 10

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'max', { value: 10 });

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * For the 'pattern' rule type with a value that doesn't match the regex,
   * validateRule SHALL produce the same output as getValidationMessage(t, 'pattern').
   */
  it('pattern: delegates to getValidationMessage', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (label) => {
          const field = makeField(label);
          const rule = { type: 'pattern', value: '^[0-9]+$' };
          const value = 'not-a-number'; // doesn't match digits-only pattern

          const result = validateRule(rule, value, field, mockT);
          const expected = getValidationMessage(mockT, 'pattern');

          return result === expected;
        }
      ),
      { numRuns: 100 }
    );
  });
});


// ---------- Property 4: rule.message override takes priority ----------

describe('validateRule - Property 4: rule.message override takes priority', () => {
  /**
   * **Validates: Requirements 3.3, 3.4**
   *
   * Property 4a: Literal messages (without `:`) are returned as-is
   *
   * For any validation rule that includes a rule.message field (non-empty,
   * without namespace prefix), validateRule SHALL return that exact rule.message
   * string regardless of what t function is provided.
   */
  it('rule.message without `:` is returned literally regardless of t function', () => {
    // Generate arbitrary literal messages that do NOT contain ':'
    const literalMessageArb = fc
      .string({ minLength: 1, maxLength: 100 })
      .filter((s) => !s.includes(':'));

    fc.assert(
      fc.property(literalMessageArb, (message) => {
        const field = makeField('TestField');
        const t = ((key: string, _opts?: any): string => {
          return `SHOULD_NOT_APPEAR:${key}`;
        }) as unknown as TFunction;

        const rule = { type: 'required', message };
        // Empty string triggers the 'required' validation failure
        const result = validateRule(rule, '', field, t);

        // The literal message must be returned exactly
        return result === message;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.3, 3.4**
   *
   * Property 4b: Namespace-prefixed messages (with `:`) are passed through t()
   *
   * For any rule.message containing a `:` (namespace prefix), validateRule SHALL
   * pass it through t() for resolution and return the t() result.
   */
  it('rule.message with `:` is passed through t() and returns the translated result', () => {
    // Generate namespace-prefixed messages: "namespace:key.path"
    const namespaceArb = fc.stringMatching(/^[a-zA-Z]{1,15}$/);
    const keyArb = fc.stringMatching(/^[a-zA-Z][a-zA-Z.]{0,20}$/);
    const namespacedMessageArb = fc.tuple(namespaceArb, keyArb).map(
      ([ns, key]) => `${ns}:${key}`
    );

    fc.assert(
      fc.property(namespacedMessageArb, (message) => {
        const field = makeField('TestField');
        const calls: string[] = [];
        const t = ((key: string, _opts?: any): string => {
          calls.push(key);
          return `translated:${key}`;
        }) as unknown as TFunction;

        const rule = { type: 'required', message };
        // Empty string triggers the 'required' validation failure
        const result = validateRule(rule, '', field, t);

        // t() must have been called with the message
        const tWasCalled = calls.includes(message);
        // The result must be what t() returned
        const resultIsTranslated = result === `translated:${message}`;

        return tWasCalled && resultIsTranslated;
      }),
      { numRuns: 100 }
    );
  });
});
