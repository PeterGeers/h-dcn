#!/usr/bin/env python3
"""
Test the deployed /members/me endpoint directly
"""

import requests
import json

def test_deployed_endpoint():
    """Test the actual deployed endpoint"""
    
    print("=" * 60)
    print("Testing deployed /members/me endpoint")
    print("=" * 60)
    
    # API Gateway URL
    base_url = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
    endpoint = f"{base_url}/members/me"
    
    # Sample JWT token (you'll need to get a real one from the frontend)
    # This is just to test the endpoint structure
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJjb2duaXRvOmdyb3VwcyI6WyJoZGNuTGVkZW4iXX0.test_signature',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Enhanced-Groups': '["hdcnLeden"]'
    }
    
    try:
        print(f"🔗 Testing endpoint: {endpoint}")
        print(f"📋 Headers: {json.dumps(headers, indent=2)}")
        
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_deployed_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Deployed endpoint is working!")
    else:
        print("❌ Deployed endpoint has issues")
    print("=" * 60)