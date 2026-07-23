# Workflow Framework — Design

## 1. Architecture Overview

```text
Handler (Lambda)
    │
    ▼
WorkflowEngine (shared layer)
    │
    ├── Transition definitions (Python config)
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
                └── audit_log → CloudWatch (WORKFLOW_AUDIT:)
```

### Design Principles

1. **Engine knows nothing about AWS** — it only evaluates transitions and returns results
2. **Actions are registered separately** — a dict of `name → callable`, keeps side effects decoupled
3. **Workflow definitions are data, not code** — lists of Transition dicts, easy to read and test
4. **Guards are named functions** — no lambdas, debuggable stack traces at scale
5. **Mandatory actions vs side effects** — if a mandatory action fails, the transition is rolled back
6. **Status field stays on the entity** — no separate WorkflowInstances table needed at this scale
7. **StrEnum everywhere** — events and states are typed, IDE autocomplete works, typos caught at compile time

---

## 2. Module Structure

```
backend/layers/auth-layer/python/shared/
├── auth_utils.py                  # Existing
├── maintenance_fallback.py        # Existing
└── workflows/                     # NEW
    ├── __init__.py                # Re-exports engine, dispatcher, types
    ├── types.py                   # Transition TypedDict, TransitionResult dataclass
    ├── states.py                  # StrEnum classes for all states/events
    ├── guards.py                  # Named guard functions
    ├── engine.py                  # WorkflowEngine class
    ├── dispatcher.py              # ActionDispatcher class
    ├── audit.py                   # write_workflow_audit function
    ├── membership.py              # Membership transition config + engine instance
    └── orders.py                  # Order transition config + engine instance
```

---

## 3. Core Types (types.py)

```python
from dataclasses import dataclass, field
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

---

## 4. State & Event Enums (states.py)

```python
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

---

## 5. Engine (engine.py)

```python
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
        The engine only evaluates — it does NOT execute actions or persist state.
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
        )
```

---

## 6. Action Dispatcher (dispatcher.py)

```python
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

        Flow:
        1. Run mandatory actions sequentially
        2. If ANY mandatory action fails → stop, set success=False, skip side effects
        3. If all mandatory actions succeed → run side effects (best-effort)
        4. Side effect failures are logged but don't affect result.success
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

---

## 7. Guard Functions (guards.py)

```python
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

---

## 8. Audit Logging (audit.py)

```python
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
        'entity_type': ctx.get('entity_type'),
        'entity_id': ctx.get('entity_id'),
        'workflow': ctx.get('workflow'),
        'old_state': ctx.get('old_state'),
        'new_state': ctx.get('new_state'),
        'event': ctx.get('event'),
        'user_email': ctx.get('user_email', 'system'),
        'actions_executed': ctx.get('actions_executed', []),
        'side_effects_executed': ctx.get('side_effects_executed', []),
        'failures': ctx.get('failures', []),
        'severity': 'WARNING' if ctx.get('failures') else 'INFO',
    }

    print(f"WORKFLOW_AUDIT: {json.dumps(log_entry)}")
```

### Existing Audit Prefixes (for context)

| Prefix                   | Source                                          | Purpose                     |
| ------------------------ | ----------------------------------------------- | --------------------------- |
| `ACCESS_AUDIT:`          | `auth_utils.py` → `log_successful_access()`     | Auth access granted         |
| `REGIONAL_ACCESS_AUDIT:` | `auth_utils.py` → `log_regional_access_event()` | Regional data access        |
| `AUDIT_LOG:`             | `update_member/field_validation.py`             | Field update tracking       |
| `WORKFLOW_AUDIT:`        | `workflows/audit.py` → `write_workflow_audit()` | **NEW** — State transitions |

### CloudWatch Insights Queries

```sql
-- All transitions for a specific member
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

### Retention

```yaml
# In template.yaml — per function log group
ConfirmPaymentLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub "/aws/lambda/${ConfirmPaymentFunction}"
    RetentionInDays: 365
```

---

## 9. Workflow Definitions

### Membership Workflow (membership.py)

```python
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

