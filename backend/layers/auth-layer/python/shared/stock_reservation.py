"""
Atomic stock reservation for order payment confirmation.

Provides idempotent stock decrement + sold_count increment on variant records
using DynamoDB conditional expressions. Designed to be called when an order
transitions to "paid" status (via Mollie webhook or admin manual payment).

Key guarantees:
- Preserves invariant: initial_stock - stock_after = sold_count_after - initial_sold_count = ordered_quantity
- Prevents double-deduction on retry using order_id as idempotency key
- Rejects reservation when allow_oversell=false and stock < requested quantity
"""

import logging
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StockReservationError(Exception):
    """Base exception for stock reservation failures."""

    def __init__(self, message: str, variant_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.variant_id = variant_id
        self.details = details or {}


class InsufficientStockError(StockReservationError):
    """Raised when a variant has insufficient stock and allow_oversell is false."""

    def __init__(self, variant_id: str, available: int, requested: int):
        super().__init__(
            f"Insufficient stock for variant {variant_id}: available={available}, requested={requested}",
            variant_id=variant_id,
            details={"available": available, "requested": requested},
        )
        self.available = available
        self.requested = requested


class AlreadyReservedError(StockReservationError):
    """Raised when stock has already been reserved for this order (idempotency guard)."""

    def __init__(self, variant_id: str, order_id: str):
        super().__init__(
            f"Stock already reserved for order {order_id} on variant {variant_id}",
            variant_id=variant_id,
            details={"order_id": order_id},
        )
        self.order_id = order_id


def reserve_stock_for_order(
    order_items: List[Dict[str, Any]],
    producten_table,
    order_id: str,
) -> List[Dict[str, Any]]:
    """
    Reserve stock for all items in a paid order.

    Uses DynamoDB conditional expressions to atomically decrement stock and
    increment sold_count on each variant record. The conditional expression
    ensures:
    1. Stock is sufficient (stock >= quantity) for variants with allow_oversell=false
    2. The order has not already reserved stock (idempotency via stock_reserved_for_order)

    For variants with allow_oversell=true, the stock check is skipped but the
    idempotency guard still applies.

    Args:
        order_items: List of dicts with keys:
            - variant_id (str): The variant record's product_id
            - quantity (int): Number of units to reserve
        producten_table: boto3 DynamoDB Table resource for the Producten table.
        order_id: The order ID triggering the reservation (used as idempotency key).

    Returns:
        List of dicts with reservation results per item:
            - variant_id (str)
            - quantity (int)
            - status: "reserved" or "already_reserved"

    Raises:
        InsufficientStockError: When a variant has allow_oversell=false and
            stock < requested quantity.
        StockReservationError: When an unexpected DynamoDB error occurs.
    """
    results = []

    for item in order_items:
        variant_id = item["variant_id"]
        quantity = item["quantity"]

        result = _reserve_single_variant(
            variant_id=variant_id,
            quantity=quantity,
            producten_table=producten_table,
            order_id=order_id,
        )
        results.append(result)

    return results


def _reserve_single_variant(
    variant_id: str,
    quantity: int,
    producten_table,
    order_id: str,
) -> Dict[str, Any]:
    """
    Reserve stock for a single variant using conditional update.

    The update uses a ConditionExpression that combines:
    - stock >= :qty (only for allow_oversell=false variants)
    - stock_reserved_for_order <> :order_id (idempotency guard)

    If the condition fails because stock was already reserved for this order,
    the function returns successfully with status "already_reserved" (idempotent).

    If the condition fails because of insufficient stock, raises InsufficientStockError.
    """
    # First, fetch the variant to check allow_oversell and current state
    variant = _get_variant(variant_id, producten_table)
    if variant is None:
        raise StockReservationError(
            f"Variant {variant_id} not found",
            variant_id=variant_id,
            details={"error": "variant_not_found"},
        )

    # Check if already reserved for this order (idempotency)
    existing_reservation = variant.get("stock_reserved_for_order")
    if existing_reservation == order_id:
        logger.info(
            "Stock already reserved for order %s on variant %s (idempotent)",
            order_id,
            variant_id,
        )
        return {
            "variant_id": variant_id,
            "quantity": quantity,
            "status": "already_reserved",
        }

    allow_oversell = variant.get("allow_oversell", False)

    try:
        if allow_oversell:
            # For oversell variants: skip stock check, only guard idempotency
            _update_stock_allow_oversell(
                variant_id=variant_id,
                quantity=quantity,
                producten_table=producten_table,
                order_id=order_id,
            )
        else:
            # For standard variants: enforce stock >= quantity AND idempotency
            _update_stock_with_check(
                variant_id=variant_id,
                quantity=quantity,
                producten_table=producten_table,
                order_id=order_id,
            )

        logger.info(
            "Stock reserved: variant=%s, quantity=%d, order=%s",
            variant_id,
            quantity,
            order_id,
        )
        return {
            "variant_id": variant_id,
            "quantity": quantity,
            "status": "reserved",
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ConditionalCheckFailedException":
            # Re-fetch to determine which condition failed
            return _handle_condition_failure(
                variant_id=variant_id,
                quantity=quantity,
                producten_table=producten_table,
                order_id=order_id,
            )
        raise StockReservationError(
            f"DynamoDB error reserving stock for variant {variant_id}: {e}",
            variant_id=variant_id,
            details={"error_code": error_code},
        ) from e


def _update_stock_with_check(
    variant_id: str,
    quantity: int,
    producten_table,
    order_id: str,
) -> None:
    """
    Conditional update: decrement stock, increment sold_count.
    Condition: stock >= quantity AND stock_reserved_for_order <> order_id.
    """
    producten_table.update_item(
        Key={"product_id": variant_id},
        UpdateExpression=(
            "SET stock = stock - :qty, "
            "sold_count = sold_count + :qty, "
            "stock_reserved_for_order = :order_id"
        ),
        ConditionExpression=(
            "attribute_exists(product_id) AND "
            "stock >= :qty AND "
            "(attribute_not_exists(stock_reserved_for_order) OR "
            "stock_reserved_for_order <> :order_id)"
        ),
        ExpressionAttributeValues={
            ":qty": quantity,
            ":order_id": order_id,
        },
    )


def _update_stock_allow_oversell(
    variant_id: str,
    quantity: int,
    producten_table,
    order_id: str,
) -> None:
    """
    Conditional update for oversell variants: decrement stock, increment sold_count.
    Condition: only idempotency guard (no stock check).
    Stock may go negative for oversell variants.
    """
    producten_table.update_item(
        Key={"product_id": variant_id},
        UpdateExpression=(
            "SET stock = stock - :qty, "
            "sold_count = sold_count + :qty, "
            "stock_reserved_for_order = :order_id"
        ),
        ConditionExpression=(
            "attribute_exists(product_id) AND "
            "(attribute_not_exists(stock_reserved_for_order) OR "
            "stock_reserved_for_order <> :order_id)"
        ),
        ExpressionAttributeValues={
            ":qty": quantity,
            ":order_id": order_id,
        },
    )


def _handle_condition_failure(
    variant_id: str,
    quantity: int,
    producten_table,
    order_id: str,
) -> Dict[str, Any]:
    """
    Determine the cause of a ConditionalCheckFailedException.

    Re-fetches the variant to distinguish between:
    1. Already reserved for this order (idempotent success)
    2. Insufficient stock (raise error)
    """
    variant = _get_variant(variant_id, producten_table)
    if variant is None:
        raise StockReservationError(
            f"Variant {variant_id} not found after condition failure",
            variant_id=variant_id,
            details={"error": "variant_not_found"},
        )

    # Check if it was an idempotency collision (already reserved for same order)
    if variant.get("stock_reserved_for_order") == order_id:
        logger.info(
            "Stock already reserved for order %s on variant %s (race condition resolved)",
            order_id,
            variant_id,
        )
        return {
            "variant_id": variant_id,
            "quantity": quantity,
            "status": "already_reserved",
        }

    # Otherwise, it must be insufficient stock
    current_stock = variant.get("stock", 0)
    raise InsufficientStockError(
        variant_id=variant_id,
        available=current_stock,
        requested=quantity,
    )


def _get_variant(variant_id: str, producten_table) -> Optional[Dict[str, Any]]:
    """Fetch a variant record from the Producten table."""
    response = producten_table.get_item(Key={"product_id": variant_id})
    return response.get("Item")
