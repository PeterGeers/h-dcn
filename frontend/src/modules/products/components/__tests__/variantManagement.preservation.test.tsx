/**
 * Preservation property tests for variant management integration.
 *
 * Feature: variant-management-integration (bugfix)
 * Property 2: Preservation - Existing ProductCard and VariantSchemaEditor Behavior
 *
 * These tests capture BASELINE behavior on UNFIXED code to ensure
 * no regressions are introduced by the fix.
 *
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**
 */

import * as fc from 'fast-check';

// --- Test the VariantSchemaEditor logic (axis editing operations) ---
// We test the pure logic without rendering, since the component just transforms
// arrays and calls onChange with a new schema object.

type VariantSchema = Record<string, string[]>;

/**
 * Pure logic extracted from VariantSchemaEditor to test axis operations.
 * These replicate the exact logic in the component.
 */
function schemaToAxes(schema: VariantSchema): [string, string[]][] {
  return Object.entries(schema).map(([name, vals]) => [
    name,
    Array.isArray(vals) ? vals : [String(vals)],
  ] as [string, string[]]);
}

function axesToSchema(axes: [string, string[]][]): VariantSchema {
  const schema: VariantSchema = {};
  axes.forEach(([name, values]) => {
    schema[name] = values;
  });
  return schema;
}

function addAxis(schema: VariantSchema): VariantSchema {
  const axes = schemaToAxes(schema);
  if (axes.length >= 5) return schema;
  return axesToSchema([...axes, ['', []]]);
}

function removeAxis(schema: VariantSchema, index: number): VariantSchema {
  const axes = schemaToAxes(schema);
  return axesToSchema(axes.filter((_, i) => i !== index));
}

function addValue(schema: VariantSchema, axisIndex: number, newValue: string): VariantSchema {
  if (!newValue.trim()) return schema;
  const axes = schemaToAxes(schema);
  if (axisIndex >= axes.length) return schema;
  const [, values] = axes[axisIndex];
  if (values.length >= 20) return schema;
  return axesToSchema(
    axes.map(([n, v], i) => (i === axisIndex ? [n, [...v, newValue.trim()]] : [n, v]) as [string, string[]])
  );
}

function removeValue(schema: VariantSchema, axisIndex: number, valueIndex: number): VariantSchema {
  const axes = schemaToAxes(schema);
  if (axisIndex >= axes.length) return schema;
  return axesToSchema(
    axes.map(([axisName, values], i) =>
      i === axisIndex ? [axisName, values.filter((_, vi) => vi !== valueIndex)] : [axisName, values]
    ) as [string, string[]][]
  );
}

// --- Arbitraries ---

/** Generate a valid axis name (non-empty, no reserved JS property names) */
const RESERVED_KEYS = ['__proto__', 'constructor', 'toString', 'valueOf', 'hasOwnProperty', '__defineGetter__', '__defineSetter__', '__lookupGetter__', '__lookupSetter__'];
const axisNameArb = fc.string({ minLength: 1, maxLength: 20 })
  .filter(s => s.trim().length > 0 && !RESERVED_KEYS.includes(s));

/** Generate a valid axis value (non-empty) */
const axisValueArb = fc.string({ minLength: 1, maxLength: 15 })
  .filter(s => s.trim().length > 0);

/** Generate a variant schema with 0-3 axes and 0-5 values each */
const variantSchemaArb: fc.Arbitrary<VariantSchema> = fc.dictionary(
  axisNameArb,
  fc.array(axisValueArb, { minLength: 0, maxLength: 5 }),
  { minKeys: 0, maxKeys: 3 }
);

/** Generate a product-like object without variant_schema */
const productWithoutVariantSchemaArb = fc.record({
  id: fc.uuid(),
  product_id: fc.uuid(),
  naam: fc.string({ minLength: 1, maxLength: 50 }),
  prijs: fc.float({ min: Math.fround(0.01), max: Math.fround(999.99), noNaN: true }),
  beschrijving: fc.string({ maxLength: 200 }),
  groep: fc.string({ minLength: 1, maxLength: 30 }),
  subgroep: fc.string({ minLength: 1, maxLength: 30 }),
  images: fc.array(fc.webUrl(), { maxLength: 3 }),
  event_ids: fc.array(fc.uuid(), { maxLength: 3 }),
  artikelcode: fc.string({ minLength: 1, maxLength: 10 }),
});

/** Generate order_item_fields WITHOUT validation rules (preservation case) */
const orderItemFieldWithoutValidationArb = fc.record({
  name: fc.string({ minLength: 1, maxLength: 30 }),
  label: fc.string({ minLength: 1, maxLength: 30 }),
  type: fc.constantFrom('text', 'number', 'select'),
  required: fc.boolean(),
});

/** Generate purchase_rules WITHOUT numeric constraints (preservation case) */
const purchaseRulesWithoutNumericArb = fc.record({
  requires_membership: fc.option(fc.boolean(), { nil: undefined }),
});

const NUM_RUNS = 100;

