/**
 * Property-based tests for event access control logic.
 *
 * Feature: closed-community-booking, Property 24
 * **Validates: Requirements 16.5, 16.7**
 *
 * Property 24: Event Access Control
 * For any (member, order) pair and API request, access SHALL be granted if and only if:
 * (a) the event_id is present in the member's allowed_events list, AND
 * (b) the member is listed as either primary_member_id or secondary_member_id on the order.
 * All other combinations SHALL receive HTTP 403.
 */

import * as fc from 'fast-check';
import {
  checkEventAccess,
  MemberAccess,
  OrderAccess,
} from '../utils/accessControl';

// --- Arbitraries ---

/** Generates a member ID */
const memberIdArb = fc.uuid();

/** Generates an event ID */
const eventIdArb = fc.uuid();

/** Generates a list of event IDs (0 to 10 events) */
const allowedEventsArb = fc.array(eventIdArb, { minLength: 0, maxLength: 10 });

/** Generates a MemberAccess object */
const memberAccessArb: fc.Arbitrary<MemberAccess> = fc.record({
  memberId: memberIdArb,
  allowedEvents: allowedEventsArb,
});

/** Generates an OrderAccess object */
const orderAccessArb: fc.Arbitrary<OrderAccess> = fc.record({
  eventId: eventIdArb,
  primaryMemberId: memberIdArb,
  secondaryMemberId: fc.option(memberIdArb, { nil: null }),
});

/**
 * Generates a (member, order) pair where access SHOULD be granted:
 * - event_id is in allowed_events
 * - member is either primary or secondary delegate
 */
const grantedAccessArb: fc.Arbitrary<{ member: MemberAccess; order: OrderAccess }> =
  fc
    .tuple(
      memberIdArb,
      eventIdArb,
      allowedEventsArb,
      fc.boolean(), // true = primary, false = secondary
      fc.option(memberIdArb, { nil: null }), // other delegate
    )
    .map(([memberId, eventId, otherEvents, isPrimary, otherDelegate]) => {
      // Ensure event_id is in allowed_events
      const allowedEvents = [...otherEvents, eventId];

      const member: MemberAccess = { memberId, allowedEvents };
      const order: OrderAccess = isPrimary
        ? {
            eventId,
            primaryMemberId: memberId,
            secondaryMemberId: otherDelegate,
          }
        : {
            eventId,
            primaryMemberId: otherDelegate || 'other-primary-id',
            secondaryMemberId: memberId,
          };

      return { member, order };
    });

/**
 * Generates a (member, order) pair where the member has event access
 * but is NOT a delegate on the order.
 */
const notDelegateArb: fc.Arbitrary<{ member: MemberAccess; order: OrderAccess }> =
  fc
    .tuple(
      memberIdArb,
      eventIdArb,
      allowedEventsArb,
      memberIdArb, // primary (different from member)
      fc.option(memberIdArb, { nil: null }), // secondary (different from member)
    )
    .filter(([memberId, , , primaryId, secondaryId]) => {
      // Ensure member is NOT primary or secondary
      return memberId !== primaryId && memberId !== secondaryId;
    })
    .map(([memberId, eventId, otherEvents, primaryId, secondaryId]) => {
      const allowedEvents = [...otherEvents, eventId];
      const member: MemberAccess = { memberId, allowedEvents };
      const order: OrderAccess = {
        eventId,
        primaryMemberId: primaryId,
        secondaryMemberId: secondaryId,
      };
      return { member, order };
    });

/**
 * Generates a (member, order) pair where the member does NOT have
 * the event in their allowed_events (regardless of delegate status).
 */
const noEventAccessArb: fc.Arbitrary<{ member: MemberAccess; order: OrderAccess }> =
  fc
    .tuple(
      memberIdArb,
      eventIdArb, // order's event
      allowedEventsArb, // member's other events
      memberIdArb, // primary
      fc.option(memberIdArb, { nil: null }), // secondary
    )
    .filter(([, eventId, otherEvents]) => {
      // Ensure the order's event_id is NOT in allowed_events
      return !otherEvents.includes(eventId);
    })
    .map(([memberId, eventId, allowedEvents, primaryId, secondaryId]) => {
      const member: MemberAccess = { memberId, allowedEvents };
      const order: OrderAccess = {
        eventId,
        primaryMemberId: primaryId,
        secondaryMemberId: secondaryId,
      };
      return { member, order };
    });

// --- Property Tests ---

