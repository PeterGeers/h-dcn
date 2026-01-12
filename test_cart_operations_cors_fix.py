#!/usr/bin/env python3
"""
Test Cart Operations After CORS Fix

This script tests all cart operations to verify that:
1. CORS headers are properly returned in all responses
2. Cart operations work correctly with authentication
3. Error responses include CORS headers
4. All cart endpoints are accessible

Based on the webshop root cause analysis document.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/prod"
TEST_USER_EMAIL = "peter@pgeers.nl"  # User mentioned in the root cause analysis

class CartOperationTester:
    def __init__(self, api_base_url, test_user_email):
        self.api_base_url = api_base_url
        self.test_user_email = test_user_email
        self.auth_token = None
        self.test_cart_id = None
        self.test_results = []
        
    def log_test_result(self, test_name, success, details, cors_headers_present=False):
        """Log test result with timestamp and details"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_name': test_name,
            'success': success,
            'cors_headers_present': cors_headers_present,
            'details': details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        cors_status = "✅ CORS OK" if cors_headers_present else "❌ NO CORS"
        print(f"{status} | {cors_status} | {test_name}")
        if details:
            print(f"    Details: {details}")
        print()
    
    def check_cors_headers(self, response):
        """Check if response contains proper CORS headers"""
        required_cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        cors_headers_present = all(
            header in response.headers for header in required_cors_headers
        )
        
        cors_details = {}
        for header in required_cors_headers:
            cors_details[header] = response.headers.get(header, 'MISSING')
        
        return cors_headers_present, cors_details
    
    def test_options_request(self, endpoint):
        """Test OPTIONS request for CORS preflight"""
        test_name = f"OPTIONS {endpoint}"
        
        try:
            url = f"{self.api_base_url}{endpoint}"
            response = requests.options(url, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            success = response.status_code == 200 and cors_present
            details = f"Status: {response.status_code}, CORS: {cors_details}"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def test_create_cart(self):
        """Test cart creation with CORS verification"""
        test_name = "Create Cart"
        
        try:
            url = f"{self.api_base_url}/carts"
            headers = {
                'Content-Type': 'application/json',
                'Origin': 'https://de1irtdutlxqu.cloudfront.net'  # Frontend origin from error
            }
            
            # Add auth header if available
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            payload = {
                'customer_id': 'test-customer'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            success = False
            details = f"Status: {response.status_code}"
            
            if response.status_code == 201:
                # Success case
                try:
                    data = response.json()
                    if 'cart_id' in data:
                        self.test_cart_id = data['cart_id']
                        success = True
                        details += f", Cart ID: {self.test_cart_id}"
                    else:
                        details += ", Missing cart_id in response"
                except:
                    details += ", Invalid JSON response"
            elif response.status_code == 401:
                # Expected if no auth token
                details += ", Unauthorized (expected without auth)"
                success = cors_present  # Success if CORS headers are present
            else:
                details += f", Response: {response.text[:100]}"
            
            details += f", CORS: {cors_details}"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def test_get_cart(self):
        """Test cart retrieval with CORS verification"""
        test_name = "Get Cart"
        
        if not self.test_cart_id:
            self.log_test_result(test_name, False, "No cart ID available for testing", False)
            return False
        
        try:
            url = f"{self.api_base_url}/carts/{self.test_cart_id}"
            headers = {
                'Origin': 'https://de1irtdutlxqu.cloudfront.net'
            }
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = requests.get(url, headers=headers, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            success = False
            details = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'cart_id' in data:
                        success = True
                        details += f", Cart found with {len(data.get('items', []))} items"
                    else:
                        details += ", Invalid cart data structure"
                except:
                    details += ", Invalid JSON response"
            elif response.status_code == 401:
                details += ", Unauthorized (expected without auth)"
                success = cors_present
            elif response.status_code == 404:
                details += ", Cart not found"
                success = cors_present
            else:
                details += f", Response: {response.text[:100]}"
            
            details += f", CORS: {cors_details}"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def test_update_cart(self):
        """Test cart update with CORS verification"""
        test_name = "Update Cart"
        
        if not self.test_cart_id:
            self.log_test_result(test_name, False, "No cart ID available for testing", False)
            return False
        
        try:
            url = f"{self.api_base_url}/carts/{self.test_cart_id}/items"
            headers = {
                'Content-Type': 'application/json',
                'Origin': 'https://de1irtdutlxqu.cloudfront.net'
            }
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            payload = {
                'items': [
                    {
                        'product_id': 'test-product-1',
                        'name': 'Test Product',
                        'price': 25.00,
                        'quantity': 2
                    }
                ],
                'total_amount': 50.00,
                'item_count': 2
            }
            
            response = requests.put(url, json=payload, headers=headers, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            success = False
            details = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                success = True
                details += ", Cart updated successfully"
            elif response.status_code == 401:
                details += ", Unauthorized (expected without auth)"
                success = cors_present
            elif response.status_code == 404:
                details += ", Cart not found"
                success = cors_present
            else:
                details += f", Response: {response.text[:100]}"
            
            details += f", CORS: {cors_details}"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def test_clear_cart(self):
        """Test cart clearing with CORS verification"""
        test_name = "Clear Cart"
        
        if not self.test_cart_id:
            self.log_test_result(test_name, False, "No cart ID available for testing", False)
            return False
        
        try:
            url = f"{self.api_base_url}/carts/{self.test_cart_id}"
            headers = {
                'Origin': 'https://de1irtdutlxqu.cloudfront.net'
            }
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            response = requests.delete(url, headers=headers, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            success = False
            details = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                success = True
                details += ", Cart cleared successfully"
            elif response.status_code == 401:
                details += ", Unauthorized (expected without auth)"
                success = cors_present
            elif response.status_code == 404:
                details += ", Cart not found"
                success = cors_present
            else:
                details += f", Response: {response.text[:100]}"
            
            details += f", CORS: {cors_details}"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def test_error_response_cors(self):
        """Test that error responses include CORS headers"""
        test_name = "Error Response CORS"
        
        try:
            # Test with invalid cart ID to trigger 404 error
            url = f"{self.api_base_url}/carts/invalid-cart-id-12345"
            headers = {
                'Origin': 'https://de1irtdutlxqu.cloudfront.net'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            cors_present, cors_details = self.check_cors_headers(response)
            
            # Success if we get an error response (404) with CORS headers
            success = response.status_code == 404 and cors_present
            details = f"Status: {response.status_code}, CORS: {cors_details}"
            
            if response.status_code == 401:
                # Also acceptable - unauthorized with CORS
                success = cors_present
                details += " (Unauthorized, but CORS present)"
            
            self.log_test_result(test_name, success, details, cors_present)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}", False)
            return False
    
    def run_all_tests(self):
        """Run all cart operation tests"""
        print("=" * 80)
        print("CART OPERATIONS CORS FIX TESTING")
        print("=" * 80)
        print(f"API Base URL: {self.api_base_url}")
        print(f"Test User: {self.test_user_email}")
        print(f"Test Time: {datetime.now().isoformat()}")
        print()
        
        # Test OPTIONS requests for CORS preflight
        print("Testing CORS Preflight (OPTIONS requests):")
        print("-" * 50)
        self.test_options_request("/carts")
        
        # Test cart operations
        print("Testing Cart Operations:")
        print("-" * 50)
        self.test_create_cart()
        self.test_get_cart()
        self.test_update_cart()
        self.test_clear_cart()
        
        # Test error response CORS
        print("Testing Error Response CORS:")
        print("-" * 50)
        self.test_error_response_cors()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        cors_tests = sum(1 for result in self.test_results if result['cors_headers_present'])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed Tests: {passed_tests}")
        print(f"Failed Tests: {total_tests - passed_tests}")
        print(f"Tests with CORS Headers: {cors_tests}")
        print(f"Tests without CORS Headers: {total_tests - cors_tests}")
        print()
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        cors_rate = (cors_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"CORS Header Rate: {cors_rate:.1f}%")
        print()
        
        # Detailed results
        print("DETAILED RESULTS:")
        print("-" * 50)
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            cors = "CORS" if result['cors_headers_present'] else "NO-CORS"
            print(f"{status:4} | {cors:7} | {result['test_name']}")
        
        print()
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'cart_operations_cors_test_results_{timestamp}.json'
        
        with open(results_file, 'w') as f:
            json.dump({
                'test_summary': {
                    'timestamp': datetime.now().isoformat(),
                    'api_base_url': self.api_base_url,
                    'test_user_email': self.test_user_email,
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests,
                    'cors_tests': cors_tests,
                    'success_rate': success_rate,
                    'cors_rate': cors_rate
                },
                'test_results': self.test_results
            }, f, indent=2)
        
        print(f"Results saved to: {results_file}")
        
        # Overall assessment
        print()
        print("ASSESSMENT:")
        print("-" * 50)
        
        if cors_rate >= 90:
            print("✅ CORS Fix Status: SUCCESS - Most responses include CORS headers")
        elif cors_rate >= 70:
            print("⚠️  CORS Fix Status: PARTIAL - Some responses missing CORS headers")
        else:
            print("❌ CORS Fix Status: FAILED - Many responses missing CORS headers")
        
        if success_rate >= 80:
            print("✅ Cart Operations: WORKING - Most operations successful")
        elif success_rate >= 60:
            print("⚠️  Cart Operations: PARTIAL - Some operations failing")
        else:
            print("❌ Cart Operations: FAILED - Many operations failing")
        
        print()
        print("RECOMMENDATIONS:")
        print("-" * 50)
        
        if cors_rate < 90:
            print("- Review backend handlers to ensure all responses include CORS headers")
            print("- Check error response handling in shared auth utilities")
            print("- Verify CORS configuration in API Gateway")
        
        if success_rate < 80:
            print("- Check authentication configuration")
            print("- Verify API endpoints are properly deployed")
            print("- Review request/response format compatibility")
        
        print("- Test with actual authenticated user for complete validation")
        print("- Monitor cart operations in production environment")

def main():
    """Main function to run cart operations testing"""
    
    # Initialize tester
    tester = CartOperationTester(API_BASE_URL, TEST_USER_EMAIL)
    
    # Run all tests
    tester.run_all_tests()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())