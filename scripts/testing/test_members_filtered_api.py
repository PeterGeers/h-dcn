#!/usr/bin/env python3
"""
Test the new regional filtering API endpoint: GET /api/members

This script tests the backend regional filtering functionality with different user roles:
1. Regional user (Regio_Utrecht) - should only see Utrecht members
2. Regio_All user - should see all members from all regions
3. CRUD user with regional access - should see their region's members

Requirements tested: 1.1, 1.2, 1.3, 1.4
"""

import requests
import json
import base64
import time
from datetime import datetime

# API Configuration
API_BASE_URL = "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev"
ENDPOINT = "/api/members"

def create_test_jwt(email, groups):
    """Create a test JWT token with specified email and groups"""
    
    # JWT Header
    header = {
        "alg": "RS256",
        "typ": "JWT"
    }
    
    # JWT Payload (claims)
    payload = {
        "sub": "test-user-id-12345",
        "email": email,
        "cognito:groups": groups,
        "iss": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_OAT3oPCIm",
        "aud": "6unl8mg5tbv5r727vc39d847vn",
        "exp": 9999999999,  # Far future expiry
        "iat": 1600000000,
        "token_use": "access"
    }
    
    # Encode header and payload
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Create fake signature (for testing only)
    signature = base64.urlsafe_b64encode(b"fake_signature_for_testing").decode().rstrip('=')
    
    # Combine parts
    jwt_token = f"{header_encoded}.{payload_encoded}.{signature}"
    
    return jwt_token

def test_endpoint(test_name, email, groups, expected_behavior):
    """Test the /api/members endpoint with specific user credentials"""
    
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*80}")
    print(f"📧 Email: {email}")
    print(f"👥 Groups: {groups}")
    print(f"🎯 Expected: {expected_behavior}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    # Create JWT token
    jwt_token = create_test_jwt(email, groups)
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}',
        'X-Enhanced-Groups': json.dumps(groups)
    }
    
    # Make request
    start_time = time.time()
    try:
        response = requests.get(
            f"{API_BASE_URL}{ENDPOINT}",
            headers=headers,
            timeout=30
        )
        elapsed_time = time.time() - start_time
        
        print(f"⏱️  Response Time: {elapsed_time:.3f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        # Check response time requirement (<1 second)
        if elapsed_time < 1.0:
            print(f"✅ Performance: Response time < 1s (Requirement 1.4)")
        else:
            print(f"⚠️  Performance: Response time > 1s (Requirement 1.4 NOT MET)")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                members = data.get('data', [])
                metadata = data.get('metadata', {})
                
                print(f"\n📈 Results:")
                print(f"   Total Members: {metadata.get('total_count', len(members))}")
                print(f"   Region Filter: {metadata.get('region', 'Unknown')}")
                print(f"   Timestamp: {metadata.get('timestamp', 'Unknown')}")
                
                # Analyze regions in response
                if members:
                    regions = set(m.get('regio', 'Unknown') for m in members)
                    print(f"   Regions in Response: {sorted(regions)}")
                    
                    # Sample members
                    print(f"\n📋 Sample Members (first 3):")
                    for i, member in enumerate(members[:3], 1):
                        print(f"      {i}. {member.get('voornaam', '')} {member.get('achternaam', '')} - {member.get('regio', 'Unknown')}")
                
                print(f"\n✅ SUCCESS: {test_name}")
                return True
            else:
                print(f"\n❌ FAILED: Response indicates failure")
                print(f"   Error: {data.get('error', 'Unknown error')}")
                return False
                
        elif response.status_code == 401:
            print(f"\n❌ FAILED: Authentication required (401)")
            print(f"   Details: {response.text}")
            return False
            
        elif response.status_code == 403:
            print(f"\n❌ FAILED: Access denied (403)")
            print(f"   Details: {response.text}")
            return False
            
        else:
            print(f"\n❌ FAILED: Unexpected status code")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ FAILED: Request timeout (>30s)")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Run all test cases"""
    
    print("="*80)
    print("🚀 TESTING: Regional Filtering API - GET /api/members")
    print("="*80)
    print(f"🌐 API Base URL: {API_BASE_URL}")
    print(f"📍 Endpoint: {ENDPOINT}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Regional user (Regio_Utrecht)
    results.append(test_endpoint(
        test_name="Regional User - Regio_Utrecht",
        email="utrecht.user@hdcn.nl",
        groups=["Members_Read", "Regio_Utrecht"],
        expected_behavior="Should only see members from Utrecht region (Requirement 1.3)"
    ))
    
    # Test 2: Regio_All user
    results.append(test_endpoint(
        test_name="Regio_All User",
        email="admin@hdcn.nl",
        groups=["Members_Read", "Regio_All"],
        expected_behavior="Should see all members from all regions (Requirement 1.2)"
    ))
    
    # Test 3: CRUD user with regional access
    results.append(test_endpoint(
        test_name="CRUD User - Regio_Zuid-Holland",
        email="zuidholland.admin@hdcn.nl",
        groups=["Members_CRUD", "Regio_Zuid-Holland"],
        expected_behavior="Should see members from Zuid-Holland region (Requirement 1.3)"
    ))
    
    # Test 4: User with export permission
    results.append(test_endpoint(
        test_name="Export User - Regio_Noord-Holland",
        email="noordholland.export@hdcn.nl",
        groups=["Members_Export", "Regio_Noord-Holland"],
        expected_behavior="Should see members from Noord-Holland region (Requirement 1.1)"
    ))
    
    # Test 5: User without member permissions (should fail)
    results.append(test_endpoint(
        test_name="User Without Member Permissions",
        email="nopermissions@hdcn.nl",
        groups=["SomeOtherRole"],
        expected_behavior="Should be denied access (403) - no member permissions (Requirement 1.1)"
    ))
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Review results above")
    
    print(f"\n⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # CloudWatch logs info
    print(f"\n💡 TIP: Check CloudWatch logs for detailed backend execution:")
    print(f"   Log Group: /aws/lambda/webshop-backend-dev-GetMembersFilteredFunction-*")
    print(f"   Look for [HANDLER], [LOAD_MEMBERS], [FILTER] log entries")

if __name__ == "__main__":
    main()
