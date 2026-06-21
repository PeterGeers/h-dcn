"""
Admin Event Dashboard handler.

GET /admin/events/{event_id}/dashboard

Returns registration progress, order status breakdown, payment status breakdown,
and per-product capacity usage for an event.

Auth: admin roles (Products_CRUD, Regio_All, System_CRUD, Events_CRUD).

Requirements: 14.1, 14.2, 14.3, 14.4
"""

import json
import os
import logging
from decimal import Decimal
from typing import TypedDict

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
        create_success_response,
        log_successful_access,
    )
    print("Using shared auth layer for admin_event_dashboard")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_event_dashboard")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
products_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# S3 client for registry file
s3 = boto3.client('s3', region_name='eu-west-1')
REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')

# Admin roles that grant access to this endpoint
ADMIN_ROLES = {'Products_CRUD', 'Regio_All', 'System_CRUD', 'Events_CRUD'}


# --- Types ---

class ProductCapacity(TypedDict):
    product_name: str
    product_id: str
    sold_count: int
    max_per_event: int


class DashboardResponse(TypedDict):
    total_rows: int
    claimed_rows: int
    unclaimed_rows: int
    registration_pct: int
    orders_by_status: dict[str, int]
    orders_by_payment: dict[str, int]
    revenue_collected: Decimal
    revenue_expected: Decimal
    product_capacity: list[ProductCapacity]


# --- Helpers ---

def _has_admin_access(user_roles: list[str]) -> bool:
    """Check if user has any admin role that grants dashboard access."""
    return bool(set(user_roles) & ADMIN_ROLES)


def _get_total_rows_from_s3(s3_path: str) -> int:
    """Fetch the invitee_registry.json from S3 and return total row count."""
    try:
        response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
        registry_data = json.loads(response['Body'].read().decode('utf-8'))
        rows = registry_data.get('rows', [])
        return len(rows)
    except Exception as e:
        logger.error(f"Error fetching registry from S3: {e}")
        return 0


def _scan_orders_for_event(event_id: str) -> list[dict]:
    """Scan all non-cancelled orders for an event."""
    filter_expr = (
        Attr('event_id').eq(event_id)
        & Attr('status').ne('cancelled')
    )

    response = orders_table.scan(
        FilterExpression=filter_expr,
    )
    items = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return items


def _get_event_products(event_id: str) -> dict[str, dict]:
    """Fetch all products linked to the event. Returns dict keyed by product_id."""
    filter_expr = Attr('event_id').eq(event_id) & Attr('is_parent').eq(True)

    response = products_table.scan(
        FilterExpression=filter_expr,
        ProjectionExpression='product_id, #n, purchase_rules',
        ExpressionAttributeNames={'#n': 'name'},
    )
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = products_table.scan(
            FilterExpression=filter_expr,
            ProjectionExpression='product_id, #n, purchase_rules',
            ExpressionAttributeNames={'#n': 'name'},
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return {item['product_id']: item for item in items}


def _to_decimal(value) -> Decimal:
    """Safely convert a value to Decimal."""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal('0')


def _convert_decimals(obj):
    """Convert DynamoDB Decimal types to int/float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _build_dashboard(event_record: dict, orders: list[dict], products: dict[str, dict]) -> dict:
    """Build the dashboard response from event data and orders."""
    registry_config = event_record.get('registry_config', {})
    registry_claims = event_record.get('registry_claims', {})

    # --- Registration stats ---
    s3_path = registry_config.get('s3_path')
    total_rows = _get_total_rows_from_s3(s3_path) if s3_path else 0
    claimed_rows = len(registry_claims)
    unclaimed_rows = max(0, total_rows - claimed_rows)
    registration_pct = int((claimed_rows / total_rows * 100)) if total_rows > 0 else 0

    # --- Order status breakdown ---
    orders_by_status: dict[str, int] = {'draft': 0, 'submitted': 0, 'locked': 0}
    for order in orders:
        status = order.get('status', 'draft')
        if status in orders_by_status:
            orders_by_status[status] += 1

    # --- Payment status breakdown ---
    orders_by_payment: dict[str, int] = {'unpaid': 0, 'partial': 0, 'paid': 0}
    revenue_collected = Decimal('0')
    revenue_expected = Decimal('0')

    for order in orders:
        payment_status = order.get('payment_status', 'unpaid')
        if payment_status in orders_by_payment:
            orders_by_payment[payment_status] += 1

        # Revenue: collected = total_paid, expected = total_amount for submitted/locked
        total_paid = _to_decimal(order.get('total_paid', 0))
        total_amount = _to_decimal(order.get('total_amount', 0))
        revenue_collected += total_paid

        # Expected revenue comes from submitted and locked orders
        status = order.get('status', 'draft')
        if status in ('submitted', 'locked'):
            revenue_expected += total_amount

    # --- Per-product capacity usage ---
    # Aggregate sold counts from all orders
    sold_counts: dict[str, int] = {}
    for order in orders:
        order_items = order.get('items', [])
        for item in order_items:
            product_id = item.get('product_id')
            if not product_id:
                continue
            quantity = item.get('quantity', 1)
            if isinstance(quantity, Decimal):
                quantity = int(quantity)
            sold_counts[product_id] = sold_counts.get(product_id, 0) + quantity

    # Build product capacity list (only for products that have max_per_event)
    product_capacity: list[dict] = []
    for product_id, product in products.items():
        purchase_rules = product.get('purchase_rules', {})
        if not purchase_rules:
            continue
        max_per_event = purchase_rules.get('max_per_event')
        if max_per_event is None:
            continue
        if isinstance(max_per_event, Decimal):
            max_per_event = int(max_per_event)

        product_capacity.append({
            'product_id': product_id,
            'product_name': product.get('name', 'Unknown'),
            'sold_count': sold_counts.get(product_id, 0),
            'max_per_event': max_per_event,
        })

    # Sort by product name for consistent ordering
    product_capacity.sort(key=lambda p: p.get('product_name', '').lower())

    return {
        'total_rows': total_rows,
        'claimed_rows': claimed_rows,
        'unclaimed_rows': unclaimed_rows,
        'registration_pct': registration_pct,
        'orders_by_status': orders_by_status,
        'orders_by_payment': orders_by_payment,
        'revenue_collected': revenue_collected,
        'revenue_expected': revenue_expected,
        'product_capacity': product_capacity,
    }


# --- Main handler ---

def lambda_handler(event, context):
    """Main handler for GET /admin/events/{event_id}/dashboard."""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Authorization: admin roles only
        if not _has_admin_access(user_roles):
            return create_error_response(403, 'Access denied: insufficient permissions')

        log_successful_access(user_email, user_roles, 'admin_event_dashboard')

        # Get event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        if not event_id:
            return create_error_response(400, 'Missing event_id parameter')

        # Fetch Event record from DynamoDB
        event_response = events_table.get_item(Key={'event_id': event_id})
        if 'Item' not in event_response:
            return create_error_response(404, 'Event not found')

        event_record = event_response['Item']

        # Fetch all non-cancelled orders for this event
        orders = _scan_orders_for_event(event_id)

        # Fetch event-linked products (for capacity info)
        products = _get_event_products(event_id)

        # Build dashboard response
        dashboard = _build_dashboard(event_record, orders, products)

        return create_success_response(_convert_decimals(dashboard))

    except Exception as e:
        logger.error(f"Error in admin_event_dashboard: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
