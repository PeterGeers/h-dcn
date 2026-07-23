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
