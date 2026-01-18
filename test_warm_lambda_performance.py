#!/usr/bin/env python3
"""
Test warm Lambda performance for regional filtering API
"""

import requests
import json
import base64
import time

API_BASE_URL = "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev"
ENDPOINT = "/api/members"

def create_test_jwt(email, groups):
    """Create a test JWT token"""
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "sub": "test-user-id",
        "email": email,
        "cognito:groups": groups,
        "iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_OAT3oPCIm",
        "aud": "6unl8mg5tbv5r727vc39d847vn",
        "exp": 9999999999,
        "iat": 1600000000,
        "token_use": "access"
    }
    
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip('=')
    
    return f"{header_encoded}.{payload_encoded}.{signature}"

def test_performance(iterations=5):
    """Test performance with multiple requests to warm Lambda"""
    
    print(f"Testing warm Lambda performance ({iterations} iterations)...")
    print("=" * 60)
    
    jwt_token = create_test_jwt("test@hdcn.nl", ["Members_Read", "Regio_Utrecht"])
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}',
        'X-Enhanced-Groups': json.dumps(["Members_Read", "Regio_Utrecht"])
    }
    
    times = []
    
    for i in range(iterations):
        start = time.time()
        response = requests.get(f"{API_BASE_URL}{ENDPOINT}", headers=headers, timeout=30)
        elapsed = time.time() - start
        times.append(elapsed)
        
        status = "✅" if elapsed < 1.0 else "⚠️"
        print(f"Request {i+1}: {elapsed:.3f}s {status} (Status: {response.status_code})")
    
    print("=" * 60)
    print(f"Average: {sum(times)/len(times):.3f}s")
    print(f"Min: {min(times):.3f}s")
    print(f"Max: {max(times):.3f}s")
    print(f"Under 1s: {sum(1 for t in times if t < 1.0)}/{len(times)}")

if __name__ == "__main__":
    test_performance()
