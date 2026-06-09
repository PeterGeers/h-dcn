import json
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
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

        _fallback_handler = create_smart_fallback_handler("lock_presmeet_orders")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))


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

        # Check PresMeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(403, "PresMeet access required")

        # Admin check - only admin with write access can lock orders
        if not is_presmeet_admin_write(user_roles):
            return create_error_response(403, "Admin access required")

        # Log successful access
        log_successful_access(user_email, user_roles, "lock_presmeet_orders")

        # Parse request body
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except (json.JSONDecodeError, TypeError):
                return create_error_response(400, "Invalid JSON in request body")

        order_ids = body.get("order_ids")
        now = datetime.now(timezone.utc).isoformat()
        locked_count = 0

        if order_ids:
            # Lock specific orders by ID
            if not isinstance(order_ids, list):
                return create_error_response(400, "order_ids must be an array")

            for order_id in order_ids:
                # Get the order
                response = orders_table.get_item(Key={"order_id": order_id})
                order = response.get("Item")

                if not order:
                    continue

                # Verify it's a PresMeet order
                if order.get("source") != "presmeet":
                    continue

                # Only lock orders in "submitted" status
                if order.get("status") != "submitted":
                    continue

                # Transition to "locked"
                orders_table.update_item(
                    Key={"order_id": order_id},
                    UpdateExpression="SET #status = :status, updated_at = :updated_at",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "locked",
                        ":updated_at": now,
                    },
                )
                locked_count += 1
        else:
            # Lock ALL: scan all PresMeet orders, lock all "submitted" ones
            scan_response = orders_table.scan(
                FilterExpression=Attr("source").eq("presmeet")
                & Attr("status").eq("submitted")
            )
            submitted_orders = scan_response["Items"]

            # Handle pagination
            while "LastEvaluatedKey" in scan_response:
                scan_response = orders_table.scan(
                    FilterExpression=Attr("source").eq("presmeet")
                    & Attr("status").eq("submitted"),
                    ExclusiveStartKey=scan_response["LastEvaluatedKey"],
                )
                submitted_orders.extend(scan_response["Items"])

            # Lock each submitted order
            for order in submitted_orders:
                order_id = order["order_id"]
                orders_table.update_item(
                    Key={"order_id": order_id},
                    UpdateExpression="SET #status = :status, updated_at = :updated_at",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "locked",
                        ":updated_at": now,
                    },
                )
                locked_count += 1

        return create_success_response({"locked_count": locked_count})

    except Exception as e:
        print(f"Error in lock_presmeet_orders handler: {str(e)}")
        return create_error_response(500, "Internal server error")
