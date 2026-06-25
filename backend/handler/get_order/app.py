"""
Unified order retrieval/creation handler.
Handles both webshop and event-scoped orders.
Replaces: get_presmeet_booking + webshop order retrieval.

Logic:
  1. Extract credentials, resolve member_id from email
  2. Read source_id from query params
  3. If source_id == "webshop": verify hdcnLeden, scope = "member"
  4. If source_id is event UUID: load event, check has_event_access, derive order scope
  5. If scope == "member": query GSI source_id + member_id, create draft if missing
  6. If scope == "registry_row": resolve registry_row_id, query GSI PK-only, filter by
     registry_row_id, verify delegate access, create draft if missing
"""

import json
import os
import uuid
import base64
import logging
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

# S3 client for registry file
s3 = boto3.client('s3', region_name='eu-west-1')
REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
            ProjectionExpression='member_id, registry_row_id, member_type, allowed_events'
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


def _create_draft_order(
    source_id: str,
    member_id: str,
    registry_row_id: str | None = None,
    registry_row_label: str | None = None,
    registry_row_logo_url: str | None = None,
    is_row_scope: bool = False,
) -> dict:
    """
    Create a new draft order and persist it.
    For row-scoped orders, stores registry_row_id, label, and logo_url.
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

    if is_row_scope and registry_row_id:
        order['registry_row_id'] = registry_row_id
        order['registry_row_label'] = registry_row_label
        order['registry_row_logo_url'] = registry_row_logo_url
        order['delegates'] = {
            'primary_member_id': member_id,
        }

    orders_table.put_item(Item=order)
    return order


def _resolve_order_scope(event_record: dict) -> str:
    """
    Derive order scope from event config.
    If registry_config exists → row-scoped (one order per registry row).
    Otherwise → member-scoped (one order per member).
    """
    if event_record.get('registry_config'):
        return 'registry_row'
    return 'member'


def _resolve_registry_row_data(event_record: dict, registry_row_id: str) -> tuple[str | None, str | None]:
    """
    Resolve label and logo_url from S3 registry file for a given row_id.
    Returns (label, logo_url). Logo_url is None if not found or absent.
    """
    registry_config = event_record.get('registry_config', {})
    s3_path = registry_config.get('s3_path')
    if not s3_path:
        return None, None

    try:
        response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
        registry_data = json.loads(response['Body'].read().decode('utf-8'))
        rows = registry_data.get('rows', [])
    except Exception as e:
        logger.error(f"Error fetching S3 registry at {s3_path}: {e}")
        return None, None

    for row in rows:
        if row.get('row_id') == registry_row_id:
            label = row.get('label')
            logo_url = row.get('logo_url', None)
            return label, logo_url

    return None, None


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

            # Check event access:
            # - Open events: any authenticated member (hdcnLeden) can access
            # - Closed events: member must be in allowed_events
            participation = event_record.get('participation', 'open')
            if participation == 'closed':
                if not has_event_access(member_id, source_id):
                    return create_error_response(403, 'Event access required')
            else:
                # Open event: any logged-in member can book
                if 'hdcnLeden' not in user_roles and not has_event_access(member_id, source_id):
                    return create_error_response(403, 'Member access required for open events')

            # Check event status for new order creation
            # (we still allow viewing existing orders for non-open events)
            order_scope = _resolve_order_scope(event_record)

        # Log access
        log_successful_access(user_email, user_roles, 'get_order')

        # 6/7. Order lookup by scope
        if order_scope == 'member':
            # --- Member-scoped: one order per member per source ---
            existing = _query_orders_by_source_and_member(source_id, member_id)
            if existing:
                return create_success_response(convert_decimals(existing[0]))

            # No existing order — check event status before creating
            if event_record and event_record.get('status') != 'published':
                return create_error_response(403, 'Registration is not open')

            # Create draft
            order = _create_draft_order(source_id, member_id)
            return create_success_response(convert_decimals(order), status_code=201)

        elif order_scope == 'registry_row':
            # --- Registry-row-scoped: one order per registry row ---
            registry_row_id = member_record.get('registry_row_id')
            if not registry_row_id:
                return create_error_response(
                    403, 'Registry row required for this event',
                    details={'error_code': 'REGISTRY_ROW_REQUIRED'}
                )

            # Query all orders for this source, filter by registry_row_id
            all_orders = _query_orders_by_source(source_id)
            row_order = next(
                (o for o in all_orders if o.get('registry_row_id') == registry_row_id), None
            )

            if row_order:
                # Verify requesting member is a delegate
                delegates = row_order.get('delegates', {})
                if member_id not in [
                    delegates.get('primary_member_id'),
                    delegates.get('secondary_member_id'),
                ]:
                    return create_error_response(403, 'You are not a delegate for this registry row')
                return create_success_response(convert_decimals(row_order))
            else:
                # No existing order — check event status before creating
                if event_record and event_record.get('status') != 'published':
                    return create_error_response(403, 'Registration is not open')

                # Resolve label and logo from S3 registry
                registry_row_label, registry_row_logo_url = _resolve_registry_row_data(
                    event_record, registry_row_id
                )

                # Create new order with requesting member as primary delegate
                order = _create_draft_order(
                    source_id,
                    member_id,
                    registry_row_id=registry_row_id,
                    registry_row_label=registry_row_label,
                    registry_row_logo_url=registry_row_logo_url,
                    is_row_scope=True,
                )
                return create_success_response(convert_decimals(order), status_code=201)

        else:
            return create_error_response(
                400, 'Invalid order scope',
                details={'error_code': 'INVALID_ORDER_SCOPE'}
            )

    except Exception as e:
        print(f"Error in get_order handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
