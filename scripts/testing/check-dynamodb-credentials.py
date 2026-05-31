#!/usr/bin/env python3
"""
Check if passkey credentials are stored in DynamoDB Members table
"""
import boto3
import json
from datetime import datetime

# Configuration
TABLE_NAME = "Members"
USER_EMAIL = "webmaster@h-dcn.nl"

def check_dynamodb_credentials():
    """Check if passkey credentials are stored in DynamoDB"""
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table(TABLE_NAME)
        
        print(f"Checking DynamoDB table '{TABLE_NAME}' for passkey data...")
        print("=" * 60)
        
        # First, let's see what the table structure looks like
        try:
            table_info = table.meta.client.describe_table(TableName=TABLE_NAME)
            print("📋 TABLE INFO:")
            print(f"  Table Status: {table_info['Table']['TableStatus']}")
            print(f"  Item Count: {table_info['Table']['ItemCount']}")
            
            # Show key schema
            key_schema = table_info['Table']['KeySchema']
            print(f"  Key Schema: {[key['AttributeName'] for key in key_schema]}")
            print()
            
        except Exception as e:
            print(f"⚠ Could not get table info: {e}")
        
        # Try to find the user by email
        print(f"🔍 SEARCHING FOR USER: {USER_EMAIL}")
        print("-" * 40)
        
        # Scan for the user (since we don't know the key structure)
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(USER_EMAIL)
        )
        
        items = response.get('Items', [])
        
        if not items:
            print(f"❌ No records found for {USER_EMAIL}")
            
            # Let's see what records exist (first 5)
            print("\n📋 SAMPLE RECORDS (first 5):")
            sample_response = table.scan(Limit=5)
            for i, item in enumerate(sample_response.get('Items', []), 1):
                print(f"  Record {i}:")
                for key, value in item.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f"    {key}: {value[:50]}...")
                    else:
                        print(f"    {key}: {value}")
                print()
            
            return None
        
        print(f"✓ Found {len(items)} record(s) for {USER_EMAIL}")
        
        # Check each record for passkey data
        for i, item in enumerate(items, 1):
            print(f"\n📄 RECORD {i}:")
            print("-" * 20)
            
            passkey_fields = {}
            other_fields = {}
            
            for key, value in item.items():
                key_lower = key.lower()
                if any(term in key_lower for term in ['passkey', 'webauthn', 'credential', 'auth']):
                    passkey_fields[key] = value
                else:
                    other_fields[key] = value
            
            # Show passkey-related fields
            if passkey_fields:
                print("🔐 PASSKEY/AUTH FIELDS:")
                for key, value in passkey_fields.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {key}: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("❌ NO PASSKEY/AUTH FIELDS FOUND")
            
            # Show other relevant fields
            print("\n📋 OTHER FIELDS:")
            for key, value in other_fields.items():
                if key in ['email', 'member_id', 'first_name', 'last_name', 'status']:
                    print(f"  {key}: {value}")
        
        return items
        
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {e}")
        return None

if __name__ == "__main__":
    print("Checking DynamoDB for Passkey Credentials")
    print("=" * 60)
    
    records = check_dynamodb_credentials()
    
    if records:
        print(f"\n💡 FOUND {len(records)} RECORD(S)")
        print("Check the output above for any passkey-related fields")
    else:
        print("\n❌ NO RECORDS FOUND")
        print("Passkey credentials are likely only stored in Cognito attributes")