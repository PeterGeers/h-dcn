#!/usr/bin/env python3
"""
Fix test@h-dcn.nl fallback emails in the database
Remove the email field entirely for members with test@h-dcn.nl
"""

import boto3
from boto3.dynamodb.conditions import Attr

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def fix_test_emails():
    """Remove test@h-dcn.nl fallback emails from the database"""
    print("🔍 Scanning for members with test@h-dcn.nl emails...")
    
    # Scan for members with email = 'test@h-dcn.nl'
    response = table.scan(
        FilterExpression=Attr('email').eq('test@h-dcn.nl')
    )
    
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Attr('email').eq('test@h-dcn.nl'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])
    
    print(f"📋 Found {len(items)} members with test@h-dcn.nl email")
    
    if len(items) == 0:
        print("✅ No members found with test@h-dcn.nl email - nothing to fix!")
        return
    
    # Show some examples
    print(f"\n📝 Examples of members to fix:")
    for i, item in enumerate(items[:10]):
        name = item.get('name', 'Unknown')
        member_id = item.get('member_id', 'Unknown')
        print(f"   {i+1}. {name} (ID: {member_id[:8]}...)")
    
    if len(items) > 10:
        print(f"   ... and {len(items) - 10} more")
    
    # Confirm before proceeding
    response = input(f"\n⚠️  Remove email field from {len(items)} members with test@h-dcn.nl? (y/N): ")
    if response.lower() != 'y':
        print("❌ Operation cancelled")
        return
    
    # Update records - REMOVE the email field entirely
    updated_count = 0
    error_count = 0
    
    print(f"\n🔧 Removing email fields...")
    
    for item in items:
        try:
            member_id = item['member_id']
            name = item.get('name', 'Unknown')
            
            # Remove the email field entirely
            table.update_item(
                Key={'member_id': member_id},
                UpdateExpression='REMOVE email SET updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':updated_at': '2026-01-06T18:30:00'  # Mark when we fixed it
                }
            )
            
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"   Updated {updated_count} records...")
            
            if updated_count <= 5:  # Show first 5 updates
                print(f"   ✅ Removed email from: {name}")
                
        except Exception as e:
            print(f"❌ Error updating {member_id}: {str(e)}")
            error_count += 1
    
    print(f"\n🎉 Update completed!")
    print(f"✅ Updated: {updated_count} members")
    print(f"❌ Errors: {error_count}")
    
    if updated_count > 0:
        print(f"\n📊 All test@h-dcn.nl emails have been removed")
        print(f"🕒 Updated timestamp set to: 2026-01-06T18:30:00")
        print(f"📋 These members now have no email field (as intended)")

if __name__ == "__main__":
    fix_test_emails()