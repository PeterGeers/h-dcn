"""
Order and payment state machines for the H-DCN webshop.

Provides two orthogonal state machines:
- Order status: draft → submitted → confirmed → completed (or cancelled)
- Payment status: unpaid → pending/awaiting_payment → paid

The coupling rule (submitted→confirmed only when payment_status→paid) is
enforced by the webhook/admin handler, not by this module.

Fulfilment state machine (v2):
- Webshop flow: draft → submitted → paid → order_received → picked → packed → shipped → delivered → completed
- Event flow: draft → submitted → locked → paid → ready_for_pickup → picked_up → completed
- Returns: delivered → return_requested → return_received → completed
- Failures: submitted → payment_failed, payment_failed → submitted (retry)

Legacy exports (ORDERED_STATES, SPECIAL_TRANSITIONS, is_valid_transition,
get_next_valid_states) are preserved for backward compatibility with existing
admin handlers.
"""

from typing import Dict, List, Optional, Tuple


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
# Fulfilment state machine v2 — explicit transition map with actor + preconditions
# =============================================================================

# Actor types for transition validation
ACTOR_CUSTOMER = 'customer'
ACTOR_ADMIN = 'admin'
ACTOR_SYSTEM = 'system'

# Valid transitions: current_status → {target_status: {actors, preconditions}}
# actors: list of actor types that may trigger this transition
# preconditions: list of field names that must be non-empty on the order
VALID_TRANSITIONS: Dict[str, Dict[str, Dict]] = {
    'draft': {
        'submitted': {'actors': [ACTOR_CUSTOMER, ACTOR_SYSTEM], 'preconditions': []},
    },
    'submitted': {
        'paid': {'actors': [ACTOR_SYSTEM], 'preconditions': []},
        'payment_failed': {'actors': [ACTOR_SYSTEM], 'preconditions': []},
        'locked': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'locked': {
        'submitted': {'actors': [ACTOR_ADMIN], 'preconditions': []},  # unlock
        'paid': {'actors': [ACTOR_SYSTEM], 'preconditions': []},
    },
    'payment_failed': {
        'submitted': {'actors': [ACTOR_CUSTOMER], 'preconditions': []},  # retry
    },
    'paid': {
        'order_received': {'actors': [ACTOR_ADMIN], 'preconditions': []},
        'ready_for_pickup': {'actors': [ACTOR_ADMIN], 'preconditions': []},  # event shortcut
    },
    'order_received': {
        'picked': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'picked': {
        'packed': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'packed': {
        'shipped': {'actors': [ACTOR_ADMIN], 'preconditions': ['tracking_number']},
    },
    'shipped': {
        'delivered': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'delivered': {
        'completed': {'actors': [ACTOR_ADMIN], 'preconditions': []},
        'return_requested': {'actors': [ACTOR_ADMIN, ACTOR_CUSTOMER], 'preconditions': []},
    },
    'return_requested': {
        'return_received': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'return_received': {
        'completed': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'ready_for_pickup': {
        'picked_up': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'picked_up': {
        'completed': {'actors': [ACTOR_ADMIN], 'preconditions': []},
    },
    'completed': {},
}


def validate_fulfilment_transition(
    current: str,
    target: str,
    actor: str = ACTOR_ADMIN,
    order: Optional[dict] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate a fulfilment status transition.

    Args:
        current: Current order status
        target: Target order status
        actor: Who is performing the transition (admin/customer/system)
        order: The order dict (for precondition checks)

    Returns:
        (True, None) if transition is valid
        (False, error_message) if transition is invalid
    """
    if current not in VALID_TRANSITIONS:
        return False, f"Unknown status '{current}'. No transitions defined."

    targets = VALID_TRANSITIONS[current]
    if target not in targets:
        allowed = list(targets.keys())
        return False, (
            f"Invalid transition from '{current}' to '{target}'. "
            f"Allowed: {allowed}"
        )

    transition_config = targets[target]

    # Validate actor
    allowed_actors = transition_config.get('actors', [])
    if actor not in allowed_actors:
        return False, (
            f"Actor '{actor}' is not allowed for transition "
            f"'{current}' → '{target}'. Allowed actors: {allowed_actors}"
        )

    # Validate preconditions
    preconditions = transition_config.get('preconditions', [])
    if preconditions and order:
        for field in preconditions:
            value = order.get(field)
            if not value:
                return False, (
                    f"Precondition failed: '{field}' is required for "
                    f"transition to '{target}'."
                )

    return True, None


def get_valid_transitions_for_actor(current: str, actor: str = ACTOR_ADMIN) -> List[str]:
    """
    Return all valid target statuses for the given current status and actor.
    """
    if current not in VALID_TRANSITIONS:
        return []

    targets = VALID_TRANSITIONS[current]
    valid = []
    for target, config in targets.items():
        if actor in config.get('actors', []):
            valid.append(target)
    return valid


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
    Check whether transitioning from current to target is allowed.

    Uses the new VALID_TRANSITIONS map first, falls back to legacy logic
    for backward compatibility.
    """
    # Try new fulfilment state machine first
    if current in VALID_TRANSITIONS:
        targets = VALID_TRANSITIONS[current]
        if target in targets:
            return True

    # Legacy fallback: terminal state
    if current == 'payment_failed':
        # payment_failed → submitted is in VALID_TRANSITIONS already
        return target == 'submitted'

    # Legacy fallback: forward movement in ordered sequence
    if current in ORDERED_STATES and target in ORDERED_STATES:
        current_idx = ORDERED_STATES.index(current)
        target_idx = ORDERED_STATES.index(target)
        if target_idx > current_idx:
            return True

    # Special transitions (legacy)
    if current in SPECIAL_TRANSITIONS:
        return target in SPECIAL_TRANSITIONS[current]

    return False


def get_next_valid_states(current_status: str) -> List[str]:
    """
    Return all states that are valid transition targets from the given state.
    Uses the new VALID_TRANSITIONS map when available.
    """
    # Use v2 fulfilment map
    if current_status in VALID_TRANSITIONS:
        return sorted(list(VALID_TRANSITIONS[current_status].keys()))

    # Fallback for unknown states
    valid_states: List[str] = []
    all_possible_targets = set(ORDERED_STATES + ['payment_failed'])

    for target in all_possible_targets:
        if target != current_status and is_valid_transition(current_status, target):
            valid_states.append(target)

    return sorted(valid_states)
