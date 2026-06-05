"""
Payment calculation helpers for the admin product management module.

Provides functions for computing payment aggregates across orders.
"""


def compute_payment_aggregates(orders: list) -> dict:
    """
    Given a list of order dicts, compute payment aggregates.

    Each order dict is expected to have:
        - total_amount (number): The total charged for the order.
        - amount_paid (number): The amount already paid on the order.

    Args:
        orders: List of order dicts with 'total_amount' and 'amount_paid' keys.

    Returns:
        Dict with keys:
            - total_charged: Sum of all order total_amount values.
            - total_paid: Sum of all order amount_paid values.
            - total_outstanding: total_charged - total_paid.
    """
    total_charged = sum(order.get('total_amount', 0) for order in orders)
    total_paid = sum(order.get('amount_paid', 0) for order in orders)
    total_outstanding = total_charged - total_paid

    return {
        'total_charged': total_charged,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding
    }
