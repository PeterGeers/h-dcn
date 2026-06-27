/**
 * BookingSummaryPdf — Download button + PDF generation for event bookings.
 *
 * Generates a PDF containing the full booking summary using jsPDF + jspdf-autotable.
 * Available at all order statuses (draft, submitted, locked).
 *
 * Content:
 * - Header: event name, row label
 * - Delegates: names and emails (primary + secondary)
 * - Table: persons → products → field values, variant, unit_price
 * - Validation: runs submission validation checks, indicates "valid" or lists issues
 * - Footer: total amount, payment status, order status
 * - Disclaimer: "Generated on {date-time}. Products and availability subject to change."
 * - Handles draft with no persons (metadata only + indication)
 *
 * Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
 */

import React, { useCallback } from 'react';
import { Button } from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Event, Order, Product } from '../types/eventBooking.types';
import { orderItemsToFormState } from '../utils/orderTransformer';
import { formatCurrency } from '../utils/priceCalculator';

// --- Props ---

export interface BookingSummaryPdfProps {
  order: Order;
  event: Event;
  products: Product[];
  /** Optional row label from registry_config (e.g. "club", "team") */
  rowLabel?: string;
}

// --- Validation Types ---

export interface PdfValidationIssue {
  personIndex: number;
  personName: string;
  productId?: string;
  productName?: string;
  field?: string;
  message: string;
}

/** Translation function type — compatible with react-i18next's t() */
type TranslateFn = (key: string, params?: Record<string, string>) => string;

// --- Helpers ---

/**
 * Sanitize a string for use in a filename:
 * - Lowercase
 * - Non-alphanumeric characters → hyphens
 * - Consecutive hyphens collapsed
 * - Leading/trailing hyphens removed
 * - Empty/absent → "unknown"
 */
export function sanitizeForFilename(value: string | null | undefined): string {
  if (!value || value.trim().length === 0) return 'unknown';
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '') || 'unknown';
}

/**
 * Build a sanitized filename for the PDF download.
 * Format: booking-{sanitized_registry_row_label}-{sanitized_event_name}.pdf
 */
export function buildFilename(registryRowLabel: string | null | undefined, eventName: string): string {
  const sanitizedLabel = sanitizeForFilename(registryRowLabel);
  const sanitizedName = sanitizeForFilename(eventName);
  return `booking-${sanitizedLabel}-${sanitizedName}.pdf`;
}

/**
 * Look up a product name by product_id from the products array.
 */
function getProductName(productId: string, products: Product[]): string {
  const product = products.find((p) => p.product_id === productId);
  return product?.naam ?? productId;
}

/**
 * Look up variant display string from variant_attributes or product variants array.
 * Formats variant_attributes as "Axis1: Value1, Axis2: Value2".
 * Returns empty string if no variant.
 */
