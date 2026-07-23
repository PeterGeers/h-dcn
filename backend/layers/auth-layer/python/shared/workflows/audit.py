"""
Audit logging for workflow state transitions.

Uses the same print-to-CloudWatch pattern as ACCESS_AUDIT and AUDIT_LOG
in auth_utils.py. Queryable via CloudWatch Insights:

    fields @timestamp, @message
    | filter @message like /WORKFLOW_AUDIT/
    | parse @message "WORKFLOW_AUDIT: *" as audit_json
"""

import json
from datetime import datetime


def write_workflow_audit(ctx: dict) -> None:
    """
    Write a structured audit log entry for a workflow state transition.

    Uses print() to emit to CloudWatch Logs (same pattern as ACCESS_AUDIT
    and AUDIT_LOG in shared.auth_utils).

    Args:
        ctx: Dictionary containing transition details. Expected keys:
            - entity_type: Type of entity (e.g. 'member', 'order')
            - entity_id: Unique identifier of the entity
            - workflow: Workflow name (e.g. 'membership', 'order')
            - old_state: State before transition
            - new_state: State after transition
            - event: Event that triggered the transition
            - user_email: Email of user who triggered (defaults to 'system')
            - actions_executed: List of mandatory actions that ran
            - side_effects_executed: List of side effects that ran
            - failures: List of failure descriptions
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'WORKFLOW_TRANSITION',
        'entity_type': ctx.get('entity_type'),
        'entity_id': ctx.get('entity_id'),
        'workflow': ctx.get('workflow'),
        'old_state': ctx.get('old_state'),
        'new_state': ctx.get('new_state'),
        'event': ctx.get('event'),
        'user_email': ctx.get('user_email', 'system'),
        'actions_executed': ctx.get('actions_executed', []),
        'side_effects_executed': ctx.get('side_effects_executed', []),
        'failures': ctx.get('failures', []),
        'severity': 'WARNING' if ctx.get('failures') else 'INFO',
    }

    print(f"WORKFLOW_AUDIT: {json.dumps(log_entry)}")
