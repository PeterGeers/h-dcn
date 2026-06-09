"""
Event-level capacity constraint validation for event registration.

Validates that adding a club's order items would not exceed event-wide
capacity limits defined in the event's constraints array.

Each constraint has a counting_rule that determines how items are counted
across all submitted/locked orders for the event:

- count_items_by_product: count items matching a specific product_id
- count_distinct_clubs: count distinct club_ids with submitted/locked orders
- sum_field: sum a numeric field across items in submitted/locked orders

Returns structured validation errors with constraint key, label,
current count, max, and a human-readable message.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional


# Order statuses that count toward constraints
COUNTABLE_STATUSES = {"submitted", "locked"}


def validate_event_constraints(
    order_items: List[Dict[str, Any]],
    event_constraints: List[Dict[str, Any]],
    all_event_orders: List[Dict[str, Any]],
    current_club_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Validate that adding order_items would not exceed any event constraint.

    Counts existing usage from all submitted/locked orders for the event
    (excluding the current club's order to avoid double-counting on resubmit),
    then checks if adding the new order's items would exceed each constraint's max.

    Args:
        order_items: The items array from the club's order being submitted.
        event_constraints: The constraints array from the Event record.
            Each constraint has: key, label, max, counting_rule, and optionally
            product_id or field_name.
        all_event_orders: All orders for this event (any status). The function
            filters to submitted/locked internally.
        current_club_id: The club_id of the order being submitted. Used to
            exclude the current club's existing order from the count (prevents
            double-counting on resubmission).

    Returns:
        List of validation error dicts. Empty list if all constraints pass.
        Each error contains:
            - constraint_key: the constraint's key identifier
            - label: human-readable constraint label
            - current_count: items already counted (excluding current club)
            - new_count: what the total would be after adding this order
            - max: the constraint's maximum
            - message: human-readable error message
    """
    if not event_constraints:
        return []

    errors = []

    # Filter to only submitted/locked orders
    countable_orders = [
        order for order in all_event_orders
        if order.get("status") in COUNTABLE_STATUSES
    ]

    # Exclude current club's order (will be replaced by new submission)
    if current_club_id:
        other_orders = [
            order for order in countable_orders
            if order.get("club_id") != current_club_id
        ]
    else:
        other_orders = countable_orders

    for constraint in event_constraints:
        counting_rule = constraint.get("counting_rule")
        constraint_key = constraint.get("key", "unknown")
        label = constraint.get("label", constraint_key)
        max_value = constraint.get("max")

        if max_value is None:
            continue

        # Convert Decimal to int if needed (DynamoDB returns Decimal)
        if isinstance(max_value, Decimal):
            max_value = int(max_value)

        current_count = _count_existing(constraint, other_orders)
        new_items_count = _count_new_items(constraint, order_items)
        total_after = current_count + new_items_count

        if total_after > max_value:
            errors.append({
                "constraint_key": constraint_key,
                "label": label,
                "current_count": current_count,
                "new_count": total_after,
                "max": max_value,
                "message": (
                    f"{label}: toevoegen van {new_items_count} zou het totaal op "
                    f"{total_after} brengen, maar het maximum is {max_value} "
                    f"(momenteel {current_count} bezet)"
                ),
            })

    return errors


def _count_existing(
    constraint: Dict[str, Any],
    orders: List[Dict[str, Any]],
) -> int:
    """
    Count existing usage for a constraint across orders.

    Dispatches to the appropriate counting function based on counting_rule.
    """
    counting_rule = constraint.get("counting_rule")

    if counting_rule == "count_items_by_product":
        return _count_items_by_product(constraint.get("product_id"), orders)
    elif counting_rule == "count_distinct_clubs":
        return _count_distinct_clubs(orders)
    elif counting_rule == "sum_field":
        return _sum_field(constraint.get("field_name"), constraint.get("product_id"), orders)
    else:
        return 0


def _count_new_items(
    constraint: Dict[str, Any],
    order_items: List[Dict[str, Any]],
) -> int:
    """
    Count how many items in the new order contribute to this constraint.
    """
    counting_rule = constraint.get("counting_rule")

    if counting_rule == "count_items_by_product":
        product_id = constraint.get("product_id")
        return sum(
            1 for item in order_items
            if item.get("product_id") == product_id
        )
    elif counting_rule == "count_distinct_clubs":
        # A single order submission always adds exactly 1 distinct club
        return 1
    elif counting_rule == "sum_field":
        field_name = constraint.get("field_name")
        product_id = constraint.get("product_id")
        return _sum_field_in_items(field_name, product_id, order_items)
    else:
        return 0


def _count_items_by_product(
    product_id: Optional[str],
    orders: List[Dict[str, Any]],
) -> int:
    """
    Count items matching a specific product_id across all orders.
    """
    if not product_id:
        return 0

    count = 0
    for order in orders:
        for item in order.get("items", []):
            if item.get("product_id") == product_id:
                count += 1
    return count


def _count_distinct_clubs(orders: List[Dict[str, Any]]) -> int:
    """
    Count distinct club_ids across submitted/locked orders.
    """
    club_ids = set()
    for order in orders:
        club_id = order.get("club_id")
        if club_id:
            club_ids.add(club_id)
    return len(club_ids)


def _sum_field(
    field_name: Optional[str],
    product_id: Optional[str],
    orders: List[Dict[str, Any]],
) -> int:
    """
    Sum a numeric field across items in submitted/locked orders.

    If product_id is specified, only sum items matching that product.
    The field is looked up in item_fields_data.
    """
    if not field_name:
        return 0

    total = 0
    for order in orders:
        for item in order.get("items", []):
            # Filter by product_id if specified
            if product_id and item.get("product_id") != product_id:
                continue

            fields_data = item.get("item_fields_data", {})
            value = fields_data.get(field_name, 0)

            # Handle various numeric types (DynamoDB Decimal, int, float)
            if isinstance(value, Decimal):
                total += int(value)
            elif isinstance(value, (int, float)):
                total += int(value)

    return total


def _sum_field_in_items(
    field_name: Optional[str],
    product_id: Optional[str],
    items: List[Dict[str, Any]],
) -> int:
    """
    Sum a numeric field across items in the new order.

    If product_id is specified, only sum items matching that product.
    """
    if not field_name:
        return 0

    total = 0
    for item in items:
        # Filter by product_id if specified
        if product_id and item.get("product_id") != product_id:
            continue

        fields_data = item.get("item_fields_data", {})
        value = fields_data.get(field_name, 0)

        if isinstance(value, Decimal):
            total += int(value)
        elif isinstance(value, (int, float)):
            total += int(value)

    return total
