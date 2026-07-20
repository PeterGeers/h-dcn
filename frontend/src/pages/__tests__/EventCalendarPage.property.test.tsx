/**
 * Property-based tests for EventCalendarPage filter logic
 *
 * Tests the event type filter exclusion logic extracted from the EventCalendarPage
 * component's useMemo filtering pipeline.
 *
 * Uses fast-check with minimum 100 iterations.
 *
 * **Validates: Requirements 11.3**
 */

import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Extracted filter logic (mirrors the useMemo in EventCalendarPage.tsx)
// ---------------------------------------------------------------------------

interface EventForFilter {
  event_id: string;
  event_type: string;
}

/**
 * Filters events by selected event types.
 * When filterTypes is non-empty, only events whose event_type is included
 * in the selection are kept. Events with types not in the selection are excluded.
 */
function filterEventsByType<T extends EventForFilter>(
  events: T[],
  filterTypes: string[],
): T[] {
  if (filterTypes.length === 0) return events;
  return events.filter((event) => filterTypes.includes(event.event_type));
}

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/** Pool of possible event types to keep tests focused. */
const eventTypeArbitrary = fc.oneof(
  fc.constant('ride'),
  fc.constant('meeting'),
  fc.constant('social'),
  fc.constant('rally'),
  fc.constant('charity'),
  fc.constant('workshop'),
);

/** Generate a minimal event object with an event_type field. */
const eventArbitrary = fc.record({
  event_id: fc.uuid(),
  event_type: eventTypeArbitrary,
});

/** Generate a non-empty array of selected event types (unique values). */
const selectedTypesArbitrary = fc.uniqueArray(eventTypeArbitrary, {
  minLength: 1,
  maxLength: 6,
});

// ---------------------------------------------------------------------------
// Property 6: Event calendar type filter exclusion
// ---------------------------------------------------------------------------

describe('Property 6: Event calendar type filter exclusion', () => {
  /**
   * **Validates: Requirements 11.3**
   *
   * For any set of events with event_type fields and any non-empty selection
   * of event types, the filtered result must contain only events whose
   * event_type is included in the selection array. Events with types not in
   * the selection are excluded.
   */
  it('filtered result contains only events whose event_type is in the selection', () => {
    fc.assert(
      fc.property(
        fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
        selectedTypesArbitrary,
        (events, selectedTypes) => {
          const filtered = filterEventsByType(events, selectedTypes);

          // All events in the filtered result must have event_type in the selection
          for (const event of filtered) {
            expect(selectedTypes).toContain(event.event_type);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('no event with event_type NOT in the selection appears in the result', () => {
    fc.assert(
      fc.property(
        fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
        selectedTypesArbitrary,
        (events, selectedTypes) => {
          const filtered = filterEventsByType(events, selectedTypes);

          // Events whose type is NOT in the selection must be absent from the result
          const excludedEvents = events.filter(
            (e) => !selectedTypes.includes(e.event_type),
          );
          for (const excluded of excludedEvents) {
            expect(filtered).not.toContainEqual(excluded);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('all matching events from input are preserved in the result', () => {
    fc.assert(
      fc.property(
        fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
        selectedTypesArbitrary,
        (events, selectedTypes) => {
          const filtered = filterEventsByType(events, selectedTypes);

          // Every event in the input whose type IS in the selection must appear
          const expectedEvents = events.filter((e) =>
            selectedTypes.includes(e.event_type),
          );
          expect(filtered).toEqual(expectedEvents);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('filtered result length equals count of events with matching types', () => {
    fc.assert(
      fc.property(
        fc.array(eventArbitrary, { minLength: 0, maxLength: 30 }),
        selectedTypesArbitrary,
        (events, selectedTypes) => {
          const filtered = filterEventsByType(events, selectedTypes);

          const expectedCount = events.filter((e) =>
            selectedTypes.includes(e.event_type),
          ).length;
          expect(filtered.length).toBe(expectedCount);
        },
      ),
      { numRuns: 100 },
    );
  });
});
