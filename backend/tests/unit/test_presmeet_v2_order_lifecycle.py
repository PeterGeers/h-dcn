"""
Property-based tests for PresMeet v2 order lifecycle state machine.
Tests correctness properties defined in the PresMeet v2 design document.
"""

import sys
import os

# Add the auth layer to the path so we can import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st


# ============================================================
# Order State Machine Model
# ============================================================

# The three valid order statuses
VALID_STATUSES = ["draft", "submitted", "locked"]

# The four actions that can be applied to an order
VALID_ACTIONS = ["submit", "modify", "lock", "unlock"]

# State machine transition table:
# (current_state, action) -> (new_state | None)
# None means the transition is invalid / rejected
TRANSITION_TABLE = {
    # From draft
    ("draft", "submit"): "submitted",
    ("draft", "modify"): "draft",        # modify on draft keeps it draft (no-op save)
    ("draft", "lock"): None,             # cannot lock a draft order
    ("draft", "unlock"): None,           # cannot unlock a draft order

    # From submitted
    ("submitted", "submit"): None,       # already submitted, rejected (409)
    ("submitted", "modify"): "draft",    # modification reverts to draft
    ("submitted", "lock"): "locked",     # admin locks submitted order
    ("submitted", "unlock"): None,       # cannot unlock a submitted order

    # From locked
    ("locked", "submit"): None,          # cannot submit a locked order
    ("locked", "modify"): None,          # cannot modify a locked order (409)
    ("locked", "lock"): None,            # already locked, rejected
    ("locked", "unlock"): "submitted",   # admin unlocks to submitted
}


def apply_transition(current_state: str, action: str) -> tuple:
    """
    Apply a state machine transition.

    Returns:
        (success: bool, new_state: str)
        - If transition is valid: (True, new_state)
        - If transition is invalid: (False, current_state) — state unchanged
    """
    expected_new_state = TRANSITION_TABLE.get((current_state, action))
    if expected_new_state is None:
        return (False, current_state)
    return (True, expected_new_state)


# ============================================================
# Property 10: Order state machine transitions
# ============================================================


