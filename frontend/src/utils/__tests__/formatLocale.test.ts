import { formatDate, formatCurrency, formatNumber } from '../formatLocale';

describe('formatLocale utilities', () => {
  describe('formatDate', () => {
    it('returns empty string for null', () => {
      expect(formatDate(null, 'short', 'nl')).toBe('');
    });

    it('returns empty string for undefined', () => {
      expect(formatDate(undefined, 'short', 'nl')).toBe('');
    });

    it('returns empty string for invalid date string', () => {
      expect(formatDate('not-a-date', 'short', 'nl')).toBe('');
    });

    it('formats a Date object with short style', () => {
      const date = new Date(2024, 11, 31); // Dec 31, 2024
      const result = formatDate(date, 'short', 'nl');
      expect(result).not.toBe('');
      // Verify it contains the year
      expect(result).toContain('2024');
    });

    it('formats a Date object with long style', () => {
      const date = new Date(2024, 11, 31);
      const result = formatDate(date, 'long', 'nl');
      expect(result).not.toBe('');
      expect(result.toLowerCase()).toContain('december');
    });

    it('formats an ISO date string', () => {
      const result = formatDate('2024-12-31T00:00:00.000Z', 'short', 'en');
      expect(result).not.toBe('');
      // Short format may use 2-digit year (12/31/24)
      expect(result).toMatch(/12/);
    });

    it('produces different output for different locales', () => {
      const date = new Date(2024, 11, 31);
      const nl = formatDate(date, 'short', 'nl');
      const en = formatDate(date, 'short', 'en');
      // Both should be non-empty strings
      expect(nl).not.toBe('');
      expect(en).not.toBe('');
      // Dutch and English short dates differ in separator/order
      expect(nl).not.toBe(en);
    });
  });

  describe('formatCurrency', () => {
    it('returns empty string for null', () => {
      expect(formatCurrency(null, 'nl')).toBe('');
    });

    it('returns empty string for undefined', () => {
      expect(formatCurrency(undefined, 'nl')).toBe('');
    });

    it('returns empty string for NaN', () => {
      expect(formatCurrency(NaN, 'nl')).toBe('');
    });

    it('formats a valid amount with EUR currency', () => {
      const result = formatCurrency(1234.5, 'nl');
      expect(result).not.toBe('');
      // Should contain euro symbol and 2 decimal places
      expect(result).toMatch(/€/);
      expect(result).toMatch(/1.*234/); // thousands separated
    });

    it('formats zero correctly', () => {
      const result = formatCurrency(0, 'nl');
      expect(result).not.toBe('');
      expect(result).toMatch(/€/);
    });

    it('formats negative amounts', () => {
      const result = formatCurrency(-50.99, 'en');
      expect(result).not.toBe('');
      expect(result).toMatch(/€/);
    });
  });

  describe('formatNumber', () => {
    it('returns empty string for null', () => {
      expect(formatNumber(null, 'nl')).toBe('');
    });

    it('returns empty string for undefined', () => {
      expect(formatNumber(undefined, 'nl')).toBe('');
    });

    it('returns empty string for NaN', () => {
      expect(formatNumber(NaN, 'nl')).toBe('');
    });

    it('formats a valid integer', () => {
      const result = formatNumber(1234567, 'nl');
      expect(result).not.toBe('');
      // Dutch uses dots as thousands separator
      expect(result).toContain('.');
    });

    it('formats a decimal number', () => {
      const result = formatNumber(3.14, 'nl');
      expect(result).not.toBe('');
      // Dutch uses comma as decimal separator
      expect(result).toContain(',');
    });

    it('formats zero', () => {
      expect(formatNumber(0, 'nl')).toBe('0');
    });

    it('uses locale-appropriate separators for English', () => {
      const result = formatNumber(1234567.89, 'en');
      expect(result).not.toBe('');
      // English uses commas for thousands and dot for decimal
      expect(result).toContain(',');
      expect(result).toContain('.');
    });
  });
});
