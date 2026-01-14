"""
Update handlers to use maintenance_fallback pattern
This replaces the non-existent local auth_fallback.py imports with shared.maintenance_fallback
"""
import os
import re

# Handlers to update (33 webshop handlers that use auth_fallback)
HANDLERS_TO_UPDATE = [
    'clear_cart',
    'create_cart',
    'create_event',
    'create_member',
    'create_order',
    'create_payment',
    'delete_event',
    'delete_payment',
    'delete_product',
    'get_cart',
    'get_customer_orders',
    'get_events',
    'get_event_byid',
    'get_member_byid',
    'get_member_payments',
    'get_members',
    'get_order_byid',
    'get_orders',
    'get_payment_byid',
    'get_payments',
    'get_product_byid',
    'insert_product',
    'scan_product',
    'update_cart_items',
    'update_event',
    'update_order_status',
    'update_payment',
    'update_product',
    's3_file_manager',
    'create_member',
    'delete_member',
    'update_member',
    'create_order'
]

def update_handler_file(handler_name):
    """Update a single handler file to use maintenance_fallback"""
    filepath = f'backend/handler/{handler_name}/app.py'
    
    if not os.path.exists(filepath):
        print(f"⚠️  Skipping {handler_name} - file not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if it already uses maintenance_fallback
    if 'from shared.maintenance_fallback import' in content:
        print(f"✅ {handler_name} - already uses maintenance_fallback")
        return True
    
    # Check if it uses auth_fallback
    if 'from auth_fallback import' not in content:
        print(f"⚠️  {handler_name} - doesn't use auth_fallback pattern")
        return True
    
    # Find the except ImportError block and replace everything until the next blank line or code
    # Pattern matches: except ImportError: ... from auth_fallback import (...) ... print(...)
    pattern = r'(except ImportError:.*?)(print\(["\']Using fallback auth[^)]*\))'
    
    # New maintenance_fallback pattern
    replacement = f'''except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {{str(e)}}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("{handler_name}")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)'''
    
    # Replace the pattern
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        print(f"❌ {handler_name} - pattern not matched, manual review needed")
        return False
    
    # Write the updated content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ {handler_name} - updated to maintenance_fallback")
    return True

def main():
    """Update all handlers"""
    print("🔄 Updating handlers to use maintenance_fallback pattern...")
    print("=" * 60)
    
    # Remove duplicates from the list
    handlers = list(set(HANDLERS_TO_UPDATE))
    handlers.sort()
    
    updated = 0
    skipped = 0
    failed = 0
    
    for handler in handlers:
        result = update_handler_file(handler)
        if result:
            updated += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   ✅ Updated: {updated}")
    print(f"   ❌ Failed: {failed}")
    
    if failed > 0:
        print(f"\n⚠️  Some handlers need manual review")
        return 1
    else:
        print(f"\n✅ All handlers updated successfully!")
        return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
