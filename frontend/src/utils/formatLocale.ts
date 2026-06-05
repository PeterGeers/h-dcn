/**
 * Locale-aware formatting utilities using the browser Intl API.
 *
 * Provides date, currency, and number formatting that respects the active locale.
 * All functions return an empty string for null/undefined/NaN/unparseable values.
 *
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

/**
 * Formats a date using Intl.DateTimeFormat with the given locale.
 *
 * - "short" style uses dateStyle: 'short' (e.g., "31-12-2024" for nl, "12/31/2024" for en)
 * - "long" style uses dateStyle: 'long' (e.g., "31 december 2024" for nl, "December 31, 2024" for en)
 *
 * Accepts Date objects or ISO date strings.
 * Returns empty string for null, undefined, or invalid/unparseable values.
 */
export function formatDate(
  date: Date | string | null | undefined,
  style: 'short' | 'long',
  locale: string
): string {
  if (date === null || date === undefined) {
    return '';
  }

  try {
    const dateObj = date instanceof Date ? date : new Date(date);

    if (isNaN(dateObj.getTime())) {
      return '';
    }

    const formatter = new Intl.DateTimeFormat(locale, {
      dateStyle: style,
    });

    return formatter.format(dateObj);
  } catch {
    return '';
  }
}

/**
 * Formats a currency amount (EUR) with locale-appropriate separators.
 *
 * Uses Intl.NumberFormat with style: 'currency', currency: 'EUR',
 * minimumFractionDigits: 2, maximumFractionDigits: 2.
 *
 * Returns empty string for null, undefined, or NaN.
 */
export function formatCurrency(
  amount: number | null | undefined,
  locale: string
): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '';
  }

  try {
    const formatter = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

    return formatter.format(amount);
  } catch {
    return '';
  }
}

/**
 * Formats a number with locale-appropriate decimal separators and thousands grouping.
 *
 * Uses Intl.NumberFormat with the given locale.
 *
 * Returns empty string for null, undefined, or NaN.
 */
export function formatNumber(
  value: number | null | undefined,
  locale: string
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '';
  }

  try {
    const formatter = new Intl.NumberFormat(locale);

    return formatter.format(value);
  } catch {
    return '';
  }
}
