"""Role query operations for Cognito User Pool administration."""
import json
import base64
from datetime import datetime

from role_helpers import cognito_client, USER_POOL_ID, calculate_user_permissions


def get_user_roles(user_id: str, event: dict, headers: dict) -> dict:
    """
    GET /auth/users/{user_id}/roles endpoint to get user roles.
    Returns roles assigned to a specific user.
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
