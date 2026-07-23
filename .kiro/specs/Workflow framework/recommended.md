# Recommended Approach: Lightweight Workflow Engine

## Summary

A self-built, minimal state machine engine (~150-200 lines Python) that lives in the shared Lambda layer. No external dependencies, no cold start penalty, fully testable, and configurable per workflow.

Key design choices:

- **Mandatory vs optional actions** — prevents inconsistent state on partial failures
- **StrEnum for events and states** — no magic strings, type-safe
- **Named functions** — debuggable at scale, no lambdas
- **TransitionResult dataclass** — rich return type instead of tuples

## Architecture

```text
Handler (Lambda)
    │
    ▼
WorkflowEngine (shared layer)
    │
    ├── Transition definitions (config)
    │     - from_state, to_state, event, guard, actions, side_effects
    │
    ├── can_transition() → validates if event is allowed
    │
    └── execute() → returns TransitionResult
          │
          ▼
    ActionDispatcher (shared layer)
          │
          ├── Mandatory actions (must all succeed, or rollback)
          │     ├── activate_member → DynamoDB
          │     └── mark_invoice_paid → DynamoDB
          │
          └── Side effects (best-effort, failures logged)
                ├── send_welcome_email → SES
                └── audit_log → DynamoDB / CloudWatch
```

## Design Principles

1. **Engine knows nothing about AWS** — it only evaluates transitions and returns results
2. **Actions are registered separately** — a dict of `name → callable`, keeps side effects decoupled
3. **Workflow definitions are data, not code** — lists of Transition dicts, easy to read and test
4. **Guards are named functions** — no lambdas, debuggable stack traces at scale
5. **Mandatory actions vs side effects** — if a mandatory action fails, the transition is rolled back
6. **Status field stays on the entity** — no separate WorkflowInstances table needed at this scale
7. **StrEnum everywhere** — events and states are typed, IDE autocomplete works, typos caught at compile time

## Core Types

```python
# shared/workflows/types.py

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict, Callable, NotRequired


class Transition(TypedDict):
    from_state: str
    to_state: str
    event: str
    guard: NotRequired[Callable[[dict], bool] | None]
    actions: list[str]          # MUST all succeed — rollback if any fails
    side_effects: list[str]     # Best-effort — failures logged, don't block transition


@dataclass
class TransitionResult:
    """Rich result object from a workflow transition attempt."""
    success: bool
    old_state: str
    new_state: str | None
    event: str
    actions_executed: list[str] = field(default_factory=list)
    side_effects_executed: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    error: str | None = None
```

## State & Event Enums

```python
# shared/workflows/states.py

from enum import StrEnum


class MemberState(StrEnum):
    PENDING = 'pending'
    WAIT_PAYMENT = 'wait_payment'
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    SUSPENDED = 'suspended'


class MemberEvent(StrEnum):
    APPROVE = 'APPROVE'
    PAYMENT_RECEIVED = 'PAYMENT_RECEIVED'
    CANCEL = 'CANCEL'
    SUSPEND = 'SUSPEND'
    REACTIVATE = 'REACTIVATE'


class OrderState(StrEnum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    PAID = 'paid'
    FULFILLED = 'fulfilled'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'


class OrderEvent(StrEnum):
    SUBMIT = 'SUBMIT'
    PAYMENT_RECEIVED = 'PAYMENT_RECEIVED'
    FULFILL = 'FULFILL'
    CANCEL = 'CANCEL'
    REFUND = 'REFUND'
```

## Engine Implementation

```python
# shared/workflows/engine.py

import logging
from .types import Transition, TransitionResult

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Lightweight state machine engine. No dependencies, no magic."""

    def __init__(self, transitions: list[Transition]):
        self._transitions = transitions

    def get_allowed_events(self, current_state: str) -> list[str]:
        """Return all events that are valid from the current state."""
        return list({
            t['event'] for t in self._transitions
            if t['from_state'] == current_state
        })

    def can_transition(self, current_state: str, event: str, context: dict | None = None) -> Transition | None:
        """Check if a transition is allowed. Returns the transition or None."""
        context = context or {}
        for t in self._transitions:
            if t['from_state'] == current_state and t['event'] == event:
                guard = t.get('guard')
                if guard is None or guard(context):
                    return t
        return None

    def execute(self, current_state: str, event: str, context: dict | None = None) -> TransitionResult:
        """
        Attempt a state transition.

        Returns a TransitionResult with full details about what happened.
        """
        context = context or {}
        transition = self.can_transition(current_state, event, context)

        if not transition:
            return TransitionResult(
                success=False,
                old_state=current_state,
                new_state=None,
                event=event,
                error=f"Transition '{event}' not allowed from state '{current_state}'",
            )

        return TransitionResult(
            success=True,
            old_state=current_state,
            new_state=transition['to_state'],
            event=event,
            # actions and side_effects are populated by the dispatcher after execution
        )
```

