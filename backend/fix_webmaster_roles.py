#!/usr/bin/env python3
"""
Fix Webmaster Role Assignments - H-DCN Cognito Authentication System

This script corrects the Webmaster test user role assignments to match
the design document specifications.

Current Webmaster groups: Members_Read_All, Events_CRUD_All, Products_CRUD_All, Communication_Export_All, System_User_Management
Required Webmaster groups: Members_Read_All, Events_CRUD_All, Products_CRUD_All, Communication_CRUD_All, System_CRUD_All
"""

import boto3
from datetime import datetime

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
REGION = "eu-west-1"
WEBMASTER_USERNAME = "test.webmaster@hdcn-test.nl"

# Correct Webmaster role assignments per design document
CORRECT_WEBMASTER_GROUPS = [
    "Members_Read_All",
    "Events_CRUD_All", 
    "Products_CRUD_All",
    "Communication_CRUD_All",  # Should be CRUD, not Export
    "System_CRUD_All"          # Should be CRUD, not User_Management
]

class WebmasterRoleFixer:
    """Fix Webmaster role assignments to match design document"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        
    def get_user_groups(self, username: str) -> list:
        """Get current groups assigned to a user"""
        try:
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except Exception as e:
            print(f"Error getting groups for {username}: {e}")
            return []
    
    def remove_user_from_group(self, username: str, group_name: str) -> bool:
        """Remove user from a specific group"""
        try:
            self.cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=group_name
            )
            print(f"  ✅ Removed from group: {group_name}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to remove from group {group_name}: {e}")
            return False
    
    def add_user_to_group(self, username: str, group_name: str) -> bool:
        """Add user to a specific group"""
        try:
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName=group_name
            )
            print(f"  ✅ Added to group: {group_name}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to add to group {group_name}: {e}")
            return False
    
    def fix_webmaster_roles(self) -> bool:
        """Fix Webmaster role assignments"""
        print("🔧 Fixing Webmaster Role Assignments")
        print(f"👤 User: {WEBMASTER_USERNAME}")
        print(f"📍 User Pool ID: {USER_POOL_ID}")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print("=" * 80)
        
        # Get current groups
        current_groups = self.get_user_groups(WEBMASTER_USERNAME)
        print(f"🔍 Current groups ({len(current_groups)}): {', '.join(current_groups)}")
        print(f"🎯 Target groups ({len(CORRECT_WEBMASTER_GROUPS)}): {', '.join(CORRECT_WEBMASTER_GROUPS)}")
        print()
        
        # Determine changes needed
        current_set = set(current_groups)
        target_set = set(CORRECT_WEBMASTER_GROUPS)
        
        groups_to_remove = current_set - target_set
        groups_to_add = target_set - current_set
        
        print(f"📤 Groups to remove ({len(groups_to_remove)}): {', '.join(sorted(groups_to_remove)) if groups_to_remove else 'None'}")
        print(f"📥 Groups to add ({len(groups_to_add)}): {', '.join(sorted(groups_to_add)) if groups_to_add else 'None'}")
        print()
        
        success = True
        
        # Remove incorrect groups
        if groups_to_remove:
            print("🗑️ Removing incorrect groups:")
            for group in groups_to_remove:
                if not self.remove_user_from_group(WEBMASTER_USERNAME, group):
                    success = False
            print()
        
        # Add correct groups
        if groups_to_add:
            print("➕ Adding correct groups:")
            for group in groups_to_add:
                if not self.add_user_to_group(WEBMASTER_USERNAME, group):
                    success = False
            print()
        
        # Verify final state
        final_groups = self.get_user_groups(WEBMASTER_USERNAME)
        final_correct = set(final_groups) == set(CORRECT_WEBMASTER_GROUPS)
        
        print("🔍 Final verification:")
        print(f"  Final groups ({len(final_groups)}): {', '.join(sorted(final_groups))}")
        print(f"  Groups correct: {'✅ Yes' if final_correct else '❌ No'}")
        
        if final_correct:
            print()
            print("🎉 Webmaster role assignments fixed successfully!")
            print("✅ Webmaster now has full system access as per design document")
            print("✅ Role assignments match design document specifications")
            print()
            print("📋 Webmaster Permissions (per design document):")
            print("  • Members: Read All")
            print("  • Events: CRUD All") 
            print("  • Products: CRUD All")
            print("  • Communication: CRUD All")
            print("  • System: CRUD All")
        else:
            print()
            print("❌ Failed to fix Webmaster role assignments")
            print("⚠️ Manual intervention may be required")
            success = False
        
        return success and final_correct

def main():
    """Main function to fix Webmaster roles"""
    try:
        fixer = WebmasterRoleFixer()
        success = fixer.fix_webmaster_roles()
        
        if success:
            print("🔄 Next Steps:")
            print("  1. ✅ Webmaster role assignments are now correct")
            print("  2. 🔄 Re-run role assignment verification")
            print("  3. 🔄 Test Webmaster login and permissions")
            print("  4. 🔄 Verify full system access works correctly")
        
        return success
        
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)