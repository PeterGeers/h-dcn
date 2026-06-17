/**
 * Safe price formatter.
 *
 * DynamoDB returns prices as strings ("25"), numbers (25), or null.
 * This helper safely converts any value to a formatted €X.XX string.
 *
 * @param value - Price value (string, number, null, or undefined)
 * @param fallback - Fallback value when price is null/undefined (default: 0)
 * @returns Formatted string like "€25.00"
 */
export function formatPrice(value: string | number | null | undefined, fallback: number = 0): string {
  const num = value != null ? Number(value) : fallback;
  if (isNaN(num)) return `€${fallback.toFixed(2)}`;
  return `€${num.toFixed(2)}`;
}

/** Alias for formatPrice — used in VariantSubTable */
export const formatPriceEuro = formatPrice;

/**
 * Safe price-to-number conversion.
 *
 * Converts a price from DynamoDB (string or number) to a numeric value.
 * Returns the fallback if the value is null, undefined, or not a valid number.
 */
export function toPrice(value: string | number | null | undefined, fallback: number = 0): number {
  if (value == null) return fallback;
  const num = Number(value);
  return isNaN(num) ? fallback : num;
}
