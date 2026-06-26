"""Shared helpers for role management operations."""
import json
import os
import base64

import boto3

from shared.role_permissions import (
    get_combined_permissions,
)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')


def validate_role_assignment_rules(user_id: str, role: str, requesting_user: str) -> bool:
    """
    Validate business rules for role assignments.
    Returns True if assignment is allowed, False otherwise.
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


def validate_role_assignment_permission(event: dict, headers: dict) -> tuple:
    """
    Helper function to validate if the requesting user has permission to assign roles.
    Returns (is_authorized, requesting_user, error_response).
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
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json.loads(payload_decoded)
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


def calculate_user_permissions(roles: list) -> list:
    """
    Calculate user permissions based on assigned roles.
    Uses the centralized role permission mapping constants.
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
