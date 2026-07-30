import fc from 'fast-check';

/**
 * Feature: event-location-maps-link, Property 1: Maps URL round-trip preserves location
 *
 * Validates: Requirements 1.1, 1.2, 2.1, 3.4
 *
 * For any non-empty, non-whitespace-only string (up to 300 characters, including Unicode),
 * constructing the Maps search URL with encodeURIComponent and then extracting and decoding
 * the query parameter with decodeURIComponent SHALL produce the original trimmed string,
 * AND the full URL SHALL be parseable by new URL(...) without throwing.
 */

// Pure function replicating the URL construction logic from LocationMapLink component
const buildMapsUrl = (location: string): string =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location.trim())}`;

describe('LocationMapLink - Property Tests', () => {
  // Arbitrary: non-empty strings up to 300 chars that are not whitespace-only
  const nonEmptyNonWhitespaceString = fc
    .string({ minLength: 1, maxLength: 300 })
    .filter((s) => s.trim().length > 0);

  // Arbitrary: full Unicode strings (including emoji, CJK, etc.)
  const fullUnicodeNonWhitespaceString = fc
    .fullUnicodeString({ minLength: 1, maxLength: 300 })
    .filter((s) => s.trim().length > 0);

  it('Maps URL round-trip preserves location (ASCII strings)', () => {
    fc.assert(
      fc.property(nonEmptyNonWhitespaceString, (location) => {
        const url = buildMapsUrl(location);

        // URL must be parseable without throwing
        const parsed = new URL(url);

        // URL.searchParams.get() automatically decodes percent-encoded values,
        // so we compare directly without calling decodeURIComponent again.
        const queryParam = parsed.searchParams.get('query');
        expect(queryParam).not.toBeNull();
        expect(queryParam).toEqual(location.trim());
      }),
      { numRuns: 100 }
    );
  });

  it('Maps URL round-trip preserves location (full Unicode strings)', () => {
    fc.assert(
      fc.property(fullUnicodeNonWhitespaceString, (location) => {
        const url = buildMapsUrl(location);

        // URL must be parseable without throwing
        const parsed = new URL(url);

        // URL.searchParams.get() automatically decodes percent-encoded values,
        // so we compare directly without calling decodeURIComponent again.
        const queryParam = parsed.searchParams.get('query');
        expect(queryParam).not.toBeNull();
        expect(queryParam).toEqual(location.trim());
      }),
      { numRuns: 100 }
    );
  });
});
