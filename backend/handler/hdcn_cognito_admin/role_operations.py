"""Role management operations for Cognito User Pool administration."""
import json
import os
import base64
from datetime import datetime

import boto3

from shared.role_permissions import (
    get_combined_permissions,
)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')


def validate_role_assignment_rules(user_id, role, requesting_user):
    """
    Validate business rules for role assignments
    Returns True if assignment is allowed, False otherwise
    """
    try:
        # Rule 1: Prevent assignment of conflicting roles
        # NOTE: Legacy _All roles have been removed - no conflicts to check
        CONFLICTING_ROLES = {
            # Legacy conflicting roles have been removed
            # New role structure uses Permission + Region combinations
        }
        
        # Get current user roles
        try:
            current_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            current_roles = [group['GroupName'] for group in current_groups_response.get('Groups', [])]
        except Exception:
            current_roles = []
        
        # Check for conflicting roles
        if role in CONFLICTING_ROLES:
            conflicting_roles = CONFLICTING_ROLES[role]
            for conflicting_role in conflicting_roles:
                if conflicting_role in current_roles:
                    print(f"Role assignment blocked: {role} conflicts with existing role {conflicting_role} for user {user_id}")
                    return False
        
        # Rule 2: Prevent self-assignment of System_User_Management unless already admin
        if role == 'System_User_Management' and requesting_user == user_id:
            try:
                requesting_user_groups = cognito_client.admin_list_groups_for_user(
                    UserPoolId=USER_POOL_ID,
                    Username=requesting_user
                )
                requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
                
                if 'System_User_Management' not in requesting_user_roles:
                    print(f"Self-assignment of System_User_Management blocked for user {user_id}")
                    return False
            except Exception:
                print(f"Could not verify self-assignment rules for user {user_id}")
                return False
        
        # Rule 3: Validate regional role assignments (future enhancement)
        # This could include checking if user belongs to the correct region
        # for regional roles like Members_Read_Region1, etc.
        
        return True
        
    except Exception as validation_error:
        print(f"Error in role assignment validation: {str(validation_error)}")
        return False


def validate_role_assignment_permission(event, headers):
    """
    Helper function to validate if the requesting user has permission to assign roles
    Returns (is_authorized, requesting_user, error_response)
    """
    try:
        # Extract Authorization header for permission check
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return False, None, {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate requesting user has permission to assign roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import json as json_lib
                
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json_lib.loads(payload_decoded)
                    requesting_user = payload.get('username') or payload.get('email')
                    
            except Exception as token_error:
                print(f"Error decoding requesting user token: {str(token_error)}")
                return False, None, {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid authorization token'})
                }
        
        if not requesting_user:
            return False, None, {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }
        
        # Check if requesting user has permission to assign roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can assign roles
            can_assign_roles = 'System_User_Management' in requesting_user_roles
            
            if not can_assign_roles:
                return False, requesting_user, {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to assign user roles',
                        'required_roles': ['System_User_Management']
                    })
                }
                
        except Exception as perm_error:
            print(f"Error checking requesting user permissions: {str(perm_error)}")
            return False, requesting_user, {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to verify permissions'})
            }
        
        return True, requesting_user, None
        
    except Exception as e:
        print(f"Error in validate_role_assignment_permission: {str(e)}")
        return False, None, {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to validate permissions'})
        }


def calculate_user_permissions(roles):
    """
    Calculate user permissions based on assigned roles
    Uses the centralized role permission mapping constants
    """
    try:
        # Validate input
        if not roles:
            print("Warning: No roles provided to calculate_user_permissions")
            return []
        
        if not isinstance(roles, (list, tuple)):
            print(f"Warning: Invalid roles type in calculate_user_permissions: {type(roles)}")
            return []
        
        # Use the centralized permission calculation function
        return get_combined_permissions(roles)
        
    except Exception as e:
        print(f"Error in calculate_user_permissions: {str(e)}")
        # Return minimal permissions in case of error
        return ['members:read_own', 'events:read_public', 'products:browse_catalog']


