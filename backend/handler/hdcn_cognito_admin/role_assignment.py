"""Role assignment and removal operations for Cognito User Pool administration."""
import json
from datetime import datetime

from role_helpers import (
    cognito_client,
    USER_POOL_ID,
    calculate_user_permissions,
    validate_role_assignment_rules,
    validate_role_assignment_permission,
)


def assign_user_roles_auth(user_id: str, event: dict, headers: dict) -> dict:
    """
    POST /auth/users/{user_id}/roles endpoint to assign roles.
    Assigns one or more roles to a specific user.
    """
    try:
        # Validate requesting user has System_User_Management permission
        is_authorized, requesting_user, error_response = validate_role_assignment_permission(event, headers)
        if not is_authorized:
            return error_response

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
            cognito_client.admin_get_user(
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
                'body': json.dumps({'error': 'Rate limit exceeded. Please try again later.', 'retry_after': 60})
            }
        except cognito_client.exceptions.InternalErrorException:
            print("Cognito internal error while validating groups")
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({'error': 'Service temporarily unavailable. Please try again later.', 'service': 'cognito'})
            }
        except Exception as groups_error:
            print(f"Error validating groups: {str(groups_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to validate roles', 'details': 'Unable to retrieve available roles from the system'})
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
                errors.append(f"User {user_id} not found while assigning role {role}")
            except cognito_client.exceptions.ResourceNotFoundException:
                errors.append(f"Role {role} not found in Cognito")
            except cognito_client.exceptions.TooManyRequestsException:
                errors.append(f"Rate limit exceeded while assigning role {role}")
            except cognito_client.exceptions.InternalErrorException:
                errors.append(f"Cognito internal error while assigning role {role}")
            except cognito_client.exceptions.InvalidParameterException as param_error:
                errors.append(f"Invalid parameter while assigning role {role}: {str(param_error)}")
            except Exception as assign_error:
                errors.append(f"Failed to assign role {role}: {str(assign_error)}")

        # Get updated user roles and permissions
        try:
            updated_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            updated_roles = [group['GroupName'] for group in updated_groups_response.get('Groups', [])]
            updated_permissions = calculate_user_permissions(updated_roles)
        except Exception:
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


def remove_user_role_auth(user_id: str, role: str, event: dict, headers: dict) -> dict:
    """
    DELETE /auth/users/{user_id}/roles/{role} endpoint to remove roles.
    Removes a specific role from a user.
    """
    try:
        # Validate requesting user has System_User_Management permission
        is_authorized, requesting_user, error_response = validate_role_assignment_permission(event, headers)
        if not is_authorized:
            return error_response

        # Verify target user exists
        try:
            cognito_client.admin_get_user(
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
                'body': json.dumps({'error': 'Rate limit exceeded. Please try again later.', 'retry_after': 60})
            }
        except cognito_client.exceptions.InternalErrorException:
            print("Cognito internal error while validating role")
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({'error': 'Service temporarily unavailable. Please try again later.', 'service': 'cognito'})
            }
        except Exception as groups_error:
            print(f"Error validating groups: {str(groups_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to validate role', 'details': 'Unable to retrieve available roles from the system'})
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
                'body': json.dumps({'error': f'User {user_id} not found', 'details': 'The specified user does not exist in the system'})
            }
        except cognito_client.exceptions.ResourceNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Role {role} not found', 'details': 'The specified role does not exist in the system'})
            }
        except cognito_client.exceptions.TooManyRequestsException:
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({'error': 'Rate limit exceeded. Please try again later.', 'retry_after': 60})
            }
        except cognito_client.exceptions.InternalErrorException:
            return {
                'statusCode': 503,
                'headers': headers,
                'body': json.dumps({'error': 'Service temporarily unavailable. Please try again later.', 'service': 'cognito'})
            }
        except cognito_client.exceptions.InvalidParameterException as param_error:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Invalid parameter: {str(param_error)}', 'details': 'The request contains invalid parameters'})
            }
        except Exception as remove_error:
            print(f"Error removing role {role} from user {user_id}: {str(remove_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': f'Failed to remove role {role} from user', 'details': 'An unexpected error occurred during role removal'})
            }

    except Exception as e:
        print(f"Error in remove_user_role_auth: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to remove user role'})
        }