## Action Dispatcher

```python
# shared/workflows/dispatcher.py

import logging
from .types import Transition, TransitionResult

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """
    Executes workflow actions with mandatory/optional distinction.

    Mandatory actions (Transition.actions): ALL must succeed.
    If any fails, the transition should be rolled back.

    Side effects (Transition.side_effects): best-effort.
    Failures are logged but don't invalidate the transition.
    """

    def __init__(self):
        self._registry: dict[str, callable] = {}

    def register(self, name: str, fn: callable) -> None:
        """Register a named action function."""
        self._registry[name] = fn

    def register_many(self, actions: dict[str, callable]) -> None:
        """Register multiple actions at once."""
        self._registry.update(actions)

    def execute_transition(self, transition: Transition, result: TransitionResult, context: dict) -> TransitionResult:
        """
        Execute all actions for a transition. Updates the result in-place.

        If a mandatory action fails:
        - result.success = False
        - result.new_state = None (caller should not update DB)
        - remaining mandatory actions are skipped
        - side effects are skipped entirely

        If a side effect fails:
        - result.success remains True
        - failure is logged in result.failures
        """
        # Execute mandatory actions
        for action_name in transition['actions']:
            if action_name not in self._registry:
                result.success = False
                result.new_state = None
                result.failures.append(f"Unknown mandatory action: {action_name}")
                result.error = f"Mandatory action '{action_name}' not registered"
                return result

            try:
                self._registry[action_name](context)
                result.actions_executed.append(action_name)
            except Exception as e:
                logger.error(f"Mandatory action '{action_name}' failed: {e}")
                result.success = False
                result.new_state = None
                result.failures.append(f"{action_name}: {e}")
                result.error = f"Mandatory action '{action_name}' failed: {e}"
                return result  # Stop — don't run side effects

        # Execute side effects (best-effort)
        for effect_name in transition.get('side_effects', []):
            if effect_name not in self._registry:
                result.failures.append(f"Unknown side effect: {effect_name}")
                logger.warning(f"Side effect '{effect_name}' not registered, skipping")
                continue

            try:
                self._registry[effect_name](context)
                result.side_effects_executed.append(effect_name)
            except Exception as e:
                logger.warning(f"Side effect '{effect_name}' failed (non-blocking): {e}")
                result.failures.append(f"{effect_name}: {e}")

        return result
```

## Guard Functions (named, not lambdas)

```python
# shared/workflows/guards.py

"""
Named guard functions for workflow transitions.

Each guard takes a context dict and returns True if the transition is allowed.
Named functions provide debuggable stack traces and clear intent.
"""


def requires_reason(ctx: dict) -> bool:
    """Guard: transition requires a 'reason' field in context."""
    return ctx.get('reason') is not None


def has_valid_payment(ctx: dict) -> bool:
    """Guard: context must contain a confirmed payment reference."""
    return bool(ctx.get('payment_id')) and ctx.get('payment_status') == 'confirmed'


def has_stock_available(ctx: dict) -> bool:
    """Guard: all items in the order must have sufficient stock."""
    items = ctx.get('items', [])
    return all(item.get('stock_available', 0) >= item.get('quantity', 0) for item in items)


def is_refundable(ctx: dict) -> bool:
    """Guard: order was paid less than 14 days ago."""
    from datetime import datetime, timedelta
    paid_at = ctx.get('paid_at')
    if not paid_at:
        return False
    if isinstance(paid_at, str):
        paid_at = datetime.fromisoformat(paid_at)
    return datetime.now() - paid_at < timedelta(days=14)
```

## Example: Membership Workflow

```python
# shared/workflows/membership.py

from .types import Transition
from .states import MemberState, MemberEvent
from .guards import requires_reason
from .engine import WorkflowEngine

MEMBERSHIP_TRANSITIONS: list[Transition] = [
    {
        'from_state': MemberState.PENDING,
        'to_state': MemberState.WAIT_PAYMENT,
        'event': MemberEvent.APPROVE,
        'actions': [],
        'side_effects': ['send_payment_request', 'audit_log'],
    },
    {
        'from_state': MemberState.WAIT_PAYMENT,
        'to_state': MemberState.ACTIVE,
        'event': MemberEvent.PAYMENT_RECEIVED,
        'actions': ['activate_member', 'mark_invoice_paid'],
        'side_effects': ['send_welcome_email', 'audit_log'],
    },
    {
        'from_state': MemberState.ACTIVE,
        'to_state': MemberState.CANCELLED,
        'event': MemberEvent.CANCEL,
        'actions': ['deactivate_member'],
        'side_effects': ['send_cancellation_email', 'audit_log'],
    },
    {
        'from_state': MemberState.ACTIVE,
        'to_state': MemberState.SUSPENDED,
        'event': MemberEvent.SUSPEND,
        'guard': requires_reason,
        'actions': ['suspend_member'],
        'side_effects': ['send_suspension_notice', 'audit_log'],
    },
]

membership_engine = WorkflowEngine(MEMBERSHIP_TRANSITIONS)
```

