/**
 * Property-based tests for club search filtering.
 *
 * Feature: presmeet-v3, Property 6
 * Validates: Requirements 4.1, 4.2
 */

import * as fc from 'fast-check';
import { filterClubs } from '../components/OnboardingFlow';
import { ClubRegistryEntry } from '../types/presmeet';

// --- Arbitraries ---

/** Generates a valid club_id string */
const clubIdArb = fc.uuid();

/** Generates a club name (non-empty string) */
const clubNameArb = fc.string({ minLength: 1, maxLength: 80 });

/** Generates a single ClubRegistryEntry */
const clubEntryArb: fc.Arbitrary<ClubRegistryEntry> = fc.record({
  club_id: clubIdArb,
  club_name: clubNameArb,
  logo_url: fc.oneof(fc.constant(null), fc.webUrl()),
  assigned_member_id: fc.oneof(fc.constant(null), fc.uuid()),
  assigned_contact: fc.oneof(fc.constant(null), fc.string({ minLength: 1, maxLength: 50 })),
  assigned_at: fc.oneof(fc.constant(null), fc.date().map((d) => d.toISOString())),
});

/** Generates a list of clubs */
const clubListArb = fc.array(clubEntryArb, { minLength: 0, maxLength: 30 });

/** Generates a non-empty search string */
const searchStringArb = fc.string({ minLength: 1, maxLength: 40 });

/** Generates an empty or whitespace-only search string */
const emptySearchArb = fc.oneof(
  fc.constant(''),
  fc.array(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 1, maxLength: 5 }).map((arr) => arr.join(''))
);

// --- Property Tests ---

describe('Club Search Filter - Property Tests', () => {
  /**
   * Property 6: Club search filter returns correct results
   *
   * For any club list and search string, the filter function SHALL return
   * exactly those clubs whose name contains the search string (case-insensitive
   * comparison). When the search string is empty, all clubs SHALL be returned.
   *
   * **Validates: Requirements 4.1, 4.2**
   */
  it('Property 6: empty/whitespace search returns all clubs', () => {
    fc.assert(
      fc.property(clubListArb, emptySearchArb, (clubs, search) => {
        const result = filterClubs(clubs, search);
        expect(result).toHaveLength(clubs.length);
        expect(result).toEqual(clubs);
      }),
      { numRuns: 100 }
    );
  });

  it('Property 6: non-empty search returns exactly clubs whose name contains the search text (case-insensitive)', () => {
    fc.assert(
      fc.property(clubListArb, searchStringArb, (clubs, search) => {
        const result = filterClubs(clubs, search);
        const trimmed = search.trim();

        if (!trimmed) {
          // Whitespace-only non-empty strings should return all
          expect(result).toEqual(clubs);
          return;
        }

        const lowerSearch = trimmed.toLowerCase();

        // Every returned club must contain the search text
        for (const club of result) {
          expect(club.club_name.toLowerCase()).toContain(lowerSearch);
        }

        // Every club NOT returned must NOT contain the search text
        const excluded = clubs.filter((c) => !result.includes(c));
        for (const club of excluded) {
          expect(club.club_name.toLowerCase()).not.toContain(lowerSearch);
        }

        // Result count matches manual filter
        const expected = clubs.filter((c) =>
          c.club_name.toLowerCase().includes(lowerSearch)
        );
        expect(result).toHaveLength(expected.length);
      }),
      { numRuns: 100 }
    );
  });

  it('Property 6: search is case-insensitive — same results for any casing of the search string', () => {
    fc.assert(
      fc.property(clubListArb, searchStringArb, (clubs, search) => {
        const resultLower = filterClubs(clubs, search.toLowerCase());
        const resultUpper = filterClubs(clubs, search.toUpperCase());
        const resultOriginal = filterClubs(clubs, search);

        // All casings produce the same results
        expect(resultLower).toEqual(resultOriginal);
        expect(resultUpper).toEqual(resultOriginal);
      }),
      { numRuns: 100 }
    );
  });

  it('Property 6: result is always a subset of the input club list (preserves order and identity)', () => {
    fc.assert(
      fc.property(clubListArb, searchStringArb, (clubs, search) => {
        const result = filterClubs(clubs, search);

        // Result must be a subsequence of the original list
        let lastIdx = -1;
        for (const club of result) {
          const idx = clubs.indexOf(club, lastIdx + 1);
          expect(idx).toBeGreaterThan(lastIdx);
          lastIdx = idx;
        }
      }),
      { numRuns: 100 }
    );
  });

  it('Property 6: searching for a substring of a known club name always includes that club', () => {
    fc.assert(
      fc.property(
        clubListArb.filter((clubs) => clubs.length > 0),
        fc.nat(),
        (clubs, idx) => {
          // Pick a random club from the list
          const targetClub = clubs[idx % clubs.length];
          const name = targetClub.club_name;

          if (name.length === 0) return; // skip empty names

          // Pick a random substring of the club's name
          const start = idx % name.length;
          const end = start + 1 + (idx % (name.length - start));
          const substring = name.slice(start, Math.min(end, name.length));

          const result = filterClubs(clubs, substring);

          // The target club must be in the results
          expect(result).toContainEqual(targetClub);
        }
      ),
      { numRuns: 100 }
    );
  });
});
