#!/usr/bin/env python3
"""
Test webshop endpoints to trigger new logs with enhanced JWT debugging
"""

import requests
import json

def test_webshop_endpoints():
    """
    Test webshop endpoints to trigger new logs
    """
    print("🔍 Testing webshop endpoints to trigger new logs...")
    print("=" * 60)
    
    # Test JWT token for testing (sanitized)
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImNvZ25pdG86Z3JvdXBzIjpbImhkY25MZWRlbiJdLCJhdXRoX3RpbWUiOjE3NjgzMDE0OTIsImlhdCI6MTc2ODMwMTQ5MiwiZXhwIjoxNzY4MzA1MDkyLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJjbGllbnRfaWQiOiJ0ZXN0X2NsaWVudCIsInVzZXJuYW1lIjoidGVzdEBleGFtcGxlLmNvbSIsImF1dGhfbWV0aG9kIjoicGFzc2tleSJ9.test_signature"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Enhanced-Groups': '["hdcnLeden"]'
    }
    
    base_url = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
    
    # Test scan-product endpoint
    print("📦 Testing scan-product endpoint...")
    try:
        response = requests.get(f"{base_url}/scan-product/", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Success!")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    print()
    
    # Test create cart endpoint
    print("🛒 Testing create cart endpoint...")
    try:
        cart_data = {
            "member_id": "6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579",
            "items": []
        }
        response = requests.post(f"{base_url}/carts", headers=headers, json=cart_data, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 201]:
            print("   ✅ Success!")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    print()
    print("🔍 Check CloudWatch logs now for detailed JWT token debugging...")

if __name__ == "__main__":
    test_webshop_endpoints()