### Order Workflow (orders.py)

```python
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

---

## 10. Trigger Patterns

The engine is **passive** — handlers invoke it. Three patterns:

### Pattern 1: User action via API

```text
Frontend button → POST /members/{id}/approve → approve_member handler → engine.execute()
```

Each handler fires a **fixed event**. No ambiguity about what triggers what.

### Pattern 2: External webhook

```text
Stripe webhook → POST /webhooks/stripe → stripe_webhook handler → engine.execute()
```

The webhook handler maps the external event type to the internal workflow event.

### Pattern 3: Scheduled (time-based)

```text
CloudWatch Schedule → check_expired_memberships handler → scan + engine.execute() per entity
```

### Multi-entity events

When one real-world event touches multiple entities:

| Approach                  | When to use                                   |
| ------------------------- | --------------------------------------------- |
| Sequential in one handler | Default — simple, easy to reason about        |
| Async Lambda invoke       | When one action is slow (PDF gen)             |
| EventBridge               | When multiple independent services must react |

Start with sequential. Upgrade only when complexity demands it.

### Event → Handler mapping

| Event              | Trigger               | Handler                              |
| ------------------ | --------------------- | ------------------------------------ |
| `APPROVE`          | Admin button          | `approve_member`                     |
| `PAYMENT_RECEIVED` | Stripe/Mollie webhook | `stripe_webhook` / `mollie_webhook`  |
| `CANCEL`           | Member or admin       | `cancel_membership` / `cancel_order` |
| `SUSPEND`          | Admin                 | `suspend_member`                     |
| `SUBMIT`           | Member checkout       | `submit_order`                       |
| `FULFILL`          | Admin marks shipped   | `fulfill_order`                      |
| `REFUND`           | Admin                 | `refund_order`                       |

---

## 11. Failure Handling Flow

```text
Event arrives at handler
    │
    ▼
Engine: Is transition allowed? (check state + guard)
    │
    ├── NO → return 400 (invalid transition)
    │
    └── YES → TransitionResult(success=True, new_state=X)
          │
          ▼
    Dispatcher: Run mandatory actions sequentially
          │
          ├── Action 1 → OK ✓ (added to actions_executed)
          ├── Action 2 → FAILED ✗
          │     └── STOP. success=False, new_state=None
          │           │
          │           ▼
          │     Handler: Do NOT persist state
          │     Handler: Return 500
          │     Handler: (Optional) compensate Action 1
          │
          └── All OK → Run side effects (best-effort)
                │
                ├── Side effect 1 → OK ✓
                ├── Side effect 2 → FAILED ✗ (logged, non-blocking)
                │
                └── result.success stays True
                      │
                      ▼
                Handler: Persist new state to DynamoDB
                Handler: Return 200
                Handler: Log any side effect failures
```

### Rollback / Compensation (v1)

In the first implementation, compensation is **handler-level, not engine-level**:

```python
result = dispatcher.execute_transition(transition, result, context)

if not result.success:
    # Check what already ran and compensate if needed
    if 'activate_member' in result.actions_executed:
        deactivate_member(context['member_id'])  # Manual rollback
    return create_error_response(500, result.error)
```

A formal compensation mechanism (declaring rollback actions per action) is future work — only justified if rollback logic becomes complex.

---

## 12. Handler Integration Pattern

```python
# handler/confirm_payment/app.py

from shared.workflows.engine import WorkflowEngine
from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.membership import membership_engine
from shared.workflows.states import MemberEvent
from shared.workflows.audit import write_workflow_audit

# Register concrete action implementations
dispatcher = ActionDispatcher()
dispatcher.register_many({
    'activate_member': activate_member_in_db,
    'mark_invoice_paid': mark_invoice_as_paid,
    'send_welcome_email': send_welcome_email,
    'send_payment_request': send_payment_request_email,
    'audit_log': write_audit_log,  # wraps write_workflow_audit with context enrichment
})


