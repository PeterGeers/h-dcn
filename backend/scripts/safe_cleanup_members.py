#!/usr/bin/env python3
"""
Safe Member Cleanup Script
Deletes all member records EXCEPT @h-dcn.nl accounts (preserving functional accounts)
Also excludes test@h-dcn.nl as specified in migration documentation
"""

import boto3
from datetime import datetime

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def safe_cleanup_members():
    """
    Delete all member records except:
    - Accounts ending with @h-dcn.nl (functional accounts)
    - EXCEPT test@h-dcn.nl (should be deleted)
    """
    print("🧹 Starting safe member cleanup...")
    print("📋 Preserving @h-dcn.nl accounts (except test@h-dcn.nl)")
    
    # Scan all members
    scan_response = table.scan()
    all_members = scan_response['Items']
    
    # Handle pagination if needed
    while 'LastEvaluatedKey' in scan_response:
        scan_response = table.scan(ExclusiveStartKey=scan_response['LastEvaluatedKey'])
        all_members.extend(scan_response['Items'])
    
    print(f"📊 Found {len(all_members)} total member records")
    
    # Categorize members
    to_delete = []
    to_preserve = []
    
    for member in all_members:
        email = member.get('email', '').lower()
        member_id = member.get('member_id', 'unknown')
        name = member.get('name', 'Unknown')
        
        if email.endswith('@h-dcn.nl'):
            if email == 'test@h-dcn.nl':
                # Delete test account as specified
                to_delete.append({
                    'member_id': member_id,
                    'email': email,
                    'name': name,
                    'reason': 'Test account (specified for deletion)'
                })
            else:
                # Preserve functional accounts
                to_preserve.append({
                    'member_id': member_id,
                    'email': email,
                    'name': name,
                    'reason': 'Functional @h-dcn.nl account'
                })
        else:
            # Delete regular member accounts
            to_delete.append({
                'member_id': member_id,
                'email': email,
                'name': name,
                'reason': 'Regular member account'
            })
    
    print(f"\n📈 Cleanup Summary:")
    print(f"   🗑️  To Delete: {len(to_delete)}")
    print(f"   🛡️  To Preserve: {len(to_preserve)}")
    
    # Show what will be preserved
    if to_preserve:
        print(f"\n🛡️  Preserving {len(to_preserve)} functional accounts:")
        for member in to_preserve:
            print(f"   ✅ {member['email']} - {member['name']}")
    
    # Show sample of what will be deleted
    if to_delete:
        print(f"\n🗑️  Will delete {len(to_delete)} accounts (showing first 10):")
        for member in to_delete[:10]:
            print(f"   ❌ {member['email']} - {member['name']} ({member['reason']})")
        if len(to_delete) > 10:
            print(f"   ... and {len(to_delete) - 10} more")
    
    # Confirmation prompt
    print(f"\n⚠️  CONFIRMATION REQUIRED:")
    print(f"   This will DELETE {len(to_delete)} member records")
    print(f"   This will PRESERVE {len(to_preserve)} @h-dcn.nl accounts")
    
    confirmation = input("\nType 'DELETE' to confirm (case-sensitive): ")
    
    if confirmation != 'DELETE':
        print("❌ Operation cancelled - no records deleted")
        return False
    
    # Perform deletion
    print(f"\n🗑️  Deleting {len(to_delete)} records...")
    deleted_count = 0
    
    try:
        with table.batch_writer() as batch:
            for member in to_delete:
                batch.delete_item(Key={'member_id': member['member_id']})
                deleted_count += 1
                
                if deleted_count % 100 == 0:
                    print(f"   Progress: {deleted_count}/{len(to_delete)} deleted...")
        
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   🗑️  Deleted: {deleted_count} records")
        print(f"   🛡️  Preserved: {len(to_preserve)} @h-dcn.nl accounts")
        print(f"   📅 Completed at: {datetime.now().isoformat()}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during deletion: {str(e)}")
        print(f"   Deleted {deleted_count} records before error")
        return False

def verify_cleanup():
    """Verify the cleanup results"""
    print("\n🔍 Verifying cleanup results...")
    
    scan_response = table.scan()
    remaining_members = scan_response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in scan_response:
        scan_response = table.scan(ExclusiveStartKey=scan_response['LastEvaluatedKey'])
        remaining_members.extend(scan_response['Items'])
    
    print(f"📊 Remaining members: {len(remaining_members)}")
    
    hdcn_accounts = [m for m in remaining_members if m.get('email', '').endswith('@h-dcn.nl')]
    other_accounts = [m for m in remaining_members if not m.get('email', '').endswith('@h-dcn.nl')]
    
    print(f"   🛡️  @h-dcn.nl accounts: {len(hdcn_accounts)}")
    print(f"   👤 Other accounts: {len(other_accounts)}")
    
    if hdcn_accounts:
        print(f"\n🛡️  Preserved @h-dcn.nl accounts:")
        for member in hdcn_accounts:
            print(f"   ✅ {member.get('email', 'no-email')} - {member.get('name', 'Unknown')}")
    
    if other_accounts:
        print(f"\n⚠️  Unexpected remaining accounts:")
        for member in other_accounts[:5]:
            print(f"   ❓ {member.get('email', 'no-email')} - {member.get('name', 'Unknown')}")

if __name__ == "__main__":
    print("🛡️  H-DCN Safe Member Cleanup")
    print("=" * 50)
    
    success = safe_cleanup_members()
    
    if success:
        verify_cleanup()
        print(f"\n🎉 Ready for migration import!")
        print(f"💡 Next step: python import_members_sheets.py 'HDCN Ledenbestand 2026' 'Ledenbestand'")
    else:
        print(f"\n❌ Cleanup failed or cancelled")