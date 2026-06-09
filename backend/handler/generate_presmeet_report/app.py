import json
import os
import csv
import time
import io
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
    from shared.club_identity import is_presmeet_admin, has_presmeet_access

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("generate_presmeet_report")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))
payments_table = dynamodb.Table(os.environ.get("PAYMENTS_TABLE_NAME", "Payments"))

s3_client = boto3.client("s3")
S3_REPORTS_BUCKET = os.environ.get("S3_REPORTS_BUCKET", "h-dcn-reports")
S3_PREFIX = "presmeet/"


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def scan_all_items(table, filter_expression):
    """Scan a DynamoDB table with pagination support."""
    response = table.scan(FilterExpression=filter_expression)
    items = response["Items"]

    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=filter_expression,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])

    return items


def compute_aggregates(orders, payments):
    """Compute summary aggregates from orders and payments.

    Returns:
        dict with summary (total_orders, by_status, by_product_type) and
        payments (total_charged, total_paid, total_outstanding)
    """
    # Count orders by status
    by_status = {"draft": 0, "submitted": 0, "locked": 0}
    for order in orders:
        status = order.get("status", "draft")
        if status in by_status:
            by_status[status] += 1

    # Count items per product_type per status
    by_product_type = {}
    for order in orders:
        status = order.get("status", "draft")
        items = order.get("items", [])
        for item in items:
            product_type = item.get("product_type", "unknown")
            if product_type not in by_product_type:
                by_product_type[product_type] = {"draft": 0, "submitted": 0, "locked": 0}
            if status in by_product_type[product_type]:
                by_product_type[product_type][status] += 1

    # Payment aggregates across submitted and locked orders
    total_charged = Decimal("0")
    total_paid = Decimal("0")

    for order in orders:
        status = order.get("status", "draft")
        if status in ("submitted", "locked"):
            total_charged += Decimal(str(order.get("total_amount", 0)))

    # Sum paid payments
    for payment in payments:
        if payment.get("status") == "paid":
            total_paid += Decimal(str(payment.get("amount", 0)))

    total_outstanding = max(Decimal("0"), total_charged - total_paid)

    return {
        "summary": {
            "total_orders": len(orders),
            "by_status": by_status,
            "by_product_type": by_product_type,
        },
        "payments": {
            "total_charged": total_charged,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
        },
    }


def build_order_list(orders, payments):
    """Build the order list with payment summaries per order.

    Returns:
        list of order summary dicts
    """
    # Group payments by order_id (only paid ones)
    payments_by_order = {}
    for payment in payments:
        if payment.get("status") == "paid":
            order_id = payment.get("order_id")
            if order_id:
                if order_id not in payments_by_order:
                    payments_by_order[order_id] = []
                payments_by_order[order_id].append(payment)

    order_list = []
    for order in orders:
        order_id = order.get("order_id")
        total_amount = Decimal(str(order.get("total_amount", 0)))

        # Calculate total paid for this order
        order_payments = payments_by_order.get(order_id, [])
        total_paid = sum(
            Decimal(str(p.get("amount", 0))) for p in order_payments
        )
        outstanding = max(Decimal("0"), total_amount - total_paid)

        # Determine payment status
        if total_paid == Decimal("0"):
            payment_status = "unpaid"
        elif outstanding == Decimal("0"):
            payment_status = "paid"
        else:
            payment_status = "partial"

        # Count items by product_type
        item_counts = {}
        items = order.get("items", [])
        for item in items:
            product_type = item.get("product_type", "unknown")
            item_counts[product_type] = item_counts.get(product_type, 0) + 1

        order_entry = {
            "order_id": order_id,
            "club_id": order.get("club_id"),
            "club_name": order.get("club_name", order.get("club_id", "")),
            "status": order.get("status"),
            "payment_status": payment_status,
            "total_amount": total_amount,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "item_counts": item_counts,
            "created_at": order.get("created_at"),
            "updated_at": order.get("updated_at"),
            "submitted_at": order.get("submitted_at"),
        }
        order_list.append(order_entry)

    return order_list


