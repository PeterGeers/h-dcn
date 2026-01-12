#!/usr/bin/env python3
"""
Simple test to verify POST /members/me endpoint is working

This script tests if the POST method is supported and returns appropriate responses.
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"

def test_post_members_me():
    """Test POST /members/me endpoint"""
    
    print("TESTING POST /members/me ENDPOINT")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Test POST without authentication (should get 401 with CORS headers)
    print("🔍 Testing POST /members/me without authentication")
    print("-" * 50)
    
    try:
        url = f"{API_BASE_URL}/members/me"
        headers = {
            'Origin': 'https://de1irtdutlxqu.cloudfront.net',
            'Content-Type': 'application/json'
        }
        
        # Sample member data for testing
        test_data = {
            "voornaam": "Test",
            "achternaam": "User",
            "geboortedatum": "1990-01-01",
            "geslacht": "M",
            "telefoon": "0612345678",
            "straat": "Test Street 123",
            "postcode": "1234AB",
            "woonplaats": "Amsterdam",
            "lidmaatschap": "Gewoon lid",
            "regio": "Noord-Holland",
            "privacy": "Ja"
        }
        
        response = requests.post(url, headers=headers, json=test_data, timeout=10)
        
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
                
                # Analyze response
                if response.status_code == 401:
                    print("✅ Expected 401 unauthorized response (POST method supported)")
                elif response.status_code == 405:
                    print("❌ 405 Method Not Allowed - POST method not supported yet")
                elif response.status_code == 403:
                    print("⚠️ 403 Forbidden - POST method supported but needs proper authentication")
                elif response.status_code == 502:
                    print("❌ 502 Bad Gateway - Handler error")
                else:
                    print(f"⚠️ Unexpected response: {response.status_code}")
                    
            except json.JSONDecodeError:
                print(f"Response Body (raw): {response.text[:200]}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        if response.status_code == 401:
            print("✅ POST /members/me endpoint is deployed and working")
            print("✅ Returns 401 for unauthenticated requests (expected)")
            print("✅ Ready for authenticated testing")
        elif response.status_code == 405:
            print("❌ POST method not supported - needs deployment")
        elif response.status_code == 502:
            print("❌ Handler error - check CloudWatch logs")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
        
        print(f"CORS Headers: {'✅ PRESENT' if cors_complete else '❌ MISSING'}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'post_members_me_test_results_{timestamp}.json'
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': 'POST /members/me',
            'api_base_url': API_BASE_URL,
            'test_data': test_data,
            'response': {
                'status_code': response.status_code,
                'cors_complete': cors_complete,
                'cors_headers': cors_headers,
                'response_body': response.text[:500] if response.text else None
            },
            'assessment': {
                'post_method_supported': response.status_code != 405,
                'cors_working': cors_complete,
                'ready_for_auth_testing': response.status_code == 401
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        return response.status_code != 405
        
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_post_members_me()
    if success:
        print("\n🎉 POST method is supported!")
    else:
        print("\n❌ POST method needs to be deployed")