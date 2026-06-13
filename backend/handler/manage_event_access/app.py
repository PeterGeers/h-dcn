"""
Admin handler for managing event access (grant/revoke).
Two endpoints served from the same CodeUri:
  - POST /admin/events/{event_id}/access  → grant or revoke event access for members
  - GET  /admin/events/{event_id}/access  → list members with access to an event

Body (POST):
  { "action": "grant" | "revoke", "member_ids": ["id1", "id2", ...] }

Response (POST):
  { "processed": N, "results": [{ "member_id": ..., "status": "ok"|"error", "message": ... }] }

Response (GET):
  { "event_id": ..., "members": [{ "member_id", "email", "member_type", "club_id" }] }

Access: requires events_crud or system_crud permission (admin only).
"""

import json
import os
import logging

import boto3
from boto3.dynamodb.conditions import Attr

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("manage_event_access")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def _is_admin(user_roles, user_email):
    """Check if user has admin-level access (events_crud or system_crud)."""
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['events_crud'], user_email, None
    )
    if is_authorized:
        return True
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['system_crud'], user_email, None
    )
    return is_authorized


def _grant_event_access(event_id, member_ids):
    """
    Add event_id to each member's allowed_events list (if not already present).
    Returns list of result dicts per member_id.
    """
    results = []
    for member_id in member_ids:
        try:
            # Use ADD with a set to avoid duplicates — but allowed_events is a List,
            # so we use a conditional update expression instead.
            members_table.update_item(
                Key={'member_id': member_id},
                UpdateExpression='SET allowed_events = list_append(if_not_exists(allowed_events, :empty_list), :event_list)',
                ConditionExpression='attribute_exists(member_id) AND (attribute_not_exists(allowed_events) OR NOT contains(allowed_events, :event_id))',
                ExpressionAttributeValues={
                    ':event_list': [event_id],
                    ':event_id': event_id,
                    ':empty_list': [],
                },
            )
            results.append({'member_id': member_id, 'status': 'ok', 'message': 'Access granted'})
            logger.info(f"Granted event access: member={member_id}, event={event_id}")
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Either member doesn't exist or already has access
            # Check which case
            try:
                response = members_table.get_item(
                    Key={'member_id': member_id},
                    ProjectionExpression='member_id, allowed_events'
                )
                if 'Item' not in response:
                    results.append({'member_id': member_id, 'status': 'error', 'message': 'Member not found'})
                else:
                    # Member already has access
                    results.append({'member_id': member_id, 'status': 'ok', 'message': 'Already has access'})
            except Exception:
                results.append({'member_id': member_id, 'status': 'error', 'message': 'Member not found'})
        except Exception as e:
            logger.error(f"Failed to grant access for member {member_id}: {str(e)}")
            results.append({'member_id': member_id, 'status': 'error', 'message': str(e)})

    return results


def _revoke_event_access(event_id, member_ids):
    """
    Remove event_id from each member's allowed_events list.
    Returns list of result dicts per member_id.
    """
    results = []
    for member_id in member_ids:
        try:
            # Get current allowed_events to find the index
            response = members_table.get_item(
                Key={'member_id': member_id},
                ProjectionExpression='member_id, allowed_events'
            )
            if 'Item' not in response:
                results.append({'member_id': member_id, 'status': 'error', 'message': 'Member not found'})
                continue

            member = response['Item']
            allowed_events = member.get('allowed_events', [])

            if event_id not in allowed_events:
                results.append({'member_id': member_id, 'status': 'ok', 'message': 'Did not have access'})
                continue

            # Find index and remove
            idx = allowed_events.index(event_id)
            members_table.update_item(
                Key={'member_id': member_id},
                UpdateExpression=f'REMOVE allowed_events[{idx}]',
                ConditionExpression='attribute_exists(member_id)',
            )
            results.append({'member_id': member_id, 'status': 'ok', 'message': 'Access revoked'})
            logger.info(f"Revoked event access: member={member_id}, event={event_id}")
        except Exception as e:
            logger.error(f"Failed to revoke access for member {member_id}: {str(e)}")
            results.append({'member_id': member_id, 'status': 'error', 'message': str(e)})

    return results


def _list_members_with_access(event_id):
    """
    Scan Members table and return members whose allowed_events contains event_id.
    Returns list of member dicts with member_id, email, member_type, club_id.
    """
    members = []
    scan_kwargs = {
        'FilterExpression': Attr('allowed_events').contains(event_id),
        'ProjectionExpression': 'member_id, email, member_type, club_id',
    }

    response = members_table.scan(**scan_kwargs)
    members.extend(response.get('Items', []))

    while response.get('LastEvaluatedKey'):
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        response = members_table.scan(**scan_kwargs)
        members.extend(response.get('Items', []))

    return members


def _handle_post(event_id, body, user_email):
    """Handle POST /admin/events/{event_id}/access — grant or revoke access."""
    action = body.get('action')
    member_ids = body.get('member_ids')

    if action not in ('grant', 'revoke'):
        return create_error_response(400, 'Invalid action. Must be "grant" or "revoke".')

    if not member_ids or not isinstance(member_ids, list):
        return create_error_response(400, 'member_ids must be a non-empty list.')

    # Remove duplicates while preserving order
    seen = set()
    unique_member_ids = []
    for mid in member_ids:
        if mid not in seen:
            seen.add(mid)
            unique_member_ids.append(mid)

    logger.info(f"Event access {action}: event={event_id}, members={unique_member_ids}, by={user_email}")

    if action == 'grant':
        results = _grant_event_access(event_id, unique_member_ids)
    else:
        results = _revoke_event_access(event_id, unique_member_ids)

    return create_success_response({
        'processed': len(results),
        'results': results,
    })


def _handle_get(event_id):
    """Handle GET /admin/events/{event_id}/access — list members with access."""
    members = _list_members_with_access(event_id)

    return create_success_response({
        'event_id': event_id,
        'members': members,
    })


def lambda_handler(event, context):
    """
    Routes to POST (grant/revoke) or GET (list) based on httpMethod:
      - POST /admin/events/{event_id}/access → grant/revoke
      - GET  /admin/events/{event_id}/access → list members
    """
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # 2. Admin access check: require events_crud or system_crud permission
        if not _is_admin(user_roles, user_email):
            return create_error_response(403, 'Access denied: admin permissions required')

        log_successful_access(user_email, user_roles, 'manage_event_access')

        # 3. Extract event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')

        if not event_id:
            return create_error_response(400, 'event_id path parameter is required')

        # 4. Route by HTTP method
        http_method = event.get('httpMethod', '').upper()

        if http_method == 'POST':
            try:
                body = json.loads(event.get('body') or '{}')
            except (json.JSONDecodeError, TypeError):
                return create_error_response(400, 'Invalid JSON body')
            return _handle_post(event_id, body, user_email)

        elif http_method == 'GET':
            return _handle_get(event_id)

        else:
            return create_error_response(405, f'Method {http_method} not allowed')

    except Exception as e:
        logger.error(f"Error in manage_event_access handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
