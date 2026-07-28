"""Handler for POST /members/bulk-transition.

Executes a workflow transition on multiple members independently:
1. Auth check (Members_CRUD only)
2. Validate request body + batch size (max 25)
3. For each member: load, map status → state, execute engine, dispatch, persist
4. Collect per-member results (one failure does NOT stop the rest)
5. Return summary: { total, succeeded, failed, results }
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
# Constants
# ---------------------------------------------------------------------------

MAX_BATCH_SIZE: int = 25

# ---------------------------------------------------------------------------
# Status ↔ State mapping (same as transition_member handler)
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
# Dispatcher instance (actions + side effects registered at module load)
# ---------------------------------------------------------------------------

dispatcher = ActionDispatcher()
register_actions(dispatcher)
register_email_side_effects(dispatcher)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class MemberTransitionResult:
    """Result for a single member within a bulk operation."""

    __slots__ = ('member_id', 'success', 'new_status', 'error')

    def __init__(
        self,
        member_id: str,
        success: bool,
        new_status: str | None = None,
        error: str | None = None,
    ) -> None:
        self.member_id = member_id
        self.success = success
        self.new_status = new_status
        self.error = error

    def to_dict(self) -> dict:
        """Serialize to response-friendly dict."""
        result: dict = {
            'member_id': self.member_id,
            'success': self.success,
        }
        if self.success and self.new_status:
            result['new_status'] = self.new_status
        if not self.success and self.error:
            result['error'] = self.error
        return result


# ---------------------------------------------------------------------------
# Core transition logic for a single member
# ---------------------------------------------------------------------------

def _transition_single_member(
    member_id: str,
    transition_event: str,
    transition_context: dict,
    user_email: str,
    user_roles: list[str],
) -> MemberTransitionResult:
    """Execute a transition for a single member. Never raises — returns result."""
    try:
        # Load member
        response = table.get_item(Key={'member_id': member_id})
        member = response.get('Item')
        if not member:
            return MemberTransitionResult(member_id, False, error='Member not found')

        current_status: str = member.get('status', '')

        # Map status → state
        current_state = STATUS_TO_STATE.get(current_status)
        if current_state is None:
            return MemberTransitionResult(
                member_id, False,
                error=f"Status '{current_status}' is not part of the membership workflow",
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

        # Execute engine
        result: TransitionResult = membership_engine.execute(
            current_state, transition_event, exec_context
        )

        if not result.success:
            return MemberTransitionResult(
                member_id, False,
                error=result.error or 'Transition not allowed',
            )

        # Execute dispatcher (mandatory actions + side effects)
        transition = membership_engine.can_transition(
            current_state, transition_event, exec_context
        )
        if transition:
            result = dispatcher.execute_transition(transition, result, exec_context)

        if not result.success:
            return MemberTransitionResult(
                member_id, False,
                error=result.error or 'Transition action failed',
            )

        # Persist new status + status_history
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

        return MemberTransitionResult(member_id, True, new_status=new_status)

    except Exception as e:
        logger.exception(f'Error transitioning member {member_id}')
        return MemberTransitionResult(member_id, False, error=str(e))


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context: object) -> dict:
    """Lambda entry point for POST /members/bulk-transition."""

    # CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return handle_options_request()

    try:
        # 1. Auth check — Members_CRUD only for bulk transitions
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        is_authorized, perm_error, regional_info = validate_permissions_with_regions(
            user_roles,
            ['Members_CRUD'],
            user_email,
            {'operation': 'bulk_transition_members'},
        )
        if not is_authorized:
            return perm_error

        # 2. Parse and validate request body
        body = json.loads(event.get('body') or '{}')

        transition_event: str | None = body.get('event')
        member_ids: list[str] | None = body.get('member_ids')
        transition_context: dict = body.get('context', {})

        if not transition_event:
            return create_error_response(400, 'Missing required field: event')

        if not member_ids or not isinstance(member_ids, list):
            return create_error_response(400, 'Missing or invalid field: member_ids (must be a non-empty array)')

        if len(member_ids) > MAX_BATCH_SIZE:
            return create_error_response(
                400,
                f'Batch size {len(member_ids)} exceeds maximum of {MAX_BATCH_SIZE}',
            )

        # Deduplicate member IDs while preserving order
        seen: set[str] = set()
        unique_member_ids: list[str] = []
        for mid in member_ids:
            if mid not in seen:
                seen.add(mid)
                unique_member_ids.append(mid)

        # 3. Process each member independently
        results: list[MemberTransitionResult] = []
        for member_id in unique_member_ids:
            member_result = _transition_single_member(
                member_id=member_id,
                transition_event=transition_event,
                transition_context=transition_context,
                user_email=user_email,
                user_roles=user_roles,
            )
            results.append(member_result)

        # 4. Build summary
        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        log_successful_access(user_email, user_roles, 'bulk_transition_members', {
            'event': transition_event,
            'total': len(results),
            'succeeded': succeeded,
            'failed': failed,
        })

        # 5. Return response
        return create_success_response({
            'total': len(results),
            'succeeded': succeeded,
            'failed': failed,
            'results': [r.to_dict() for r in results],
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.exception('Unexpected error in bulk_transition_members')
        return create_error_response(500, f'Internal server error: {e}')
