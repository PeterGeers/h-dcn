/**
 * Property-based tests for VariantSelector resolution logic.
 *
 * Feature: product-model-unification
 * **Validates: Requirements 4.5, 4.6**
 *
 * Property 5: VariantSelector resolves correct variant
 * For any variant schema with N axes and a set of variant records,
 * when all N axes have selections made, the VariantSelector resolves
 * the unique variant whose variant_attributes match all selections exactly,
 * or resolves to null if no matching variant exists.
 */

import * as fc from 'fast-check';
import { resolveVariant } from '../../../components/VariantSelector';
import { VariantRecord, VariantSchema } from '../types/unifiedProduct.types';

// ---------- Arbitraries ----------

/** Generates a valid axis name (non-empty, alphanumeric-ish) */
const axisNameArb = fc
  .stringMatching(/^[A-Za-z][A-Za-z0-9 ]{0,14}$/)
  .filter((s) => s.trim().length > 0);

/** Generates a valid axis value (non-empty) */
const axisValueArb = fc
  .stringMatching(/^[A-Za-z0-9][A-Za-z0-9 -]{0,9}$/)
  .filter((s) => s.trim().length > 0);

/** Generates unique axis values for a single axis (1-5 values) */
const axisValuesArb = fc
  .uniqueArray(axisValueArb, { minLength: 1, maxLength: 5 })
  .filter((arr) => arr.length >= 1);

/**
 * Generates a valid variant schema with 1-4 axes, each with unique values.
 * Ensures axis names are unique.
 */
const variantSchemaArb: fc.Arbitrary<VariantSchema> = fc
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

/** Creates a VariantRecord from given attributes */
function makeVariantRecord(
  attributes: Record<string, string>,
  parentId: string = 'parent_001'
): VariantRecord {
  const attrKey = Object.values(attributes).join('_');
  return {
    product_id: `var_${attrKey}_${Math.random().toString(36).slice(2, 8)}`,
    parent_id: parentId,
    name: `Variant ${attrKey}`,
    variant_attributes: attributes,
    price: 25.0,
    stock: 10,
    sold_count: 0,
    allow_oversell: false,
    active: true,
  };
}

/**
 * Generate all possible combinations from a variant schema.
 * E.g. {Maat: ["S","M"], Kleur: ["R","B"]} → [{Maat:"S",Kleur:"R"}, {Maat:"S",Kleur:"B"}, ...]
 */
function allCombinations(schema: VariantSchema): Record<string, string>[] {
  const axes = Object.keys(schema);
  if (axes.length === 0) return [{}];

  const [firstAxis, ...restAxes] = axes;
  const restSchema: VariantSchema = {};
  restAxes.forEach((a) => (restSchema[a] = schema[a]));
  const restCombinations = allCombinations(restSchema);

  const result: Record<string, string>[] = [];
  for (const value of schema[firstAxis]) {
    for (const combo of restCombinations) {
      result.push({ [firstAxis]: value, ...combo });
    }
  }
  return result;
}

/**
 * Generates a variant schema AND a complete set of variant records for all combinations.
 * Returns { schema, variants, combinations }.
 */
const schemaWithFullVariantsArb = variantSchemaArb.map((schema) => {
  const combinations = allCombinations(schema);
  const variants = combinations.map((attrs) => makeVariantRecord(attrs));
  return { schema, variants, combinations };
});

/**
 * Generates a variant schema and a partial set of variant records (subset of combinations).
 * Some combinations will have variants, some won't.
 */
const schemaWithPartialVariantsArb = variantSchemaArb.chain((schema) => {
  const combinations = allCombinations(schema);
  // Randomly include/exclude each combination
  return fc
    .array(fc.boolean(), { minLength: combinations.length, maxLength: combinations.length })
    .map((includes) => {
      const variants = combinations
        .filter((_, i) => includes[i])
        .map((attrs) => makeVariantRecord(attrs));
      return { schema, variants, combinations, includes };
    });
});

// ---------- Tests ----------

describe('VariantSelector Resolution - Property Tests', () => {
  /**
   * **Validates: Requirements 4.5**
   *
   * Property 5a: When all axes are selected and a matching variant exists,
   * resolveVariant returns that specific variant (variant_attributes match exactly).
   */
  it('resolves the correct variant when all axes selected and variant exists', () => {
    fc.assert(
      fc.property(
        schemaWithFullVariantsArb,
        fc.integer({ min: 0, max: 999 }),
        ({ schema, variants, combinations }, seed) => {
          // Pick a random combination to select
          const idx = seed % combinations.length;
          const selectedCombination = combinations[idx];
          const expectedVariant = variants[idx];

          // Resolve
          const result = resolveVariant(selectedCombination, variants, schema);

          // Must return a variant (not null)
          if (result === null) return false;

          // Returned variant's variant_attributes must match all selections exactly
          const axes = Object.keys(schema);
          for (const axis of axes) {
            if (result.variant_attributes[axis] !== selectedCombination[axis]) {
              return false;
            }
          }

          // Must be the same variant object we expected
          if (result.product_id !== expectedVariant.product_id) return false;

          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 4.6**
   *
   * Property 5b: When all axes are selected but no matching variant exists,
   * resolveVariant returns null (combination unavailable).
   */
  it('returns null when all axes selected but no matching variant exists', () => {
    fc.assert(
      fc.property(schemaWithPartialVariantsArb, ({ schema, variants, combinations, includes }) => {
        // Find a combination that was NOT included (no variant exists for it)
        const missingIdx = includes.indexOf(false);
        if (missingIdx === -1) {
          // All combinations have variants — skip this case (cannot test)
          return true;
        }

        const missingCombination = combinations[missingIdx];

        // Resolve with the missing combination
        const result = resolveVariant(missingCombination, variants, schema);

        // Must return null since no variant matches
        return result === null;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 4.5**
   *
   * Property 5c: Resolution is deterministic — same inputs always produce same output.
   */
  it('resolution is deterministic for same inputs', () => {
    fc.assert(
      fc.property(
        schemaWithFullVariantsArb,
        fc.integer({ min: 0, max: 999 }),
        ({ schema, variants, combinations }, seed) => {
          const idx = seed % combinations.length;
          const selections = combinations[idx];

          // Call resolve twice with same inputs
          const result1 = resolveVariant(selections, variants, schema);
          const result2 = resolveVariant(selections, variants, schema);

          // Must return same result both times
          if (result1 === null && result2 === null) return true;
          if (result1 === null || result2 === null) return false;
          return result1.product_id === result2.product_id;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 4.5, 4.6**
   *
   * Property 5d: Incomplete selections (not all axes selected) always return null.
   */
  it('returns null when not all axes have selections', () => {
    fc.assert(
      fc.property(
        schemaWithFullVariantsArb,
        fc.integer({ min: 0, max: 999 }),
        ({ schema, variants, combinations }, seed) => {
          const axes = Object.keys(schema);
          if (axes.length < 2) {
            // With only 1 axis, we can't have incomplete selections (it's either all or nothing)
            return true;
          }

          // Pick a valid combination but remove one axis selection
          const idx = seed % combinations.length;
          const fullSelection = { ...combinations[idx] };
          const axisToRemove = axes[seed % axes.length];
          delete fullSelection[axisToRemove];

          const result = resolveVariant(fullSelection, variants, schema);
          return result === null;
        }
      ),
      { numRuns: 100 }
    );
  });
});
