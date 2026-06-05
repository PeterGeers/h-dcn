/**
 * Property-based tests for translation file conventions.
 *
 * Validates: Requirements 10.2, 10.3
 *
 * Property 11: Translation file key naming convention
 * - All keys match pattern ^[a-z][a-z0-9_.]*[a-z0-9]$
 *
 * Property 12: Translation file maximum nesting depth
 * - No translation file has nesting deeper than 2 levels
 */

import * as fc from 'fast-check';
import * as fs from 'fs';
import * as path from 'path';

// ---------- Utility Functions ----------

const KEY_PATTERN = /^[a-z][a-z0-9_.]*[a-z0-9]$/;

/**
 * Validates that a translation key matches the required naming convention.
 * Pattern: ^[a-z][a-z0-9_.]*[a-z0-9]$
 * - Starts with a lowercase letter
 * - Contains only lowercase alphanumeric, dots, underscores
 * - Ends with a lowercase letter or digit
 * - Minimum length: 2 characters
 */
export function isValidTranslationKey(key: string): boolean {
  if (key.length < 2) return false;
  return KEY_PATTERN.test(key);
}

/**
 * Calculates the maximum nesting depth of a JSON object.
 * A flat object { "key": "value" } has depth 1.
 * A nested object { "group": { "key": "value" } } has depth 2.
 */
export function getMaxNestingDepth(obj: unknown, currentDepth = 0): number {
  if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
    return currentDepth;
  }

  const entries = Object.values(obj);
  if (entries.length === 0) return currentDepth + 1;

  let maxDepth = currentDepth + 1;
  for (const value of entries) {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const childDepth = getMaxNestingDepth(value, currentDepth + 1);
      maxDepth = Math.max(maxDepth, childDepth);
    }
  }
  return maxDepth;
}

/**
 * Extracts all keys at every level from a nested translation object.
 */
export function extractAllKeys(obj: unknown, keys: string[] = []): string[] {
  if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
    return keys;
  }

  for (const [key, value] of Object.entries(obj)) {
    keys.push(key);
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      extractAllKeys(value, keys);
    }
  }
  return keys;
}

// ---------- File Loading Helpers ----------

const LOCALES_DIR = path.resolve(__dirname, '../../locales/nl');

function getTranslationFiles(): { name: string; content: Record<string, unknown> }[] {
  const files = fs.readdirSync(LOCALES_DIR).filter((f) => f.endsWith('.json'));
  return files.map((name) => {
    const filePath = path.join(LOCALES_DIR, name);
    const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    return { name, content };
  });
}

// ---------- Arbitraries ----------

/** Generates a string that matches the valid key pattern */
const validKeyArb = fc
  .tuple(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split('')),
    fc.stringOf(
      fc.constantFrom(
        ...'abcdefghijklmnopqrstuvwxyz0123456789_.'.split('')
      ),
      { minLength: 0, maxLength: 20 }
    ),
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split(''))
  )
  .map(([first, middle, last]) => `${first}${middle}${last}`);

/** Generates a string that should NOT match the valid key pattern */
const invalidKeyArb = fc.oneof(
  // Starts with digit
  fc.tuple(
    fc.constantFrom(...'0123456789'.split('')),
    fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split('')), { minLength: 1, maxLength: 10 })
  ).map(([first, rest]) => `${first}${rest}`),
  // Starts with uppercase
  fc.tuple(
    fc.constantFrom(...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')),
    fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split('')), { minLength: 1, maxLength: 10 })
  ).map(([first, rest]) => `${first}${rest}`),
  // Ends with dot or underscore
  fc.tuple(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split('')),
    fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split('')), { minLength: 0, maxLength: 10 }),
    fc.constantFrom('.', '_')
  ).map(([first, middle, last]) => `${first}${middle}${last}`),
  // Contains invalid characters (uppercase, space, special chars)
  fc.tuple(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split('')),
    fc.constantFrom(' ', '-', '@', '#', '!', 'A', 'B', 'Z'),
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789'.split(''))
  ).map(([first, invalid, last]) => `${first}${invalid}${last}`),
  // Single character (too short)
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split(''))
);

