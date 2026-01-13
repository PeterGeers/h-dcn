#!/usr/bin/env python3
"""
Trigger a real request to match what the frontend is sending
"""

import requests
import json

def trigger_real_request():
    """Send a request that matches what the frontend is sending"""
    
    # Use a test JWT token for testing
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiY29nbml0bzpncm91cHMiOlsiaGRjbkxlZGVuIl0sImlzcyI6Imh0dHBzOi8vY29nbml0by1pZHAuZXUtd2VzdC0xLmFtYXpvbmF3cy5jb20vZXUtd2VzdC0xX1RBVDNPUENJBCJ9.test_signature"
    
    # Use the exact headers from the frontend logs
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Enhanced-Groups': '["hdcnLeden"]'
    }
    
    base_url = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
    
    print("🔍 Sending request with EXACT frontend headers and JWT token")
    print(f"JWT token length: {len(jwt_token)}")
    print(f"Headers: {list(headers.keys())}")
    print(f"X-Enhanced-Groups: {headers['X-Enhanced-Groups']}")
    
    try:
        response = requests.get(f"{base_url}/scan-product/", headers=headers, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: Found {len(data)} products")
        else:
            print(f"❌ FAILED: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    trigger_real_request()