## Example: Order Workflow

```python
# shared/workflows/orders.py

from .types import Transition
from .states import OrderState, OrderEvent
from .guards import has_stock_available, is_refundable
from .engine import WorkflowEngine

ORDER_TRANSITIONS: list[Transition] = [
    {
        'from_state': OrderState.DRAFT,
        'to_state': OrderState.SUBMITTED,
        'event': OrderEvent.SUBMIT,
        'guard': has_stock_available,
        'actions': ['reserve_stock'],
        'side_effects': ['send_order_confirmation', 'audit_log'],
    },
    {
        'from_state': OrderState.SUBMITTED,
        'to_state': OrderState.PAID,
        'event': OrderEvent.PAYMENT_RECEIVED,
        'actions': ['mark_paid'],
        'side_effects': ['audit_log'],
    },
    {
        'from_state': OrderState.PAID,
        'to_state': OrderState.FULFILLED,
        'event': OrderEvent.FULFILL,
        'actions': ['decrement_stock', 'generate_invoice_pdf'],
        'side_effects': ['send_shipping_notification', 'audit_log'],
    },
    {
        'from_state': OrderState.SUBMITTED,
        'to_state': OrderState.CANCELLED,
        'event': OrderEvent.CANCEL,
        'actions': ['release_stock'],
        'side_effects': ['send_cancellation_email', 'audit_log'],
    },
    {
        'from_state': OrderState.PAID,
        'to_state': OrderState.REFUNDED,
        'event': OrderEvent.REFUND,
        'guard': is_refundable,
        'actions': ['process_refund', 'release_stock'],
        'side_effects': ['send_refund_email', 'audit_log'],
    },
]

order_engine = WorkflowEngine(ORDER_TRANSITIONS)
```

## Defining & Updating Workflows

### Workflows are Python code, not JSON or database config

Transitions, states, events, and guards are all defined in Python files within the shared layer. This is a deliberate choice:

| Approach                       | Pros                                                          | Cons                                                             |
| ------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Python files** (this design) | Type-checked, IDE support, git history, testable, code review | Requires deploy to change                                        |
| JSON files                     | Editable without code changes                                 | No type checking, no IDE support, easy to break silently         |
| DynamoDB config                | Runtime-editable, no deploy                                   | No version control, no type safety, hard to test, migration risk |

For H-DCN (5-10 workflows, changes monthly at most, single tenant), Python-as-config wins decisively.

### Adding a new workflow

1. Add states and events to `states.py`:

```python
# shared/workflows/states.py

class EventRegState(StrEnum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CHECKED_IN = 'checked_in'
    CANCELLED = 'cancelled'

class EventRegEvent(StrEnum):
    CONFIRM = 'CONFIRM'
    SCAN_TICKET = 'SCAN_TICKET'
    CANCEL = 'CANCEL'
```

2. Add guard functions to `guards.py` (if needed):

```python
# shared/workflows/guards.py

def has_available_spots(ctx: dict) -> bool:
    """Guard: event must have spots remaining."""
    return ctx.get('spots_remaining', 0) > 0
```

3. Create the workflow file:

```python
# shared/workflows/event_registration.py

from .types import Transition
from .states import EventRegState, EventRegEvent
from .guards import has_available_spots
from .engine import WorkflowEngine

EVENT_REGISTRATION_TRANSITIONS: list[Transition] = [
    {
        'from_state': EventRegState.PENDING,
        'to_state': EventRegState.CONFIRMED,
        'event': EventRegEvent.CONFIRM,
        'guard': has_available_spots,
        'actions': ['reserve_spot'],
        'side_effects': ['send_confirmation_email', 'audit_log'],
    },
    {
        'from_state': EventRegState.CONFIRMED,
        'to_state': EventRegState.CANCELLED,
        'event': EventRegEvent.CANCEL,
        'actions': ['release_spot'],
        'side_effects': ['send_cancellation_email', 'audit_log'],
    },
]

event_registration_engine = WorkflowEngine(EVENT_REGISTRATION_TRANSITIONS)
```

4. Register actions in the handler that uses it.
5. Add tests.
6. Deploy.

### Modifying an existing workflow

**Adding a transition** — append to the list, add StrEnum value if new event/state:

```python
# Add REINSTATE to membership workflow
class MemberEvent(StrEnum):
    # ... existing ...
    REINSTATE = 'REINSTATE'

# In membership.py, add to MEMBERSHIP_TRANSITIONS:
{
    'from_state': MemberState.CANCELLED,
    'to_state': MemberState.ACTIVE,
    'event': MemberEvent.REINSTATE,
    'guard': has_valid_payment,
    'actions': ['activate_member', 'mark_invoice_paid'],
    'side_effects': ['send_welcome_back_email', 'audit_log'],
},
```

