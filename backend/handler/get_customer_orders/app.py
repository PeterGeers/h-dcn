"""
Get customer orders handler for H-DCN.

GET /orders/my — Returns all orders belonging to the authenticated user (read-only).
Displays order status, items, totals, and payment status.
Supports both webshop orders (event_id null) and event orders (event_id set).

Requirements: 7.14, 7.15
"""

import json
import os
import logging
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

# Import from shared auth layer
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
    print("Using shared auth layer for get_customer_orders")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_customer_orders")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def _json_serialize(obj):
    """Custom JSON serializer for Decimal and other non-standard types."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _get_member_id(user_email):
    """Resolve member_id from user email. Returns (member_id, error_response)."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='member_id',
        )
        items = response.get('Items', [])
        if not items:
            return None, create_error_response(404, 'Member record not found')
        member_id = items[0].get('member_id')
        if not member_id:
            return None, create_error_response(500, 'Member record missing member_id')
        return member_id, None
    except Exception as e:
        logger.error(f"Error looking up member for {user_email}: {e}")
        return None, create_error_response(500, 'Error looking up member information')


def lambda_handler(event, context):
    """Main handler for GET /orders/my."""
    try:
        # Handle OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication — any authenticated user can view their own orders
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Resolve member_id from user email
        member_id, member_error = _get_member_id(user_email)
        if member_error:
            return member_error

        # Scan Orders table for records matching this member_id
        filter_expr = Attr('member_id').eq(member_id)

        response = orders_table.scan(FilterExpression=filter_expr)
        orders = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = orders_table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            orders.extend(response.get('Items', []))

        # Sort by created_at descending (newest first)
        orders.sort(key=lambda o: o.get('created_at', ''), reverse=True)

        # Shape the response to include relevant fields
        result_orders = []
        for order in orders:
            result_orders.append({
                'order_id': order.get('order_id'),
                'order_number': order.get('order_number'),
                'event_id': order.get('event_id'),
                'status': order.get('status'),
                'payment_status': order.get('payment_status'),
                'items': order.get('items', []),
                'total_amount': order.get('total_amount', 0),
                'total_paid': order.get('total_paid', 0),
                'delivery_option': order.get('delivery_option'),
                'delivery_cost': order.get('delivery_cost', 0),
                'tracking_number': order.get('tracking_number'),
                'shipping_carrier': order.get('shipping_carrier'),
                'shipped_at': order.get('shipped_at'),
                'created_at': order.get('created_at'),
                'updated_at': order.get('updated_at'),
            })

        return create_success_response(
            json.loads(json.dumps({
                'orders': result_orders,
                'total_count': len(result_orders),
            }, default=_json_serialize))
        )

    except Exception as e:
        logger.error(f"Error retrieving customer orders: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
