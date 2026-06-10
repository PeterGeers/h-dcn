"""
Order and payment state machines for the H-DCN webshop.

Provides two orthogonal state machines:
- Order status: draft → submitted → confirmed → completed (or cancelled)
- Payment status: unpaid → pending/awaiting_payment → paid

The coupling rule (submitted→confirmed only when payment_status→paid) is
enforced by the webhook/admin handler, not by this module.

Legacy exports (ORDERED_STATES, SPECIAL_TRANSITIONS, is_valid_transition,
get_next_valid_states) are preserved for backward compatibility with existing
admin handlers.
"""

from typing import Dict, List


# =============================================================================
# New two-axis state machine
# =============================================================================

# Allowed order status transitions
ORDER_TRANSITIONS: Dict[str, List[str]] = {
    'draft': ['submitted', 'cancelled'],
    'submitted': ['confirmed', 'cancelled'],
    'confirmed': ['completed'],
    'completed': [],
    'cancelled': [],
}

# Allowed payment status transitions
PAYMENT_TRANSITIONS: Dict[str, List[str]] = {
    'unpaid': ['pending', 'awaiting_payment'],
    'pending': ['paid', 'unpaid'],           # unpaid = failed payment retry
    'awaiting_payment': ['paid'],
    'paid': [],                              # terminal
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: str, target: str, allowed: List[str]):
        self.current = current
        self.target = target
        self.allowed = allowed
        super().__init__(
            f"Invalid transition from '{current}' to '{target}'. "
            f"Allowed transitions: {allowed}"
        )


def validate_order_transition(current: str, target: str) -> bool:
    """Return True if the order status transition is valid."""
    if current not in ORDER_TRANSITIONS:
        return False
    return target in ORDER_TRANSITIONS[current]


def validate_payment_transition(current: str, target: str) -> bool:
    """Return True if the payment status transition is valid."""
    if current not in PAYMENT_TRANSITIONS:
        return False
    return target in PAYMENT_TRANSITIONS[current]


def transition_order(current_status: str, target_status: str) -> str:
    """
    Return target_status if transition is valid, raise InvalidTransitionError otherwise.
    """
    if validate_order_transition(current_status, target_status):
        return target_status
    allowed = ORDER_TRANSITIONS.get(current_status, [])
    raise InvalidTransitionError(current_status, target_status, allowed)


def transition_payment(current_status: str, target_status: str) -> str:
    """
    Return target_status if transition is valid, raise InvalidTransitionError otherwise.
    """
    if validate_payment_transition(current_status, target_status):
        return target_status
    allowed = PAYMENT_TRANSITIONS.get(current_status, [])
    raise InvalidTransitionError(current_status, target_status, allowed)


# =============================================================================
# Legacy state machine (backward compatibility for admin handlers)
# =============================================================================

ORDERED_STATES: List[str] = [
    'draft',
    'submitted',
    'locked',
    'order_received',
    'payment_pending',
    'paid',
    'picked',
    'packed',
    'shipped',
    'delivered',
    'return_requested',
    'return_received',
    'completed',
]

SPECIAL_TRANSITIONS: dict = {
    'order_received': ['payment_pending', 'paid'],
    'payment_pending': ['paid', 'payment_failed'],
    'delivered': ['return_requested', 'completed'],
    'locked': ['submitted'],  # unlock
}


def is_valid_transition(current: str, target: str) -> bool:
    """
    Check whether transitioning from current to target is allowed (legacy).

    Rules:
    - locked → submitted (unlock) is always valid
    - payment_failed is a terminal state (no transitions out)
    - Any forward skip within ORDERED_STATES is valid
    - Special transitions define additional valid targets from specific states
    - All other transitions are invalid
    """
    # Special case: unlock
    if current == 'locked' and target == 'submitted':
        return True

    # Terminal state
    if current == 'payment_failed':
        return False

    # Check if target is reachable forward in the ordered sequence
    if current in ORDERED_STATES and target in ORDERED_STATES:
        current_idx = ORDERED_STATES.index(current)
        target_idx = ORDERED_STATES.index(target)
        if target_idx > current_idx:
            return True

    # Special transitions
    if current in SPECIAL_TRANSITIONS:
        return target in SPECIAL_TRANSITIONS[current]

    return False


def get_next_valid_states(current_status: str) -> List[str]:
    """
    Return all states that are valid transition targets from the given state (legacy).
    """
    valid_states: List[str] = []
    all_possible_targets = set(ORDERED_STATES + ['payment_failed'])

    for target in all_possible_targets:
        if target != current_status and is_valid_transition(current_status, target):
            valid_states.append(target)

    return sorted(valid_states)