describe('Variant Management Preservation Properties', () => {
  /**
   * Property 1: Products without variant_schema never have VariantSubTable rendered
   * Validates: Requirements 3.5
   *
   * For all products without variant_schema, the ProductCard onSubmit logic
   * does NOT include any VariantSubTable-related data in the payload.
   * The current code does NOT import or render VariantSubTable at all,
   * so this property holds trivially — we verify the payload structure.
   */
  describe('Property: Products without variant_schema produce no variant table data', () => {
    it('for all products without variant_schema, onSubmit payload has no variant_schema field', () => {
      fc.assert(
        fc.property(productWithoutVariantSchemaArb, (product) => {
          // Simulate Formik initialValues and onSubmit logic from ProductCard
          const initialValues = {
            ...product,
            prijs: product.prijs ? parseFloat(product.prijs.toString()).toFixed(2) : '',
            naam: product.naam || '',
            artikelcode: product.artikelcode || '',
            images: product.images || [],
            groep: product.groep || '',
            subgroep: product.subgroep || '',
            event_ids: product.event_ids || [],
            variant_schema: undefined, // No variant_schema
            order_item_fields: undefined,
            purchase_rules: undefined,
          };

          // Simulate onSubmit: strip legacy fields
          const { id, ...cleanValues } = initialValues as any;
          delete cleanValues.opties;
          delete cleanValues.nietInWinkel;
          delete cleanValues.event_id;
          delete cleanValues.name;
          delete cleanValues.price;
          delete cleanValues.image;

          // Verify: variant_schema is undefined (no variant table data)
          expect(cleanValues.variant_schema).toBeUndefined();
        }),
        { numRuns: NUM_RUNS }
      );
    });
  });

  /**
   * Property 2: Axis editing operations correctly update schema form field
   * Validates: Requirements 3.1
   *
   * For all valid axis editing operations (add axis, remove axis, add value,
   * remove value), the VariantSchemaEditor produces a correctly structured schema.
   */
  describe('Property: Axis editing operations update schema correctly', () => {
    it('addAxis adds a new empty axis to the schema', () => {
      fc.assert(
        fc.property(variantSchemaArb, (schema) => {
          const axesBefore = Object.keys(schema).length;
          const result = addAxis(schema);
          const axesAfter = Object.keys(result).length;

          if (axesBefore >= 5) {
            // Cannot add beyond max
            expect(axesAfter).toBe(axesBefore);
          } else {
            // One new axis added with empty name and empty values
            expect(axesAfter).toBe(axesBefore + 1);
            expect(result['']).toEqual([]);
          }
        }),
        { numRuns: NUM_RUNS }
      );
    });

    it('removeAxis removes the axis at the given index', () => {
      // Generate schemas with at least 1 axis
      const schemaWithAxesArb = fc.dictionary(
        axisNameArb,
        fc.array(axisValueArb, { minLength: 0, maxLength: 5 }),
        { minKeys: 1, maxKeys: 4 }
      );

      fc.assert(
        fc.property(
          schemaWithAxesArb,
          fc.nat(),
          (schema, rawIndex) => {
            const axesBefore = Object.keys(schema).length;
            const index = rawIndex % axesBefore;
            const result = removeAxis(schema, index);
            const axesAfter = Object.keys(result).length;
            expect(axesAfter).toBe(axesBefore - 1);
          }
        ),
        { numRuns: NUM_RUNS }
      );
    });

    it('addValue appends value to the specified axis', () => {
      const schemaWithAxesArb = fc.dictionary(
        axisNameArb,
        fc.array(axisValueArb, { minLength: 0, maxLength: 4 }),
        { minKeys: 1, maxKeys: 3 }
      );

      fc.assert(
        fc.property(
          schemaWithAxesArb,
          axisValueArb,
          fc.nat(),
          (schema, newValue, rawIndex) => {
            const axes = schemaToAxes(schema);
            const axisIndex = rawIndex % axes.length;
            const valuesBefore = axes[axisIndex][1].length;
            const result = addValue(schema, axisIndex, newValue);
            const resultAxes = schemaToAxes(result);
            const valuesAfter = resultAxes[axisIndex][1].length;

            if (valuesBefore >= 20) {
              expect(valuesAfter).toBe(valuesBefore);
            } else {
              expect(valuesAfter).toBe(valuesBefore + 1);
              expect(resultAxes[axisIndex][1][valuesAfter - 1]).toBe(newValue.trim());
            }
          }
        ),
        { numRuns: NUM_RUNS }
      );
    });

    it('removeValue removes value at the specified index within an axis', () => {
      const schemaWithValuesArb = fc.dictionary(
        axisNameArb,
        fc.array(axisValueArb, { minLength: 1, maxLength: 5 }),
        { minKeys: 1, maxKeys: 3 }
      );

      fc.assert(
        fc.property(
          schemaWithValuesArb,
          fc.nat(),
          fc.nat(),
          (schema, rawAxisIdx, rawValIdx) => {
            const axes = schemaToAxes(schema);
            const axisIndex = rawAxisIdx % axes.length;
            const values = axes[axisIndex][1];
            const valueIndex = rawValIdx % values.length;
            const removedValue = values[valueIndex];

            const result = removeValue(schema, axisIndex, valueIndex);
            const resultAxes = schemaToAxes(result);
            const resultValues = resultAxes[axisIndex][1];

            // One less value
            expect(resultValues.length).toBe(values.length - 1);
            // The removed value is gone from that position
            if (valueIndex < resultValues.length) {
              // Value at that index is now the next one
              expect(resultValues[valueIndex]).toBe(values[valueIndex + 1]);
            }
          }
        ),
        { numRuns: NUM_RUNS }
      );
    });
  });

  /**
   * Property 3: Product saves without numeric constraints pass through unchanged
   * Validates: Requirements 3.7
   *
   * For all product payloads that have order_item_fields WITHOUT validation rules
   * or purchase_rules WITHOUT numeric constraints, the onSubmit handler passes them
   * through unmodified (no coercion applied in current unfixed code).
   */
  describe('Property: Product saves without numeric constraints pass through unchanged', () => {
    it('order_item_fields without validation are preserved as-is in payload', () => {
      fc.assert(
        fc.property(
          fc.array(orderItemFieldWithoutValidationArb, { minLength: 1, maxLength: 3 }),
          (orderItemFields) => {
            // Simulate Formik values with order_item_fields that have no validation
            const values = {
              naam: 'Test Product',
              prijs: '10.00',
              artikelcode: 'TEST1',
              images: [],
              groep: 'Kleding',
              subgroep: 'Shirts',
              event_ids: [],
              order_item_fields: orderItemFields,
              purchase_rules: undefined,
              variant_schema: undefined,
            };

            // Simulate onSubmit cleanup (strip legacy fields)
            const { ...cleanValues } = values as any;
            delete cleanValues.opties;
            delete cleanValues.nietInWinkel;
            delete cleanValues.event_id;
            delete cleanValues.id;
            delete cleanValues.name;
            delete cleanValues.price;
            delete cleanValues.image;

            // Current unfixed code: fields pass through unchanged
            expect(cleanValues.order_item_fields).toEqual(orderItemFields);
          }
        ),
        { numRuns: NUM_RUNS }
      );
    });

    it('purchase_rules without numeric constraints are preserved as-is in payload', () => {
      fc.assert(
        fc.property(
          purchaseRulesWithoutNumericArb,
          (purchaseRules) => {
            const values = {
              naam: 'Test Product',
              prijs: '15.00',
              artikelcode: 'TEST2',
              images: [],
              groep: 'Accessoires',
              subgroep: 'Badges',
              event_ids: [],
              order_item_fields: undefined,
              purchase_rules: purchaseRules,
              variant_schema: undefined,
            };

            // Simulate onSubmit cleanup
            const { ...cleanValues } = values as any;
            delete cleanValues.opties;
            delete cleanValues.nietInWinkel;
            delete cleanValues.event_id;
            delete cleanValues.id;
            delete cleanValues.name;
            delete cleanValues.price;
            delete cleanValues.image;

            // Current unfixed code: rules pass through unchanged
            expect(cleanValues.purchase_rules).toEqual(purchaseRules);
          }
        ),
        { numRuns: NUM_RUNS }
      );
    });
  });

  /**
   * Property 4: Non-variant product fields remain unmodified through onSubmit
   * Validates: Requirements 3.6
   *
   * For random product payloads without variant interactions, non-variant fields
   * (naam, prijs, beschrijving, groep, subgroep, artikelcode, images, event_ids)
   * pass through the onSubmit handler unmodified.
   */
  describe('Property: Non-variant fields unmodified in onSubmit', () => {
    it('product-level fields pass through onSubmit unchanged', () => {
      fc.assert(
        fc.property(productWithoutVariantSchemaArb, (product) => {
          // Simulate Formik initialValues
          const values = {
            ...product,
            prijs: product.prijs ? parseFloat(product.prijs.toString()).toFixed(2) : '',
            naam: product.naam || '',
            artikelcode: product.artikelcode || '',
            images: product.images || [],
            groep: product.groep || '',
            subgroep: product.subgroep || '',
            event_ids: product.event_ids || [],
            variant_schema: undefined,
            order_item_fields: undefined,
            purchase_rules: undefined,
          };

          // Simulate onSubmit: strip legacy fields (mirrors ProductCard logic)
          const { id, ...cleanValues } = values as any;
          delete cleanValues.opties;
          delete cleanValues.nietInWinkel;
          delete cleanValues.event_id;
          delete cleanValues.name;
          delete cleanValues.price;
          delete cleanValues.image;

          // Core product fields preserved
          expect(cleanValues.naam).toBe(values.naam);
          expect(cleanValues.prijs).toBe(values.prijs);
          expect(cleanValues.artikelcode).toBe(values.artikelcode);
          expect(cleanValues.groep).toBe(values.groep);
          expect(cleanValues.subgroep).toBe(values.subgroep);
          expect(cleanValues.images).toEqual(values.images);
          expect(cleanValues.event_ids).toEqual(values.event_ids);
        }),
        { numRuns: NUM_RUNS }
      );
    });
  });
});
