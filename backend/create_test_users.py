#!/usr/bin/env python3
"""
Create Test Users for H-DCN Cognito Authentication System

This script creates test users for each role type defined in the H-DCN system:
1. Regular Member (hdcnLeden)
2. Member Administration (multiple roles)
3. National Chairman (multiple roles)
4. Webmaster (multiple roles)

Usage:
    python create_test_users.py

Requirements:
    - AWS credentials configured
    - boto3 installed
    - Access to the H-DCN Cognito User Pool
"""

import boto3
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"  # H-DCN Cognito User Pool ID
DEFAULT_TEMP_PASSWORD = "TempPass123!"

# Test user definitions with their role combinations
TEST_USERS = [
    {
        "username": "test.regular@hdcn-test.nl",
        "email": "test.regular@hdcn-test.nl",
        "given_name": "Test",
        "family_name": "Regular",
        "role_type": "Regular Member",
        "groups": ["hdcnLeden"],
        "description": "Basic H-DCN member with access to personal data and webshop"
    },
    {
        "username": "test.memberadmin@hdcn-test.nl", 
        "email": "test.memberadmin@hdcn-test.nl",
        "given_name": "Test",
        "family_name": "MemberAdmin",
        "role_type": "Member Administration",
        "groups": [
            "Members_CRUD",
            "Events_Read", 
            "Products_Read",
            "Communication_Read",
            "Regio_All",
            "System_User_Management"
        ],
        "description": "Member administration with full member management permissions"
    },
    {
        "username": "test.chairman@hdcn-test.nl",
        "email": "test.chairman@hdcn-test.nl", 
        "given_name": "Test",
        "family_name": "Chairman",
        "role_type": "National Chairman",
        "groups": [
            "Members_Read",
            "Members_Status_Approve",
            "Events_Read",
            "Products_Read", 
            "Communication_Read",
            "Regio_All",
            "System_Logs_Read"
        ],
        "description": "National Chairman with read access and status approval permissions"
    },
    {
        "username": "test.webmaster@hdcn-test.nl",
        "email": "test.webmaster@hdcn-test.nl",
        "given_name": "Test", 
        "family_name": "Webmaster",
        "role_type": "Webmaster",
        "groups": [
            "Members_Read",
            "Events_CRUD",
            "Products_CRUD",
            "Communication_Export",  # Using available Communication group
            "Regio_All",
            "System_User_Management"     # Using available System group
        ],
        "description": "Webmaster with full system access and available CRUD permissions"
    }
]

