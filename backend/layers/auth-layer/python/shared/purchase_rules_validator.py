"""
Purchase rules validator module for the H-DCN webshop order pipeline.

Provides a pure validation function that checks purchase constraints against
pre-computed quantities. Unlike purchase_rules_engine.py (which queries DynamoDB
for existing counts), this module takes existing_count as a parameter, making it
suitable for server-side validation where counts have already been resolved.

Error responses follow the standard format defined in the design document:
- PurchaseRuleViolation (400): {"error": "Purchase rule violated", "rule": "...", "limit": N, "current": M}
- MembershipRequired (403): {"error": "Active membership required"}

Usage:
    from shared.purchase_rules_validator import validate_purchase_rules

    error = validate_purchase_rules(
        purchase_rules=product.get("purchase_rules", {}),
        existing_count=3,
        new_quantity=2,
        is_member=True,
    )
    if error:
        return create_error_response(error.get("status_code", 400), error)
"""

from typing import Any, Dict, Optional


def validate_purchase_rules(
    purchase_rules: Dict[str, Any],
    existing_count: int,
    new_quantity: int,
    is_member: bool,
) -> Optional[Dict[str, Any]]:
    """
    Validate purchase against product purchase rules.

    Checks each applicable rule in order: requires_membership first (since it's
    a hard block regardless of quantity), then max_per_order, max_per_member,
    and max_per_club. Returns the first violation found, or None if all pass.

    Args:
        purchase_rules: Dict with optional keys: max_per_order, max_per_member,
                        max_per_club, requires_membership. If None or empty,
                        validation passes.
        existing_count: Number of this product already purchased by the
                        member/club (depending on which rule applies).
        new_quantity: Number being added in this order.
        is_member: Whether the buyer is an active member.

    Returns:
        None if valid, or error dict with keys: error, rule, limit, current
        (for quantity rules) or just error (for membership requirement).
    """
    if not purchase_rules:
        return None

    # Check requires_membership first — hard block for non-members
    requires_membership = purchase_rules.get("requires_membership")
    if requires_membership and not is_member:
        return {
            "error": "Active membership required",
            "status_code": 403,
        }

    # Check max_per_order — limit on quantity within a single order
    # existing_count here represents items of this product already in the order
    max_per_order = purchase_rules.get("max_per_order")
    if max_per_order is not None:
        total = existing_count + new_quantity
        if total > max_per_order:
            return _purchase_rule_violation("max_per_order", max_per_order, existing_count)

    # Check max_per_member — limit on total quantity across all member orders
    max_per_member = purchase_rules.get("max_per_member")
    if max_per_member is not None:
        total = existing_count + new_quantity
        if total > max_per_member:
            return _purchase_rule_violation("max_per_member", max_per_member, existing_count)

    # Check max_per_club — limit on total quantity across all club orders
    max_per_club = purchase_rules.get("max_per_club")
    if max_per_club is not None:
        total = existing_count + new_quantity
        if total > max_per_club:
            return _purchase_rule_violation("max_per_club", max_per_club, existing_count)

    return None


def _purchase_rule_violation(
    rule: str, limit: int, current: int
) -> Dict[str, Any]:
    """
    Build a standardized PurchaseRuleViolation error response.

    Args:
        rule: The rule name that was violated (max_per_order, max_per_member, max_per_club).
        limit: The maximum allowed value for this rule.
        current: The current count (existing purchases for member/club rules,
                 or the requested quantity for max_per_order).

    Returns:
        Error dict matching the design document format.
    """
    return {
        "error": "Purchase rule violated",
        "rule": rule,
        "limit": limit,
        "current": current,
        "status_code": 400,
    }
