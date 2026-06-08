/**
 * Property-based tests for party ticket name validation.
 *
 * Feature: presmeet-v3, Property 11
 * Validates: Requirements 9.1, 9.2
 */

import * as fc from 'fast-check';
import {
  validatePartyTicketName,
  validateBookingSubmission,
} from '../utils/validation';
import { CartItem, ProductType } from '../types/presmeet';

// --- Arbitraries ---

const itemIdArb = fc.uuid();

const unitPriceArb = fc
  .double({ min: 1, max: 500, noNaN: true })
  .map((v) => Math.round(v * 100) / 100);

/** Generates an empty string */
const emptyNameArb = fc.constant('');

/** Generates a whitespace-only string (spaces, tabs, newlines) */
const whitespaceOnlyArb = fc
  .array(fc.constantFrom(' ', '\t', '\n', '\r', '  ', '\t\t'), { minLength: 1, maxLength: 10 })
  .map((arr) => arr.join(''));

/** Generates a party_ticket CartItem with an invalid (empty/whitespace/missing) name */
const invalidPartyTicketArb: fc.Arbitrary<CartItem> = fc.oneof(
  // Case 1: name is empty string
  fc.record({
    item_id: itemIdArb,
    product_type: fc.constant('party_ticket' as ProductType),
    attributes: fc.record({ name: emptyNameArb }).map((attrs) => ({ ...attrs })),
    unit_price: unitPriceArb,
  }),
  // Case 2: name is whitespace-only
  fc.record({
    item_id: itemIdArb,
    product_type: fc.constant('party_ticket' as ProductType),
    attributes: whitespaceOnlyArb.map((ws) => ({ name: ws })),
    unit_price: unitPriceArb,
  }),
  // Case 3: name attribute is missing (not present in attributes)
  fc.record({
    item_id: itemIdArb,
    product_type: fc.constant('party_ticket' as ProductType),
    attributes: fc.constant({}),
    unit_price: unitPriceArb,
  }),
  // Case 4: name attribute is null
  fc.record({
    item_id: itemIdArb,
    product_type: fc.constant('party_ticket' as ProductType),
    attributes: fc.constant({ name: null }),
    unit_price: unitPriceArb,
  }),
  // Case 5: name attribute is undefined
  fc.record({
    item_id: itemIdArb,
    product_type: fc.constant('party_ticket' as ProductType),
    attributes: fc.constant({ name: undefined }),
    unit_price: unitPriceArb,
  })
);

/** Generates a valid non-empty name (at least one non-whitespace character) */
const validNameArb = fc
  .string({ minLength: 1, maxLength: 100 })
  .filter((s) => s.trim().length > 0);

/** Generates a party_ticket CartItem with a valid name */
const validPartyTicketArb: fc.Arbitrary<CartItem> = fc.record({
  item_id: itemIdArb,
  product_type: fc.constant('party_ticket' as ProductType),
  attributes: validNameArb.map((name) => ({ name, person_type: 'guest' })),
  unit_price: unitPriceArb,
});

/** Generates a non-party_ticket CartItem (should pass validation regardless of name) */
const nonPartyTicketArb: fc.Arbitrary<CartItem> = fc.record({
  item_id: itemIdArb,
  product_type: fc.constantFrom(
    'meeting_ticket' as ProductType,
    'tshirt' as ProductType,
    'airport_transfer' as ProductType
  ),
  attributes: fc.oneof(
    fc.constant({}),
    fc.constant({ name: '' }),
    fc.constant({ name: null }),
    validNameArb.map((name) => ({ name }))
  ),
  unit_price: unitPriceArb,
});

// --- Property Tests ---

describe('Party Ticket Name Validation - Property Tests', () => {
  /**
   * Property 11: Party ticket name validation
   *
   * For any party_ticket cart item with an empty string, whitespace-only string,
   * or missing name attribute, the validation function SHALL produce a validation
   * error indicating that a name is required.
   *
   * **Validates: Requirements 9.1, 9.2**
   */
  it('Property 11: validatePartyTicketName returns an error for any party_ticket with invalid name', () => {
    fc.assert(
      fc.property(invalidPartyTicketArb, (item) => {
        const error = validatePartyTicketName(item);

        // Must produce a non-null error
        expect(error).not.toBeNull();
        expect(error!.item_id).toBe(item.item_id);
        expect(error!.field).toBe(`items.${item.item_id}.name`);
        expect(error!.message).toContain('name');
        expect(error!.constraint).toBe('required');
      }),
      { numRuns: 100 }
    );
  });

  /**
   * Property 11 (complementary): validatePartyTicketName returns null for
   * party_ticket items with valid (non-empty, non-whitespace) names.
   *
   * **Validates: Requirements 9.1, 9.2**
   */
  it('Property 11: validatePartyTicketName returns null for party_ticket items with valid names', () => {
    fc.assert(
      fc.property(validPartyTicketArb, (item) => {
        const error = validatePartyTicketName(item);
        expect(error).toBeNull();
      }),
      { numRuns: 100 }
    );
  });

  /**
   * Property 11 (complementary): validatePartyTicketName returns null for
   * non-party_ticket items regardless of name attribute.
   *
   * **Validates: Requirements 9.1, 9.2**
   */
  it('Property 11: validatePartyTicketName returns null for non-party_ticket items', () => {
    fc.assert(
      fc.property(nonPartyTicketArb, (item) => {
        const error = validatePartyTicketName(item);
        expect(error).toBeNull();
      }),
      { numRuns: 100 }
    );
  });

  /**
   * Property 11 (batch): validateBookingSubmission returns an error for every
   * party_ticket item with an invalid name in a mixed cart.
   *
   * **Validates: Requirements 9.1, 9.2**
   */
  it('Property 11: validateBookingSubmission returns errors for all invalid party_tickets in a mixed cart', () => {
    fc.assert(
      fc.property(
        fc.array(invalidPartyTicketArb, { minLength: 1, maxLength: 5 }),
        fc.array(validPartyTicketArb, { minLength: 0, maxLength: 5 }),
        fc.array(nonPartyTicketArb, { minLength: 0, maxLength: 5 }),
        (invalidItems, validItems, otherItems) => {
          const allItems = [...invalidItems, ...validItems, ...otherItems];
          const errors = validateBookingSubmission(allItems);

          // Must have exactly as many errors as invalid party_ticket items
          expect(errors).toHaveLength(invalidItems.length);

          // Each invalid item must have a corresponding error
          for (const item of invalidItems) {
            const matchingError = errors.find((e) => e.item_id === item.item_id);
            expect(matchingError).toBeDefined();
            expect(matchingError!.constraint).toBe('required');
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