def get_user_roles(user_id, event, headers):
    """
    GET /auth/users/{user_id}/roles endpoint to get user roles
    Returns roles assigned to a specific user
    """
    try:
        # Extract Authorization header for permission check
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate requesting user has permission to view user roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import json as json_lib
                
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json_lib.loads(payload_decoded)
                    requesting_user = payload.get('username') or payload.get('email')
                    
            except Exception as token_error:
                print(f"Error decoding requesting user token: {str(token_error)}")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid authorization token'})
                }
        
        if not requesting_user:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }
        
        # Check if requesting user has permission to view user roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can view other users' roles
            # Users can always view their own roles
            can_view_roles = (
                user_id == requesting_user or
                'System_User_Management' in requesting_user_roles
            )
            
            if not can_view_roles:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to view user roles',
                        'required_roles': ['System_User_Management']
                    })
                }
                
        except Exception as perm_error:
            print(f"Error checking requesting user permissions: {str(perm_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to verify permissions'})
            }
        
        # Get target user information and roles
        try:
            # Verify target user exists
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            
            # Extract user attributes
            user_attributes = {}
            for attr in user_response.get('UserAttributes', []):
                user_attributes[attr['Name']] = attr['Value']
            
            # Get user groups/roles
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            
            # Format role information
            roles = []
            for group in groups_response.get('Groups', []):
                roles.append({
                    'name': group['GroupName'],
                    'description': group.get('Description', ''),
                    'precedence': group.get('Precedence'),
                    'creation_date': group.get('CreationDate'),
                    'last_modified_date': group.get('LastModifiedDate')
                })
            
            # Calculate permissions for this user
            role_names = [role['name'] for role in roles]
            permissions = calculate_user_permissions(role_names)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'user_id': user_id,
                    'user_info': {
                        'username': user_id,
                        'email': user_attributes.get('email'),
                        'given_name': user_attributes.get('given_name'),
                        'family_name': user_attributes.get('family_name'),
                        'user_status': user_response.get('UserStatus'),
                        'enabled': user_response.get('Enabled', True)
                    },
                    'roles': roles,
                    'role_names': role_names,
                    'permissions': permissions,
                    'role_count': len(roles),
                    'is_admin': any(role in ['System_User_Management'] for role in role_names),
                    'is_regular_member': 'hdcnLeden' in role_names,
                    'requested_by': requesting_user,
                    'retrieved_at': datetime.now().isoformat()
                })
            }
            
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'User {user_id} not found'})
            }
        except Exception as user_error:
            print(f"Error retrieving user roles for {user_id}: {str(user_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to retrieve user roles'})
            }
        
    except Exception as e:
        print(f"Error in get_user_roles: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get user roles'})
        }


