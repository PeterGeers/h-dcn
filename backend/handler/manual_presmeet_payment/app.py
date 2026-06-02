import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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
    from shared.presmeet_validation import calculate_outstanding_balance

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("manual_presmeet_payment")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))
payments_table = dynamodb.Table(os.environ.get("PAYMENTS_TABLE_NAME", "Payments"))


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

        # Validate permissions - require events_read at minimum
        required_permissions = ["events_read"]
        is_authorized, error_response, regional_info = (
            validate_permissions_with_regions(
                user_roles, required_permissions, user_email, None
            )
        )
        if not is_authorized:
            return error_response

        # Admin check - only webmaster can record manual payments
        is_admin = "webmaster" in user_roles
        if not is_admin:
            return create_error_response(403, "Admin access required")

        # Log successful access
        log_successful_access(user_email, user_roles, "manual_presmeet_payment")

        # Parse request body
        if not event.get("body"):
            return create_error_response(400, "Request body is required")

        try:
            body = json.loads(event["body"])
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, "Invalid JSON in request body")

        # Validate required fields
        order_id = body.get("order_id")
        amount = body.get("amount")
        date = body.get("date")
        description = body.get("description")

        if not order_id:
            return create_error_response(400, "order_id is required")

        if amount is None:
            return create_error_response(400, "amount is required")

        if not date:
            return create_error_response(400, "date is required")

        if not description:
            return create_error_response(400, "description is required")

        # Validate amount (€0.01–€999,999.99)
        try:
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            return create_error_response(400, "amount must be a valid number")

        if amount_decimal < Decimal("0.01") or amount_decimal > Decimal("999999.99"):
            return create_error_response(
                400, "amount must be between €0.01 and €999,999.99"
            )

        # Validate description (max 255 chars)
        if not isinstance(description, str) or len(description) > 255:
            return create_error_response(
                400, "description must be a string of maximum 255 characters"
            )

        # Load order from Orders table
        response = orders_table.get_item(Key={"order_id": order_id})
        order = response.get("Item")

        if not order:
            return create_error_response(404, "Order not found")

        # Verify it's a PresMeet order
        if order.get("source") != "presmeet":
            return create_error_response(404, "Order not found")

        # Create payment record
        now = datetime.now(timezone.utc).isoformat()
        payment_id = str(uuid.uuid4())
        club_id = order.get("club_id")

        payment_record = {
            "payment_id": payment_id,
            "source": "presmeet",
            "order_id": order_id,
            "club_id": club_id,
            "amount": amount_decimal,
            "status": "paid",
            "provider": "manual",
            "description": description,
            "date": date,
            "created_at": now,
            "created_by": user_email,
        }

        payments_table.put_item(Item=payment_record)

        # Recalculate order payment_status based on outstanding balance
        # Load all payments for this order where status="paid"
        payments_response = payments_table.scan(
            FilterExpression=Attr("order_id").eq(order_id)
            & Attr("status").eq("paid")
            & Attr("source").eq("presmeet")
        )
        paid_payments = payments_response["Items"]

        # Handle pagination
        while "LastEvaluatedKey" in payments_response:
            payments_response = payments_table.scan(
                FilterExpression=Attr("order_id").eq(order_id)
                & Attr("status").eq("paid")
                & Attr("source").eq("presmeet"),
                ExclusiveStartKey=payments_response["LastEvaluatedKey"],
            )
            paid_payments.extend(payments_response["Items"])

        # Calculate outstanding balance
        order_total = Decimal(str(order.get("total_amount", 0)))
        outstanding = calculate_outstanding_balance(order_total, paid_payments)

        # Update order payment_status
        if outstanding == Decimal("0.00"):
            new_payment_status = "paid"
        else:
            new_payment_status = "partial"

        orders_table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET payment_status = :ps, updated_at = :updated_at",
            ExpressionAttributeValues={
                ":ps": new_payment_status,
                ":updated_at": now,
            },
        )

        # Return the created payment record
        # Convert Decimal to float for JSON serialization
        response_payment = {
            "payment_id": payment_id,
            "source": "presmeet",
            "order_id": order_id,
            "club_id": club_id,
            "amount": float(amount_decimal),
            "status": "paid",
            "provider": "manual",
            "description": description,
            "date": date,
            "created_at": now,
            "created_by": user_email,
            "payment_status": new_payment_status,
        }

        return create_success_response(response_payment)

    except Exception as e:
        print(f"Error in manual_presmeet_payment handler: {str(e)}")
        return create_error_response(500, "Internal server error")
