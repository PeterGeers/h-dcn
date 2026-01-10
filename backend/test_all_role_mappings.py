#!/usr/bin/env python3
"""
Comprehensive Role Mapping Test Suite

This script runs all role mapping tests to verify that the authentication system
works correctly as required by the role migration plan task:
"Test role mappings: Verify all role-to-permission mappings work correctly"

Test Suites:
1. Core Authentication Layer Tests (test_core_authentication_layer.py)
2. Role-to-Permission Mapping Tests (test_role_permission_mappings.py)
"""

import sys
import os
import subprocess
from pathlib import Path


def run_test_suite(test_file, description):
    """Run a test suite and return success status"""
    print(f"\n{'='*80}")
    print(f"🧪 Running {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        
        if success:
            print(f"✅ {description} - ALL TESTS PASSED")
        else:
            print(f"❌ {description} - SOME TESTS FAILED")
            
        return success
        
    except Exception as e:
        print(f"💥 Failed to run {description}: {str(e)}")
        return False


def main():
    """Run all role mapping test suites"""
    print("🚀 Comprehensive Role Mapping Verification")
    print("Task: Test role mappings - Verify all role-to-permission mappings work correctly")
    print("=" * 80)
    
    # Track overall results
    all_tests_passed = True
    test_results = {}
    
    # Test Suite 1: Core Authentication Layer
    success1 = run_test_suite(
        "test_core_authentication_layer.py",
        "Core Authentication Layer Tests"
    )
    test_results["Core Authentication"] = success1
    all_tests_passed = all_tests_passed and success1
    
    # Test Suite 2: Role-to-Permission Mappings
    success2 = run_test_suite(
        "test_role_permission_mappings.py", 
        "Role-to-Permission Mapping Tests"
    )
    test_results["Role Mappings"] = success2
    all_tests_passed = all_tests_passed and success2
    
    # Final Summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n{'='*80}")
    
    if all_tests_passed:
        print("🎉 ALL ROLE MAPPING TESTS PASSED!")
        print("\n✅ VERIFICATION COMPLETE:")
        print("  ✓ Admin roles work correctly")
        print("  ✓ New role structure (permission + region) works correctly") 
        print("  ✓ Legacy role cleanup verified (old roles correctly removed)")
        print("  ✓ Regional access controls work correctly")
        print("  ✓ Permission validation works correctly")
        print("  ✓ All individual role-to-permission mappings work correctly")
        print("  ✓ Role combinations work correctly")
        print("  ✓ Read-only and export-only restrictions work correctly")
        print("  ✓ Organizational and special roles work correctly")
        print("  ✓ Invalid roles correctly grant no permissions")
        print("  ✓ Error handling for incomplete structures works correctly")
        
        print("\n🚀 TASK COMPLETION STATUS:")
        print("  Task: 'Test role mappings: Verify all role-to-permission mappings work correctly'")
        print("  Status: ✅ COMPLETED SUCCESSFULLY")
        print("  Result: All role-to-permission mappings verified and working correctly")
        
        print("\n📋 MIGRATION PLAN STATUS:")
        print("  ✅ Core authentication layer is working correctly")
        print("  ✅ New role structure validation is working correctly")
        print("  ✅ Regional access controls are working correctly")
        print("  ✅ Legacy role cleanup has been verified")
        print("  ✅ All role-to-permission mappings are correct and functional")
        
        print("\n🎯 NEXT STEPS:")
        print("  1. Mark this task as completed in the role migration plan")
        print("  2. Continue with remaining migration tasks")
        print("  3. Test organizational role combinations")
        print("  4. Proceed to frontend authentication migration when ready")
        
        return True
    else:
        print("❌ SOME ROLE MAPPING TESTS FAILED!")
        print("\n🔍 Failed Test Suites:")
        for test_name, passed in test_results.items():
            if not passed:
                print(f"  - {test_name}")
        
        print("\n⚠️ TASK STATUS:")
        print("  Task: 'Test role mappings: Verify all role-to-permission mappings work correctly'")
        print("  Status: ❌ FAILED - Some role mappings need attention")
        
        print("\n🛠️ REQUIRED ACTIONS:")
        print("  1. Review failed tests above")
        print("  2. Fix any role mapping issues identified")
        print("  3. Re-run this comprehensive test suite")
        print("  4. Do not proceed with migration until all tests pass")
        
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)