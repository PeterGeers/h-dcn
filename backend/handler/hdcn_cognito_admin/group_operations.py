"""Group management operations for Cognito User Pool administration."""
import json
import os
import base64
from datetime import datetime

import boto3

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')


def get_groups(headers):
    # Use pagination to ensure we get all groups
    all_groups = []
    paginator = cognito_client.get_paginator('list_groups')

    try:
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            all_groups.extend(page.get('Groups', []))

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(all_groups, default=str)
        }
    except Exception as e:
        print(f"Error listing groups with pagination: {str(e)}")
        # Fallback to original method if pagination fails
        response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response['Groups'], default=str)
        }


def create_group(event, headers):
    data = json.loads(event['body'])

    response = cognito_client.create_group(
        UserPoolId=USER_POOL_ID,
        GroupName=data['groupName'],
        Description=data.get('description', '')
    )

    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({'message': 'Group created successfully', 'group': response['Group']}, default=str)
    }


def delete_group(group_name, headers):
    cognito_client.delete_group(
        UserPoolId=USER_POOL_ID,
        GroupName=group_name
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'Group deleted successfully'})
    }


def add_user_to_group(username, group_name, headers):
    # Note: This function is deprecated in favor of assign_user_roles_auth
    # which includes proper role assignment validation
    # This function is kept for backward compatibility but should not be used
    # for new implementations

    cognito_client.admin_add_user_to_group(
        UserPoolId=USER_POOL_ID,
        Username=username,
        GroupName=group_name
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User added to group successfully'})
    }


def remove_user_from_group(username, group_name, headers):
    # Note: This function is deprecated in favor of remove_user_role_auth
    # which includes proper role assignment validation
    # This function is kept for backward compatibility but should not be used
    # for new implementations

    cognito_client.admin_remove_user_from_group(
        UserPoolId=USER_POOL_ID,
        Username=username,
        GroupName=group_name
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User removed from group successfully'})
    }


def get_user_groups(username, headers):
    response = cognito_client.admin_list_groups_for_user(
        UserPoolId=USER_POOL_ID,
        Username=username
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response['Groups'], default=str)
    }


def import_groups(event, headers):
    data = json.loads(event['body'])
    groups = data.get('groups', [])

    created_groups = []
    errors = []

    for group_data in groups:
        try:
            response = cognito_client.create_group(
                UserPoolId=USER_POOL_ID,
                GroupName=group_data['groupName'],
                Description=group_data.get('description', '')
            )
            created_groups.append(group_data['groupName'])
        except cognito_client.exceptions.GroupExistsException:
            errors.append(f"Group {group_data['groupName']} already exists")
        except Exception as e:
            errors.append(f"Failed to create group {group_data['groupName']}: {str(e)}")

    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({
            'message': f'Import completed. Created {len(created_groups)} groups.',
            'created_groups': created_groups,
            'errors': errors
        })
    }


def assign_user_groups(event, headers):
    """
    Bulk assign groups to users with role assignment validation
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
        data = json.loads(event['body'])
        users = data.get('users', [])

        if not users:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No users specified for group assignment'})
            }

        assigned_count = 0
        errors = []

        for user_data in users:
            username = user_data.get('username')
            groups = user_data.get('groups', '')

            if not username or not groups:
                errors.append(f"Missing username or groups for user: {user_data}")
                continue

            group_list = [g.strip() for g in groups.split(';') if g.strip()]

            # Verify user exists
            try:
                cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
            except cognito_client.exceptions.UserNotFoundException:
                errors.append(f"User {username} not found")
                continue

            for group_name in group_list:
                try:
                    # Validate that the group exists
                    all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
                    existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]

                    if group_name not in existing_groups:
                        errors.append(f"Group {group_name} does not exist")
                        continue

                    cognito_client.admin_add_user_to_group(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        GroupName=group_name
                    )
                    assigned_count += 1
                except Exception as e:
                    errors.append(f"Failed to add {username} to {group_name}: {str(e)}")

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': f'Group assignment completed. {assigned_count} assignments made.',
                'assigned_count': assigned_count,
                'errors': errors,
                'assigned_by': requesting_user,
                'assigned_at': datetime.now().isoformat()
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error in assign_user_groups: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to assign user groups'})
        }


def get_users_in_group(group_name, headers):
    try:
        response = cognito_client.list_users_in_group(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name
        )
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response['Users'], default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
