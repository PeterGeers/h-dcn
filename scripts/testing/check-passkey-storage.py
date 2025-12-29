#!/usr/bin/env python3
"""
Check what passkey data is stored for webmaster@h-dcn.nl
"""
import boto3
import json
from datetime import datetime

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
USER_EMAIL = "webmaster@h-dcn.nl"

def check_user_passkey_data():
    """Check what passkey-related data is stored for the user"""
    
    cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    try:
        # Get user details
        print(f"Checking passkey data for: {USER_EMAIL}")
        print("=" * 60)
        
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=USER_EMAIL
        )
        
        print(f"✓ User found: {USER_EMAIL}")
        print(f"  Status: {response['UserStatus']}")
        print(f"  Created: {response.get('UserCreateDate', 'Unknown')}")
        print(f"  Modified: {response.get('UserLastModifiedDate', 'Unknown')}")
        print()
        
        # Check all user attributes
        print("User Attributes:")
        print("-" * 40)
        
        passkey_attributes = {}
        other_attributes = {}
        
        for attr in response.get('UserAttributes', []):
            name = attr['Name']
            value = attr['Value']
            
            if 'passkey' in name.lower() or 'webauthn' in name.lower():
                passkey_attributes[name] = value
            else:
                other_attributes[name] = value
        
        # Show passkey-related attributes
        if passkey_attributes:
            print("🔐 PASSKEY-RELATED ATTRIBUTES:")
            for name, value in passkey_attributes.items():
                print(f"  {name}: {value}")
        else:
            print("❌ NO PASSKEY-RELATED ATTRIBUTES FOUND")
        
        print()
        
        # Show other relevant attributes
        print("📋 OTHER ATTRIBUTES:")
        for name, value in other_attributes.items():
            if name in ['email', 'email_verified', 'given_name', 'family_name', 'sub']:
                print(f"  {name}: {value}")
        
        print()
        
        # Check user groups
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=USER_EMAIL
            )
            
            groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
            print(f"👥 USER GROUPS: {', '.join(groups) if groups else 'None'}")
            
        except Exception as e:
            print(f"⚠ Could not retrieve groups: {e}")
        
        print()
        print("=" * 60)
        
        # Analysis
        print("🔍 ANALYSIS:")
        
        if passkey_attributes:
            print("✓ User has passkey-related data stored")
            
            if 'custom:passkey_registered' in passkey_attributes:
                registered = passkey_attributes['custom:passkey_registered']
                print(f"  - Passkey registered flag: {registered}")
                
            if 'custom:passkey_credential_id' in passkey_attributes:
                cred_id = passkey_attributes['custom:passkey_credential_id']
                print(f"  - Credential ID stored: {cred_id[:20]}..." if len(cred_id) > 20 else f"  - Credential ID: {cred_id}")
            else:
                print("  - ❌ NO CREDENTIAL ID STORED (this is the problem!)")
                
            if 'custom:passkey_date' in passkey_attributes:
                date = passkey_attributes['custom:passkey_date']
                print(f"  - Registration date: {date}")
        else:
            print("❌ No passkey data found - user may not have completed registration")
        
        return passkey_attributes
        
    except cognito_client.exceptions.UserNotFoundException:
        print(f"❌ User {USER_EMAIL} not found in Cognito")
        return None
        
    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return None

if __name__ == "__main__":
    print("Checking Passkey Storage for webmaster@h-dcn.nl")
    print("=" * 60)
    
    passkey_data = check_user_passkey_data()
    
    if passkey_data:
        print("\n💡 RECOMMENDATIONS:")
        
        if 'custom:passkey_registered' in passkey_data and passkey_data['custom:passkey_registered'] == 'true':
            if 'custom:passkey_credential_id' not in passkey_data:
                print("- The user has the 'registered' flag but NO credential ID")
                print("- This explains why authentication fails")
                print("- The laptop passkey exists but the system can't find it")
                print("- Need to either:")
                print("  1. Re-register the passkey (will store credential ID)")
                print("  2. Or find where the credential ID is actually stored")
            else:
                print("- User has both registration flag AND credential ID")
                print("- The issue might be in the authentication logic")
        else:
            print("- User doesn't have passkey registration flag")
            print("- May need to complete passkey setup")
    else:
        print("\n❌ Could not retrieve user data")