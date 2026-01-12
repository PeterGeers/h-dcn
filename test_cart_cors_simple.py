#!/usr/bin/env python3
"""
Simple Cart CORS Test

This script performs a focused test on cart CORS headers to verify the fix.
It tests both successful and error responses to ensure CORS headers are present.
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"

def test_cors_headers(url, method='GET', headers=None, data=None):
    """Test CORS headers for a specific endpoint"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {method} {url}")
    print(f"{'='*60}")
    
    try:
        # Add origin header to trigger CORS
        test_headers = {
            'Origin': 'https://de1irtdutlxqu.cloudfront.net',
            'Content-Type': 'application/json'
        }
        if headers:
            test_headers.update(headers)
        
        # Make request
        if method == 'OPTIONS':
            response = requests.options(url, headers=test_headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=test_headers, json=data, timeout=10)
        elif method == 'GET':
            response = requests.get(url, headers=test_headers, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, headers=test_headers, json=data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=test_headers, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
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
        
        # Check if all required CORS headers are present
        cors_complete = all(value != 'MISSING' for value in cors_headers.values())
        
        print(f"\nCORS Status: {'✅ COMPLETE' if cors_complete else '❌ INCOMPLETE'}")
        
        # Show response body (truncated)
        if response.text:
            body = response.text[:200] + "..." if len(response.text) > 200 else response.text
            print(f"Response Body: {body}")
        
        return cors_complete
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    """Run CORS tests for cart operations"""
    
    print("CART OPERATIONS CORS VERIFICATION")
    print("=" * 80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    
    results = []
    
    # Test 1: OPTIONS request for CORS preflight
    print("\n🔍 Testing CORS Preflight (OPTIONS)")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/carts", method='OPTIONS')
    results.append(('OPTIONS /carts', cors_ok))
    
    # Test 2: POST request (create cart) - expect 401 without auth
    print("\n🔍 Testing Create Cart (POST) - Unauthorized")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/carts", method='POST', 
                               data={'customer_id': 'test-customer'})
    results.append(('POST /carts (no auth)', cors_ok))
    
    # Test 3: GET request (get cart) - expect 401 without auth
    print("\n🔍 Testing Get Cart (GET) - Unauthorized")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/carts/test-cart-id", method='GET')
    results.append(('GET /carts/test-cart-id (no auth)', cors_ok))
    
    # Test 4: PUT request (update cart) - expect 401 without auth
    print("\n🔍 Testing Update Cart (PUT) - Unauthorized")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/carts/test-cart-id/items", method='PUT',
                               data={'items': [], 'total_amount': 0})
    results.append(('PUT /carts/test-cart-id/items (no auth)', cors_ok))
    
    # Test 5: DELETE request (clear cart) - expect 401 without auth
    print("\n🔍 Testing Clear Cart (DELETE) - Unauthorized")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/carts/test-cart-id", method='DELETE')
    results.append(('DELETE /carts/test-cart-id (no auth)', cors_ok))
    
    # Test 6: Test with invalid endpoint to check 404 CORS
    print("\n🔍 Testing Invalid Endpoint (404) - CORS Check")
    cors_ok = test_cors_headers(f"{API_BASE_URL}/invalid-endpoint", method='GET')
    results.append(('GET /invalid-endpoint (404)', cors_ok))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    print(f"Total Tests: {total_tests}")
    print(f"CORS Complete: {passed_tests}")
    print(f"CORS Incomplete: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results:
        status = "✅ CORS OK" if success else "❌ CORS MISSING"
        print(f"  {status} | {test_name}")
    
    # Assessment
    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    
    if passed_tests == total_tests:
        print("✅ CORS FIX STATUS: SUCCESS")
        print("   All cart operations return proper CORS headers")
        print("   Frontend should be able to make cart requests without CORS errors")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  CORS FIX STATUS: MOSTLY WORKING")
        print("   Most cart operations return CORS headers")
        print("   Some endpoints may still cause CORS issues")
    else:
        print("❌ CORS FIX STATUS: NEEDS ATTENTION")
        print("   Many cart operations missing CORS headers")
        print("   Frontend will likely encounter CORS errors")
    
    print("\nRecommendations:")
    if passed_tests < total_tests:
        print("- Check API Gateway CORS configuration")
        print("- Verify Lambda function deployment status")
        print("- Review error handling in backend handlers")
        print("- Test with actual authentication tokens")
    else:
        print("- CORS headers are working correctly")
        print("- Test cart operations with authenticated user")
        print("- Monitor cart functionality in production")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'cart_cors_test_results_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'api_base_url': API_BASE_URL,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': (passed_tests / total_tests) * 100,
            'test_results': [{'test': name, 'cors_complete': success} for name, success in results]
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    main()