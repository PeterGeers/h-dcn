from enum import StrEnum


class MemberState(StrEnum):
    APPLIED = 'applied'
    PENDING = 'pending'
    WAIT_PAYMENT = 'wait_payment'
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    SUSPENDED = 'suspended'


class MemberEvent(StrEnum):
    SUBMIT = 'SUBMIT'
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
