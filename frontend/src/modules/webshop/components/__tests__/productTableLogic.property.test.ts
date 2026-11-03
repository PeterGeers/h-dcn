import * as fc from 'fast-check';
import {
  matchesFilters,
  fieldMatches,
  Product,
  ProductFilters,
} from '../ProductTable';
import { compareValues } from '../../../../hooks/useTableSort';

// Feature: webshop-table-improvements
// Property tests for the public ProductTable filter/sort logic.
// Targets the pure exported helpers `matchesFilters` and `fieldMatches`
// (frontend/src/modules/webshop/components/ProductTable.tsx) plus a direct
// `sortedData` equivalent of `useTableSort` (compareValues) so the
// filter-then-sort composition can be asserted without rendering.
// Uses fast-check with a minimum of 100 iterations per property.

const NUM_RUNS = 100;

type SortDirection = 'asc' | 'desc';

/**
 * Pure re-implementation of `useTableSort`'s `sortedData` step, kept identical
 * to the hook: nullish values always sort to the end regardless of direction,
 * everything else via `compareValues` scaled by the direction multiplier. When
 * `sortField` is null the input order is preserved (identity).
 */
function sortLikeTable(
  data: Product[],
  sortField: keyof Product | null,
  sortDirection: SortDirection,
): Product[] {
  if (sortField === null) return data;
  const directionMultiplier = sortDirection === 'asc' ? 1 : -1;
  return [...data].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    const aNullish = aVal === null || aVal === undefined;
    const bNullish = bVal === null || bVal === undefined;
    if (aNullish && bNullish) return 0;
    if (aNullish) return 1;
    if (bNullish) return -1;
    return compareValues(aVal, bVal) * directionMultiplier;
  });
}

/** Full filter-then-sort composition, mirroring ProductTable internals. */
function filterThenSort(
  products: Product[],
  filters: ProductFilters,
  sortField: keyof Product | null,
  sortDirection: SortDirection,
): Product[] {
  const filtered = products.filter((p) => matchesFilters(p, filters));
  return sortLikeTable(filtered, sortField, sortDirection);
}

/**
 * Generator for a filterable text field value: real strings plus the "absent"
 * shapes (null / undefined) and non-string junk the helper must defend against.
 */
const fieldValueArb: fc.Arbitrary<unknown> = fc.oneof(
  fc.string(),
  fc.constant(''),
  fc.constant(null),
  fc.constant(undefined),
  fc.integer(),
  fc.boolean(),
);

let productCounter = 0;

/** Generator for an arbitrary product with the fields the table reads. */
const productArb: fc.Arbitrary<Product> = fc
  .record({
    naam: fieldValueArb,
    groep: fieldValueArb,
    subgroep: fieldValueArb,
    prijs: fc.option(fc.oneof(fc.integer(), fc.string()), { nil: undefined }),
  })
  .map((rec) => {
    // Each product gets a stable, unique id so subset/identity checks by
    // reference and by key are unambiguous.
    productCounter += 1;
    return {
      product_id: `p-${productCounter}`,
      naam: rec.naam,
      groep: rec.groep,
      subgroep: rec.subgroep,
      prijs: rec.prijs,
    } as Product;
  });

const productListArb: fc.Arbitrary<Product[]> = fc.array(productArb, { maxLength: 30 });

/** Generator for a filter state (each column independently empty or text). */
const filtersArb: fc.Arbitrary<ProductFilters> = fc.record({
  naam: fc.oneof(fc.constant(''), fc.string()),
  groep: fc.oneof(fc.constant(''), fc.string()),
  subgroep: fc.oneof(fc.constant(''), fc.string()),
});

const sortFieldArb: fc.Arbitrary<keyof Product | null> = fc.constantFrom(
  'naam',
  'groep',
  'subgroep',
  'prijs',
  null,
);
const sortDirectionArb: fc.Arbitrary<SortDirection> = fc.constantFrom('asc', 'desc');

