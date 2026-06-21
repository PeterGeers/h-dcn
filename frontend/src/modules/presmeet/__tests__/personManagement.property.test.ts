/**
 * Property-based tests for person management logic.
 *
 * Feature: closed-community-booking
 * Validates: Requirements 6.1, 6.4, 6.5
 *
 * Property 12: Maximum Persons Derived from Products
 * Property 14: Person Name Sync to Product Lines
 * Property 15: Person Removal Cascades to Product Lines
 */

import * as fc from 'fast-check';
import { Product, PurchaseRules } from '../types/presmeet.types';
import { PersonFormState, PersonFormEntry, PersonProduct } from '../utils/orderTransformer';
import {
  getMaxPersons,
  syncPersonName,
  getProductLinesWithNames,
  removePerson,
} from '../utils/personManagement';

// ---------- Arbitraries ----------

/** Generates a valid max_per_club value (1–50) */
const maxPerClubArb = fc.integer({ min: 1, max: 50 });

/** Generates purchase_rules with a max_per_club value */
const purchaseRulesArb: fc.Arbitrary<PurchaseRules> = fc
  .record({
    max_per_club: fc.option(maxPerClubArb, { nil: undefined }),
    max_per_event: fc.option(fc.integer({ min: 1, max: 500 }), { nil: undefined }),
    min_per_club: fc.option(fc.integer({ min: 0, max: 10 }), { nil: undefined }),
  })
  .map((r) => {
    const rules: PurchaseRules = {};
    if (r.max_per_club !== undefined) rules.max_per_club = r.max_per_club;
    if (r.max_per_event !== undefined) rules.max_per_event = r.max_per_event;
    if (r.min_per_club !== undefined) rules.min_per_club = r.min_per_club;
    return rules;
  });

/** Generates a minimal Product with realistic purchase_rules */
const productArb: fc.Arbitrary<Product> = fc
  .record({
    product_id: fc.uuid(),
    name: fc.string({ minLength: 1, maxLength: 30 }),
    event_type: fc.constant('presmeet'),
    price: fc.double({ min: 0.01, max: 500, noNaN: true, noDefaultInfinity: true }),
    purchase_rules: purchaseRulesArb,
  })
  .map((r) => ({
    ...r,
    order_item_fields: [],
    variant_schema: null,
  }));

/** Generates a non-empty array of products */
const productsArb = fc.array(productArb, { minLength: 1, maxLength: 10 });

/** Generates a person name (non-empty trimmed string) */
const personNameArb = fc
  .string({ minLength: 1, maxLength: 50 })
  .filter((s) => s.trim().length > 0);

/** Generates a PersonProduct entry */
const personProductArb: fc.Arbitrary<PersonProduct> = fc
  .record({
    product_id: fc.uuid(),
    variant_id: fc.option(fc.uuid(), { nil: null }),
    fields: fc.constant({}),
  })
  .map((r) => ({
    product_id: r.product_id,
    variant_id: r.variant_id,
    fields: r.fields,
  }));

/** Generates a PersonFormEntry with 0–5 products */
const personFormEntryArb: fc.Arbitrary<PersonFormEntry> = fc
  .record({
    name: personNameArb,
    role: fc.string({ minLength: 0, maxLength: 20 }),
    products: fc.array(personProductArb, { minLength: 0, maxLength: 5 }),
  });

/** Generates a PersonFormState with 1–8 persons */
const personFormStateArb: fc.Arbitrary<PersonFormState> = fc
  .array(personFormEntryArb, { minLength: 1, maxLength: 8 })
  .map((persons) => ({ persons }));

/** Generates a PersonFormState with at least 2 persons (for removal tests) */
const personFormStateMultiArb: fc.Arbitrary<PersonFormState> = fc
  .array(personFormEntryArb, { minLength: 2, maxLength: 8 })
  .map((persons) => ({ persons }));

// ---------- Tests ----------

