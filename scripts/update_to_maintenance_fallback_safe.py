"""
Safely update handlers to use maintenance_fallback pattern
Uses exact string matching for safety
"""
import os
import subprocess

# Handlers that need updating
HANDLERS = [
    'clear_cart', 'create_cart', 'create_event', 'create_member', 'create_order',
    'create_payment', 'delete_event', 'delete_payment', 'delete_product',
    'get_cart', 'get_customer_orders', 'get_events', 'get_event_byid',
    'get_member_byid', 'get_member_payments', 'get_members',
    'get_order_byid', 'get_orders', 'get_payment_byid', 'get_payments',
    'get_product_byid', 'insert_product', 'scan_product',
    'update_cart_items', 'update_event', 'update_order_status',
    'update_payment', 'update_product', 's3_file_manager'
]

def update_handler(handler_name):
    """Update a single handler using string replacement"""
    filepath = f'backend/handler/{handler_name}/app.py'
    
    if not os.path.exists(filepath):
        print(f"⚠️  {handler_name} - file not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already updated
    if 'from shared.maintenance_fallback import' in content:
        print(f"✅ {handler_name} - already uses maintenance_fallback")
        return True
    
    # Check if uses auth_fallback
    if 'from auth_fallback import' not in content:
        print(f"⚠️  {handler_name} - doesn't use auth_fallback")
        return True
    
    # Find the old pattern - there are variations
    old_patterns = [
        # Pattern 1: With comment about NEW ROLE STRUCTURE
        '''except ImportError:
    # Fallback to local auth_fallback.py (UPDATED FOR NEW ROLE STRUCTURE)
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")''',
        
        # Pattern 2: Without NEW ROLE STRUCTURE comment
        '''except ImportError:
    # Fallback to local auth_fallback.py
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")''',
        
        # Pattern 3: Different print message
        '''except ImportError:
    # Fallback to local auth_fallback.py if shared module not available
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")''',
    ]
    
    # New pattern
    new_pattern = f'''except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {{str(e)}}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("{handler_name}")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)'''
    
    # Try each pattern
    updated = False
    for old_pattern in old_patterns:
        if old_pattern in content:
            new_content = content.replace(old_pattern, new_pattern)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ {handler_name} - updated successfully")
            updated = True
            break
    
    if not updated:
        print(f"❌ {handler_name} - pattern not found, needs manual review")
        # Show what we're looking for
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'except ImportError' in line:
                    print(f"   Found at line {i+1}: {line.strip()}")
                    # Show next 10 lines
                    for j in range(i+1, min(i+11, len(lines))):
                        print(f"   {j+1}: {lines[j].rstrip()}")
                    break
        return False
    
    return True

def main():
    """Update all handlers"""
    print("🔄 Updating handlers to maintenance_fallback pattern...")
    print("=" * 60)
    
    updated = 0
    failed = 0
    
    for handler in HANDLERS:
        if update_handler(handler):
            updated += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   ✅ Updated/Already OK: {updated}")
    print(f"   ❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n⚠️  Some handlers need manual review")
        print(f"💡 Run validation to check for issues:")
        print(f"   python scripts/validate_all.py")
        return 1
    else:
        print(f"\n✅ All handlers processed successfully!")
        print(f"\n🔍 Running validation checks...")
        result = subprocess.run(['python', 'scripts/validate_all.py'])
        return result.returncode

if __name__ == '__main__':
    import sys
    sys.exit(main())
