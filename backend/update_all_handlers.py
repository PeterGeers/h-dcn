#!/usr/bin/env python3
"""
Script to update all Lambda handlers with consistent authentication
"""

import os
import shutil

# Standard auth import block that all handlers should use
AUTH_IMPORT_BLOCK = '''
# Import shared authentication utilities
import sys
sys.path.append('/opt/python')  # Lambda layer path
sys.path.append('../../shared')  # Local development path
try:
    from shared.auth_utils import (
        extract_user_credentials, validate_permissions, cors_headers, 
        handle_options_request, log_successful_access, create_error_response, create_success_response
    )
except ImportError:
    try:
        from auth_fallback import (
            extract_user_credentials, validate_permissions, cors_headers, 
            handle_options_request, log_successful_access, create_error_response, create_success_response
        )
    except ImportError:
        print("ERROR: No auth module available")
        raise
'''

# Standard auth check block for handlers
AUTH_CHECK_BLOCK = '''
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions (customize required_permissions per handler)
        has_permission, permission_error = validate_permissions(
            user_roles, 
            {required_permissions},
            user_email,
            {{'operation': '{operation}', 'resource_type': '{resource_type}'}}
        )
        if not has_permission:
            return permission_error
        
        # Log successful access
        log_successful_access(user_email, user_roles, '{operation}')
'''

def copy_auth_fallback_to_handler(handler_path):
    """Copy auth_fallback.py to handler directory"""
    fallback_source = 'shared/auth_fallback.py'
    fallback_dest = os.path.join(handler_path, 'auth_fallback.py')
    
    if os.path.exists(fallback_source):
        shutil.copy2(fallback_source, fallback_dest)
        print(f"Copied auth_fallback.py to {handler_path}")
    else:
        print(f"Warning: {fallback_source} not found")

def get_handler_directories():
    """Get all handler directories"""
    handler_base = 'handler'
    if not os.path.exists(handler_base):
        print(f"Handler directory {handler_base} not found")
        return []
    
    handlers = []
    for item in os.listdir(handler_base):
        item_path = os.path.join(handler_base, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, 'app.py')):
            handlers.append(item_path)
    
    return handlers

def main():
    """Update all handlers with consistent auth"""
    print("🔧 Updating all Lambda handlers with consistent authentication...")
    
    handlers = get_handler_directories()
    print(f"Found {len(handlers)} handlers to update")
    
    for handler_path in handlers:
        print(f"\n📁 Processing {handler_path}...")
        
        # Copy auth fallback to each handler
        copy_auth_fallback_to_handler(handler_path)
        
        # Note: Actual code modification would require more complex parsing
        # For now, we'll copy the fallback and handlers can be updated manually
        # with the standard patterns shown above
    
    print("\n✅ Auth fallback copied to all handlers")
    print("📝 Next: Update each handler's app.py to use the standard auth pattern")

if __name__ == "__main__":
    main()