"""Dispatcher actions for membership workflow transitions.

These are MANDATORY actions and side effects registered with the ActionDispatcher.
Each action receives a context dict and performs its operation.

Mandatory actions (must succeed for transition to complete):
- activate_member: Set status=Actief, set ingangsdatum, add Cognito group
- deactivate_member: Set status=Opgezegd, remove Cognito group
- suspend_member: Set status=Geschorst, store reason
- flag_welcome_pack: Set welcome_pack_status=pending, validate address

Side effects (best-effort, failures don't block transition):
- audit_log: Write structured audit entry to CloudWatch
"""

import logging
import os
from datetime import date
from typing import Any

import boto3

from shared.workflows import ActionDispatcher, write_workflow_audit
from shared.number_generator import generate_member_number

logger = logging.getLogger(__name__)

# --- AWS resources ---

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
counters_table = dynamodb.Table(os.environ.get('COUNTERS_TABLE_NAME', 'Counters'))
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')

COGNITO_USER_POOL_ID: str = os.environ.get('COGNITO_USER_POOL_ID', '')


# --- Helper functions ---


def _get_cognito_username(email: str) -> str | None:
    """Find Cognito username by email address.

    Returns the Username if found, None otherwise.
    """
    try:
        response = cognito_client.list_users(
            UserPoolId=COGNITO_USER_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1,
        )
        users = response.get('Users', [])
        if users:
            return users[0]['Username']
        return None
    except Exception as e:
        logger.error(f"Failed to look up Cognito user for email {email}: {e}")
        raise


def _add_to_cognito_group(email: str, group_name: str) -> None:
    """Add a user to a Cognito group by their email."""
    username = _get_cognito_username(email)
    if not username:
        raise ValueError(f"No Cognito user found for email: {email}")

    cognito_client.admin_add_user_to_group(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=username,
        GroupName=group_name,
    )
    logger.info(f"Added user {email} to Cognito group '{group_name}'")


def _remove_from_cognito_group(email: str, group_name: str) -> None:
    """Remove a user from a Cognito group by their email."""
    username = _get_cognito_username(email)
    if not username:
        raise ValueError(f"No Cognito user found for email: {email}")

    cognito_client.admin_remove_user_from_group(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=username,
        GroupName=group_name,
    )
    logger.info(f"Removed user {email} from Cognito group '{group_name}'")


# --- Mandatory actions ---


def activate_member(ctx: dict[str, Any]) -> None:
    """Activate a member: set status=Actief, assign lidnummer, set ingangsdatum, add hdcnLeden group.

    Expected context keys:
        - member_id: str
        - member: dict (full member record with 'email' field)
    """
    member_id: str = ctx['member_id']
    member: dict[str, Any] = ctx.get('member', {})
    email: str = member.get('email', '')

    if not email:
        raise ValueError(f"Member {member_id} has no email — cannot add to Cognito group")

    today_iso: str = date.today().isoformat()

    # Generate next lidnummer via atomic counter
    lidnummer: int = generate_member_number(counters_table)

    # Update DynamoDB: status + ingangsdatum + lidnummer
    table.update_item(
        Key={'member_id': member_id},
        UpdateExpression='SET #status = :status, ingangsdatum = :datum, lidnummer = :lidnr',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'Actief',
            ':datum': today_iso,
            ':lidnr': lidnummer,
        },
    )

    # Add to hdcnLeden Cognito group
    _add_to_cognito_group(email, 'hdcnLeden')

    # Store lidnummer in context so side effects (send_welcome_email) can read it
    ctx['lidnummer'] = lidnummer
    member['lidnummer'] = lidnummer

    logger.info(f"Activated member {member_id}, lidnummer={lidnummer}, ingangsdatum={today_iso}")