**Changing actions** — edit the transition dict directly:

```python
# Before: fulfilment only decremented stock
'actions': ['decrement_stock'],

# After: added mandatory invoice generation
'actions': ['decrement_stock', 'generate_invoice_pdf'],
```

**Adding a guard** — write the function in `guards.py`, reference it in the transition:

```python
# In guards.py
def is_within_cancellation_window(ctx: dict) -> bool:
    """Guard: order can only be cancelled within 24h of submission."""
    from datetime import datetime, timedelta
    submitted_at = ctx.get('submitted_at')
    if not submitted_at:
        return False
    if isinstance(submitted_at, str):
        submitted_at = datetime.fromisoformat(submitted_at)
    return datetime.now() - submitted_at < timedelta(hours=24)

# In orders.py — add guard to the CANCEL transition
{
    'from_state': OrderState.SUBMITTED,
    'to_state': OrderState.CANCELLED,
    'event': OrderEvent.CANCEL,
    'guard': is_within_cancellation_window,  # NEW
    'actions': ['release_stock'],
    'side_effects': ['send_cancellation_email', 'audit_log'],
},
```

**Removing a transition** — delete it from the list. The engine returns "not allowed" for that event/state combination.

### The change process

```text
1. Edit transitions / states / guards in the shared layer
2. Pyright catches type errors immediately (wrong StrEnum values, missing fields)
3. Run unit + property tests (catches broken transition logic)
4. Code review (git diff shows exactly what changed)
5. Deploy (sam build + sam deploy)
6. CloudWatch WORKFLOW_AUDIT confirms new transitions are firing
```

### Why not JSON or DynamoDB?

The ChatGPT recommendation suggested "configurable from DynamoDB or JSON files." That makes sense for multi-tenant SaaS where customers define their own workflows at runtime. For H-DCN:

- Workflows change rarely (monthly at most)
- There's one tenant
- A deploy takes ~3 minutes
- Type safety and testability outweigh runtime flexibility
- Git blame tells you who changed a workflow and why

If multi-tenancy becomes real, the upgrade path is clear: move transition definitions to DynamoDB, keep the engine code unchanged. But that's a future concern.

## Usage in a Handler

```python
# handler/confirm_payment/app.py

from shared.workflows.engine import WorkflowEngine
from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.membership import membership_engine
from shared.workflows.states import MemberEvent

# Register concrete action implementations (named functions)
dispatcher = ActionDispatcher()
dispatcher.register_many({
    'activate_member': activate_member_in_db,
    'mark_invoice_paid': mark_invoice_as_paid,
    'send_welcome_email': send_welcome_email,
    'send_payment_request': send_payment_request_email,
    'audit_log': write_audit_log,
})


def lambda_handler(event, context):
    # ... auth, parse body ...

    member = get_member(member_id)
    current_state = member.get('status', 'unknown')

    # Attempt transition
    result = membership_engine.execute(
        current_state=current_state,
        event=MemberEvent.PAYMENT_RECEIVED,
        context={'member_id': member_id, 'email': member['email'], 'invoice_id': invoice_id},
    )

    if not result.success:
        return create_error_response(400, result.error)

    # Find the transition to get actions/side_effects
    transition = membership_engine.can_transition(
        current_state, MemberEvent.PAYMENT_RECEIVED,
        {'member_id': member_id, 'email': member['email'], 'invoice_id': invoice_id},
    )

    # Execute actions (mandatory + side effects)
    action_context = {
        'member_id': member_id,
        'email': member['email'],
        'invoice_id': invoice_id,
    }
    result = dispatcher.execute_transition(transition, result, action_context)

    if not result.success:
        # Mandatory action failed — state was NOT updated
        return create_error_response(500, result.error)

    # All mandatory actions succeeded — now persist the state change
    update_member_status(member_id, result.new_state)

    # Log side effect failures (non-blocking)
    if result.failures:
        logger.warning(f"Side effect failures for member {member_id}: {result.failures}")

    return create_success_response({
        'status': result.new_state,
        'actions': result.actions_executed,
    })
```

**Key pattern**: state is only persisted in DynamoDB AFTER mandatory actions succeed. This prevents the inconsistent state problem.

## Trigger Patterns: How Transitions Are Invoked

The engine is **passive** — it doesn't listen for events or subscribe to queues. Handlers call it explicitly. There are three trigger patterns:

### Pattern 1: User action via API (most common)

A user clicks a button in the portal → frontend calls an API endpoint → the handler fires the event.

```text
Frontend: "Approve Member" button
    → POST /members/{id}/approve
    → approve_member handler
    → membership_engine.execute(current_state, MemberEvent.APPROVE, context)
```

