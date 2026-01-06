#!/usr/bin/env python3
"""
Fix incorrect region values in the database
Change "Other" to "Overig" to match memberFields.ts
"""

import boto3
from boto3.dynamodb.conditions import Attr

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def fix_region_values():
    """Fix incorrect 'Other' region values to 'Overig'"""
    print("🔍 Scanning for members with 'Other' region...")
    
    # Scan for members with regio = 'Other'
    response = table.scan(
        FilterExpression=Attr('regio').eq('Other')
    )
    
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Attr('regio').eq('Other'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])
    
    print(f"📋 Found {len(items)} members with 'Other' region")
    
    if len(items) == 0:
        print("✅ No members found with 'Other' region - nothing to fix!")
        return
    
    # Show some examples
    print(f"\n📝 Examples of members to fix:")
    for i, item in enumerate(items[:5]):
        name = item.get('name', 'Unknown')
        member_id = item.get('member_id', 'Unknown')
        print(f"   {i+1}. {name} (ID: {member_id[:8]}...)")
    
    if len(items) > 5:
        print(f"   ... and {len(items) - 5} more")
    
    # Confirm before proceeding
    response = input(f"\n⚠️  Fix {len(items)} members by changing 'Other' → 'Overig'? (y/N): ")
    if response.lower() != 'y':
        print("❌ Operation cancelled")
        return
    
    # Update records
    updated_count = 0
    error_count = 0
    
    print(f"\n🔧 Updating records...")
    
    for item in items:
        try:
            member_id = item['member_id']
            
            # Update the region
            table.update_item(
                Key={'member_id': member_id},
                UpdateExpression='SET regio = :new_regio, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':new_regio': 'Overig',
                    ':updated_at': '2026-01-06T18:00:00'  # Mark when we fixed it
                }
            )
            
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"   Updated {updated_count} records...")
                
        except Exception as e:
            print(f"❌ Error updating {member_id}: {str(e)}")
            error_count += 1
    
    print(f"\n🎉 Update completed!")
    print(f"✅ Updated: {updated_count} members")
    print(f"❌ Errors: {error_count}")
    
    if updated_count > 0:
        print(f"\n📊 All 'Other' regions have been changed to 'Overig'")
        print(f"🕒 Updated timestamp set to: 2026-01-06T18:00:00")

if __name__ == "__main__":
    fix_region_values()