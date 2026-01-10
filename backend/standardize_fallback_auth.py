#!/usr/bin/env python3
"""
Standardize Fallback Authentication Script
Ensures all auth_fallback.py files use the same standardized implementation

This script:
1. Copies the standardized template to all handler directories
2. Creates backups of existing files
3. Ensures consistent fallback behavior across all handlers
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def find_all_handler_directories():
    """Find all handler directories that should have auth_fallback.py files"""
    handlers_dir = Path("backend/handler")
    handler_dirs = []
    
    if not handlers_dir.exists():
        print(f"❌ Handler directory not found: {handlers_dir}")
        return []
    
    for item in handlers_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            handler_dirs.append(item)
    
    return sorted(handler_dirs)


def backup_existing_file(file_path):
    """Create a backup of existing auth_fallback.py file"""
    if not file_path.exists():
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_suffix(f'.py.backup_{timestamp}')
    
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"⚠️ Failed to create backup for {file_path}: {e}")
        return None


def copy_standardized_template(handler_dir):
    """Copy the standardized template to a handler directory"""
    template_path = Path("backend/shared/auth_fallback_template.py")
    target_path = handler_dir / "auth_fallback.py"
    
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}")
        return False
    
    try:
        # Create backup if file exists
        backup_path = None
        if target_path.exists():
            backup_path = backup_existing_file(target_path)
        
        # Copy template
        shutil.copy2(template_path, target_path)
        
        # Update the header comment to be handler-specific
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace template header with handler-specific header
        handler_name = handler_dir.name
        updated_content = content.replace(
            'STANDARDIZED Fallback Authentication Module Template',
            f'Fallback authentication module for {handler_name} handler'
        ).replace(
            'This template ensures consistent auth behavior across all handlers',
            'This ensures consistent auth behavior when shared modules aren\'t available'
        )
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        return {
            'success': True,
            'backup_created': backup_path,
            'target_path': target_path
        }
        
    except Exception as e:
        print(f"❌ Failed to copy template to {handler_dir}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def validate_auth_fallback_file(file_path):
    """Validate that an auth_fallback.py file has the required functions"""
    required_functions = [
        'extract_user_credentials',
        'validate_permissions',
        'validate_permissions_with_regions',
        'determine_regional_access',
        'cors_headers',
        'handle_options_request',
        'create_error_response',
        'create_success_response',
        'log_successful_access',
        'require_auth_and_permissions'
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_functions = []
        for func in required_functions:
            if f"def {func}(" not in content:
                missing_functions.append(func)
        
        return {
            'valid': len(missing_functions) == 0,
            'missing_functions': missing_functions,
            'has_standardized_constants': 'SYSTEM_ADMIN_ROLES' in content,
            'has_version_info': 'FALLBACK_AUTH_VERSION' in content
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }


def main():
    """Main standardization function"""
    print("🚀 Starting Fallback Authentication Standardization")
    print("=" * 60)
    
    # Find all handler directories
    handler_dirs = find_all_handler_directories()
    
    if not handler_dirs:
        print("❌ No handler directories found!")
        return
    
    print(f"Found {len(handler_dirs)} handler directories")
    
    # Process each handler directory
    results = []
    for handler_dir in handler_dirs:
        print(f"\n🔧 Processing: {handler_dir.name}")
        
        # Copy standardized template
        result = copy_standardized_template(handler_dir)
        
        if result['success']:
            # Validate the copied file
            validation = validate_auth_fallback_file(handler_dir / "auth_fallback.py")
            
            result.update({
                'handler': handler_dir.name,
                'validation': validation
            })
            
            if validation['valid']:
                print(f"  ✅ Successfully standardized auth_fallback.py")
                if result['backup_created']:
                    print(f"  💾 Backup created: {result['backup_created'].name}")
                if validation['has_version_info']:
                    print(f"  📋 Version info included")
            else:
                print(f"  ⚠️ Validation issues: {validation.get('missing_functions', [])}")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
            result['handler'] = handler_dir.name
        
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Standardization Summary:")
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    print(f"  ✅ Successfully standardized: {len(successful)}")
    print(f"  ❌ Failed standardizations: {len(failed)}")
    
    if successful:
        print("\n  ✅ Successfully standardized handlers:")
        for result in successful:
            validation = result.get('validation', {})
            status = "✓" if validation.get('valid', False) else "⚠"
            print(f"    {status} {result['handler']}")
    
    if failed:
        print("\n  ❌ Failed handlers:")
        for result in failed:
            print(f"    ✗ {result['handler']}: {result.get('error', 'Unknown error')}")
    
    print("\n🎯 Standardization Complete!")
    print("All auth_fallback.py files now use the same standardized implementation.")
    print("This ensures consistent fallback behavior across all handlers.")
    
    # Additional validation summary
    valid_files = [r for r in successful if r.get('validation', {}).get('valid', False)]
    print(f"\n📋 Validation Summary:")
    print(f"  • Files with all required functions: {len(valid_files)}")
    print(f"  • Files with version info: {len([r for r in successful if r.get('validation', {}).get('has_version_info', False)])}")
    print(f"  • Files with standardized constants: {len([r for r in successful if r.get('validation', {}).get('has_standardized_constants', False)])}")


if __name__ == '__main__':
    main()