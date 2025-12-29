#!/usr/bin/env python3
"""
Test script to check PostAuthentication trigger and manually test the logic
"""

import boto3
import json
from botocore.exceptions import ClientError

# Initialize clients
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
lambda_client = boto3.client('lambda', region_name='eu-west-1')

USER_POOL_ID = 'eu-west-1_OAT3oPCIm'
USERNAME = 'webmaster@h-dcn.nl'

def check_current_user_groups():
    """Check current groups for the user"""
    try:
        print(f"=== Current Groups for {USERNAME} ===")
        
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=USERNAME
        )
        
        groups = response.get('Groups', [])
        print(f"Total groups: {len(groups)}")
        
        for group in groups:
            print(f"  - {group['GroupName']}")
            if 'Description' in group:
                print(f"    Description: {group['Description']}")
        
        return [group['GroupName'] for group in groups]
        
    except Exception as e:
        print(f"Error checking user groups: {str(e)}")
        return []

def test_post_auth_logic(current_groups):
    """Test the PostAuthentication logic"""
    print(f"\n=== Testing PostAuthentication Logic ===")
    
    # Check if user needs role assignment
    federated_groups = [group for group in current_groups if '_Google' in group or '_Facebook' in group or '_SAML' in group]
    meaningful_groups = [group for group in current_groups if group not in federated_groups]
    
    print(f"Federated groups: {federated_groups}")
    print(f"Meaningful groups: {meaningful_groups}")
    
    needs_assignment = False
    
    if not current_groups:
        print("❌ User has no groups - needs assignment")
        needs_assignment = True
    elif federated_groups and not meaningful_groups:
        print("❌ User only has federated groups - needs assignment")
        needs_assignment = True
    elif 'hdcnLeden' not in current_groups:
        print("❌ User missing basic member role - needs assignment")
        needs_assignment = True
    else:
        print("✅ User has appropriate roles")
    
    return needs_assignment

def find_post_auth_lambda():
    """Find the PostAuthentication Lambda function"""
    try:
        print(f"\n=== Finding PostAuthentication Lambda ===")
        
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        post_auth_functions = []
        for func in functions:
            if 'PostAuthentication' in func['FunctionName'] or 'post-authentication' in func['FunctionName']:
                post_auth_functions.append(func['FunctionName'])
                print(f"Found: {func['FunctionName']}")
        
        if not post_auth_functions:
            print("❌ No PostAuthentication Lambda function found")
            print("Available functions:")
            for func in functions:
                if 'Cognito' in func['FunctionName']:
                    print(f"  - {func['FunctionName']}")
        
        return post_auth_functions
        
    except Exception as e:
        print(f"Error finding Lambda functions: {str(e)}")
        return []

def manually_invoke_post_auth():
    """Manually invoke PostAuthentication trigger"""
    try:
        print(f"\n=== Manually Invoking PostAuthentication ===")
        
        # Find the function
        functions = find_post_auth_lambda()
        if not functions:
            print("Cannot invoke - no PostAuthentication function found")
            return
        
        function_name = functions[0]
        print(f"Invoking: {function_name}")
        
        # Create mock PostAuthentication event
        mock_event = {
            "version": "1",
            "region": "eu-west-1",
            "userPoolId": USER_POOL_ID,
            "userName": USERNAME,
            "triggerSource": "PostAuthentication_Authentication",
            "request": {
                "userAttributes": {
                    "email": USERNAME,
                    "email_verified": "true",
                    "given_name": "Web",
                    "family_name": "Master"
                }
            },
            "response": {}
        }
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(mock_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda response: {result}")
        
        if response['StatusCode'] == 200:
            print("✅ PostAuthentication Lambda invoked successfully")
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
        
    except Exception as e:
        print(f"Error invoking PostAuthentication Lambda: {str(e)}")

def main():
    print("=== PostAuthentication Trigger Test ===")
    
    # Check current user groups
    current_groups = check_current_user_groups()
    
    # Test the logic
    needs_assignment = test_post_auth_logic(current_groups)
    
    # Find PostAuth Lambda
    find_post_auth_lambda()
    
    # If user needs assignment, try manual invocation
    if needs_assignment:
        print(f"\n🔧 User needs role assignment - attempting manual trigger...")
        manually_invoke_post_auth()
        
        # Check groups again after manual invocation
        print(f"\n=== Groups After Manual Trigger ===")
        new_groups = check_current_user_groups()
        
        if len(new_groups) > len(current_groups):
            print("✅ New groups were assigned!")
        else:
            print("❌ No new groups assigned")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    main()