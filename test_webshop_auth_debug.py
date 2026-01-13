#!/usr/bin/env python3
"""
Test webshop authentication with debug logging
This will help us see exactly what's happening in the backend
"""

import requests
import json
import base64
import sys

def create_test_jwt():
    """Create a properly formatted test JWT token"""
    
    # JWT Header
    header = {
        "alg": "RS256",
        "typ": "JWT"
    }
    
    # JWT Payload (claims)
    payload = {
        "sub": "6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579",
        "email": "test@example.com",
        "cognito:groups": ["hdcnLeden"],
        "iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_OAT7oPCIl",
        "aud": "6unl8mg5tbv5r727vc39d847vn",
        "exp": 9999999999,  # Far future expiry
        "iat": 1600000000,
        "token_use": "access"
    }
    
    # Encode header and payload
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Create fake signature (for testing only - real JWT would have proper signature)
    signature = base64.urlsafe_b64encode(b"fake_signature_for_testing").decode().rstrip('=')
    
    # Combine parts
    jwt_token = f"{header_encoded}.{payload_encoded}.{signature}"
    
    return jwt_token

def test_webshop_endpoints():
    """Test webshop endpoints with test@example.com credentials"""
    
    # API base URL
    base_url = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
    
    # Create proper JWT token
    test_jwt = create_test_jwt()
    
    # Headers for API requests
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {test_jwt}',
        'X-Enhanced-Groups': json.dumps(['hdcnLeden']),
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    print("🔍 Testing webshop authentication with debug logging")
    print(f"📧 User: test@example.com")
    print(f"👥 Groups: ['hdcnLeden']")
    print(f"🌐 API Base: {base_url}")
    print(f"🔑 JWT Token (first 50 chars): {test_jwt[:50]}...")
    print("=" * 60)
    
    # Test 1: Scan Products (GET /scan-product/)
    print("\n🛍️ Test 1: Scan Products")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/scan-product/", headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Found {len(data)} products")
            if data:
                print(f"Sample product: {data[0].get('naam', 'Unknown')}")
        else:
            print(f"❌ FAILED: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test 2: Create Cart (POST /carts)
    print("\n🛒 Test 2: Create Cart")
    print("-" * 30)
    try:
        cart_data = {
            "customer_id": "6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579"  # Peter's member_id
        }
        
        response = requests.post(f"{base_url}/carts", 
                               headers=headers, 
                               json=cart_data, 
                               timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ SUCCESS: Cart created with ID: {data.get('cart_id', 'Unknown')}")
        else:
            print(f"❌ FAILED: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🔍 Check CloudWatch logs for detailed debug information:")
    print("   - /aws/lambda/webshop-backend-dev-scanProductFunction-*")
    print("   - /aws/lambda/webshop-backend-dev-CreateCartFunction-*")
    print("   - Look for FIX_2026_01_13_001 in the logs")

if __name__ == "__main__":
    test_webshop_endpoints()