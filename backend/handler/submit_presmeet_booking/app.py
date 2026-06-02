import json
import os
from datetime import datetime, timezone
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
    from shared.presmeet_validation import extract_club_id, validate_order_submission

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("submit_presmeet_booking")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))
producten_table = dynamodb.Table(os.environ.get("PRODUCTEN_TABLE_NAME", "Producten"))
events_table = dynamodb.Table(os.environ.get("EVENTS_TABLE_NAME", "Events"))


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

        # Validate permissions - Club_User level access
        required_permissions = ["events_read"]
        is_authorized, error_response, regional_info = (
            validate_permissions_with_regions(
                user_roles, required_permissions, user_email, None
            )
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, "submit_presmeet_booking")

        # Extract club_id from Cognito groups
        club_id = extract_club_id(user_roles)
        if not club_id:
            return create_error_response(403, "Missing club assignment")

        # Load order from Orders table for this club
        scan_response = orders_table.scan(
            FilterExpression=Attr("source").eq("presmeet")
            & Attr("club_id").eq(club_id)
        )
        existing_orders = scan_response["Items"]

        # Handle pagination
        while "LastEvaluatedKey" in scan_response:
            scan_response = orders_table.scan(
                FilterExpression=Attr("source").eq("presmeet")
                & Attr("club_id").eq(club_id),
                ExclusiveStartKey=scan_response["LastEvaluatedKey"],
            )
            existing_orders.extend(scan_response["Items"])

        # Return 404 if no order exists
        if not existing_orders:
            return create_error_response(404, "Booking not found")

        order = existing_orders[0]

        # Verify club_id match (defense-in-depth, already filtered by scan)
        if order.get("club_id") != club_id:
            return create_error_response(403, "Access denied: club mismatch")

        # Verify order status is "draft" — cannot submit from submitted or locked
        current_status = order.get("status", "draft")
        if current_status != "draft":
            return create_error_response(
                409,
                f"Cannot submit order in {current_status} status"
            )

        # Load product type configs from Producten table
        config_response = producten_table.scan(
            FilterExpression=Attr("source").eq("presmeet_config")
        )
        config_items = config_response["Items"]

        while "LastEvaluatedKey" in config_response:
            config_response = producten_table.scan(
                FilterExpression=Attr("source").eq("presmeet_config"),
                ExclusiveStartKey=config_response["LastEvaluatedKey"],
            )
            config_items.extend(config_response["Items"])

        # Build config dict keyed by product_type
        config = {}
        for item in config_items:
            product_type = item.get("product_type")
            if product_type:
                config[product_type] = item

        # Load event from Events table
        events_response = events_table.scan(
            FilterExpression=Attr("source").eq("presmeet")
        )
        event_items = events_response["Items"]

        while "LastEvaluatedKey" in events_response:
            events_response = events_table.scan(
                FilterExpression=Attr("source").eq("presmeet"),
                ExclusiveStartKey=events_response["LastEvaluatedKey"],
            )
            event_items.extend(events_response["Items"])

        # Get the active event (first match, or empty dict)
        presmeet_event = event_items[0] if event_items else {}

        # Run full submission validation
        errors = validate_order_submission(order, config, presmeet_event)

        # If validation fails, return 400 with error list, keep order in "draft"
        if errors:
            return create_error_response(
                400,
                "Validation failed",
                {"errors": convert_decimals(errors)}
            )

        # Validation passed — transition order status to "submitted"
        now = datetime.now(timezone.utc).isoformat()

        orders_table.update_item(
            Key={"order_id": order["order_id"]},
            UpdateExpression="SET #status = :status, submitted_at = :submitted_at, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "submitted",
                ":submitted_at": now,
                ":updated_at": now,
            },
        )

        # Return success with the updated order
        order["status"] = "submitted"
        order["submitted_at"] = now
        order["updated_at"] = now

        return create_success_response(convert_decimals(order))

    except Exception as e:
        print(f"Error in submit_presmeet_booking handler: {str(e)}")
        return create_error_response(500, "Internal server error")
