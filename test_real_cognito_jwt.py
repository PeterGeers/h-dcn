#!/usr/bin/env python3
"""
Test with a more realistic Cognito JWT token structure
"""

import requests
import json
import base64
import sys

def create_realistic_cognito_jwt():
    """Create a JWT token that matches real Cognito structure more closely"""
    
    # JWT Header (typical Cognito)
    header = {
        "kid": "test-key-id",
        "alg": "RS256"
    }
    
    # JWT Payload (more realistic Cognito structure)
    payload = {
        "sub": "6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579",
        "aud": "6unl8mg5tbv5r727vc39d847vn",
        "cognito:groups": ["hdcnLeden"],
        "email_verified": True,
        "iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_OAT7oPCIl",
        "cognito:username": "test@example.com",
        "given_name": "",
        "family_name": "",
        "aud": "6unl8mg5tbv5r727vc39d847vn",
        "event_id": "test-event-id",
        "token_use": "access",
        "auth_time": 1600000000,
        "exp": 9999999999,
        "iat": 1600000000,
        "jti": "test-jti",
        "email": "test@example.com"
    }
    
    # Encode using base64url (like real JWT)
    def base64url_encode(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
    
    header_encoded = base64url_encode(header)
    payload_encoded = base64url_encode(payload)
    
    # Create fake signature
    signature = base64.urlsafe_b64encode(b"fake_signature_for_testing").decode().rstrip('=')
    
    # Combine parts
    jwt_token = f"{header_encoded}.{payload_encoded}.{signature}"
    
    return jwt_token

def test_with_realistic_jwt():
    """Test with more realistic Cognito JWT structure"""
    
    base_url = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
    
    # Create realistic JWT
    test_jwt = create_realistic_cognito_jwt()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {test_jwt}',
        'X-Enhanced-Groups': json.dumps(['hdcnLeden']),
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    print("🔍 Testing with realistic Cognito JWT structure")
    print(f"🔑 JWT Token (first 50 chars): {test_jwt[:50]}...")
    print("=" * 60)
    
    # Test scan products
    print("\n🛍️ Test: Scan Products")
    print("-" * 30)
    try:
        response = requests.get(f"{base_url}/scan-product/", headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Found {len(data)} products")
        else:
            print(f"❌ FAILED: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

def test_jwt_decoding_issue():
    """Test if there's a JWT decoding issue in our backend"""
    
    print("\n🔍 Testing JWT decoding compatibility")
    print("=" * 50)
    
    # Test different JWT encoding scenarios
    test_cases = [
        {
            "name": "Standard base64url (correct)",
            "payload": {"email": "test@example.com", "cognito:groups": ["hdcnLeden"]},
            "encoding": "base64url"
        },
        {
            "name": "Standard base64 (incorrect but common mistake)",
            "payload": {"email": "test@example.com", "cognito:groups": ["hdcnLeden"]},
            "encoding": "base64"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 Test case: {test_case['name']}")
        
        # Create header
        header = {"alg": "RS256", "typ": "JWT"}
        
        if test_case['encoding'] == 'base64url':
            # Correct JWT encoding
            header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
            payload_encoded = base64.urlsafe_b64encode(json.dumps(test_case['payload']).encode()).decode().rstrip('=')
        else:
            # Standard base64 (wrong for JWT)
            header_encoded = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
            payload_encoded = base64.b64encode(json.dumps(test_case['payload']).encode()).decode().rstrip('=')
        
        signature = "fake_sig"
        jwt_token = f"{header_encoded}.{payload_encoded}.{signature}"
        
        # Test decoding (simulate what our backend does)
        try:
            parts = jwt_token.split('.')
            if len(parts) == 3:
                # Add padding if needed
                payload_part = parts[1]
                payload_part += '=' * (4 - len(payload_part) % 4)
                
                # Try to decode
                decoded = base64.urlsafe_b64decode(payload_part)
                parsed = json.loads(decoded)
                
                print(f"   ✅ Decoding successful: {parsed}")
            else:
                print(f"   ❌ Invalid JWT format")
                
        except Exception as e:
            print(f"   ❌ Decoding failed: {str(e)}")

if __name__ == "__main__":
    test_jwt_decoding_issue()
    test_with_realistic_jwt()