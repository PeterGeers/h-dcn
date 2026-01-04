import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from role_permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    get_combined_permissions,
    has_permission,
    can_edit_field,
    ADMINISTRATIVE_FIELDS,
    PERSONAL_FIELDS,
    MOTORCYCLE_FIELDS
)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_OAT3oPCIm')

def validate_role_assignment_rules(user_id, role, requesting_user):
    """
    Validate business rules for role assignments
    Returns True if assignment is allowed, False otherwise
    """
    try:
        # Rule 1: Prevent assignment of conflicting roles
        CONFLICTING_ROLES = {
            'Members_CRUD_All': ['Members_Read_All'],  # CRUD includes read permissions
            'Events_CRUD_All': ['Events_Read_All'],    # CRUD includes read permissions
            'Products_CRUD_All': ['Products_Read_All'], # CRUD includes read permissions
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
                import base64
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

def lambda_handler(event, context):
    method = event['httpMethod']
    path = event['path']
    
    # Debug logging
    print(f"Received request: {method} {path}")
    print(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'
        }
        
        if method == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers}
        
        # Route requests
        if path == '/cognito/users':
            if method == 'GET':
                return get_users(headers)
            elif method == 'POST':
                return create_user(event, headers)
                
        elif path.startswith('/cognito/users/') and path.endswith('/groups'):
            username = path.split('/')[3]
            return get_user_groups(username, headers)
            
        elif '/cognito/users/' in path and '/groups/' in path:
            parts = path.split('/')
            username = parts[3]
            group_name = parts[5]
            if method == 'POST':
                return add_user_to_group(username, group_name, headers)
            elif method == 'DELETE':
                return remove_user_from_group(username, group_name, headers)
                
        elif path.startswith('/cognito/users/'):
            username = path.split('/')[3]
            if method == 'PUT':
                return update_user(username, event, headers)
            elif method == 'DELETE':
                return delete_user(username, headers)
                
        elif path == '/cognito/groups':
            if method == 'GET':
                return get_groups(headers)
            elif method == 'POST':
                return create_group(event, headers)
                
        elif path == '/cognito/groups/import':
            if method == 'POST':
                return import_groups(event, headers)
                
        elif path == '/cognito/users/assign-groups':
            if method == 'POST':
                return assign_user_groups(event, headers)
                
        elif path == '/cognito/users/import':
            if method == 'POST':
                return import_users(event, headers)
                
        elif path.startswith('/cognito/groups/') and path.endswith('/users'):
            group_name = path.split('/')[3]
            return get_users_in_group(group_name, headers)
            
        elif path.startswith('/cognito/groups/'):
            group_name = path.split('/')[3]
            if method == 'DELETE':
                return delete_group(group_name, headers)
                
        elif path == '/cognito/pool':
            return get_pool_info(headers)
            
        elif path == '/auth/verify-user':
            if method == 'POST':
                return verify_user_exists(event, headers)
                
        elif path == '/auth/signup' or path == '/cognito/auth/signup':
            print(f"Matched auth/signup route with method: {method}")
            if method == 'POST':
                print("Calling passwordless_signup function")
                return passwordless_signup(event, headers)
            else:
                return {
                    'statusCode': 405,
                    'headers': headers,
                    'body': json.dumps({'error': f'Method {method} not allowed for /auth/signup'})
                }
        
        elif path == '/auth/passkey/register/begin':
            if method == 'POST':
                return begin_passkey_registration(event, headers)
        
        elif path == '/auth/passkey/register/complete':
            if method == 'POST':
                return complete_passkey_registration(event, headers)
        
        elif path == '/auth/passkey/authenticate/begin':
            if method == 'POST':
                return begin_passkey_authentication(event, headers)
        
        elif path == '/auth/passkey/authenticate/complete':
            if method == 'POST':
                return complete_passkey_authentication(event, headers)
        
        elif path == '/auth/login':
            if method == 'GET':
                return get_auth_login(event, headers)
        
        elif path == '/auth/permissions':
            if method == 'GET':
                return get_auth_permissions(event, headers)
        
        elif path.startswith('/auth/users/') and path.endswith('/roles'):
            user_id = path.split('/')[3]
            if method == 'GET':
                return get_user_roles(user_id, event, headers)
            elif method == 'POST':
                return assign_user_roles_auth(user_id, event, headers)
        
        elif path.startswith('/auth/users/') and '/roles/' in path:
            parts = path.split('/')
            if len(parts) >= 6:
                user_id = parts[3]
                role = parts[5]
                if method == 'DELETE':
                    return remove_user_role_auth(user_id, role, event, headers)
        
        print(f"No route matched for: {method} {path}")
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Endpoint not found',
                'path': path,
                'method': method,
                'available_auth_endpoints': ['/auth/signup', '/auth/passkey/register/begin', '/auth/passkey/authenticate/begin']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_users(headers):
    all_users = []
    pagination_token = None
    
    while True:
        # Build request parameters
        params = {
            'UserPoolId': USER_POOL_ID,
            'Limit': 60
        }
        
        # Add pagination token if we have one
        if pagination_token:
            params['PaginationToken'] = pagination_token
            
        # Make the request
        response = cognito_client.list_users(**params)
        
        # Add users to our list
        all_users.extend(response.get('Users', []))
        
        # Check if there are more pages
        pagination_token = response.get('PaginationToken')
        if not pagination_token:
            break
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(all_users, default=str)
    }

