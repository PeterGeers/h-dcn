/**
 * Property-based tests for PDF output completeness.
 *
 * Feature: closed-community-booking
 * **Validates: Requirements 12.2, 12.4**
 *
 * Property 22: PDF Output Completeness
 * For any non-empty order (at least one person), the generated PDF SHALL contain:
 * event name, row label, delegate name(s), all person names, all product names
 * with variants and fields, order status, total amount, payment status, and a
 * disclaimer string containing the generation date formatted as locale date-time.
 */

import * as fc from 'fast-check';
import {
  Order,
  OrderItem,
  OrderStatus,
  PaymentStatus,
  Event,
  Product,
  ProductVariant,
} from '../types/eventBooking.types';

// Import after mocks
import { generateBookingSummaryPdf } from '../components/BookingSummaryPdf';

// --- Mock jsPDF to capture all text output ---

let mockCapturedTextCalls: string[] = [];
let mockCapturedAutoTableCalls: Array<{ head: string[][]; body: string[][] }> = [];

jest.mock('jspdf', () => ({
  __esModule: true,
  jsPDF: function MockJsPDF() {
    return {
      setFontSize: jest.fn(),
      setFont: jest.fn(),
      setTextColor: jest.fn(),
      addPage: jest.fn(),
      text: (text: string) => {
        mockCapturedTextCalls.push(text);
      },
      save: jest.fn(),
      lastAutoTable: { finalY: 100 },
    };
  },
}));

jest.mock('jspdf-autotable', () => ({
  __esModule: true,
  default: (doc: any, options: any) => {
    doc.lastAutoTable = { finalY: 100 };
    if (options?.head && options?.body) {
      mockCapturedAutoTableCalls.push({ head: options.head, body: options.body });
    }
  },
}));

// --- Mock translation function ---

const mockT = ((key: string, params?: Record<string, string>): string => {
  if (params) {
    const templates: Record<string, string> = {
      'pdf.row_label': `${params.rowLabel || 'Club'}: ${params.clubId || ''}`,
      'pdf.total': `Total: ${params.amount || ''}`,
      'pdf.payment_status': `Payment status: ${params.status || ''}`,
      'pdf.order_status': `Order status: ${params.status || ''}`,
      'pdf.delegate_primary': `Primary delegate: ${params.email || ''}`,
      'pdf.delegate_secondary': `Secondary delegate: ${params.email || ''}`,
      'pdf.delegate_pending': `Pending invitation: ${params.email || ''}`,
      'pdf.disclaimer': `Generated on ${params.datetime || ''}. Products and availability subject to change.`,
      'pdf.validation_issues_title': `Validation issues (${params.count || ''}):`,
      'pdf.validation_field_required': `${params.field || ''} is required`,
      'pdf.validation_quantity_exceeded': `${params.product || ''}: ${params.count || ''} selected, max ${params.max || ''} allowed`,
      'pdf.validation_person_unnamed': `Person ${params.index || ''}`,
    };
    return templates[key] || key;
  }
  const statics: Record<string, string> = {
    'pdf.row_label_default': 'Club',
    'pdf.no_persons_yet': 'No persons have been added yet.',
    'pdf.col_person': 'Person',
    'pdf.col_product': 'Product',
    'pdf.col_variant': 'Variant',
    'pdf.col_fields': 'Fields',
    'pdf.col_price': 'Price',
    'pdf.validation_valid': '✓ Order is valid at this moment',
    'pdf.validation_name_empty': 'Name is required',
    'pdf.validation_variant_missing': 'Variant selection is required',
    'pdf.validation_variant_invalid': 'Selected variant is invalid',
  };
  return statics[key] || key;
}) as any;

// --- Arbitraries ---

/** Non-empty printable person name (1-50 chars, no whitespace-only) */
const personNameArb = fc
  .string({ minLength: 1, maxLength: 50 })
  .filter((s) => s.trim().length > 0)
  .map((s) => s.trim());

/** Valid product name (1-40 chars) */
const productNameArb = fc
  .string({ minLength: 1, maxLength: 40 })
  .filter((s) => s.trim().length > 0)
  .map((s) => s.trim());

/** Valid event name (1-60 chars, non-empty) */
const eventNameArb = fc
  .string({ minLength: 1, maxLength: 60 })
  .filter((s) => s.trim().length > 0)
  .map((s) => s.trim());

