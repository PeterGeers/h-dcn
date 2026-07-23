"""Unit tests for ActionDispatcher.

Tests cover:
- 5.1: register, register_many, execute_transition basic flow
- 5.2: Mandatory action failure sets success=False, stops remaining, skips side effects
- 5.3: Side effect failure logs in failures but keeps success=True
- 5.4: Unknown action names treated as error
"""

import pytest

from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.types import Transition, TransitionResult


def _make_transition(
    actions: list[str] | None = None,
    side_effects: list[str] | None = None,
) -> Transition:
    """Helper to create a minimal Transition for testing."""
    t: Transition = {
        'from_state': 'pending',
        'to_state': 'active',
        'event': 'APPROVE',
        'actions': actions or [],
        'side_effects': side_effects or [],
    }
    return t


def _make_result() -> TransitionResult:
    """Helper to create a fresh TransitionResult."""
    return TransitionResult(
        success=True,
        old_state='pending',
        new_state='active',
        event='APPROVE',
    )


# --- 5.1: Basic registration and execution ---


class TestRegister:
    def test_register_single_action(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register('do_thing', lambda ctx: called.append('done'))

        transition = _make_transition(actions=['do_thing'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == ['done']
        assert result.success is True
        assert 'do_thing' in result.actions_executed

    def test_register_many(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register_many({
            'action_a': lambda ctx: called.append('a'),
            'action_b': lambda ctx: called.append('b'),
        })

        transition = _make_transition(actions=['action_a', 'action_b'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == ['a', 'b']
        assert result.actions_executed == ['action_a', 'action_b']

    def test_execute_transition_passes_context(self):
        dispatcher = ActionDispatcher()
        received_ctx = {}

        def capture_context(ctx: dict) -> None:
            received_ctx.update(ctx)

        dispatcher.register('capture', capture_context)
        transition = _make_transition(actions=['capture'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {'member_id': '123'})

        assert received_ctx == {'member_id': '123'}

    def test_execute_transition_runs_actions_then_side_effects(self):
        dispatcher = ActionDispatcher()
        order = []
        dispatcher.register_many({
            'mandatory_1': lambda ctx: order.append('m1'),
            'mandatory_2': lambda ctx: order.append('m2'),
            'effect_1': lambda ctx: order.append('e1'),
            'effect_2': lambda ctx: order.append('e2'),
        })

        transition = _make_transition(
            actions=['mandatory_1', 'mandatory_2'],
            side_effects=['effect_1', 'effect_2'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert order == ['m1', 'm2', 'e1', 'e2']
        assert result.success is True
        assert result.actions_executed == ['mandatory_1', 'mandatory_2']
        assert result.side_effects_executed == ['effect_1', 'effect_2']


# --- 5.2: Mandatory action failure ---


class TestMandatoryActionFailure:
    def test_failure_sets_success_false(self):
        dispatcher = ActionDispatcher()
        dispatcher.register('fail_action', lambda ctx: (_ for _ in ()).throw(ValueError("db error")))

        transition = _make_transition(actions=['fail_action'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert result.success is False
        assert result.new_state is None

    def test_failure_stops_remaining_actions(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register_many({
            'action_1': lambda ctx: called.append('1'),
            'action_2': lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")),
            'action_3': lambda ctx: called.append('3'),
        })

        transition = _make_transition(actions=['action_1', 'action_2', 'action_3'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == ['1']  # action_3 never ran
        assert result.success is False
        assert 'action_1' in result.actions_executed
        assert 'action_3' not in result.actions_executed

    def test_failure_skips_side_effects(self):
        dispatcher = ActionDispatcher()
        side_effect_called = []
        dispatcher.register_many({
            'bad_action': lambda ctx: (_ for _ in ()).throw(RuntimeError("fail")),
            'my_effect': lambda ctx: side_effect_called.append(True),
        })

        transition = _make_transition(
            actions=['bad_action'],
            side_effects=['my_effect'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert side_effect_called == []  # Side effects never ran
        assert result.success is False
        assert result.side_effects_executed == []

    def test_failure_records_error_message(self):
        dispatcher = ActionDispatcher()
        dispatcher.register('explode', lambda ctx: (_ for _ in ()).throw(ValueError("kaboom")))

        transition = _make_transition(actions=['explode'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert result.error is not None
        assert 'explode' in result.error
        assert 'kaboom' in result.error
        assert any('kaboom' in f for f in result.failures)


# --- 5.3: Side effect failure ---


class TestSideEffectFailure:
    def test_side_effect_failure_keeps_success_true(self):
        dispatcher = ActionDispatcher()
        dispatcher.register_many({
            'good_action': lambda ctx: None,
            'bad_effect': lambda ctx: (_ for _ in ()).throw(RuntimeError("email failed")),
        })

        transition = _make_transition(
            actions=['good_action'],
            side_effects=['bad_effect'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert result.success is True
        assert result.new_state == 'active'  # Not cleared

    def test_side_effect_failure_logged_in_failures(self):
        dispatcher = ActionDispatcher()
        dispatcher.register_many({
            'good_action': lambda ctx: None,
            'bad_effect': lambda ctx: (_ for _ in ()).throw(RuntimeError("email failed")),
        })

        transition = _make_transition(
            actions=['good_action'],
            side_effects=['bad_effect'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert len(result.failures) == 1
        assert 'bad_effect' in result.failures[0]
        assert 'email failed' in result.failures[0]

    def test_side_effect_failure_does_not_stop_other_effects(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register_many({
            'good_action': lambda ctx: None,
            'effect_1': lambda ctx: (_ for _ in ()).throw(RuntimeError("fail")),
            'effect_2': lambda ctx: called.append('e2'),
        })

        transition = _make_transition(
            actions=['good_action'],
            side_effects=['effect_1', 'effect_2'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == ['e2']
        assert result.success is True
        assert 'effect_2' in result.side_effects_executed


# --- 5.4: Unknown action names ---


class TestUnknownActions:
    def test_unknown_mandatory_action_is_error(self):
        dispatcher = ActionDispatcher()
        # Don't register anything

        transition = _make_transition(actions=['nonexistent_action'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert result.success is False
        assert result.new_state is None
        assert result.error is not None
        assert 'nonexistent_action' in result.error
        assert any('nonexistent_action' in f for f in result.failures)

    def test_unknown_mandatory_action_stops_execution(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register('action_after', lambda ctx: called.append('after'))

        transition = _make_transition(actions=['unknown_first', 'action_after'])
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == []  # Nothing ran after the unknown action
        assert result.success is False

    def test_unknown_mandatory_action_skips_side_effects(self):
        dispatcher = ActionDispatcher()
        effect_called = []
        dispatcher.register('my_effect', lambda ctx: effect_called.append(True))

        transition = _make_transition(
            actions=['unknown_action'],
            side_effects=['my_effect'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert effect_called == []
        assert result.success is False

    def test_unknown_side_effect_logged_in_failures(self):
        dispatcher = ActionDispatcher()
        dispatcher.register('good_action', lambda ctx: None)

        transition = _make_transition(
            actions=['good_action'],
            side_effects=['nonexistent_effect'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        # Unknown side effect is logged but doesn't fail the transition
        assert result.success is True
        assert any('nonexistent_effect' in f for f in result.failures)

    def test_unknown_side_effect_does_not_stop_other_effects(self):
        dispatcher = ActionDispatcher()
        called = []
        dispatcher.register_many({
            'good_action': lambda ctx: None,
            'effect_2': lambda ctx: called.append('e2'),
        })

        transition = _make_transition(
            actions=['good_action'],
            side_effects=['unknown_effect', 'effect_2'],
        )
        result = _make_result()
        dispatcher.execute_transition(transition, result, {})

        assert called == ['e2']
        assert result.success is True
        assert 'effect_2' in result.side_effects_executed
