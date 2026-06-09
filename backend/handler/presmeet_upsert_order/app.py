"""
PresMeet Upsert Order Handler

PUT /presmeet/orders/{id}
Updates items array on a PresMeet order with optimistic locking.
No field validation on draft save (accept incomplete data).

Requirements: 2 (Order Updates), 9.2 (Admin direct edit)
"""

import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal

try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import get_club_id, is_presmeet_admin, has_presmeet_access
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("presmeet_upsert_order")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
table = dynamodb.Table(table_name)


def _calculate_total_amount(items):
    """
    Recalculate total_amount from items.
    total_amount = sum(item.unit_price * item.quantity) for each item.
    If quantity is missing, default to 1.
    """
    total = Decimal('0')
    for item in items:
        unit_price = item.get('unit_price', 0)
        quantity = item.get('quantity', 1)
        if unit_price is None:
            unit_price = 0
        if quantity is None:
            quantity = 1
        total += Decimal(str(unit_price)) * Decimal(str(quantity))
    return total


def _is_delegate(order, user_email):
    """Check if user is a delegate (primary or secondary) on this order."""
    delegates = order.get('delegates', {})
    primary = delegates.get('primary', '')
    secondary = delegates.get('secondary')
    return (
        user_email.lower() == primary.lower()
        or (secondary and user_email.lower() == secondary.lower())
    )


def lambda_handler(event, context):
    """Handle PUT /presmeet/orders/{id}"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # --- Authentication ---
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate PresMeet access (Regio_Pressmeet or Regio_All required)
        if not has_presmeet_access(user_roles):
            return create_error_response(
                403, 'Access denied: Requires Regio_Pressmeet or Regio_All'
            )

        # Determine if user is admin
        admin = is_presmeet_admin(user_roles)

        # --- Extract order_id from path ---
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # --- Parse request body ---
        body = json.loads(event.get('body') or '{}')
        items = body.get('items')
        version = body.get('version')

        if items is None:
            return create_error_response(400, 'items field is required')
        if version is None:
            return create_error_response(400, 'version field is required for optimistic locking')

        # Ensure version is an integer
        try:
            version = int(version)
        except (TypeError, ValueError):
            return create_error_response(400, 'version must be an integer')

        # --- Fetch current order ---
        order_response = table.get_item(Key={'order_id': order_id})
        order = order_response.get('Item')

        if not order:
            return create_error_response(404, 'Order not found')

        # --- Authorization: check user is delegate or admin ---
        if not admin:
            # Non-admin: must have a club_id and be a delegate on this order
            club_id = get_club_id(user_email)
            if not club_id:
                return create_error_response(
                    403, 'Missing club assignment. Please complete onboarding first.'
                )
            # Check club matches
            if order.get('club_id') != club_id:
                return create_error_response(403, 'Access denied: order belongs to a different club')
            # Check delegate status
            if not _is_delegate(order, user_email):
                return create_error_response(403, 'Access denied: you are not a delegate on this order')

        # --- Status check ---
        current_status = order.get('status', 'draft')

        if current_status == 'locked' and not admin:
            return create_error_response(403, 'Order is locked')

        # --- Recalculate total_amount ---
        total_amount = _calculate_total_amount(items)

        # --- Build update expression ---
        now = datetime.now(timezone.utc).isoformat()
        new_version = version + 1

        update_expr_parts = [
            '#items = :items',
            '#version = :new_version',
            'updated_at = :now',
            'total_amount = :total_amount',
        ]
        expr_attr_names = {
            '#items': 'items',
            '#version': 'version',
        }
        expr_attr_values = {
            ':items': items,
            ':new_version': new_version,
            ':now': now,
            ':total_amount': total_amount,
            ':expected_version': version,
        }

        # Determine status transitions and status_history updates
        status_history_entry = None

        if admin and current_status == 'locked':
            # Admin editing locked order: keep status locked, record in status_history (Req 9.2)
            status_history_entry = {
                'from': 'locked',
                'to': 'locked',
                'at': now,
                'by': user_email,
                'source': 'admin',
            }
        elif not admin and current_status == 'submitted':
            # Delegate editing submitted order: revert to draft (Req 2.6)
            update_expr_parts.append('#current_status = :draft')
            expr_attr_names['#current_status'] = 'status'
            expr_attr_values[':draft'] = 'draft'
            status_history_entry = {
                'from': 'submitted',
                'to': 'draft',
                'at': now,
                'by': user_email,
                'source': 'delegate',
            }
        elif admin and current_status == 'submitted':
            # Admin editing submitted order: also revert to draft and record
            update_expr_parts.append('#current_status = :draft')
            expr_attr_names['#current_status'] = 'status'
            expr_attr_values[':draft'] = 'draft'
            status_history_entry = {
                'from': 'submitted',
                'to': 'draft',
                'at': now,
                'by': user_email,
                'source': 'admin',
            }

        # Append status_history entry if needed
        if status_history_entry:
            update_expr_parts.append(
                'status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)'
            )
            expr_attr_values[':history_entry'] = [status_history_entry]
            expr_attr_values[':empty_list'] = []

        update_expression = 'SET ' + ', '.join(update_expr_parts)

        # Condition: optimistic locking on version
        condition_expression = '#version = :expected_version'

        # --- Execute update ---
        try:
            update_response = table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values,
                ConditionExpression=condition_expression,
                ReturnValues='ALL_NEW',
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Version conflict — fetch current version to return to client
            current_order = table.get_item(Key={'order_id': order_id}).get('Item', {})
            current_version = current_order.get('version', 'unknown')
            return {
                'statusCode': 409,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'version_conflict',
                    'current_version': int(current_version) if isinstance(current_version, (int, float, Decimal)) else current_version,
                    'message': 'Order has been modified by another user. Please reload and try again.',
                }),
            }

        log_successful_access(user_email, user_roles, 'presmeet_upsert_order')

        # --- Build response ---
        updated_order = update_response.get('Attributes', {})
        # Convert Decimal fields to float for JSON serialization
        response_data = _serialize_order(updated_order)

        return create_success_response(response_data)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error in presmeet_upsert_order: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, 'Internal server error')


def _serialize_order(order):
    """Convert DynamoDB Decimal types to JSON-safe types."""
    if isinstance(order, dict):
        return {k: _serialize_order(v) for k, v in order.items()}
    elif isinstance(order, list):
        return [_serialize_order(i) for i in order]
    elif isinstance(order, Decimal):
        # Return int if whole number, else float
        if order % 1 == 0:
            return int(order)
        return float(order)
    return order
