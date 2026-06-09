/**
 * Property-based tests for CSV variant_schema formatting.
 *
 * Feature: product-model-unification
 * **Validates: Requirements 8.2, 8.3**
 *
 * Property 14: CSV export formats variant_schema correctly
 * For any product with a variant_schema containing axes and values,
 * the CSV export SHALL format variant information as "AxisName: Value1, Value2, ..."
 * for each axis, joined by "; " for multiple axes.
 * Products without variant_schema SHALL export "Standaard" in the variant column.
 */

import * as fc from 'fast-check';
import { formatVariantSchemaForCsv } from '../formatVariantSchema';
import { VariantSchema } from '../../webshop/types/unifiedProduct.types';

// ---------- Arbitraries ----------

/** Generates a valid axis name (non-empty, alphanumeric with spaces) */
const axisNameArb = fc
  .stringMatching(/^[A-Za-z][A-Za-z0-9 ]{0,14}$/)
  .filter((s) => s.trim().length > 0);

/** Generates a valid axis value (non-empty) */
const axisValueArb = fc
  .stringMatching(/^[A-Za-z0-9][A-Za-z0-9 -]{0,9}$/)
  .filter((s) => s.trim().length > 0);

/** Generates unique axis values for a single axis (1-8 values) */
const axisValuesArb = fc
  .uniqueArray(axisValueArb, { minLength: 1, maxLength: 8 })
  .filter((arr) => arr.length >= 1);

/**
 * Generates a single-axis variant schema (exactly 1 axis).
 */
const singleAxisSchemaArb: fc.Arbitrary<VariantSchema> = fc
  .tuple(axisNameArb, axisValuesArb)
  .map(([name, values]) => ({ [name]: values }));

/**
 * Generates a multi-axis variant schema (2-4 axes with unique names).
 */
const multiAxisSchemaArb: fc.Arbitrary<VariantSchema> = fc
  .uniqueArray(axisNameArb, { minLength: 2, maxLength: 4 })
  .filter((names) => names.length >= 2)
  .chain((axisNames) =>
    fc.tuple(...axisNames.map(() => axisValuesArb)).map((valuesArrays) => {
      const schema: VariantSchema = {};
      axisNames.forEach((name, i) => {
        schema[name] = valuesArrays[i];
      });
      return schema;
    })
  );

/**
 * Generates any valid variant schema (1-4 axes).
 */
const anySchemaArb: fc.Arbitrary<VariantSchema> = fc
  .uniqueArray(axisNameArb, { minLength: 1, maxLength: 4 })
  .filter((names) => names.length >= 1)
  .chain((axisNames) =>
    fc.tuple(...axisNames.map(() => axisValuesArb)).map((valuesArrays) => {
      const schema: VariantSchema = {};
      axisNames.forEach((name, i) => {
        schema[name] = valuesArrays[i];
      });
      return schema;
    })
  );

// ---------- Tests ----------

describe('CSV variant_schema formatting - Property Tests', () => {
  /**
   * **Validates: Requirements 8.3**
   *
   * Property 14a: Products without variant_schema produce "Standaard".
   */
  it('returns "Standaard" for null, undefined, or empty variant_schema', () => {
    expect(formatVariantSchemaForCsv(null)).toBe('Standaard');
    expect(formatVariantSchemaForCsv(undefined)).toBe('Standaard');
    expect(formatVariantSchemaForCsv({})).toBe('Standaard');
  });

  /**
   * **Validates: Requirements 8.2**
   *
   * Property 14b: Single-axis schemas produce "Axis: val1, val2, val3" format.
   */
  it('formats single-axis schemas as "Axis: val1, val2, val3"', () => {
    fc.assert(
      fc.property(singleAxisSchemaArb, (schema) => {
        const result = formatVariantSchemaForCsv(schema);
        const [axisName, values] = Object.entries(schema)[0];

        // Should be in format "AxisName: val1, val2, ..."
        const expected = `${axisName}: ${values.join(', ')}`;
        return result === expected;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 8.2**
   *
   * Property 14c: Multi-axis schemas produce "Axis1: val1, val2; Axis2: val3, val4" format.
   */
  it('formats multi-axis schemas with semicolon separator between axes', () => {
    fc.assert(
      fc.property(multiAxisSchemaArb, (schema) => {
        const result = formatVariantSchemaForCsv(schema);

        // Result should contain semicolons separating axes
        const axisParts = result.split('; ');
        const axisCount = Object.keys(schema).length;

        // Number of parts should equal number of axes
        if (axisParts.length !== axisCount) return false;

        // Each part should be in "AxisName: val1, val2" format
        const entries = Object.entries(schema);
        for (let i = 0; i < entries.length; i++) {
          const [axisName, values] = entries[i];
          const expectedPart = `${axisName}: ${values.join(', ')}`;
          if (axisParts[i] !== expectedPart) return false;
        }

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 8.2, 8.3**
   *
   * Property 14d: Format is consistent regardless of axis/value content — 
   * result is never empty and always either "Standaard" or contains ":" separator.
   */
  it('format is consistent: always "Standaard" or contains axis:values pattern', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          anySchemaArb,
          fc.constant(null as VariantSchema | null),
          fc.constant(undefined as VariantSchema | undefined),
          fc.constant({} as VariantSchema)
        ),
        (schema) => {
          const result = formatVariantSchemaForCsv(schema);

          // Result is never empty
          if (result.length === 0) return false;

          // Either "Standaard" or contains ":" (axis separator)
          if (!schema || Object.keys(schema).length === 0) {
            return result === 'Standaard';
          } else {
            // Must contain at least one ":" for the axis:values pattern
            return result.includes(':');
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
