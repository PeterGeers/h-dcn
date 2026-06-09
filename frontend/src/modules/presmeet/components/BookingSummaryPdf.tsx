/**
 * BookingSummaryPdf — Download button + PDF generation for PresMeet bookings.
 *
 * Generates a PDF containing the full booking summary using jsPDF + jspdf-autotable.
 * Available at all order statuses (draft, submitted, locked).
 *
 * Content:
 * - Header: event name, club name
 * - Table: persons → products → field values, variant, unit_price
 * - Footer: total amount, payment status, order status, generated date
 *
 * Validates: Requirements 11.10, 11.11
 */

import React, { useCallback } from 'react';
import { Button } from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { TFunction } from 'i18next';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Event, Order, Product } from '../types/presmeet.types';
import { orderItemsToFormState } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';

// --- Props ---

export interface BookingSummaryPdfProps {
  order: Order;
  event: Event;
  products: Product[];
}

// --- Helpers ---

/**
 * Build a sanitized filename for the PDF download.
 * Format: presmeet-booking-{club_id}-{event_name}.pdf
 */
export function buildFilename(clubId: string, eventName: string): string {
  const sanitized = eventName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `presmeet-booking-${clubId}-${sanitized}.pdf`;
}

/**
 * Look up a product name by product_id from the products array.
 */
function getProductName(productId: string, products: Product[]): string {
  const product = products.find((p) => p.product_id === productId);
  return product?.name ?? productId;
}

/**
 * Look up variant display string from product variant_schema and variant_id.
 * Returns empty string if no variant.
 */
function getVariantLabel(
  variantId: string | null,
  productId: string,
  products: Product[]
): string {
  if (!variantId) return '';
  const product = products.find((p) => p.product_id === productId);
  if (!product?.variant_schema) return variantId;
  // variant_id may encode the variant values — display as-is if not parseable
  return variantId;
}

/**
 * Format field values from item_fields_data into a readable string,
 * excluding name and role (already shown at person level).
 */
function formatFieldValues(fields: Record<string, any>): string {
  const excluded = new Set(['name', 'role']);
  const entries = Object.entries(fields)
    .filter(([key]) => !excluded.has(key))
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => `${key}: ${value}`);
  return entries.join(', ');
}

// --- PDF Generation ---

/**
 * Generate and download the booking summary PDF.
 */
export function generateBookingSummaryPdf(
  order: Order,
  event: Event,
  products: Product[],
  t: TFunction
): void {
  const doc = new jsPDF();
  const formState = orderItemsToFormState(order.items);

  let yPos = 20;

  // --- Header: Event name ---
  doc.setFontSize(16);
  doc.text(event.name, 14, yPos);
  yPos += 8;

  // --- Sub-header: Club ID ---
  doc.setFontSize(12);
  doc.text(t('pdf.club', { clubId: order.club_id }), 14, yPos);
  yPos += 6;

  // --- Event details ---
  doc.setFontSize(10);
  doc.text(t('pdf.location', { location: event.location }), 14, yPos);
  yPos += 5;
  doc.text(t('pdf.event_dates', { start: event.start_date, end: event.end_date }), 14, yPos);
  yPos += 10;

  // --- Persons table ---
  if (formState.persons.length > 0) {
    const tableHead = [[
      t('pdf.col_person'),
      t('pdf.col_role'),
      t('pdf.col_product'),
      t('pdf.col_variant'),
      t('pdf.col_fields'),
      t('pdf.col_price'),
    ]];
    const tableBody: string[][] = [];

    for (const person of formState.persons) {
      if (person.products.length === 0) {
        // Person with no products — show name/role only
        tableBody.push([person.name || '—', person.role || '—', '', '', '', '']);
      } else {
        for (let i = 0; i < person.products.length; i++) {
          const pp = person.products[i];
          const productName = getProductName(pp.product_id, products);
          const variantLabel = getVariantLabel(pp.variant_id, pp.product_id, products);
          const fieldValues = formatFieldValues(pp.fields);

          // Look up unit price from the matching order item
          const matchingItem = order.items.find(
            (item) =>
              item.product_id === pp.product_id &&
              item.item_fields_data?.name === person.name
          );
          const price = matchingItem
            ? formatCurrency(matchingItem.unit_price)
            : '';

          // Show person name/role only on first row for this person
          if (i === 0) {
            tableBody.push([
              person.name || '—',
              person.role || '—',
              productName,
              variantLabel,
              fieldValues,
              price,
            ]);
          } else {
            tableBody.push(['', '', productName, variantLabel, fieldValues, price]);
          }
        }
      }
    }

    autoTable(doc, {
      startY: yPos,
      head: tableHead,
      body: tableBody,
      theme: 'striped',
      headStyles: { fillColor: [66, 66, 66] },
      margin: { left: 14 },
      styles: { fontSize: 8, cellPadding: 2 },
      columnStyles: {
        0: { cellWidth: 30 },
        1: { cellWidth: 22 },
        2: { cellWidth: 35 },
        3: { cellWidth: 25 },
        4: { cellWidth: 45 },
        5: { cellWidth: 22 },
      },
    });

    yPos = (doc as any).lastAutoTable.finalY + 10;
  } else {
    doc.setFontSize(10);
    doc.text(t('pdf.no_items'), 14, yPos);
    yPos += 10;
  }

  // --- Footer: totals and status ---
  doc.setFontSize(11);
  doc.setFont(undefined as any, 'bold');
  doc.text(t('pdf.total', { amount: formatCurrency(order.total_amount) }), 14, yPos);
  yPos += 7;
  doc.setFont(undefined as any, 'normal');
  doc.setFontSize(10);
  doc.text(t('pdf.payment_status', { status: order.payment_status }), 14, yPos);
  yPos += 5;
  doc.text(t('pdf.order_status', { status: order.status }), 14, yPos);
  yPos += 5;
  doc.text(t('pdf.generated', { date: new Date().toLocaleString('nl-NL') }), 14, yPos);

  // --- Download ---
  const filename = buildFilename(order.club_id, event.name);
  doc.save(filename);
}

// --- Component ---

const BookingSummaryPdf: React.FC<BookingSummaryPdfProps> = ({
  order,
  event,
  products,
}) => {
  const { t } = useTranslation('presmeet');

  const handleDownload = useCallback(() => {
    generateBookingSummaryPdf(order, event, products, t);
  }, [order, event, products, t]);

  return (
    <Button
      leftIcon={<DownloadIcon />}
      colorScheme="orange"
      variant="outline"
      size="sm"
      onClick={handleDownload}
    >
      {t('pdf.download_button')}
    </Button>
  );
};

export default BookingSummaryPdf;
