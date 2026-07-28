"""Handler for POST /members/{member_id}/transition.

Executes a workflow transition on a single member:
1. Auth check (Members_CRUD or Members_Status_Approve)
2. Load member from DynamoDB
3. Map DynamoDB status → workflow state
4. Run engine.execute(state, event, context)
5. Run dispatcher.execute_transition(transition, result, context)
6. Persist new status + append to status_history
7. Return TransitionResult as JSON
"""

import json
import os
import logging
from datetime import datetime, timezone

import boto3

from shared.auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    create_success_response,
    create_error_response,
    cors_headers,
    handle_options_request,
    log_successful_access,
)
from shared.workflows.membership import membership_engine
from shared.workflows.states import MemberState
from shared.workflows.dispatcher import ActionDispatcher
from shared.workflows.types import TransitionResult

from actions import register_actions
from email_side_effects import register_email_side_effects

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status ↔ State mapping
# ---------------------------------------------------------------------------

STATUS_TO_STATE: dict[str, str] = {
    'Aangemeld': MemberState.APPLIED,
    'wachtRegio': MemberState.PENDING,
    'wachtBetaling': MemberState.WAIT_PAYMENT,
    'Actief': MemberState.ACTIVE,
    'Opgezegd': MemberState.CANCELLED,
    'Geschorst': MemberState.SUSPENDED,
}

STATE_TO_STATUS: dict[str, str] = {v: k for k, v in STATUS_TO_STATE.items()}

# ---------------------------------------------------------------------------
# DynamoDB setup
# ---------------------------------------------------------------------------

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

# ---------------------------------------------------------------------------
# Dispatcher instance (actions registered at module load)
# ---------------------------------------------------------------------------

dispatcher = ActionDispatcher()
register_actions(dispatcher)
register_email_side_effects(dispatcher)


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda entry point for POST /members/{member_id}/transition."""

    # CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return handle_options_request()

    try:
        # 1. Auth check
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        is_authorized, perm_error, regional_info = validate_permissions_with_regions(
            user_roles,
            ['Members_CRUD', 'Members_Status_Approve'],
            user_email,
            {'operation': 'transition_member'},
        )
        if not is_authorized:
            return perm_error

        # Parse request
        member_id = event.get('pathParameters', {}).get('id') or event.get('pathParameters', {}).get('member_id')
        if not member_id:
            return create_error_response(400, 'Missing member_id path parameter')

        body = json.loads(event.get('body') or '{}')
        transition_event: str | None = body.get('event')
        transition_context: dict = body.get('context', {})

        if not transition_event:
            return create_error_response(400, 'Missing required field: event')

        # 2. Load member from DynamoDB
        response = table.get_item(Key={'member_id': member_id})
        member = response.get('Item')
        if not member:
            return create_error_response(404, 'Member not found')

        current_status: str = member.get('status', '')

        # 3. Map status → state
        current_state = STATUS_TO_STATE.get(current_status)
        if current_state is None:
            return create_error_response(
                400,
                f"Status '{current_status}' is not part of the membership workflow",
            )

        # Build context for engine and dispatcher
        exec_context: dict = {
            **transition_context,
            'member_id': member_id,
            'member': member,
            'user_email': user_email,
            'user_roles': user_roles,
            'table': table,
        }

        # 4. Execute engine (evaluates transition, no side effects)
        result: TransitionResult = membership_engine.execute(
            current_state, transition_event, exec_context
        )

        if not result.success:
            return create_error_response(400, result.error or 'Transition not allowed')

        # 5. Execute dispatcher (mandatory actions + side effects)
        transition = membership_engine.can_transition(
            current_state, transition_event, exec_context
        )
        if transition:
            result = dispatcher.execute_transition(transition, result, exec_context)

        if not result.success:
            return create_error_response(
                500,
                result.error or 'Transition action failed',
                details={'failures': result.failures},
            )

        # 6. Persist new status + status_history
        new_status = STATE_TO_STATUS.get(result.new_state or '', result.new_state or '')
        now_iso = datetime.now(timezone.utc).isoformat()

        history_entry = {
            'from': current_status,
            'to': new_status,
            'event': transition_event,
            'at': now_iso,
            'by': user_email,
        }

        table.update_item(
            Key={'member_id': member_id},
            UpdateExpression=(
                'SET #status = :new_status, '
                'updated_at = :now, '
                '#hist = list_append(if_not_exists(#hist, :empty_list), :entry)'
            ),
            ExpressionAttributeNames={
                '#status': 'status',
                '#hist': 'status_history',
            },
            ExpressionAttributeValues={
                ':new_status': new_status,
                ':now': now_iso,
                ':entry': [history_entry],
                ':empty_list': [],
            },
        )

        log_successful_access(user_email, user_roles, 'transition_member', {
            'member_id': member_id,
            'event': transition_event,
            'old_status': current_status,
            'new_status': new_status,
        })

        # 7. Return result
        return create_success_response({
            'success': True,
            'old_status': current_status,
            'new_status': new_status,
            'actions_executed': result.actions_executed,
            'side_effects_executed': result.side_effects_executed,
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.exception('Unexpected error in transition_member')
        return create_error_response(500, f'Internal server error: {e}')