Each handler has a **fixed event** it fires. The `approve_member` handler always fires `APPROVE`. The `cancel_membership` handler always fires `CANCEL`. There's no ambiguity.

```python
# handler/approve_member/app.py
def lambda_handler(event, context):
    # auth + parse
    member = get_member(member_id)
    result = membership_engine.execute(member['status'], MemberEvent.APPROVE, ctx)
    # ...
```

### Pattern 2: External webhook (system-initiated)

An external service (Stripe, iDEAL, payment provider) calls your webhook endpoint.

```text
Stripe: payment_intent.succeeded
    → POST /webhooks/stripe
    → stripe_webhook handler
    → Lookup order by payment_intent_id
    → order_engine.execute(order['status'], OrderEvent.PAYMENT_RECEIVED, context)
```

```python
# handler/stripe_webhook/app.py
def lambda_handler(event, context):
    payload = parse_stripe_event(event)
    if payload['type'] == 'payment_intent.succeeded':
        order = find_order_by_payment(payload['payment_intent_id'])
        result = order_engine.execute(order['status'], OrderEvent.PAYMENT_RECEIVED, {
            'order_id': order['order_id'],
            'payment_id': payload['payment_intent_id'],
            'amount': payload['amount'],
        })
        # ...
```

### Pattern 3: Scheduled trigger (time-based)

A CloudWatch Events rule fires on a schedule → Lambda checks for entities that need a transition.

```text
CloudWatch Schedule: daily at 02:00
    → check_expired_memberships handler
    → Scan for members where expiry_date < today AND status = 'active'
    → For each: membership_engine.execute('active', MemberEvent.EXPIRE, context)
```

```python
# handler/check_expired_memberships/app.py
def lambda_handler(event, context):
    expired = scan_expired_members()
    results = []
    for member in expired:
        result = membership_engine.execute(member['status'], MemberEvent.EXPIRE, {
            'member_id': member['member_id'],
            'reason': 'Membership expired',
        })
        if result.success:
            dispatcher.execute_transition(...)
            update_member_status(member['member_id'], result.new_state)
        results.append(result)
    return {'processed': len(results), 'failed': sum(1 for r in results if not r.success)}
```

### One event, multiple entities?

If a single real-world event needs to update multiple entities (e.g., payment received updates both Order AND Membership):

**Option A: Sequential in one handler (simple, fine for now)**

```python
# handler/stripe_webhook/app.py
order_result = order_engine.execute(order['status'], OrderEvent.PAYMENT_RECEIVED, ctx)
member_result = membership_engine.execute(member['status'], MemberEvent.PAYMENT_RECEIVED, ctx)
```

**Option B: Async fan-out (when it gets complex)**

```python
# handler/stripe_webhook/app.py — fires two separate Lambdas
lambda_client.invoke(FunctionName='process_order_payment', InvocationType='Event', Payload=...)
lambda_client.invoke(FunctionName='activate_membership', InvocationType='Event', Payload=...)
```

**Option C: EventBridge (when you need decoupling at scale)**

```python
# handler/stripe_webhook/app.py — publish event, let subscribers react
eventbridge.put_events(Entries=[{
    'Source': 'h-dcn.payments',
    'DetailType': 'PaymentReceived',
    'Detail': json.dumps({'order_id': '...', 'member_id': '...', 'amount': ...})
}])
```

Start with Option A. Move to B when the handler gets too long. Move to C only if multiple independent services need to react.

### Summary: Where does each event originate?

| Event              | Trigger                | Handler                     |
| ------------------ | ---------------------- | --------------------------- |
| `APPROVE`          | Admin clicks button    | `approve_member`            |
| `PAYMENT_RECEIVED` | Stripe webhook         | `stripe_webhook`            |
| `CANCEL`           | Member or admin action | `cancel_membership`         |
| `SUSPEND`          | Admin action           | `suspend_member`            |
| `EXPIRE`           | Daily scheduled check  | `check_expired_memberships` |
| `SUBMIT`           | Member submits order   | `submit_order`              |
| `FULFILL`          | Admin marks shipped    | `fulfill_order`             |
| `REFUND`           | Admin initiates refund | `refund_order`              |

The handler IS the trigger. No event bus, no queue, no middleware. If you need to trace "who fired this transition?", you look at the handler.

## Where This Lives in the Codebase

```
backend/layers/auth-layer/python/shared/
├── auth_utils.py                  # Existing
├── maintenance_fallback.py        # Existing
└── workflows/                     # NEW
    ├── __init__.py
    ├── types.py                   # Transition, TransitionResult
    ├── states.py                  # StrEnum classes for all states/events
    ├── guards.py                  # Named guard functions
    ├── engine.py                  # WorkflowEngine class
    ├── dispatcher.py              # ActionDispatcher class
    ├── membership.py              # Membership transition config
    └── orders.py                  # Order transition config
```