def generate_csv(orders, filter_statuses=None):
    """Generate CSV export from orders.

    Args:
        orders: list of order records (raw from DynamoDB)
        filter_statuses: if set, only include orders with these statuses.
                         None means include all.

    Returns:
        CSV string with columns: club_name, order_status, product_type, quantity, unit_price, attribute values
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "club_name",
        "order_status",
        "product_type",
        "quantity",
        "unit_price",
        "attributes",
    ])

    for order in orders:
        status = order.get("status", "draft")

        # Apply filter if specified
        if filter_statuses and status not in filter_statuses:
            continue

        club_name = order.get("club_name", order.get("club_id", ""))
        items = order.get("items", [])

        for item in items:
            product_type = item.get("product_type", "")
            unit_price = item.get("unit_price", "")
            attributes = item.get("attributes", {})

            # Format attributes as key=value pairs
            attr_str = "; ".join(
                f"{k}={v}" for k, v in sorted(attributes.items())
            ) if attributes else ""

            writer.writerow([
                club_name,
                status,
                product_type,
                1,  # quantity is 1 per row (one row per item)
                str(unit_price),
                attr_str,
            ])

    return output.getvalue()


def write_to_s3(key, content, content_type="application/json"):
    """Write content to S3 bucket."""
    s3_client.put_object(
        Bucket=S3_REPORTS_BUCKET,
        Key=f"{S3_PREFIX}{key}",
        Body=content.encode("utf-8") if isinstance(content, str) else content,
        ContentType=content_type,
    )


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

        # Access gate - require PresMeet region role
        if not has_presmeet_access(user_roles):
            return create_error_response(403, "PresMeet access required")

        # Admin check - only PresMeet admins can generate reports
        if not is_presmeet_admin(user_roles):
            return create_error_response(403, "Admin access required")

        # Log successful access
        log_successful_access(user_email, user_roles, "generate_presmeet_report")

        # Track generation time
        start_time = time.time()
        now = datetime.now(timezone.utc).isoformat()

        # Scan Orders table for all PresMeet records
        orders = scan_all_items(
            orders_table, Attr("source").eq("presmeet")
        )

        # Scan Payments table for all PresMeet records
        payments = scan_all_items(
            payments_table, Attr("source").eq("presmeet")
        )

        # Compute aggregates
        aggregates = compute_aggregates(orders, payments)

        # Build order list with payment summaries
        order_list = build_order_list(orders, payments)

        # Count total items across all orders
        total_items = sum(
            len(order.get("items", [])) for order in orders
        )

        # Generate CSV exports
        csv_submitted = generate_csv(orders, filter_statuses={"submitted"})
        csv_all = generate_csv(orders, filter_statuses=None)

        # Build overview.json
        overview = {
            "generated_at": now,
            "generated_by": user_email,
            "summary": aggregates["summary"],
            "payments": aggregates["payments"],
        }

        # Build orders.json
        orders_report = {
            "generated_at": now,
            "orders": order_list,
        }

        # Calculate generation duration
        end_time = time.time()
        generation_duration_ms = int((end_time - start_time) * 1000)

        # Build metadata.json
        metadata = {
            "generated_at": now,
            "generated_by": user_email,
            "total_orders": len(orders),
            "total_items": total_items,
            "generation_duration_ms": generation_duration_ms,
        }

        # Write all files to S3
        try:
            write_to_s3(
                "overview.json",
                json.dumps(overview, cls=DecimalEncoder),
            )
            write_to_s3(
                "orders.json",
                json.dumps(orders_report, cls=DecimalEncoder),
            )
            write_to_s3(
                "export_submitted.csv",
                csv_submitted,
                content_type="text/csv",
            )
            write_to_s3(
                "export_all.csv",
                csv_all,
                content_type="text/csv",
            )
            write_to_s3(
                "metadata.json",
                json.dumps(metadata, cls=DecimalEncoder),
            )
        except Exception as e:
            print(f"S3 write error: {str(e)}")
            return create_error_response(502, "Report generation failed")

        # Return success with generation metadata
        return create_success_response({
            "generated_at": now,
            "total_orders": len(orders),
            "total_items": total_items,
            "generation_duration_ms": generation_duration_ms,
        })

    except Exception as e:
        print(f"Error in generate_presmeet_report handler: {str(e)}")
        return create_error_response(500, "Internal server error")