class CognitoTestUserManager:
    """Manages creation and assignment of test users in Cognito"""
    
    def __init__(self, user_pool_id: str):
        self.user_pool_id = user_pool_id
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        self.results = []
        
    def check_user_exists(self, username: str) -> bool:
        """Check if a user already exists in the user pool"""
        try:
            self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return True
        except self.cognito_client.exceptions.UserNotFoundException:
            return False
        except Exception as e:
            print(f"Error checking user {username}: {str(e)}")
            return False
    
    def check_group_exists(self, group_name: str) -> bool:
        """Check if a group exists in the user pool"""
        try:
            self.cognito_client.get_group(
                UserPoolId=self.user_pool_id,
                GroupName=group_name
            )
            return True
        except self.cognito_client.exceptions.ResourceNotFoundException:
            return False
        except Exception as e:
            print(f"Error checking group {group_name}: {str(e)}")
            return False
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single test user with specified attributes and groups"""
        username = user_data["username"]
        email = user_data["email"]
        
        result = {
            "username": username,
            "role_type": user_data["role_type"],
            "success": False,
            "message": "",
            "groups_assigned": [],
            "groups_failed": []
        }
        
        try:
            # Check if user already exists
            if self.check_user_exists(username):
                result["message"] = f"User {username} already exists - skipping creation"
                result["success"] = True
                print(f"⚠️  User {username} already exists")
                return result
            
            # Prepare user attributes
            user_attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'given_name', 'Value': user_data.get("given_name", "Test")},
                {'Name': 'family_name', 'Value': user_data.get("family_name", "User")}
            ]
            
            # Create user in Cognito
            print(f"🔄 Creating user: {username} ({user_data['role_type']})")
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=user_attributes,
                TemporaryPassword=DEFAULT_TEMP_PASSWORD,
                MessageAction='SUPPRESS'  # Don't send welcome email for test users
            )
            
            print(f"✅ User {username} created successfully")
            result["success"] = True
            result["message"] = "User created successfully"
            
            # Assign user to groups
            groups = user_data.get("groups", [])
            for group_name in groups:
                try:
                    # Check if group exists
                    if not self.check_group_exists(group_name):
                        print(f"⚠️  Group {group_name} does not exist - skipping assignment")
                        result["groups_failed"].append(f"{group_name} (group not found)")
                        continue
                    
                    # Add user to group
                    self.cognito_client.admin_add_user_to_group(
                        UserPoolId=self.user_pool_id,
                        Username=username,
                        GroupName=group_name
                    )
                    result["groups_assigned"].append(group_name)
                    print(f"  ✅ Added to group: {group_name}")
                    
                except Exception as group_error:
                    error_msg = f"{group_name} ({str(group_error)})"
                    result["groups_failed"].append(error_msg)
                    print(f"  ❌ Failed to add to group {group_name}: {str(group_error)}")
            
        except Exception as e:
            result["message"] = f"Failed to create user: {str(e)}"
            print(f"❌ Failed to create user {username}: {str(e)}")
            
        return result
    
    def create_all_test_users(self) -> List[Dict[str, Any]]:
        """Create all test users defined in TEST_USERS"""
        print("🚀 Starting test user creation for H-DCN Cognito Authentication System")
        print(f"📍 User Pool ID: {self.user_pool_id}")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print("=" * 80)
        
        for user_data in TEST_USERS:
            result = self.create_user(user_data)
            self.results.append(result)
            print()  # Add spacing between users
        
        return self.results
    
    def print_summary(self):
        """Print a summary of the test user creation results"""
        print("=" * 80)
        print("📊 TEST USER CREATION SUMMARY")
        print("=" * 80)
        
        successful_users = [r for r in self.results if r["success"]]
        failed_users = [r for r in self.results if not r["success"]]
        
        print(f"✅ Successfully created/verified: {len(successful_users)} users")
        print(f"❌ Failed: {len(failed_users)} users")
        print()
        
        if successful_users:
            print("✅ SUCCESSFUL USERS:")
            for result in successful_users:
                print(f"  • {result['username']} ({result['role_type']})")
                if result["groups_assigned"]:
                    print(f"    Groups: {', '.join(result['groups_assigned'])}")
                if result["groups_failed"]:
                    print(f"    Failed groups: {', '.join(result['groups_failed'])}")
            print()
        
        if failed_users:
            print("❌ FAILED USERS:")
            for result in failed_users:
                print(f"  • {result['username']}: {result['message']}")
            print()
        
        print("🔐 TEST USER CREDENTIALS:")
        print(f"  Temporary Password: {DEFAULT_TEMP_PASSWORD}")
        print("  Note: Users will need to set up passwordless authentication on first login")
        print()
        
        print("🧪 TESTING INSTRUCTIONS:")
        print("1. Use these test users to verify role-based authentication")
        print("2. Test login with each user type to verify permissions")
        print("3. Verify JWT tokens contain correct cognito:groups")
        print("4. Test role-based UI rendering and access control")
        print("5. Verify field-level permissions work correctly")
        
    def save_results_to_file(self, filename: str = None):
        """Save results to a JSON file for reference"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_user_creation_results_{timestamp}.json"
        
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "user_pool_id": self.user_pool_id,
            "total_users": len(self.results),
            "successful_users": len([r for r in self.results if r["success"]]),
            "failed_users": len([r for r in self.results if not r["success"]]),
            "results": self.results,
            "test_credentials": {
                "temporary_password": DEFAULT_TEMP_PASSWORD,
                "note": "Users need to set up passwordless authentication on first login"
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"📄 Results saved to: {filename}")

def main():
    """Main function to create test users"""
    try:
        # Initialize the test user manager
        manager = CognitoTestUserManager(USER_POOL_ID)
        
        # Create all test users
        results = manager.create_all_test_users()
        
        # Print summary
        manager.print_summary()
        
        # Save results to file
        manager.save_results_to_file()
        
        # Exit with appropriate code
        failed_count = len([r for r in results if not r["success"]])
        if failed_count > 0:
            print(f"⚠️  {failed_count} users failed to create properly")
            sys.exit(1)
        else:
            print("🎉 All test users created successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()