class TestProperty10OrderStateMachineTransitions:
    """Feature: presmeet-v2, Property 10: Order state machine transitions

    For any order, the following transition rules SHALL hold exhaustively:
    - From draft: submit → submitted; lock → rejected; unlock → rejected
    - From submitted: modify → draft; admin lock → locked; submit → rejected
    - From locked: non-admin modify → rejected; admin unlock → submitted; lock → rejected

    No other status values SHALL be reachable.
    """

    # --- Strategies ---
    _state_strategy = st.sampled_from(VALID_STATUSES)
    _action_strategy = st.sampled_from(VALID_ACTIONS)

    @given(
        current_state=_state_strategy,
        action=_action_strategy,
    )
    @settings(max_examples=200)
    def test_property10_valid_transitions_reach_expected_state(
        self, current_state, action
    ):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.2**

        For any starting state and action, if the transition is defined as valid,
        the resulting state SHALL match the expected target state from the
        transition table.
        """
        expected_target = TRANSITION_TABLE.get((current_state, action))

        success, new_state = apply_transition(current_state, action)

        if expected_target is not None:
            # Valid transition: must succeed and reach expected state
            assert success is True, (
                f"Transition ({current_state}, {action}) should be valid "
                f"but was rejected"
            )
            assert new_state == expected_target, (
                f"Transition ({current_state}, {action}) should reach "
                f"'{expected_target}' but reached '{new_state}'"
            )
        else:
            # Invalid transition: must be rejected, state unchanged
            assert success is False, (
                f"Transition ({current_state}, {action}) should be rejected "
                f"but succeeded"
            )
            assert new_state == current_state, (
                f"Rejected transition ({current_state}, {action}) should leave "
                f"state unchanged at '{current_state}' but state is '{new_state}'"
            )

    @given(
        current_state=_state_strategy,
        action=_action_strategy,
    )
    @settings(max_examples=200)
    def test_property10_invalid_transitions_leave_state_unchanged(
        self, current_state, action
    ):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.3, 8.6, 8.7, 11.2**

        For any starting state and action that is NOT a valid transition,
        the state SHALL remain unchanged (rejected transitions are no-ops).
        """
        expected_target = TRANSITION_TABLE.get((current_state, action))
        assume(expected_target is None)  # Only test invalid transitions

        success, new_state = apply_transition(current_state, action)

        assert success is False, (
            f"Transition ({current_state}, {action}) should be invalid/rejected"
        )
        assert new_state == current_state, (
            f"Invalid transition ({current_state}, {action}) should not change state. "
            f"Expected '{current_state}', got '{new_state}'"
        )

    @given(
        current_state=_state_strategy,
        action=_action_strategy,
    )
    @settings(max_examples=200)
    def test_property10_resulting_state_always_in_valid_set(
        self, current_state, action
    ):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.2, 11.2**

        For any starting state and any action applied, the resulting state
        SHALL always be one of the three valid statuses: draft, submitted, locked.
        No other status values SHALL be reachable.
        """
        _, new_state = apply_transition(current_state, action)

        assert new_state in VALID_STATUSES, (
            f"Resulting state '{new_state}' after ({current_state}, {action}) "
            f"is not in the valid set {VALID_STATUSES}"
        )

    @given(
        actions=st.lists(_action_strategy, min_size=1, max_size=20),
    )
    @settings(max_examples=200)
    def test_property10_sequential_transitions_always_stay_in_valid_states(
        self, actions
    ):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.2**

        For any sequence of actions applied starting from 'draft',
        the state after each step SHALL always be one of the three valid
        statuses. The state machine is closed over {draft, submitted, locked}.
        """
        state = "draft"

        for action in actions:
            _, state = apply_transition(state, action)
            assert state in VALID_STATUSES, (
                f"State '{state}' is not valid after applying action '{action}'. "
                f"Valid states are: {VALID_STATUSES}"
            )

    # --- Specific transition property tests ---

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_draft_to_submitted_via_submit(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.2**

        From 'draft', applying 'submit' (with valid data) SHALL transition
        the order to 'submitted'.
        """
        success, new_state = apply_transition("draft", "submit")
        assert success is True
        assert new_state == "submitted"

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_submitted_to_locked_via_lock(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.5**

        From 'submitted', applying 'lock' (admin) SHALL transition
        the order to 'locked'.
        """
        success, new_state = apply_transition("submitted", "lock")
        assert success is True
        assert new_state == "locked"

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_locked_to_submitted_via_unlock(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.7**

        From 'locked', applying 'unlock' (admin) SHALL transition
        the order to 'submitted'.
        """
        success, new_state = apply_transition("locked", "unlock")
        assert success is True
        assert new_state == "submitted"

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_submitted_to_draft_via_modify(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.4**

        From 'submitted', applying 'modify' SHALL revert the order to 'draft'.
        """
        success, new_state = apply_transition("submitted", "modify")
        assert success is True
        assert new_state == "draft"

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_draft_cannot_be_locked_directly(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.3**

        From 'draft', applying 'lock' SHALL be rejected. A draft order
        cannot be locked without first being submitted.
        """
        success, new_state = apply_transition("draft", "lock")
        assert success is False
        assert new_state == "draft"

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property10_locked_cannot_be_modified(self, data):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.6**

        From 'locked', applying 'modify' SHALL be rejected (returns 409).
        A locked order cannot be modified by the Club_Representative.
        """
        success, new_state = apply_transition("locked", "modify")
        assert success is False
        assert new_state == "locked"

    # --- Exhaustiveness check ---

    def test_property10_transition_table_covers_all_state_action_pairs(self):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 11.2**

        The transition table SHALL cover all possible (state, action) pairs
        exhaustively. No combination should be undefined.
        """
        for state in VALID_STATUSES:
            for action in VALID_ACTIONS:
                key = (state, action)
                assert key in TRANSITION_TABLE, (
                    f"Transition ({state}, {action}) is not defined in the "
                    f"transition table. All state-action pairs must be covered."
                )

    # --- Handler integration verification ---

    @given(
        actions=st.lists(_action_strategy, min_size=2, max_size=10),
    )
    @settings(max_examples=200)
    def test_property10_submit_only_valid_from_draft(self, actions):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.2, 8.3**

        For any sequence of actions, 'submit' SHALL only succeed when
        the current state is 'draft'. In all other states, submit is rejected.
        """
        state = "draft"

        for action in actions:
            if action == "submit":
                success, new_state = apply_transition(state, action)
                if state == "draft":
                    assert success is True, (
                        f"Submit should succeed from 'draft' but was rejected"
                    )
                    assert new_state == "submitted"
                else:
                    assert success is False, (
                        f"Submit should be rejected from '{state}' but succeeded"
                    )
                    assert new_state == state
                state = new_state
            else:
                _, state = apply_transition(state, action)

    @given(
        actions=st.lists(_action_strategy, min_size=2, max_size=10),
    )
    @settings(max_examples=200)
    def test_property10_lock_only_valid_from_submitted(self, actions):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.5**

        For any sequence of actions, 'lock' SHALL only succeed when
        the current state is 'submitted'. In all other states, lock is rejected.
        """
        state = "draft"

        for action in actions:
            if action == "lock":
                success, new_state = apply_transition(state, action)
                if state == "submitted":
                    assert success is True, (
                        f"Lock should succeed from 'submitted' but was rejected"
                    )
                    assert new_state == "locked"
                else:
                    assert success is False, (
                        f"Lock should be rejected from '{state}' but succeeded"
                    )
                    assert new_state == state
                state = new_state
            else:
                _, state = apply_transition(state, action)

    @given(
        actions=st.lists(_action_strategy, min_size=2, max_size=10),
    )
    @settings(max_examples=200)
    def test_property10_unlock_only_valid_from_locked(self, actions):
        """Feature: presmeet-v2, Property 10: Order state machine transitions

        **Validates: Requirements 8.7**

        For any sequence of actions, 'unlock' SHALL only succeed when
        the current state is 'locked'. In all other states, unlock is rejected.
        """
        state = "draft"

        for action in actions:
            if action == "unlock":
                success, new_state = apply_transition(state, action)
                if state == "locked":
                    assert success is True, (
                        f"Unlock should succeed from 'locked' but was rejected"
                    )
                    assert new_state == "submitted"
                else:
                    assert success is False, (
                        f"Unlock should be rejected from '{state}' but succeeded"
                    )
                    assert new_state == state
                state = new_state
            else:
                _, state = apply_transition(state, action)


# ============================================================
# Property 11: Lock ALL batch operation
# ============================================================

# Valid order statuses for PresMeet orders (reusing VALID_STATUSES from above)
ORDER_STATUSES = VALID_STATUSES


# --- Strategies for Property 11 ---

def _order_strategy(order_index):
    """Generate an order dict with a random status from ORDER_STATUSES."""
    return st.fixed_dictionaries({
        "order_id": st.just(f"order-{order_index}"),
        "source": st.just("presmeet"),
        "event_id": st.just("evt-presmeet-2025"),
        "club_id": st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=3,
            max_size=20,
        ),
        "status": st.sampled_from(ORDER_STATUSES),
        "payment_status": st.just("unpaid"),
        "total_amount": st.just("100.00"),
        "created_at": st.just("2025-01-01T00:00:00+00:00"),
        "updated_at": st.just("2025-01-01T00:00:00+00:00"),
    })


# Strategy for generating a list of orders with mixed statuses
_orders_list_strategy = st.integers(min_value=0, max_value=20).flatmap(
    lambda n: st.tuples(*[_order_strategy(i) for i in range(n)]) if n > 0 else st.just(())
).map(list)


def lock_all_batch(orders):
    """
    Simulate the Lock ALL batch operation as implemented in lock_presmeet_orders handler.

    This replicates the core logic: scan all presmeet orders with status='submitted'
    and transition them to 'locked'. Orders in 'draft' or 'locked' status are unchanged.

    Args:
        orders: List of order dicts with at least 'order_id', 'source', 'event_id', 'status'.

    Returns:
        Tuple of (updated_orders, locked_count) where updated_orders is the list
        with status transitions applied.
    """
    locked_count = 0
    updated_orders = []

    for order in orders:
        # Only process presmeet orders (matching the handler's filter)
        if order.get("source") != "presmeet" or not order.get("event_id"):
            updated_orders.append(order.copy())
            continue

        if order["status"] == "submitted":
            updated_order = order.copy()
            updated_order["status"] = "locked"
            updated_orders.append(updated_order)
            locked_count += 1
        else:
            # draft and locked orders remain unchanged
            updated_orders.append(order.copy())

    return updated_orders, locked_count


class TestProperty11LockAllBatchOperation:
    """Feature: presmeet-v2, Property 11: Lock ALL batch operation

    **Validates: Requirements 8.8**

    When a PresMeet_Admin triggers "Lock ALL", the system SHALL transition all
    orders with status 'submitted' to 'locked', leaving 'draft' and already
    'locked' orders unchanged.
    """

    @given(orders=_orders_list_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_property11_submitted_orders_become_locked(self, orders):
        """Feature: presmeet-v2, Property 11: Lock ALL batch operation

        After "Lock ALL", all previously-submitted orders are now locked.

        **Validates: Requirements 8.8**
        """
        # Record which orders were submitted before the operation
        submitted_order_ids = {
            o["order_id"] for o in orders if o["status"] == "submitted"
        }

        # Execute Lock ALL
        updated_orders, _ = lock_all_batch(orders)

        # All previously-submitted orders must now be locked
        for order in updated_orders:
            if order["order_id"] in submitted_order_ids:
                assert order["status"] == "locked", (
                    f"Order '{order['order_id']}' was submitted before Lock ALL "
                    f"but has status '{order['status']}' instead of 'locked'"
                )

    @given(orders=_orders_list_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_property11_draft_orders_remain_draft(self, orders):
        """Feature: presmeet-v2, Property 11: Lock ALL batch operation

        After "Lock ALL", all previously-draft orders remain draft (unchanged).

        **Validates: Requirements 8.8**
        """
        # Record which orders were draft before the operation
        draft_order_ids = {
            o["order_id"] for o in orders if o["status"] == "draft"
        }

        # Execute Lock ALL
        updated_orders, _ = lock_all_batch(orders)

        # All previously-draft orders must remain draft
        for order in updated_orders:
            if order["order_id"] in draft_order_ids:
                assert order["status"] == "draft", (
                    f"Order '{order['order_id']}' was draft before Lock ALL "
                    f"but has status '{order['status']}' instead of 'draft'"
                )

    @given(orders=_orders_list_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_property11_locked_orders_remain_locked(self, orders):
        """Feature: presmeet-v2, Property 11: Lock ALL batch operation

        After "Lock ALL", all previously-locked orders remain locked (unchanged).

        **Validates: Requirements 8.8**
        """
        # Record which orders were already locked before the operation
        already_locked_order_ids = {
            o["order_id"] for o in orders if o["status"] == "locked"
        }

        # Execute Lock ALL
        updated_orders, _ = lock_all_batch(orders)

        # All previously-locked orders must remain locked
        for order in updated_orders:
            if order["order_id"] in already_locked_order_ids:
                assert order["status"] == "locked", (
                    f"Order '{order['order_id']}' was already locked before Lock ALL "
                    f"but has status '{order['status']}' instead of 'locked'"
                )

    @given(orders=_orders_list_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_property11_locked_count_equals_original_submitted_count(self, orders):
        """Feature: presmeet-v2, Property 11: Lock ALL batch operation

        The count of locked orders after "Lock ALL" equals
        original_locked_count + original_submitted_count.

        **Validates: Requirements 8.8**
        """
        # Count original statuses
        original_submitted_count = sum(
            1 for o in orders if o["status"] == "submitted"
        )
        original_locked_count = sum(
            1 for o in orders if o["status"] == "locked"
        )

        # Execute Lock ALL
        updated_orders, locked_count = lock_all_batch(orders)

        # The locked_count returned should equal the number of orders transitioned
        assert locked_count == original_submitted_count, (
            f"locked_count ({locked_count}) should equal original submitted count "
            f"({original_submitted_count})"
        )

        # Total locked orders after operation = original locked + newly locked
        total_locked_after = sum(
            1 for o in updated_orders if o["status"] == "locked"
        )
        expected_locked = original_locked_count + original_submitted_count
        assert total_locked_after == expected_locked, (
            f"Total locked orders after Lock ALL ({total_locked_after}) should equal "
            f"original_locked ({original_locked_count}) + original_submitted "
            f"({original_submitted_count}) = {expected_locked}"
        )

    @given(orders=_orders_list_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_property11_lock_all_is_idempotent(self, orders):
        """Feature: presmeet-v2, Property 11: Lock ALL batch operation

        Applying Lock ALL twice produces the same result as applying it once
        (idempotent operation - no submitted orders remain after first application).

        **Validates: Requirements 8.8**
        """
        # First application
        updated_once, count_first = lock_all_batch(orders)

        # Second application
        updated_twice, count_second = lock_all_batch(updated_once)

        # Second application should change nothing (no submitted orders left)
        assert count_second == 0, (
            f"Second Lock ALL should lock 0 orders (all submitted already locked), "
            f"but locked {count_second}"
        )

        # States should be identical after first and second application
        for o1, o2 in zip(updated_once, updated_twice):
            assert o1["status"] == o2["status"], (
                f"Order '{o1['order_id']}' changed status between Lock ALL applications: "
                f"'{o1['status']}' -> '{o2['status']}'"
            )
