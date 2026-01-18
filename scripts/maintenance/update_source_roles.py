#!/usr/bin/env python3
"""
Update role references in source files only (exclude build directories)
"""

import os
import re

# Define the role mappings from deprecated to current
# NOTE: These deprecated _All roles have been removed from production
# This script is for reference/migration purposes only
ROLE_MAPPINGS = {
    # DEPRECATED ROLES - REMOVED FROM PRODUCTION
    'Members_CRUD_All': 'Members_CRUD',
    'Members_Read_All': 'Members_Read', 
    'Members_Export_All': 'Members_Export',
    'Events_CRUD_All': 'Events_CRUD',
    'Events_Read_All': 'Events_Read',
    'Events_Export_All': 'Events_Export',
    'Products_CRUD_All': 'Products_CRUD',
    'Products_Read_All': 'Products_Read',
    'Products_Export_All': 'Products_Export',
    'Communication_CRUD_All': 'Communication_CRUD',
    'Communication_Read_All': 'Communication_Read',
    'Communication_Export_All': 'Communication_Export',
    'System_CRUD_All': 'System_CRUD',
}

# Files to update (specific source files only)
TARGET_FILES = [
    'backend/shared/auth_utils.py',
    'backend/handler/generate_member_parquet/app.py',
    'backend/handler/download_parquet/app.py',
    'backend/handler/update_product/app.py',
    'backend/handler/update_member/app.py',
    'backend/handler/update_order_status/app.py',
    'backend/handler/update_payment/app.py',
    'backend/handler/s3_file_manager/app.py',
    'backend/handler/hdcn_cognito_admin/app.py',
    'backend/handler/hdcn_cognito_admin/role_permissions.py',
    'backend/handler/update_member/role_permissions.py',
    'backend/test_passwordless_chairman.py',
    'backend/test_passwordless_member_admin.py',
    'backend/test_passwordless_webmaster.py',
    'backend/test_member_admin_login.py',
    'backend/test_member_admin_simple.py',
    'backend/verify_role_assignments.py',
    'backend/create_test_users.py',
]

# Auth fallback files pattern
AUTH_FALLBACK_PATTERN = 'backend/handler/*/auth_fallback.py'

def find_auth_fallback_files():
    """Find all auth_fallback.py files"""
    import glob
    return glob.glob(AUTH_FALLBACK_PATTERN)

def update_file_roles(file_path):
    """Update role references in a single file"""
    try:
        if not os.path.exists(file_path):
            return False, [f"File not found: {file_path}"]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Replace each deprecated role with current role
        for old_role, new_role in ROLE_MAPPINGS.items():
            # Pattern to match the deprecated role name (with word boundaries)
            pattern = r'\b' + re.escape(old_role) + r'\b'
            
            if re.search(pattern, content):
                content = re.sub(pattern, new_role, content)
                changes_made.append(f"{old_role} -> {new_role}")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes_made
        
        return False, []
        
    except Exception as e:
        return False, [f"Error: {str(e)}"]

def main():
    """Update role references in source files"""
    print("🔄 Updating Source File Role References")
    print("=" * 60)
    print("Converting deprecated _All roles to current simplified role structure")
    print()
    
    # Get all target files
    all_files = TARGET_FILES.copy()
    
    # Add auth_fallback files
    auth_fallback_files = find_auth_fallback_files()
    all_files.extend(auth_fallback_files)
    
    print(f"📁 Found {len(all_files)} source files to update")
    print()
    
    # Track results
    updated_files = []
    unchanged_files = []
    error_files = []
    
    # Process each file
    for file_path in all_files:
        print(f"🔍 Checking: {file_path}")
        
        success, changes = update_file_roles(file_path)
        
        if success and changes:
            updated_files.append((file_path, changes))
            print(f"   ✅ Updated: {len(changes)} changes")
            for change in changes:
                print(f"      • {change}")
        elif success:
            unchanged_files.append(file_path)
            print(f"   ℹ️  No changes needed")
        else:
            error_files.append((file_path, changes))
            print(f"   ❌ Error: {changes}")
        
        print()
    
    # Summary
    print("📊 UPDATE SUMMARY")
    print("=" * 60)
    
    print(f"✅ Files updated: {len(updated_files)}")
    if updated_files:
        for file_path, changes in updated_files:
            print(f"   📄 {file_path}")
            for change in changes:
                print(f"      • {change}")
        print()
    
    print(f"ℹ️  Files unchanged: {len(unchanged_files)}")
    if unchanged_files:
        for file_path in unchanged_files[:5]:  # Show first 5
            print(f"   📄 {file_path}")
        if len(unchanged_files) > 5:
            print(f"   ... and {len(unchanged_files) - 5} more")
        print()
    
    print(f"❌ Files with errors: {len(error_files)}")
    if error_files:
        for file_path, errors in error_files:
            print(f"   📄 {file_path}")
            for error in errors:
                print(f"      • {error}")
        print()
    
    # Role mapping summary
    print("🔄 ROLE MAPPINGS APPLIED:")
    for old_role, new_role in ROLE_MAPPINGS.items():
        print(f"   • {old_role} → {new_role}")
    
    print()
    print("💡 NEXT STEPS:")
    print("   1. Test updated backend handlers")
    print("   2. Deploy updated functions to AWS")
    print("   3. Verify authentication works with current roles")
    print("   4. Update any remaining test files if needed")
    
    return len(error_files) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)