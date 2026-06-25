"""
Admin Event Claims handler.

Routes based on httpMethod + path:
  GET    /admin/events/{event_id}/claims            → List all claims with labels, paginate at 50/page
  DELETE /admin/events/{event_id}/claims/{row_id}   → Release claim (remove from registry_claims, keep order)
  POST   /admin/events/{event_id}/claims/{row_id}   → Manually assign row (verify not already claimed, create draft order)

Supports:
  - Reassign primary delegate (POST with action=reassign_primary)
  - Remove secondary delegate (POST with action=remove_secondary)
  - Cancel pending invitation (POST with action=cancel_invitation)

Admin auth required: Products_CRUD, Regio_All, or System_CRUD.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict, NotRequired

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

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
    print("Using shared auth layer for admin_event_claims")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_event_claims")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
s3 = boto3.client('s3', region_name='eu-west-1')

REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')
PAGE_SIZE = 50

# Admin roles that grant access
ADMIN_ROLES = {'Products_CRUD', 'Regio_All', 'System_CRUD'}


# --- Types ---

class ClaimEntry(TypedDict):
    row_id: str
    label: str
    status: str  # 'available', 'claimed', 'pending'
    delegate_name: NotRequired[str]
    delegate_email: NotRequired[str]
    claimed_at: NotRequired[str]


# --- Auth ---

def _is_admin(user_roles: list[str]) -> bool:
    """Check if user has admin access."""
    return bool(set(user_roles) & ADMIN_ROLES)


# --- Helpers ---

def _get_event_with_claims(event_id: str) -> tuple[dict | None, str | None]:
    """Get event record with registry_claims. Returns (event, error)."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        item = response.get('Item')
        if not item:
            return None, 'Event not found'
        return item, None
    except ClientError as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        return None, 'Failed to fetch event'


def _get_s3_registry(s3_path: str) -> list[dict] | None:
    """Fetch the invitee registry from S3."""
    try:
        response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
        registry_data = json.loads(response['Body'].read().decode('utf-8'))
        return registry_data.get('rows', [])
    except Exception as e:
        logger.error(f"Error fetching S3 registry at {s3_path}: {e}")
        return None


def _find_member_by_email(email: str) -> dict | None:
    """Find a member record by email (case-insensitive)."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(email.lower()),
            Limit=10,
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error finding member by email: {e}")
        return None


def _find_order_for_row(event_id: str, registry_row_id: str) -> dict | None:
    """Find the non-cancelled order for a specific registry row in an event."""
    try:
        response = orders_table.scan(
            FilterExpression=(
                Attr('event_id').eq(event_id)
                & Attr('registry_row_id').eq(registry_row_id)
                & Attr('status').ne('cancelled')
            ),
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error finding order for row: {e}")
        return None


def _resolve_registry_row_data(event_id: str, registry_row_id: str) -> tuple[str | None, str | None]:
    """
    Resolve label and logo_url from S3 registry file for a given row_id.
    Returns (label, logo_url). Logo_url is None if not found or absent.
    """
    event_record, error = _get_event_with_claims(event_id)
    if error or not event_record:
        return None, None

    registry_config = event_record.get('registry_config', {})
    s3_path = registry_config.get('s3_path')
    if not s3_path:
        return None, None

    rows = _get_s3_registry(s3_path)
    if rows is None:
        return None, None

    for row in rows:
        if row.get('row_id') == registry_row_id:
            label = row.get('label')
            logo_url = row.get('logo_url', None)
            return label, logo_url

    return None, None


def _create_draft_order_for_claim(
    event_id: str,
    row_id: str,
    member_id: str,
    member_email: str,
) -> dict | None:
    """Create a draft order for a manually assigned row with registry row data resolved from S3."""
    now = datetime.now(timezone.utc).isoformat()

    # Resolve label and logo from S3 registry
    registry_row_label, registry_row_logo_url = _resolve_registry_row_data(event_id, row_id)

    order = {
        'order_id': str(uuid.uuid4()),
        'status': 'draft',
        'payment_status': 'unpaid',
        'event_id': event_id,
        'registry_row_id': row_id,
        'registry_row_label': registry_row_label,
        'registry_row_logo_url': registry_row_logo_url,
        'member_id': member_id,
        'user_email': member_email,
        'delegates': {
            'primary': member_email,
            'primary_member_id': member_id,
            'secondary': None,
            'secondary_member_id': None,
            'pending_secondary_email': None,
        },
        'items': [],
        'total_amount': Decimal('0'),
        'total_paid': Decimal('0'),
        'version': 1,
        'created_at': now,
        'updated_at': now,
    }

    try:
        orders_table.put_item(Item=order)
        return order
    except ClientError as e:
        logger.error(f"Error creating draft order: {e}")
        return None


def _convert_decimals(obj):
    """Recursively convert Decimal to int/float for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


