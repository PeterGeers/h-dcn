import json
import os
import uuid
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
    from shared.presmeet_validation import extract_club_id, calculate_cart_total

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("save_presmeet_booking")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE_NAME", "Orders"))

# Default max_per_club limits (used when Producten table config is not available)
MAX_PER_CLUB = {
    "meeting_ticket": 3,
    "party_ticket": 13,
    "tshirt": 13,
    "airport_transfer": 20,
}


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


def map_delegates_to_items(delegates):
    """
    Map delegate form entries to cart items.

    Each delegate produces:
    - 1 meeting_ticket (name, role)
    - Optionally 1 party_ticket (name, person_type="delegate") if party attendance selected
    - Optionally 1 tshirt (name, gender, size) if tshirt selected
    """
    items = []
    for delegate in delegates:
        name = delegate.get("name", "")
        role = delegate.get("role", "")

        # meeting_ticket for every delegate
        items.append(
            {
                "item_id": str(uuid.uuid4()),
                "product_type": "meeting_ticket",
                "attributes": {"name": name, "role": role},
            }
        )

        # party_ticket if party attendance selected
        if delegate.get("party", False):
            items.append(
                {
                    "item_id": str(uuid.uuid4()),
                    "product_type": "party_ticket",
                    "attributes": {"name": name, "person_type": "delegate"},
                }
            )

        # tshirt if selected
        tshirt = delegate.get("tshirt")
        if tshirt and isinstance(tshirt, dict):
            items.append(
                {
                    "item_id": str(uuid.uuid4()),
                    "product_type": "tshirt",
                    "attributes": {
                        "name": name,
                        "gender": tshirt.get("gender", ""),
                        "size": tshirt.get("size", ""),
                    },
                }
            )

    return items


def map_guests_to_items(guests):
    """
    Map guest form entries to cart items.

    Each guest produces:
    - 1 party_ticket (name, person_type="guest")
    - Optionally 1 tshirt (name, gender, size) if tshirt selected
    """
    items = []
    for guest in guests:
        name = guest.get("name", "")

        # party_ticket for every guest
        items.append(
            {
                "item_id": str(uuid.uuid4()),
                "product_type": "party_ticket",
                "attributes": {"name": name, "person_type": "guest"},
            }
        )

        # tshirt if selected
        tshirt = guest.get("tshirt")
        if tshirt and isinstance(tshirt, dict):
            items.append(
                {
                    "item_id": str(uuid.uuid4()),
                    "product_type": "tshirt",
                    "attributes": {
                        "name": name,
                        "gender": tshirt.get("gender", ""),
                        "size": tshirt.get("size", ""),
                    },
                }
            )

    return items


def map_transfers_to_items(transfers):
    """
    Map transfer form entries to cart items.

    Each transfer produces:
    - 1 airport_transfer (direction, airport, flight, date, time, persons)
    """
    items = []
    for transfer in transfers:
        items.append(
            {
                "item_id": str(uuid.uuid4()),
                "product_type": "airport_transfer",
                "attributes": {
                    "direction": transfer.get("direction", ""),
                    "airport": transfer.get("airport", ""),
                    "flight": transfer.get("flight", ""),
                    "date": transfer.get("date", ""),
                    "time": transfer.get("time", ""),
                    "persons": transfer.get("persons", 1),
                },
            }
        )
    return items


def validate_max_per_club(items):
    """
    Validate that items do not exceed max_per_club limits.

    Returns (is_valid, error_message) tuple.
    """
    type_counts = {}
    for item in items:
        pt = item.get("product_type")
        if pt:
            type_counts[pt] = type_counts.get(pt, 0) + 1

    for product_type, count in type_counts.items():
        max_allowed = MAX_PER_CLUB.get(product_type)
        if max_allowed is not None and count > max_allowed:
            return (
                False,
                f"Maximum {product_type} limit reached ({max_allowed}). "
                f"You have {count} items.",
            )

    return (True, None)


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

        # Validate permissions - Club_User level access (events_read covers hdcnLeden members)
        required_permissions = ["events_read"]
        is_authorized, error_response, regional_info = (
            validate_permissions_with_regions(
                user_roles, required_permissions, user_email, None
            )
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, "save_presmeet_booking")

        # Extract club_id from Cognito groups
        club_id = extract_club_id(user_roles)
        if not club_id:
            return create_error_response(403, "Missing club assignment")

        # Parse request body
        body = event.get("body")
        if not body:
            return create_error_response(400, "Invalid JSON in request body")

        try:
            form_data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, "Invalid JSON in request body")

        # Extract form sections
        delegates = form_data.get("delegates", [])
        guests = form_data.get("guests", [])
        transfers = form_data.get("transfers", [])

        # Map form data to typed cart items
        items = []
        items.extend(map_delegates_to_items(delegates))
        items.extend(map_guests_to_items(guests))
        items.extend(map_transfers_to_items(transfers))

        # Validate max_per_club limits BEFORE saving
        is_valid, error_msg = validate_max_per_club(items)
        if not is_valid:
            return create_error_response(400, error_msg)

        # Calculate total amount
        total_amount = calculate_cart_total(items)

        # Check for existing order for this club
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

        now = datetime.now(timezone.utc).isoformat()

        if existing_orders:
            existing_order = existing_orders[0]
            current_status = existing_order.get("status", "draft")

            # Reject if order is locked
            if current_status == "locked":
                return create_error_response(
                    409, "Order is locked and cannot be modified"
                )

            # Reuse existing order_id for upsert
            order_id = existing_order["order_id"]

            # Build updated order — transition submitted back to draft on modification
            order_record = {
                "order_id": order_id,
                "source": "presmeet",
                "club_id": club_id,
                "status": "draft",  # Always set to draft on save (Req 5.4)
                "payment_status": existing_order.get("payment_status", "unpaid"),
                "items": items,
                "total_amount": total_amount,
                "created_at": existing_order.get("created_at", now),
                "updated_at": now,
                "submitted_at": existing_order.get("submitted_at"),
                "created_by": existing_order.get("created_by", user_email),
            }
        else:
            # Create new order
            order_id = str(uuid.uuid4())
            order_record = {
                "order_id": order_id,
                "source": "presmeet",
                "club_id": club_id,
                "status": "draft",
                "payment_status": "unpaid",
                "items": items,
                "total_amount": total_amount,
                "created_at": now,
                "updated_at": now,
                "submitted_at": None,
                "created_by": user_email,
            }

        # Upsert order using put_item
        orders_table.put_item(Item=order_record)

        return create_success_response(convert_decimals(order_record))

    except Exception as e:
        print(f"Error in save_presmeet_booking handler: {str(e)}")
        return create_error_response(500, "Internal server error")