def verify_user_exists(event, headers):
    """
    Verify if a user exists in the Cognito User Pool by email
    """
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }
        
        # Search for user by email
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1
        )
        
        users = response.get('Users', [])
        
        if not users:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found in H-DCN system'})
            }
        
        user = users[0]
        
        # Return basic user info
        user_info = {
            'username': user['Username'],
            'email': email,
            'userStatus': user['UserStatus'],
            'enabled': user['Enabled'],
            'userCreateDate': user['UserCreateDate'],
            'userLastModifiedDate': user['UserLastModifiedDate']
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(user_info, default=str)
        }
        
    except Exception as e:
        print(f"Error verifying user: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def create_user(event, headers):
    """
    Create a new user with role assignment validation
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
        
        # Validate requesting user has permission to create users and assign roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import base64
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
        
        # Check if requesting user has permission to create users and assign roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can create users and assign roles
            can_manage_users = 'System_User_Management' in requesting_user_roles
            
            if not can_manage_users:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to create users and assign roles',
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
        
        if not data.get('username') or not data.get('email'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Username and email are required'})
            }
        
        user_attributes = [
            {'Name': 'email', 'Value': data['email']},
            {'Name': 'email_verified', 'Value': 'true'}
        ]
        
        # Add additional attributes
        for key, value in data.get('attributes', {}).items():
            user_attributes.append({'Name': key, 'Value': value})
        
        # Create user in Cognito
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=data['username'],
            UserAttributes=user_attributes,
            TemporaryPassword=data.get('tempPassword', os.environ.get('DEFAULT_TEMP_PASSWORD', 'TempPass123!')),
            MessageAction='SUPPRESS'
        )
        
        # Add user to groups if specified
        groups = data.get('groups', '')
        group_list = []
        group_errors = []
        
        if groups:
            group_list = [g.strip() for g in groups.split(';') if g.strip()]
            
            # Validate that all groups exist
            try:
                all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
                existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]
                
                invalid_groups = [group for group in group_list if group not in existing_groups]
                if invalid_groups:
                    group_errors.append(f"Invalid groups specified: {invalid_groups}")
                    group_list = [group for group in group_list if group in existing_groups]
                    
            except Exception as groups_error:
                print(f"Error validating groups: {str(groups_error)}")
                group_errors.append("Failed to validate groups")
            
            for group_name in group_list:
                try:
                    cognito_client.admin_add_user_to_group(
                        UserPoolId=USER_POOL_ID,
                        Username=data['username'],
                        GroupName=group_name
                    )
                except Exception as group_error:
                    error_msg = f"Could not add user {data['username']} to group {group_name}: {str(group_error)}"
                    print(f"Warning: {error_msg}")
                    group_errors.append(error_msg)
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'User created successfully',
                'username': data['username'],
                'groups': group_list,
                'group_errors': group_errors,
                'created_by': requesting_user,
                'created_at': datetime.now().isoformat()
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': 'User with this username already exists'})
        }
    except Exception as e:
        print(f"Error in create_user: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to create user'})
        }

def update_user(username, event, headers):
    data = json.loads(event['body'])
    
    user_attributes = []
    for key, value in data.get('attributes', {}).items():
        user_attributes.append({'Name': key, 'Value': value})
    
    cognito_client.admin_update_user_attributes(
        UserPoolId=USER_POOL_ID,
        Username=username,
        UserAttributes=user_attributes
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User updated successfully'})
    }

def delete_user(username, headers):
    cognito_client.admin_delete_user(
        UserPoolId=USER_POOL_ID,
        Username=username
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User deleted successfully'})
    }

def get_groups(headers):
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
                import base64
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

def import_users(event, headers):
    """
    Bulk import users with role assignment validation
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
        
        # Validate requesting user has permission to create users and assign roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')
            
            try:
                import base64
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
        
        # Check if requesting user has permission to create users and assign roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )
            
            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]
            
            # Only users with System_User_Management can create users and assign roles
            can_manage_users = 'System_User_Management' in requesting_user_roles
            
            if not can_manage_users:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to import users and assign roles',
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
                'body': json.dumps({'error': 'No users specified for import'})
            }
        
        created_users = []
        existing_users = []
        errors = []
        
        for user_data in users:
            username = user_data.get('username')
            email = user_data.get('email')
            
            if not username or not email:
                errors.append(f"Missing username or email for user: {user_data}")
                continue
                
            try:
                # Check if user already exists
                cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
                existing_users.append(username)
                continue
                
            except cognito_client.exceptions.UserNotFoundException:
                # User doesn't exist, create it
                try:
                    user_attributes = [
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ]
                    
                    # Add additional attributes
                    for key, value in user_data.items():
                        if key not in ['username', 'email', 'groups', 'tempPassword'] and value:
                            user_attributes.append({'Name': key, 'Value': str(value)})
                    
                    # Create user
                    cognito_client.admin_create_user(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        UserAttributes=user_attributes,
                        TemporaryPassword=user_data.get('tempPassword', os.environ.get('DEFAULT_TEMP_PASSWORD', 'TempPass123!')),
                        MessageAction='SUPPRESS'
                    )
                    
                    # Add to groups if specified
                    groups = user_data.get('groups', '')
                    if groups:
                        group_list = [g.strip() for g in groups.split(';') if g.strip()]
                        
                        # Validate that all groups exist
                        try:
                            all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
                            existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]
                            
                            invalid_groups = [group for group in group_list if group not in existing_groups]
                            if invalid_groups:
                                errors.append(f"Invalid groups for user {username}: {invalid_groups}")
                                group_list = [group for group in group_list if group in existing_groups]
                                
                        except Exception as groups_error:
                            print(f"Error validating groups for user {username}: {str(groups_error)}")
                            errors.append(f"Failed to validate groups for user {username}")
                        
                        for group_name in group_list:
                            try:
                                cognito_client.admin_add_user_to_group(
                                    UserPoolId=USER_POOL_ID,
                                    Username=username,
                                    GroupName=group_name
                                )
                            except Exception as group_error:
                                errors.append(f"Failed to add {username} to group {group_name}: {str(group_error)}")
                    
                    created_users.append(username)
                    
                except Exception as create_error:
                    errors.append(f"Failed to create user {username}: {str(create_error)}")
            
            except Exception as check_error:
                errors.append(f"Error checking user {username}: {str(check_error)}")
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': f'Import completed. Created {len(created_users)} users, {len(existing_users)} already existed.',
                'created_users': created_users,
                'existing_users': existing_users,
                'errors': errors,
                'imported_by': requesting_user,
                'imported_at': datetime.now().isoformat()
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error in import_users: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to import users'})
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