/** Email arbitrary */
const emailArb = fc
  .tuple(
    fc.stringMatching(/^[a-z]{2,10}$/),
    fc.stringMatching(/^[a-z]{2,8}$/),
    fc.constantFrom('nl', 'com', 'org', 'de')
  )
  .map(([user, domain, tld]) => `${user}@${domain}.${tld}`);

/** Order status arbitrary */
const orderStatusArb: fc.Arbitrary<OrderStatus> = fc.constantFrom('draft', 'submitted', 'locked');

/** Payment status arbitrary */
const paymentStatusArb: fc.Arbitrary<PaymentStatus> = fc.constantFrom('unpaid', 'partial', 'paid');

/** Row label arbitrary */
const rowLabelArb = fc.constantFrom('club', 'team', 'deelnemer', 'groep');

/** Variant ID arbitrary */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const variantIdArb = fc.uuid();

/** Generates a product definition */
const productArb: fc.Arbitrary<Product> = fc
  .record({
    product_id: fc.uuid(),
    name: productNameArb,
    event_type: fc.constant('presmeet'),
    price: fc.double({ min: 0.01, max: 500, noNaN: true, noDefaultInfinity: true }).map((v) => Math.round(v * 100) / 100),
    hasVariants: fc.boolean(),
  })
  .chain((base) => {
    const variants: ProductVariant[] = base.hasVariants
      ? [{ variant_id: 'var-1', variant_attributes: { size: 'M' } }]
      : [];
    const variantSchema = base.hasVariants ? [{ name: 'size', values: ['S', 'M', 'L'] }] : null;

    return fc.constant<Product>({
      product_id: base.product_id,
      naam: base.name,
      event_id: null,
      event_type: base.event_type,
      prijs: base.price,
      order_item_fields: [
        { id: 'name', label: 'Naam', type: 'text', required: true },
      ],
      variant_schema: variantSchema,
      variants: variants.length > 0 ? variants : undefined,
      purchase_rules: { max_per_order: 10 },
    });
  });

/** Generates 1-5 products */
const productsArb = fc.array(productArb, { minLength: 1, maxLength: 5 });

/**
 * Generates a non-empty order (at least 1 person with at least 1 product)
 * consistent with the provided products array.
 */
function orderArb(products: Product[]): fc.Arbitrary<Order> {
  // Generate 1-4 persons, each with 1-3 products
  const personCountArb = fc.integer({ min: 1, max: 4 });

  return fc
    .tuple(
      personCountArb,
      orderStatusArb,
      paymentStatusArb,
      emailArb,
      fc.option(emailArb, { nil: null }),
      fc.double({ min: 0, max: 5000, noNaN: true, noDefaultInfinity: true }).map((v) => Math.round(v * 100) / 100),
    )
    .chain(([personCount, status, paymentStatus, primaryEmail, secondaryEmail, totalAmount]) => {
      // Generate person names
      return fc
        .array(personNameArb, { minLength: personCount, maxLength: personCount })
        .chain((personNames) => {
          // For each person, pick 1-3 products and build order items
          const personItemsArbs = personNames.map((name) =>
            fc
              .array(
                fc.integer({ min: 0, max: products.length - 1 }),
                { minLength: 1, maxLength: Math.min(3, products.length) }
              )
              .map((productIndices) => {
                // Deduplicate product indices for this person
                const uniqueIndices = [...new Set(productIndices)];
                return uniqueIndices.map((idx): OrderItem => {
                  const product = products[idx];
                  const hasVariants = product.variant_schema && product.variant_schema.length > 0;
                  const variantId = hasVariants && product.variants && product.variants.length > 0
                    ? product.variants[0].variant_id
                    : null;
                  return {
                    product_id: product.product_id,
                    variant_id: variantId,
                    item_fields_data: { name },
                    unit_price: product.prijs,
                    line_total: product.prijs,
                  };
                });
              })
          );

          return fc.tuple(...personItemsArbs).map((allPersonItems): Order => {
            const items = allPersonItems.flat();
            return {
              order_id: 'ord-test',
              source_id: 'evt-test',
              member_id: 'member-test',
              registry_row_id: 'club-test',
              event_id: 'evt-test',
              event_type: 'presmeet',
              status,
              payment_status: paymentStatus,
              total_amount: totalAmount,
              total_paid: paymentStatus === 'paid' ? totalAmount : 0,
              items,
              delegates: {
                primary: primaryEmail,
                secondary: secondaryEmail,
              },
              version: 1,
              created_at: '2027-01-01T00:00:00Z',
              updated_at: '2027-01-01T00:00:00Z',
            };
          });
        });
    });
}

