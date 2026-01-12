#!/usr/bin/env python3
"""
Debug script to investigate the LidNummer issue
This script will:
1. Get a record from the member table with lidmaatschap == 'Gewoon Lid'
2. Check what the lidnummer value is in the database
3. Analyze possible reasons for the 0 presentation
"""

import boto3
import json
from decimal import Decimal

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def main():
    print("=== LidNummer Debug Investigation ===")
    
    # Initialize DynamoDB with explicit region
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    try:
        # Scan for members with lidmaatschap == 'Gewoon lid' (note lowercase 'l')
        print("\n1. Scanning for members with lidmaatschap == 'Gewoon lid'...")
        
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('lidmaatschap').eq('Gewoon lid'),
            Limit=5  # Just get first 5 records
        )
        
        members = response['Items']
        print(f"Found {len(members)} members with 'Gewoon Lid' membership")
        
        if not members:
            print("No members found with 'Gewoon lid' membership. Let's check all members...")
            
            # Get all members to see what we have
            all_response = table.scan(Limit=10)
            all_members = all_response['Items']
            
            print(f"\nFound {len(all_members)} total members (first 10):")
            for i, member in enumerate(all_members):
                print(f"  {i+1}. ID: {member.get('member_id', 'N/A')}")
                print(f"     Lidmaatschap: {member.get('lidmaatschap', 'N/A')}")
                print(f"     Lidnummer: {member.get('lidnummer', 'N/A')} (type: {type(member.get('lidnummer', 'N/A'))})")
                print(f"     Status: {member.get('status', 'N/A')}")
                print(f"     Naam: {member.get('voornaam', 'N/A')} {member.get('achternaam', 'N/A')}")
                print()
            
            return
        
        # Analyze the first few members
        print("\n2. Analyzing member records:")
        for i, member in enumerate(members[:3]):
            print(f"\n--- Member {i+1} ---")
            print(f"Member ID: {member.get('member_id', 'N/A')}")
            print(f"Naam: {member.get('voornaam', 'N/A')} {member.get('achternaam', 'N/A')}")
            print(f"Lidmaatschap: {member.get('lidmaatschap', 'N/A')}")
            print(f"Status: {member.get('status', 'N/A')}")
            
            # Focus on lidnummer field
            lidnummer = member.get('lidnummer')
            print(f"Lidnummer: {lidnummer}")
            print(f"Lidnummer type: {type(lidnummer)}")
            print(f"Lidnummer repr: {repr(lidnummer)}")
            
            # Check if it's a Decimal that equals 0
            if isinstance(lidnummer, Decimal):
                print(f"Lidnummer as int: {int(lidnummer)}")
                print(f"Lidnummer as float: {float(lidnummer)}")
                print(f"Is zero?: {lidnummer == 0}")
            
            # Check all fields that might be related
            print("\nAll numeric fields:")
            for key, value in member.items():
                if isinstance(value, (int, float, Decimal)):
                    print(f"  {key}: {value} (type: {type(value)})")
            
            print("\nFull member record:")
            print(json.dumps(member, indent=2, default=decimal_default))
        
        # Check statistics
        print("\n3. Statistics on lidnummer values:")
        lidnummer_values = []
        zero_count = 0
        non_zero_count = 0
        
        for member in members:
            lidnummer = member.get('lidnummer')
            if lidnummer is not None:
                lidnummer_values.append(lidnummer)
                if isinstance(lidnummer, (int, float, Decimal)) and lidnummer == 0:
                    zero_count += 1
                else:
                    non_zero_count += 1
        
        print(f"Total members with lidnummer field: {len(lidnummer_values)}")
        print(f"Members with lidnummer = 0: {zero_count}")
        print(f"Members with lidnummer != 0: {non_zero_count}")
        
        if lidnummer_values:
            max_lidnummer = max(lidnummer_values)
            min_lidnummer = min(lidnummer_values)
            print(f"Highest lidnummer: {max_lidnummer}")
            print(f"Lowest lidnummer: {min_lidnummer}")
        
        # Check if there are any members without lidnummer field
        members_without_lidnummer = [m for m in members if 'lidnummer' not in m]
        print(f"Members without lidnummer field: {len(members_without_lidnummer)}")
        
        print("\n4. Possible reasons for 0 presentation:")
        print("   a) Database actually contains 0 values")
        print("   b) Frontend is not properly handling Decimal types from DynamoDB")
        print("   c) Field mapping issue between database field name and frontend")
        print("   d) Computed field logic is not working correctly")
        print("   e) Data migration issue where lidnummer was not properly set")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()