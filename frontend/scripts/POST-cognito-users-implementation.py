# POST /cognito/users endpoint implementation

def create_user(event, headers):
    """
    POST /cognito/users
    Creates a new Cognito user with attributes and group assignments
    """
    try:
        # Parse request body
        data = json.loads(event['body'])
        
        # Required fields validation
        username = data.get('username')
        email = data.get('email')
        temp_password = data.get('tempPassword', 'WelkomHDCN2024!')
        
        if not username or not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Username and email are required'})
            }
        
        # Prepare user attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true'}
        ]
        
        # Add optional attributes
        attributes = data.get('attributes', {})
        for key, value in attributes.items():
            if value:  # Only add non-empty values
                user_attributes.append({'Name': key, 'Value': str(value)})
        
        # Create user in Cognito
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
            UserAttributes=user_attributes,
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        # Add user to groups if specified
        groups = data.get('groups', '')
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
                    print(f"Warning: Could not add user {username} to group {group_name}: {str(group_error)}")
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'User created successfully',
                'username': username,
                'email': email,
                'groups': group_list if groups else []
            })
        }
        
    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': f'User {username} already exists'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to create user: {str(e)}'})
        }

# Add this to your main lambda_handler routing:
def lambda_handler(event, context):
    method = event['httpMethod']
    path = event['path']
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers}
    
    try:
        # Route for POST /cognito/users
        if path == '/cognito/users' and method == 'POST':
            return create_user(event, headers)
            
        # ... other routes ...
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

# Test payload example:
"""
POST /cognito/users
Content-Type: application/json

{
  "username": "test_user",
  "email": "test@h-dcn.nl",
  "tempPassword": "WelkomHDCN2024!",
  "attributes": {
    "given_name": "Test",
    "family_name": "User",
    "phone_number": "+31612345678"
  },
  "groups": "hdcnLeden;hdcnRegio_Utrecht"
}
"""