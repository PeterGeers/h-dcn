"""
PresMeet Manage Delegates Handler

POST /presmeet/orders/{id}/delegates
Manages secondary delegate assignment on a PresMeet order.

Body: { "action": "add"|"remove", "email": "..." }

- Only the PRIMARY delegate can add/remove secondary delegates
- Add: validates email is an existing portal user with Regio_Pressmeet or Regio_All
- Remove: primary can remove secondary at any time
- Stores delegates: { primary: email, secondary: email|null } on the order record

Requirements: 12.6-12.10
"""

import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal

try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import get_club_id, is_presmeet_admin, has_presmeet_access
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("presmeet_manage_delegates")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

cognito_client = boto3.client('cognito-idp')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')

VALID_ACTIONS = ('add', 'remove')
REQUIRED_GROUPS = ('Regio_Pressmeet', 'Regio_All')


def lambda_handler(event, context):
    """Handle POST /presmeet/orders/{id}/delegates"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # --- Authentication ---
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate PresMeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(
                403, 'Access denied: Requires Regio_Pressmeet or Regio_All'
            )

        # --- Extract order_id from path ---
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # --- Parse request body ---
        body = json.loads(event.get('body') or '{}')
        action = body.get('action')
        target_email = body.get('email', '').strip().lower()

        if action not in VALID_ACTIONS:
            return create_error_response(
                400, f'action must be one of: {", ".join(VALID_ACTIONS)}'
            )

        if action == 'add' and not target_email:
            return create_error_response(400, 'email is required for add action')

        # --- Fetch current order ---
        order_response = orders_table.get_item(Key={'order_id': order_id})
        order = order_response.get('Item')

        if not order:
            return create_error_response(404, 'Order not found')

        # --- Authorization: only primary delegate (or admin) can manage delegates ---
        delegates = order.get('delegates', {})
        primary_email = (delegates.get('primary') or '').lower()
        admin = is_presmeet_admin(user_roles)

        if not admin and user_email.lower() != primary_email:
            return create_error_response(
                403,
                'Only the primary delegate can manage secondary delegates'
            )

        # --- Execute action ---
        if action == 'add':
            return _handle_add(order_id, order, target_email, user_email)
        else:
            return _handle_remove(order_id, order, user_email)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error in presmeet_manage_delegates: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, 'Internal server error')


def _handle_add(order_id, order, target_email, requester_email):
    """
    Add a secondary delegate to the order.
    Validates the target email is an existing portal user with required groups.
    """
    delegates = order.get('delegates', {})
    primary_email = (delegates.get('primary') or '').lower()

    # Cannot add yourself (you're already primary)
    if target_email == primary_email:
        return create_error_response(
            400, 'Cannot add the primary delegate as secondary'
        )

    # Check if secondary already set to same email
    current_secondary = (delegates.get('secondary') or '')
    if current_secondary and current_secondary.lower() == target_email:
        return create_error_response(
            400, 'This user is already the secondary delegate'
        )

    # Validate: email must be an existing portal user (exists in Members table)
    if not _member_exists(target_email):
        return create_error_response(
            404, 'User not found: email does not belong to an existing portal member'
        )

    # Validate: user must have Regio_Pressmeet or Regio_All in Cognito groups
    if not _user_has_required_groups(target_email):
        return create_error_response(
            403,
            'User does not have PresMeet access (requires Regio_Pressmeet or Regio_All)'
        )

    # Update the order record
    now = datetime.now(timezone.utc).isoformat()
    try:
        response = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET delegates.secondary = :email, updated_at = :now',
            ExpressionAttributeValues={
                ':email': target_email,
                ':now': now,
            },
            ReturnValues='ALL_NEW',
        )
    except Exception as e:
        print(f"Error updating delegates: {str(e)}")
        return create_error_response(500, 'Failed to update delegates')

    log_successful_access(requester_email, [], 'presmeet_manage_delegates:add')

    updated_order = response.get('Attributes', {})
    return create_success_response({
        'message': f'Secondary delegate added: {target_email}',
        'delegates': _serialize(updated_order.get('delegates', {})),
    })


def _handle_remove(order_id, order, requester_email):
    """
    Remove the secondary delegate from the order.
    Primary can remove at any time.
    """
    delegates = order.get('delegates', {})
    current_secondary = delegates.get('secondary')

    if not current_secondary:
        return create_error_response(400, 'No secondary delegate to remove')

    # Update the order record — set secondary to None
    now = datetime.now(timezone.utc).isoformat()
    try:
        response = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET delegates.secondary = :null_val, updated_at = :now',
            ExpressionAttributeValues={
                ':null_val': None,
                ':now': now,
            },
            ReturnValues='ALL_NEW',
        )
    except Exception as e:
        print(f"Error removing delegate: {str(e)}")
        return create_error_response(500, 'Failed to remove delegate')

    log_successful_access(requester_email, [], 'presmeet_manage_delegates:remove')

    updated_order = response.get('Attributes', {})
    return create_success_response({
        'message': 'Secondary delegate removed',
        'delegates': _serialize(updated_order.get('delegates', {})),
    })


def _member_exists(email):
    """Check if a member with this email exists in the Members table."""
    from boto3.dynamodb.conditions import Attr
    response = members_table.scan(
        FilterExpression=Attr('email').eq(email),
        ProjectionExpression='member_id',
        Limit=1,
    )
    return len(response.get('Items', [])) > 0


def _user_has_required_groups(email):
    """
    Check if the user has Regio_Pressmeet or Regio_All in their Cognito groups.
    Uses AdminListGroupsForUser via the user's email (username in Cognito).
    """
    if not COGNITO_USER_POOL_ID:
        # If pool ID not configured, skip group check (for local dev/testing)
        print("WARNING: COGNITO_USER_POOL_ID not set, skipping group check")
        return True

    try:
        # Look up user by email
        response = cognito_client.list_users(
            UserPoolId=COGNITO_USER_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1,
        )
        users = response.get('Users', [])
        if not users:
            return False

        username = users[0]['Username']

        # Get user's groups
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
        )
        user_groups = [g['GroupName'] for g in groups_response.get('Groups', [])]

        return any(group in REQUIRED_GROUPS for group in user_groups)
    except Exception as e:
        print(f"Error checking Cognito groups for {email}: {str(e)}")
        return False


def _serialize(obj):
    """Convert Decimal types to JSON-safe types."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize(i) for i in obj]
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj
