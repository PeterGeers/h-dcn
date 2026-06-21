"""
Admin CSV Export Orders handler.

GET /admin/events/{event_id}/export-csv

Exports all orders for an event to CSV including:
- Order items (product name, variant, quantity, unit price)
- Delegate name and email
- Person names
- Order status, payment status, and order total

Auth: Admin (Products_CRUD, Regio_All, System_CRUD, Events_CRUD)

Requirements: 14.6
"""

import os
import io
import csv
import base64
import logging
from decimal import Decimal
from typing import TypedDict, NotRequired

import boto3
from boto3.dynamodb.conditions import Attr

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        log_successful_access,
    )
    print("Using shared auth layer for admin_export_orders_csv")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_export_orders_csv")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# Admin roles that grant access
ADMIN_ROLES = ['Products_CRUD', 'Regio_All', 'System_CRUD', 'Events_CRUD']

# CSV column headers
CSV_COLUMNS = [
    'order_id',
    'club_name',
    'delegate_name',
    'delegate_email',
    'person_name',
    'product_name',
    'variant',
    'quantity',
    'unit_price',
    'line_total',
    'order_status',
    'payment_status',
    'order_total',
]


def _decimal_to_str(value) -> str:
    """Convert a Decimal or numeric value to a string with 2 decimal places."""
    if value is None:
        return '0.00'
    if isinstance(value, Decimal):
        return f"{float(value):.2f}"
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return '0.00'


def _fetch_all_orders(event_id: str) -> list[dict]:
    """Fetch all orders for the given event_id (all statuses)."""
    filter_expr = Attr('event_id').eq(event_id)

    response = orders_table.scan(
        FilterExpression=filter_expr,
    )
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return items


def _fetch_product_names(product_ids: set[str]) -> dict[str, str]:
    """Fetch product names for a set of product_ids using batch_get_item."""
    if not product_ids:
        return {}

    product_names: dict[str, str] = {}

    # DynamoDB batch_get_item supports max 100 keys per request
    product_id_list = list(product_ids)
    for i in range(0, len(product_id_list), 100):
        batch = product_id_list[i:i + 100]
        keys = [{'product_id': pid} for pid in batch]

        response = dynamodb.batch_get_item(
            RequestItems={
                producten_table.name: {
                    'Keys': keys,
                    'ProjectionExpression': 'product_id, #n',
                    'ExpressionAttributeNames': {'#n': 'name'},
                }
            }
        )

        for item in response.get('Responses', {}).get(producten_table.name, []):
            product_names[item['product_id']] = item.get('name', 'Unknown')

        # Handle unprocessed keys
        unprocessed = response.get('UnprocessedKeys', {}).get(producten_table.name, {})
        while unprocessed:
            response = dynamodb.batch_get_item(
                RequestItems={producten_table.name: unprocessed}
            )
            for item in response.get('Responses', {}).get(producten_table.name, []):
                product_names[item['product_id']] = item.get('name', 'Unknown')
            unprocessed = response.get('UnprocessedKeys', {}).get(producten_table.name, {})

    return product_names


def _get_variant_label(item: dict) -> str:
    """Extract variant label from an order item."""
    # Try variant_label first (may be stored directly)
    variant_label = item.get('variant_label', '')
    if variant_label:
        return variant_label

    # Fall back to variant_id
    variant_id = item.get('variant_id', '')
    return variant_id or ''


def _build_csv_rows(orders: list[dict], product_names: dict[str, str]) -> list[dict]:
    """
    Build CSV rows from orders.

    Each row represents one order item line, with order-level context repeated.
    If an order has no items, one row is still generated with order metadata.
    """
    csv_rows: list[dict] = []

    for order in orders:
        order_id = order.get('order_id', '')
        club_name = order.get('club_name', order.get('club_id', ''))
        status = order.get('status', '')
        payment_status = order.get('payment_status', '')
        total_amount = order.get('total_amount', 0)

        # Delegate info
        delegates = order.get('delegates', {})
        delegate_name = delegates.get('primary_name', '')
        delegate_email = delegates.get('primary', '')

        # If delegate name is not in delegates structure, try member_name
        if not delegate_name:
            delegate_name = order.get('member_name', '')

        items = order.get('items', [])

        if not items:
            # Order with no items — still include in export
            csv_rows.append({
                'order_id': order_id,
                'club_name': club_name,
                'delegate_name': delegate_name,
                'delegate_email': delegate_email,
                'person_name': '',
                'product_name': '',
                'variant': '',
                'quantity': '',
                'unit_price': '',
                'line_total': '',
                'order_status': status,
                'payment_status': payment_status,
                'order_total': _decimal_to_str(total_amount),
            })
        else:
            for item in items:
                product_id = item.get('product_id', '')
                product_name = product_names.get(product_id, product_id)
                variant = _get_variant_label(item)
                quantity = item.get('quantity', 1)
                if isinstance(quantity, Decimal):
                    quantity = int(quantity)
                unit_price = item.get('unit_price', 0)
                line_total = item.get('line_total', 0)

                # Person name from item_fields_data
                item_fields = item.get('item_fields_data', {})
                person_name = item_fields.get('name', '')

                csv_rows.append({
                    'order_id': order_id,
                    'club_name': club_name,
                    'delegate_name': delegate_name,
                    'delegate_email': delegate_email,
                    'person_name': person_name,
                    'product_name': product_name,
                    'variant': variant,
                    'quantity': str(quantity),
                    'unit_price': _decimal_to_str(unit_price),
                    'line_total': _decimal_to_str(line_total),
                    'order_status': status,
                    'payment_status': payment_status,
                    'order_total': _decimal_to_str(total_amount),
                })

    return csv_rows


def _generate_csv(rows: list[dict]) -> str:
    """Generate CSV string from rows."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def lambda_handler(event, context):
    """Main handler for GET /admin/events/{event_id}/export-csv."""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # --- Authentication & Authorization ---
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ADMIN_ROLES, user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_export_orders_csv')

        # --- Extract event_id from path ---
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        if not event_id:
            return create_error_response(400, 'Missing required path parameter: event_id')

        # --- Fetch all orders for the event ---
        orders = _fetch_all_orders(event_id)

        if not orders:
            # Return empty CSV with headers only
            csv_content = ','.join(CSV_COLUMNS) + '\n'
        else:
            # Collect all product IDs from orders
            product_ids: set[str] = set()
            for order in orders:
                for item in order.get('items', []):
                    pid = item.get('product_id')
                    if pid:
                        product_ids.add(pid)

            # Fetch product names
            product_names = _fetch_product_names(product_ids)

            # Build CSV rows
            csv_rows = _build_csv_rows(orders, product_names)

            # Generate CSV content
            csv_content = _generate_csv(csv_rows)

        # Return CSV as base64-encoded response for API Gateway binary support
        filename = f"orders_export_{event_id}.csv"

        return {
            'statusCode': 200,
            'headers': {
                **cors_headers(),
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'attachment; filename="{filename}"',
            },
            'body': base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'),
            'isBase64Encoded': True,
        }

    except Exception as e:
        logger.error(f"Error in admin_export_orders_csv: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
