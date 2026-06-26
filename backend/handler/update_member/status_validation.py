"""
Status change validation, logging, and role assignment trigger for update_member handler.

Extracted from app.py to reduce file length. Contains:
- validate_status_change: Permission check for status field modifications
- log_status_change_denial: Security audit logging for denied status changes
- log_status_change_validation: Audit logging for validation results
- log_status_change_success: Audit logging for successful status changes
- determine_status_change_type: Categorize status transitions
- trigger_role_assignment_if_needed: Async Lambda invocation for Cognito role sync
"""

import json
import os
import boto3
from datetime import datetime


def validate_status_change(user_roles: list, user_email: str, member_id: str,
                           new_status: str, current_status: str | None = None,
                           cors_headers_fn=None):
    """
    Validate status field changes with enhanced security and logging.

    Args:
        user_roles: List of user's roles from JWT token
        user_email: User's email from JWT token
        member_id: ID of member record being updated
        new_status: New status value being set
        current_status: Current status value (optional)
        cors_headers_fn: Function returning CORS headers dict

    Returns:
        tuple: (is_valid, error_response, validation_details)
    """
    validation_details = {
        'timestamp': datetime.now().isoformat(),
        'user_email': user_email,
        'user_roles': user_roles,
        'member_id': member_id,
        'new_status': new_status,
        'current_status': current_status,
        'validation_result': None,
        'reason': None
    }

    try:
        # Check if user has permission to modify member status using new role structure
        has_members_crud = any(role.startswith('Members_CRUD') for role in user_roles)
        has_system_management = 'System_User_Management' in user_roles

        has_status_permission = has_members_crud or has_system_management

        if not has_status_permission:
            validation_details['validation_result'] = 'DENIED'
            validation_details['reason'] = 'Missing Members_CRUD permission'

            log_status_change_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                attempted_status=new_status,
                current_status=current_status,
                reason='Insufficient permissions to modify member status'
            )

            headers = cors_headers_fn() if cors_headers_fn else {}
            return False, {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Access denied: Requires Members_CRUD permission to modify member status',
                    'field': 'status',
                    'user_roles': user_roles,
                    'user_email': user_email
                })
            }, validation_details

        # Validation passed
        validation_details['validation_result'] = 'APPROVED'
        validation_details['reason'] = 'Valid status change request'

        log_status_change_validation(validation_details)

        return True, None, validation_details

    except Exception as e:
        validation_details['validation_result'] = 'ERROR'
        validation_details['reason'] = f'Validation error: {str(e)}'

        print(f"Error validating status change: {str(e)}")
        headers = cors_headers_fn() if cors_headers_fn else {}
        return False, {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Error validating status change'})
        }, validation_details


def log_status_change_denial(user_email: str, user_roles: list, member_id: str,
                             attempted_status: str, current_status: str | None,
                             reason: str):
    """Log denied status change attempts for security monitoring."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'STATUS_CHANGE_DENIED',
        'user_email': user_email,
        'user_roles': user_roles,
        'member_id': member_id,
        'attempted_status': attempted_status,
        'current_status': current_status,
        'denial_reason': reason,
        'severity': 'HIGH',
        'requires_review': True
    }

    print(f"STATUS_SECURITY_AUDIT: {json.dumps(log_entry)}")
    print(f"STATUS CHANGE DENIED: User {user_email} (roles: {user_roles}) attempted to change "
          f"member {member_id} status from '{current_status}' to '{attempted_status}' - {reason}")


def log_status_change_validation(validation_details: dict):
    """Log status change validation results."""
    log_entry = {
        'event_type': 'STATUS_CHANGE_VALIDATION',
        **validation_details,
        'severity': 'INFO'
    }
    print(f"STATUS_VALIDATION_AUDIT: {json.dumps(log_entry)}")


def log_status_change_success(user_email: str, user_roles: list, member_id: str,
                              member_email: str, old_status: str | None,
                              new_status: str):
    """Log successful status changes with enhanced audit trail."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'STATUS_CHANGE_SUCCESS',
        'user_email': user_email,
        'user_roles': user_roles,
        'member_id': member_id,
        'member_email': member_email,
        'old_status': old_status,
        'new_status': new_status,
        'severity': 'CRITICAL',
        'requires_review': True,
        'change_type': determine_status_change_type(old_status, new_status)
    }

    print(f"STATUS_CHANGE_AUDIT: {json.dumps(log_entry)}")
    print(f"STATUS CHANGE SUCCESS: User {user_email} (roles: {user_roles}) changed "
          f"member {member_id} ({member_email}) status from '{old_status}' to '{new_status}'")

    critical_changes = ['suspended', 'inactive', 'rejected', 'cancelled']
    if new_status in critical_changes:
        print(f"CRITICAL STATUS CHANGE: Member {member_id} status changed to '{new_status}' - "
              f"immediate review recommended")


def determine_status_change_type(old_status: str | None, new_status: str) -> str:
    """Determine the type of status change for categorization."""
    if not old_status:
        return 'initial_status_set'

    activation_statuses = ['active', 'approved', 'Actief', 'HdcnAccount', 'Club', 'Sponsor']
    deactivation_statuses = ['inactive', 'suspended', 'cancelled', 'expired', 'Opgezegd', 'Geschorst']
    approval_statuses = ['approved', 'Actief']
    rejection_statuses = ['rejected', 'Opgezegd']

    if old_status in ['pending', 'new_applicant'] and new_status in approval_statuses:
        return 'approval'
    elif old_status in ['pending', 'new_applicant'] and new_status in rejection_statuses:
        return 'rejection'
    elif old_status not in deactivation_statuses and new_status in deactivation_statuses:
        return 'deactivation'
    elif old_status in deactivation_statuses and new_status in activation_statuses:
        return 'reactivation'
    else:
        return 'status_update'


def trigger_role_assignment_if_needed(member_email: str, old_status: str | None,
                                      new_status: str):
    """
    Trigger role assignment Lambda function if status change requires it.

    Args:
        member_email: Member's email address (Cognito username)
        old_status: Previous status
        new_status: New status
    """
    try:
        approved_statuses = ['active', 'approved', 'Actief', 'HdcnAccount', 'Club', 'Sponsor']

        old_should_have_role = old_status in approved_statuses if old_status else False
        new_should_have_role = new_status in approved_statuses if new_status else False

        if old_should_have_role != new_should_have_role:
            lambda_client = boto3.client('lambda')

            payload = {
                'member_email': member_email,
                'action': 'assign_default_role' if new_should_have_role else 'remove_all_roles',
                'status_change': {
                    'old_status': old_status,
                    'new_status': new_status
                }
            }

            role_assignment_function = os.environ.get(
                'ROLE_ASSIGNMENT_FUNCTION_NAME', 'hdcn-cognito-role-assignment'
            )

            try:
                lambda_client.invoke(
                    FunctionName=role_assignment_function,
                    InvocationType='Event',
                    Payload=json.dumps(payload)
                )
                print(f"Role assignment triggered for {member_email}: {old_status} -> {new_status}")

            except Exception as lambda_error:
                print(f"Warning: Failed to trigger role assignment for {member_email}: {str(lambda_error)}")
                print("Status change completed but role assignment may need manual intervention")
        else:
            print(f"No role assignment change needed for {member_email}: {old_status} -> {new_status}")

    except Exception as e:
        print(f"Error in role assignment trigger for {member_email}: {str(e)}")
