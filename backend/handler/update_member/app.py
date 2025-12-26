import json
import boto3
import base64
from datetime import datetime
import sys
import os

# Add the role_permissions module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'hdcn_cognito_admin'))
from role_permissions import can_edit_field, PERSONAL_FIELDS, MOTORCYCLE_FIELDS, ADMINISTRATIVE_FIELDS

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
        # Check if user has Members_CRUD_All role (required for status changes)
        if 'Members_CRUD_All' not in user_roles:
            validation_details['validation_result'] = 'DENIED'
            validation_details['reason'] = 'Missing Members_CRUD_All role'
            
            # Log the denial attempt
            log_status_change_denial(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                attempted_status=new_status,
                current_status=current_status,
                reason='Insufficient role permissions'
            )
            
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: Only users with Members_CRUD_All role can modify member status',
                    'field': 'status',
                    'required_role': 'Members_CRUD_All',
                    'user_roles': user_roles
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
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def extract_user_roles_from_jwt(event):
    """
    Extract user roles from JWT token in Authorization header
    
    Args:
        event: Lambda event containing headers
        
    Returns:
        tuple: (user_email, user_roles, error_response)
               If successful: (email_string, roles_list, None)
               If error: (None, None, error_response_dict)
    """
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate Bearer token format
        if not auth_header.startswith('Bearer '):
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid authorization header format'})
            }
        
        # Extract JWT token
        jwt_token = auth_header.replace('Bearer ', '')
        
        # Decode JWT token to get user info and roles
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token format'})
            }
        
        # Decode payload (second part of JWT)
        payload_encoded = parts[1]
        # Add padding if needed for base64 decoding
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        # Extract user email and roles
        user_email = payload.get('email') or payload.get('username')
        user_roles = payload.get('cognito:groups', [])
        
        if not user_email:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        return user_email, user_roles, None
        
    except Exception as e:
        print(f"Error extracting user roles from JWT: {str(e)}")
        return None, None, {
            'statusCode': 401,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid authorization token'})
        }

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
        
        # Extract user roles from JWT token
        user_email, user_roles, auth_error = extract_user_roles_from_jwt(event)
        if auth_error:
            return auth_error
        
        # Get member ID and request body
        member_id = event['pathParameters']['id']
        body = json.loads(event['body'])
        
        # Get member record for validation and logging (we'll need this for multiple purposes)
        member_response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in member_response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Member record not found'})
            }
        
        member_record = member_response['Item']
        member_email = member_record.get('email', '')
        
        # Special validation for status field changes
        if 'status' in body:
            current_status = member_record.get('status')
            new_status = body['status']
            
            # Validate status change
            status_valid, status_error, status_validation = validate_status_change(
                user_roles, user_email, member_id, new_status, current_status
            )
            if not status_valid:
                return status_error
        
        # Validate field permissions
        is_valid, permission_error, forbidden_fields = validate_field_permissions(
            user_roles, user_email, member_id, body
        )
        if not is_valid:
            return permission_error
        
        # Get member record for enhanced logging (we already validated it exists in validate_field_permissions)
        member_response = table.get_item(Key={'member_id': member_id})
        member_record = member_response.get('Item', {})
        member_email = member_record.get('email', '')
        
        # If validation passes, proceed with update
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in body.items():
            if key != 'member_id':
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
        
        # Special logging for status changes
        if 'status' in body:
            old_status = member_record.get('status')
            new_status = body['status']
            log_status_change_success(
                user_email=user_email,
                user_roles=user_roles,
                member_id=member_id,
                member_email=member_email,
                old_status=old_status,
                new_status=new_status
            )
            
            # Trigger role assignment if status changed to approved
            trigger_role_assignment_if_needed(member_email, old_status, new_status)
        
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
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'message': 'Member updated successfully',
                'updated_fields': list(body.keys())
            })
        }
        
    except KeyError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Unexpected error in update_member: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }
