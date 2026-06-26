"""
Field-level permission validation and audit logging for update_member handler.

Extracted from app.py to reduce file length. Contains:
- validate_field_permissions: Check user can modify requested fields
- categorize_forbidden_fields: Group denied fields by category
- build_permission_error_message: Human-readable permission error
- log_field_permission_denial: Security audit for denied field edits
- log_successful_field_update: Audit trail for successful updates
- log_administrative_field_changes: Enhanced logging for admin field changes
"""

import json
from datetime import datetime

from shared.role_permissions import (
    can_edit_field,
    PERSONAL_FIELDS,
    MOTORCYCLE_FIELDS,
    ADMINISTRATIVE_FIELDS,
)


def validate_field_permissions(table, user_roles: list, user_email: str,
                               member_id: str, fields_to_update: dict,
                               cors_headers_fn=None):
    """
    Validate user has permission to modify the requested fields.

    Args:
        table: DynamoDB Table resource (Members table)
        user_roles: List of user's roles from JWT token
        user_email: User's email from JWT token
        member_id: ID of member record being updated
        fields_to_update: Dictionary of fields and values to update
        cors_headers_fn: Function returning CORS headers dict

    Returns:
        tuple: (is_valid, error_response, forbidden_fields)
    """
    try:
        response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in response:
            headers = cors_headers_fn() if cors_headers_fn else {}
            return False, {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Member record not found'})
            }, []

        member_record = response['Item']
        member_email = member_record.get('email', '')
        is_own_record = (user_email.lower() == member_email.lower())

        # Check permissions for each field
        forbidden_fields = []
        for field_name in fields_to_update.keys():
            if not can_edit_field(user_roles, field_name, is_own_record):
                forbidden_fields.append(field_name)

        if forbidden_fields:
            field_categories = categorize_forbidden_fields(forbidden_fields)
            error_message = build_permission_error_message(
                forbidden_fields, field_categories, is_own_record
            )

            log_field_permission_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                forbidden_fields=forbidden_fields,
                field_categories=field_categories,
                is_own_record=is_own_record,
                member_email=member_record.get('email', 'unknown')
            )

            headers = cors_headers_fn() if cors_headers_fn else {}
            return False, {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({
                    'error': error_message,
                    'forbidden_fields': forbidden_fields,
                    'field_categories': field_categories
                })
            }, forbidden_fields

        return True, None, []

    except Exception as e:
        print(f"Error validating field permissions: {str(e)}")
        headers = cors_headers_fn() if cors_headers_fn else {}
        return False, {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Error validating permissions'})
        }, []


def categorize_forbidden_fields(forbidden_fields: list) -> dict:
    """Categorize forbidden fields by type for better error messages."""
    categories = {
        'administrative': [],
        'personal': [],
        'motorcycle': [],
        'other': []
    }

    for field in forbidden_fields:
        if field in ADMINISTRATIVE_FIELDS:
            categories['administrative'].append(field)
        elif field in PERSONAL_FIELDS:
            categories['personal'].append(field)
        elif field in MOTORCYCLE_FIELDS:
            categories['motorcycle'].append(field)
        else:
            categories['other'].append(field)

    return {k: v for k, v in categories.items() if v}


def build_permission_error_message(forbidden_fields: list, field_categories: dict,
                                   is_own_record: bool) -> str:
    """Build a descriptive error message for permission violations."""
    if len(forbidden_fields) == 1:
        field = forbidden_fields[0]
        if field in ADMINISTRATIVE_FIELDS:
            return f"Access denied: Field '{field}' requires administrative privileges to modify"
        elif not is_own_record and (field in PERSONAL_FIELDS or field in MOTORCYCLE_FIELDS):
            return f"Access denied: You can only modify your own {field} information"
        else:
            return f"Access denied: Insufficient permissions to modify field '{field}'"

    messages = []
    if 'administrative' in field_categories:
        admin_fields = ', '.join(field_categories['administrative'])
        messages.append(f"Administrative fields ({admin_fields}) require administrative privileges")

    if not is_own_record and ('personal' in field_categories or 'motorcycle' in field_categories):
        personal_fields = field_categories.get('personal', []) + field_categories.get('motorcycle', [])
        personal_fields_str = ', '.join(personal_fields)
        messages.append(f"Personal fields ({personal_fields_str}) can only be modified on your own record")

    if 'other' in field_categories:
        other_fields = ', '.join(field_categories['other'])
        messages.append(f"Fields ({other_fields}) require additional permissions")

    return f"Access denied: {'; '.join(messages)}"


