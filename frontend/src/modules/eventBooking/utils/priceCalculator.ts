/**
 * Price calculator utility — computes client-side order totals.
 *
 * Calculates the total order amount from the order items array.
 * Uses line_total if available, otherwise falls back to unit_price.
 *
 * Validates: Requirements 11.5, 11.6, 11.7
 */

import { OrderItem, Product } from '../types/eventBooking.types';

/**
 * Calculate the total order amount from a list of order items.
 *
 * Uses each item's line_total when available (non-zero), otherwise
 * falls back to unit_price. Returns the sum rounded to 2 decimal places.
 *
 * @param items - Array of order items
 * @returns Total amount as a number with at most 2 decimal places
 */
export function calculateTotal(items: OrderItem[]): number {
  if (items.length === 0) return 0;

  const total = items.reduce((sum, item) => {
    const amount = item.line_total > 0 ? item.line_total : item.unit_price;
    return sum + amount;
  }, 0);

  return Math.round(total * 100) / 100;
}

/**
 * Calculate the total amount from order items, looking up prices
 * from product definitions. Useful when items don't yet have prices
 * assigned (e.g., during form editing before save).
 *
 * @param items - Array of order items (may have zero prices)
 * @param products - Product definitions with prices
 * @returns Total amount as a number with at most 2 decimal places
 */
export function calculateTotalFromProducts(
  items: OrderItem[],
  products: Product[]
): number {
  if (items.length === 0) return 0;

  const productMap = new Map(products.map((p) => [p.product_id, p]));

  const total = items.reduce((sum, item) => {
    // Prefer line_total, then unit_price from item, then product price
    if (item.line_total > 0) return sum + item.line_total;
    if (item.unit_price > 0) return sum + item.unit_price;
    const productDef = productMap.get(item.product_id);
    return sum + (productDef?.prijs ?? 0);
  }, 0);

  return Math.round(total * 100) / 100;
}

/**
 * Calculate the outstanding amount (balance due).
 *
 * @param totalAmount - Total order amount
 * @param totalPaid - Amount already paid
 * @returns Outstanding balance (never negative)
 */
export function calculateOutstanding(totalAmount: number, totalPaid: number): number {
  const outstanding = totalAmount - totalPaid;
  return Math.max(0, Math.round(outstanding * 100) / 100);
}

/**
 * Format a numeric amount as EUR currency string with 2 decimal places.
 *
 * Uses the nl-NL locale for proper EUR formatting (e.g., "€ 50,00").
 *
 * @param amount - Numeric amount to format
 * @returns Formatted currency string
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('nl-NL', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}
