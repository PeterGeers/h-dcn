#!/usr/bin/env python3
"""
Verify Test Users for H-DCN Cognito Authentication System

This script verifies that the test users were created successfully and shows their group assignments.
"""

import boto3
import json
from typing import List, Dict, Any

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"

# Test users to verify
TEST_USERNAMES = [
    "test.regular@hdcn-test.nl",
    "test.memberadmin@hdcn-test.nl", 
    "test.chairman@hdcn-test.nl",
    "test.webmaster@hdcn-test.nl"
]

class CognitoTestUserVerifier:
    """Verifies test users exist and shows their group assignments"""
    
    def __init__(self, user_pool_id: str):
        self.user_pool_id = user_pool_id
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
    
    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user information and group assignments"""
        try:
            # Get user details
            user_response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Get user's groups
            groups_response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Extract user attributes
            attributes = {}
            for attr in user_response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']
            
            # Extract group names
            group_names = [group['GroupName'] for group in groups_response.get('Groups', [])]
            
            return {
                'username': username,
                'exists': True,
                'status': user_response.get('UserStatus'),
                'enabled': user_response.get('Enabled'),
                'email': attributes.get('email'),
                'given_name': attributes.get('given_name'),
                'family_name': attributes.get('family_name'),
                'groups': group_names,
                'group_count': len(group_names)
            }
            
        except self.cognito_client.exceptions.UserNotFoundException:
            return {
                'username': username,
                'exists': False,
                'error': 'User not found'
            }
        except Exception as e:
            return {
                'username': username,
                'exists': False,
                'error': str(e)
            }
    
    def verify_all_test_users(self) -> List[Dict[str, Any]]:
        """Verify all test users"""
        print("🔍 Verifying H-DCN Test Users")
        print(f"📍 User Pool ID: {self.user_pool_id}")
        print("=" * 80)
        
        results = []
        for username in TEST_USERNAMES:
            print(f"🔄 Checking user: {username}")
            user_info = self.get_user_info(username)
            results.append(user_info)
            
            if user_info['exists']:
                print(f"✅ User exists")
                print(f"   Status: {user_info['status']}")
                print(f"   Email: {user_info['email']}")
                print(f"   Name: {user_info['given_name']} {user_info['family_name']}")
                print(f"   Groups ({user_info['group_count']}): {', '.join(user_info['groups'])}")
            else:
                print(f"❌ User not found: {user_info.get('error', 'Unknown error')}")
            print()
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print verification summary"""
        print("=" * 80)
        print("📊 TEST USER VERIFICATION SUMMARY")
        print("=" * 80)
        
        existing_users = [r for r in results if r['exists']]
        missing_users = [r for r in results if not r['exists']]
        
        print(f"✅ Existing users: {len(existing_users)}")
        print(f"❌ Missing users: {len(missing_users)}")
        print()
        
        if existing_users:
            print("✅ EXISTING TEST USERS:")
            for user in existing_users:
                role_type = self.get_role_type_from_groups(user['groups'])
                print(f"  • {user['username']} ({role_type})")
                print(f"    Groups: {', '.join(user['groups'])}")
            print()
        
        if missing_users:
            print("❌ MISSING TEST USERS:")
            for user in missing_users:
                print(f"  • {user['username']}: {user.get('error', 'Unknown error')}")
            print()
        
        print("🧪 NEXT STEPS:")
        if len(existing_users) == len(TEST_USERNAMES):
            print("✅ All test users exist and are ready for testing!")
            print("1. Test login with each user type")
            print("2. Verify JWT tokens contain correct cognito:groups")
            print("3. Test role-based UI rendering and permissions")
            print("4. Verify field-level access control")
        else:
            print("⚠️  Some test users are missing. Run create_test_users.py to create them.")
    
    def get_role_type_from_groups(self, groups: List[str]) -> str:
        """Determine role type based on group assignments"""
        if 'Members_CRUD_All' in groups:
            return "Member Administration"
        elif 'Members_Status_Approve' in groups:
            return "National Chairman"
        elif 'Events_CRUD_All' in groups and 'Products_CRUD_All' in groups:
            return "Webmaster"
        elif 'hdcnLeden' in groups:
            return "Regular Member"
        else:
            return "Unknown Role"

def main():
    """Main function to verify test users"""
    try:
        verifier = CognitoTestUserVerifier(USER_POOL_ID)
        results = verifier.verify_all_test_users()
        verifier.print_summary(results)
        
        # Exit with appropriate code
        missing_count = len([r for r in results if not r['exists']])
        if missing_count > 0:
            exit(1)
        else:
            exit(0)
            
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()