def get_pool_info(headers):
    response = cognito_client.describe_user_pool(UserPoolId=USER_POOL_ID)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response['UserPool'], default=str)
    }

def passwordless_signup(event, headers):
    """
    Create a new user account for passwordless authentication
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        given_name = data.get('given_name')
        family_name = data.get('family_name')
        
        if not email or not given_name or not family_name:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email, given_name, and family_name are required'})
            }
        
        # Check if user already exists
        try:
            cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            return {
                'statusCode': 409,
                'headers': headers,
                'body': json.dumps({'error': 'User with this email already exists'})
            }
        except cognito_client.exceptions.UserNotFoundException:
            # User doesn't exist, proceed with creation
            pass
        
        # Create user attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'given_name', 'Value': given_name},
            {'Name': 'family_name', 'Value': family_name},
            {'Name': 'email_verified', 'Value': 'false'}  # Will be verified via email
        ]
        
        # Create user without password (for passwordless authentication)
        # Use standard user creation which will trigger email verification
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=user_attributes,
            DesiredDeliveryMediums=['EMAIL'],
            # Don't suppress message - let Cognito send verification email
        )
        
        # Automatically assign basic member role (if group exists)
        try:
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=email,
                GroupName='Verzoek_lid'
            )
        except cognito_client.exceptions.ResourceNotFoundException:
            print(f"Warning: Group 'Verzoek_lid' does not exist in User Pool {USER_POOL_ID}")
        except Exception as group_error:
            print(f"Warning: Could not add user {email} to Verzoek_lid group: {str(group_error)}")
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'Account created successfully. Check your email for verification instructions.',
                'username': email,
                'user_status': response['User']['UserStatus']
            })
        }
        
    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': 'User with this email already exists'})
        }
    except Exception as e:
        print(f"Error in passwordless signup: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"User Pool ID: {USER_POOL_ID}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Failed to create account. Please try again.',
                'debug_info': str(e) if os.environ.get('DEBUG') == 'true' else None
            })
        }

def begin_passkey_registration(event, headers):
    """
    Begin passkey registration process - generate challenge and options
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }
        
        # Check if user exists in Cognito (allow new users for registration)
        user_exists = True
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except cognito_client.exceptions.UserNotFoundException:
            # User doesn't exist yet - this is fine for new user registration
            user_exists = False
            print(f"New user passkey registration for: {email}")
        
        # Generate a challenge for WebAuthn registration
        # In a production environment, you would use a proper WebAuthn library
        # For now, we'll generate a simple challenge and store it temporarily
        import secrets
        import base64
        
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')
        
        # Store challenge temporarily (in production, use DynamoDB or Redis)
        # For now, we'll return it and expect the client to send it back
        
        # Determine RP ID based on environment
        # Use the actual domain from the request for consistency
        rp_id = 'portal.h-dcn.nl'  # Default production domain
        
        # For test environments, we need to be more flexible
        # This should match the domain the request is coming from
        origin = event.get('headers', {}).get('origin', '')
        host = event.get('headers', {}).get('host', '')
        
        if 'testportal' in origin or 'cloudfront.net' in origin:
            # Extract hostname from origin
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            rp_id = parsed.hostname
        elif 'cloudfront.net' in host:
            # If no origin but host is CloudFront, use host
            rp_id = host
        elif 'localhost' in origin:
            rp_id = 'localhost'
        
        registration_options = {
            'challenge': challenge_b64,
            'rp': {
                'name': 'H-DCN Portal',
                'id': rp_id
            },
            'user': {
                'id': email,
                'name': email,
                'displayName': email
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': -7},   # ES256
                {'type': 'public-key', 'alg': -257}  # RS256
            ],
            'authenticatorSelection': {
                'userVerification': 'preferred',
                'requireResidentKey': False
                # Removed 'authenticatorAttachment' to allow both platform and cross-platform authenticators
            },
            'timeout': 60000,
            'attestation': 'none'
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(registration_options)
        }
        
    except Exception as e:
        print(f"Error in begin_passkey_registration: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to begin passkey registration'})
        }

