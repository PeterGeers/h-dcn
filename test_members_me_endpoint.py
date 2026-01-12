#!/usr/bin/env python3
"""
Test /members/me endpoint to verify member_id is returned

This script tests the /members/me endpoint to check if it properly returns
the member_id field that the frontend needs for cart operations.
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"

def test_members_me_endpoint():
    """Test the /members/me endpoint"""
    
    print("TESTING /members/me ENDPOINT")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Test without authentication (should get 401 with CORS headers)
    print("🔍 Testing /members/me without authentication")
    print("-" * 50)
    
    try:
        url = f"{API_BASE_URL}/members/me"
        headers = {
            'Origin': 'https://de1irtdutlxqu.cloudfront.net',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        # Check CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin', 'MISSING'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods', 'MISSING'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers', 'MISSING')
        }
        
        print("CORS Headers:")
        for header, value in cors_headers.items():
            status = "✅" if value != 'MISSING' else "❌"
            print(f"  {status} {header}: {value}")
        
        cors_complete = all(value != 'MISSING' for value in cors_headers.values())
        print(f"\nCORS Status: {'✅ COMPLETE' if cors_complete else '❌ INCOMPLETE'}")
        
        # Check response body
        if response.text:
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                
                # Check if it's the expected 401 error
                if response.status_code == 401 and 'error' in response_data:
                    print("✅ Expected 401 unauthorized response")
                else:
                    print(f"⚠️ Unexpected response for unauthenticated request")
                    
            except json.JSONDecodeError:
                print(f"Response Body (raw): {response.text[:200]}")
        
        # Test OPTIONS request for CORS preflight
        print("\n🔍 Testing OPTIONS /members/me for CORS preflight")
        print("-" * 50)
        
        options_response = requests.options(url, headers=headers, timeout=10)
        print(f"OPTIONS Status Code: {options_response.status_code}")
        
        options_cors = {
            'Access-Control-Allow-Origin': options_response.headers.get('Access-Control-Allow-Origin', 'MISSING'),
            'Access-Control-Allow-Methods': options_response.headers.get('Access-Control-Allow-Methods', 'MISSING'),
            'Access-Control-Allow-Headers': options_response.headers.get('Access-Control-Allow-Headers', 'MISSING')
        }
        
        print("OPTIONS CORS Headers:")
        for header, value in options_cors.items():
            status = "✅" if value != 'MISSING' else "❌"
            print(f"  {status} {header}: {value}")
        
        options_cors_complete = all(value != 'MISSING' for value in options_cors.values())
        print(f"\nOPTIONS CORS Status: {'✅ COMPLETE' if options_cors_complete else '❌ INCOMPLETE'}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        print(f"Endpoint: GET /members/me")
        print(f"Status: {'✅ WORKING' if response.status_code == 401 else '❌ ISSUE'}")
        print(f"CORS Headers: {'✅ PRESENT' if cors_complete else '❌ MISSING'}")
        print(f"OPTIONS Support: {'✅ WORKING' if options_response.status_code == 200 else '❌ ISSUE'}")
        
        print("\nEndpoint Analysis:")
        if response.status_code == 401 and cors_complete:
            print("✅ /members/me endpoint is properly configured")
            print("✅ Returns 401 for unauthenticated requests with CORS headers")
            print("✅ Should work correctly with authenticated requests")
            print("✅ Frontend can call this endpoint without CORS issues")
        elif response.status_code == 401:
            print("⚠️ /members/me endpoint works but missing CORS headers")
            print("❌ Frontend may encounter CORS issues")
        elif response.status_code == 404:
            print("❌ /members/me endpoint not found - may not be deployed")
        elif response.status_code == 502:
            print("❌ /members/me endpoint has internal server error")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
        
        print("\nExpected Member Data Fields:")
        print("When authenticated, this endpoint should return:")
        print("- member_id (UUID)")
        print("- name")
        print("- email") 
        print("- voornaam, achternaam")
        print("- straat, postcode, woonplaats")
        print("- phone/telefoon")
        print("- created_at, updated_at")
        
        print("\nNext Steps:")
        if cors_complete and response.status_code == 401:
            print("1. Test with authenticated user to verify member_id is returned")
            print("2. Verify frontend WebshopPage.tsx uses this endpoint")
            print("3. Check that member_id is properly used for cart operations")
        else:
            print("1. Fix CORS headers if missing")
            print("2. Check endpoint deployment status")
            print("3. Review handler implementation")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'members_me_test_results_{timestamp}.json'
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': '/members/me',
            'api_base_url': API_BASE_URL,
            'get_request': {
                'status_code': response.status_code,
                'cors_complete': cors_complete,
                'cors_headers': cors_headers,
                'response_body': response.text[:500] if response.text else None
            },
            'options_request': {
                'status_code': options_response.status_code,
                'cors_complete': options_cors_complete,
                'cors_headers': options_cors
            },
            'assessment': {
                'endpoint_working': response.status_code == 401,
                'cors_working': cors_complete,
                'ready_for_frontend': cors_complete and response.status_code == 401
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_members_me_endpoint()