"""
Restore truncated handlers from git and fix the fallback pattern
"""
import subprocess
import os

# List of truncated handlers (under 50 lines)
TRUNCATED_HANDLERS = [
    'backend/handler/get_member_byid/app.py',
    'backend/handler/get_member_payments/app.py',
    'backend/handler/get_payment_byid/app.py',
    'backend/handler/get_payments/app.py',
    'backend/handler/get_order_byid/app.py',
    'backend/handler/delete_payment/app.py',
    'backend/handler/get_orders/app.py',
    'backend/handler/get_customer_orders/app.py',
    'backend/handler/update_cart_items/app.py',
    'backend/handler/scan_product/app.py',
    'backend/handler/create_cart/app.py',
    'backend/handler/get_cart/app.py',
    'backend/handler/update_payment/app.py',
    'backend/handler/delete_product/app.py',
    'backend/handler/delete_event/app.py',
    'backend/handler/create_payment/app.py',
    'backend/handler/update_event/app.py',
    'backend/handler/update_order_status/app.py',
    'backend/handler/update_product/app.py',
    'backend/handler/create_order/app.py',
    'backend/handler/get_product_byid/app.py',
    'backend/handler/insert_product/app.py',
    'backend/handler/create_member/app.py',
    'backend/handler/create_event/app.py',
]

# Handlers that are working and should NOT be restored (only fix sys.exit)
WORKING_HANDLERS = [
    'backend/handler/get_member_self/app.py',
    'backend/handler/cognito_post_authentication/app.py',
    'backend/handler/cognito_custom_message/app.py',
    'backend/handler/cognito_post_confirmation/app.py',
]

def restore_from_git(filepath, commit='954ecb7'):
    """Restore a file from a git commit"""
    try:
        result = subprocess.run(
            ['git', 'show', f'{commit}:{filepath}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        return True, "Restored"
    except subprocess.CalledProcessError as e:
        return False, f"Git error: {e.stderr}"
    except Exception as e:
        return False, str(e)

def remove_sys_exit(filepath):
    """Remove sys.exit(0) from a handler file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'sys.exit(0)' not in content:
            return True, "No sys.exit found"
        
        # Remove the sys.exit block
        lines = content.split('\n')
        new_lines = []
        skip_next = 0
        
        for i, line in enumerate(lines):
            if skip_next > 0:
                skip_next -= 1
                continue
            
            if 'sys.exit(0)' in line:
                # Also remove the "import sys" line before it
                if i > 0 and 'import sys' in lines[i-1]:
                    new_lines.pop()  # Remove the import sys line we just added
                # Also remove the comment line before that
                if len(new_lines) > 0 and 'Exit early' in new_lines[-1]:
                    new_lines.pop()
                continue
            
            new_lines.append(line)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        return True, "Removed sys.exit"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("RESTORING AND FIXING LAMBDA HANDLERS")
    print("=" * 60)
    
    # Step 1: Restore truncated handlers
    print("\n📦 Step 1: Restoring truncated handlers from git commit 954ecb7...")
    restored_count = 0
    for filepath in TRUNCATED_HANDLERS:
        success, message = restore_from_git(filepath)
        if success:
            print(f"  ✅ Restored: {filepath}")
            restored_count += 1
        else:
            print(f"  ❌ Failed: {filepath} - {message}")
    
    print(f"\n✅ Restored {restored_count}/{len(TRUNCATED_HANDLERS)} truncated handlers")
    
    # Step 2: Remove sys.exit from ALL handlers (including working ones)
    print("\n🔧 Step 2: Removing sys.exit(0) from all handlers...")
    all_handlers = TRUNCATED_HANDLERS + WORKING_HANDLERS
    fixed_count = 0
    
    for filepath in all_handlers:
        if os.path.exists(filepath):
            success, message = remove_sys_exit(filepath)
            if success:
                print(f"  ✅ Fixed: {filepath} - {message}")
                fixed_count += 1
            else:
                print(f"  ❌ Failed: {filepath} - {message}")
    
    print(f"\n✅ Fixed {fixed_count}/{len(all_handlers)} handlers")
    
    print("\n" + "=" * 60)
    print("✅ DONE! Handlers restored and fixed")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the changes with: git diff backend/handler")
    print("2. Test locally if possible")
    print("3. Deploy with: .\\scripts\\deployment\\backend-build-and-deploy-fast.ps1")

if __name__ == '__main__':
    main()
