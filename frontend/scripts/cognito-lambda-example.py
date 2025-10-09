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
    response = cognito_client.list_users(UserPoolId=USER_POOL_ID, Limit=60)
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response['Users'], default=str)
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
    
    response = cognito_client.admin_create_user(
        UserPoolId=USER_POOL_ID,
        Username=data['username'],
        UserAttributes=user_attributes,
        TemporaryPassword=data.get('tempPassword', 'TempPass123!'),
        MessageAction='SUPPRESS'
    )
    
    return {
        'statusCode': 201,
        'headers': headers,
        'body': json.dumps({'message': 'User created successfully', 'user': response['User']}, default=str)
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

def get_pool_info(headers):
    response = cognito_client.describe_user_pool(UserPoolId=USER_POOL_ID)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(response['UserPool'], default=str)
    }