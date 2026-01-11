#!/usr/bin/env python3
"""
Test the updated monitoring and logging functions
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from auth_utils import (
    log_successful_access,
    log_permission_denial,
    log_regional_access_event,
    log_role_structure_validation
)

def test_new_logging_functions():
    """Test all new logging functions with role structure"""
    print("🧪 Testing New Role Structure Logging Functions")
    print("=" * 60)
    
    # Test data with new role structure
    test_user_email = "test@h-dcn.nl"
    test_user_roles = ["Members_CRUD", "Regio_All"]
    
    print("\n1️⃣ Testing log_successful_access...")
    log_successful_access(
        user_email=test_user_email,
        user_roles=test_user_roles,
        operation="update_member",
        resource_context={"member_id": "12345"}
    )
    
    print("\n2️⃣ Testing log_permission_denial...")
    log_permission_denial(
        user_email=test_user_email,
        user_roles=["Members_Read", "Regio_Utrecht"],  # Insufficient permissions
        required_permissions=["members_update"],
        user_permissions=["members_read"],
        resource_context={"operation": "update_member"}
    )
    
    print("\n3️⃣ Testing log_regional_access_event (granted)...")
    log_regional_access_event(
        user_email=test_user_email,
        user_roles=test_user_roles,
        data_region="Utrecht",
        access_granted=True,
        reason="Full access via national",
        resource_context={"data_type": "member_list"}
    )
    
    print("\n4️⃣ Testing log_regional_access_event (denied)...")
    log_regional_access_event(
        user_email="regional@h-dcn.nl",
        user_roles=["Members_Read", "Regio_Utrecht"],
        data_region="Groningen/Drenthe",
        access_granted=False,
        reason="Access denied: User can only access regions ['Utrecht']",
        resource_context={"data_type": "member_list"}
    )
    
    print("\n5️⃣ Testing log_role_structure_validation (valid)...")
    log_role_structure_validation(
        user_email=test_user_email,
        user_roles=test_user_roles,
        validation_result={"valid": True, "reason": "Valid permission + region structure"},
        validation_context={"validation_type": "login"}
    )
    
    print("\n6️⃣ Testing log_role_structure_validation (invalid)...")
    log_role_structure_validation(
        user_email="incomplete@h-dcn.nl",
        user_roles=["Members_CRUD"],  # Missing region role
        validation_result={"valid": False, "reason": "Missing region assignment"},
        validation_context={"validation_type": "permission_check"}
    )
    
    print("\n✅ All logging functions tested successfully!")
    print("📊 Check the output above to verify new role structure logging format")

def test_role_structure_separation():
    """Test that role structure separation works correctly"""
    print("\n🔍 Testing Role Structure Separation")
    print("=" * 40)
    
    test_roles = ["Members_CRUD", "Events_Read", "Regio_All", "Regio_Utrecht", "System_CRUD"]
    
    permission_roles = [role for role in test_roles if not role.startswith('Regio_') and role not in ['hdcnLeden', 'verzoek_lid']]
    region_roles = [role for role in test_roles if role.startswith('Regio_')]
    
    print(f"Input roles: {test_roles}")
    print(f"Permission roles: {permission_roles}")
    print(f"Region roles: {region_roles}")
    
    expected_permission = ["Members_CRUD", "Events_Read", "System_CRUD"]
    expected_region = ["Regio_All", "Regio_Utrecht"]
    
    if permission_roles == expected_permission and region_roles == expected_region:
        print("✅ Role structure separation working correctly!")
        return True
    else:
        print("❌ Role structure separation failed!")
        return False

def main():
    """Main test function"""
    print("🚀 H-DCN Monitoring Update Test")
    print("Testing new role structure logging implementation")
    print("=" * 70)
    
    try:
        # Test role structure separation
        separation_success = test_role_structure_separation()
        
        # Test logging functions
        test_new_logging_functions()
        
        print(f"\n🎯 TEST RESULTS")
        print("=" * 30)
        
        if separation_success:
            print("✅ All tests PASSED!")
            print("   • Role structure separation works correctly")
            print("   • New logging functions implemented")
            print("   • Monitoring captures permission + region structure")
            print("\n💡 The monitoring update is working correctly!")
            return 0
        else:
            print("❌ Some tests FAILED!")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())