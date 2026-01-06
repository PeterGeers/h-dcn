#!/usr/bin/env python3
"""
Check Peter's record in the database
"""

import boto3
from boto3.dynamodb.conditions import Attr
import json

# Configure AWS
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def check_peter_record():
    """Check Peter's member record"""
    print("🔍 Looking for peter@pgeers.nl record...")
    
    # Find Peter's record by email
    response = table.scan(
        FilterExpression=Attr('email').eq('peter@pgeers.nl')
    )
    
    items = response['Items']
    
    if not items:
        print("❌ No record found for peter@pgeers.nl")
        return
    
    if len(items) > 1:
        print(f"⚠️  Multiple records found: {len(items)}")
    
    peter = items[0]
    
    print(f"✅ Found record for: {peter.get('name', 'Unknown')}")
    print(f"📧 Email: {peter.get('email', 'Unknown')}")
    print(f"🆔 Member ID: {peter.get('member_id', 'Unknown')}")
    
    # Check key fields
    key_fields = [
        'lidnummer',
        'tijdstempel',
        'geboortedatum', 
        'status',
        'lidmaatschap',
        'regio',
        'created_at',
        'updated_at',
        'voornaam',
        'achternaam',
        'bouwjaar',
        'motormerk'
    ]
    
    print(f"\n📋 Key field values:")
    for field in key_fields:
        value = peter.get(field, 'NOT_SET')
        print(f"   {field}: {value}")
    
    # Show all fields
    print(f"\n📄 Complete record:")
    print(json.dumps(peter, indent=2, default=str, ensure_ascii=False))
    
    # Check specific issues
    print(f"\n🔍 Issue Analysis:")
    
    # Check tijdstempel (Lid sinds)
    tijdstempel = peter.get('tijdstempel')
    if not tijdstempel:
        print(f"❌ tijdstempel (Lid sinds) is empty/missing")
    else:
        print(f"✅ tijdstempel (Lid sinds): {tijdstempel}")
    
    # Check bouwjaar
    bouwjaar = peter.get('bouwjaar')
    if not bouwjaar:
        print(f"⚠️  bouwjaar is empty/missing")
    else:
        print(f"✅ bouwjaar: {bouwjaar} (type: {type(bouwjaar)})")
    
    # Check status
    status = peter.get('status')
    print(f"📊 Status: {status}")
    
    return peter

if __name__ == "__main__":
    check_peter_record()