describe('Person Management - Property Tests', () => {
  /**
   * **Validates: Requirements 6.1**
   *
   * Property 12: Maximum Persons Derived from Products
   * For any set of event-linked products with varying max_per_club values,
   * the maximum number of persons allowed on an order SHALL equal the highest
   * max_per_club value across all products, with a minimum of 1.
   */
  describe('Property 12: Maximum Persons Derived from Products', () => {
    it('max persons equals the highest max_per_club across all products, minimum 1', () => {
      fc.assert(
        fc.property(productsArb, (products) => {
          const result = getMaxPersons(products);

          // Result must be at least 1
          expect(result).toBeGreaterThanOrEqual(1);

          // Result must equal the highest max_per_club value (or 1 if all are undefined/lower)
          const maxFromProducts = Math.max(
            ...products.map((p) => p.purchase_rules?.max_per_club ?? 1)
          );
          const expected = Math.max(1, maxFromProducts);
          expect(result).toBe(expected);
        }),
        { numRuns: 200 }
      );
    });

    it('returns 1 when products array is empty', () => {
      expect(getMaxPersons([])).toBe(1);
    });

    it('returns 1 when all products have max_per_club = 1', () => {
      fc.assert(
        fc.property(
          fc.array(
            productArb.map((p) => ({
              ...p,
              purchase_rules: { max_per_club: 1 },
            })),
            { minLength: 1, maxLength: 10 }
          ),
          (products) => {
            expect(getMaxPersons(products)).toBe(1);
          }
        ),
        { numRuns: 50 }
      );
    });

    it('max persons is at least as large as any single product max_per_club', () => {
      fc.assert(
        fc.property(productsArb, (products) => {
          const result = getMaxPersons(products);
          for (const product of products) {
            const productMax = product.purchase_rules?.max_per_club ?? 1;
            expect(result).toBeGreaterThanOrEqual(productMax);
          }
        }),
        { numRuns: 100 }
      );
    });
  });

  /**
   * **Validates: Requirements 6.4**
   *
   * Property 14: Person Name Sync to Product Lines
   * For any order with persons and product lines, when a person's name is
   * updated to a new value, every product line associated with that person
   * SHALL have its item_fields_data.name updated to the new value.
   * Product lines for other persons SHALL remain unchanged.
   */
  describe('Property 14: Person Name Sync to Product Lines', () => {
    it('updating a person name syncs to all their product lines and leaves others unchanged', () => {
      fc.assert(
        fc.property(
          personFormStateArb,
          fc.nat(),
          personNameArb,
          (state, rawIndex, newName) => {
            // Pick a valid person index
            const personIndex = rawIndex % state.persons.length;

            // Apply name sync
            const updatedState = syncPersonName(state, personIndex, newName);

            // The updated person should have the new name
            expect(updatedState.persons[personIndex].name).toBe(newName);

            // All product lines for the updated person should reflect the new name
            const lines = getProductLinesWithNames(updatedState);
            const updatedPersonLines = lines.filter((l) => l.personIndex === personIndex);
            for (const line of updatedPersonLines) {
              expect(line.name).toBe(newName);
            }

            // Product lines for other persons should be unchanged
            const otherLines = lines.filter((l) => l.personIndex !== personIndex);
            const originalLines = getProductLinesWithNames(state).filter(
              (l) => l.personIndex !== personIndex
            );
            expect(otherLines).toEqual(originalLines);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('products array of the updated person is preserved (only name changes)', () => {
      fc.assert(
        fc.property(
          personFormStateArb,
          fc.nat(),
          personNameArb,
          (state, rawIndex, newName) => {
            const personIndex = rawIndex % state.persons.length;
            const updatedState = syncPersonName(state, personIndex, newName);

            // Products array should be identical (same references)
            expect(updatedState.persons[personIndex].products).toEqual(
              state.persons[personIndex].products
            );

            // Role should be unchanged
            expect(updatedState.persons[personIndex].role).toBe(
              state.persons[personIndex].role
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * **Validates: Requirements 6.5**
   *
   * Property 15: Person Removal Cascades to Product Lines
   * For any order with N persons and their associated product lines,
   * removing person at index I SHALL:
   * (a) remove all product lines where the person index matches I,
   * (b) leave all product lines for other persons intact,
   * (c) result in exactly (N-1) persons remaining.
   */
  describe('Property 15: Person Removal Cascades to Product Lines', () => {
    it('removing a person results in (N-1) persons and removes all their product lines', () => {
      fc.assert(
        fc.property(
          personFormStateMultiArb,
          fc.nat(),
          (state, rawIndex) => {
            const N = state.persons.length;
            const personIndex = rawIndex % N;

            // Capture the product lines before removal
            const linesBefore = getProductLinesWithNames(state);
            const removedPersonLines = linesBefore.filter(
              (l) => l.personIndex === personIndex
            );

            // Remove the person
            const updatedState = removePerson(state, personIndex);

            // (c) Result has exactly (N-1) persons
            expect(updatedState.persons.length).toBe(N - 1);

            // (a) All product lines for the removed person are gone
            const linesAfter = getProductLinesWithNames(updatedState);
            // Total lines after should be total before minus removed person's lines
            expect(linesAfter.length).toBe(
              linesBefore.length - removedPersonLines.length
            );

            // (b) Product lines for other persons are intact (content preserved)
            // After removal, indices shift: persons after the removed index shift down by 1
            for (const afterLine of linesAfter) {
              // Find the original person index
              const originalIdx =
                afterLine.personIndex >= personIndex
                  ? afterLine.personIndex + 1
                  : afterLine.personIndex;

              // The person's data should match the original
              expect(updatedState.persons[afterLine.personIndex].name).toBe(
                state.persons[originalIdx].name
              );
              expect(updatedState.persons[afterLine.personIndex].products).toEqual(
                state.persons[originalIdx].products
              );
            }
          }
        ),
        { numRuns: 200 }
      );
    });

    it('removing an out-of-range index returns state unchanged', () => {
      fc.assert(
        fc.property(personFormStateArb, (state) => {
          const resultNeg = removePerson(state, -1);
          const resultOver = removePerson(state, state.persons.length);

          expect(resultNeg).toBe(state);
          expect(resultOver).toBe(state);
        }),
        { numRuns: 50 }
      );
    });

    it('each remaining person preserves their products array exactly', () => {
      fc.assert(
        fc.property(
          personFormStateMultiArb,
          fc.nat(),
          (state, rawIndex) => {
            const personIndex = rawIndex % state.persons.length;
            const updatedState = removePerson(state, personIndex);

            // Build expected persons (all except the removed one)
            const expectedPersons = state.persons.filter((_, idx) => idx !== personIndex);

            expect(updatedState.persons.length).toBe(expectedPersons.length);
            for (let i = 0; i < expectedPersons.length; i++) {
              expect(updatedState.persons[i].name).toBe(expectedPersons[i].name);
              expect(updatedState.persons[i].role).toBe(expectedPersons[i].role);
              expect(updatedState.persons[i].products).toEqual(expectedPersons[i].products);
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
