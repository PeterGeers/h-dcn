"""
Test script to call /api/members endpoint and see the backend response
"""
import requests
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev"
ENDPOINT = "/api/members"

# Get JWT token from user (you'll need to paste this)
print("=" * 60)
print("TEST: /api/members endpoint")
print("=" * 60)
print()
print("Please provide your JWT token from the browser:")
print("1. Open DevTools (F12)")
print("2. Go to Console tab")
print("3. Run: localStorage.getItem('hdcn_auth_tokens')")
print("4. Copy the 'AccessToken' value")
print()

jwt_token = input("Paste JWT token here: ").strip()

if not jwt_token:
    print("ERROR: No token provided")
    exit(1)

# Make request
url = f"{API_BASE_URL}{ENDPOINT}"
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json"
}

print()
print(f"Making request to: {url}")
print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
print()

try:
    response = requests.get(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2, default=str))
        print()
        
        if 'metadata' in data:
            print("Metadata:")
            print(f"  Total Count: {data['metadata'].get('total_count')}")
            print(f"  Region: '{data['metadata'].get('region')}'")
            print(f"  Timestamp: {data['metadata'].get('timestamp')}")
        
        if 'data' in data:
            print(f"\nData: {len(data['data'])} members returned")
            if len(data['data']) > 0:
                print(f"First member: {data['data'][0].get('lidnummer')} - {data['data'][0].get('voornaam')} {data['data'][0].get('achternaam')}")
    else:
        print("Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
