/**
 * Invoice PDF (Factuur) generation utility for H-DCN Webshop.
 *
 * Generates a formal Dutch invoice PDF distinct from the order confirmation.
 * Only available when an order has been paid (invoice_number is present).
 *
 * Uses jsPDF + jspdf-autotable for client-side PDF rendering.
 */

import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// --- Interfaces ---

export interface InvoiceOrderItem {
  name: string;
  variant_attributes?: Record<string, string>;
  quantity: number;
  unit_price: number;
}

export interface InvoiceCustomerInfo {
  name: string;
  email?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  phone?: string;
}

export interface InvoiceOrder {
  order_id: string;
  order_number?: string;
  invoice_number: string;
  items: InvoiceOrderItem[];
  customer_info: InvoiceCustomerInfo;
  total_amount: number;
  paid_at?: string;
  created_at?: string;
}

// --- Constants ---

const H_DCN_ORG = {
  name: 'Harley-Davidson Club Nederland',
  shortName: 'H-DCN',
  btwNummer: 'NL818444285B01',
  kvkNummer: '40346415',
  address: 'Postbus 1903',
  postcode: '5602 BX',
  city: 'Eindhoven',
  country: 'Nederland',
  website: 'www.h-dcn.nl',
};

const VAT_RATE = 0.21;
const PAGE_WIDTH = 210;
const PAGE_HEIGHT = 297;
const MARGIN = 15;

// --- Helpers ---

