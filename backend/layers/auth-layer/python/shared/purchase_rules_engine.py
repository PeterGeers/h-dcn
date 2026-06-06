"""
Purchase rules enforcement engine for the unified webshop pipeline.

Provides functions to validate purchase constraints (max_per_order, max_per_member,
max_per_club, requires_membership) and an orchestrator that runs all applicable rules
for a given product/order context.

Each enforce_* function returns None if the constraint passes, or a violation dict
matching the standard error format:
{
    "error": "purchase_rule_violation",
    "details": {
        "rule": "<rule_name>",
        "product_id": "<product_id>",
        "limit": <limit_value>,
        "current_total": <existing_quantity>,
        "requested": <new_quantity>,
        "remaining_allowed": <remaining>
    }
}
"""

from typing import Any, Dict, List, Optional

import boto3.dynamodb.conditions


def enforce_max_per_order(
    quantity: int,
    max_per_order: int,
) -> Optional[Dict[str, Any]]:
    """
    Enforce the max_per_order constraint.

    Args:
        quantity: The quantity being ordered in this line item.
        max_per_order: Maximum allowed quantity per single order.

    Returns:
        None if the constraint passes, or a violation dict.
    """
    if quantity <= max_per_order:
        return None

    return {
        "error": "purchase_rule_violation",
        "details": {
            "rule": "max_per_order",
            "limit": max_per_order,
            "current_total": 0,
            "requested": quantity,
            "remaining_allowed": max_per_order,
        },
    }


def enforce_max_per_member(
    member_id: str,
    product_id: str,
    new_quantity: int,
    max_per_member: int,
    orders_table,
) -> Optional[Dict[str, Any]]:
    """
    Enforce the max_per_member constraint by querying existing orders.

    Sums the quantity of the given product across all orders for this member
    with status "paid" or "pending", then checks whether adding new_quantity
    would exceed max_per_member.

    Args:
        member_id: The member placing the order.
        product_id: The product being ordered.
        new_quantity: The quantity being added in the current order.
        max_per_member: Maximum total quantity this member may purchase.
        orders_table: DynamoDB Table resource for Orders.

    Returns:
        None if the constraint passes, or a violation dict.
    """
    current_total = _sum_member_product_quantity(
        member_id, product_id, orders_table
    )

    if current_total + new_quantity <= max_per_member:
        return None

    remaining = max(0, max_per_member - current_total)
    return {
        "error": "purchase_rule_violation",
        "details": {
            "rule": "max_per_member",
            "product_id": product_id,
            "limit": max_per_member,
            "current_total": current_total,
            "requested": new_quantity,
            "remaining_allowed": remaining,
        },
    }


def enforce_max_per_club(
    club_id: str,
    product_id: str,
    new_quantity: int,
    max_per_club: int,
    orders_table,
) -> Optional[Dict[str, Any]]:
    """
    Enforce the max_per_club constraint by querying existing orders.

    Sums the quantity of the given product across all orders for this club
    with status "paid" or "pending", then checks whether adding new_quantity
    would exceed max_per_club.

    Args:
        club_id: The club placing the order.
        product_id: The product being ordered.
        new_quantity: The quantity being added in the current order.
        max_per_club: Maximum total quantity this club may purchase.
        orders_table: DynamoDB Table resource for Orders.

    Returns:
        None if the constraint passes, or a violation dict.
    """
    current_total = _sum_club_product_quantity(
        club_id, product_id, orders_table
    )

    if current_total + new_quantity <= max_per_club:
        return None

    remaining = max(0, max_per_club - current_total)
    return {
        "error": "purchase_rule_violation",
        "details": {
            "rule": "max_per_club",
            "product_id": product_id,
            "limit": max_per_club,
            "current_total": current_total,
            "requested": new_quantity,
            "remaining_allowed": remaining,
        },
    }


def enforce_requires_membership(
    member_id: str,
    memberships_table,
) -> Optional[Dict[str, Any]]:
    """
    Enforce the requires_membership constraint.

    Checks that the member has at least one membership record with status "active"
    in the Memberships table.

    Args:
        member_id: The member placing the order.
        memberships_table: DynamoDB Table resource for Memberships.

    Returns:
        None if the member has an active membership, or a violation dict.
    """
    has_active = _check_active_membership(member_id, memberships_table)

    if has_active:
        return None

    return {
        "error": "purchase_rule_violation",
        "details": {
            "rule": "requires_membership",
            "reason": "Active membership required to purchase this product",
        },
    }