# --- GET: List all claims ---

def _handle_list_claims(event_id: str, query_params: dict) -> dict:
    """
    List all registry rows with their claim status.
    Merges S3 registry with DynamoDB registry_claims.
    Paginates at 50 per page.
    """
    # Get event record
    event_record, error = _get_event_with_claims(event_id)
    if error:
        return create_error_response(404, error)

    registry_config = event_record.get('registry_config', {})
    registry_claims = event_record.get('registry_claims', {})
    s3_path = registry_config.get('s3_path')

    if not s3_path:
        return create_error_response(400, 'Event has no registry configured')

    # Fetch S3 registry
    s3_rows = _get_s3_registry(s3_path)
    if s3_rows is None:
        return create_error_response(500, 'Failed to load registry from S3')

    # Merge with claims
    merged: list[ClaimEntry] = []
    for row in s3_rows:
        row_id = row.get('row_id', '')
        label = row.get('label', row_id)
        claim = registry_claims.get(row_id)

        if claim:
            entry: ClaimEntry = {
                'row_id': row_id,
                'label': label,
                'status': 'claimed',
                'delegate_name': claim.get('name', ''),
                'delegate_email': claim.get('email', ''),
                'claimed_at': claim.get('claimed_at', ''),
            }
        else:
            entry = {
                'row_id': row_id,
                'label': label,
                'status': 'available',
            }
        merged.append(entry)

    # Sort alphabetically by label (case-insensitive)
    merged.sort(key=lambda x: x['label'].lower())

    # Pagination
    page = 1
    try:
        page = int(query_params.get('page', '1'))
    except (ValueError, TypeError):
        page = 1
    page = max(1, page)

    total_items = len(merged)
    total_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_items = merged[start_idx:end_idx]

    return create_success_response({
        'claims': page_items,
        'pagination': {
            'page': page,
            'page_size': PAGE_SIZE,
            'total_items': total_items,
            'total_pages': total_pages,
        },
        'row_label': registry_config.get('row_label', 'row'),
    })


# --- DELETE: Release claim ---

def _handle_release_claim(event_id: str, row_id: str) -> dict:
    """
    Release a claim: remove from registry_claims, keep the associated order.
    Req 13.2: Removes entry from Registry_Claims_Map, retains order.
    """
    # Verify event exists and row is claimed
    event_record, error = _get_event_with_claims(event_id)
    if error:
        return create_error_response(404, error)

    registry_claims = event_record.get('registry_claims', {})
    if row_id not in registry_claims:
        return create_error_response(404, 'Row is not claimed')

    # Remove claim from registry_claims map
    try:
        events_table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='REMOVE registry_claims.#row',
            ConditionExpression='attribute_exists(registry_claims.#row)',
            ExpressionAttributeNames={'#row': row_id},
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return create_error_response(404, 'Row is not claimed')
        logger.error(f"Error releasing claim: {e}")
        return create_error_response(500, 'Failed to release claim')

    return create_success_response({
        'message': f'Claim released for row {row_id}',
        'row_id': row_id,
    })


# --- POST: Manual assign or delegate actions ---

