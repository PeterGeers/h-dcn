/**
 * Property-based tests for the PDF Generator utility.
 *
 * Feature: presmeet-v3
 * Validates: Requirements 1.1, 1.2, 1.4, 1.5
 *
 * Property 1: PDF data preparation produces correct grouped output
 * Property 2: PDF includes payment instructions conditionally
 * Property 3: PDF filename matches expected pattern
 */

import * as fc from 'fast-check';
import { CartItem, ProductType, PaymentStatus } from '../types/presmeet';
import { PdfBookingData } from '../utils/pdfGenerator';

// ---------- Mock jsPDF for Property 2 ----------

/** Captured text calls from the latest generateBookingPdf invocation */
let mockCapturedTextCalls: string[] = [];

jest.mock('jspdf', () => {
  return {
    __esModule: true,
    jsPDF: function MockJsPDF() {
      return {
        setFontSize: () => {},
        setFont: () => {},
        text: (text: string) => {
          mockCapturedTextCalls.push(text);
        },
        save: () => {},
        lastAutoTable: { finalY: 100 },
      };
    },
  };
});

jest.mock('jspdf-autotable', () => ({
  __esModule: true,
  default: (doc: any) => {
    doc.lastAutoTable = { finalY: 100 };
  },
}));

// Import after mocks are set up
import {
  preparePdfData,
  generateBookingPdf,
  buildPdfFilename,
} from '../utils/pdfGenerator';

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

/** Generates a valid PdfBookingData object with optional fixed paymentStatus */
function pdfBookingDataArb(
  paymentStatusOverride?: fc.Arbitrary<PaymentStatus>
): fc.Arbitrary<PdfBookingData> {
  const psArb =
    paymentStatusOverride ??
    fc.constantFrom<PaymentStatus>('unpaid', 'partial', 'paid');

  return fc
    .tuple(
      nameArb,
      cartItemsArb,
      psArb,
      fc
        .double({ min: 0, max: 1000, noNaN: true, noDefaultInfinity: true })
        .map((v) => Math.round(v * 100) / 100)
    )
    .map(([clubName, items, ps, totalPaid]) => ({
      clubName,
      items,
      status: 'draft' as const,
      paymentStatus: ps,
      totalAmount: 0,
      totalPaid,
      submittedAt: null,
    }));
}

/** Generates a valid club_id string (alphanumeric with dashes) */
const clubIdArb = fc.stringMatching(/^[a-zA-Z0-9][a-zA-Z0-9\-]{0,29}$/);

// ---------- Helper ----------

function computeExpectedLineTotal(item: CartItem): number {
  if (item.product_type === 'airport_transfer') {
    const persons = Number(item.attributes.persons) || 1;
    return persons * item.unit_price;
  }
  return 1 * item.unit_price;
}

// ---------- Tests ----------

describe('PDF Generator - Property Tests', () => {
  /**
   * **Validates: Requirements 1.1, 1.4**
   *
   * Property 1: PDF data preparation produces correct grouped output
   * For any valid cart items, preparePdfData groups items by product_type,
   * each group's items sum to group total, all group totals sum to grand total.
   */
  it('preparePdfData groups items by product_type with correct totals', () => {
    fc.assert(
      fc.property(pdfBookingDataArb(), (data) => {
        const groups = preparePdfData(data);

        // All items must be accounted for in groups
        const totalItemsInGroups = groups.reduce(
          (sum, g) => sum + g.items.length,
          0
        );
        if (totalItemsInGroups !== data.items.length) return false;

        // Each group must only contain items of its product type
        for (const group of groups) {
          const expectedItems = data.items.filter(
            (i) => i.product_type === group.productType
          );
          if (group.items.length !== expectedItems.length) return false;
        }

        // Each group's items line totals must sum to group total
        for (const group of groups) {
          const itemsSum = group.items.reduce(
            (sum, li) => sum + li.lineTotal,
            0
          );
          if (Math.abs(itemsSum - group.groupTotal) > 0.001) return false;
        }

        // All group totals must sum to the grand total of all line items
        const grandTotal = groups.reduce((sum, g) => sum + g.groupTotal, 0);
        const expectedGrandTotal = data.items.reduce(
          (sum, item) => sum + computeExpectedLineTotal(item),
          0
        );
        if (Math.abs(grandTotal - expectedGrandTotal) > 0.001) return false;

        return true;
      }),
      { numRuns: 100 }
    );
  });

  /**
   * **Validates: Requirements 1.2**
   *
   * Property 2: PDF includes payment instructions conditionally
   * For payment_status "unpaid"/"partial" output includes payment instructions;
   * for "paid" it does not.
   */
  describe('Payment instructions conditional inclusion', () => {
    it('includes "Payment Instructions" for unpaid/partial payment status', () => {
      fc.assert(
        fc.property(
          pdfBookingDataArb(
            fc.constantFrom<PaymentStatus>('unpaid', 'partial')
          ),
          (data) => {
            mockCapturedTextCalls = [];
            generateBookingPdf(data);
            return mockCapturedTextCalls.some((t) =>
              t.includes('Payment Instructions')
            );
          }
        ),
        { numRuns: 100 }
      );
    });

    it('does NOT include "Payment Instructions" for paid payment status', () => {
      fc.assert(
        fc.property(
          pdfBookingDataArb(fc.constant<PaymentStatus>('paid')),
          (data) => {
            mockCapturedTextCalls = [];
            generateBookingPdf(data);
            return !mockCapturedTextCalls.some((t) =>
              t.includes('Payment Instructions')
            );
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  /**
   * **Validates: Requirements 1.5**
   *
   * Property 3: PDF filename matches expected pattern
   * For any club_id, buildPdfFilename returns `presmeet-booking-{clubId}.pdf`.
   */
  it('buildPdfFilename returns correct filename pattern for any clubId', () => {
    fc.assert(
      fc.property(clubIdArb, (clubId) => {
        const filename = buildPdfFilename(clubId);
        const expected = `presmeet-booking-${clubId}.pdf`;
        return filename === expected;
      }),
      { numRuns: 100 }
    );
  });
});
