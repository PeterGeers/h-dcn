#!/usr/bin/env python3
"""
Check member record in DynamoDB using the member_id from Cognito
"""

import boto3
import json
from decimal import Decimal

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def check_member_table():
    """Check member record in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    member_id = '6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579'  # From Cognito custom:member_id
    
    print(f"Checking Members table for member_id: {member_id}")
    
    try:
        # Get the member record directly by member_id (primary key)
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✅ Member record found!")
            print(json.dumps(item, indent=2, default=decimal_default))
            
            # Check which fields have data
            filled_fields = []
            empty_fields = []
            
            for key, value in item.items():
                if value and value != '' and value != 0:
                    filled_fields.append(key)
                else:
                    empty_fields.append(key)
            
            print(f"\n📊 Field Summary:")
            print(f"✅ Fields with data ({len(filled_fields)}): {filled_fields}")
            if empty_fields:
                print(f"⚠️  Empty fields ({len(empty_fields)}): {empty_fields}")
        else:
            print(f"❌ No member record found with ID: {member_id}")
            
            # Let's also try searching by email as fallback
            print(f"\n🔍 Searching by email as fallback...")
            email = 'peter@pgeers.nl'
            
            scan_response = table.scan(
                FilterExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            items = scan_response.get('Items', [])
            if items:
                print(f"✅ Found {len(items)} record(s) by email:")
                for i, item in enumerate(items):
                    print(f"\n--- Record {i+1} ---")
                    print(f"ID: {item.get('id')}")
                    print(f"Email: {item.get('email')}")
                    print(f"Name: {item.get('voornaam', '')} {item.get('achternaam', '')}")
                    print(f"Status: {item.get('status', 'N/A')}")
            else:
                print(f"❌ No records found by email either")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_member_table()