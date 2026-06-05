"""
Order state machine for the webshop management admin.

Defines the valid order states and transitions. State transitions allow
forward skipping (e.g., order_received → paid directly) provided the target
is reachable in the defined sequence. The locked → submitted unlock is the
only backward transition allowed. payment_failed is a terminal state.
"""

from typing import List


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
    Return all states that are valid transition targets from the given state.

    Uses the same logic as is_valid_transition to determine which states
    are reachable from current_status.
    """
    valid_states: List[str] = []

    # All possible target states to check
    all_possible_targets = set(ORDERED_STATES + ['payment_failed'])

    for target in all_possible_targets:
        if target != current_status and is_valid_transition(current_status, target):
            valid_states.append(target)

    return sorted(valid_states)
