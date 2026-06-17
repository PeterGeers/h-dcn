import * as fc from 'fast-check';
import { filterEvents, getSelectedEventTags } from '../modules/products/components/EventSelector';
import { Event as HDCNEvent } from '../types';

// Feature: product-variant-simplification, Property 5: Event search filter correctness
// Feature: product-variant-simplification, Property 6: Collapsed event display matches selection

/**
 * Property-based tests for EventSelector utility functions.
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 6.2, 6.3, 6.6**
 */

const NUM_RUNS = 100;

// --- Generators ---

/**
 * Generator for a non-empty event name string (alphanumeric + spaces, 1-30 chars).
 */
const eventNameArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')),
  { minLength: 1, maxLength: 30 },
);

/**
 * Generator for a unique event_id.
 */
const eventIdArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789-'.split('')),
  { minLength: 4, maxLength: 20 },
);

/**
 * Generator for an HDCNEvent object.
 * Randomly picks whether the event name is in title, naam, or only event_id.
 */
const hdcnEventArb: fc.Arbitrary<HDCNEvent> = fc.oneof(
  // Event with title set
  fc.record({
    event_id: eventIdArb,
    title: eventNameArb,
    naam: fc.constant(undefined),
  }),
  // Event with naam set (no title)
  fc.record({
    event_id: eventIdArb,
    title: fc.constant(undefined),
    naam: eventNameArb,
  }),
  // Event with only event_id (no title/naam)
  fc.record({
    event_id: eventIdArb,
    title: fc.constant(undefined),
    naam: fc.constant(undefined),
  }),
) as fc.Arbitrary<HDCNEvent>;

/**
 * Generator for a list of events with unique event_ids.
 */
const eventListArb = fc.uniqueArray(hdcnEventArb, {
  minLength: 0,
  maxLength: 20,
  selector: (e) => e.event_id || '',
});

/**
 * Generator for a search string (may include empty/whitespace).
 */
const searchStringArb = fc.oneof(
  fc.constant(''),
  fc.constant('   '),
  fc.stringOf(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')),
    { minLength: 1, maxLength: 15 },
  ),
);

// --- Helper ---

/** Computes the event name using the same logic as the component. */
function getEventName(event: HDCNEvent): string {
  return event.title || event.naam || event.event_id || '';
}

// --- Property 5: Event search filter correctness ---