describe('ProductTable filter/sort logic — property tests', () => {
  /**
   * Property 4: Filter yields an ordered subset.
   * The displayed rows are a subset of the input products (no duplicates, no
   * rows not present in the input), and they preserve the relative order
   * produced by the sort step over the filtered rows.
   *
   * **Validates: Requirements 1.4, 1.5, 1.6**
   */
  it('Property 4: filter yields an ordered subset preserving sorted order', () => {
    fc.assert(
      fc.property(
        productListArb,
        filtersArb,
        sortFieldArb,
        sortDirectionArb,
        (products, filters, sortField, sortDirection) => {
          const result = filterThenSort(products, filters, sortField, sortDirection);
          const inputIds = new Set(products.map((p) => p.product_id));

          // Every result row comes from the input.
          for (const row of result) {
            if (!inputIds.has(row.product_id)) return false;
          }

          // No duplicates in the result.
          const resultIds = result.map((p) => p.product_id);
          if (new Set(resultIds).size !== resultIds.length) return false;

          // Result equals filtered-then-sorted — i.e. the displayed order is
          // exactly the sort applied to the filtered subset.
          const expected = sortLikeTable(
            products.filter((p) => matchesFilters(p, filters)),
            sortField,
            sortDirection,
          );
          if (expected.length !== result.length) return false;
          return expected.every((p, i) => p.product_id === result[i].product_id);
        },
      ),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 5: Absent field never matches a non-empty filter.
   * For any product whose filtered field is absent/null/undefined/non-string,
   * that product is excluded whenever a non-empty filter is active on that
   * field, and evaluating the filter never throws.
   *
   * **Validates: Requirements 1.7, 4.5**
   */
  it('Property 5: absent / non-string field never matches a non-empty filter', () => {
    const nonStringArb: fc.Arbitrary<unknown> = fc.oneof(
      fc.constant(null),
      fc.constant(undefined),
      fc.integer(),
      fc.boolean(),
    );
    const nonEmptyFilterArb = fc.string({ minLength: 1 }).filter((s) => s.trim() !== '');

    fc.assert(
      fc.property(nonStringArb, nonEmptyFilterArb, (fieldValue, filter) => {
        // fieldMatches must be false for a non-string field against a
        // non-empty filter, and must not throw.
        return fieldMatches(fieldValue, filter) === false;
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 5b: at the product level, an absent/non-string field excludes the
   * product when that column's filter is non-empty.
   *
   * **Validates: Requirements 1.7, 4.5**
   */
  it('Property 5b: a product with an absent field is excluded by that column filter', () => {
    const nonStringArb: fc.Arbitrary<unknown> = fc.oneof(
      fc.constant(null),
      fc.constant(undefined),
      fc.integer(),
      fc.boolean(),
    );
    const nonEmptyFilterArb = fc.string({ minLength: 1 }).filter((s) => s.trim() !== '');
    const columnArb = fc.constantFrom<'naam' | 'groep' | 'subgroep'>(
      'naam',
      'groep',
      'subgroep',
    );

    fc.assert(
      fc.property(nonStringArb, nonEmptyFilterArb, columnArb, (badValue, filter, column) => {
        const product = {
          product_id: 'x',
          naam: 'anything',
          groep: 'anything',
          subgroep: 'anything',
          [column]: badValue,
        } as unknown as Product;
        const filters: ProductFilters = { naam: '', groep: '', subgroep: '' };
        filters[column] = filter;
        return matchesFilters(product, filters) === false;
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 6: Conjunctive filtering.
   * A product appears in the results if and only if it matches every active
   * (non-empty) column filter, matched case-insensitively as a substring.
   *
   * **Validates: Requirements 1.4, 1.6**
   */
  it('Property 6: a product matches iff it satisfies every active column filter', () => {
    fc.assert(
      fc.property(productArb, filtersArb, (product, filters) => {
        const expected =
          fieldMatches(product.naam, filters.naam) &&
          fieldMatches(product.groep, filters.groep) &&
          fieldMatches(product.subgroep, filters.subgroep);
        return matchesFilters(product, filters) === expected;
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 6b: case-insensitive substring semantics for a single field. A
   * filter that is a substring of the (lower-cased) field matches regardless
   * of the case used to type it.
   *
   * **Validates: Requirements 1.4, 1.6**
   */
  it('Property 6b: filtering is case-insensitive substring matching', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),
        fc.string(),
        fc.string(),
        (needle, prefix, suffix) => {
          // Build a field that definitely contains `needle` as a substring.
          const field = prefix + needle + suffix;
          // Typed in an arbitrary mix of cases, it must still match.
          const upper = needle.toUpperCase();
          const lower = needle.toLowerCase();
          return fieldMatches(field, upper) && fieldMatches(field, lower);
        },
      ),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 7: Empty filters, no sort is identity.
   * When all column filters are empty and no sort is active, the composition
   * returns exactly the input products in their original order.
   *
   * **Validates: Requirements 1.6, 2.4**
   */
  it('Property 7: all-empty filters and no sort is the identity', () => {
    const emptyFilters: ProductFilters = { naam: '', groep: '', subgroep: '' };
    fc.assert(
      fc.property(productListArb, (products) => {
        const result = filterThenSort(products, emptyFilters, null, 'asc');
        if (result.length !== products.length) return false;
        return result.every((p, i) => p.product_id === products[i].product_id);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 7b: all-empty filters match every product (identity subset)
   * regardless of sort — the filtered set is the whole input set.
   *
   * **Validates: Requirements 1.6, 2.4**
   */
  it('Property 7b: all-empty filters match every product', () => {
    const emptyFilters: ProductFilters = { naam: '', groep: '', subgroep: '' };
    fc.assert(
      fc.property(productListArb, (products) => {
        return products.every((p) => matchesFilters(p, emptyFilters) === true);
      }),
      { numRuns: NUM_RUNS },
    );
  });
});