def log_field_permission_denial(user_email: str, user_roles: list, member_id: str,
                                forbidden_fields: list, field_categories: dict,
                                is_own_record: bool, member_email: str):
    """Log field-level permission denials for audit and security monitoring."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'FIELD_PERMISSION_DENIED',
        'user_email': user_email,
        'user_roles': user_roles,
        'target_member_id': member_id,
        'target_member_email': member_email,
        'is_own_record': is_own_record,
        'forbidden_fields': forbidden_fields,
        'field_categories': field_categories,
        'severity': 'WARNING' if is_own_record else 'HIGH'
    }

    print(f"SECURITY_AUDIT: {json.dumps(log_entry)}")

    action_type = "own record" if is_own_record else f"another user's record ({member_email})"
    fields_summary = ", ".join(forbidden_fields)
    print(f"Field permission denied: User {user_email} (roles: {user_roles}) attempted to modify "
          f"forbidden fields [{fields_summary}] on {action_type}")


def log_successful_field_update(user_email: str, user_roles: list, member_id: str,
                                updated_fields: list, field_values: dict | None = None,
                                member_email: str | None = None):
    """Log successful field updates for audit trail."""
    administrative_fields = [f for f in updated_fields if f in ADMINISTRATIVE_FIELDS]
    personal_fields = [f for f in updated_fields if f in PERSONAL_FIELDS]
    motorcycle_fields = [f for f in updated_fields if f in MOTORCYCLE_FIELDS]
    other_fields = [f for f in updated_fields
                    if f not in ADMINISTRATIVE_FIELDS + PERSONAL_FIELDS + MOTORCYCLE_FIELDS]

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'FIELD_UPDATE_SUCCESS',
        'user_email': user_email,
        'user_roles': user_roles,
        'target_member_id': member_id,
        'target_member_email': member_email,
        'updated_fields': updated_fields,
        'field_count': len(updated_fields),
        'field_categories': {
            'administrative': administrative_fields,
            'personal': personal_fields,
            'motorcycle': motorcycle_fields,
            'other': other_fields
        },
        'has_administrative_changes': len(administrative_fields) > 0,
        'administrative_field_count': len(administrative_fields)
    }

    if field_values and administrative_fields:
        log_entry['administrative_field_changes'] = {
            field: field_values.get(field) for field in administrative_fields
        }

    print(f"AUDIT_LOG: {json.dumps(log_entry)}")

    if administrative_fields:
        _log_administrative_field_changes(
            user_email, user_roles, member_id, member_email,
            administrative_fields, field_values
        )


def _log_administrative_field_changes(user_email: str, user_roles: list, member_id: str,
                                      member_email: str | None, admin_fields: list,
                                      field_values: dict | None = None):
    """Enhanced logging specifically for administrative field changes."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ADMINISTRATIVE_FIELD_UPDATE',
        'user_email': user_email,
        'user_roles': user_roles,
        'target_member_id': member_id,
        'target_member_email': member_email,
        'administrative_fields_changed': admin_fields,
        'change_count': len(admin_fields),
        'severity': 'HIGH',
        'requires_review': True
    }

    if field_values:
        log_entry['field_changes'] = {
            field: field_values.get(field) for field in admin_fields
        }

    critical_fields = ['status', 'lidmaatschap', 'regio', 'lidnummer']
    critical_changes = [field for field in admin_fields if field in critical_fields]
    if critical_changes:
        log_entry['critical_fields_changed'] = critical_changes
        log_entry['severity'] = 'CRITICAL'
        log_entry['requires_immediate_review'] = True

    print(f"ADMIN_AUDIT: {json.dumps(log_entry)}")

    is_own_record = user_email.lower() == (member_email or '').lower()
    target_description = "own record" if is_own_record else f"member record ({member_email})"

    print(f"ADMINISTRATIVE CHANGE: User {user_email} (roles: {user_roles}) modified "
          f"administrative fields {admin_fields} on {target_description} (member_id: {member_id})")

    if critical_changes:
        print(f"CRITICAL ADMINISTRATIVE CHANGE: Critical fields {critical_changes} were modified - "
              f"immediate review recommended")
