#!/usr/bin/env python3
"""
Check member record for peter@pgeers.nl
"""

import boto3
import json
from decimal import Decimal

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def check_member_record():
    """Check member record in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    email = 'peter@pgeers.nl'
    
    print(f"Checking member record for: {email}")
    
    try:
        # Scan for the member record by email
        response = table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        items = response.get('Items', [])
        
        if not items:
            print("❌ No member record found")
            return
        
        print(f"✅ Found {len(items)} member record(s):")
        
        for i, item in enumerate(items):
            print(f"\n--- Record {i+1} ---")
            print(json.dumps(item, indent=2, default=decimal_default))
            
            # Check which fields are empty
            empty_fields = []
            for key, value in item.items():
                if value == '' or value is None or (isinstance(value, (int, float)) and value == 0):
                    empty_fields.append(key)
            
            if empty_fields:
                print(f"\n⚠️  Empty/null fields: {empty_fields}")
            else:
                print("\n✅ All fields have values")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_member_record()