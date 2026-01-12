#!/usr/bin/env python3
"""
Debug script to analyze Peter's login issue
Checks Cognito user status, groups, and member database record
"""

import boto3
import json
from datetime import datetime

def check_cognito_user(email):
    """Check Peter's Cognito user status and groups"""
    cognito = boto3.client('cognito-idp', region_name='eu-west-1')
    user_pool_id = 'eu-west-1_OAT3oPCIm'  # H-DCN-Authentication-Pool with Lambda triggers
    
    try:
        # Get user details
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        print(f"✅ User {email} found in Cognito")
        print(f"   Status: {response.get('UserStatus')}")
        print(f"   Enabled: {response.get('Enabled')}")
        print(f"   Created: {response.get('UserCreateDate')}")
        print(f"   Modified: {response.get('UserLastModifiedDate')}")
        
        # Get user's groups
        groups_response = cognito.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
        print(f"   Groups: {groups}")
        
        return {
            'exists': True,
            'status': response.get('UserStatus'),
            'enabled': response.get('Enabled'),
            'groups': groups
        }
        
    except cognito.exceptions.UserNotFoundException:
        print(f"❌ User {email} NOT found in Cognito")
        return {'exists': False}
    except Exception as e:
        print(f"❌ Error checking Cognito user: {e}")
        return {'exists': False, 'error': str(e)}

def check_member_database(email):
    """Check Peter's record in the Members table"""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Members')
    
    try:
        # Scan for member with matching email
        response = table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        if response.get('Items'):
            member = response['Items'][0]
            print(f"✅ Member {email} found in database")
            print(f"   Name: {member.get('voornaam')} {member.get('achternaam')}")
            print(f"   Status: {member.get('status')}")
            print(f"   Lidmaatschap: {member.get('lidmaatschap')}")
            print(f"   Regio: {member.get('regio')}")
            print(f"   Lidnummer: {member.get('lidnummer')}")
            print(f"   Created: {member.get('created_at')}")
            print(f"   Updated: {member.get('updated_at')}")
            
            return {
                'exists': True,
                'status': member.get('status'),
                'lidmaatschap': member.get('lidmaatschap'),
                'regio': member.get('regio'),
                'member': member
            }
        else:
            print(f"❌ Member {email} NOT found in database")
            return {'exists': False}
            
    except Exception as e:
        print(f"❌ Error checking member database: {e}")
        return {'exists': False, 'error': str(e)}

def analyze_login_flow(email):
    """Analyze what should happen in the login flow"""
    print(f"\n🔍 ANALYZING LOGIN FLOW FOR {email}")
    print("=" * 60)
    
    # Check Cognito status
    print("\n1. COGNITO STATUS:")
    cognito_status = check_cognito_user(email)
    
    # Check member database
    print("\n2. MEMBER DATABASE STATUS:")
    member_status = check_member_database(email)
    
    # Analyze what should happen
    print("\n3. LOGIN FLOW ANALYSIS:")
    
    if not cognito_status.get('exists'):
        print("❌ ISSUE: User doesn't exist in Cognito - should not be able to login")
        return
    
    if not member_status.get('exists'):
        print("❌ ISSUE: User exists in Cognito but not in Members table")
        print("   → Should be redirected to new-member-application")
        return
    
    # Both exist - check what roles should be assigned
    user_groups = cognito_status.get('groups', [])
    member_db_status = member_status.get('status', '')
    
    print(f"   Cognito Groups: {user_groups}")
    print(f"   Member Status: {member_db_status}")
    
    # Check if user should have hdcnLeden role
    if member_db_status.lower() in ['actief', 'active', 'approved']:
        if 'hdcnLeden' not in user_groups:
            print("❌ ISSUE: Active member missing hdcnLeden role")
            print("   → Post-authentication handler should assign hdcnLeden role")
        else:
            print("✅ Active member has hdcnLeden role")
    
    # Check if user has valid access
    has_valid_role = any(group in user_groups for group in [
        'hdcnLeden', 'Members_CRUD', 'Members_Read', 'System_User_Management'
    ])
    
    if not has_valid_role:
        print("❌ ISSUE: User has no valid access roles")
        print("   → Should be redirected to new-member-application or shown access denied")
    else:
        print("✅ User has valid access roles")
    
    # Check regional access
    region_roles = [role for role in user_groups if role.startswith('Regio_')]
    member_region = member_status.get('regio', '')
    
    if region_roles:
        print(f"   Regional roles: {region_roles}")
    else:
        print("   No regional roles (basic member access)")
    
    print(f"   Member region: {member_region}")

def main():
    """Main function"""
    email = "peter@pgeers.nl"
    
    print("🔍 H-DCN LOGIN ISSUE ANALYSIS")
    print("=" * 60)
    print(f"Analyzing login issue for: {email}")
    print(f"Analysis time: {datetime.now().isoformat()}")
    
    analyze_login_flow(email)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()