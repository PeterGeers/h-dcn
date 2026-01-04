#!/usr/bin/env python3
"""
Script to add a test member to the Members table
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal

def add_test_member():
    """Add peter.geers@live.nl as a test member"""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    # Member data for peter.geers@live.nl
    member_data = {
        'email': 'peter.geers@live.nl',
        'voornaam': 'Peter',
        'achternaam': 'Geers',
        'status': 'Actief',
        'lidmaatschap': 'Gewoon lid',
        'regio': 'Noord-Holland',
        'lidnummer': 9999,  # Test member number
        'clubblad': 'Digitaal',
        'nieuwsbrief': 'Ja',
        'privacy': 'Ja',
        'betaalwijze': 'Incasso',
        'land': 'Nederland',
        'nationaliteit': 'Nederlandse',
        'tijdstempel': datetime.now().isoformat(),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'jaren_lid': 1,
        'aanmeldingsjaar': 2024
    }
    
    try:
        # Add the member
        response = table.put_item(Item=member_data)
        print(f"✅ Successfully added member: {member_data['email']}")
        print(f"   Name: {member_data['voornaam']} {member_data['achternaam']}")
        print(f"   Status: {member_data['status']}")
        print(f"   Member #: {member_data['lidnummer']}")
        print(f"   Region: {member_data['regio']}")
        
    except Exception as e:
        print(f"❌ Error adding member: {str(e)}")
        raise

if __name__ == "__main__":
    print("🚀 Adding test member to Members table...")
    add_test_member()
    print("✅ Done!")