describe('EventSelector filterEvents property tests', () => {
  /**
   * Property 5a: When search is empty or whitespace-only, all events are returned.
   */
  describe('Property 5a: Empty/whitespace search returns all events', () => {
    it('filterEvents with empty/whitespace search returns the full event list', () => {
      fc.assert(
        fc.property(
          eventListArb,
          fc.oneof(fc.constant(''), fc.constant('  '), fc.constant('\t')),
          (events, search) => {
            const result = filterEvents(events, search);
            expect(result).toEqual(events);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 5b: filterEvents returns exactly those events whose name contains
   * the search string as a case-insensitive substring.
   */
  describe('Property 5b: Filter returns exactly matching events', () => {
    it('result is the subset of events whose name includes search (case-insensitive)', () => {
      fc.assert(
        fc.property(eventListArb, searchStringArb, (events, search) => {
          const result = filterEvents(events, search);

          if (!search.trim()) {
            // Empty search returns all
            expect(result).toEqual(events);
          } else {
            const lowerSearch = search.toLowerCase();
            const expected = events.filter((event) =>
              getEventName(event).toLowerCase().includes(lowerSearch),
            );
            expect(result).toEqual(expected);
          }
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 5c: filterEvents result is always a subset of the input list
   * (no elements are added, order preserved).
   */
  describe('Property 5c: Result is a subset maintaining order', () => {
    it('every element in the result appears in the input in the same order', () => {
      fc.assert(
        fc.property(eventListArb, searchStringArb, (events, search) => {
          const result = filterEvents(events, search);

          // Every result element exists in events
          for (const r of result) {
            expect(events).toContain(r);
          }

          // Order is preserved (result indices are increasing in original array)
          let lastIdx = -1;
          for (const r of result) {
            const idx = events.indexOf(r);
            expect(idx).toBeGreaterThan(lastIdx);
            lastIdx = idx;
          }
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 5d: If a substring of an event name is used as search,
   * that event is guaranteed to be in the result.
   */
  describe('Property 5d: Substring of event name always matches', () => {
    it('filtering by a substring of an event name includes that event', () => {
      fc.assert(
        fc.property(
          eventListArb.filter((events) => events.length > 0),
          fc.nat(),
          (events, pickIdx) => {
            const event = events[pickIdx % events.length];
            const name = getEventName(event);
            if (name.length === 0) return; // skip events with empty names

            // Pick a random substring
            const start = pickIdx % name.length;
            const end = start + 1 + (pickIdx % (name.length - start));
            const substring = name.slice(start, Math.min(end, name.length));

            const result = filterEvents(events, substring);
            expect(result).toContain(event);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });
});

// --- Property 6: Collapsed event display matches selection ---

describe('EventSelector getSelectedEventTags property tests', () => {
  /**
   * Property 6a: The number of returned tags equals the number of selected IDs
   * that exist in the events array.
   */
  describe('Property 6a: Tag count matches number of valid selected IDs', () => {
    it('length equals count of selectedIds that map to an existing event', () => {
      fc.assert(
        fc.property(
          eventListArb,
          fc.array(eventIdArb, { minLength: 0, maxLength: 10 }),
          (events, selectedIds) => {
            const result = getSelectedEventTags(events, selectedIds);

            const validCount = selectedIds.filter((id) =>
              events.some((e) => (e.event_id || '') === id),
            ).length;

            expect(result.length).toBe(validCount);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 6b: Each tag's label matches the corresponding event's name.
   */
  describe('Property 6b: Tag labels match event names', () => {
    it('every tag label equals the name of the event with that ID', () => {
      fc.assert(
        fc.property(
          eventListArb.filter((events) => events.length > 0),
          fc.array(fc.nat(), { minLength: 1, maxLength: 5 }),
          (events, indices) => {
            // Select IDs that actually exist in the events
            const selectedIds = indices.map((i) => events[i % events.length].event_id || '');
            const uniqueIds = [...new Set(selectedIds)];

            const result = getSelectedEventTags(events, uniqueIds);

            for (const tag of result) {
              const event = events.find((e) => (e.event_id || '') === tag.id);
              expect(event).toBeDefined();
              const expectedLabel = getEventName(event!);
              expect(tag.label).toBe(expectedLabel);
            }
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 6c: Selected IDs that do NOT exist in events produce no tags.
   */
  describe('Property 6c: Non-existent IDs produce no tags', () => {
    it('tags only contain IDs that exist in the events array', () => {
      fc.assert(
        fc.property(
          eventListArb,
          fc.array(eventIdArb, { minLength: 1, maxLength: 10 }),
          (events, randomIds) => {
            // Use IDs that definitely don't exist
            const existingIds = new Set(events.map((e) => e.event_id || ''));
            const nonExistentIds = randomIds.filter((id) => !existingIds.has(id));

            if (nonExistentIds.length === 0) return; // skip if all happen to match

            const result = getSelectedEventTags(events, nonExistentIds);
            expect(result.length).toBe(0);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 6d: Order of returned tags matches order of selectedIds
   * (filtered to those that exist). Uses unique selectedIds to avoid
   * duplicate-handling edge cases.
   */
  describe('Property 6d: Tag order matches selectedIds order', () => {
    it('tags are returned in the same order as the selectedIds input', () => {
      fc.assert(
        fc.property(
          eventListArb.filter((events) => events.length > 1),
          (events) => {
            // Shuffle event IDs to create a unique selection order
            const allIds = events.map((e) => e.event_id || '');
            const uniqueIds = [...new Set(allIds)];
            // Pick a subset to select (at least 2 for meaningful ordering test)
            const selectedIds = uniqueIds.slice(0, Math.min(uniqueIds.length, 5));

            const result = getSelectedEventTags(events, selectedIds);

            // Verify order: result tags appear in the same order as selectedIds
            let lastSelIdx = -1;
            for (const tag of result) {
              const selIdx = selectedIds.indexOf(tag.id);
              expect(selIdx).toBeGreaterThan(lastSelIdx);
              lastSelIdx = selIdx;
            }
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });
});
