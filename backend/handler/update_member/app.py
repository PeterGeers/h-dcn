import json
import boto3
import base64
from datetime import datetime
import sys
import os

# Import role_permissions from local directory
from role_permissions import can_edit_field, PERSONAL_FIELDS, MOTORCYCLE_FIELDS, ADMINISTRATIVE_FIELDS, get_combined_permissions

# Fallback auth utilities (in case layer doesn't work)
def extract_user_credentials_fallback(event):
    """Extract user credentials with enhanced groups support"""
    try:
        # Debug: Print all headers to see what we're receiving
        print(f"🔍 DEBUG: All headers received: {event.get('headers', {})}")
        
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        jwt_token = auth_header.replace('Bearer ', '')
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token format'})
            }
        
        payload_encoded = parts[1]
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        user_email = payload.get('email') or payload.get('username')
        if not user_email:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        # Check for enhanced groups from frontend
        enhanced_groups_header = event.get('headers', {}).get('X-Enhanced-Groups') or event.get('headers', {}).get('x-enhanced-groups')
        print(f"🔍 DEBUG: Enhanced groups header value: {enhanced_groups_header}")
        
        if enhanced_groups_header:
            try:
                enhanced_groups = json.loads(enhanced_groups_header)
                if isinstance(enhanced_groups, list):
                    print(f"🔍 FALLBACK AUTH: Using enhanced groups: {enhanced_groups} for {user_email}")
                    return user_email, enhanced_groups, None
            except json.JSONDecodeError:
                print(f"🔍 DEBUG: Failed to parse enhanced groups header")
                pass
        
        user_roles = payload.get('cognito:groups', [])
        print(f"🔍 FALLBACK AUTH: Using JWT groups: {user_roles} for {user_email}")
        return user_email, user_roles, None
        
    except Exception as e:
        print(f"FALLBACK AUTH ERROR: {str(e)}")
        return None, None, {
            'statusCode': 401,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid authorization token'})
        }