def assign_user_roles_auth(user_id, event, headers):
    """
    POST /auth/users/{user_id}/roles endpoint to assign roles
    Assigns one or more roles to a specific user
    """
    try:
        # Extract Authorization header for permission check
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate requesting user has permission to assign roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import json as json_lib
                
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json_lib.loads(payload_decoded)
                    requesting_user = payload.get('username') or payload.get('email')
                    
            except Exception as token_error:
                print(f"Error decoding requesting user token: {str(token_error)}")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid authorization token'})
                }
        
        if not requesting_user:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }
        
        # Check if requesting user has permission to assign roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can assign roles
            can_assign_roles = 'System_User_Management' in requesting_user_roles
            
            if not can_assign_roles:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to assign user roles',
                        'required_roles': ['System_User_Management']
                    })
                }
                
        except Exception as perm_error:
            print(f"Error checking requesting user permissions: {str(perm_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to verify permissions'})
            }
        
        # Parse request body
        try:
            data = json.loads(event['body'])
            roles_to_assign = data.get('roles', [])
            
            if not roles_to_assign:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'No roles specified for assignment'})
                }
            
            # Ensure roles_to_assign is a list
            if isinstance(roles_to_assign, str):
                roles_to_assign = [roles_to_assign]
            
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Verify target user exists
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'User {user_id} not found'})
            }
        
        # Validate that all roles exist in Cognito
        try:
            all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
            existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]
            
            invalid_roles = [role for role in roles_to_assign if role not in existing_groups]
            if invalid_roles:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Invalid roles specified',
                        'invalid_roles': invalid_roles,
                        'available_roles': existing_groups,
                        'details': f'The following roles do not exist in the system: {", ".join(invalid_roles)}'
                    })
                }
                
        except cognito_client.exceptions.TooManyRequestsException:
            print("Rate limit exceeded while validating groups")
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                })
            }
        except cognito_client.exceptions.InternalErrorException:
            print("Cognito internal error while validating groups")
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Service temporarily unavailable. Please try again later.',
                    'service': 'cognito'
                })
            }
        except Exception as groups_error:
            print(f"Error validating groups: {str(groups_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Failed to validate roles',
                    'details': 'Unable to retrieve available roles from the system'
                })
            }
        
        # Get current user roles to avoid duplicates
        try:
            current_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            current_roles = [group['GroupName'] for group in current_groups_response.get('Groups', [])]
            
        except Exception as current_roles_error:
            print(f"Error getting current user roles: {str(current_roles_error)}")
            current_roles = []
        
        # Assign roles to user
        assigned_roles = []
        already_assigned = []
        errors = []
        
        for role in roles_to_assign:
            try:
                if role in current_roles:
                    already_assigned.append(role)
                    continue
                
                # Additional validation for role assignment business rules
                if not validate_role_assignment_rules(user_id, role, requesting_user):
                    errors.append(f"Role assignment rule violation for role {role}")
                    continue
                
                cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=user_id,
                    GroupName=role
                )
                assigned_roles.append(role)
                
            except cognito_client.exceptions.UserNotFoundException:
                error_msg = f"User {user_id} not found while assigning role {role}"
                errors.append(error_msg)
                print(error_msg)
            except cognito_client.exceptions.ResourceNotFoundException:
                error_msg = f"Role {role} not found in Cognito"
                errors.append(error_msg)
                print(error_msg)
            except cognito_client.exceptions.TooManyRequestsException:
                error_msg = f"Rate limit exceeded while assigning role {role}"
                errors.append(error_msg)
                print(error_msg)
            except cognito_client.exceptions.InternalErrorException:
                error_msg = f"Cognito internal error while assigning role {role}"
                errors.append(error_msg)
                print(error_msg)
            except cognito_client.exceptions.InvalidParameterException as param_error:
                error_msg = f"Invalid parameter while assigning role {role}: {str(param_error)}"
                errors.append(error_msg)
                print(error_msg)
            except Exception as assign_error:
                error_msg = f"Failed to assign role {role}: {str(assign_error)}"
                errors.append(error_msg)
                print(error_msg)
        
        # Get updated user roles and permissions
        try:
            updated_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            updated_roles = [group['GroupName'] for group in updated_groups_response.get('Groups', [])]
            updated_permissions = calculate_user_permissions(updated_roles)
            
        except Exception as update_error:
            print(f"Error getting updated user roles: {str(update_error)}")
            updated_roles = current_roles + assigned_roles
            updated_permissions = calculate_user_permissions(updated_roles)
        
        # Prepare response
        response_data = {
            'user_id': user_id,
            'assigned_roles': assigned_roles,
            'already_assigned': already_assigned,
            'errors': errors,
            'current_roles': updated_roles,
            'permissions': updated_permissions,
            'assigned_by': requesting_user,
            'assigned_at': datetime.now().isoformat()
        }
        
        # Determine response status
        if assigned_roles:
            status_code = 200
            response_data['message'] = f'Successfully assigned {len(assigned_roles)} role(s) to user {user_id}'
        elif already_assigned and not errors:
            status_code = 200
            response_data['message'] = f'All specified roles were already assigned to user {user_id}'
        elif errors and not assigned_roles:
            status_code = 500
            response_data['message'] = 'Failed to assign any roles'
        else:
            status_code = 207  # Multi-status (partial success)
            response_data['message'] = f'Partial success: assigned {len(assigned_roles)} roles, {len(errors)} errors'
        
        return {
            'statusCode': status_code,
            'headers': headers,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"Error in assign_user_roles_auth: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to assign user roles'})
        }


