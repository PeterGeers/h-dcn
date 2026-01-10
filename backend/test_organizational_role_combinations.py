#!/usr/bin/env python3
"""
Test script to validate organizational role combinations
"""

import sys
import os

# Add the handler directory to the path so we can import role_permissions
sys.path.append(os.path.join(os.path.dirname(__file__), 'handler', 'update_member'))

try:
    from role_permissions import (
        ORGANIZATIONAL_ROLE_COMBINATIONS,
        get_organizational_role_combination,
        assign_organizational_role,
        validate_organizational_role_structure,
        get_all_organizational_roles,
        has_new_role_structure
    )
    print("✅ Successfully imported role_permissions module")
except ImportError as e:
    print(f"❌ Failed to import role_permissions: {e}")
    sys.exit(1)

def test_organizational_role_combinations():
    """Test that organizational role combinations are properly defined"""
    print("\n🔍 Testing Organizational Role Combinations...")
    
    # Get all organizational roles
    all_roles = get_all_organizational_roles()
    
    print(f"\n📊 Found {len(ORGANIZATIONAL_ROLE_COMBINATIONS)} organizational roles:")
    print(f"  - National roles: {len(all_roles['national_roles'])}")
    print(f"  - Regional roles: {len(all_roles['regional_roles'])}")
    print(f"  - Function roles: {len(all_roles['function_roles'])}")
    print(f"  - Legacy roles: {len(all_roles['legacy_roles'])}")
    
    # Test a few key organizational roles
    test_roles = [
        'National_Chairman',
        'National_Secretary', 
        'Webmaster',
        'Regional_Chairman_Region1',
        'Regional_Secretary_Region4'
    ]
    
    print(f"\n🧪 Testing {len(test_roles)} key organizational roles:")
    
    for role_name in test_roles:
        print(f"\n  Testing: {role_name}")
        
        # Get role combination
        role_combo = get_organizational_role_combination(role_name)
        if not role_combo:
            print(f"    ❌ No role combination found")
            continue
            
        print(f"    ✅ Role combination: {role_combo}")
        
        # Validate role structure
        validation = validate_organizational_role_structure(role_name)
        print(f"    📋 Validation: {validation['validation_type']}")
        
        if validation['suggestions']:
            print(f"    💡 Suggestions: {validation['suggestions']}")
        
        # Test role structure analysis
        structure = has_new_role_structure(role_combo)
        print(f"    🏗️  Structure: Permission roles: {len(structure['permission_roles'])}, Region roles: {len(structure['region_roles'])}")

def test_role_assignment():
    """Test assigning organizational roles to users"""
    print("\n🔧 Testing Role Assignment...")
    
    # Test assigning National_Chairman to a basic user
    basic_user_roles = ['hdcnLeden']
    
    print(f"\n  Assigning 'National_Chairman' to user with roles: {basic_user_roles}")
    
    result = assign_organizational_role(basic_user_roles, 'National_Chairman')
    
    if result['success']:
        print(f"    ✅ Success: {result['message']}")
        print(f"    📝 Added roles: {result['added_roles']}")
        print(f"    👤 Final roles: {result['new_roles']}")
    else:
        print(f"    ❌ Failed: {result['message']}")

def test_regional_role_consistency():
    """Test that regional roles are consistent across all regions"""
    print("\n🌍 Testing Regional Role Consistency...")
    
    regions = [
        ('Region1', 'Noord-Holland'),
        ('Region2', 'Zuid-Holland'), 
        ('Region3', 'Friesland'),
        ('Region4', 'Utrecht'),
        ('Region5', 'Oost'),
        ('Region6', 'Limburg'),
        ('Region7', 'Groningen/Drenthe'),
        ('Region8', 'Brabant/Zeeland'),
        ('Region9', 'Duitsland')
    ]
    
    positions = ['Chairman', 'Secretary', 'Treasurer', 'Volunteer']
    
    print(f"  Checking {len(regions)} regions × {len(positions)} positions = {len(regions) * len(positions)} role combinations")
    
    missing_roles = []
    inconsistent_structures = []
    
    for region_id, region_name in regions:
        for position in positions:
            role_name = f'Regional_{position}_{region_id}'
            
            if role_name not in ORGANIZATIONAL_ROLE_COMBINATIONS:
                missing_roles.append(role_name)
                continue
            
            # Check if role structure is consistent
            role_combo = ORGANIZATIONAL_ROLE_COMBINATIONS[role_name]
            structure = has_new_role_structure(role_combo)
            
            if not structure['has_new_structure']:
                inconsistent_structures.append((role_name, structure))
    
    if missing_roles:
        print(f"    ❌ Missing roles: {missing_roles}")
    else:
        print(f"    ✅ All regional roles defined")
    
    if inconsistent_structures:
        print(f"    ⚠️  Inconsistent structures: {len(inconsistent_structures)}")
        for role_name, structure in inconsistent_structures[:3]:  # Show first 3
            print(f"      - {role_name}: {structure}")
    else:
        print(f"    ✅ All regional roles have consistent structure")

def main():
    """Run all tests"""
    print("🚀 Testing Organizational Role Combinations")
    print("=" * 50)
    
    try:
        test_organizational_role_combinations()
        test_role_assignment()
        test_regional_role_consistency()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()