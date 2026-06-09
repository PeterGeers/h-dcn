"""
PresMeet Get Order handler.

GET /presmeet/orders?event_id=X

Retrieves the club's order for a given event. If no order exists and the event
is open, auto-creates a draft order. Uses the event-club-index GSI for efficient
queries and conditional PutItem to prevent duplicate creation (race condition).

Requirements: 1, 15
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Import shared auth layer
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
    from shared.club_identity import get_club_id, has_presmeet_access, is_presmeet_admin
    print("Using shared auth layer for presmeet_get_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("presmeet_get_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

# GSI name for event+club queries
EVENT_CLUB_INDEX = 'event-club-index'


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
    """Main handler for GET /presmeet/orders?event_id=X."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Gate: require Regio_Pressmeet or Regio_All
        if not has_presmeet_access(user_roles):
            return create_error_response(403, 'PresMeet access required', {
                'required_roles': ['Regio_Pressmeet', 'Regio_All'],
            })

        log_successful_access(user_email, user_roles, 'presmeet_get_order')

        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        event_id = query_params.get('event_id')

        if not event_id:
            return create_error_response(400, 'event_id query parameter is required')

        # Determine admin status
        is_admin = is_presmeet_admin(user_roles)

        # Resolve club_id
        if is_admin and 'club_id' in query_params:
            # Admin can query any club via query parameter
            club_id = query_params['club_id']
        elif is_admin:
            # Admin without club_id param: try member record, but don't block access
            club_id = get_club_id(user_email)
            if not club_id:
                # Admin has no personal club — return empty response (they use admin tab)
                return create_success_response({
                    'admin_no_club': True,
                    'message': 'No personal club assignment. Use admin tab to manage orders.',
                })
        else:
            # Regular user: resolve club from member record
            club_id = get_club_id(user_email)
            if not club_id:
                return create_error_response(403, 'Missing club assignment', {
                    'details': 'Club assignment is required before booking. '
                               'Please complete the onboarding flow first.',
                })

        # Query for existing order using GSI
        existing_order = _query_order_by_event_and_club(event_id, club_id)

        if existing_order:
            # Validate user is authorized to view this order
            auth_check = _check_order_access(existing_order, user_email, is_admin)
            if auth_check:
                return auth_check

            return create_success_response(convert_decimals(existing_order))

        # No existing order — check event status to decide action
        event_record = _get_event(event_id)
        if not event_record:
            return create_error_response(404, 'Event not found', {
                'event_id': event_id,
            })

        event_status = event_record.get('status', '')

        if event_status != 'open':
            return create_error_response(403, 'Registration is not active', {
                'event_id': event_id,
                'event_status': event_status,
                'details': 'Orders can only be created when the event is in open status.',
            })

        # Auto-create draft order
        new_order = _create_draft_order(event_id, club_id, user_email, event_record)
        if new_order is None:
            # Race condition: another request already created the order
            # Re-query and return it
            existing_order = _query_order_by_event_and_club(event_id, club_id)
            if existing_order:
                return create_success_response(convert_decimals(existing_order))
            # Should not happen, but handle gracefully
            return create_error_response(500, 'Failed to create or retrieve order')

        return create_success_response(convert_decimals(new_order), status_code=201)

    except Exception as e:
        logger.error(f"Error in presmeet_get_order: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _query_order_by_event_and_club(event_id, club_id):
    """
    Query the event-club-index GSI for an order matching event_id + club_id.
    Returns the order dict or None.
    """
    try:
        response = orders_table.query(
            IndexName=EVENT_CLUB_INDEX,
            KeyConditionExpression=Key('event_id').eq(event_id) & Key('club_id').eq(club_id),
        )
        items = response.get('Items', [])
        if items:
            return items[0]
        return None
    except ClientError as e:
        logger.error(f"Error querying GSI: {e}")
        raise


def _get_event(event_id):
    """Fetch event record from Events table."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        raise


def _create_draft_order(event_id, club_id, user_email, event_record):
    """
    Create a new draft order with conditional PutItem to prevent duplicates.
    Uses attribute_not_exists(order_id) to ensure only one order is created
    per club+event combination.

    Returns the new order dict, or None if a duplicate was detected (race condition).
    """
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    new_order = {
        'order_id': order_id,
        'club_id': club_id,
        'event_id': event_id,
        'event_type': 'presmeet',
        'channel': 'presmeet',
        'status': 'draft',
        'payment_status': 'unpaid',
        'total_amount': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'items': [],
        'delegates': {
            'primary': user_email,
            'secondary': None,
        },
        'version': 1,
        'status_history': [],
        'created_at': now,
        'updated_at': now,
        'created_by': user_email,
    }

    try:
        orders_table.put_item(
            Item=new_order,
            ConditionExpression=Attr('order_id').not_exists(),
        )
        logger.info(f"Created draft order {order_id} for club {club_id}, event {event_id}")
        return new_order
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Another request already created an order with this order_id (extremely unlikely)
            # or race condition — re-query the GSI
            logger.warning(
                f"Conditional put failed for club {club_id}, event {event_id} — "
                f"likely race condition"
            )
            return None
        raise


def _check_order_access(order, user_email, is_admin):
    """
    Validate user is authorized to access this order.
    Returns an error response if unauthorized, or None if authorized.
    """
    if is_admin:
        return None

    delegates = order.get('delegates', {})
    primary = delegates.get('primary', '')
    secondary = delegates.get('secondary')

    if user_email.lower() == (primary or '').lower():
        return None
    if secondary and user_email.lower() == secondary.lower():
        return None

    return create_error_response(403, 'Access denied: You are not a delegate for this order', {
        'details': 'Only the primary or secondary delegate can access this order.',
    })