def remove_user_role_auth(user_id, role, event, headers):
    """
    DELETE /auth/users/{user_id}/roles/{role} endpoint to remove roles
    Removes a specific role from a user
    """
    try:
        # Extract Authorization header for permission check
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate requesting user has permission to remove roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import json as json_lib
                
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json_lib.loads(payload_decoded)
                    requesting_user = payload.get('username') or payload.get('email')
                    
            except Exception as token_error:
                print(f"Error decoding requesting user token: {str(token_error)}")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid authorization token'})
                }
        
        if not requesting_user:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }
        
        # Check if requesting user has permission to remove roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can remove roles
            can_remove_roles = 'System_User_Management' in requesting_user_roles
            
            if not can_remove_roles:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to remove user roles',
                        'required_roles': ['System_User_Management']
                    })
                }
                
        except Exception as perm_error:
            print(f"Error checking requesting user permissions: {str(perm_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to verify permissions'})
            }
        
        # Verify target user exists
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'User {user_id} not found'})
            }
        
        # Validate that the role exists in Cognito
        try:
            all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
            existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]
            
            if role not in existing_groups:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'Role {role} does not exist',
                        'available_roles': existing_groups,
                        'details': f'The role "{role}" is not a valid role in the system'
                    })
                }
                
        except cognito_client.exceptions.TooManyRequestsException:
            print("Rate limit exceeded while validating role")
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                })
            }
        except cognito_client.exceptions.InternalErrorException:
            print("Cognito internal error while validating role")
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Service temporarily unavailable. Please try again later.',
                    'service': 'cognito'
                })
            }
        except Exception as groups_error:
            print(f"Error validating groups: {str(groups_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Failed to validate role',
                    'details': 'Unable to retrieve available roles from the system'
                })
            }
        
        # Get current user roles to check if role is assigned
        try:
            current_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            current_roles = [group['GroupName'] for group in current_groups_response.get('Groups', [])]
            
            if role not in current_roles:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'User {user_id} is not assigned to role {role}',
                        'current_roles': current_roles
                    })
                }
                
        except Exception as current_roles_error:
            print(f"Error getting current user roles: {str(current_roles_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to get current user roles'})
            }
        
        # Prevent removal of hdcnLeden role (basic member role should always be present)
        if role == 'hdcnLeden':
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Cannot remove hdcnLeden role - this is the basic member role',
                    'role': role,
                    'details': 'The hdcnLeden role is required for all members and cannot be removed'
                })
            }
        
        # Prevent removal of System_User_Management from self unless other admins exist
        if role == 'System_User_Management' and requesting_user == user_id:
            try:
                # Check if there are other users with System_User_Management role
                users_in_group_response = cognito_client.list_users_in_group(
                    UserPoolId=USER_POOL_ID,
                    GroupName='System_User_Management'
                )
                admin_users = users_in_group_response.get('Users', [])
                
                if len(admin_users) <= 1:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({
                            'error': 'Cannot remove System_User_Management role from yourself',
                            'details': 'You are the only user with System_User_Management role. At least one admin must remain.'
                        })
                    }
            except Exception as admin_check_error:
                print(f"Error checking admin users: {str(admin_check_error)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Failed to validate admin role removal',
                        'details': 'Unable to verify if other administrators exist'
                    })
                }
        
        # Remove role from user
        try:
            cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=user_id,
                GroupName=role
            )
            
            # Get updated user roles and permissions
            updated_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            updated_roles = [group['GroupName'] for group in updated_groups_response.get('Groups', [])]
            updated_permissions = calculate_user_permissions(updated_roles)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': f'Successfully removed role {role} from user {user_id}',
                    'user_id': user_id,
                    'removed_role': role,
                    'remaining_roles': updated_roles,
                    'permissions': updated_permissions,
                    'removed_by': requesting_user,
                    'removed_at': datetime.now().isoformat()
                })
            }
            
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': f'User {user_id} not found',
                    'details': 'The specified user does not exist in the system'
                })
            }
        except cognito_client.exceptions.ResourceNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Role {role} not found',
                    'details': 'The specified role does not exist in the system'
                })
            }
        except cognito_client.exceptions.TooManyRequestsException:
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 60
                })
            }
        except cognito_client.exceptions.InternalErrorException:
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Service temporarily unavailable. Please try again later.',
                    'service': 'cognito'
                })
            }
        except cognito_client.exceptions.InvalidParameterException as param_error:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Invalid parameter: {str(param_error)}',
                    'details': 'The request contains invalid parameters'
                })
            }
        except Exception as remove_error:
            print(f"Error removing role {role} from user {user_id}: {str(remove_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Failed to remove role {role} from user',
                    'details': 'An unexpected error occurred during role removal'
                })
            }
        
    except Exception as e:
        print(f"Error in remove_user_role_auth: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to remove user role'})
        }
