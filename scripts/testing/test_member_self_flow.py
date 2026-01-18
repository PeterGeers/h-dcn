#!/usr/bin/env python3
"""
Test the complete flow for /members/me endpoint
This simulates what the Lambda function will do
"""

import boto3
import json
import base64

def test_member_self_flow():
    """Test the complete flow"""
    
    print("=" * 60)
    print("Testing /members/me endpoint flow")
    print("=" * 60)
    
    # Step 1: Simulate JWT token with Cognito user ID
    print("\n1️⃣ Step 1: Extract Cognito user ID from JWT token")
    print("-" * 60)
    
    # This is a sample JWT payload (the actual one from your login)
    jwt_payload = {
        "sub": "c24584c4-5071-70e3-e44e-d3786b406450",  # Cognito user ID
        "email": "peter@pgeers.nl",
        "cognito:groups": ["hdcnLeden"]
    }
    
    cognito_user_id = jwt_payload.get('sub')
    user_email = jwt_payload.get('email')
    
    print(f"✅ Cognito user ID: {cognito_user_id}")
    print(f"✅ Email: {user_email}")
    
    # Step 2: Get member_id from Cognito
    print("\n2️⃣ Step 2: Get member_id from Cognito user attributes")
    print("-" * 60)
    
    try:
        cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        user_pool_id = 'eu-west-1_OAT3oPCIm'
        
        # Get user details from Cognito using the Cognito user ID
        cognito_response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=cognito_user_id
        )
        
        print(f"✅ Successfully retrieved Cognito user")
        
        # Extract member_id from user attributes
        member_id = None
        for attr in cognito_response.get('UserAttributes', []):
            if attr['Name'] == 'custom:member_id':
                member_id = attr['Value']
                print(f"✅ Found custom:member_id: {member_id}")
                break
        
        if not member_id:
            print("❌ ERROR: custom:member_id not found in Cognito user attributes")
            return False
            
    except Exception as e:
        print(f"❌ ERROR getting member_id from Cognito: {str(e)}")
        return False
    
    # Step 3: Get member record from DynamoDB
    print("\n3️⃣ Step 3: Get member record from DynamoDB")
    print("-" * 60)
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('Members')
        
        # Get the member record using member_id as primary key
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✅ Successfully retrieved member record")
            print(f"   Name: {item.get('voornaam')} {item.get('achternaam')}")
            print(f"   Email: {item.get('email')}")
            print(f"   Status: {item.get('status')}")
            print(f"   Lidnummer: {item.get('lidnummer')}")
            
            # Check how many fields have data
            filled_fields = sum(1 for v in item.values() if v and v != '')
            print(f"   Total fields with data: {filled_fields}/{len(item)}")
            
            return True
        else:
            print(f"❌ ERROR: No member record found with member_id: {member_id}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR getting member record: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n")
    success = test_member_self_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED - All steps completed successfully!")
        print("=" * 60)
        print("\n✅ The flow is working correctly. Ready to deploy!")
    else:
        print("❌ TEST FAILED - There are issues to fix")
        print("=" * 60)
        print("\n❌ Fix the issues above before deploying")
    print("\n")
