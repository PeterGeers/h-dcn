#!/usr/bin/env python3
"""
Simple test to verify permission checking logic
"""

import json
import base64
import sys
import os

# Add the handler directory to Python path
handler_dir = os.path.join(os.path.dirname(__file__), 'handler', 'generate_member_parquet')
sys.path.insert(0, handler_dir)

def create_mock_jwt_token(email: str, groups: list) -> str:
    """Create a mock JWT token for testing"""
    payload = {
        'email': email,
        'cognito:groups': groups,
    }
    
    payload_json = json.dumps(payload)
    payload_encoded = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
    
    header = base64.urlsafe_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
    signature = 'mock_signature'
    
    return f"{header}.{payload_encoded}.{signature}"

def test_permission_check():
    """Test the permission checking logic directly"""
    
    # Import the handler
    import app
    
    print("Testing permission check logic...")
    
    # Test case 1: Members_CRUD + Regio_Utrecht (should fail - regional access not allowed)
    print("\n🧪 Test 1: Members_CRUD + Regio_Utrecht")
    
    jwt_token = create_mock_jwt_token("test@hdcn.nl", ["Members_CRUD", "Regio_Utrecht"])
    
    event = {
        'httpMethod': 'POST',
        'headers': {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'options': {}})
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = 'test'
            self.aws_request_id = 'test'
    
    context = MockContext()
    
    # Call the handler
    response = app.lambda_handler(event, context)
    
    print(f"Status Code: {response.get('statusCode')}")
    print(f"Response Body: {response.get('body')}")
    
    # Test case 2: Members_CRUD + Regio_All (should succeed until pandas check)
    print("\n🧪 Test 2: Members_CRUD + Regio_All")
    
    jwt_token = create_mock_jwt_token("test@hdcn.nl", ["Members_CRUD", "Regio_All"])
    
    event = {
        'httpMethod': 'POST',
        'headers': {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'options': {}})
    }
    
    response = app.lambda_handler(event, context)
    
    print(f"Status Code: {response.get('statusCode')}")
    print(f"Response Body: {response.get('body')}")
    
    # Test case 3: Members_CRUD + Multiple regions (should fail)
    print("\n🧪 Test 3: Members_CRUD + Multiple Regions")
    
    jwt_token = create_mock_jwt_token("test@hdcn.nl", ["Members_CRUD", "Regio_Utrecht", "Regio_Limburg"])
    
    event = {
        'httpMethod': 'POST',
        'headers': {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'options': {}})
    }
    
    response = app.lambda_handler(event, context)
    
    print(f"Status Code: {response.get('statusCode')}")
    print(f"Response Body: {response.get('body')}")

if __name__ == "__main__":
    test_permission_check()