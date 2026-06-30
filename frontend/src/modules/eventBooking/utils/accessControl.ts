/**
 * Access control utility — pure functions for determining whether a member
 * has access to perform booking API operations on an order.
 *
 * Access is granted if and only if:
 * (a) The event_id is present in the member's allowed_events list, AND
 * (b) The member is listed as either primary_member_id or secondary_member_id on the order.
 *
 * All other combinations result in HTTP 403.
 *
 * Validates: Requirements 16.5, 16.7
 */

export interface MemberAccess {
  /** The member's unique ID */
  memberId: string;
  /** List of event IDs this member is allowed to access */
  allowedEvents: string[];
}

export interface OrderAccess {
  /** The event this order belongs to */
  eventId: string;
  /** The primary delegate's member ID */
  primaryMemberId: string;
  /** The secondary delegate's member ID (null if none assigned) */
  secondaryMemberId: string | null;
}

export interface AccessCheckResult {
  /** Whether access is granted */
  granted: boolean;
  /** Reason for denial (null if granted) */
  reason: 'event_not_allowed' | 'not_a_delegate' | null;
}

/**
 * Check whether a member has access to an order's booking API endpoints.
 *
 * Two conditions must BOTH be true for access to be granted:
 * 1. The order's event_id must be in the member's allowed_events list
 * 2. The member must be listed as primary_member_id OR secondary_member_id on the order
 *
 * If either condition fails, access is denied with a specific reason.
 * The order of checks matters: event access is checked first (condition a),
 * then delegate status (condition b).
 */
export function checkEventAccess(
  member: MemberAccess,
  order: OrderAccess
): AccessCheckResult {
  // Condition (a): event_id must be in allowed_events
  const hasEventAccess = member.allowedEvents.includes(order.eventId);
  if (!hasEventAccess) {
    return {
      granted: false,
      reason: 'event_not_allowed',
    };
  }

  // Condition (b): member must be primary or secondary delegate
  const isDelegate =
    member.memberId === order.primaryMemberId ||
    member.memberId === order.secondaryMemberId;

  if (!isDelegate) {
    return {
      granted: false,
      reason: 'not_a_delegate',
    };
  }

  return {
    granted: true,
    reason: null,
  };
}