/** Generates a nested object with depth exceeding 2 (depth 3+) */
const deepNestedObjectArb = fc
  .tuple(
    fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
    fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
    fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
    fc.string({ minLength: 1, maxLength: 20 })
  )
  .map(([key1, key2, key3, value]) => ({
    [key1]: { [key2]: { [key3]: value } },
  }));

/** Generates a valid object with depth at most 2 */
const shallowObjectArb = fc.oneof(
  // Depth 1: flat key-value
  fc.dictionary(
    fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
    fc.string({ minLength: 1, maxLength: 20 }),
    { minKeys: 1, maxKeys: 5 }
  ),
  // Depth 2: one level of grouping
  fc.dictionary(
    fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
    fc.dictionary(
      fc.string({ minLength: 2, maxLength: 8 }).filter((s) => KEY_PATTERN.test(s)),
      fc.string({ minLength: 1, maxLength: 20 }),
      { minKeys: 1, maxKeys: 3 }
    ),
    { minKeys: 1, maxKeys: 3 }
  )
);

// ---------- Tests ----------

describe('Translation File Conventions - Property Tests', () => {
  describe('Property 11: Translation file key naming convention', () => {
    /**
     * **Validates: Requirements 10.3**
     *
     * Property: isValidTranslationKey correctly accepts keys matching
     * the pattern ^[a-z][a-z0-9_.]*[a-z0-9]$
     */
    it('accepts keys that match the naming convention pattern', () => {
      fc.assert(
        fc.property(validKeyArb, (key) => {
          return isValidTranslationKey(key) === true;
        }),
        { numRuns: 20 }
      );
    });

    /**
     * **Validates: Requirements 10.3**
     *
     * Property: isValidTranslationKey correctly rejects keys that do NOT match
     * the pattern ^[a-z][a-z0-9_.]*[a-z0-9]$
     */
    it('rejects keys that violate the naming convention pattern', () => {
      fc.assert(
        fc.property(invalidKeyArb, (key) => {
          return isValidTranslationKey(key) === false;
        }),
        { numRuns: 20 }
      );
    });

    /**
     * **Validates: Requirements 10.3**
     *
     * Integration: All keys in all Dutch translation files match the naming convention.
     */
    it('all keys in actual translation files match the naming convention', () => {
      const files = getTranslationFiles();
      expect(files.length).toBeGreaterThan(0);

      for (const { name, content } of files) {
        const allKeys = extractAllKeys(content);
        for (const key of allKeys) {
          expect(isValidTranslationKey(key)).toBe(true);
        }
      }
    });
  });

  describe('Property 12: Translation file maximum nesting depth', () => {
    /**
     * **Validates: Requirements 10.2**
     *
     * Property: getMaxNestingDepth correctly identifies objects with depth <= 2
     * as valid (within the allowed nesting limit).
     */
    it('reports depth <= 2 for shallow objects', () => {
      fc.assert(
        fc.property(shallowObjectArb, (obj) => {
          const depth = getMaxNestingDepth(obj);
          return depth <= 2;
        }),
        { numRuns: 20 }
      );
    });

    /**
     * **Validates: Requirements 10.2**
     *
     * Property: getMaxNestingDepth correctly identifies objects with depth > 2
     * as violations (exceeding the allowed nesting limit).
     */
    it('reports depth > 2 for deeply nested objects', () => {
      fc.assert(
        fc.property(deepNestedObjectArb, (obj) => {
          const depth = getMaxNestingDepth(obj);
          return depth > 2;
        }),
        { numRuns: 20 }
      );
    });

    /**
     * **Validates: Requirements 10.2**
     *
     * Integration: No actual translation file exceeds 2 levels of nesting.
     */
    it('all actual translation files have nesting depth <= 2', () => {
      const files = getTranslationFiles();
      expect(files.length).toBeGreaterThan(0);

      for (const { name, content } of files) {
        const depth = getMaxNestingDepth(content);
        expect(depth).toBeLessThanOrEqual(2);
      }
    });
  });
});
