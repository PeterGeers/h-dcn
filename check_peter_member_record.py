#!/usr/bin/env python3
"""
Check if peter.geers@live.nl has a member record in the database
"""
import boto3
from decimal import Decimal

def check_member_record():
    """Check for peter.geers@live.nl in Members table"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    email = 'peter.geers@live.nl'
    
    print(f"\n🔍 Checking for member record with email: {email}")
    print("=" * 60)
    
    # Scan for member by email
    response = table.scan(
        FilterExpression='email = :email',
        ExpressionAttributeValues={':email': email}
    )
    
    items = response.get('Items', [])
    
    if items:
        print(f"\n✅ Found {len(items)} member record(s):")
        for item in items:
            print(f"\n📋 Member Record:")
            print(f"   member_id: {item.get('member_id')}")
            print(f"   email: {item.get('email')}")
            print(f"   status: {item.get('status')}")
            print(f"   voornaam: {item.get('voornaam')}")
            print(f"   achternaam: {item.get('achternaam')}")
            print(f"   straat: {item.get('straat')}")
            print(f"   created: {item.get('created')}")
            print(f"   lastModified: {item.get('lastModified')}")
            
            # Check if it has actual data
            has_data = bool(item.get('voornaam') or item.get('achternaam') or item.get('straat'))
            print(f"   Has application data: {has_data}")
    else:
        print(f"\n❌ No member record found for {email}")
    
    # Also check Cognito
    print(f"\n🔍 Checking Cognito for {email}")
    print("=" * 60)
    
    cognito = boto3.client('cognito-idp', region_name='eu-west-1')
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    
    try:
        # List users with this email
        response = cognito.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"'
        )
        
        if response['Users']:
            for user in response['Users']:
                print(f"\n✅ Found Cognito user:")
                print(f"   Username (sub): {user['Username']}")
                print(f"   Status: {user['UserStatus']}")
                print(f"   Attributes:")
                for attr in user['Attributes']:
                    print(f"      {attr['Name']}: {attr['Value']}")
        else:
            print(f"\n❌ No Cognito user found for {email}")
    except Exception as e:
        print(f"\n❌ Error checking Cognito: {str(e)}")

if __name__ == '__main__':
    check_member_record()