describe('Event Access Control - Property Tests', () => {
  /**
   * Property 24: Access SHALL be granted when BOTH conditions are met:
   * (a) event_id in allowed_events AND (b) member is a delegate.
   *
   * **Validates: Requirements 16.5**
   */
  it('access is granted when event is in allowed_events AND member is a delegate', () => {
    fc.assert(
      fc.property(grantedAccessArb, ({ member, order }) => {
        const result = checkEventAccess(member, order);

        expect(result.granted).toBe(true);
        expect(result.reason).toBeNull();
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: Access SHALL be denied when member is NOT a delegate,
   * even if they have event access.
   *
   * **Validates: Requirements 16.5, 16.7**
   */
  it('access is denied when member is not a delegate (even with event access)', () => {
    fc.assert(
      fc.property(notDelegateArb, ({ member, order }) => {
        const result = checkEventAccess(member, order);

        expect(result.granted).toBe(false);
        expect(result.reason).toBe('not_a_delegate');
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: Access SHALL be denied when event is NOT in allowed_events,
   * regardless of delegate status.
   *
   * **Validates: Requirements 16.5, 16.7**
   */
  it('access is denied when event is not in allowed_events (regardless of delegate status)', () => {
    fc.assert(
      fc.property(noEventAccessArb, ({ member, order }) => {
        const result = checkEventAccess(member, order);

        expect(result.granted).toBe(false);
        expect(result.reason).toBe('event_not_allowed');
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: Access check is symmetric for primary and secondary delegates.
   * If a member is the secondary delegate with event access, they get the same
   * access grant as the primary delegate would.
   *
   * **Validates: Requirements 16.5**
   */
  it('secondary delegate has same access as primary delegate', () => {
    fc.assert(
      fc.property(
        memberIdArb,
        eventIdArb,
        memberIdArb,
        (memberId, eventId, otherDelegateId) => {
          fc.pre(memberId !== otherDelegateId);

          const member: MemberAccess = {
            memberId,
            allowedEvents: [eventId],
          };

          // As primary
          const orderAsPrimary: OrderAccess = {
            eventId,
            primaryMemberId: memberId,
            secondaryMemberId: otherDelegateId,
          };

          // As secondary
          const orderAsSecondary: OrderAccess = {
            eventId,
            primaryMemberId: otherDelegateId,
            secondaryMemberId: memberId,
          };

          const resultPrimary = checkEventAccess(member, orderAsPrimary);
          const resultSecondary = checkEventAccess(member, orderAsSecondary);

          expect(resultPrimary.granted).toBe(true);
          expect(resultSecondary.granted).toBe(true);
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: When both conditions fail (no event access AND not a delegate),
   * access is denied with event_not_allowed (checked first per implementation).
   *
   * **Validates: Requirements 16.7**
   */
  it('when both conditions fail, event_not_allowed takes priority', () => {
    fc.assert(
      fc.property(
        memberIdArb,
        eventIdArb,
        memberIdArb,
        fc.option(memberIdArb, { nil: null }),
        (memberId, eventId, primaryId, secondaryId) => {
          // Ensure member is NOT a delegate AND has no event access
          fc.pre(memberId !== primaryId && memberId !== secondaryId);

          const member: MemberAccess = {
            memberId,
            allowedEvents: [], // No events at all
          };
          const order: OrderAccess = {
            eventId,
            primaryMemberId: primaryId,
            secondaryMemberId: secondaryId,
          };

          const result = checkEventAccess(member, order);

          expect(result.granted).toBe(false);
          // event_not_allowed is checked first
          expect(result.reason).toBe('event_not_allowed');
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: Access is never granted with an empty allowed_events list,
   * regardless of delegate status on the order.
   *
   * **Validates: Requirements 16.5, 16.7**
   */
  it('access is never granted with empty allowed_events', () => {
    fc.assert(
      fc.property(
        memberIdArb,
        orderAccessArb,
        (memberId, order) => {
          const member: MemberAccess = {
            memberId,
            allowedEvents: [], // Empty — no events
          };

          const result = checkEventAccess(member, order);

          expect(result.granted).toBe(false);
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: Access check result is a strict boolean — granted is true or false,
   * never undefined or null.
   *
   * **Validates: Requirements 16.5**
   */
  it('result is always a strict boolean (granted is true or false)', () => {
    fc.assert(
      fc.property(memberAccessArb, orderAccessArb, (member, order) => {
        const result = checkEventAccess(member, order);

        expect(typeof result.granted).toBe('boolean');
        if (result.granted) {
          expect(result.reason).toBeNull();
        } else {
          expect(result.reason).not.toBeNull();
        }
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 24: A member with null secondary_member_id on the order can still
   * access as primary. The null secondary doesn't interfere.
   *
   * **Validates: Requirements 16.5**
   */
  it('null secondary_member_id does not interfere with primary access', () => {
    fc.assert(
      fc.property(memberIdArb, eventIdArb, (memberId, eventId) => {
        const member: MemberAccess = {
          memberId,
          allowedEvents: [eventId],
        };
        const order: OrderAccess = {
          eventId,
          primaryMemberId: memberId,
          secondaryMemberId: null, // No secondary
        };

        const result = checkEventAccess(member, order);
        expect(result.granted).toBe(true);
      }),
      { numRuns: 100 }
    );
  });
});