def _handle_post_action(event_id: str, row_id: str, body: dict) -> dict:
    """
    Route POST requests based on 'action' field:
    - (default/assign): manually assign row to a member
    - reassign_primary: reassign primary delegate on the order
    - remove_secondary: remove secondary delegate from order
    - cancel_invitation: cancel pending secondary invitation
    """
    action = body.get('action', 'assign')

    if action == 'assign':
        return _handle_manual_assign(event_id, row_id, body)
    elif action == 'reassign_primary':
        return _handle_reassign_primary(event_id, row_id, body)
    elif action == 'remove_secondary':
        return _handle_remove_secondary(event_id, row_id)
    elif action == 'cancel_invitation':
        return _handle_cancel_invitation(event_id, row_id)
    else:
        return create_error_response(400, f'Unknown action: {action}')


def _handle_manual_assign(event_id: str, row_id: str, body: dict) -> dict:
    """
    Manually assign a row to a member (identified by email).
    Req 13.4: Write claim + create draft order.
    Req 13.5: If already claimed, show current claimant, require release first.
    """
    email = body.get('email', '').strip().lower()
    if not email or '@' not in email:
        return create_error_response(400, 'Valid email is required')

    # Get event record
    event_record, error = _get_event_with_claims(event_id)
    if error:
        return create_error_response(404, error)

    registry_claims = event_record.get('registry_claims', {})

    # Req 13.5: Check if row is already claimed
    if row_id in registry_claims:
        existing = registry_claims[row_id]
        return create_error_response(409, {
            'message': 'Row is already claimed. Release the existing claim first.',
            'current_claimant': {
                'name': existing.get('name', ''),
                'email': existing.get('email', ''),
                'claimed_at': existing.get('claimed_at', ''),
            },
        })

    # Find member by email
    member = _find_member_by_email(email)
    if not member:
        return create_error_response(404, f'No member found with email: {email}')

    member_id = member['member_id']
    member_name = member.get('name', email)

    # Write claim to registry_claims (conditional write for safety)
    now = datetime.now(timezone.utc).isoformat()
    claim_data = {
        'member_id': member_id,
        'email': email,
        'name': member_name,
        'claimed_at': now,
    }

    try:
        events_table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='SET registry_claims.#row = :claim',
            ConditionExpression='attribute_not_exists(registry_claims.#row)',
            ExpressionAttributeNames={'#row': row_id},
            ExpressionAttributeValues={':claim': claim_data},
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return create_error_response(409, 'Row was claimed by another user concurrently')
        logger.error(f"Error writing claim: {e}")
        return create_error_response(500, 'Failed to write claim')

    # Check for existing order for this row
    existing_order = _find_order_for_row(event_id, row_id)
    order_id = None

    if existing_order:
        order_id = existing_order.get('order_id')
    else:
        # Create draft order
        new_order = _create_draft_order_for_claim(event_id, row_id, member_id, email)
        if new_order:
            order_id = new_order['order_id']
        else:
            logger.warning(f"Failed to create draft order for row {row_id}")

    return create_success_response({
        'message': f'Row {row_id} assigned to {email}',
        'row_id': row_id,
        'member_id': member_id,
        'order_id': order_id,
        'claim': claim_data,
    })


def _handle_reassign_primary(event_id: str, row_id: str, body: dict) -> dict:
    """
    Reassign the primary delegate on the order for this row.
    Req 13.6: Support reassign primary delegate.
    """
    new_email = body.get('email', '').strip().lower()
    if not new_email or '@' not in new_email:
        return create_error_response(400, 'Valid email is required for new primary delegate')

    # Find the order for this row
    order = _find_order_for_row(event_id, row_id)
    if not order:
        return create_error_response(404, 'No order found for this row')

    # Find member by email
    member = _find_member_by_email(new_email)
    if not member:
        return create_error_response(404, f'No member found with email: {new_email}')

    new_member_id = member['member_id']
    new_name = member.get('name', new_email)
    order_id = order['order_id']

    # Update order delegates
    now = datetime.now(timezone.utc).isoformat()
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.#primary_key = :email, '
                'delegates.primary_member_id = :mid, '
                'member_id = :mid, '
                'user_email = :email, '
                'updated_at = :now'
            ),
            ExpressionAttributeNames={
                '#primary_key': 'primary',
            },
            ExpressionAttributeValues={
                ':email': new_email,
                ':mid': new_member_id,
                ':now': now,
            },
        )
    except ClientError as e:
        logger.error(f"Error reassigning primary delegate: {e}")
        return create_error_response(500, 'Failed to reassign primary delegate')

    # Update the claim in registry_claims to reflect new owner
    try:
        events_table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='SET registry_claims.#row.member_id = :mid, registry_claims.#row.email = :email, registry_claims.#row.#nm = :name',
            ExpressionAttributeNames={'#row': row_id, '#nm': 'name'},
            ExpressionAttributeValues={
                ':mid': new_member_id,
                ':email': new_email,
                ':name': new_name,
            },
        )
    except ClientError as e:
        logger.warning(f"Failed to update claim after reassign: {e}")

    return create_success_response({
        'message': f'Primary delegate reassigned to {new_email}',
        'order_id': order_id,
        'new_primary_member_id': new_member_id,
    })