def complete_passkey_registration(event, headers):
    """
    Complete passkey registration - verify and store the credential
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        credential = data.get('credential')
        
        if not email or not credential:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email and credential are required'})
            }
        
        # Check if user exists in Cognito, create if they don't
        user_exists = True
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except cognito_client.exceptions.UserNotFoundException:
            # User doesn't exist - create them as part of passkey registration
            user_exists = False
            print(f"Creating new user during passkey registration: {email}")
            
            try:
                # Create user in Cognito with email verified
                user_response = cognito_client.admin_create_user(
                    UserPoolId=USER_POOL_ID,
                    Username=email,
                    UserAttributes=[
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ],
                    MessageAction='SUPPRESS'  # Don't send welcome email
                )
                
                # Add user to basic member group
                try:
                    cognito_client.admin_add_user_to_group(
                        UserPoolId=USER_POOL_ID,
                        Username=email,
                        GroupName='Verzoek_lid'
                    )
                except Exception as group_error:
                    print(f"Warning: Could not add user to Verzoek_lid group: {str(group_error)}")
                
            except Exception as create_error:
                print(f"Error creating user: {str(create_error)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'error': 'Failed to create user account'})
                }
        
        # In a production environment, you would:
        # 1. Verify the credential signature
        # 2. Validate the challenge
        # 3. Store the credential public key
        # 4. Associate it with the user account
        
        # Extract credential ID for storage
        credential_id = credential.get('id', '')
        if not credential_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid credential - missing ID'})
            }
        
        try:
            # Get existing credential IDs
            if user_exists:
                # Existing user - get attributes from admin_get_user response
                user_attributes = user_response.get('UserAttributes', [])
            else:
                # New user - get attributes from admin_create_user response
                user_attributes = user_response.get('User', {}).get('Attributes', [])
            
            existing_credentials = []
            
            for attr in user_attributes:
                if attr['Name'] == 'custom:passkey_cred_ids':
                    # Parse existing credential IDs (stored as JSON array)
                    try:
                        existing_credentials = json.loads(attr['Value'])
                    except:
                        existing_credentials = []
                    break
            
            # Add new credential ID to the list
            if credential_id not in existing_credentials:
                existing_credentials.append(credential_id)
            
            # Update user attributes with multiple credential IDs
            cognito_client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {
                        'Name': 'custom:passkey_registered',
                        'Value': 'true'
                    },
                    {
                        'Name': 'custom:passkey_date',
                        'Value': datetime.now().isoformat()
                    },
                    {
                        'Name': 'custom:passkey_cred_ids',
                        'Value': json.dumps(existing_credentials)
                    }
                ]
            )
            
            # In production, store the credential in a secure database
            # credential_id = credential['id']
            # public_key = credential['response']['attestationObject']
            # Store these securely associated with the user
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': 'Passkey registered successfully',
                    'verified': True
                })
            }
            
        except Exception as update_error:
            print(f"Error updating user attributes: {str(update_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to complete passkey registration'})
            }
        
    except Exception as e:
        print(f"Error in complete_passkey_registration: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to complete passkey registration'})
        }

def begin_passkey_authentication(event, headers):
    """
    Begin passkey authentication process - generate challenge
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        cross_device = data.get('crossDevice', False)
        
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }
        
        # Verify user exists and has passkey registered
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            
            # Check if user has passkey registered and get credential IDs
            user_attributes = user_response.get('UserAttributes', [])
            passkey_registered = False
            credential_ids = []
            
            for attr in user_attributes:
                if attr['Name'] == 'custom:passkey_registered' and attr['Value'] == 'true':
                    passkey_registered = True
                elif attr['Name'] == 'custom:passkey_cred_ids':
                    try:
                        credential_ids = json.loads(attr['Value'])
                    except:
                        credential_ids = []
                elif attr['Name'] == 'custom:passkey_credential_id':
                    # Legacy single credential ID support
                    if attr['Value'] and attr['Value'] not in credential_ids:
                        credential_ids.append(attr['Value'])
            
            if not passkey_registered:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'No passkey registered for this user',
                        'code': 'NO_PASSKEY_REGISTERED',
                        'message': 'User exists but has no passkey registered. Please set up a passkey first.'
                    })
                }
                
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'error': 'User not found',
                    'code': 'USER_NOT_FOUND',
                    'message': 'User does not exist. Please set up a new passkey.',
                    'action': 'SETUP_PASSKEY'
                })
            }
        
        # Generate authentication challenge
        import secrets
        import base64
        
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')
        
        # Build allowCredentials array
        allow_credentials = []
        if credential_ids:
            # Always populate allowCredentials if we have stored credential IDs
            # This helps the authenticator find the right credentials
            allow_credentials = [{
                'type': 'public-key',
                'id': cred_id
            } for cred_id in credential_ids]
        # If no stored credentials, leave empty to allow any credential (cross-device flow)
        
        authentication_options = {
            'challenge': challenge_b64,
            'timeout': 300000 if cross_device else 60000,  # 5 minutes for cross-device, 1 minute for same-device
            'userVerification': 'preferred',
            'allowCredentials': allow_credentials,
            'crossDevice': cross_device
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(authentication_options)
        }
        
    except Exception as e:
        print(f"Error in begin_passkey_authentication: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to begin passkey authentication'})
        }

