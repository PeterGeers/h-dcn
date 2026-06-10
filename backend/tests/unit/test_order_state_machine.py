"""
Property-based tests for the order and payment state machines.

Uses Hypothesis to verify universal properties across all valid/invalid
status transitions.

Feature: order-pipeline-improvements
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from shared.order_state_machine import (
    ORDER_TRANSITIONS,
    PAYMENT_TRANSITIONS,
    validate_order_transition,
    validate_payment_transition,
    transition_order,
    transition_payment,
    InvalidTransitionError,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

order_statuses = st.sampled_from(list(ORDER_TRANSITIONS.keys()))
payment_statuses = st.sampled_from(list(PAYMENT_TRANSITIONS.keys()))


# ---------------------------------------------------------------------------
# Property 1: Order state machine accepts all valid transitions
# Feature: order-pipeline-improvements, Property 1: Order state machine accepts all valid transitions
# Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6
# ---------------------------------------------------------------------------

@given(current=order_statuses)
@settings(max_examples=200)
def test_property_1_order_valid_transitions_accepted(current):
    """For any order status current and target in allowed transitions,
    validate_order_transition(current, target) returns True."""
    allowed = ORDER_TRANSITIONS[current]
    for target in allowed:
        assert validate_order_transition(current, target) is True, (
            f"Expected valid transition {current} -> {target} to be accepted"
        )


# ---------------------------------------------------------------------------
# Property 2: Order state machine rejects all invalid transitions
# Feature: order-pipeline-improvements, Property 2: Order state machine rejects all invalid transitions
# Validates: Requirements 1.7
# ---------------------------------------------------------------------------

@given(current=order_statuses, target=order_statuses)
@settings(max_examples=200)
def test_property_2_order_invalid_transitions_rejected(current, target):
    """For any order status current and target NOT in allowed transitions,
    validate_order_transition(current, target) returns False."""
    allowed = ORDER_TRANSITIONS[current]
    assume(target not in allowed)
    assert validate_order_transition(current, target) is False, (
        f"Expected invalid transition {current} -> {target} to be rejected"
    )


# ---------------------------------------------------------------------------
# Property 3: Payment state machine accepts all valid transitions
# Feature: order-pipeline-improvements, Property 3: Payment state machine accepts all valid transitions
# Validates: Requirements 2.1, 2.2, 2.3, 2.4
# ---------------------------------------------------------------------------

@given(current=payment_statuses)
@settings(max_examples=200)
def test_property_3_payment_valid_transitions_accepted(current):
    """For any payment status current and target in allowed transitions,
    validate_payment_transition(current, target) returns True."""
    allowed = PAYMENT_TRANSITIONS[current]
    for target in allowed:
        assert validate_payment_transition(current, target) is True, (
            f"Expected valid transition {current} -> {target} to be accepted"
        )


# ---------------------------------------------------------------------------
# Property 4: Payment state machine rejects all invalid transitions
# Feature: order-pipeline-improvements, Property 4: Payment state machine rejects all invalid transitions
# Validates: Requirements 2.5
# ---------------------------------------------------------------------------

@given(current=payment_statuses, target=payment_statuses)
@settings(max_examples=200)
def test_property_4_payment_invalid_transitions_rejected(current, target):
    """For any payment status current and target NOT in allowed transitions,
    validate_payment_transition(current, target) returns False."""
    allowed = PAYMENT_TRANSITIONS[current]
    assume(target not in allowed)
    assert validate_payment_transition(current, target) is False, (
        f"Expected invalid transition {current} -> {target} to be rejected"
    )


# ---------------------------------------------------------------------------
# Property 5: Payment confirmation triggers order confirmation
# Feature: order-pipeline-improvements, Property 5: Payment confirmation triggers order confirmation
# Validates: Requirements 1.3, 1.4
# ---------------------------------------------------------------------------

@given(
    payment_status=st.sampled_from(['pending', 'awaiting_payment'])
)
@settings(max_examples=200)
def test_property_5_payment_paid_triggers_order_confirmed(payment_status):
    """For any order with status='submitted' and payment_status in
    ['pending', 'awaiting_payment'], when payment_status transitions to 'paid',
    the order status can also transition to 'confirmed'.

    This property verifies the coupling rule: submitted→confirmed is valid
    when payment transitions to paid. The coupling is enforced in the handler,
    but the state machine must ALLOW both transitions."""
    # Payment transition to 'paid' must be valid
    assert validate_payment_transition(payment_status, 'paid') is True, (
        f"Payment transition {payment_status} -> paid should be valid"
    )

    # Order transition submitted → confirmed must be valid (the coupling rule)
    assert validate_order_transition('submitted', 'confirmed') is True, (
        "Order transition submitted -> confirmed should be valid"
    )

    # Verify transition_order returns the target status
    result = transition_order('submitted', 'confirmed')
    assert result == 'confirmed', (
        f"transition_order('submitted', 'confirmed') should return 'confirmed', got '{result}'"
    )

    # Verify transition_payment returns 'paid'
    result = transition_payment(payment_status, 'paid')
    assert result == 'paid', (
        f"transition_payment('{payment_status}', 'paid') should return 'paid', got '{result}'"
    )