function getVariantLabel(
  variantId: string | null,
  productId: string,
  products: Product[],
  variantAttributes?: Record<string, string>
): string {
  if (!variantId) return '';

  // Prefer variant_attributes stored directly on the order item
  if (variantAttributes && Object.keys(variantAttributes).length > 0) {
    return Object.entries(variantAttributes)
      .map(([axis, value]) => `${axis}: ${value}`)
      .join(', ');
  }

  // Fallback: look up in product's variants array
  const product = products.find((p) => p.product_id === productId);
  if (!product) return variantId;

  if (product.variants && product.variants.length > 0) {
    const variant = product.variants.find((v) => v.variant_id === variantId);
    if (variant && variant.variant_attributes) {
      return Object.entries(variant.variant_attributes)
        .map(([axis, value]) => `${axis}: ${value}`)
        .join(', ');
    }
  }

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

/**
 * Run validation checks against the order at PDF generation time.
 * Mirrors the same checks as order submission (Requirement 12.3).
 *
 * Checks:
 * - Person names non-empty
 * - item_fields_data.name populated
 * - Required order_item_fields filled
 * - Per-order quantity limits (max_per_order)
 * - Variant validity (variant_id exists in product's variants)
 *
 * Note: per-event capacity (max_per_event) is not checked client-side because
 * it requires fresh sold_count data from the backend. The PDF indicates this
 * cannot be verified client-side.
 */
export function runValidationChecks(
  order: Order,
  products: Product[],
  t: TranslateFn
): PdfValidationIssue[] {
  const issues: PdfValidationIssue[] = [];
  const formState = orderItemsToFormState(order.items);
  const productMap = new Map(products.map((p) => [p.product_id, p]));

  for (let pIdx = 0; pIdx < formState.persons.length; pIdx++) {
    const person = formState.persons[pIdx];
    const personName = person.name || t('pdf.validation_person_unnamed', { index: String(pIdx + 1) });

    // Check person name non-empty
    if (!person.name || person.name.trim().length === 0) {
      issues.push({
        personIndex: pIdx,
        personName,
        message: t('pdf.validation_name_empty'),
      });
    }

    // Check products
    for (const personProduct of person.products) {
      const productDef = productMap.get(personProduct.product_id);
      const productName = getProductName(personProduct.product_id, products);

      // Check required order_item_fields
      if (productDef) {
        for (const field of productDef.order_item_fields) {
          if (!field.required) continue;
          // Skip name — validated separately at person level above
          if (field.id === 'name') continue;

          // role is stored at person level by orderItemsToFormState, not in fields
          if (field.id === 'role') {
            const roleValue = person.role;
            const roleEmpty =
              roleValue === undefined ||
              roleValue === null ||
              (typeof roleValue === 'string' && roleValue.trim().length === 0);
            if (roleEmpty) {
              issues.push({
                personIndex: pIdx,
                personName,
                productId: personProduct.product_id,
                productName,
                field: field.label,
                message: t('pdf.validation_field_required', { field: field.label }),
              });
            }
            continue;
          }

          const value = personProduct.fields[field.id];
          const isEmpty =
            value === undefined ||
            value === null ||
            (typeof value === 'string' && value.trim().length === 0);

          if (isEmpty) {
            issues.push({
              personIndex: pIdx,
              personName,
              productId: personProduct.product_id,
              productName,
              field: field.label,
              message: t('pdf.validation_field_required', { field: field.label }),
            });
          }
        }

        // Check variant validity
        if (productDef.variant_schema && productDef.variant_schema.length > 0) {
          if (!personProduct.variant_id) {
            issues.push({
              personIndex: pIdx,
              personName,
              productId: personProduct.product_id,
              productName,
              message: t('pdf.validation_variant_missing'),
            });
          } else if (productDef.variants && productDef.variants.length > 0) {
            const validVariant = productDef.variants.some(
              (v) => v.variant_id === personProduct.variant_id
            );
            if (!validVariant) {
              issues.push({
                personIndex: pIdx,
                personName,
                productId: personProduct.product_id,
                productName,
                message: t('pdf.validation_variant_invalid'),
              });
            }
          }
        }
      }
    }
  }

  // Check per-order quantity limits (max_per_order)
  const productCounts = new Map<string, number>();
  for (const item of order.items) {
    const count = productCounts.get(item.product_id) || 0;
    productCounts.set(item.product_id, count + 1);
  }

  for (const [productId, count] of productCounts) {
    const productDef = productMap.get(productId);
    if (productDef?.purchase_rules?.max_per_order && count > productDef.purchase_rules.max_per_order) {
      issues.push({
        personIndex: -1,
        personName: '',
        productId,
        productName: getProductName(productId, products),
        message: t('pdf.validation_quantity_exceeded', {
          product: getProductName(productId, products),
          count: String(count),
          max: String(productDef.purchase_rules.max_per_order),
        }),
      });
    }
  }

  return issues;
}

// --- PDF Generation ---

/**
 * Generate and download the booking summary PDF.
 * Implements Requirements 12.1, 12.2, 12.3, 12.4, 12.5.
 */
export function generateBookingSummaryPdf(
  order: Order,
  event: Event,
  products: Product[],
  t: TranslateFn,
  rowLabel?: string
): void {
  const doc = new jsPDF();
  const formState = orderItemsToFormState(order.items);

  let yPos = 20;

  // --- Header: Event name ---
  doc.setFontSize(16);
  doc.text(event.name, 14, yPos);
  yPos += 8;

  // --- Row logo + label (registry_row_logo_url + registry_row_label) ---
  if (order.registry_row_logo_url) {
    try {
      doc.addImage(order.registry_row_logo_url, 'PNG', 14, yPos - 4, 12, 12);
      // Shift text to the right when logo is present
      doc.setFontSize(12);
      const displayRowLabel = rowLabel || t('pdf.row_label_default');
      doc.text(
        t('pdf.row_label', { rowLabel: displayRowLabel, name: order.registry_row_label || '' }),
        28,
        yPos + 4
      );
    } catch {
      // If image fails to load, render text only
      doc.setFontSize(12);
      const displayRowLabel = rowLabel || t('pdf.row_label_default');
      doc.text(
        t('pdf.row_label', { rowLabel: displayRowLabel, name: order.registry_row_label || '' }),
        14,
        yPos
      );
    }
    yPos += 12;
  } else {
    doc.setFontSize(12);
    const displayRowLabel = rowLabel || t('pdf.row_label_default');
    doc.text(
      t('pdf.row_label', { rowLabel: displayRowLabel, name: order.registry_row_label || '' }),
      14,
      yPos
    );
    yPos += 8;
  }

  // --- Delegates section (Requirement 12.2) ---
  doc.setFontSize(10);
  if (order.delegates || order.created_by) {
    const primaryEmail = order.delegates?.primary || order.user_email || order.created_by || '';
    const primaryLabel = t('pdf.delegate_primary', { email: primaryEmail });
    doc.text(primaryLabel, 14, yPos);
    yPos += 5;

    if (order.delegates?.secondary) {
      const secondaryLabel = t('pdf.delegate_secondary', { email: order.delegates.secondary });
      doc.text(secondaryLabel, 14, yPos);
      yPos += 5;
    }

    if (order.delegates?.pending_secondary_email) {
      const pendingLabel = t('pdf.delegate_pending', { email: order.delegates.pending_secondary_email });
      doc.text(pendingLabel, 14, yPos);
      yPos += 5;
    }
  }
  yPos += 3;

  // --- Order status and payment info (Requirement 12.2) ---
  doc.text(t('pdf.order_status', { status: order.status }), 14, yPos);
  yPos += 5;
  doc.text(t('pdf.payment_status', { status: order.payment_status || 'unpaid' }), 14, yPos);
  yPos += 5;
  doc.setFont(undefined as any, 'bold');
  doc.text(t('pdf.total', { amount: formatCurrency(order.total_amount || 0) }), 14, yPos);
  doc.setFont(undefined as any, 'normal');
  yPos += 8;

  // --- Persons table (Requirement 12.2) ---
  if (formState.persons.length > 0) {
    const tableHead = [[
      t('pdf.col_person'),
      t('pdf.col_product'),
      t('pdf.col_variant'),
      t('pdf.col_fields'),
      t('pdf.col_price'),
    ]];
    const tableBody: string[][] = [];

    for (const person of formState.persons) {
      if (person.products.length === 0) {
        tableBody.push([person.name || '—', '', '', '', '']);
      } else {
        for (let i = 0; i < person.products.length; i++) {
          const pp = person.products[i];
          const productName = getProductName(pp.product_id, products);
          const variantLabel = getVariantLabel(pp.variant_id, pp.product_id, products, pp.variant_attributes);
          const fieldValues = formatFieldValues(pp.fields);

          const matchingItem = order.items.find(
            (item) =>
              item.product_id === pp.product_id &&
              item.item_fields_data?.name === person.name
          );
          const price = matchingItem
            ? formatCurrency(matchingItem.unit_price)
            : '';

          if (i === 0) {
            tableBody.push([person.name || '—', productName, variantLabel, fieldValues, price]);
          } else {
            tableBody.push(['', productName, variantLabel, fieldValues, price]);
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
        0: { cellWidth: 35 },
        1: { cellWidth: 40 },
        2: { cellWidth: 30 },
        3: { cellWidth: 50 },
        4: { cellWidth: 25 },
      },
    });

    yPos = (doc as any).lastAutoTable.finalY + 10;
  } else {
    // Requirement 12.5: Draft with no persons — show metadata + indication
    doc.setFontSize(10);
    doc.text(t('pdf.no_persons_yet'), 14, yPos);
    yPos += 10;
  }

  // --- Validation section (Requirement 12.3) ---
  const validationIssues = runValidationChecks(order, products, t);

  doc.setFontSize(10);
  if (validationIssues.length === 0) {
    doc.setTextColor(0, 128, 0);
    doc.text(t('pdf.validation_valid'), 14, yPos);
    doc.setTextColor(0, 0, 0);
    yPos += 7;
  } else {
    doc.setTextColor(200, 0, 0);
    doc.text(t('pdf.validation_issues_title', { count: String(validationIssues.length) }), 14, yPos);
    doc.setTextColor(0, 0, 0);
    yPos += 6;

    doc.setFontSize(8);
    for (const issue of validationIssues) {
      // Page break if needed
      if (yPos > 270) {
        doc.addPage();
        yPos = 20;
      }
      const prefix = issue.personName
        ? `${issue.personName}${issue.productName ? ' / ' + issue.productName : ''}: `
        : '';
      doc.text(`• ${prefix}${issue.message}`, 16, yPos);
      yPos += 4;
    }
    yPos += 4;
  }

  // --- Disclaimer (Requirement 12.4) ---
  doc.setFontSize(8);
  doc.setTextColor(100, 100, 100);
  const generatedDateTime = new Date().toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
  const disclaimer = t('pdf.disclaimer', { datetime: generatedDateTime });
  doc.text(disclaimer, 14, yPos);
  doc.setTextColor(0, 0, 0);

  // --- Download ---
  const filename = buildFilename(order.registry_row_label, event.name);
  doc.save(filename);
}

// --- Component ---

const BookingSummaryPdf: React.FC<BookingSummaryPdfProps> = ({
  order,
  event,
  products,
  rowLabel,
}) => {
  const { t } = useTranslation('eventBooking');

  const handleDownload = useCallback(() => {
    generateBookingSummaryPdf(order, event, products, t as unknown as TranslateFn, rowLabel);
  }, [order, event, products, t, rowLabel]);

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
