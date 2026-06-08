/**
 * PDF Generator utility for PresMeet booking overview.
 *
 * Generates a downloadable PDF with grouped booking items, club name header,
 * grand total, and conditional payment instructions.
 *
 * Uses jsPDF + jspdf-autotable for client-side PDF rendering.
 */

import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  CartItem,
  OrderStatus,
  PaymentStatus,
  ProductType,
} from '../types/presmeet';

// --- Interfaces ---

export interface PdfBookingData {
  clubName: string;
  items: CartItem[];
  status: OrderStatus;
  paymentStatus: PaymentStatus;
  totalAmount: number;
  totalPaid: number;
  submittedAt: string | null;
}

export interface PdfLineItem {
  label: string;
  unitPrice: number;
  quantity: number;
  lineTotal: number;
}

export interface PdfGroupData {
  groupHeading: string;
  productType: ProductType;
  items: PdfLineItem[];
  groupTotal: number;
}

// --- Constants ---

const PRODUCT_TYPE_HEADINGS: Record<ProductType, string> = {
  meeting_ticket: 'Meeting Tickets',
  party_ticket: 'Party Tickets',
  tshirt: 'T-Shirts',
  airport_transfer: 'Airport Transfers',
};

// --- Helpers ---

function formatEur(amount: number): string {
  return `€${amount.toFixed(2)}`;
}

function getItemLabel(item: CartItem): string {
  const attrs = item.attributes;
  switch (item.product_type) {
    case 'meeting_ticket':
      return attrs.name ?? '—';
    case 'party_ticket':
      return attrs.name ?? '—';
    case 'tshirt':
      return `${attrs.name ?? '—'} (${attrs.size ?? '?'})`;
    case 'airport_transfer': {
      const direction = attrs.direction ?? '?';
      const airport = attrs.airport ?? '?';
      const persons = Number(attrs.persons) || 1;
      return persons > 1
        ? `${direction} – ${airport} (${persons} persons)`
        : `${direction} – ${airport}`;
    }
    default:
      return '—';
  }
}

function computeLineTotal(item: CartItem): number {
  if (item.product_type === 'airport_transfer') {
    const persons = Number(item.attributes.persons) || 1;
    return persons * item.unit_price;
  }
  return 1 * item.unit_price;
}

function computeQuantity(item: CartItem): number {
  if (item.product_type === 'airport_transfer') {
    return Number(item.attributes.persons) || 1;
  }
  return 1;
}

// --- Exported Functions ---

/**
 * Groups cart items by product type and computes line totals.
 *
 * For airport_transfer items: lineTotal = persons × unit_price
 * For all other items: lineTotal = 1 × unit_price
 */
export function preparePdfData(data: PdfBookingData): PdfGroupData[] {
  const groupMap = new Map<ProductType, CartItem[]>();

  for (const item of data.items) {
    const existing = groupMap.get(item.product_type) ?? [];
    existing.push(item);
    groupMap.set(item.product_type, existing);
  }

  const groups: PdfGroupData[] = [];

  for (const [productType, groupItems] of groupMap.entries()) {
    const pdfLineItems: PdfLineItem[] = groupItems.map((item) => ({
      label: getItemLabel(item),
      unitPrice: item.unit_price,
      quantity: computeQuantity(item),
      lineTotal: computeLineTotal(item),
    }));

    const groupTotal = pdfLineItems.reduce((sum, li) => sum + li.lineTotal, 0);

    groups.push({
      groupHeading: PRODUCT_TYPE_HEADINGS[productType],
      productType,
      items: pdfLineItems,
      groupTotal,
    });
  }

  return groups;
}

/**
 * Generates a PDF document with booking overview and triggers browser download.
 *
 * Includes:
 * - Club name header
 * - Grouped items with quantities, unit prices, and line totals
 * - Grand total
 * - Payment instructions (when payment_status is "unpaid" or "partial")
 */
export function generateBookingPdf(data: PdfBookingData): void {
  const doc = new jsPDF();
  const groups = preparePdfData(data);
  const grandTotal = groups.reduce((sum, g) => sum + g.groupTotal, 0);
  const remainingBalance = Math.max(0, grandTotal - data.totalPaid);

  let yPos = 20;

  // Header: Club name
  doc.setFontSize(18);
  doc.text(data.clubName, 14, yPos);
  yPos += 10;

  // Subtitle
  doc.setFontSize(12);
  doc.text("Presidents' Meeting - Booking Overview", 14, yPos);
  yPos += 8;

  // Submission date if applicable
  if (data.submittedAt && (data.status === 'submitted' || data.status === 'locked')) {
    doc.setFontSize(10);
    doc.text(`Submitted: ${data.submittedAt}`, 14, yPos);
    yPos += 8;
  }

  // Status
  doc.setFontSize(10);
  doc.text(`Status: ${data.status}`, 14, yPos);
  yPos += 10;

  // Render each group as a table
  for (const group of groups) {
    doc.setFontSize(12);
    doc.text(group.groupHeading, 14, yPos);
    yPos += 2;

    const tableBody = group.items.map((item) => [
      item.label,
      String(item.quantity),
      formatEur(item.unitPrice),
      formatEur(item.lineTotal),
    ]);

    // Add group subtotal row
    tableBody.push(['', '', 'Subtotal:', formatEur(group.groupTotal)]);

    autoTable(doc, {
      startY: yPos,
      head: [['Item', 'Qty', 'Unit Price', 'Total']],
      body: tableBody,
      theme: 'striped',
      headStyles: { fillColor: [66, 66, 66] },
      margin: { left: 14 },
      styles: { fontSize: 9 },
    });

    yPos = (doc as any).lastAutoTable.finalY + 10;
  }

  // Grand total section
  doc.setFontSize(12);
  doc.setFont(undefined as any, 'bold');
  doc.text(`Grand Total: ${formatEur(grandTotal)}`, 14, yPos);
  yPos += 7;
  doc.text(`Total Paid: ${formatEur(data.totalPaid)}`, 14, yPos);
  yPos += 7;
  doc.text(`Remaining Balance: ${formatEur(remainingBalance)}`, 14, yPos);
  yPos += 12;
  doc.setFont(undefined as any, 'normal');

  // Payment instructions (conditional)
  if (data.paymentStatus === 'unpaid' || data.paymentStatus === 'partial') {
    doc.setFontSize(11);
    doc.setFont(undefined as any, 'bold');
    doc.text('Payment Instructions', 14, yPos);
    yPos += 7;
    doc.setFont(undefined as any, 'normal');
    doc.setFontSize(10);

    const instructions = [
      `Outstanding amount: ${formatEur(remainingBalance)}`,
      '',
      'Please transfer the outstanding amount to:',
      'Account: NL00 INGB 0000 0000 00',
      'Name: FH-DCE',
      `Reference: PM-${data.clubName}`,
      '',
      'Payment must be received before the event start date.',
    ];

    for (const line of instructions) {
      doc.text(line, 14, yPos);
      yPos += 5;
    }
  }

  // Trigger download
  const filename = buildPdfFilename(data.clubName);
  doc.save(filename);
}

/**
 * Builds a PDF filename from the club ID.
 *
 * @returns `presmeet-booking-{clubId}.pdf`
 */
export function buildPdfFilename(clubId: string): string {
  return `presmeet-booking-${clubId}.pdf`;
}
