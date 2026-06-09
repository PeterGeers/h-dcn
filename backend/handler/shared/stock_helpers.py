"""
Stock management helpers for the admin product management module.

Provides functions for reserving stock on paid orders and recording
inbound stock movements (purchase receipts).
"""

import uuid
from datetime import datetime, timezone


def reserve_stock(order_items: list, producten_table, movements_table, order_id: str) -> None:
    """
    Decrement stock and increment sold_count when an order transitions to 'paid'.
    Stock is ALWAYS on variant records — including Default_Variants for simple products.
    Every cart item has a variant_id; there is no path that targets a parent product directly.
    Also creates sale movement records in the StockMovements table for each line item.

    Args:
        order_items: List of order line item dicts, each with 'variant_id' and 'quantity'.
        producten_table: DynamoDB Table resource for Producten.
        movements_table: DynamoDB Table resource for StockMovements.
        order_id: The order ID triggering the stock reservation.
    """
    for item in order_items:
        variant_id = item['variant_id']
        quantity = item['quantity']

        # Decrement stock and increment sold_count on the variant
        producten_table.update_item(
            Key={'product_id': variant_id},
            UpdateExpression='SET stock = stock - :qty, sold_count = sold_count + :qty',
            ExpressionAttributeValues={':qty': quantity}
        )

        # Create sale movement record
        movements_table.put_item(Item={
            'movement_id': f'mov_{uuid.uuid4().hex[:12]}',
            'variant_id': variant_id,
            'type': 'sale',
            'quantity': -quantity,
            'purchase_price_per_unit': None,
            'total_cost': None,
            'supplier_name': None,
            'recorded_by': 'system',
            'reference': None,
            'order_id': order_id,
            'created_at': datetime.now(timezone.utc).isoformat()
        })


def create_inbound_movement(
    variant_id: str,
    quantity: int,
    purchase_price_per_unit: float,
    supplier_name: str,
    recorded_by: str,
    reference: str | None,
    movements_table
) -> dict:
    """
    Create an inbound stock movement record for a variant purchase/receipt.

    Args:
        variant_id: The variant receiving stock.
        quantity: Positive integer quantity being added.
        purchase_price_per_unit: Cost per unit in euros.
        supplier_name: Name of the supplier.
        recorded_by: Email of the user recording the movement.
        reference: Optional reference/note (e.g., PO number).
        movements_table: DynamoDB Table resource for StockMovements.

    Returns:
        The created movement record dict.
    """
    total_cost = round(quantity * purchase_price_per_unit, 2)

    movement = {
        'movement_id': f'mov_{uuid.uuid4().hex[:12]}',
        'variant_id': variant_id,
        'type': 'inbound',
        'quantity': quantity,
        'purchase_price_per_unit': purchase_price_per_unit,
        'total_cost': total_cost,
        'supplier_name': supplier_name,
        'recorded_by': recorded_by,
        'reference': reference,
        'order_id': None,
        'created_at': datetime.now(timezone.utc).isoformat()
    }

    movements_table.put_item(Item=movement)

    return movement
