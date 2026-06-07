"""
Auth operations for hdcn_cognito_admin handler.

Contains: get_auth_login, get_auth_permissions, get_pool_info
"""
import json
import base64
import os
from datetime import datetime

import boto3

from shared.role_permissions import get_combined_permissions

# Initialize Cognito client (same as app.py)
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')


def get_pool_info(headers):
    """
    GET /cognito/pool endpoint
    Returns Cognito user pool information.
    """
    response = cognito_client.describe_user_pool(UserPoolId=USER_POOL_ID)

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response['UserPool'], default=str)
    }


def get_auth_login(event, headers):
    """
    GET /auth/login endpoint for user authentication
    Validates user authentication and returns user information with roles
    """
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }

        # Extract JWT token from Authorization header
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid authorization format. Use Bearer token.'})
            }

        jwt_token = auth_header.replace('Bearer ', '')

        # Decode and validate JWT token (simplified validation)
        try:
            # Split JWT token into parts
            parts = jwt_token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")

            # Decode payload (second part)
            payload_encoded = parts[1]
            # Add padding if needed
            payload_encoded += '=' * (4 - len(payload_encoded) % 4)
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_decoded)

            # Extract user information from JWT
            username = payload.get('username') or payload.get('email')
            email = payload.get('email')
            cognito_groups = payload.get('cognito:groups', [])

            if not username:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid token: missing username'})
                }

        except Exception as token_error:
            print(f"Error decoding JWT token: {str(token_error)}")
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid or expired token'})
            }

        # Verify user exists in Cognito and get current information
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )

            # Extract user attributes
            user_attributes = {}
            for attr in user_response.get('UserAttributes', []):
                user_attributes[attr['Name']] = attr['Value']

            # Get current user groups from Cognito
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )

            current_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]

            # Calculate permissions based on roles
            permissions = calculate_user_permissions(current_groups)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'authenticated': True,
                    'user': {
                        'username': username,
                        'email': user_attributes.get('email', email),
                        'given_name': user_attributes.get('given_name'),
                        'family_name': user_attributes.get('family_name'),
                        'user_status': user_response.get('UserStatus'),
                        'enabled': user_response.get('Enabled', True)
                    },
                    'roles': current_groups,
                    'permissions': permissions,
                    'token_groups': cognito_groups,  # Groups from JWT token for comparison
                    'login_time': datetime.now().isoformat()
                })
            }

        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found in system'})
            }
        except Exception as user_error:
            print(f"Error retrieving user information: {str(user_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to retrieve user information'})
            }

    except Exception as e:
        print(f"Error in get_auth_login: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Authentication check failed'})
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


def get_auth_permissions(event, headers):
    """
    GET /auth/permissions endpoint for user permissions
    Returns detailed permissions for the authenticated user
    """
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }

        # Extract JWT token from Authorization header
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid authorization format. Use Bearer token.'})
            }

        jwt_token = auth_header.replace('Bearer ', '')

        # Decode and validate JWT token
        try:
            # Split JWT token into parts
            parts = jwt_token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")

            # Decode payload (second part)
            payload_encoded = parts[1]
            # Add padding if needed
            payload_encoded += '=' * (4 - len(payload_encoded) % 4)
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_decoded)

            # Extract user information from JWT
            username = payload.get('username') or payload.get('email')

            if not username:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid token: missing username'})
                }

        except Exception as token_error:
            print(f"Error decoding JWT token: {str(token_error)}")
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid or expired token'})
            }

        # Get user groups from Cognito
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )

            user_groups = [group['GroupName'] for group in groups_response.get('Groups', [])]

            # Calculate permissions based on roles
            permissions = calculate_user_permissions(user_groups)

            # Get detailed role information
            role_details = []
            for group in groups_response.get('Groups', []):
                role_details.append({
                    'name': group['GroupName'],
                    'description': group.get('Description', ''),
                    'precedence': group.get('Precedence'),
                    'creation_date': group.get('CreationDate'),
                    'last_modified_date': group.get('LastModifiedDate')
                })

            # Organize permissions by category
            permission_categories = {
                'members': [],
                'events': [],
                'products': [],
                'communication': [],
                'system': [],
                'webshop': [],
                'cognito': []
            }

            for permission in permissions:
                category = permission.split(':')[0]
                if category in permission_categories:
                    permission_categories[category].append(permission)
                else:
                    # Handle unknown categories
                    if 'other' not in permission_categories:
                        permission_categories['other'] = []
                    permission_categories['other'].append(permission)

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'username': username,
                    'roles': user_groups,
                    'role_details': role_details,
                    'permissions': permissions,
                    'permission_categories': permission_categories,
                    'permission_count': len(permissions),
                    'is_admin': any(role in ['System_User_Management'] for role in user_groups),
                    'is_regular_member': 'hdcnLeden' in user_groups,
                    'calculated_at': datetime.now().isoformat()
                }, default=str)
            }

        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found in system'})
            }
        except Exception as user_error:
            print(f"Error retrieving user permissions: {str(user_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to retrieve user permissions'})
            }

    except Exception as e:
        print(f"Error in get_auth_permissions: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Permission check failed'})
        }