## Testing Strategy

### Unit tests (pure logic, no AWS)

```python
from shared.workflows.engine import WorkflowEngine
from shared.workflows.membership import MEMBERSHIP_TRANSITIONS, membership_engine
from shared.workflows.states import MemberState, MemberEvent


def test_valid_transition():
    result = membership_engine.execute(MemberState.WAIT_PAYMENT, MemberEvent.PAYMENT_RECEIVED, {})
    assert result.success is True
    assert result.new_state == MemberState.ACTIVE
    assert result.old_state == MemberState.WAIT_PAYMENT
    assert result.error is None


def test_invalid_transition():
    result = membership_engine.execute(MemberState.PENDING, MemberEvent.PAYMENT_RECEIVED, {})
    assert result.success is False
    assert result.new_state is None
    assert result.error is not None


def test_guard_blocks_transition():
    result = membership_engine.execute(MemberState.ACTIVE, MemberEvent.SUSPEND, {})
    assert result.success is False  # No reason provided


def test_guard_allows_transition():
    result = membership_engine.execute(MemberState.ACTIVE, MemberEvent.SUSPEND, {'reason': 'Non-payment'})
    assert result.success is True
    assert result.new_state == MemberState.SUSPENDED


def test_get_allowed_events():
    events = membership_engine.get_allowed_events(MemberState.ACTIVE)
    assert MemberEvent.CANCEL in events
    assert MemberEvent.SUSPEND in events
    assert MemberEvent.APPROVE not in events
```

### Dispatcher tests (with mocks)

```python
from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.types import Transition, TransitionResult


def test_mandatory_action_failure_blocks_transition():
    dispatcher = ActionDispatcher()
    dispatcher.register('will_fail', lambda ctx: (_ for _ in ()).throw(RuntimeError("DB error")))
    dispatcher.register('should_not_run', lambda ctx: None)

    transition: Transition = {
        'from_state': 'a', 'to_state': 'b', 'event': 'X',
        'actions': ['will_fail', 'should_not_run'],
        'side_effects': ['also_should_not_run'],
    }
    result = TransitionResult(success=True, old_state='a', new_state='b', event='X')
    result = dispatcher.execute_transition(transition, result, {})

    assert result.success is False
    assert result.new_state is None
    assert 'will_fail' in result.failures[0]
    assert 'should_not_run' not in result.actions_executed


def test_side_effect_failure_does_not_block():
    calls = []
    dispatcher = ActionDispatcher()
    dispatcher.register('mandatory_ok', lambda ctx: calls.append('mandatory'))
    dispatcher.register('effect_fails', lambda ctx: (_ for _ in ()).throw(RuntimeError("SES down")))

    transition: Transition = {
        'from_state': 'a', 'to_state': 'b', 'event': 'X',
        'actions': ['mandatory_ok'],
        'side_effects': ['effect_fails'],
    }
    result = TransitionResult(success=True, old_state='a', new_state='b', event='X')
    result = dispatcher.execute_transition(transition, result, {})

    assert result.success is True
    assert result.new_state == 'b'
    assert 'mandatory_ok' in result.actions_executed
    assert len(result.failures) == 1  # Side effect failure logged
```

### Property tests (Hypothesis)

```python
from hypothesis import given, strategies as st
from shared.workflows.engine import WorkflowEngine
from shared.workflows.membership import MEMBERSHIP_TRANSITIONS


@given(state=st.text(min_size=1), event=st.text(min_size=1))
def test_engine_never_crashes(state, event):
    """Engine always returns a valid TransitionResult, never raises."""
    engine = WorkflowEngine(MEMBERSHIP_TRANSITIONS)
    result = engine.execute(state, event, {})
    assert isinstance(result.success, bool)
    if result.success:
        assert result.new_state is not None
        assert result.error is None
    else:
        assert result.new_state is None
        assert result.error is not None


@given(state=st.sampled_from(['pending', 'wait_payment', 'active', 'cancelled', 'suspended']))
def test_allowed_events_are_all_valid(state):
    """Every event returned by get_allowed_events must produce a successful transition."""
    engine = WorkflowEngine(MEMBERSHIP_TRANSITIONS)
    events = engine.get_allowed_events(state)
    for event in events:
        # Some transitions have guards, so we provide a permissive context
        result = engine.execute(state, event, {'reason': 'test', 'payment_id': 'x', 'payment_status': 'confirmed'})
        assert result.success, f"Event '{event}' from '{state}' should succeed but got: {result.error}"
```

## Failure Handling: The Full Picture

