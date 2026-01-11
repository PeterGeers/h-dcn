#!/usr/bin/env python3
"""
Authentication Performance Test

This test verifies that the new authentication system doesn't impact performance
and meets the required response time benchmarks for the H-DCN system.

Performance Requirements:
- Authentication validation: < 100ms per request
- Permission checking: < 50ms per request  
- Regional filtering: < 25ms per request
- Concurrent user handling: Support 10+ simultaneous users
- Memory usage: Stable under load
"""

import time
import json
import threading
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add the shared directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        check_regional_data_access,
        get_user_accessible_regions,
        has_permission_and_region_access,
        can_access_resource_region,
        validate_crud_access
    )
except ImportError:
    print("⚠️ Could not import from shared.auth_utils, using local fallback")
    # Import from local auth_utils if shared is not available
    from auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        validate_permissions,
        determine_regional_access,
        check_regional_data_access,
        get_user_accessible_regions,
        has_permission_and_region_access,
        can_access_resource_region,
        validate_crud_access
    )


class AuthenticationPerformanceTest:
    """Test authentication system performance under various conditions"""
    
    def __init__(self):
        self.test_results = {
            'test_suite': 'Authentication Performance',
            'timestamp': datetime.now().isoformat(),
            'performance_tests': [],
            'summary': {}
        }
        
        # Performance benchmarks (in milliseconds)
        self.benchmarks = {
            'authentication_validation': 100,  # < 100ms
            'permission_checking': 50,         # < 50ms
            'regional_filtering': 25,          # < 25ms
            'concurrent_users': 200,           # < 200ms under load
            'memory_stable': True              # Memory should be stable
        }
        
        # Test data for various user scenarios
        self.test_users = {
            'national_admin': ['Members_CRUD', 'Regio_All'],
            'regional_admin': ['Members_CRUD', 'Regio_Utrecht'],
            'read_only_national': ['Members_Read', 'Regio_All'],
            'read_only_regional': ['Members_Read', 'Regio_Groningen/Drenthe'],
            'export_user': ['Members_Export', 'Regio_All'],
            'system_admin': ['System_CRUD'],
            'basic_member': ['hdcnLeden'],
            'incomplete_user': ['Members_CRUD'],  # Missing region role
            'multi_permission': ['Members_CRUD', 'Events_CRUD', 'Products_CRUD', 'Regio_All'],
            'multi_region': ['Members_Read', 'Regio_Utrecht', 'Regio_Noord-Holland', 'Regio_Limburg']
        }
        
        # Test scenarios for different operations
        self.test_scenarios = [
            {'operation': 'members_read', 'permissions': ['members_read']},
            {'operation': 'members_create', 'permissions': ['members_create']},
            {'operation': 'members_update', 'permissions': ['members_update']},
            {'operation': 'members_delete', 'permissions': ['members_delete']},
            {'operation': 'members_export', 'permissions': ['members_export']},
            {'operation': 'events_crud', 'permissions': ['events_create', 'events_update']},
            {'operation': 'products_crud', 'permissions': ['products_create', 'products_update']},
            {'operation': 'multi_permission', 'permissions': ['members_read', 'events_read', 'products_read']},
        ]

    def create_mock_event(self, user_roles, user_email="test@hdcn.nl"):
        """Create a mock Lambda event for testing"""
        # Create a simple JWT-like token for testing
        import base64
        
        payload = {
            'email': user_email,
            'cognito:groups': user_roles
        }
        
        # Simple base64 encoding for testing (not a real JWT)
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        mock_token = f"header.{payload_encoded}.signature"
        
        return {
            'headers': {
                'Authorization': f'Bearer {mock_token}',
                'Content-Type': 'application/json'
            },
            'httpMethod': 'POST',
            'body': json.dumps({'test': 'data'})
        }

    def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function in milliseconds"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000
        return execution_time_ms, result

    def test_authentication_validation_performance(self):
        """Test performance of user credential extraction and validation"""
        print("\n🔐 Testing Authentication Validation Performance")
        print("=" * 60)
        
        performance_results = []
        
        for user_type, user_roles in self.test_users.items():
            # Test credential extraction
            mock_event = self.create_mock_event(user_roles, f"{user_type}@hdcn.nl")
            
            execution_time, (user_email, extracted_roles, error) = self.measure_execution_time(
                extract_user_credentials, mock_event
            )
            
            success = error is None and user_email is not None
            meets_benchmark = execution_time <= self.benchmarks['authentication_validation']
            
            performance_results.append({
                'user_type': user_type,
                'execution_time_ms': execution_time,
                'success': success,
                'meets_benchmark': meets_benchmark,
                'extracted_roles': extracted_roles
            })
            
            status = "✅ PASS" if meets_benchmark else "❌ FAIL"
            print(f"{status} {user_type:20} | {execution_time:6.2f}ms | Benchmark: {self.benchmarks['authentication_validation']}ms")
        
        # Calculate statistics
        execution_times = [r['execution_time_ms'] for r in performance_results if r['success']]
        avg_time = statistics.mean(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0
        
        print(f"\n📊 Authentication Performance Summary:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Benchmark: {self.benchmarks['authentication_validation']}ms")
        
        self.test_results['performance_tests'].append({
            'test_name': 'authentication_validation_performance',
            'results': performance_results,
            'statistics': {
                'avg_time_ms': avg_time,
                'max_time_ms': max_time,
                'min_time_ms': min_time,
                'benchmark_ms': self.benchmarks['authentication_validation']
            },
            'overall_pass': max_time <= self.benchmarks['authentication_validation']
        })
        
        return max_time <= self.benchmarks['authentication_validation']

    def test_permission_checking_performance(self):
        """Test performance of permission validation"""
        print("\n🔑 Testing Permission Checking Performance")
        print("=" * 60)
        
        performance_results = []
        
        for user_type, user_roles in self.test_users.items():
            for scenario in self.test_scenarios:
                execution_time, (is_authorized, error_response, regional_info) = self.measure_execution_time(
                    validate_permissions_with_regions,
                    user_roles, scenario['permissions'], f"{user_type}@hdcn.nl", None
                )
                
                meets_benchmark = execution_time <= self.benchmarks['permission_checking']
                
                performance_results.append({
                    'user_type': user_type,
                    'scenario': scenario['operation'],
                    'execution_time_ms': execution_time,
                    'is_authorized': is_authorized,
                    'meets_benchmark': meets_benchmark
                })
                
                status = "✅ PASS" if meets_benchmark else "❌ FAIL"
                auth_status = "AUTH" if is_authorized else "DENY"
                print(f"{status} {user_type:15} | {scenario['operation']:15} | {execution_time:6.2f}ms | {auth_status}")
        
        # Calculate statistics
        execution_times = [r['execution_time_ms'] for r in performance_results]
        avg_time = statistics.mean(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        
        print(f"\n📊 Permission Checking Performance Summary:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Benchmark: {self.benchmarks['permission_checking']}ms")
        
        self.test_results['performance_tests'].append({
            'test_name': 'permission_checking_performance',
            'results': performance_results,
            'statistics': {
                'avg_time_ms': avg_time,
                'max_time_ms': max_time,
                'benchmark_ms': self.benchmarks['permission_checking']
            },
            'overall_pass': max_time <= self.benchmarks['permission_checking']
        })
        
        return max_time <= self.benchmarks['permission_checking']

    def test_regional_filtering_performance(self):
        """Test performance of regional access validation"""
        print("\n🌍 Testing Regional Filtering Performance")
        print("=" * 60)
        
        performance_results = []
        test_regions = ['Utrecht', 'Noord-Holland', 'Groningen/Drenthe', 'Limburg', 'Brabant/Zeeland']
        
        for user_type, user_roles in self.test_users.items():
            for region in test_regions:
                execution_time, (can_access, reason) = self.measure_execution_time(
                    check_regional_data_access,
                    user_roles, region, f"{user_type}@hdcn.nl"
                )
                
                meets_benchmark = execution_time <= self.benchmarks['regional_filtering']
                
                performance_results.append({
                    'user_type': user_type,
                    'region': region,
                    'execution_time_ms': execution_time,
                    'can_access': can_access,
                    'meets_benchmark': meets_benchmark
                })
                
                status = "✅ PASS" if meets_benchmark else "❌ FAIL"
                access_status = "ACCESS" if can_access else "DENY"
                print(f"{status} {user_type:15} | {region:20} | {execution_time:6.2f}ms | {access_status}")
        
        # Calculate statistics
        execution_times = [r['execution_time_ms'] for r in performance_results]
        avg_time = statistics.mean(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        
        print(f"\n📊 Regional Filtering Performance Summary:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Benchmark: {self.benchmarks['regional_filtering']}ms")
        
        self.test_results['performance_tests'].append({
            'test_name': 'regional_filtering_performance',
            'results': performance_results,
            'statistics': {
                'avg_time_ms': avg_time,
                'max_time_ms': max_time,
                'benchmark_ms': self.benchmarks['regional_filtering']
            },
            'overall_pass': max_time <= self.benchmarks['regional_filtering']
        })
        
        return max_time <= self.benchmarks['regional_filtering']

    def simulate_concurrent_user_request(self, user_type, user_roles, request_id):
        """Simulate a single user request for concurrent testing"""
        try:
            start_time = time.perf_counter()
            
            # Simulate full authentication flow
            mock_event = self.create_mock_event(user_roles, f"{user_type}_{request_id}@hdcn.nl")
            
            # Extract credentials
            user_email, extracted_roles, error = extract_user_credentials(mock_event)
            if error:
                return {'success': False, 'error': 'credential_extraction_failed', 'execution_time_ms': 0}
            
            # Validate permissions
            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                extracted_roles, ['members_read'], user_email, None
            )
            
            # Check regional access
            can_access, reason = check_regional_data_access(extracted_roles, 'Utrecht', user_email)
            
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            
            return {
                'success': True,
                'user_type': user_type,
                'request_id': request_id,
                'execution_time_ms': execution_time_ms,
                'is_authorized': is_authorized,
                'can_access_region': can_access
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': 0,
                'user_type': user_type,
                'request_id': request_id
            }

    def test_concurrent_user_performance(self):
        """Test performance under concurrent user load"""
        print("\n👥 Testing Concurrent User Performance")
        print("=" * 60)
        
        # Test with 10 concurrent users (mix of different user types)
        concurrent_users = 10
        requests_per_user = 5
        
        # Create test scenarios
        test_requests = []
        for i in range(concurrent_users):
            user_type = list(self.test_users.keys())[i % len(self.test_users)]
            user_roles = self.test_users[user_type]
            
            for j in range(requests_per_user):
                test_requests.append((user_type, user_roles, f"{i}_{j}"))
        
        print(f"Executing {len(test_requests)} concurrent requests...")
        
        # Execute concurrent requests
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(self.simulate_concurrent_user_request, user_type, user_roles, request_id)
                for user_type, user_roles, request_id in test_requests
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        if successful_requests:
            execution_times = [r['execution_time_ms'] for r in successful_requests]
            avg_time = statistics.mean(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
        else:
            avg_time = max_time = min_time = 0
        
        success_rate = len(successful_requests) / len(results) * 100
        meets_benchmark = max_time <= self.benchmarks['concurrent_users'] and success_rate >= 95
        
        print(f"\n📊 Concurrent User Performance Results:")
        print(f"   Total Requests: {len(results)}")
        print(f"   Successful: {len(successful_requests)} ({success_rate:.1f}%)")
        print(f"   Failed: {len(failed_requests)}")
        print(f"   Total Time: {total_time_ms:.2f}ms")
        print(f"   Average Request Time: {avg_time:.2f}ms")
        print(f"   Max Request Time: {max_time:.2f}ms")
        print(f"   Min Request Time: {min_time:.2f}ms")
        print(f"   Benchmark: {self.benchmarks['concurrent_users']}ms")
        
        status = "✅ PASS" if meets_benchmark else "❌ FAIL"
        print(f"\n{status} Concurrent Performance Test")
        
        self.test_results['performance_tests'].append({
            'test_name': 'concurrent_user_performance',
            'total_requests': len(results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': success_rate,
            'statistics': {
                'total_time_ms': total_time_ms,
                'avg_time_ms': avg_time,
                'max_time_ms': max_time,
                'min_time_ms': min_time,
                'benchmark_ms': self.benchmarks['concurrent_users']
            },
            'overall_pass': meets_benchmark
        })
        
        return meets_benchmark

    def test_memory_stability(self):
        """Test memory usage stability under repeated operations"""
        print("\n💾 Testing Memory Stability")
        print("=" * 60)
        
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Initial Memory Usage: {initial_memory:.2f} MB")
        
        # Perform many authentication operations
        iterations = 1000
        memory_samples = []
        
        for i in range(iterations):
            # Perform authentication operations
            for user_type, user_roles in list(self.test_users.items())[:3]:  # Test with 3 user types
                mock_event = self.create_mock_event(user_roles, f"{user_type}_{i}@hdcn.nl")
                user_email, extracted_roles, error = extract_user_credentials(mock_event)
                
                if not error:
                    validate_permissions_with_regions(
                        extracted_roles, ['members_read'], user_email, None
                    )
                    check_regional_data_access(extracted_roles, 'Utrecht', user_email)
            
            # Sample memory every 100 iterations
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
                print(f"Iteration {i:4d}: {current_memory:.2f} MB")
        
        # Force garbage collection
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Analyze memory stability
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_samples) if memory_samples else final_memory
        memory_stable = memory_increase < 10  # Less than 10MB increase is acceptable
        
        print(f"\n📊 Memory Stability Results:")
        print(f"   Initial Memory: {initial_memory:.2f} MB")
        print(f"   Final Memory: {final_memory:.2f} MB")
        print(f"   Max Memory: {max_memory:.2f} MB")
        print(f"   Memory Increase: {memory_increase:.2f} MB")
        print(f"   Iterations: {iterations}")
        
        status = "✅ PASS" if memory_stable else "❌ FAIL"
        print(f"\n{status} Memory Stability Test")
        
        self.test_results['performance_tests'].append({
            'test_name': 'memory_stability',
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'max_memory_mb': max_memory,
            'memory_increase_mb': memory_increase,
            'iterations': iterations,
            'memory_stable': memory_stable,
            'overall_pass': memory_stable
        })
        
        return memory_stable

    def run_all_performance_tests(self):
        """Run all performance tests and generate summary"""
        print("🚀 H-DCN Authentication Performance Test Suite")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Run all performance tests
        test_results = {
            'authentication_validation': self.test_authentication_validation_performance(),
            'permission_checking': self.test_permission_checking_performance(),
            'regional_filtering': self.test_regional_filtering_performance(),
            'concurrent_users': self.test_concurrent_user_performance(),
            'memory_stability': self.test_memory_stability()
        }
        
        # Generate summary
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        overall_pass = all(test_results.values())
        
        print("\n" + "=" * 80)
        print("📋 PERFORMANCE TEST SUMMARY")
        print("=" * 80)
        
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
        
        if overall_pass:
            print("🎉 ALL PERFORMANCE TESTS PASSED!")
            print("✅ New authentication system meets performance requirements")
        else:
            print("⚠️ SOME PERFORMANCE TESTS FAILED!")
            print("❌ Performance optimization may be needed")
        
        # Update summary
        self.test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'overall_pass': overall_pass,
            'test_results': test_results
        }
        
        # Save results to file
        results_filename = f"authentication_performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_filename}")
        
        return overall_pass


def main():
    """Main function to run performance tests"""
    try:
        # Check if psutil is available for memory testing
        try:
            import psutil
        except ImportError:
            print("⚠️ psutil not available - memory stability test will be skipped")
            print("   Install with: pip install psutil")
        
        # Run performance tests
        performance_test = AuthenticationPerformanceTest()
        success = performance_test.run_all_performance_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Performance test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()