def lambda_handler(event, context):
    user_email, user_roles, error = extract_user_credentials(event)
    if error:
        return error

    body = json.loads(event.get('body', '{}'))
    member_id = body['member_id']
    member = get_member(member_id)
    current_state = member.get('status', 'unknown')

    # 1. Check if transition is allowed
    result = membership_engine.execute(
        current_state=current_state,
        event=MemberEvent.PAYMENT_RECEIVED,
        context={'member_id': member_id, 'email': member['email']},
    )

    if not result.success:
        return create_error_response(400, result.error)

    # 2. Get the transition definition (for actions/side_effects)
    transition = membership_engine.can_transition(
        current_state, MemberEvent.PAYMENT_RECEIVED,
        {'member_id': member_id, 'email': member['email']},
    )

    # 3. Execute actions
    action_context = {
        'member_id': member_id,
        'email': member['email'],
        'invoice_id': body.get('invoice_id'),
        'user_email': user_email,
        'entity_type': 'member',
        'entity_id': member_id,
        'workflow': 'membership',
    }
    result = dispatcher.execute_transition(transition, result, action_context)

    # 4. Handle result
    if not result.success:
        return create_error_response(500, result.error)

    # 5. Persist state (ONLY after mandatory actions succeed)
    update_member_status(member_id, result.new_state)

    if result.failures:
        logger.warning(f"Side effect failures: {result.failures}")

    return create_success_response({'status': result.new_state})
```

---

## 13. Defining & Updating Workflows

### Workflows are Python files — not JSON, not DynamoDB

| Approach                       | Pros                                                          | Cons                                             |
| ------------------------------ | ------------------------------------------------------------- | ------------------------------------------------ |
| **Python files** (this design) | Type-checked, IDE support, git history, testable, code review | Requires deploy                                  |
| JSON files                     | Editable without code changes                                 | No type checking, no IDE, breaks silently        |
| DynamoDB config                | Runtime-editable                                              | No version control, no type safety, hard to test |

### The change process

```text
1. Edit transitions / states / guards in the shared layer
2. Pyright catches type errors (wrong StrEnum values, missing fields)
3. Run unit + property tests
4. Code review (git diff shows exactly what changed)
5. Deploy (sam build + sam deploy)
6. CloudWatch WORKFLOW_AUDIT confirms transitions are firing
```

### Common modifications

| Change            | What to edit                                            |
| ----------------- | ------------------------------------------------------- |
| New transition    | Add dict to transitions list + StrEnum value if needed  |
| New guard         | Add function to `guards.py`, reference in transition    |
| Change actions    | Edit `actions` or `side_effects` list in the transition |
| Remove transition | Delete from list — engine returns "not allowed"         |
| New workflow      | New file + StrEnum classes + engine instance            |

---

## 14. Async Actions (opt-in)

By default, all actions run synchronously in the handler. For slow operations:

```python
import boto3

lambda_client = boto3.client('lambda')

def generate_invoice_pdf_async(ctx: dict) -> None:
    """Fire-and-forget: invoke PDF generator Lambda asynchronously."""
    lambda_client.invoke(
        FunctionName='generate_invoice_pdf',
        InvocationType='Event',  # Returns immediately
        Payload=json.dumps({
            'order_id': ctx['order_id'],
            'template': 'invoice',
        }),
    )

# Register as async
dispatcher.register('generate_invoice_pdf', generate_invoice_pdf_async)
```

The tradeoff: async actions can't report failure back to the original request. Use only for non-critical, slow operations.

---

## 15. Future Considerations (NOT built now)

### WorkflowService Facade

Extract when 3+ handlers repeat the same engine + dispatcher + persist pattern:

```python
class WorkflowService:
    def process(self, entity: dict, event: str, context: dict) -> TransitionResult:
        """One-call workflow processing."""
        ...
```

### Multi-tenancy

Architecture supports it without changes — instantiate different engines per tenant. Add `workflow` field to entities only when SaaS is on the roadmap.

### Step Functions / EventBridge

Upgrade triggers:

- Workflow spans > 5 minutes
- Need automatic retries with backoff
- Multiple independent services react to same state change
- Visual monitoring needed in AWS console
- Rollback logic becomes complex (compensating transactions)
