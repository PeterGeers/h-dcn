"""
Unified order retrieval/creation handler.
Handles both webshop and event-scoped orders.
Replaces: get_presmeet_booking + webshop order retrieval.

Logic:
  1. Extract credentials, resolve member_id from email
  2. Read source_id from query params
  3. If source_id == "webshop": verify hdcnLeden, scope = "member"
  4. If source_id is event UUID: load event, check has_event_access, read order_scope
  5. If order_scope == "member": query GSI source_id + member_id, create draft if missing
  6. If order_scope == "club": resolve club_id, query GSI PK-only, filter by club_id,
     verify delegate access, create draft if missing
"""

import json
import os
import uuid
import base64
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
    from shared.event_access import has_event_access, verify_order_event_access
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_order")
    import sys
    sys.exit(0)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

GSI_NAME = 'event-member-index'


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


def _resolve_member_id(user_email):
    """
    Resolve member_id from the Members table by email scan.
    Returns (member_record, error_response) tuple.
    """
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email),
            ProjectionExpression='member_id, club_id, member_type, allowed_events'
        )
        items = response.get('Items', [])
        if not items:
            return None, create_error_response(404, 'Member record not found')
        return items[0], None
    except Exception as e:
        print(f"Error resolving member: {str(e)}")
        return None, create_error_response(500, 'Failed to resolve member record')


def _get_event(event_id):
    """Load an event record by event_id. Returns None if not found."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        return response.get('Item')
    except Exception:
        return None


def _query_orders_by_source_and_member(source_id, member_id):
    """Query GSI with source_id + member_id (full key)."""
    response = orders_table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key('source_id').eq(source_id) & Key('member_id').eq(member_id)
    )
    return response.get('Items', [])


def _query_orders_by_source(source_id):
    """Query GSI with source_id only (PK-only, returns all orders for this source)."""
    items = []
    response = orders_table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key('source_id').eq(source_id)
    )
    items.extend(response.get('Items', []))
    while response.get('LastEvaluatedKey'):
        response = orders_table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('source_id').eq(source_id),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    return items


def _create_draft_order(source_id, member_id, club_id=None, is_club_scope=False):
    """
    Create a new draft order and persist it.
    Returns the created order dict.
    """
    now = datetime.now(timezone.utc).isoformat()
    order = {
        'order_id': str(uuid.uuid4()),
        'source_id': source_id,
        'member_id': member_id,
        'status': 'draft',
        'items': [],
        'version': 1,
        'created_at': now,
        'updated_at': now,
    }

    if is_club_scope and club_id:
        order['club_id'] = club_id
        order['delegates'] = {
            'primary_member_id': member_id,
        }

    orders_table.put_item(Item=order)
    return order


def lambda_handler(event, context):
    """GET /booking?source_id={webshop|event_uuid}"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # No broad permission check here — access is controlled per-source:
        # - Webshop: requires hdcnLeden group (checked below)
        # - Events: requires has_event_access(member_id, event_id) (checked below)
        # This allows event_participant users to access their allowed events
        # without needing events_read admin permission.

        # 2. Get source_id from query params
        query_params = event.get('queryStringParameters') or {}
        source_id = query_params.get('source_id')
        if not source_id:
            return create_error_response(400, 'source_id query parameter is required')

        # 3. Resolve member record from email
        member_record, member_error = _resolve_member_id(user_email)
        if member_error:
            return member_error

        member_id = member_record['member_id']

        # 4/5. Branch on source_id
        if source_id == 'webshop':
            # --- Webshop source ---
            if 'hdcnLeden' not in user_roles:
                return create_error_response(403, 'Member access required')
            order_scope = 'member'
            event_record = None
        else:
            # --- Event source (UUID) ---
            event_record = _get_event(source_id)
            if not event_record:
                return create_error_response(404, 'Event not found')

            # Check event access via allowed_events
            if not has_event_access(member_id, source_id):
                return create_error_response(403, 'Event access required')

            # Check event status for new order creation
            # (we still allow viewing existing orders for non-open events)
            order_scope = event_record.get('order_scope', 'member')

        # Log access
        log_successful_access(user_email, user_roles, 'get_order')

        # 6/7. Order lookup by scope
        if order_scope == 'member':
            # --- Member-scoped: one order per member per source ---
            existing = _query_orders_by_source_and_member(source_id, member_id)
            if existing:
                return create_success_response(convert_decimals(existing[0]))

            # No existing order — check event status before creating
            if event_record and event_record.get('status') != 'open':
                return create_error_response(403, 'Registration is not open')

            # Create draft
            order = _create_draft_order(source_id, member_id)
            return create_success_response(convert_decimals(order), status_code=201)

        elif order_scope == 'club':
            # --- Club-scoped: one order per club ---
            club_id = member_record.get('club_id')
            if not club_id:
                return create_error_response(403, 'Club assignment required for this event')

            # Query all orders for this source, filter by club_id
            all_orders = _query_orders_by_source(source_id)
            club_order = next(
                (o for o in all_orders if o.get('club_id') == club_id), None
            )

            if club_order:
                # Verify requesting member is a delegate
                delegates = club_order.get('delegates', {})
                if member_id not in [
                    delegates.get('primary_member_id'),
                    delegates.get('secondary_member_id'),
                ]:
                    return create_error_response(403, 'You are not a delegate for this club')
                return create_success_response(convert_decimals(club_order))
            else:
                # No existing order — check event status before creating
                if event_record and event_record.get('status') != 'open':
                    return create_error_response(403, 'Registration is not open')

                # Create new order with requesting member as primary delegate
                order = _create_draft_order(
                    source_id, member_id, club_id=club_id, is_club_scope=True
                )
                return create_success_response(convert_decimals(order), status_code=201)

        else:
            return create_error_response(400, f'Unknown order_scope: {order_scope}')

    except Exception as e:
        print(f"Error in get_order handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
