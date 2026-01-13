"""
Authentication Performance and Load Testing
Tests authentication system performance under various load conditions
"""

import json
import pytest
import time
import base64
import concurrent.futures
import threading
from unittest.mock import Mock, patch
import sys
import os

# Add the shared directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    validate_permissions,
    determine_regional_access,
    check_regional_data_access
)


class TestAuthenticationPerformance:
    """Test authentication system performance"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_credential_extraction_performance(self):
        """Test performance of credential extraction"""
        token = self.create_jwt_token("test@hdcn.nl", ["hdcnLeden", "Regio_1"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Measure time for single extraction
        start_time = time.time()
        email, roles, error = extract_user_credentials(event)
        single_time = time.time() - start_time
        
        assert email == "test@hdcn.nl"
        assert error is None
        assert single_time < 0.1, f"Single credential extraction took {single_time:.3f}s, should be < 0.1s"
        
        # Measure time for multiple extractions
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            email, roles, error = extract_user_credentials(event)
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        assert avg_time < 0.01, f"Average credential extraction took {avg_time:.6f}s, should be < 0.01s"
        print(f"Credential extraction: {avg_time:.6f}s average over {iterations} iterations")
    
    def test_permission_validation_performance(self):
        """Test performance of permission validation"""
        user_roles = ["Members_CRUD", "Events_Read", "Regio_1", "Regio_2"]
        required_permissions = ["members_read", "events_read"]
        
        # Measure time for single validation
        start_time = time.time()
        is_authorized, error = validate_permissions(user_roles, required_permissions)
        single_time = time.time() - start_time
        
        assert is_authorized is True
        assert error is None
        assert single_time < 0.05, f"Single permission validation took {single_time:.3f}s, should be < 0.05s"
        
        # Measure time for multiple validations
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            is_authorized, error = validate_permissions(user_roles, required_permissions)
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        assert avg_time < 0.005, f"Average permission validation took {avg_time:.6f}s, should be < 0.005s"
        print(f"Permission validation: {avg_time:.6f}s average over {iterations} iterations")
    
    def test_regional_access_performance(self):
        """Test performance of regional access determination"""
        user_roles = ["Members_Read", "Regio_1", "Regio_3", "Regio_5"]
        
        # Measure time for single regional access check
        start_time = time.time()
        regional_info = determine_regional_access(user_roles)
        single_time = time.time() - start_time
        
        assert regional_info['access_type'] == 'regional'
        assert single_time < 0.01, f"Single regional access check took {single_time:.3f}s, should be < 0.01s"
        
        # Measure time for multiple regional access checks
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            regional_info = determine_regional_access(user_roles)
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        assert avg_time < 0.001, f"Average regional access check took {avg_time:.6f}s, should be < 0.001s"
        print(f"Regional access determination: {avg_time:.6f}s average over {iterations} iterations")
    
    def test_complete_auth_flow_performance(self):
        """Test performance of complete authentication flow"""
        token = self.create_jwt_token("admin@hdcn.nl", ["Members_CRUD", "Events_Read", "Regio_All"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        def complete_auth_flow():
            # Extract credentials
            email, roles, error = extract_user_credentials(event)
            if error:
                return False
            
            # Validate permissions
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                roles, ["members_read", "events_read"], email
            )
            if not is_authorized:
                return False
            
            # Check regional access
            is_allowed, reason = check_regional_data_access(roles, "3", email)
            return is_allowed
        
        # Measure time for single complete flow
        start_time = time.time()
        result = complete_auth_flow()
        single_time = time.time() - start_time
        
        assert result is True
        assert single_time < 0.2, f"Single complete auth flow took {single_time:.3f}s, should be < 0.2s"
        
        # Measure time for multiple complete flows
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            result = complete_auth_flow()
            assert result is True
        
        total_time = time.time() - start_time
        avg_time = total_time / iterations
        
        assert avg_time < 0.05, f"Average complete auth flow took {avg_time:.6f}s, should be < 0.05s"
        print(f"Complete auth flow: {avg_time:.6f}s average over {iterations} iterations")


class TestAuthenticationConcurrency:
    """Test authentication system under concurrent load"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_concurrent_credential_extraction(self):
        """Test concurrent credential extraction"""
        token = self.create_jwt_token("concurrent@hdcn.nl", ["hdcnLeden", "Regio_1"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        def extract_credentials():
            email, roles, error = extract_user_credentials(event)
            return email == "concurrent@hdcn.nl" and error is None
        
        # Test with multiple threads
        num_threads = 50
        num_requests_per_thread = 20
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                for _ in range(num_requests_per_thread):
                    future = executor.submit(extract_credentials)
                    futures.append(future)
            
            # Wait for all requests to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        total_requests = num_threads * num_requests_per_thread
        avg_time = total_time / total_requests
        
        # All requests should succeed
        assert all(results), "Some concurrent credential extractions failed"
        assert avg_time < 0.1, f"Average concurrent extraction took {avg_time:.6f}s, should be < 0.1s"
        
        print(f"Concurrent credential extraction: {total_requests} requests in {total_time:.3f}s")
        print(f"Average time per request: {avg_time:.6f}s")
    
    def test_concurrent_permission_validation(self):
        """Test concurrent permission validation"""
        test_cases = [
            (["hdcnLeden"], ["profile_read"]),
            (["Members_Read", "Regio_1"], ["members_read"]),
            (["Members_CRUD", "Regio_All"], ["members_create"]),
            (["Events_Read", "Regio_2"], ["events_read"]),
            (["System_CRUD"], ["members_delete"])
        ]
        
        def validate_permission(user_roles, required_permissions):
            is_authorized, error = validate_permissions(user_roles, required_permissions)
            return is_authorized and error is None
        
        # Test with multiple threads and different permission scenarios
        num_threads = 20
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                for user_roles, required_permissions in test_cases:
                    future = executor.submit(validate_permission, user_roles, required_permissions)
                    futures.append(future)
            
            # Wait for all validations to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        total_requests = num_threads * len(test_cases)
        avg_time = total_time / total_requests
        
        # All requests should succeed
        assert all(results), "Some concurrent permission validations failed"
        assert avg_time < 0.05, f"Average concurrent validation took {avg_time:.6f}s, should be < 0.05s"
        
        print(f"Concurrent permission validation: {total_requests} requests in {total_time:.3f}s")
        print(f"Average time per request: {avg_time:.6f}s")
    
    def test_concurrent_complete_auth_flows(self):
        """Test concurrent complete authentication flows"""
        users = [
            ("user1@hdcn.nl", ["hdcnLeden"]),
            ("admin1@hdcn.nl", ["Members_CRUD", "Regio_1"]),
            ("admin2@hdcn.nl", ["Events_Read", "Regio_All"]),
            ("regional@hdcn.nl", ["Members_Read", "Regio_3"]),
            ("national@hdcn.nl", ["System_CRUD"])
        ]
        
        def complete_auth_flow(email, roles):
            token = self.create_jwt_token(email, roles)
            event = {
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
            
            # Extract credentials
            extracted_email, extracted_roles, error = extract_user_credentials(event)
            if error or extracted_email != email:
                return False
            
            # Validate permissions based on role type
            if "hdcnLeden" in roles:
                required_permissions = ["profile_read"]
            elif "System_CRUD" in roles:
                required_permissions = ["members_delete"]
            else:
                required_permissions = ["members_read"]
            
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                extracted_roles, required_permissions, extracted_email
            )
            
            return is_authorized and error_response is None
        
        # Test with multiple threads
        num_threads = 25
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                for email, roles in users:
                    future = executor.submit(complete_auth_flow, email, roles)
                    futures.append(future)
            
            # Wait for all flows to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        total_requests = num_threads * len(users)
        avg_time = total_time / total_requests
        
        # All requests should succeed
        assert all(results), "Some concurrent auth flows failed"
        assert avg_time < 0.2, f"Average concurrent auth flow took {avg_time:.6f}s, should be < 0.2s"
        
        print(f"Concurrent complete auth flows: {total_requests} requests in {total_time:.3f}s")
        print(f"Average time per request: {avg_time:.6f}s")


class TestAuthenticationMemoryUsage:
    """Test authentication system memory usage"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_memory_usage_with_large_role_sets(self):
        """Test memory usage with large numbers of roles"""
        # Create user with many roles (simulating complex organizational structure)
        large_role_set = []
        for i in range(1, 10):  # All 9 regions
            large_role_set.append(f"Regio_{i}")
        
        # Add various permission roles
        permission_roles = [
            "Members_CRUD", "Events_CRUD", "Products_CRUD", 
            "Communication_CRUD", "Members_Export", "Events_Export"
        ]
        large_role_set.extend(permission_roles)
        
        token = self.create_jwt_token("complex_user@hdcn.nl", large_role_set)
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Test that large role sets don't cause performance issues
        start_time = time.time()
        
        for _ in range(100):
            email, roles, error = extract_user_credentials(event)
            assert error is None
            assert len(roles) == len(large_role_set)
            
            # Test permission validation with large role set
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                roles, ["members_read", "events_create"], email
            )
            assert is_authorized is True
            assert error_response is None
        
        total_time = time.time() - start_time
        avg_time = total_time / 100
        
        assert avg_time < 0.1, f"Large role set processing took {avg_time:.6f}s, should be < 0.1s"
        print(f"Large role set ({len(large_role_set)} roles) processing: {avg_time:.6f}s average")
    
    def test_memory_usage_with_many_users(self):
        """Test memory usage when processing many different users"""
        # Create many different users
        users = []
        for i in range(1000):
            email = f"user{i}@hdcn.nl"
            roles = ["hdcnLeden", f"Regio_{(i % 9) + 1}"]  # Distribute across regions
            if i % 10 == 0:  # Every 10th user is an admin
                roles.extend(["Members_Read", "Events_Read"])
            users.append((email, roles))
        
        # Process all users
        start_time = time.time()
        
        for email, roles in users:
            token = self.create_jwt_token(email, roles)
            event = {
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
            
            extracted_email, extracted_roles, error = extract_user_credentials(event)
            assert error is None
            assert extracted_email == email
            
            # Quick permission check
            is_authorized, error = validate_permissions(extracted_roles, ["profile_read"])
            assert is_authorized is True
        
        total_time = time.time() - start_time
        avg_time = total_time / len(users)
        
        assert avg_time < 0.01, f"Processing {len(users)} users took {avg_time:.6f}s average, should be < 0.01s"
        print(f"Processed {len(users)} users in {total_time:.3f}s ({avg_time:.6f}s average)")


class TestAuthenticationStressTest:
    """Stress test authentication system under extreme conditions"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    def test_high_frequency_auth_requests(self):
        """Test authentication system under high frequency requests"""
        token = self.create_jwt_token("stress_test@hdcn.nl", ["Members_CRUD", "Regio_All"])
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Simulate high frequency requests (like a busy API)
        num_requests = 5000
        start_time = time.time()
        
        success_count = 0
        for _ in range(num_requests):
            email, roles, error = extract_user_credentials(event)
            if error is None and email == "stress_test@hdcn.nl":
                success_count += 1
        
        total_time = time.time() - start_time
        avg_time = total_time / num_requests
        
        assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
        assert avg_time < 0.005, f"High frequency requests took {avg_time:.6f}s average, should be < 0.005s"
        
        print(f"High frequency test: {num_requests} requests in {total_time:.3f}s")
        print(f"Success rate: {(success_count/num_requests)*100:.1f}%")
        print(f"Average time per request: {avg_time:.6f}s")
    
    def test_burst_load_handling(self):
        """Test authentication system handling burst loads"""
        def burst_worker(worker_id, num_requests):
            """Worker function for burst testing"""
            token = self.create_jwt_token(f"burst_user_{worker_id}@hdcn.nl", ["hdcnLeden"])
            event = {
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
            
            success_count = 0
            for _ in range(num_requests):
                email, roles, error = extract_user_credentials(event)
                if error is None:
                    # Also test permission validation
                    is_authorized, error = validate_permissions(roles, ["profile_read"])
                    if is_authorized:
                        success_count += 1
            
            return success_count
        
        # Simulate burst load with many concurrent workers
        num_workers = 100
        requests_per_worker = 50
        total_expected = num_workers * requests_per_worker
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(burst_worker, worker_id, requests_per_worker)
                for worker_id in range(num_workers)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        total_success = sum(results)
        
        assert total_success == total_expected, f"Only {total_success}/{total_expected} burst requests succeeded"
        
        avg_time = total_time / total_expected
        assert avg_time < 0.1, f"Burst load handling took {avg_time:.6f}s average, should be < 0.1s"
        
        print(f"Burst load test: {total_expected} requests from {num_workers} workers in {total_time:.3f}s")
        print(f"Success rate: {(total_success/total_expected)*100:.1f}%")
        print(f"Average time per request: {avg_time:.6f}s")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])  # -s to see print statements