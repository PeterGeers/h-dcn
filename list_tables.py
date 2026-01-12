#!/usr/bin/env python3
"""
List available DynamoDB tables
"""

import boto3

def list_dynamodb_tables():
    """List all DynamoDB tables"""
    
    try:
        dynamodb = boto3.client('dynamodb', region_name='eu-west-1')
        
        print("🔍 Listing DynamoDB tables...")
        
        response = dynamodb.list_tables()
        tables = response['TableNames']
        
        print(f"✅ Found {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
            
        return tables
        
    except Exception as e:
        print(f"❌ Error listing tables: {str(e)}")
        return []

if __name__ == "__main__":
    list_dynamodb_tables()