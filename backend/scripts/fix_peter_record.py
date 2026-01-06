#!/usr/bin/env python3
"""
Fix Peter's record issues
"""

import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def fix_peter_record():
    """Fix issues in Peter's record"""
    print("🔧 Fixing Peter's record...")
    
    # Find Peter's record
    response = table.scan(
        FilterExpression=Attr('email').eq('peter@pgeers.nl')
    )
    
    items = response['Items']
    if not items:
        print("❌ No record found for peter@pgeers.nl")
        return
    
    peter = items[0]
    member_id = peter['member_id']
    
    print(f"✅ Found record: {peter.get('name')}")
    
    # Fixes to apply
    updates = {}
    
    # Fix motormerk: FLHXI -> Harley-Davidson (since FLHXI is a Harley model)
    if peter.get('motormerk') == 'FLHXI':
        updates['motormerk'] = 'Harley-Davidson'
        print(f"🔧 Fixing motormerk: FLHXI -> Harley-Davidson")
    
    # Add bouwjaar if missing (based on kenteken MP-PX-15, this looks like a 2015 bike)
    if 'bouwjaar' not in peter or not peter.get('bouwjaar'):
        updates['bouwjaar'] = 2015  # Reasonable guess based on kenteken
        print(f"🔧 Adding bouwjaar: 2015")
    
    if not updates:
        print("✅ No fixes needed")
        return
    
    # Apply updates
    try:
        update_expression = "SET "
        expression_values = {}
        expression_names = {}
        
        for i, (field, value) in enumerate(updates.items()):
            if i > 0:
                update_expression += ", "
            
            field_name = f"#field{i}"
            value_name = f":val{i}"
            
            update_expression += f"{field_name} = {value_name}"
            expression_names[field_name] = field
            expression_values[value_name] = value
        
        # Add updated timestamp
        update_expression += ", updated_at = :updated_at"
        expression_values[':updated_at'] = datetime.now().isoformat()
        
        table.update_item(
            Key={'member_id': member_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )
        
        print(f"✅ Successfully updated Peter's record")
        for field, value in updates.items():
            print(f"   {field}: {value}")
        
    except Exception as e:
        print(f"❌ Error updating record: {str(e)}")

if __name__ == "__main__":
    print("🔧 Peter's Record Fix")
    print("📋 Will fix:")
    print("   - motormerk: FLHXI -> Harley-Davidson")
    print("   - bouwjaar: Add 2015 (estimated)")
    
    response = input("\nContinue with fixes? (y/N): ")
    if response.lower() != 'y':
        print("❌ Fixes cancelled")
        exit(0)
    
    fix_peter_record()