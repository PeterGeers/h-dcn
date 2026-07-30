# Implementation Plan

## Overview

Implement a lightweight workflow engine in the shared Lambda Layer that provides state machine capabilities for membership and order status transitions. The engine evaluates transitions, dispatches mandatory actions and side effects, and logs audit trails — all without AWS SDK dependencies in the core engine.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "2.1", "3.1"] },
    {
      "id": 1,
      "tasks": [
        "4.1",
        "4.2",
        "4.3",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "6.1",
        "6.2",
        "6.3"
      ]
    },
    { "id": 2, "tasks": ["7.1", "7.2", "8.1", "8.2"] },
    { "id": 3, "tasks": ["9.1", "10.1", "11.1"] },
    { "id": 4, "tasks": ["12.1", "12.2", "12.3"] }
  ]
}
```

## Tasks

- [x] 1. Create module structure and core types
  - [x] 1.1 Create directory `backend/layers/auth-layer/python/shared/workflows/` with `__init__.py` (re-exports engine, dispatcher, types, states, guards, audit)
  - [x] 1.2 Create `types.py` containing `Transition` TypedDict (from_state, to_state, event, guard, actions, side_effects) and `TransitionResult` dataclass (success, old_state, new_state, event, actions_executed, side_effects_executed, failures, error)
  - [x] 1.3 Verify with Pyright

- [x] 2. Define state and event enums
  - [x] 2.1 Create `states.py` with StrEnum classes: `MemberState` (APPLIED, PENDING, WAIT_PAYMENT, ACTIVE, CANCELLED, SUSPENDED), `MemberEvent` (SUBMIT, APPROVE, PAYMENT_RECEIVED, CANCEL, SUSPEND, REACTIVATE), `OrderState` (DRAFT, SUBMITTED, PAID, FULFILLED, CANCELLED, REFUNDED), `OrderEvent` (SUBMIT, PAYMENT_RECEIVED, FULFILL, CANCEL, REFUND)

- [x] 3. Implement guard functions
  - [x] 3.1 Create `guards.py` with named guard functions (no lambdas): `requires_reason(ctx)`, `has_valid_payment(ctx)`, `has_stock_available(ctx)`, `is_refundable(ctx)`. Each with descriptive docstring.

- [x] 4. Implement WorkflowEngine
  - [x] 4.1 Create `engine.py` with `WorkflowEngine` class supporting `get_allowed_events(current_state)`, `can_transition(current_state, event, context)`, and `execute(current_state, event, context)`
  - [x] 4.2 Engine must never raise exceptions (returns success=False with error for invalid transitions)
  - [x] 4.3 Engine must NOT import any AWS SDK modules

- [x] 5. Implement ActionDispatcher
  - [x] 5.1 Create `dispatcher.py` with `ActionDispatcher` class providing `register(name, fn)`, `register_many(dict)`, and `execute_transition(transition, result, context)`
  - [x] 5.2 Mandatory action failure sets success=False, stops remaining actions, skips side effects
  - [x] 5.3 Side effect failure logs in failures but keeps success=True
  - [x] 5.4 Unknown action names treated as error

- [x] 6. Implement audit logging
  - [x] 6.1 Create `audit.py` with `write_workflow_audit(ctx)` function using `WORKFLOW_AUDIT:` prefix with JSON payload via print()
  - [x] 6.2 Include: timestamp, event_type, entity_type, entity_id, workflow, old_state, new_state, event, user_email, actions_executed, side_effects_executed, failures, severity
  - [x] 6.3 Follow same pattern as existing ACCESS_AUDIT and AUDIT_LOG

- [x] 7. Define membership workflow
  - [x] 7.1 Create `membership.py` with MEMBERSHIP_TRANSITIONS list containing: applied→pending (SUBMIT, side effects: send_application_received, audit_log), pending→wait_payment (APPROVE), wait_payment→active (PAYMENT_RECEIVED, actions: activate_member, mark_invoice_paid), active→cancelled (CANCEL, actions: deactivate_member), active→suspended (SUSPEND, guard: requires_reason, actions: suspend_member)
  - [x] 7.2 Create `membership_engine` instance

- [x] 8. Define order workflow
  - [x] 8.1 Create `orders.py` with ORDER_TRANSITIONS list containing: draft→submitted (SUBMIT, guard: has_stock_available), submitted→paid (PAYMENT_RECEIVED), paid→fulfilled (FULFILL), submitted→cancelled (CANCEL), paid→refunded (REFUND, guard: is_refundable)
  - [x] 8.2 Create `order_engine` instance

- [x] 9. Unit tests for WorkflowEngine
  - [x] 9.1 Create `backend/tests/unit/test_workflow_engine.py` testing: valid transitions return success=True with correct new_state, invalid transitions return success=False with error, guards that block return success=False, guards that allow return success=True, get_allowed_events returns correct events, engine never raises exceptions regardless of input

- [x] 10. Unit tests for ActionDispatcher
  - [x] 10.1 Create `backend/tests/unit/test_workflow_dispatcher.py` testing: all mandatory actions succeed, mandatory action failure stops execution and skips side effects, side effect failure is non-blocking, unknown mandatory action is error, unknown side effect is logged, register and register_many work correctly

- [x] 11. Property-based tests (Hypothesis)
  - [x] 11.1 Create `backend/tests/unit/test_workflow_engine_properties.py` with properties: engine.execute() never raises regardless of input, always returns TransitionResult with correct types, success=True implies new_state is not None, success=False implies new_state is None, get_allowed_events() never raises

- [x] 12. Run all tests and verify
  - [x] 12.1 Run all three test files with pytest and verify they pass
  - [x] 12.2 Verify imports work correctly (`from shared.workflows import ...`)
  - [x] 12.3 Verify Pyright finds no type errors in the workflows module

## Notes

- The engine lives in the shared Lambda Layer alongside auth_utils.py, so it's available to all handlers without extra dependencies.
- No AWS SDK imports in engine.py or dispatcher.py — they are pure Python logic. Only audit.py uses print() for CloudWatch (no boto3 needed).
- Tests use direct imports since the workflows module doesn't have the same `app.py` naming conflict described in testing conventions.
- Property tests use Hypothesis (already in backend dev dependencies).
