#!/usr/bin/env python3
"""
Update all codebase references from deprecated _All roles to current simplified role structure
"""

import os
import re
import glob
from pathlib import Path

# Define the role mappings from deprecated to current
ROLE_MAPPINGS = {
    # Deprecated _All roles -> Current simplified roles
    'Members_CRUD': 'Members_CRUD',
    'Members_Read': 'Members_Read', 
    'Events_CRUD': 'Events_CRUD',
    'Events_Read': 'Events_Read',
    'Products_CRUD': 'Products_CRUD',
    'Products_Read': 'Products_Read',
    'Communication_CRUD': 'Communication_CRUD',
    'Communication_Read': 'Communication_Read',
    'Communication_Export': 'Communication_Export',
    'System_CRUD': 'System_CRUD',
    
    # Keep these as-is (they don't have _All suffix or are special)
    # 'System_User_Management': 'System_User_Management',
    # 'Members_Status_Approve': 'Members_Status_Approve',
    # 'Webshop_Management': 'Webshop_Management',
    # 'hdcnAdmins': 'hdcnAdmins',
    # 'Webmaster': 'Webmaster',
}

def find_python_files(directory='.'):
    """Find all Python files in the directory"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files

def update_file_roles(file_path):
    """Update role references in a single file"""
    try:
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
    """Update all role references in the codebase"""
    print("🔄 Updating Codebase Role References")
    print("=" * 60)
    print("Converting deprecated _All roles to current simplified role structure")
    print()
    
    # Find all Python files
    python_files = find_python_files()
    print(f"📁 Found {len(python_files)} Python files to check")
    print()
    
    # Track results
    updated_files = []
    unchanged_files = []
    error_files = []
    
    # Process each file
    for file_path in python_files:
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
    print("   1. Test updated code to ensure it works with current roles")
    print("   2. Update any remaining hardcoded role references")
    print("   3. Verify users have the current roles assigned in Cognito")
    print("   4. Update frontend code if needed")
    print("   5. Update documentation with current role structure")
    
    return len(error_files) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)