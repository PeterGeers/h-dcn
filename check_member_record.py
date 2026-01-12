#!/usr/bin/env python3
"""
Check if a member record exists for a specific email address
"""

import boto3
import json
from datetime import datetime

def check_member_record(email):
    """Check if a member record exists for the given email"""
    
    try:
        # Initialize DynamoDB with correct region
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('Members')
        
        print(f"🔍 Checking for member record with email: {email}")
        
        # Try to query using email index if it exists
        try:
            response = table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if response['Items']:
                member = response['Items'][0]
                print(f"✅ Found member record via GSI:")
                print_member_info(member)
                return member
            else:
                print(f"⚠️ No member found via GSI, trying scan...")
                
        except Exception as gsi_error:
            print(f"⚠️ GSI query failed: {str(gsi_error)}")
            print(f"⚠️ Falling back to scan...")
        
        # Fallback to scan
        response = table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        if response['Items']:
            member = response['Items'][0]
            print(f"✅ Found member record via scan:")
            print_member_info(member)
            return member
        else:
            print(f"❌ No member record found for {email}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking member record: {str(e)}")
        return None

def print_member_info(member):
    """Print formatted member information"""
    
    print(f"   Member ID: {member.get('member_id', 'N/A')}")
    print(f"   Email: {member.get('email', 'N/A')}")
    print(f"   Name: {member.get('voornaam', '')} {member.get('tussenvoegsel', '')} {member.get('achternaam', '')}".strip())
    print(f"   Status: {member.get('status', 'N/A')}")
    print(f"   Membership: {member.get('lidmaatschap', 'N/A')}")
    print(f"   Region: {member.get('regio', 'N/A')}")
    print(f"   Created: {member.get('created_at', 'N/A')}")
    print(f"   Updated: {member.get('updated_at', 'N/A')}")
    
    # Show key fields for verification
    key_fields = ['telefoon', 'straat', 'postcode', 'woonplaats', 'geboortedatum']
    for field in key_fields:
        if member.get(field):
            print(f"   {field.capitalize()}: {member.get(field)}")

def main():
    """Main function"""
    
    email = "pjageers@gmail.com"
    
    print("=" * 60)
    print("H-DCN Member Record Check")
    print("=" * 60)
    
    member = check_member_record(email)
    
    if member:
        print(f"\n📋 Summary:")
        print(f"   Record exists: ✅ YES")
        print(f"   Status: {member.get('status', 'Unknown')}")
        print(f"   Application complete: {'✅ YES' if member.get('voornaam') and member.get('achternaam') else '❌ NO'}")
    else:
        print(f"\n📋 Summary:")
        print(f"   Record exists: ❌ NO")
        print(f"   User needs to create application via /members/me POST")

if __name__ == "__main__":
    main()