```text
PAYMENT_RECEIVED event arrives
    │
    ▼
Engine: Is transition allowed?
    │
    ├── NO → return error (400)
    │
    └── YES → proceed
          │
          ▼
    Dispatcher: Run mandatory actions
          │
          ├── activate_member() → OK ✓
          ├── mark_invoice_paid() → FAILED ✗
          │
          └── STOP. result.success = False, result.new_state = None
                │
                ▼
          Handler: Do NOT update DynamoDB status
          Handler: Return 500 with error details
          Handler: (Optional) Rollback activate_member if needed

---

If all mandatory actions succeed:

    Dispatcher: Run side effects
          │
          ├── send_welcome_email() → OK ✓
          ├── audit_log() → FAILED ✗ (SES/CW hiccup)
          │
          └── Continue. result.success stays True.
                │
                ▼
          Handler: Update DynamoDB status to ACTIVE
          Handler: Log side effect failures for retry/monitoring
          Handler: Return 200
```

## Audit What are then current workflows ng Strategy

### Current State: Existing Log Prefixes

The codebase already uses structured `print()` → CloudWatch Logs with these prefixes:

| Prefix                   | Source                                          | Purpose                     |
| ------------------------ | ----------------------------------------------- | --------------------------- |
| `ACCESS_AUDIT:`          | `auth_utils.py` → `log_successful_access()`     | Auth access granted events  |
| `REGIONAL_ACCESS_AUDIT:` | `auth_utils.py` → `log_regional_access_event()` | Regional data access checks |
| `AUDIT_LOG:`             | `update_member/field_validation.py`             | Field update tracking       |

All follow the same pattern: `print(f"PREFIX: {json.dumps(structured_dict)}")` — ends up in CloudWatch Logs, queryable via CloudWatch Insights.

### New Prefix for Workflow Transitions

The workflow engine adds one new prefix:

| Prefix            | Source                                          | Purpose           |
| ----------------- | ----------------------------------------------- | ----------------- |
| `WORKFLOW_AUDIT:` | `workflows/audit.py` → `write_workflow_audit()` | State transitions |

### Unified Log Structure

All audit log entries share a common base structure:

```python
{
    "timestamp": "2026-07-21T14:30:00.000000",
    "event_type": "...",            # Specific event identifier
    "user_email": "user@h-dcn.nl",  # Who triggered it (or 'system' for scheduled)
    "severity": "INFO",             # INFO, WARNING, ERROR
}
```

### Workflow Audit Implementation

```python
# shared/workflows/audit.py

import json
from datetime import datetime


def write_workflow_audit(ctx: dict) -> None:
    """
    Audit log for workflow state transitions. Stored in CloudWatch Logs.

    Uses the same print-to-CloudWatch pattern as ACCESS_AUDIT and AUDIT_LOG.
    Queryable via CloudWatch Insights:
        fields @timestamp, @message
        | filter @message like /WORKFLOW_AUDIT/
        | parse @message "WORKFLOW_AUDIT: *" as audit_json
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'WORKFLOW_TRANSITION',
        'entity_type': ctx.get('entity_type'),          # 'member', 'order'
        'entity_id': ctx.get('entity_id'),              # member_id, order_id
        'workflow': ctx.get('workflow'),                 # 'membership', 'order'
        'old_state': ctx.get('old_state'),
        'new_state': ctx.get('new_state'),
        'event': ctx.get('event'),                      # MemberEvent/OrderEvent value
        'user_email': ctx.get('user_email', 'system'),
        'actions_executed': ctx.get('actions_executed', []),
        'side_effects_executed': ctx.get('side_effects_executed', []),
        'failures': ctx.get('failures', []),
        'severity': 'WARNING' if ctx.get('failures') else 'INFO',
    }

    print(f"WORKFLOW_AUDIT: {json.dumps(log_entry)}")
```

### How It Integrates with the Dispatcher

The `audit_log` action in every transition's `side_effects` list calls `write_workflow_audit`. The dispatcher automatically enriches the context with transition result data:

```python
# In the handler, after dispatcher.execute_transition():
dispatcher.register('audit_log', lambda ctx: write_workflow_audit({
    **ctx,
    'old_state': result.old_state,
    'new_state': result.new_state,
    'event': result.event,
    'actions_executed': result.actions_executed,
    'side_effects_executed': result.side_effects_executed,
    'failures': result.failures,
}))
```

### Complete Audit Prefix Inventory

After implementation, the project has these structured log types:

| Prefix                   | Fires on                     | Typical volume        |
| ------------------------ | ---------------------------- | --------------------- |
| `ACCESS_AUDIT:`          | Every authenticated API call | High (~every request) |
| `REGIONAL_ACCESS_AUDIT:` | Regional data access checks  | Medium                |
| `AUDIT_LOG:`             | Member field updates         | Low (admin actions)   |
| `WORKFLOW_AUDIT:`        | State transitions            | Low (business events) |

### CloudWatch Insights Queries