def _handle_remove_secondary(event_id: str, row_id: str) -> dict:
    """
    Remove secondary delegate from the order for this row.
    Req 13.6: Support remove secondary delegate.
    """
    order = _find_order_for_row(event_id, row_id)
    if not order:
        return create_error_response(404, 'No order found for this row')

    order_id = order['order_id']
    delegates = order.get('delegates', {})

    if not delegates.get('secondary_member_id') and not delegates.get('secondary'):
        return create_error_response(400, 'No secondary delegate to remove')

    now = datetime.now(timezone.utc).isoformat()
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.secondary = :null, '
                'delegates.secondary_member_id = :null, '
                'updated_at = :now'
            ),
            ExpressionAttributeValues={
                ':null': None,
                ':now': now,
            },
        )
    except ClientError as e:
        logger.error(f"Error removing secondary delegate: {e}")
        return create_error_response(500, 'Failed to remove secondary delegate')

    return create_success_response({
        'message': 'Secondary delegate removed',
        'order_id': order_id,
    })


def _handle_cancel_invitation(event_id: str, row_id: str) -> dict:
    """
    Cancel a pending secondary delegate invitation for the order on this row.
    Req 13.6: Support cancel pending invitation.
    """
    order = _find_order_for_row(event_id, row_id)
    if not order:
        return create_error_response(404, 'No order found for this row')

    order_id = order['order_id']
    delegates = order.get('delegates', {})

    if not delegates.get('pending_secondary_email'):
        return create_error_response(400, 'No pending invitation to cancel')

    now = datetime.now(timezone.utc).isoformat()
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.pending_secondary_email = :null, '
                'updated_at = :now'
            ),
            ExpressionAttributeValues={
                ':null': None,
                ':now': now,
            },
        )
    except ClientError as e:
        logger.error(f"Error cancelling invitation: {e}")
        return create_error_response(500, 'Failed to cancel invitation')

    return create_success_response({
        'message': 'Pending invitation cancelled',
        'order_id': order_id,
    })


# --- Main Handler ---

def lambda_handler(event, context):
    """Admin Event Claims — Routes based on httpMethod + path."""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Authorization: admin only
        if not _is_admin(user_roles):
            return create_error_response(403, 'Access denied: admin role required')

        log_successful_access(user_email, user_roles, 'admin_event_claims')

        # Extract path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        row_id = path_params.get('row_id')

        if not event_id:
            return create_error_response(400, 'Missing event_id parameter')

        http_method = event.get('httpMethod', '').upper()
        query_params = event.get('queryStringParameters') or {}

        # Route based on method
        if http_method == 'GET':
            return _handle_list_claims(event_id, query_params)

        elif http_method == 'DELETE':
            if not row_id:
                return create_error_response(400, 'Missing row_id parameter for DELETE')
            return _handle_release_claim(event_id, row_id)

        elif http_method == 'POST':
            if not row_id:
                return create_error_response(400, 'Missing row_id parameter for POST')
            try:
                body = json.loads(event.get('body') or '{}')
            except (json.JSONDecodeError, TypeError):
                return create_error_response(400, 'Invalid JSON body')
            return _handle_post_action(event_id, row_id, body)

        else:
            return create_error_response(405, 'Method not allowed')

    except Exception as e:
        logger.error(f"Error in admin_event_claims: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