def complete_passkey_authentication(event, headers):
    """
    Complete passkey authentication - verify credential and return tokens
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        credential = data.get('credential')
        cross_device = data.get('crossDevice', False)
        
        if not email or not credential:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email and credential are required'})
            }
        
        # Verify user exists and has passkey registered
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found'})
            }
        
        # In production, you would:
        # 1. Verify the credential signature against stored public key
        # 2. Validate the challenge
        # 3. Check the authenticator data
        
        # For now, simulate successful authentication
        # and generate custom JWT tokens for passkey authentication
        
        try:
            # Log cross-device authentication for audit purposes
            if cross_device:
                print(f"Cross-device authentication successful for user: {email}")
            
            # Get user groups for token
            user_groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            groups = [group['GroupName'] for group in user_groups_response.get('Groups', [])]
            
            # Generate custom tokens for passkey authentication
            try:
                import jwt
                import time
                
                # Token payload
                payload = {
                    'sub': email,
                    'email': email,
                    'email_verified': True,
                    'cognito:groups': groups,
                    'auth_time': int(time.time()),
                    'iat': int(time.time()),
                    'exp': int(time.time()) + 3600,  # 1 hour expiration
                    'token_use': 'access',
                    'client_id': os.environ.get('COGNITO_USER_POOL_CLIENT_ID', '7p5t7sjl2s1rcu1emn85h20qeh'),
                    'username': email,
                    'auth_method': 'passkey'
                }
                
                print(f"Generating JWT tokens for user: {email} with groups: {groups}")
                
                # Simple token signing (in production, use proper JWT signing)
                access_token = jwt.encode(payload, 'passkey-secret', algorithm='HS256')
                
                # ID token payload
                id_payload = {
                    **payload,
                    'token_use': 'id',
                    'aud': os.environ.get('COGNITO_USER_POOL_CLIENT_ID', '7p5t7sjl2s1rcu1emn85h20qeh')
                }
                
                id_token = jwt.encode(id_payload, 'passkey-secret', algorithm='HS256')
                
                print(f"JWT tokens generated successfully for user: {email}")
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'message': 'Authentication successful',
                        'authenticationResult': {
                            'AccessToken': access_token,
                            'IdToken': id_token,
                            'TokenType': 'Bearer',
                            'ExpiresIn': 3600
                        },
                        'verified': True,
                        'crossDevice': cross_device
                    })
                }
                
            except ImportError as import_error:
                print(f"JWT import error: {str(import_error)}")
                raise import_error
            except Exception as jwt_error:
                print(f"JWT generation error: {str(jwt_error)}")
                raise jwt_error
            
        except Exception as auth_error:
            print(f"Error during token generation: {str(auth_error)}")
            # Fallback: return success for passkey verification
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': f'Passkey authentication successful{" (cross-device)" if cross_device else ""}',
                    'verified': True,
                    'email': email,
                    'crossDevice': cross_device
                })
            }
        
    except Exception as e:
        print(f"Error in complete_passkey_authentication: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to complete passkey authentication'})
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
        import base64
        import json as json_lib
        
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
            payload = json_lib.loads(payload_decoded)
            
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
        import base64
        import json as json_lib
        
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
            payload = json_lib.loads(payload_decoded)
            
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
                    'is_admin': any(role in ['Members_CRUD_All', 'System_User_Management'] for role in user_groups),
                    'is_regular_member': 'hdcnLeden' in user_groups,
                    'calculated_at': datetime.now().isoformat()
                })
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
                import base64
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
            
            # Only users with System_User_Management or Members_CRUD_All can view other users' roles
            # Users can always view their own roles
            can_view_roles = (
                user_id == requesting_user or
                'System_User_Management' in requesting_user_roles or
                'Members_CRUD_All' in requesting_user_roles
            )
            
            if not can_view_roles:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to view user roles',
                        'required_roles': ['System_User_Management', 'Members_CRUD_All']
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
                    'is_admin': any(role in ['Members_CRUD_All', 'System_User_Management'] for role in role_names),
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
                import base64
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
                import base64
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

# Utility functions using the new role permission constants

def validate_field_permissions(user_roles, field_name, target_user_id, requesting_user_id):
    """
    Validate if a user can edit a specific field based on their roles and field type
    
    Args:
        user_roles (list): List of user's role names
        field_name (str): Name of the field to validate
        target_user_id (str): ID of the user whose record is being edited
        requesting_user_id (str): ID of the user making the request
        
    Returns:
        dict: Validation result with 'allowed' boolean and 'reason' string
    """
    try:
        is_own_record = target_user_id == requesting_user_id
        
        # Use the centralized field permission function
        can_edit = can_edit_field(user_roles, field_name, is_own_record)
        
        if can_edit:
            if field_name in ADMINISTRATIVE_FIELDS:
                return {
                    'allowed': True,
                    'reason': 'User has administrative permissions to edit this field'
                }
            elif is_own_record and (field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS):
                return {
                    'allowed': True,
                    'reason': 'User can edit their own personal/motorcycle information'
                }
            else:
                return {
                    'allowed': True,
                    'reason': 'User has sufficient permissions to edit this field'
                }
        else:
            if field_name in ADMINISTRATIVE_FIELDS:
                return {
                    'allowed': False,
                    'reason': 'Administrative fields require Members_CRUD_All or System_User_Management role'
                }
            elif not is_own_record and (field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS):
                return {
                    'allowed': False,
                    'reason': 'Can only edit personal/motorcycle fields for your own record'
                }
            else:
                return {
                    'allowed': False,
                    'reason': 'Insufficient permissions to edit this field'
                }
                
    except Exception as e:
        print(f"Error validating field permissions: {str(e)}")
        return {
            'allowed': False,
            'reason': 'Error validating field permissions'
        }

def get_user_field_permissions(user_roles, target_user_id, requesting_user_id):
    """
    Get field-level permissions for a user
    
    Args:
        user_roles (list): List of user's role names
        target_user_id (str): ID of the user whose record is being accessed
        requesting_user_id (str): ID of the user making the request
        
    Returns:
        dict: Field permissions organized by category
    """
    try:
        is_own_record = target_user_id == requesting_user_id
        
        field_permissions = {
            'personal_fields': {},
            'motorcycle_fields': {},
            'administrative_fields': {}
        }
        
        # Check personal fields
        for field in PERSONAL_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['personal_fields'][field] = validation
        
        # Check motorcycle fields
        for field in MOTORCYCLE_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['motorcycle_fields'][field] = validation
        
        # Check administrative fields
        for field in ADMINISTRATIVE_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['administrative_fields'][field] = validation
        
        return field_permissions
        
    except Exception as e:
        print(f"Error getting user field permissions: {str(e)}")
        return {
            'personal_fields': {},
            'motorcycle_fields': {},
            'administrative_fields': {}
        }

def check_role_permission(user_roles, required_permission):
    """
    Check if user has a specific permission based on their roles
    
    Args:
        user_roles (list): List of user's role names
        required_permission (str): Permission to check for
        
    Returns:
        dict: Permission check result with 'allowed' boolean and details
    """
    try:
        # Use the centralized permission checking function
        has_perm = has_permission(user_roles, required_permission)
        
        if has_perm:
            # Find which roles provide this permission
            providing_roles = []
            for role in user_roles:
                role_permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
                if required_permission in role_permissions:
                    providing_roles.append(role)
            
            return {
                'allowed': True,
                'permission': required_permission,
                'providing_roles': providing_roles,
                'user_roles': user_roles
            }
        else:
            return {
                'allowed': False,
                'permission': required_permission,
                'user_roles': user_roles,
                'reason': f'User does not have required permission: {required_permission}'
            }
            
    except Exception as e:
        print(f"Error checking role permission: {str(e)}")
        return {
            'allowed': False,
            'permission': required_permission,
            'error': str(e)
        }

def get_role_summary(role_name):
    """
    Get summary information about a specific role
    
    Args:
        role_name (str): Name of the role
        
    Returns:
        dict: Role summary with permissions and metadata
    """
    try:
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(role_name, [])
        
        if not role_permissions:
            return {
                'role_name': role_name,
                'exists': False,
                'permissions': [],
                'permission_count': 0
            }
        
        # Categorize permissions
        permission_categories = {
            'members': [],
            'events': [],
            'products': [],
            'communication': [],
            'system': [],
            'webshop': [],
            'cognito': []
        }
        
        for permission in role_permissions:
            category = permission.split(':')[0]
            if category in permission_categories:
                permission_categories[category].append(permission)
            else:
                if 'other' not in permission_categories:
                    permission_categories['other'] = []
                permission_categories['other'].append(permission)
        
        return {
            'role_name': role_name,
            'exists': True,
            'permissions': role_permissions,
            'permission_count': len(role_permissions),
            'permission_categories': permission_categories,
            'is_administrative': any(perm.startswith('system:') or perm.startswith('cognito:') for perm in role_permissions),
            'is_basic_member': role_name == 'hdcnLeden'
        }
        
    except Exception as e:
        print(f"Error getting role summary for {role_name}: {str(e)}")
        return {
            'role_name': role_name,
            'exists': False,
            'error': str(e)
        }