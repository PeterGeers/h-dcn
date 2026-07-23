"""Membership workflow — transition definitions and engine instance.

Defines the complete membership lifecycle from application to activation,
cancellation, and suspension.
"""

from .types import Transition
from .states import MemberState, MemberEvent
from .guards import requires_reason
from .engine import WorkflowEngine

MEMBERSHIP_TRANSITIONS: list[Transition] = [
    {
        'from_state': MemberState.APPLIED,
        'to_state': MemberState.PENDING,
        'event': MemberEvent.SUBMIT,
        'actions': [],
        'side_effects': ['send_application_received', 'audit_log'],
    },
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