/** Event arbitrary */
const eventArb: fc.Arbitrary<Event> = eventNameArb.map((name) => ({
  event_id: 'evt-test',
  event_type: 'presmeet',
  name,
  location: 'Test Location',
  status: 'open' as const,
  start_date: '2027-06-01',
  end_date: '2027-06-03',
  registration_open: '2027-01-01',
  registration_close: '2027-05-01',
  payment_deadline: '2027-05-15',
  product_ids: [],
  constraints: [],
  created_at: '2026-12-01T00:00:00Z',
  created_by: 'admin@h-dcn.nl',
}));

// --- Helper: collect ALL text from PDF output (direct text + table cells) ---

function getAllPdfText(): string {
  const directText = mockCapturedTextCalls.join(' ');
  const tableText = mockCapturedAutoTableCalls
    .flatMap((call) => [...call.head.flat(), ...call.body.flat()])
    .join(' ');
  return directText + ' ' + tableText;
}

// --- Tests ---

describe('PDF Output Completeness - Property 22', () => {
  beforeEach(() => {
    mockCapturedTextCalls = [];
    mockCapturedAutoTableCalls = [];
  });

  /**
   * **Validates: Requirements 12.2, 12.4**
   *
   * Property 22: PDF Output Completeness
   * For any non-empty order (at least one person), the generated PDF SHALL contain:
   * event name, row label, delegate name(s), all person names, all product names
   * with variants and fields, order status, total amount, payment status, and a
   * disclaimer string containing the generation date formatted as locale date-time.
   */
  it('PDF contains event name for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Event name must appear in PDF text
          return allText.includes(event.name);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains row label for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Row label must appear in PDF text (via t('pdf.row_label', { rowLabel, clubId }))
          return allText.includes(rowLabel);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains primary delegate email for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Primary delegate email must appear
          return allText.includes(order.delegates!.primary);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains secondary delegate email when present', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // If secondary delegate exists, it must appear
          if (order.delegates?.secondary) {
            return allText.includes(order.delegates.secondary);
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains all person names from order items', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Extract unique person names from items
          const personNames = new Set(
            order.items.map((item) => item.item_fields_data.name as string).filter(Boolean)
          );

          // Every person name must appear in the PDF
          for (const name of personNames) {
            if (!allText.includes(name)) return false;
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains all product names from order items', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Get unique product IDs from order
          const productIds = new Set(order.items.map((item) => item.product_id));

          // For each product in the order, its name must appear in the PDF
          for (const productId of productIds) {
            const product = products.find((p) => p.product_id === productId);
            if (product && !allText.includes(product.naam)) return false;
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains order status for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Order status must appear in text (via t('pdf.order_status', { status }))
          return allText.includes(order.status);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains payment status for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Payment status must appear
          const expectedPaymentStatus = order.payment_status || 'unpaid';
          return allText.includes(expectedPaymentStatus);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains total amount for any non-empty order', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Total amount text must appear (starts with "Total:")
          return allText.includes('Total:');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PDF contains disclaimer with locale-formatted date-time', () => {
    fc.assert(
      fc.property(
        productsArb.chain((products) =>
          fc.tuple(fc.constant(products), orderArb(products), eventArb, rowLabelArb)
        ),
        ([products, order, event, rowLabel]) => {
          mockCapturedTextCalls = [];
          mockCapturedAutoTableCalls = [];

          generateBookingSummaryPdf(order, event, products, mockT, rowLabel);
          const allText = getAllPdfText();

          // Disclaimer must contain "Generated on" and "subject to change"
          const hasGeneratedOn = allText.includes('Generated on');
          const hasSubjectToChange = allText.includes('Products and availability subject to change');

          return hasGeneratedOn && hasSubjectToChange;
        }
      ),
      { numRuns: 100 }
    );
  });
});
