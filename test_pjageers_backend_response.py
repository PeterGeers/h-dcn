#!/usr/bin/env python3
"""
Test what the backend returns for pjageers@gmail.com
"""
import boto3
import json

def test_pjageers():
    """Check pjageers@gmail.com data"""
    
    email = 'pjageers@gmail.com'
    
    print(f"\n🔍 Testing backend response for {email}")
    print("=" * 60)
    
    # Check Cognito
    print("\n1️⃣ Checking Cognito...")
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    
    try:
        response = cognito_client.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"'
        )
        
        if response['Users']:
            user = response['Users'][0]
            cognito_user_id = user['Username']
            print(f"   ✅ Found Cognito user: {cognito_user_id}")
            
            member_id = None
            for attr in user['Attributes']:
                if attr['Name'] == 'custom:member_id':
                    member_id = attr['Value']
                    print(f"   ✅ member_id: {member_id}")
                    break
            
            if not member_id:
                print(f"   ❌ No member_id in Cognito")
        else:
            print(f"   ❌ User not found")
            return
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return
    
    # Check Members table
    print(f"\n2️⃣ Checking Members table...")
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    if member_id:
        response = table.get_item(Key={'member_id': member_id})
        item = response.get('Item')
        
        if item:
            print(f"   ✅ Found member record")
            print(f"   voornaam: {item.get('voornaam')}")
            print(f"   achternaam: {item.get('achternaam')}")
            print(f"   straat: {item.get('straat')}")
            print(f"   status: {item.get('status')}")
            
            # Check if has application data
            has_data = bool(item.get('voornaam') or item.get('achternaam') or item.get('straat'))
            print(f"   Has application data: {has_data}")
            
            # Show what backend would return
            print(f"\n3️⃣ Backend would return:")
            print("=" * 60)
            
            def convert_decimals(obj):
                if isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_decimals(value) for key, value in obj.items()}
                elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
                    return float(obj)
                else:
                    return obj
            
            member_data = convert_decimals(item)
            print(json.dumps(member_data, indent=2, default=str))
        else:
            print(f"   ❌ No member record found")
    else:
        print(f"   ⚠️  No member_id to look up")

if __name__ == '__main__':
    test_pjageers()
