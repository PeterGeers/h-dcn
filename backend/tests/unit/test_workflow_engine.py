"""Unit tests for the WorkflowEngine.

Tests use the membership workflow as a fixture to validate:
- Valid transitions return success=True with correct new_state
- Invalid transitions return success=False with error
- Guards that block return success=False
- Guards that allow return success=True
- get_allowed_events returns correct events
- Engine never raises exceptions regardless of input
"""

import pytest
from shared.workflows.engine import WorkflowEngine
from shared.workflows.membership import membership_engine, MEMBERSHIP_TRANSITIONS
from shared.workflows.states import MemberState, MemberEvent


class TestValidTransitions:
    """Valid transitions return success=True with correct new_state."""

    def test_applied_submit_goes_to_pending(self) -> None:
        result = membership_engine.execute('applied', 'SUBMIT')
        assert result.success is True
        assert result.new_state == 'pending'

    def test_pending_approve_goes_to_wait_payment(self) -> None:
        result = membership_engine.execute('pending', 'APPROVE')
        assert result.success is True
        assert result.new_state == 'wait_payment'

    def test_wait_payment_payment_received_goes_to_active(self) -> None:
        result = membership_engine.execute('wait_payment', 'PAYMENT_RECEIVED')
        assert result.success is True
        assert result.new_state == 'active'

    def test_active_cancel_goes_to_cancelled(self) -> None:
        result = membership_engine.execute('active', 'CANCEL')
        assert result.success is True
        assert result.new_state == 'cancelled'

    def test_result_contains_old_state_and_event(self) -> None:
        result = membership_engine.execute('applied', 'SUBMIT')
        assert result.old_state == 'applied'
        assert result.event == 'SUBMIT'


class TestInvalidTransitions:
    """Invalid transitions return success=False with error."""

    def test_active_submit_is_invalid(self) -> None:
        result = membership_engine.execute('active', 'SUBMIT')
        assert result.success is False
        assert result.error is not None

    def test_invalid_transition_has_no_new_state(self) -> None:
        result = membership_engine.execute('active', 'SUBMIT')
        assert result.new_state is None

    def test_nonexistent_state_is_invalid(self) -> None:
        result = membership_engine.execute('nonexistent', 'SUBMIT')
        assert result.success is False
        assert result.error is not None

    def test_nonexistent_event_is_invalid(self) -> None:
        result = membership_engine.execute('applied', 'NONEXISTENT')
        assert result.success is False
        assert result.error is not None


class TestGuardBlocks:
    """Guards that block return success=False."""

    def test_suspend_without_reason_blocked(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND', {})
        assert result.success is False

    def test_suspend_with_empty_reason_blocked(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND', {'reason': None})
        assert result.success is False

    def test_suspend_without_context_blocked(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND')
        assert result.success is False


class TestGuardAllows:
    """Guards that allow return success=True."""

    def test_suspend_with_reason_allowed(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND', {'reason': 'unpaid'})
        assert result.success is True
        assert result.new_state == 'suspended'

    def test_suspend_with_any_reason_string_allowed(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND', {'reason': 'violation'})
        assert result.success is True
        assert result.new_state == 'suspended'


class TestGetAllowedEvents:
    """get_allowed_events returns correct events for a given state."""

    def test_active_state_has_cancel_and_suspend(self) -> None:
        events = membership_engine.get_allowed_events('active')
        assert 'CANCEL' in events
        assert 'SUSPEND' in events

    def test_applied_state_has_submit(self) -> None:
        events = membership_engine.get_allowed_events('applied')
        assert 'SUBMIT' in events

    def test_cancelled_state_has_no_events(self) -> None:
        events = membership_engine.get_allowed_events('cancelled')
        assert events == []

    def test_nonexistent_state_returns_empty(self) -> None:
        events = membership_engine.get_allowed_events('nonexistent_state')
        assert events == []


class TestEngineNeverRaises:
    """Engine never raises exceptions regardless of input."""

    def test_none_state_does_not_raise(self) -> None:
        result = membership_engine.execute(None, 'SUBMIT')  # type: ignore[arg-type]
        assert result.success is False

    def test_none_event_does_not_raise(self) -> None:
        result = membership_engine.execute('applied', None)  # type: ignore[arg-type]
        assert result.success is False

    def test_numeric_state_does_not_raise(self) -> None:
        result = membership_engine.execute(123, 'SUBMIT')  # type: ignore[arg-type]
        assert result.success is False

    def test_empty_string_state_does_not_raise(self) -> None:
        result = membership_engine.execute('', '')
        assert result.success is False

    def test_get_allowed_events_with_none_does_not_raise(self) -> None:
        events = membership_engine.get_allowed_events(None)  # type: ignore[arg-type]
        assert isinstance(events, list)

    def test_execute_with_bad_context_type_does_not_raise(self) -> None:
        result = membership_engine.execute('active', 'SUSPEND', 'not_a_dict')  # type: ignore[arg-type]
        assert isinstance(result.success, bool)

    def test_engine_with_broken_guard_does_not_raise(self) -> None:
        """An engine with a guard that raises should still return a result."""

        def exploding_guard(ctx: dict) -> bool:
            raise RuntimeError("boom")

        transitions = [
            {
                'from_state': 'a',
                'to_state': 'b',
                'event': 'GO',
                'guard': exploding_guard,
                'actions': [],
                'side_effects': [],
            }
        ]
        engine = WorkflowEngine(transitions)
        result = engine.execute('a', 'GO', {})
        assert result.success is False
