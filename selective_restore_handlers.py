"""
Selectively restore handlers:
- Restore webshop/product/cart handlers from 954ecb7 (last working version)
- Keep member/me and cognito handlers from HEAD (current, working version)
"""
import subprocess
import os

# Handlers to restore from 954ecb7 (broken in current commit)
RESTORE_FROM_954 = [
    'backend/handler/scan_product/app.py',
    'backend/handler/get_product_byid/app.py',
    'backend/handler/insert_product/app.py',
    'backend/handler/update_product/app.py',
    'backend/handler/delete_product/app.py',
    'backend/handler/create_cart/app.py',
    'backend/handler/get_cart/app.py',
    'backend/handler/clear_cart/app.py',
    'backend/handler/update_cart_items/app.py',
    'backend/handler/create_order/app.py',
    'backend/handler/get_orders/app.py',
    'backend/handler/get_order_byid/app.py',
    'backend/handler/get_customer_orders/app.py',
    'backend/handler/update_order_status/app.py',
    'backend/handler/create_payment/app.py',
    'backend/handler/get_payments/app.py',
    'backend/handler/get_payment_byid/app.py',
    'backend/handler/update_payment/app.py',
    'backend/handler/delete_payment/app.py',
    'backend/handler/create_event/app.py',
    'backend/handler/get_events/app.py',
    'backend/handler/get_event_byid/app.py',
    'backend/handler/update_event/app.py',
    'backend/handler/delete_event/app.py',
    'backend/handler/get_member_byid/app.py',
    'backend/handler/get_member_payments/app.py',
    'backend/handler/create_member/app.py',
    'backend/handler/update_member/app.py',
    'backend/handler/delete_member/app.py',
    'backend/handler/get_members/app.py',
    'backend/handler/create_membership/app.py',
    'backend/handler/get_memberships/app.py',
    'backend/handler/get_membership_byid/app.py',
    'backend/handler/update_membership/app.py',
    'backend/handler/delete_membership/app.py',
]

# Handlers to keep from HEAD (working in current commit)
KEEP_FROM_HEAD = [
    'backend/handler/get_member_self/app.py',
    'backend/handler/cognito_post_authentication/app.py',
    'backend/handler/cognito_custom_message/app.py',
    'backend/handler/cognito_post_confirmation/app.py',
    'backend/handler/hdcn_cognito_admin/app.py',
    'backend/handler/cognito_role_assignment/app.py',
    'backend/handler/export_members/app.py',
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

def main():
    print("=" * 70)
    print("SELECTIVE HANDLER RESTORATION")
    print("=" * 70)
    
    # Step 1: Restore broken handlers from 954ecb7
    print("\n📦 Restoring webshop/product handlers from 954ecb7...")
    restored_count = 0
    for filepath in RESTORE_FROM_954:
        success, message = restore_from_git(filepath, '954ecb7')
        if success:
            print(f"  ✅ {filepath}")
            restored_count += 1
        else:
            print(f"  ❌ {filepath} - {message}")
    
    print(f"\n✅ Restored {restored_count}/{len(RESTORE_FROM_954)} handlers from 954ecb7")
    
    # Step 2: Restore working handlers from HEAD
    print("\n📦 Restoring member/cognito handlers from HEAD...")
    kept_count = 0
    for filepath in KEEP_FROM_HEAD:
        success, message = restore_from_git(filepath, 'HEAD')
        if success:
            print(f"  ✅ {filepath}")
            kept_count += 1
        else:
            print(f"  ❌ {filepath} - {message}")
    
    print(f"\n✅ Kept {kept_count}/{len(KEEP_FROM_HEAD)} handlers from HEAD")
    
    print("\n" + "=" * 70)
    print("✅ DONE!")
    print("=" * 70)
    print("\nSummary:")
    print(f"  - Restored {restored_count} webshop handlers from 954ecb7")
    print(f"  - Kept {kept_count} member/cognito handlers from HEAD")
    print("\nNext: Deploy with backend-build-and-deploy-fast.ps1")

if __name__ == '__main__':
    main()
