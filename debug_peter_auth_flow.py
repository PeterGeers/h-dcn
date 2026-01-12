#!/usr/bin/env python3
"""
Debug Peter's authentication flow to understand why he's being redirected
to new-member-application despite having hdcnLeden role
"""

import boto3
import json
import base64
from datetime import datetime, timedelta

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
USER_POOL_ID = 'eu-west-1_OAT3oPCIm'

def simulate_peter_login():
    """Simulate Peter's login flow to debug the issue"""
    
    email = "peter@pgeers.nl"
    print(f"🔍 Debugging authentication flow for: {email}")
    print("=" * 60)
    
    # Step 1: Get user from Cognito
    try:
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"'
        )
        
        users = response.get('Users', [])
        if not users:
            print(f"❌ ISSUE FOUND: User {email} not found in Cognito")
            return
        
        user = users[0]
        username = user['Username']
        
        print(f"✅ Step 1: User found in Cognito")
        print(f"   Username: {username}")
        print(f"   Status: {user.get('UserStatus', 'Unknown')}")
        print(f"   Enabled: {user.get('Enabled', False)}")
        
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return
    
    # Step 2: Get user's groups
    try:
        groups_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        
        groups = groups_response.get('Groups', [])
        group_names = [g['GroupName'] for g in groups]
        
        print(f"\n✅ Step 2: User groups retrieved")
        print(f"   Groups ({len(groups)}): {group_names}")
        
        # Check the specific logic from Dashboard.tsx
        has_hdcn_leden = 'hdcnLeden' in group_names
        has_valid_member_role = any(group in group_names for group in [
            'hdcnLeden'
        ]) or any(
            group.startswith(prefix) for group in group_names 
            for prefix in ['Members_', 'Events_', 'Products_', 'System_', 'Communication_', 'National_', 'Regional_', 'Webmaster', 'Regio_']
        )
        
        is_only_applicant = len(group_names) == 1 and 'verzoek_lid' in group_names
        has_no_groups = len(group_names) == 0
        
        print(f"\n🔍 Step 3: Dashboard logic analysis")
        print(f"   has_hdcn_leden: {has_hdcn_leden}")
        print(f"   has_valid_member_role: {has_valid_member_role}")
        print(f"   is_only_applicant: {is_only_applicant}")
        print(f"   has_no_groups: {has_no_groups}")
        
        should_redirect = has_no_groups or is_only_applicant
        print(f"   should_redirect_to_application: {should_redirect}")
        
        if should_redirect:
            print(f"\n❌ ISSUE FOUND: User would be redirected to new-member-application")
            if has_no_groups:
                print(f"   Reason: User has no groups")
            if is_only_applicant:
                print(f"   Reason: User only has verzoek_lid role")
        else:
            print(f"\n✅ User should NOT be redirected - has valid roles")
            
    except Exception as e:
        print(f"❌ Error getting groups: {e}")
        return
    
    # Step 4: Check member database status
    print(f"\n🔍 Step 4: Member database check")
    print(f"   Peter's member record exists: ✅ (confirmed from peter_record_20260112_113254.json)")
    print(f"   Status: 'Actief'")
    print(f"   Member ID: '6bcc949f-49ab-4d8b-93e3-ba9f7ab3e579'")
    
    # Step 5: Analyze potential issues
    print(f"\n🔍 Step 5: Potential issues analysis")
    
    # Check if there were recent changes to authentication logic
    print(f"   Recent changes to check:")
    print(f"   1. Dashboard.tsx logic changes")
    print(f"   2. GroupAccessGuard.tsx changes") 
    print(f"   3. JWT token decoding issues")
    print(f"   4. Frontend credential extraction issues")
    print(f"   5. Post-authentication handler changes")
    
    # Check JWT token structure (simulate)
    print(f"\n🔍 Step 6: JWT token simulation")
    print(f"   Expected JWT payload should contain:")
    print(f"   - email: {email}")
    print(f"   - cognito:groups: {group_names}")
    print(f"   - sub: {user.get('Username')}")
    
    # Timeline analysis
    print(f"\n📅 Step 7: Timeline analysis")
    print(f"   User created: {user.get('UserCreateDate')}")
    print(f"   Last modified: {user.get('UserLastModifiedDate')}")
    print(f"   Issue reported: Between Jan 6-10, 2025")
    print(f"   Auth fallback updated: 2026-01-08 (from backup timestamp)")
    
    # Recommendations
    print(f"\n💡 Step 8: Recommendations")
    if not should_redirect:
        print(f"   ✅ Cognito setup appears correct")
        print(f"   🔍 Issue likely in frontend:")
        print(f"      - JWT token not being decoded properly")
        print(f"      - Groups not being extracted from token")
        print(f"      - Browser cache issues")
        print(f"      - Frontend authentication state issues")
        print(f"\n   🛠️  Suggested fixes:")
        print(f"      1. Clear browser cache/localStorage")
        print(f"      2. Check browser console for JWT decoding errors")
        print(f"      3. Verify frontend credential extraction logic")
        print(f"      4. Test with fresh login session")
    else:
        print(f"   ❌ Cognito role assignment issue found")
        print(f"   🛠️  Need to fix Cognito groups")

if __name__ == "__main__":
    simulate_peter_login()