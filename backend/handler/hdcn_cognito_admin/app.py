import json
import boto3
from datetime import datetime

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = 'eu-west-1_VtKQHhXGN'

def lambda_handler(event, context):
    method = event['httpMethod']
    path = event['path']
    
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
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
        
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Endpoint not found'})
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

def create_user(event, headers):
    data = json.loads(event['body'])
    
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
        TemporaryPassword=data.get('tempPassword', 'WelkomHDCN2024!'),
        MessageAction='SUPPRESS'
    )
    
    # Add user to groups if specified
    groups = data.get('groups', '')
    group_list = []
    if groups:
        group_list = [g.strip() for g in groups.split(';') if g.strip()]
        
        for group_name in group_list:
            try:
                cognito_client.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=data['username'],
                    GroupName=group_name
                )
            except Exception as group_error:
                print(f"Warning: Could not add user {data['username']} to group {group_name}: {str(group_error)}")
    
    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({
            'message': 'User created successfully',
            'username': data['username'],
            'groups': group_list
        })
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
    data = json.loads(event['body'])
    users = data.get('users', [])
    
    assigned_count = 0
    errors = []
    
    for user_data in users:
        username = user_data.get('username')
        groups = user_data.get('groups', '')
        
        if not username or not groups:
            continue
            
        group_list = [g.strip() for g in groups.split(';') if g.strip()]
        
        for group_name in group_list:
            try:
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
            'errors': errors
        })
    }

def import_users(event, headers):
    data = json.loads(event['body'])
    users = data.get('users', [])
    
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
                    TemporaryPassword=user_data.get('tempPassword', 'WelkomHDCN2024!'),
                    MessageAction='SUPPRESS'
                )
                
                # Add to groups if specified
                groups = user_data.get('groups', '')
                if groups:
                    group_list = [g.strip() for g in groups.split(';') if g.strip()]
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
            'errors': errors
        })
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