```sql
-- All workflow transitions for a specific member
fields @timestamp, @message
| filter @message like /WORKFLOW_AUDIT/
| parse @message "WORKFLOW_AUDIT: *" as audit
| filter audit.entity_id = "member_123"
| sort @timestamp desc

-- Failed side effects in the last 24h
fields @timestamp, @message
| filter @message like /WORKFLOW_AUDIT/
| parse @message "WORKFLOW_AUDIT: *" as audit
| filter audit.severity = "WARNING"
| sort @timestamp desc

-- Transition frequency by event type
fields @timestamp, @message
| filter @message like /WORKFLOW_AUDIT/
| parse @message "WORKFLOW_AUDIT: *" as audit
| stats count() by audit.event
```

### Decision: Why CloudWatch, Not a DynamoDB Table

| Consideration            | CloudWatch                                    | DynamoDB AuditLog table     |
| ------------------------ | --------------------------------------------- | --------------------------- |
| Cost                     | Free (included in Lambda)                     | Extra writes per transition |
| Setup                    | Zero (print = done)                           | New table + IAM permissions |
| Query                    | CloudWatch Insights (SQL-like)                | Scan/Query with filters     |
| Retention                | Configurable (default 30 days, set to 1 year) | Unlimited                   |
| Matches existing pattern | ✅ Same as ACCESS_AUDIT                       | ❌ New pattern              |
| Frontend queryable       | ❌ Not directly                               | ✅ Via API endpoint         |

**Decision**: Stay with CloudWatch. Add a DynamoDB table only if/when:

- The frontend needs to display an audit trail to admins
- Regulatory requirements demand structured retention beyond CloudWatch
- You need cross-entity audit queries that CloudWatch Insights can't handle efficiently

### Retention Configuration

Set CloudWatch log group retention to 365 days for Lambda functions that emit workflow audits:

```yaml
# In template.yaml — per function log group
ConfirmPaymentLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub "/aws/lambda/${ConfirmPaymentFunction}"
    RetentionInDays: 365
```

## What This Does NOT Cover (by design)

- **Parallel workflows** — not needed; one entity has one status
- **Long-running sagas with compensation** — use Step Functions if this ever becomes needed
- **User-configurable workflows via admin UI** — out of scope for now; admin edits code/config
- **Workflow versioning** — transitions are simple enough to evolve in-place
- **Multi-tenancy / workflow_name on entities** — deferred until SaaS is on the roadmap; architecture supports it without changes (just instantiate different engine per tenant)
- **Before/after hooks** — guards handle "before" checks; side_effects handle "after" work; adding a third layer is premature

## Future: WorkflowService Facade (extract when needed)

Once 3+ handlers repeat the same engine + dispatcher + persist pattern, extract:

```python
# shared/workflows/service.py (FUTURE — don't build yet)

class WorkflowService:
    def __init__(self, engine: WorkflowEngine, dispatcher: ActionDispatcher, persist_fn: callable):
        self._engine = engine
        self._dispatcher = dispatcher
        self._persist = persist_fn

    def process(self, entity: dict, event: str, context: dict) -> TransitionResult:
        """One-call workflow processing. Handler only sees the result."""
        current_state = entity.get('status', 'unknown')
        result = self._engine.execute(current_state, event, context)

        if not result.success:
            return result

        transition = self._engine.can_transition(current_state, event, context)
        result = self._dispatcher.execute_transition(transition, result, context)

        if result.success:
            self._persist(entity, result.new_state)

        return result
```

Handler becomes:

```python
result = membership_service.process(entity=member, event=MemberEvent.PAYMENT_RECEIVED, context=ctx)
if not result.success:
    return create_error_response(500, result.error)
return create_success_response({'status': result.new_state})
```

Extract this when the pattern repeats — not before.

## Migration Path

### Phase 1: Engine + Membership workflow

- Build the engine, types, states, guards, dispatcher in the shared layer
- Define membership transitions
- Migrate the membership approval/activation handler
- Add unit + property tests

### Phase 2: Order workflow

- Define order transitions and guards
- Migrate payment confirmation and fulfilment handlers
- Replace ad-hoc status checks with `engine.can_transition()`

### Phase 3: Frontend integration

- Expose `get_allowed_events()` in entity API responses
- Frontend uses allowed events to show/hide action buttons dynamically
- TypeScript enum mirrors for states/events

### Phase 4 (optional): WorkflowService facade

- Extract when 3+ handlers repeat the same pattern
- Single `workflow_service.process()` call per handler

## When to Reconsider

Upgrade to Step Functions or EventBridge if:

- A workflow spans more than ~5 minutes (Lambda timeout)
- You need automatic retries with exponential backoff on action failures
- Multiple independent services need to react to the same state change
- You need visual workflow monitoring/debugging in the AWS console
- Rollback logic becomes complex (compensating transactions across services)