function formatCurrency(amount: number): string {
  return `€ ${amount.toFixed(2)}`;
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('nl-NL', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function getItemDescription(item: InvoiceOrderItem): string {
  if (!item.variant_attributes || Object.keys(item.variant_attributes).length === 0) {
    return item.name;
  }
  const variants = Object.entries(item.variant_attributes)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ');
  return `${item.name} (${variants})`;
}

function calculateSubtotal(items: InvoiceOrderItem[]): number {
  return items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);
}

function calculateVatFromTotal(totalInclVat: number): { subtotalExVat: number; vatAmount: number } {
  const subtotalExVat = totalInclVat / (1 + VAT_RATE);
  const vatAmount = totalInclVat - subtotalExVat;
  return { subtotalExVat, vatAmount };
}

// --- Validation ---

/**
 * Returns true if the order has an invoice_number and is eligible for invoice generation.
 * Invoice PDFs are only available for paid orders.
 */
export function canGenerateInvoice(order: Partial<InvoiceOrder>): boolean {
  return !!order.invoice_number && order.invoice_number.trim().length > 0;
}

// --- PDF Generation ---

/**
 * Generates and downloads an invoice PDF (factuur) for a paid order.
 *
 * The invoice is distinct from the order confirmation:
 * - Uses invoice_number (F-YYYY-NNNN) instead of order_number
 * - Contains H-DCN BTW-nummer and KvK details
 * - Shows itemized amounts with VAT breakdown
 * - Only available after payment confirmation
 *
 * @param order - The order with invoice_number, items, and customer info
 * @returns true if generation succeeded, false otherwise
 */
export function generateInvoicePdf(order: InvoiceOrder): boolean {
  if (!canGenerateInvoice(order)) {
    console.error('Cannot generate invoice: invoice_number is missing');
    return false;
  }

  try {
    const doc = new jsPDF('p', 'mm', 'a4');
    let yPos = MARGIN;

    // --- Header ---
    yPos = renderHeader(doc, order, yPos);

    // --- Organization & Customer Info ---
    yPos = renderPartyDetails(doc, order, yPos);

    // --- Invoice Meta ---
    yPos = renderInvoiceMeta(doc, order, yPos);

    // --- Items Table ---
    yPos = renderItemsTable(doc, order.items, yPos);

    // --- Totals ---
    yPos = renderTotals(doc, order, yPos);

    // --- Footer ---
    renderFooter(doc, order);

    // Trigger download
    const filename = `factuur-${order.invoice_number}.pdf`;
    doc.save(filename);

    return true;
  } catch (error) {
    console.error('Invoice PDF generation failed:', error);
    return false;
  }
}

// --- Render Sections ---

function renderHeader(doc: jsPDF, order: InvoiceOrder, yPos: number): number {
  // Title
  doc.setFontSize(22);
  doc.setTextColor(0, 0, 0);
  doc.setFont(undefined as any, 'bold');
  doc.text('FACTUUR', MARGIN, yPos + 10);

  // Invoice number aligned right
  doc.setFontSize(12);
  doc.setFont(undefined as any, 'normal');
  doc.text(order.invoice_number, PAGE_WIDTH - MARGIN, yPos + 10, { align: 'right' });

  return yPos + 20;
}

function renderPartyDetails(doc: jsPDF, order: InvoiceOrder, yPos: number): number {
  const colLeft = MARGIN;
  const colRight = PAGE_WIDTH / 2 + 10;

  // Organization details (left column)
  doc.setFontSize(11);
  doc.setFont(undefined as any, 'bold');
  doc.text(H_DCN_ORG.name, colLeft, yPos);
  yPos += 6;

  doc.setFont(undefined as any, 'normal');
  doc.setFontSize(9);
  doc.text(H_DCN_ORG.address, colLeft, yPos);
  yPos += 5;
  doc.text(`${H_DCN_ORG.postcode} ${H_DCN_ORG.city}`, colLeft, yPos);
  yPos += 5;
  doc.text(H_DCN_ORG.country, colLeft, yPos);
  yPos += 5;
  doc.text(`BTW-nr: ${H_DCN_ORG.btwNummer}`, colLeft, yPos);
  yPos += 5;
  doc.text(`KvK-nr: ${H_DCN_ORG.kvkNummer}`, colLeft, yPos);

  // Customer details (right column)
  let rightY = yPos - 20; // Align with org start
  doc.setFontSize(9);
  doc.setFont(undefined as any, 'bold');
  doc.text('Klant:', colRight, rightY);
  rightY += 6;

  doc.setFont(undefined as any, 'normal');
  const customer = order.customer_info;
  doc.text(customer.name, colRight, rightY);
  rightY += 5;

  if (customer.straat) {
    doc.text(customer.straat, colRight, rightY);
    rightY += 5;
  }
  if (customer.postcode || customer.woonplaats) {
    doc.text(
      `${customer.postcode || ''} ${customer.woonplaats || ''}`.trim(),
      colRight,
      rightY
    );
    rightY += 5;
  }
  if (customer.email) {
    doc.text(customer.email, colRight, rightY);
    rightY += 5;
  }
  if (customer.phone) {
    doc.text(customer.phone, colRight, rightY);
  }

  return yPos + 15;
}

function renderInvoiceMeta(doc: jsPDF, order: InvoiceOrder, yPos: number): number {
  // Separator line
  doc.setDrawColor(200, 200, 200);
  doc.line(MARGIN, yPos, PAGE_WIDTH - MARGIN, yPos);
  yPos += 8;

  doc.setFontSize(9);
  doc.setTextColor(60, 60, 60);

  const metaLines: [string, string][] = [
    ['Factuurnummer:', order.invoice_number],
    ['Factuurdatum:', formatDate(order.paid_at || order.created_at)],
  ];

  if (order.order_number) {
    metaLines.push(['Ordernummer:', order.order_number]);
  }

  for (const [label, value] of metaLines) {
    doc.setFont(undefined as any, 'bold');
    doc.text(label, MARGIN, yPos);
    doc.setFont(undefined as any, 'normal');
    doc.text(value, MARGIN + 35, yPos);
    yPos += 5;
  }

  doc.setTextColor(0, 0, 0);
  yPos += 5;

  return yPos;
}

function renderItemsTable(doc: jsPDF, items: InvoiceOrderItem[], yPos: number): number {
  const tableBody = items.map((item) => {
    const lineTotal = item.quantity * item.unit_price;
    return [
      getItemDescription(item),
      String(item.quantity),
      formatCurrency(item.unit_price),
      formatCurrency(lineTotal),
    ];
  });

  autoTable(doc, {
    startY: yPos,
    head: [['Omschrijving', 'Aantal', 'Stukprijs (incl. BTW)', 'Totaal (incl. BTW)']],
    body: tableBody,
    theme: 'striped',
    headStyles: {
      fillColor: [51, 51, 51],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 9,
    },
    bodyStyles: {
      fontSize: 9,
    },
    columnStyles: {
      0: { cellWidth: 90 },
      1: { cellWidth: 20, halign: 'center' },
      2: { cellWidth: 35, halign: 'right' },
      3: { cellWidth: 35, halign: 'right' },
    },
    margin: { left: MARGIN, right: MARGIN },
  });

  return (doc as any).lastAutoTable.finalY + 10;
}

function renderTotals(doc: jsPDF, order: InvoiceOrder, yPos: number): number {
  const subtotalIncl = calculateSubtotal(order.items);
  const totalAmount = order.total_amount || subtotalIncl;
  const { subtotalExVat, vatAmount } = calculateVatFromTotal(totalAmount);

  const totalsX = PAGE_WIDTH - MARGIN - 70;
  const valuesX = PAGE_WIDTH - MARGIN;

  doc.setFontSize(10);

  // Subtotal ex VAT
  doc.setFont(undefined as any, 'normal');
  doc.text('Subtotaal excl. BTW:', totalsX, yPos);
  doc.text(formatCurrency(subtotalExVat), valuesX, yPos, { align: 'right' });
  yPos += 6;

  // VAT
  doc.text(`BTW (${(VAT_RATE * 100).toFixed(0)}%):`, totalsX, yPos);
  doc.text(formatCurrency(vatAmount), valuesX, yPos, { align: 'right' });
  yPos += 6;

  // Separator
  doc.setDrawColor(0, 0, 0);
  doc.line(totalsX, yPos, valuesX, yPos);
  yPos += 6;

  // Total
  doc.setFont(undefined as any, 'bold');
  doc.setFontSize(11);
  doc.text('Totaal incl. BTW:', totalsX, yPos);
  doc.text(formatCurrency(totalAmount), valuesX, yPos, { align: 'right' });
  yPos += 12;

  return yPos;
}

function renderFooter(doc: jsPDF, order: InvoiceOrder): void {
  const footerY = PAGE_HEIGHT - 25;

  // Separator line
  doc.setDrawColor(200, 200, 200);
  doc.line(MARGIN, footerY - 5, PAGE_WIDTH - MARGIN, footerY - 5);

  doc.setFontSize(8);
  doc.setTextColor(100, 100, 100);
  doc.setFont(undefined as any, 'normal');

  // Payment confirmation
  const paymentText = order.paid_at
    ? `Betaald op ${formatDate(order.paid_at)}`
    : 'Betaald';
  doc.text(paymentText, MARGIN, footerY);

  // Organization info
  doc.text(
    `${H_DCN_ORG.shortName} | BTW ${H_DCN_ORG.btwNummer} | KvK ${H_DCN_ORG.kvkNummer}`,
    PAGE_WIDTH / 2,
    footerY + 5,
    { align: 'center' }
  );

  // Page info
  doc.text(
    `Factuur ${order.invoice_number}`,
    PAGE_WIDTH - MARGIN,
    footerY,
    { align: 'right' }
  );
}