def validate_permissions_fallback(user_roles, required_permissions, user_email=None):
    """
    UPDATED permission validation using new role structure
    Replaces legacy role references with new permission + region validation
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # SYSTEM ADMIN ROLES (Full access, no region required)
        system_admin_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
        if any(role in system_admin_roles for role in user_roles):
            print(f"✅ System admin access granted for {user_email}: {[r for r in user_roles if r in system_admin_roles]}")
            return True, None
        
        # LEGACY ADMIN ROLES (Backward compatibility)
        legacy_admin_roles = ['National_Chairman', 'National_Secretary']
        if any(role in legacy_admin_roles for role in user_roles):
            print(f"✅ Legacy admin access granted for {user_email}: {[r for r in user_roles if r in legacy_admin_roles]}")
            return True, None
        
        # NEW ROLE STRUCTURE: Permission-based roles
        permission_roles = [
            'Members_CRUD', 'Members_Read', 'Members_Export',
            'Events_CRUD', 'Events_Read', 'Events_Export', 
            'Products_CRUD', 'Products_Read', 'Products_Export',
            'Communication_CRUD', 'Communication_Read', 'Communication_Export',
            'Webshop_Management', 'Members_Status_Approve'
        ]
        
        # Check if user has any permission roles
        user_permission_roles = [role for role in user_roles if role in permission_roles]
        if user_permission_roles:
            # For new role structure, also check for region roles
            region_roles = [role for role in user_roles if role.startswith('Regio_')]
            
            if region_roles:
                print(f"✅ Permission + region access granted for {user_email}: permissions={user_permission_roles}, regions={region_roles}")
                return True, None
            else:
                # User has permission role but no region role - incomplete new structure
                print(f"❌ Incomplete role structure for {user_email}: has permissions {user_permission_roles} but no region role")
                return False, {
                    'statusCode': 403,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        'error': 'Access denied: Permission role requires region role',
                        'required_structure': 'Permission role (e.g., Members_CRUD) + Region role (e.g., Regio_All)',
                        'user_roles': user_roles,
                        'missing': 'Region role (Regio_All, Regio_Noord-Holland, etc.)'
                    })
                }
        
        # REMOVED: Legacy compatibility code - no longer supporting old _All roles
        # All users must use new role structure: Permission + Region
        
        # SPECIAL ROLES: Limited access roles
        special_roles = ['hdcnLeden', 'Verzoek Lid']
        if any(role in special_roles for role in user_roles):
            # These roles have limited access - allow for own record updates only
            print(f"⚠️ Limited role access for {user_email}: {[r for r in user_roles if r in special_roles]} (own records only)")
            return True, None  # Let field-level validation handle the restrictions
        
        # No valid roles found
        print(f"❌ No valid roles found for {user_email}: {user_roles}")
        return False, {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Access denied: No valid permissions found',
                'required_permissions': required_permissions,
                'user_roles': user_roles,
                'help': 'Contact administrator to assign appropriate permission and region roles'
            })
        }
        
    except Exception as e:
        print(f"Error validating permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }

# Try to import from shared auth layer, fall back to local implementation
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,  # UPDATED: Use enhanced validation
        create_success_response, 
        create_error_response,
        cors_headers,
        handle_options_request
    )
    print("🔍 Successfully imported enhanced auth from shared layer")
    
    # Use the enhanced validation system
    def extract_user_credentials_fallback(event):
        return extract_user_credentials(event)
    
    def validate_permissions_fallback(user_roles, required_permissions, user_email=None):
        """Enhanced validation using new role structure"""
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email
        )
        if is_authorized:
            return True, None, regional_info
        else:
            return False, error_response, None
            
except ImportError:
    print("⚠️ Shared auth layer import failed, using enhanced fallback auth")
    # Enhanced fallback implementations are defined below
    
    def create_success_response(data, status_code=200):
        return {
            'statusCode': status_code,
            'headers': cors_headers(),
            'body': json.dumps(data)
        }
        
    def create_error_response(status_code, error_message, details=None):
        body = {'error': error_message}
        if details: 
            body.update(details)
        return {
            'statusCode': status_code,
            'headers': cors_headers(),
            'body': json.dumps(body)
        }
        
    def handle_options_request():
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': ''
        }

def validate_status_change(user_roles, user_email, member_id, new_status, current_status=None):
    """
    Validate status field changes with enhanced security and logging
    
    Args:
        user_roles (list): List of user's roles from JWT token
        user_email (str): User's email from JWT token
        member_id (str): ID of member record being updated
        new_status (str): New status value being set
        current_status (str): Current status value (optional)
        
    Returns:
        tuple: (is_valid, error_response, validation_details)
               If valid: (True, None, validation_info_dict)
               If invalid: (False, error_response_dict, validation_info_dict)
    """
    import json
    from datetime import datetime
    
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
        # Use the same permission system as the frontend - check if user has admin access
        # The frontend already shows this user has "Systeembeheerder - Volledige toegang"
        # so we should respect that instead of hardcoding role name checks
        
        # Check if user has permission to modify member status using new role structure
        # Users need Members_CRUD permission to modify member status
        has_members_crud = any(role.startswith('Members_CRUD') for role in user_roles)
        has_system_management = 'System_User_Management' in user_roles
        
        has_status_permission = has_members_crud or has_system_management
        
        if not has_status_permission:
            validation_details['validation_result'] = 'DENIED'
            validation_details['reason'] = 'Missing Members_CRUD permission'
            
            # Log the denial attempt
            log_status_change_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                attempted_status=new_status,
                current_status=current_status,
                reason='Insufficient permissions to modify member status'
            )
            
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: Requires Members_CRUD permission to modify member status',
                    'field': 'status',
                    'user_roles': user_roles,
                    'user_email': user_email
                })
            }, validation_details
        
        # Validate status value (basic validation - could be enhanced with parameter store lookup)
        valid_statuses = [
            'active', 'inactive', 'suspended', 'pending', 'new_applicant', 
            'approved', 'rejected', 'expired', 'cancelled'
        ]
        
        if new_status and new_status not in valid_statuses:
            validation_details['validation_result'] = 'DENIED'
            validation_details['reason'] = f'Invalid status value: {new_status}'
            
            # Log the invalid status attempt
            log_status_change_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                attempted_status=new_status,
                current_status=current_status,
                reason=f'Invalid status value: {new_status}'
            )
            
            return False, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': f'Invalid status value: {new_status}',
                    'field': 'status',
                    'valid_statuses': valid_statuses
                })
            }, validation_details
        
        # If we get here, validation passed
        validation_details['validation_result'] = 'APPROVED'
        validation_details['reason'] = 'Valid status change request'
        
        # Log the approved status change attempt (actual change will be logged separately)
        log_status_change_validation(validation_details)
        
        return True, None, validation_details
        
    except Exception as e:
        validation_details['validation_result'] = 'ERROR'
        validation_details['reason'] = f'Validation error: {str(e)}'
        
        print(f"Error validating status change: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating status change'})
        }, validation_details

def log_status_change_denial(user_email, user_roles, member_id, attempted_status, current_status, reason):
    """
    Log denied status change attempts for security monitoring
    
    Args:
        user_email (str): Email of user attempting the change
        user_roles (list): List of user's roles
        member_id (str): ID of member record
        attempted_status (str): Status value that was attempted
        current_status (str): Current status value
        reason (str): Reason for denial
    """
    import json
    from datetime import datetime
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'STATUS_CHANGE_DENIED',
        'user_email': user_email,
        'user_roles': user_roles,
        'member_id': member_id,
        'attempted_status': attempted_status,
        'current_status': current_status,
        'denial_reason': reason,
        'severity': 'HIGH',  # Status change denials are high priority for security
        'requires_review': True
    }
    
    # Log as structured JSON for monitoring systems
    print(f"STATUS_SECURITY_AUDIT: {json.dumps(log_entry)}")
    
    # Human-readable log
    print(f"STATUS CHANGE DENIED: User {user_email} (roles: {user_roles}) attempted to change "
          f"member {member_id} status from '{current_status}' to '{attempted_status}' - {reason}")

def log_status_change_validation(validation_details):
    """
    Log status change validation results
    
    Args:
        validation_details (dict): Dictionary containing validation information
    """
    import json
    
    log_entry = {
        'event_type': 'STATUS_CHANGE_VALIDATION',
        **validation_details,
        'severity': 'INFO'
    }
    
    # Log as structured JSON for monitoring systems
    print(f"STATUS_VALIDATION_AUDIT: {json.dumps(log_entry)}")

def log_status_change_success(user_email, user_roles, member_id, member_email, old_status, new_status):
    """
    Log successful status changes with enhanced audit trail
    
    Args:
        user_email (str): Email of user who made the change
        user_roles (list): List of user's roles
        member_id (str): ID of member record changed
        member_email (str): Email of member whose status was changed
        old_status (str): Previous status value
        new_status (str): New status value
    """
    import json
    from datetime import datetime
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'STATUS_CHANGE_SUCCESS',
        'user_email': user_email,
        'user_roles': user_roles,
        'member_id': member_id,
        'member_email': member_email,
        'old_status': old_status,
        'new_status': new_status,
        'severity': 'CRITICAL',  # All status changes are critical for audit
        'requires_review': True,
        'change_type': determine_status_change_type(old_status, new_status)
    }
    
    # Log as structured JSON for monitoring systems
    print(f"STATUS_CHANGE_AUDIT: {json.dumps(log_entry)}")
    
    # Human-readable log for administrators
    print(f"STATUS CHANGE SUCCESS: User {user_email} (roles: {user_roles}) changed "
          f"member {member_id} ({member_email}) status from '{old_status}' to '{new_status}'")
    
    # Special logging for critical status changes
    critical_changes = ['suspended', 'inactive', 'rejected', 'cancelled']
    if new_status in critical_changes:
        print(f"CRITICAL STATUS CHANGE: Member {member_id} status changed to '{new_status}' - "
              f"immediate review recommended")

def determine_status_change_type(old_status, new_status):
    """
    Determine the type of status change for categorization
    
    Args:
        old_status (str): Previous status
        new_status (str): New status
        
    Returns:
        str: Type of change (activation, deactivation, approval, etc.)
    """
    if not old_status:
        return 'initial_status_set'
    
    # Define status change patterns
    activation_statuses = ['active', 'approved']
    deactivation_statuses = ['inactive', 'suspended', 'cancelled', 'expired']
    approval_statuses = ['approved']
    rejection_statuses = ['rejected']
    
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

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

# REMOVED: Custom JWT parsing function - now using shared auth system
# This function has been replaced by extract_user_credentials from shared.auth_utils
# REMOVED: Custom JWT parsing logic - now using shared auth system
# The extract_user_credentials function from shared.auth_utils handles all JWT parsing

def validate_field_permissions(user_roles, user_email, member_id, fields_to_update):
    """
    Validate user has permission to modify the requested fields
    
    Args:
        user_roles (list): List of user's roles from JWT token
        user_email (str): User's email from JWT token
        member_id (str): ID of member record being updated
        fields_to_update (dict): Dictionary of fields and values to update
        
    Returns:
        tuple: (is_valid, error_response, forbidden_fields)
               If valid: (True, None, [])
               If invalid: (False, error_response_dict, list_of_forbidden_fields)
    """
    try:
        # Get the member record to check if this is the user's own record
        response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in response:
            return False, {
                'statusCode': 404,
                'headers': cors_headers(),
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
        
        # If there are forbidden fields, log the denial and return error
        if forbidden_fields:
            field_categories = categorize_forbidden_fields(forbidden_fields)
            error_message = build_permission_error_message(forbidden_fields, field_categories, is_own_record)
            
            # Log field-level permission denial for audit purposes
            log_field_permission_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                forbidden_fields=forbidden_fields,
                field_categories=field_categories,
                is_own_record=is_own_record,
                member_email=member_record.get('email', 'unknown')
            )
            
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': error_message,
                    'forbidden_fields': forbidden_fields,
                    'field_categories': field_categories
                })
            }, forbidden_fields
        
        return True, None, []
        
    except Exception as e:
        print(f"Error validating field permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }, []

def categorize_forbidden_fields(forbidden_fields):
    """
    Categorize forbidden fields by type for better error messages
    
    Args:
        forbidden_fields (list): List of field names that are forbidden
        
    Returns:
        dict: Dictionary categorizing fields by type
    """
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
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}

def log_successful_field_update(user_email, user_roles, member_id, updated_fields, field_values=None, member_email=None):
    """
    Log successful field updates for audit trail
    
    Args:
        user_email (str): Email of the user performing the update
        user_roles (list): List of user's roles
        member_id (str): ID of the member record updated
        updated_fields (list): List of fields that were successfully updated
        field_values (dict): Optional dictionary of field names to new values
        member_email (str): Optional email of the member record being updated
    """
    import json
    from datetime import datetime
    
    # Categorize updated fields for better audit tracking
    administrative_fields = [field for field in updated_fields if field in ADMINISTRATIVE_FIELDS]
    personal_fields = [field for field in updated_fields if field in PERSONAL_FIELDS]
    motorcycle_fields = [field for field in updated_fields if field in MOTORCYCLE_FIELDS]
    other_fields = [field for field in updated_fields if field not in ADMINISTRATIVE_FIELDS + PERSONAL_FIELDS + MOTORCYCLE_FIELDS]
    
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
    
    # Add field values for administrative fields (for enhanced audit trail)
    if field_values and administrative_fields:
        log_entry['administrative_field_changes'] = {
            field: field_values.get(field) for field in administrative_fields
        }
    
    # Log as structured JSON for easy parsing by monitoring systems
    print(f"AUDIT_LOG: {json.dumps(log_entry)}")
    
    # Special logging for administrative field changes
    if administrative_fields:
        log_administrative_field_changes(
            user_email, user_roles, member_id, member_email, 
            administrative_fields, field_values
        )

def log_administrative_field_changes(user_email, user_roles, member_id, member_email, admin_fields, field_values=None):
    """
    Enhanced logging specifically for administrative field changes
    
    Args:
        user_email (str): Email of the user performing the update
        user_roles (list): List of user's roles
        member_id (str): ID of the member record updated
        member_email (str): Email of the member record being updated
        admin_fields (list): List of administrative fields that were changed
        field_values (dict): Optional dictionary of field names to new values
    """
    import json
    from datetime import datetime
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ADMINISTRATIVE_FIELD_UPDATE',
        'user_email': user_email,
        'user_roles': user_roles,
        'target_member_id': member_id,
        'target_member_email': member_email,
        'administrative_fields_changed': admin_fields,
        'change_count': len(admin_fields),
        'severity': 'HIGH',  # Administrative changes are high-priority for audit
        'requires_review': True
    }
    
    # Add specific field changes if values are provided
    if field_values:
        log_entry['field_changes'] = {
            field: field_values.get(field) for field in admin_fields
        }
    
    # Special handling for critical fields
    critical_fields = ['status', 'lidmaatschap', 'regio', 'lidnummer']
    critical_changes = [field for field in admin_fields if field in critical_fields]
    if critical_changes:
        log_entry['critical_fields_changed'] = critical_changes
        log_entry['severity'] = 'CRITICAL'
        log_entry['requires_immediate_review'] = True
    
    # Log as structured JSON for monitoring systems
    print(f"ADMIN_AUDIT: {json.dumps(log_entry)}")
    
    # Human-readable log for administrators
    is_own_record = user_email.lower() == (member_email or '').lower()
    target_description = "own record" if is_own_record else f"member record ({member_email})"
    
    print(f"ADMINISTRATIVE CHANGE: User {user_email} (roles: {user_roles}) modified "
          f"administrative fields {admin_fields} on {target_description} (member_id: {member_id})")
    
    if critical_changes:
        print(f"CRITICAL ADMINISTRATIVE CHANGE: Critical fields {critical_changes} were modified - "
              f"immediate review recommended")

def log_field_permission_denial(user_email, user_roles, member_id, forbidden_fields, field_categories, is_own_record, member_email):
    """
    Log field-level permission denials for audit and security monitoring
    
    Args:
        user_email (str): Email of the user attempting the update
        user_roles (list): List of user's roles
        member_id (str): ID of the member record being updated
        forbidden_fields (list): List of fields that were denied
        field_categories (dict): Categorized forbidden fields
        is_own_record (bool): Whether this is the user's own record
        member_email (str): Email of the member record being updated
    """
    import json
    from datetime import datetime
    
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
        'severity': 'WARNING' if is_own_record else 'HIGH'  # Higher severity for cross-user attempts
    }
    
    # Log as structured JSON for easy parsing by monitoring systems
    print(f"SECURITY_AUDIT: {json.dumps(log_entry)}")
    
    # Also log human-readable message
    action_type = "own record" if is_own_record else f"another user's record ({member_email})"
    fields_summary = ", ".join(forbidden_fields)
    print(f"Field permission denied: User {user_email} (roles: {user_roles}) attempted to modify "
          f"forbidden fields [{fields_summary}] on {action_type}")

def build_permission_error_message(forbidden_fields, field_categories, is_own_record):
    """
    Build a descriptive error message for permission violations
    
    Args:
        forbidden_fields (list): List of forbidden field names
        field_categories (dict): Categorized forbidden fields
        is_own_record (bool): Whether this is the user's own record
        
    Returns:
        str: Descriptive error message
    """
    if len(forbidden_fields) == 1:
        field = forbidden_fields[0]
        if field in ADMINISTRATIVE_FIELDS:
            return f"Access denied: Field '{field}' requires administrative privileges to modify"
        elif not is_own_record and (field in PERSONAL_FIELDS or field in MOTORCYCLE_FIELDS):
            return f"Access denied: You can only modify your own {field} information"
        else:
            return f"Access denied: Insufficient permissions to modify field '{field}'"
    
    # Multiple fields - provide categorized message
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
def trigger_role_assignment_if_needed(member_email, old_status, new_status):
    """
    Trigger role assignment Lambda function if status change requires it
    
    Args:
        member_email (str): Member's email address (Cognito username)
        old_status (str): Previous status
        new_status (str): New status
    """
    try:
        # Define status categories
        approved_statuses = ['active', 'approved']
        
        # Check if role assignment change is needed
        old_should_have_role = old_status in approved_statuses if old_status else False
        new_should_have_role = new_status in approved_statuses if new_status else False
        
        if old_should_have_role != new_should_have_role:
            # Role assignment change is needed - invoke role assignment Lambda
            lambda_client = boto3.client('lambda')
            
            payload = {
                'member_email': member_email,
                'action': 'assign_default_role' if new_should_have_role else 'remove_all_roles',
                'status_change': {
                    'old_status': old_status,
                    'new_status': new_status
                }
            }
            
            # Get role assignment function name from environment
            role_assignment_function = os.environ.get('ROLE_ASSIGNMENT_FUNCTION_NAME', 'hdcn-cognito-role-assignment')
            
            try:
                response = lambda_client.invoke(
                    FunctionName=role_assignment_function,
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps(payload)
                )
                
                print(f"Role assignment triggered for {member_email}: {old_status} -> {new_status}")
                
            except Exception as lambda_error:
                # Log error but don't fail the member update
                print(f"Warning: Failed to trigger role assignment for {member_email}: {str(lambda_error)}")
                print(f"Status change completed but role assignment may need manual intervention")
        else:
            print(f"No role assignment change needed for {member_email}: {old_status} -> {new_status}")
            
    except Exception as e:
        # Log error but don't fail the member update
        print(f"Error in role assignment trigger for {member_email}: {str(e)}")

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }
        
        # Extract user credentials using enhanced auth system
        user_email, user_roles, auth_error = extract_user_credentials_fallback(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Use enhanced permission validation with new role structure
        # This replaces the legacy role check
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, 
            ['members_update', 'members_create'],  # Required permissions for member updates
            user_email,
            {'operation': 'update_member'}
        )
        if not is_authorized:
            return error_response
        
        print(f"🔍 AUTH SUCCESS: User {user_email} with roles {user_roles} authorized for member update using new role structure")
        
        # Get member ID and request body
        member_id = event['pathParameters']['id']
        body = json.loads(event['body'])
        
        # Debug: Log the exact request body to see what fields are being sent
        print(f"🔍 DEBUG: Request body fields: {list(body.keys())}")
        print(f"🔍 DEBUG: Full request body: {body}")
        
        # Get member record for validation and logging (we'll need this for multiple purposes)
        member_response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in member_response:
            return create_error_response(404, 'Member record not found')
        
        member_record = member_response['Item']
        member_email = member_record.get('email', '')
        
        # REGIONAL FILTERING: Apply regional access control
        if regional_info and not regional_info.get('has_full_access', False):
            member_region = member_record.get('regio', 'Overig')  # Default to 'Overig' if no region
            allowed_regions = regional_info.get('allowed_regions', [])
            
            # Check if user can access this member's region
            if member_region and allowed_regions and member_region not in allowed_regions:
                print(f"REGIONAL_ACCESS_DENIED: User {user_email} (regions: {allowed_regions}) "
                      f"attempted to update member from region: {member_region}")
                return create_error_response(403, 
                    f'Access denied: You can only update members from regions: {", ".join(allowed_regions)}')
        
        # Log successful regional access check
        if regional_info:
            print(f"✅ Regional access granted for member update: User {user_email} "
                  f"(access: {regional_info.get('access_type', 'unknown')}) updating member from region: {member_record.get('regio', 'Overig')}")
        
        # Validate field permissions
        is_valid, permission_error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, body
        )
        if not is_valid:
            return permission_error
        
        # Special validation for status field changes
        if 'status' in body:
            current_status = member_record.get('status')
            new_status = body['status']
            
            is_status_valid, status_error, status_details = validate_status_change(
                user_roles, user_email, member_id, new_status, current_status
            )
            if not is_status_valid:
                return status_error
        
        # If validation passes, proceed with update
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in body.items():
            if key not in ['member_id', 'updated_at']:  # Exclude member_id and updated_at to avoid conflicts
                # Use ExpressionAttributeNames for all keys to avoid reserved keyword issues
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_params = {
            'Key': {'member_id': member_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        table.update_item(**update_params)
        
        # Log successful update for audit purposes with enhanced information
        log_successful_field_update(
            user_email=user_email,
            user_roles=user_roles,
            member_id=member_id,
            updated_fields=list(body.keys()),
            field_values=body,
            member_email=member_email
        )
        print(f"Member {member_id} updated by user {user_email} with roles {user_roles}. Fields updated: {list(body.keys())}")
        
        return create_success_response({
            'message': 'Member updated successfully',
            'updated_fields': list(body.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_member: {str(e)}")
        return create_error_response(500, 'Internal server error')
