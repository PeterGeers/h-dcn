#!/usr/bin/env python3
"""
Check Current Authentication Flows Available in Cognito User Pool Client
"""

import boto3
import json
from botocore.exceptions import ClientError

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
CLIENT_ID = "7p5t7sjl2s1rcu1emn85h20qeh"
REGION = "eu-west-1"

def check_auth_flows():
    """Check what authentication flows are currently enabled"""
    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        # Get User Pool Client details
        response = cognito_client.describe_user_pool_client(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID
        )
        
        client_details = response.get('UserPoolClient', {})
        explicit_auth_flows = client_details.get('ExplicitAuthFlows', [])
        
        print("🔍 Current Cognito User Pool Client Configuration:")
        print(f"Client Name: {client_details.get('ClientName')}")
        print(f"Client ID: {CLIENT_ID}")
        print(f"User Pool ID: {USER_POOL_ID}")
        print()
        
        print("🔐 Enabled Authentication Flows:")
        for flow in explicit_auth_flows:
            print(f"  ✅ {flow}")
        
        print()
        print("📋 Available Authentication Methods:")
        
        # Check what each flow enables
        flow_descriptions = {
            'ALLOW_USER_AUTH': 'Choice-based authentication (passwordless compatible)',
            'ALLOW_USER_SRP_AUTH': 'Secure Remote Password (SRP) authentication',
            'ALLOW_REFRESH_TOKEN_AUTH': 'Refresh token authentication',
            'ALLOW_ADMIN_USER_PASSWORD_AUTH': 'Admin user/password authentication (for testing)',
            'ALLOW_CUSTOM_AUTH': 'Custom authentication flows',
            'ALLOW_USER_PASSWORD_AUTH': 'Direct user/password authentication'
        }
        
        for flow in explicit_auth_flows:
            description = flow_descriptions.get(flow, 'Unknown flow')
            print(f"  • {flow}: {description}")
        
        print()
        print("🧪 Recommended Test Approach:")
        
        if 'ALLOW_ADMIN_USER_PASSWORD_AUTH' in explicit_auth_flows:
            print("  ✅ Use AdminInitiateAuth with ADMIN_USER_PASSWORD_AUTH")
        elif 'ALLOW_USER_PASSWORD_AUTH' in explicit_auth_flows:
            print("  ✅ Use InitiateAuth with USER_PASSWORD_AUTH")
        elif 'ALLOW_USER_SRP_AUTH' in explicit_auth_flows:
            print("  ⚠️  Use InitiateAuth with USER_SRP_AUTH (requires SRP calculation)")
        elif 'ALLOW_USER_AUTH' in explicit_auth_flows:
            print("  ⚠️  Use InitiateAuth with USER_AUTH (passwordless flow)")
        else:
            print("  ❌ No suitable authentication flow for password testing")
        
        return explicit_auth_flows
        
    except ClientError as e:
        print(f"❌ Error checking authentication flows: {e}")
        return []

if __name__ == "__main__":
    check_auth_flows()