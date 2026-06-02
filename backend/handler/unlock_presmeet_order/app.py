import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import is_presmeet_admin_write, has_presmeet_access

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("unlock_presmeet_order")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))


def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def lambda_handler(event, context):
    if not _IMPORTS_AVAILABLE:
        if _fallback_handler:
            return _fallback_handler(event, context)
        return {"statusCode": 503, "body": "Service unavailable"}

    try:
        # Handle OPTIONS request
        if event.get("httpMethod") == "OPTIONS":
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Gate: check Regio_Pressmeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(403, "PresMeet access required")

        # Admin-only: check user has PresMeet admin write access
        if not is_presmeet_admin_write(user_roles):
            return create_error_response(403, "Admin access required")

        # Log successful access
        log_successful_access(user_email, user_roles, "unlock_presmeet_order")

        # Get order_id from path parameter
        path_params = event.get("pathParameters") or {}
        order_id = path_params.get("order_id")
        if not order_id:
            return create_error_response(400, "Missing order_id path parameter")

        # Load order from Orders table by order_id
        response = orders_table.get_item(Key={"order_id": order_id})
        order = response.get("Item")

        # Verify order exists
        if not order:
            return create_error_response(404, "Booking not found")

        # Verify order is a PresMeet order
        if order.get("source") != "presmeet":
            return create_error_response(404, "Booking not found")

        # Verify order status is "locked"
        current_status = order.get("status", "draft")
        if current_status != "locked":
            return create_error_response(
                409,
                f"Cannot unlock order in {current_status} status",
            )

        # Transition status to "submitted"
        now = datetime.now(timezone.utc).isoformat()

        orders_table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET #status = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "submitted",
                ":updated_at": now,
            },
        )

        # Return the updated order
        order["status"] = "submitted"
        order["updated_at"] = now

        return create_success_response(convert_decimals(order))

    except Exception as e:
        print(f"Error in unlock_presmeet_order handler: {str(e)}")
        return create_error_response(500, "Internal server error")
