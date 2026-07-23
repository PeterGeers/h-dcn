"""Order workflow — transition definitions and engine instance.

Defines the complete order lifecycle from draft through submission,
payment, fulfillment, cancellation, and refund.
"""

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
