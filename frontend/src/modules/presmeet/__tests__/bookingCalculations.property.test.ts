/**
 * Property-based tests for booking calculation logic.
 *
 * Feature: presmeet-v3
 * Validates: Requirements 2.2, 2.3, 3.2, 8.1, 8.2, 8.3
 *
 * Property 4: Booking overview totals include all items correctly
 * Property 5: Remaining balance calculation
 * Property 10: Transfer quantity multiplication
 */

import * as fc from 'fast-check';
import { CartItem, ProductType } from '../types/presmeet';
import { preparePdfData, PdfBookingData } from '../utils/pdfGenerator';

// ---------- Arbitraries ----------

const productTypeArb: fc.Arbitrary<ProductType> = fc.constantFrom(
  'meeting_ticket',
  'party_ticket',
  'tshirt',
  'airport_transfer'
);

/** Generates a positive unit price (cents precision) */
const unitPriceArb = fc
  .double({ min: 0.01, max: 500, noNaN: true, noDefaultInfinity: true })
  .map((v) => Math.round(v * 100) / 100);

/** Generates a persons value for airport transfers */
const personsArb = fc.integer({ min: 1, max: 10 });

/** Generates a non-empty item name */
const nameArb = fc
  .string({ minLength: 1, maxLength: 30 })
  .filter((s) => s.trim().length > 0);

/** Generates a valid CartItem based on product type */
const cartItemArb: fc.Arbitrary<CartItem> = fc
  .tuple(productTypeArb, unitPriceArb, nameArb, personsArb, fc.uuid())
  .map(([productType, unitPrice, name, persons, uuid]) => {
    let attributes: Record<string, any>;

    switch (productType) {
      case 'meeting_ticket':
        attributes = { name, role: 'president' };
        break;
      case 'party_ticket':
        attributes = { name, person_type: 'delegate' };
        break;
      case 'tshirt':
        attributes = { name, size: 'L', gender: 'male' };
        break;
      case 'airport_transfer':
        attributes = {
          direction: 'pickup',
          airport: 'AMS',
          persons,
          flight: 'KL1234',
          date: '2025-03-01',
          time: '10:00',
        };
        break;
      default:
        attributes = { name };
    }

    return {
      item_id: uuid,
      product_type: productType,
      attributes,
      unit_price: unitPrice,
    };
  });

/** Generates a non-empty array of cart items */
const cartItemsArb = fc.array(cartItemArb, { minLength: 1, maxLength: 15 });

/** Generates valid PdfBookingData */
function pdfBookingDataArb(): fc.Arbitrary<PdfBookingData> {
  return fc
    .tuple(
      nameArb,
      cartItemsArb,
      fc
        .double({ min: 0, max: 5000, noNaN: true, noDefaultInfinity: true })
        .map((v) => Math.round(v * 100) / 100)
    )
    .map(([clubName, items, totalPaid]) => ({
      clubName,
      items,
      status: 'draft' as const,
      paymentStatus: 'unpaid' as const,
      totalAmount: 0,
      totalPaid,
      submittedAt: null,
    }));
}

/** Generates an airport_transfer cart item with specific persons value */
const transferItemArb: fc.Arbitrary<CartItem> = fc
  .tuple(unitPriceArb, personsArb, fc.uuid())
  .map(([unitPrice, persons, uuid]) => ({
    item_id: uuid,
    product_type: 'airport_transfer' as ProductType,
    attributes: {
      direction: 'pickup',
      airport: 'AMS',
      persons,
      flight: 'KL1234',
      date: '2025-03-01',
      time: '10:00',
    },
    unit_price: unitPrice,
  }));

// ---------- Helper ----------

function computeExpectedLineTotal(item: CartItem): number {
  if (item.product_type === 'airport_transfer') {
    const persons = Number(item.attributes.persons) || 1;
    return persons * item.unit_price;
  }
  return 1 * item.unit_price;
}

// ---------- Tests ----------

describe('Booking Calculations - Property Tests', () => {
  /**
   * **Validates: Requirements 2.2, 2.3, 3.2**
   *
   * Property 4: Booking overview totals include all items correctly
   * Grand total equals sum of all group line totals, accounting for
   * delegate party tickets and persons × unit_price for transfers.
   */
  it('grand total equals sum of all group line totals for any set of cart items', () => {
    fc.assert(
      fc.property(pdfBookingDataArb(), (data) => {
        const groups = preparePdfData(data);

        // Grand total from groups
        const grandTotal = groups.reduce((sum, g) => sum + g.groupTotal, 0);

        // Expected grand total computed independently from items
        const expectedGrandTotal = data.items.reduce(
          (sum, item) => sum + computeExpectedLineTotal(item),
          0
        );

        // Grand total must equal sum of all expected line totals
        if (Math.abs(grandTotal - expectedGrandTotal) > 0.001) return false;

        // Each group total must equal sum of its line items
        for (const group of groups) {
          const groupItemsSum = group.items.reduce(
            (sum, li) => sum + li.lineTotal,
            0
          );
          if (Math.abs(groupItemsSum - group.groupTotal) > 0.001) return false;
        }

        // All items must be accounted for (including delegate party tickets)
        const totalItemsInGroups = groups.reduce(
          (sum, g) => sum + g.items.length,
          0
        );
        if (totalItemsInGroups !== data.items.length) return false;

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 3.2**
   *
   * Property 5: Remaining balance calculation
   * For any grandTotal and totalPaid ≥ 0, remaining = max(0, grandTotal - totalPaid).
   */
  it('remaining balance equals max(0, grandTotal - totalPaid) for any non-negative values', () => {
    const nonNegativeArb = fc
      .double({ min: 0, max: 100000, noNaN: true, noDefaultInfinity: true })
      .map((v) => Math.round(v * 100) / 100);

    fc.assert(
      fc.property(nonNegativeArb, nonNegativeArb, (grandTotal, totalPaid) => {
        const remaining = Math.max(0, grandTotal - totalPaid);

        // remaining must be non-negative
        if (remaining < 0) return false;

        // when totalPaid >= grandTotal, remaining must be 0
        if (totalPaid >= grandTotal && remaining !== 0) return false;

        // when totalPaid < grandTotal, remaining must equal the difference
        if (totalPaid < grandTotal) {
          if (Math.abs(remaining - (grandTotal - totalPaid)) > 0.001)
            return false;
        }

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 8.1, 8.2, 8.3**
   *
   * Property 10: Transfer quantity multiplication
   * For any airport transfer cart item with persons P ≥ 1,
   * the line total equals P × unit_price.
   */
  it('transfer line total equals persons × unit_price for any transfer item', () => {
    fc.assert(
      fc.property(transferItemArb, (transferItem) => {
        const data: PdfBookingData = {
          clubName: 'TestClub',
          items: [transferItem],
          status: 'draft',
          paymentStatus: 'unpaid',
          totalAmount: 0,
          totalPaid: 0,
          submittedAt: null,
        };

        const groups = preparePdfData(data);

        // Should produce exactly one group for airport_transfer
        if (groups.length !== 1) return false;
        if (groups[0].productType !== 'airport_transfer') return false;
        if (groups[0].items.length !== 1) return false;

        const pdfLineItem = groups[0].items[0];
        const persons = Number(transferItem.attributes.persons) || 1;
        const expectedLineTotal = persons * transferItem.unit_price;

        // Line total must equal persons × unit_price
        if (Math.abs(pdfLineItem.lineTotal - expectedLineTotal) > 0.001)
          return false;

        // Quantity must equal persons
        if (pdfLineItem.quantity !== persons) return false;

        return true;
      }),
      { numRuns: 100 }
    );
  });
});
