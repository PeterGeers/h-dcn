import json
import boto3
import base64
from datetime import datetime
import os

# Import from extracted helper modules (same handler directory)
from status_validation import (
    validate_status_change,
    trigger_role_assignment_if_needed,
)
from field_validation import (
    validate_field_permissions,
    log_successful_field_update,
)

# Import role_permissions from shared layer
from shared.role_permissions import can_edit_field, PERSONAL_FIELDS, MOTORCYCLE_FIELDS, ADMINISTRATIVE_FIELDS, get_combined_permissions


def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }


# Fallback auth utilities (in case layer doesn't work)
def extract_user_credentials_fallback(event):
    """Extract user credentials with enhanced groups support"""
    try:
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
        enhanced_groups_header = (
            event.get('headers', {}).get('X-Enhanced-Groups')
            or event.get('headers', {}).get('x-enhanced-groups')
        )

        if enhanced_groups_header:
            try:
                enhanced_groups = json.loads(enhanced_groups_header)
                if isinstance(enhanced_groups, list):
                    print(f"FALLBACK AUTH: Using enhanced groups: {enhanced_groups} for {user_email}")
                    return user_email, enhanced_groups, None
            except json.JSONDecodeError:
                pass

        user_roles = payload.get('cognito:groups', [])
        print(f"FALLBACK AUTH: Using JWT groups: {user_roles} for {user_email}")
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
    UPDATED permission validation using new role structure.
    Replaces old Members_CRUD_All references with new permission + region validation.
    """
    try:
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]

        # SYSTEM ADMIN ROLES (Full access, no region required)
        system_admin_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
        if any(role in system_admin_roles for role in user_roles):
            return True, None

        # LEGACY ADMIN ROLES (Backward compatibility)
        legacy_admin_roles = ['National_Chairman', 'National_Secretary']
        if any(role in legacy_admin_roles for role in user_roles):
            return True, None

        # NEW ROLE STRUCTURE: Permission-based roles
        permission_roles = [
            'Members_CRUD', 'Members_Read', 'Members_Export',
            'Events_CRUD', 'Events_Read', 'Events_Export',
            'Products_CRUD', 'Products_Read', 'Products_Export',
            'Communication_CRUD', 'Communication_Read', 'Communication_Export',
            'Webshop_Management', 'Members_Status_Approve'
        ]

        user_permission_roles = [role for role in user_roles if role in permission_roles]
        if user_permission_roles:
            region_roles = [role for role in user_roles if role.startswith('Regio_')]
            if region_roles:
                return True, None
            else:
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

        # LEGACY COMPATIBILITY: Check for old _All roles (being phased out)
        legacy_all_roles = [role for role in user_roles if role.endswith('_All') and not role.startswith('Regio_')]
        if legacy_all_roles:
            return True, None

        # SPECIAL ROLES: Limited access roles
        special_roles = ['hdcnLeden', 'Verzoek Lid']
        if any(role in special_roles for role in user_roles):
            return True, None

        # No valid roles found
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
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        cors_headers,
        handle_options_request
    )
    from shared.i18n.locale_resolver import resolve_request_locale
    print("Successfully imported enhanced auth from shared layer")

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
    print("Shared auth layer import failed, using enhanced fallback auth")

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


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }

        # Resolve locale from Accept-Language header
        locale = resolve_request_locale(event)

        # Extract user credentials using enhanced auth system
        user_email, user_roles, auth_error = extract_user_credentials_fallback(event)
        if auth_error:
            return auth_error

        # Use enhanced permission validation with new role structure
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles,
            ['members_update', 'members_create'],
            user_email,
            {'operation': 'update_member'}
        )
        if not is_authorized:
            return error_response

        print(f"AUTH SUCCESS: User {user_email} with roles {user_roles} authorized for member update")

        # Get member ID and request body
        member_id = event['pathParameters']['id']
        body = json.loads(event['body'])

        print(f"DEBUG: Request body fields: {list(body.keys())}")

        # Get member record for validation and logging
        member_response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in member_response:
            return create_error_response(404, 'Member record not found',
                                         error_key='member_not_found', locale=locale)

        member_record = member_response['Item']
        member_email = member_record.get('email', '')

        # REGIONAL FILTERING: Apply regional access control
        if regional_info and not regional_info.get('has_full_access', False):
            member_region = member_record.get('regio', 'Overig')
            allowed_regions = regional_info.get('allowed_regions', [])

            if member_region and allowed_regions and member_region not in allowed_regions:
                print(f"REGIONAL_ACCESS_DENIED: User {user_email} (regions: {allowed_regions}) "
                      f"attempted to update member from region: {member_region}")
                return create_error_response(403,
                    f'Access denied: You can only update members from regions: {", ".join(allowed_regions)}',
                    error_key='forbidden', locale=locale)

        if regional_info:
            print(f"Regional access granted: User {user_email} "
                  f"(access: {regional_info.get('access_type', 'unknown')}) "
                  f"updating member from region: {member_record.get('regio', 'Overig')}")

        # Validate field permissions
        is_valid, permission_error, forbidden_fields = validate_field_permissions(
            table, user_roles, user_email, member_id, body, cors_headers
        )
        if not is_valid:
            return permission_error

        # Special validation for status field changes
        if 'status' in body:
            current_status = member_record.get('status')
            new_status = body['status']

            is_status_valid, status_error, status_details = validate_status_change(
                user_roles, user_email, member_id, new_status, current_status, cors_headers
            )
            if not is_status_valid:
                return status_error

        # Build DynamoDB update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}

        for key, value in body.items():
            if key not in ['member_id', 'updated_at']:
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

        # Trigger role assignment if status changed
        if 'status' in body:
            current_status = member_record.get('status')
            new_status = body['status']
            if current_status != new_status:
                trigger_role_assignment_if_needed(member_email, current_status, new_status)

        # Log successful update for audit purposes
        log_successful_field_update(
            user_email=user_email,
            user_roles=user_roles,
            member_id=member_id,
            updated_fields=list(body.keys()),
            field_values=body,
            member_email=member_email
        )
        print(f"Member {member_id} updated by user {user_email}. Fields: {list(body.keys())}")

        return create_success_response({
            'message': 'Member updated successfully',
            'updated_fields': list(body.keys())
        })

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}',
                                     error_key='validation_error', locale=locale)
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body',
                                     error_key='invalid_input', locale=locale)
    except Exception as e:
        print(f"Unexpected error in update_member: {str(e)}")
        return create_error_response(500, 'Internal server error',
                                     error_key='internal_error', locale=locale)