def validate_purchase_rules(
    rules: Optional[Dict[str, Any]],
    context: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Orchestrator that runs all applicable purchase rules for a product.

    Checks each rule defined in the purchase_rules dict. If a rule key is absent
    or None, that constraint is skipped (no limit enforced). Returns the first
    violation found, or None if all rules pass.

    Args:
        rules: The product's purchase_rules dict, or None if no rules defined.
        context: Dict containing:
            - quantity (int): quantity being ordered
            - product_id (str): the product being ordered
            - member_id (str): the member placing the order
            - club_id (str, optional): the club placing the order
            - orders_table: DynamoDB Table resource for Orders
            - memberships_table: DynamoDB Table resource for Memberships

    Returns:
        None if all rules pass, or the first violation dict encountered.
    """
    if not rules:
        return None

    quantity = context["quantity"]
    product_id = context["product_id"]
    member_id = context["member_id"]
    orders_table = context.get("orders_table")
    memberships_table = context.get("memberships_table")
    club_id = context.get("club_id")

    # max_per_order
    max_per_order = rules.get("max_per_order")
    if max_per_order is not None:
        violation = enforce_max_per_order(quantity, max_per_order)
        if violation:
            violation["details"]["product_id"] = product_id
            return violation

    # max_per_member
    max_per_member = rules.get("max_per_member")
    if max_per_member is not None and orders_table is not None:
        violation = enforce_max_per_member(
            member_id, product_id, quantity, max_per_member, orders_table
        )
        if violation:
            return violation

    # max_per_club
    max_per_club = rules.get("max_per_club")
    if max_per_club is not None and club_id and orders_table is not None:
        violation = enforce_max_per_club(
            club_id, product_id, quantity, max_per_club, orders_table
        )
        if violation:
            return violation

    # requires_membership
    requires_membership = rules.get("requires_membership")
    if requires_membership and memberships_table is not None:
        violation = enforce_requires_membership(member_id, memberships_table)
        if violation:
            violation["details"]["product_id"] = product_id
            return violation

    return None


# ---------------------------------------------------------------------------
# Private helpers for DynamoDB queries
# ---------------------------------------------------------------------------


def _sum_member_product_quantity(
    member_id: str,
    product_id: str,
    orders_table,
) -> int:
    """
    Sum the quantity of a specific product across a member's paid/pending orders.

    Uses a scan with filter since Orders table uses order_id as PK.
    """
    total = 0

    filter_expr = (
        boto3.dynamodb.conditions.Attr("member_id").eq(member_id)
        & boto3.dynamodb.conditions.Attr("status").is_in(["paid", "pending"])
    )

    response = orders_table.scan(FilterExpression=filter_expr)
    items = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    for order in items:
        for item in order.get("items", []):
            if item.get("product_id") == product_id:
                total += int(item.get("quantity", 0))

    return total


def _sum_club_product_quantity(
    club_id: str,
    product_id: str,
    orders_table,
) -> int:
    """
    Sum the quantity of a specific product across a club's paid/pending orders.

    Uses a scan with filter since Orders table uses order_id as PK.
    """
    total = 0

    filter_expr = (
        boto3.dynamodb.conditions.Attr("club_id").eq(club_id)
        & boto3.dynamodb.conditions.Attr("status").is_in(["paid", "pending"])
    )

    response = orders_table.scan(FilterExpression=filter_expr)
    items = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    for order in items:
        for item in order.get("items", []):
            if item.get("product_id") == product_id:
                total += int(item.get("quantity", 0))

    return total


def _check_active_membership(
    member_id: str,
    memberships_table,
) -> bool:
    """
    Check if a member has at least one active membership.

    Scans the Memberships table for records matching the member_id
    with status "active".
    """
    filter_expr = (
        boto3.dynamodb.conditions.Attr("member_id").eq(member_id)
        & boto3.dynamodb.conditions.Attr("status").eq("active")
    )

    response = memberships_table.scan(
        FilterExpression=filter_expr,
        Limit=1,
    )

    return len(response.get("Items", [])) > 0
