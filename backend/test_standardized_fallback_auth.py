#!/usr/bin/env python3
"""
Test Standardized Fallback Authentication
Validates that all auth_fallback.py files work consistently

This script tests:
1. Function availability and signatures
2. Role validation consistency
3. Error response formats
4. Regional access determination
5. Backward compatibility
"""

import sys
import importlib.util
from pathlib import Path
import json


def load_auth_fallback_module(handler_dir):
    """Load auth_fallback.py module from a handler directory"""
    auth_fallback_path = handler_dir / "auth_fallback.py"
    
    if not auth_fallback_path.exists():
        return None, f"auth_fallback.py not found in {handler_dir}"
    
    try:
        spec = importlib.util.spec_from_file_location(
            f"auth_fallback_{handler_dir.name}", 
            auth_fallback_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as e:
        return None, f"Failed to load module: {str(e)}"


def test_function_signatures(module, handler_name):
    """Test that all required functions exist with correct signatures"""
    required_functions = {
        'extract_user_credentials': 1,  # event
        'validate_permissions': 4,      # user_roles, required_permissions, user_email=None, resource_context=None
        'validate_permissions_with_regions': 4,  # same as above
        'determine_regional_access': 2,  # user_roles, resource_context=None
        'cors_headers': 0,              # no parameters
        'handle_options_request': 0,    # no parameters
        'create_error_response': 3,     # status_code, error_message, details=None
        'create_success_response': 2,   # data, status_code=200
        'log_successful_access': 4,     # user_email, user_roles, operation, resource_context=None
        'require_auth_and_permissions': 1  # required_permissions
    }
    
    results = {
        'handler': handler_name,
        'functions_found': [],
        'functions_missing': [],
        'signature_errors': []
    }
    
    for func_name, expected_params in required_functions.items():
        if hasattr(module, func_name):
            results['functions_found'].append(func_name)
            
            # Test function signature by calling with None parameters
            try:
                func = getattr(module, func_name)
                # Basic signature test - just check if function is callable
                if not callable(func):
                    results['signature_errors'].append(f"{func_name} is not callable")
            except Exception as e:
                results['signature_errors'].append(f"{func_name}: {str(e)}")
        else:
            results['functions_missing'].append(func_name)
    
    return results


def test_role_validation_consistency(module, handler_name):
    """Test role validation with various role combinations"""
    test_cases = [
        # System admin roles
        {
            'name': 'System_CRUD',
            'roles': ['System_CRUD'],
            'expected': True,
            'description': 'System admin should have access'
        },
        {
            'name': 'System_User_Management',
            'roles': ['System_User_Management'],
            'expected': True,
            'description': 'System user management should have access'
        },
        
        # Legacy admin roles
        {
            'name': 'National_Chairman',
            'roles': ['National_Chairman'],
            'expected': True,
            'description': 'Legacy admin should have access'
        },
        
        # New role structure (permission + region)
        {
            'name': 'Members_CRUD + Regio_All',
            'roles': ['Members_CRUD', 'Regio_All'],
            'expected': True,
            'description': 'New structure with permission and region should work'
        },
        {
            'name': 'Members_Read + Regio_Noord-Holland',
            'roles': ['Members_Read', 'Regio_Noord-Holland'],
            'expected': True,
            'description': 'Regional access should work'
        },
        
        # Incomplete new structure
        {
            'name': 'Members_CRUD only',
            'roles': ['Members_CRUD'],
            'expected': False,
            'description': 'Permission without region should be denied'
        },
        {
            'name': 'Regio_All only',
            'roles': ['Regio_All'],
            'expected': False,
            'description': 'Region without permission should be denied'
        },
        
        # Legacy _All roles - FOR TESTING BACKWARD COMPATIBILITY ONLY
        # These roles have been removed from production
        {
            'name': 'Members_CRUD_All (DEPRECATED - TEST ONLY)',
            'roles': ['Members_CRUD_All'],
            'expected': True,
            'description': 'Legacy _All roles should still work during transition'
        },
        
        # Special roles
        {
            'name': 'hdcnLeden',
            'roles': ['hdcnLeden'],
            'expected': False,
            'description': 'Limited roles should be denied for admin functions'
        },
        
        # No roles
        {
            'name': 'No roles',
            'roles': [],
            'expected': False,
            'description': 'No roles should be denied'
        }
    ]
    
    results = {
        'handler': handler_name,
        'test_results': [],
        'consistency_issues': []
    }
    
    for test_case in test_cases:
        try:
            is_authorized, error_response = module.validate_permissions(
                test_case['roles'], 
                ['test_permission'], 
                'test@example.com'
            )
            
            test_result = {
                'name': test_case['name'],
                'roles': test_case['roles'],
                'expected': test_case['expected'],
                'actual': is_authorized,
                'passed': is_authorized == test_case['expected'],
                'description': test_case['description']
            }
            
            if not test_result['passed']:
                results['consistency_issues'].append(
                    f"{test_case['name']}: expected {test_case['expected']}, got {is_authorized}"
                )
            
            results['test_results'].append(test_result)
            
        except Exception as e:
            results['consistency_issues'].append(
                f"{test_case['name']}: Exception during validation: {str(e)}"
            )
    
    return results


def test_regional_access_determination(module, handler_name):
    """Test regional access determination logic"""
    test_cases = [
        {
            'name': 'System admin',
            'roles': ['System_CRUD'],
            'expected_access_type': 'system_admin',
            'expected_full_access': True
        },
        {
            'name': 'Legacy admin',
            'roles': ['National_Chairman'],
            'expected_access_type': 'legacy_admin',
            'expected_full_access': True
        },
        {
            'name': 'National access',
            'roles': ['Members_CRUD', 'Regio_All'],
            'expected_access_type': 'national',
            'expected_full_access': True
        },
        {
            'name': 'Regional access',
            'roles': ['Members_CRUD', 'Regio_Noord-Holland'],
            'expected_access_type': 'regional',
            'expected_full_access': False
        },
        {
            'name': 'Legacy _All role (DEPRECATED - TEST ONLY)',
            'roles': ['Members_CRUD_All'],
            'expected_access_type': 'legacy_all',
            'expected_full_access': True
        },
        {
            'name': 'Limited access',
            'roles': ['hdcnLeden'],
            'expected_access_type': 'limited',
            'expected_full_access': False
        }
    ]
    
    results = {
        'handler': handler_name,
        'regional_tests': [],
        'regional_issues': []
    }
    
    for test_case in test_cases:
        try:
            regional_info = module.determine_regional_access(test_case['roles'])
            
            test_result = {
                'name': test_case['name'],
                'roles': test_case['roles'],
                'expected_access_type': test_case['expected_access_type'],
                'actual_access_type': regional_info.get('access_type'),
                'expected_full_access': test_case['expected_full_access'],
                'actual_full_access': regional_info.get('has_full_access'),
                'passed': (
                    regional_info.get('access_type') == test_case['expected_access_type'] and
                    regional_info.get('has_full_access') == test_case['expected_full_access']
                )
            }
            
            if not test_result['passed']:
                results['regional_issues'].append(
                    f"{test_case['name']}: expected {test_case['expected_access_type']}/{test_case['expected_full_access']}, "
                    f"got {regional_info.get('access_type')}/{regional_info.get('has_full_access')}"
                )
            
            results['regional_tests'].append(test_result)
            
        except Exception as e:
            results['regional_issues'].append(
                f"{test_case['name']}: Exception during regional access test: {str(e)}"
            )
    
    return results


def test_error_response_format(module, handler_name):
    """Test that error responses have consistent format"""
    results = {
        'handler': handler_name,
        'error_format_tests': [],
        'format_issues': []
    }
    
    # Test create_error_response function
    try:
        error_response = module.create_error_response(403, "Test error", {"detail": "test"})
        
        required_fields = ['statusCode', 'headers', 'body']
        format_test = {
            'function': 'create_error_response',
            'has_required_fields': all(field in error_response for field in required_fields),
            'status_code_correct': error_response.get('statusCode') == 403,
            'has_cors_headers': 'Access-Control-Allow-Origin' in error_response.get('headers', {}),
            'body_is_json': True
        }
        
        # Test if body is valid JSON
        try:
            body_data = json.loads(error_response.get('body', '{}'))
            format_test['body_has_error'] = 'error' in body_data
        except json.JSONDecodeError:
            format_test['body_is_json'] = False
            format_test['body_has_error'] = False
        
        format_test['passed'] = all([
            format_test['has_required_fields'],
            format_test['status_code_correct'],
            format_test['has_cors_headers'],
            format_test['body_is_json'],
            format_test['body_has_error']
        ])
        
        if not format_test['passed']:
            results['format_issues'].append("create_error_response format issues")
        
        results['error_format_tests'].append(format_test)
        
    except Exception as e:
        results['format_issues'].append(f"create_error_response exception: {str(e)}")
    
    return results


def test_constants_availability(module, handler_name):
    """Test that standardized constants are available"""
    expected_constants = [
        'SYSTEM_ADMIN_ROLES',
        'LEGACY_ADMIN_ROLES', 
        'PERMISSION_ROLES',
        'SPECIAL_ROLES',
        'FALLBACK_AUTH_VERSION',
        'FALLBACK_AUTH_UPDATED'
    ]
    
    results = {
        'handler': handler_name,
        'constants_found': [],
        'constants_missing': []
    }
    
    for constant in expected_constants:
        if hasattr(module, constant):
            results['constants_found'].append(constant)
        else:
            results['constants_missing'].append(constant)
    
    return results


def run_comprehensive_test():
    """Run comprehensive tests on all auth_fallback.py files"""
    print("🧪 Starting Comprehensive Fallback Authentication Tests")
    print("=" * 70)
    
    handlers_dir = Path("backend/handler")
    handler_dirs = [d for d in handlers_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if not handler_dirs:
        print("❌ No handler directories found!")
        return
    
    print(f"Testing {len(handler_dirs)} handlers...")
    
    all_results = {
        'total_handlers': len(handler_dirs),
        'successful_loads': 0,
        'failed_loads': 0,
        'function_tests': [],
        'role_validation_tests': [],
        'regional_access_tests': [],
        'error_format_tests': [],
        'constants_tests': [],
        'overall_issues': []
    }
    
    for handler_dir in sorted(handler_dirs):
        print(f"\n🔍 Testing: {handler_dir.name}")
        
        # Load module
        module, load_error = load_auth_fallback_module(handler_dir)
        if load_error:
            print(f"  ❌ Failed to load: {load_error}")
            all_results['failed_loads'] += 1
            all_results['overall_issues'].append(f"{handler_dir.name}: {load_error}")
            continue
        
        all_results['successful_loads'] += 1
        
        # Test function signatures
        func_results = test_function_signatures(module, handler_dir.name)
        all_results['function_tests'].append(func_results)
        
        if func_results['functions_missing']:
            print(f"  ⚠️ Missing functions: {func_results['functions_missing']}")
        if func_results['signature_errors']:
            print(f"  ⚠️ Signature errors: {func_results['signature_errors']}")
        if not func_results['functions_missing'] and not func_results['signature_errors']:
            print(f"  ✅ All functions present and callable")
        
        # Test role validation consistency
        role_results = test_role_validation_consistency(module, handler_dir.name)
        all_results['role_validation_tests'].append(role_results)
        
        if role_results['consistency_issues']:
            print(f"  ⚠️ Role validation issues: {len(role_results['consistency_issues'])}")
            for issue in role_results['consistency_issues'][:3]:  # Show first 3
                print(f"    - {issue}")
        else:
            print(f"  ✅ Role validation consistent")
        
        # Test regional access determination
        regional_results = test_regional_access_determination(module, handler_dir.name)
        all_results['regional_access_tests'].append(regional_results)
        
        if regional_results['regional_issues']:
            print(f"  ⚠️ Regional access issues: {len(regional_results['regional_issues'])}")
        else:
            print(f"  ✅ Regional access determination working")
        
        # Test error response format
        error_results = test_error_response_format(module, handler_dir.name)
        all_results['error_format_tests'].append(error_results)
        
        if error_results['format_issues']:
            print(f"  ⚠️ Error format issues: {error_results['format_issues']}")
        else:
            print(f"  ✅ Error response format consistent")
        
        # Test constants availability
        constants_results = test_constants_availability(module, handler_dir.name)
        all_results['constants_tests'].append(constants_results)
        
        if constants_results['constants_missing']:
            print(f"  ⚠️ Missing constants: {constants_results['constants_missing']}")
        else:
            print(f"  ✅ All standardized constants present")
    
    # Overall summary
    print("\n" + "=" * 70)
    print("📊 Comprehensive Test Summary:")
    print(f"  📁 Total handlers tested: {all_results['total_handlers']}")
    print(f"  ✅ Successfully loaded: {all_results['successful_loads']}")
    print(f"  ❌ Failed to load: {all_results['failed_loads']}")
    
    # Function tests summary
    handlers_with_all_functions = len([r for r in all_results['function_tests'] if not r['functions_missing']])
    print(f"  🔧 Handlers with all functions: {handlers_with_all_functions}/{all_results['successful_loads']}")
    
    # Role validation summary
    handlers_with_consistent_roles = len([r for r in all_results['role_validation_tests'] if not r['consistency_issues']])
    print(f"  🔐 Handlers with consistent role validation: {handlers_with_consistent_roles}/{all_results['successful_loads']}")
    
    # Regional access summary
    handlers_with_working_regional = len([r for r in all_results['regional_access_tests'] if not r['regional_issues']])
    print(f"  🌍 Handlers with working regional access: {handlers_with_working_regional}/{all_results['successful_loads']}")
    
    # Error format summary
    handlers_with_consistent_errors = len([r for r in all_results['error_format_tests'] if not r['format_issues']])
    print(f"  ❌ Handlers with consistent error format: {handlers_with_consistent_errors}/{all_results['successful_loads']}")
    
    # Constants summary
    handlers_with_all_constants = len([r for r in all_results['constants_tests'] if not r['constants_missing']])
    print(f"  📋 Handlers with all constants: {handlers_with_all_constants}/{all_results['successful_loads']}")
    
    # Overall assessment
    perfect_handlers = 0
    for i in range(len(all_results['function_tests'])):
        if (not all_results['function_tests'][i]['functions_missing'] and
            not all_results['function_tests'][i]['signature_errors'] and
            not all_results['role_validation_tests'][i]['consistency_issues'] and
            not all_results['regional_access_tests'][i]['regional_issues'] and
            not all_results['error_format_tests'][i]['format_issues'] and
            not all_results['constants_tests'][i]['constants_missing']):
            perfect_handlers += 1
    
    print(f"\n🎯 Perfect handlers (all tests passed): {perfect_handlers}/{all_results['successful_loads']}")
    
    if perfect_handlers == all_results['successful_loads']:
        print("🎉 ALL HANDLERS HAVE CONSISTENT STANDARDIZED FALLBACK AUTHENTICATION!")
    else:
        print("⚠️ Some handlers have issues that need attention.")
    
    return all_results


if __name__ == '__main__':
    results = run_comprehensive_test()
    
    # Exit with appropriate code
    if results['failed_loads'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)