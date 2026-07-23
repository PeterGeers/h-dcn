"""Property-based tests for WorkflowEngine using Hypothesis.

**Validates: Requirements 1.3, 8.3**

These tests prove the engine never crashes regardless of input and always
returns correctly-typed TransitionResult objects with consistent invariants.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from shared.workflows.engine import WorkflowEngine
from shared.workflows.types import TransitionResult
from shared.workflows.membership import membership_engine
from shared.workflows.orders import order_engine


# -- Strategies --

arbitrary_context = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(st.text(max_size=50), st.integers(), st.booleans(), st.none()),
    max_size=10,
)

arbitrary_state = st.text(min_size=0, max_size=50)
arbitrary_event = st.text(min_size=0, max_size=50)


# -- Property 1: engine.execute() never raises regardless of input --

@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_membership_engine_execute_never_raises(state, event, context):
    """engine.execute() never raises regardless of input (membership engine)."""
    result = membership_engine.execute(state, event, context)
    assert isinstance(result, TransitionResult)


@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_order_engine_execute_never_raises(state, event, context):
    """engine.execute() never raises regardless of input (order engine)."""
    result = order_engine.execute(state, event, context)
    assert isinstance(result, TransitionResult)


# -- Property 2: Always returns TransitionResult with correct types --

@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_execute_returns_correct_types(state, event, context):
    """execute() always returns TransitionResult with correct field types."""
    result = membership_engine.execute(state, event, context)

    assert isinstance(result.success, bool)
    assert isinstance(result.old_state, str)
    assert result.new_state is None or isinstance(result.new_state, str)
    assert isinstance(result.event, str)
    assert isinstance(result.actions_executed, list)
    assert isinstance(result.side_effects_executed, list)
    assert isinstance(result.failures, list)
    assert result.error is None or isinstance(result.error, str)


# -- Property 3: success=True implies new_state is not None --

@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_success_true_implies_new_state_not_none(state, event, context):
    """When success=True, new_state must not be None."""
    result = membership_engine.execute(state, event, context)

    if result.success:
        assert result.new_state is not None


@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_order_success_true_implies_new_state_not_none(state, event, context):
    """When success=True, new_state must not be None (order engine)."""
    result = order_engine.execute(state, event, context)

    if result.success:
        assert result.new_state is not None


# -- Property 4: success=False implies new_state is None --

@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_success_false_implies_new_state_none(state, event, context):
    """When success=False, new_state must be None."""
    result = membership_engine.execute(state, event, context)

    if not result.success:
        assert result.new_state is None


@given(state=arbitrary_state, event=arbitrary_event, context=arbitrary_context)
@settings(max_examples=200)
def test_order_success_false_implies_new_state_none(state, event, context):
    """When success=False, new_state must be None (order engine)."""
    result = order_engine.execute(state, event, context)

    if not result.success:
        assert result.new_state is None


# -- Property 5: get_allowed_events() never raises regardless of input --

@given(state=arbitrary_state)
@settings(max_examples=200)
def test_membership_get_allowed_events_never_raises(state):
    """get_allowed_events() never raises regardless of input."""
    result = membership_engine.get_allowed_events(state)
    assert isinstance(result, list)
    assert all(isinstance(e, str) for e in result)


@given(state=arbitrary_state)
@settings(max_examples=200)
def test_order_get_allowed_events_never_raises(state):
    """get_allowed_events() never raises regardless of input (order engine)."""
    result = order_engine.get_allowed_events(state)
    assert isinstance(result, list)
    assert all(isinstance(e, str) for e in result)
