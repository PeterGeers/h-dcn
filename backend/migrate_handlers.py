#!/usr/bin/env python3
"""
Handler Migration Script
Automatically updates handlers from old _All roles to new permission + region structure
"""

import os
import sys
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir / 'shared'))

from auth_utils import (
    update_auth_fallback_file,
    create_handler_migration_template,
    get_new_role_structure_mapping
)

def find_handlers_with_old_roles():
    """Find all handlers that reference old _All roles"""
    handlers_dir = backend_dir / 'handler'
    broken_handlers = []
    
    # NOTE: These deprecated _All roles have been removed from production
    # This script is for migration reference purposes only
    old_roles = [
        # DEPRECATED ROLES - REMOVED FROM PRODUCTION
        'Members_CRUD', 'Members_Read', 'Members_Export',
        'Events_CRUD', 'Events_Read', 'Events_Export',
        'Products_CRUD', 'Products_Read', 'Products_Export',
        'Communication_CRUD', 'Communication_Read', 'Communication_Export'
    ]
    
    for handler_dir in handlers_dir.iterdir():
        if handler_dir.is_dir():
            # Check app.py for old role references
            app_py = handler_dir / 'app.py'
            if app_py.exists():
                try:
                    with open(app_py, 'r', encoding='utf-8') as f:
                        content = f.read()
                        found_roles = [role for role in old_roles if role in content]
                        if found_roles:
                            broken_handlers.append({
                                'handler': handler_dir.name,
                                'path': str(handler_dir),
                                'old_roles_found': found_roles
                            })
                except UnicodeDecodeError:
                    print(f"Warning: Could not read {app_py} due to encoding issues")
            
            # Check auth_fallback.py for old role references
            auth_fallback = handler_dir / 'auth_fallback.py'
            if auth_fallback.exists():
                try:
                    with open(auth_fallback, 'r', encoding='utf-8') as f:
                        content = f.read()
                        found_roles = [role for role in old_roles if role in content]
                        if found_roles:
                            # Add to existing entry or create new one
                            existing = next((h for h in broken_handlers if h['handler'] == handler_dir.name), None)
                            if existing:
                                existing['auth_fallback_roles'] = found_roles
                            else:
                                broken_handlers.append({
                                    'handler': handler_dir.name,
                                    'path': str(handler_dir),
                                    'auth_fallback_roles': found_roles
                                })
                except UnicodeDecodeError:
                    print(f"Warning: Could not read {auth_fallback} due to encoding issues")
    
    return broken_handlers

def migrate_handler(handler_info):
    """Migrate a single handler"""
    print(f"\nMigrating handler: {handler_info['handler']}")
    
    # Update auth_fallback.py
    result = update_auth_fallback_file(handler_info['path'])
    if result['success']:
        print(f"  Updated auth_fallback.py")
        for change in result['changes_made']:
            print(f"    - {change}")
        print(f"  Backup created: {result['backup_created']}")
    else:
        print(f"  Failed to update auth_fallback.py: {result.get('error', 'Unknown error')}")
    
    # Generate migration template for app.py
    old_roles = handler_info.get('old_roles_found', [])
    if old_roles:
        template = create_handler_migration_template(handler_info['handler'], old_roles)
        template_path = os.path.join(handler_info['path'], f"{handler_info['handler']}_migration_template.py")
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"  Created migration template: {template_path}")
        print(f"    Old roles: {old_roles}")
    
    return result

def main():
    """Main migration function"""
    print("Starting Handler Migration Process")
    print("=" * 50)
    
    # Find broken handlers
    broken_handlers = find_handlers_with_old_roles()
    
    if not broken_handlers:
        print("No handlers found with old role references!")
        return
    
    print(f"Found {len(broken_handlers)} handlers that need migration:")
    for handler in broken_handlers:
        print(f"  - {handler['handler']}: {handler.get('old_roles_found', [])} {handler.get('auth_fallback_roles', [])}")
    
    print("\n" + "=" * 50)
    
    # Migrate each handler
    results = []
    for handler_info in broken_handlers:
        result = migrate_handler(handler_info)
        results.append({
            'handler': handler_info['handler'],
            'success': result['success'],
            'changes': result.get('changes_made', [])
        })
    
    # Summary
    print("\n" + "=" * 50)
    print("Migration Summary:")
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"  Successfully migrated: {len(successful)}")
    print(f"  Failed migrations: {len(failed)}")
    
    if successful:
        print("\n  Successful migrations:")
        for result in successful:
            print(f"    - {result['handler']}")
    
    if failed:
        print("\n  Failed migrations:")
        for result in failed:
            print(f"    - {result['handler']}")
    
    print("\nNext Steps:")
    print("  1. Review the migration templates created for each handler")
    print("  2. Update the app.py files using the templates as guides")
    print("  3. Test each handler with the new role structure")
    print("  4. Remove the migration templates once migration is complete")

if __name__ == '__main__':
    main()