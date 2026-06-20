"""
Get Product Sold Counts handler.

GET /products/sold-counts?event_id={id}

Returns aggregate sold counts per product for an event.
Used by the booking form to calculate effective per-event limits.

Auth: event_participant or hdcnLeden or admin roles.

Requirements: 7.3, 7.5, 7.8
"""

import os
import logging
from decimal import Decimal

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
    print("Using shared auth layer for get_product_sold_counts")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_product_sold_counts")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))

# Roles that grant access to this endpoint
ALLOWED_ROLES = {
    'event_participant',
    'hdcnLeden',
    'Products_CRUD',
    'Products_Read',
    'Regio_All',
    'Webshop_Management',
    'System_CRUD',
}


def _has_access(user_roles: list[str]) -> bool:
    """Check if user has any role that grants access to sold counts."""
    return bool(set(user_roles) & ALLOWED_ROLES)


def _aggregate_sold_counts(event_id: str) -> dict[str, int]:
    """
    Scan Orders for the given event_id where status != 'cancelled',
    and aggregate product quantities across all order items.

    Returns:
        dict mapping product_id to total sold count.
    """
    sold_counts: dict[str, int] = {}

    filter_expr = (
        Attr('event_id').eq(event_id)
        & Attr('status').ne('cancelled')
    )

    response = orders_table.scan(
        FilterExpression=filter_expr,
        ProjectionExpression='#items_attr',
        ExpressionAttributeNames={'#items_attr': 'items'},
    )

    items = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ProjectionExpression='#items_attr',
            ExpressionAttributeNames={'#items_attr': 'items'},
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    # Aggregate quantities per product_id
    for order in items:
        order_items = order.get('items', [])
        for item in order_items:
            product_id = item.get('product_id')
            if not product_id:
                continue
            # Each item line represents 1 unit (per the booking form pattern)
            # But check if quantity field exists for webshop-style orders
            quantity = item.get('quantity', 1)
            # DynamoDB may store as Decimal
            if isinstance(quantity, Decimal):
                quantity = int(quantity)
            sold_counts[product_id] = sold_counts.get(product_id, 0) + quantity

    return sold_counts


def lambda_handler(event, context):
    """Main handler for GET /products/sold-counts."""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Authorization: event_participant or hdcnLeden or admin
        if not _has_access(user_roles):
            return create_error_response(403, 'Access denied: insufficient permissions')

        log_successful_access(user_email, user_roles, 'get_product_sold_counts')

        # Get event_id from query parameters
        query_params = event.get('queryStringParameters') or {}
        event_id = query_params.get('event_id')

        if not event_id:
            return create_error_response(400, 'Missing required query parameter: event_id')

        # Aggregate sold counts
        sold_counts = _aggregate_sold_counts(event_id)

        return create_success_response(sold_counts)

    except Exception as e:
        logger.error(f"Error in get_product_sold_counts: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