def deactivate_member(ctx: dict[str, Any]) -> None:
    """Deactivate a member: set status=Opgezegd, remove hdcnLeden group.

    Expected context keys:
        - member_id: str
        - member: dict (full member record with 'email' field)
    """
    member_id: str = ctx['member_id']
    member: dict[str, Any] = ctx.get('member', {})
    email: str = member.get('email', '')

    # Update DynamoDB status
    table.update_item(
        Key={'member_id': member_id},
        UpdateExpression='SET #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'Opgezegd'},
    )

    # Remove from hdcnLeden Cognito group
    if email:
        _remove_from_cognito_group(email, 'hdcnLeden')
    else:
        logger.warning(f"Member {member_id} has no email — skipping Cognito group removal")

    logger.info(f"Deactivated member {member_id}")


def suspend_member(ctx: dict[str, Any]) -> None:
    """Suspend a member: set status=Geschorst, store reason.

    Expected context keys:
        - member_id: str
        - reason: str (required by guard, should always be present)
    """
    member_id: str = ctx['member_id']
    reason: str = ctx.get('reason', '')

    update_expr = 'SET #status = :status'
    expr_names: dict[str, str] = {'#status': 'status'}
    expr_values: dict[str, str] = {':status': 'Geschorst'}

    if reason:
        update_expr += ', suspension_reason = :reason'
        expr_values[':reason'] = reason

    table.update_item(
        Key={'member_id': member_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )

    logger.info(f"Suspended member {member_id}, reason={reason}")


def flag_welcome_pack(ctx: dict[str, Any]) -> None:
    """Flag welcome pack as pending and validate postal address.

    Sets welcome_pack_status=pending. If the address is incomplete,
    adds a note for the admin to verify before sending.

    Expected context keys:
        - member_id: str
        - member: dict (full member record)
    """
    member_id: str = ctx['member_id']
    member: dict[str, Any] = ctx.get('member', {})

    # Validate address completeness
    has_street = bool(member.get('straat') or member.get('postadres'))
    has_postcode = bool(member.get('postcode') or member.get('postpostcode'))
    has_city = bool(member.get('woonplaats') or member.get('postwoonplaats'))
    has_address = has_street and has_postcode and has_city

    update_expr = 'SET welcome_pack_status = :status'
    expr_values: dict[str, str] = {':status': 'pending'}

    if not has_address:
        update_expr += ', welcome_pack_notes = :notes'
        expr_values[':notes'] = 'Adres onvolledig — controleer voor verzending'

    table.update_item(
        Key={'member_id': member_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
    )

    logger.info(
        f"Flagged welcome pack for member {member_id} "
        f"(address complete: {has_address})"
    )


def mark_invoice_paid(ctx: dict[str, Any]) -> None:
    """Mark the membership invoice as paid.

    Currently a no-op placeholder. Will integrate with Payments table
    when automated payment tracking is implemented.

    Expected context keys:
        - member_id: str
    """
    member_id: str = ctx.get('member_id', '')
    logger.info(f"mark_invoice_paid called for member {member_id} (no-op: manual payment tracking)")


# --- Side effects ---


def audit_log(ctx: dict[str, Any]) -> None:
    """Write structured audit log entry via write_workflow_audit.

    Builds the audit context from the transition context and delegates
    to the shared audit module.
    """
    audit_ctx: dict[str, Any] = {
        'entity_type': 'member',
        'entity_id': ctx.get('member_id'),
        'workflow': 'membership',
        'old_state': ctx.get('old_state'),
        'new_state': ctx.get('new_state'),
        'event': ctx.get('event'),
        'user_email': ctx.get('triggered_by', ctx.get('user_email', 'system')),
        'actions_executed': ctx.get('actions_executed', []),
        'side_effects_executed': ctx.get('side_effects_executed', []),
        'failures': ctx.get('failures', []),
    }
    write_workflow_audit(audit_ctx)


# --- Registration ---


def register_actions(dispatcher: ActionDispatcher) -> None:
    """Register all membership workflow actions with the dispatcher.

    Call this during handler initialization to make actions available
    for transition execution.
    """
    dispatcher.register_many({
        'activate_member': activate_member,
        'deactivate_member': deactivate_member,
        'suspend_member': suspend_member,
        'mark_invoice_paid': mark_invoice_paid,
        'flag_welcome_pack': flag_welcome_pack,
        'audit_log': audit_log,
    })
