#!/usr/bin/env python3
"""
Test what the backend returns for peter.geers@live.nl
Simulates the GET /members/me request
"""
import boto3
import json

def test_get_member_self():
    """Simulate GET /members/me for peter.geers@live.nl"""
    
    email = 'peter.geers@live.nl'
    cognito_user_id = '42653434-c081-7058-54f2-6a4026432cfc'
    
    print(f"\n🔍 Testing GET /members/me for {email}")
    print("=" * 60)
    
    # Step 1: Check Cognito for member_id
    print("\n1️⃣ Checking Cognito for custom:member_id...")
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    user_pool_id = 'eu-west-1_OAT3oPCIm'
    
    try:
        cognito_response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=cognito_user_id
        )
        
        member_id = None
        for attr in cognito_response.get('UserAttributes', []):
            if attr['Name'] == 'custom:member_id':
                member_id = attr['Value']
                break
        
        if member_id:
            print(f"   ✅ Found member_id in Cognito: {member_id}")
        else:
            print(f"   ❌ No member_id in Cognito")
    except Exception as e:
        print(f"   ❌ Error checking Cognito: {str(e)}")
        member_id = None
    
    # Step 2: If no member_id, check Members table by email
    if not member_id:
        print(f"\n2️⃣ No member_id - checking Members table by email...")
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('Members')
        
        scan_response = table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        if scan_response.get('Items'):
            member_id = scan_response['Items'][0]['member_id']
            print(f"   ✅ Found existing member record with member_id: {member_id}")
            print(f"   ⚠️  Backend would sync this to Cognito")
        else:
            print(f"   ❌ No member record found by email")
    
    # Step 3: Determine what backend returns
    print(f"\n3️⃣ Backend response:")
    print("=" * 60)
    
    if not member_id:
        # No member_id - backend returns null
        response = {
            'member': None,
            'message': 'No member record found. You may need to complete your membership application.',
            'email': email
        }
        print("   📋 Response body:")
        print(json.dumps(response, indent=2))
        print("\n   ✅ This is CORRECT - frontend should show empty application form")
    else:
        # Has member_id - get the record
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('Members')
        
        response = table.get_item(Key={'member_id': member_id})
        item = response.get('Item')
        
        if not item:
            response = {
                'member': None,
                'message': 'No member record found. You may need to complete your membership application.',
                'email': email,
                'member_id': member_id
            }
            print("   📋 Response body:")
            print(json.dumps(response, indent=2))
            print("\n   ✅ This is CORRECT - frontend should show empty application form")
        else:
            # Convert Decimal to regular types for display
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
            
            print("   📋 Response body:")
            print(json.dumps(member_data, indent=2))
            
            # Check if has application data
            has_data = bool(member_data.get('voornaam') or member_data.get('achternaam') or member_data.get('straat'))
            print(f"\n   Has application data: {has_data}")
            
            if has_data:
                print("   ⚠️  Frontend will show 'Aanvraag Status' box")
            else:
                print("   ✅ Frontend should show empty application form")

if __name__ == '__main__':
    test_get_member_self()
