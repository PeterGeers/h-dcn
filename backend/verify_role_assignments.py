#!/usr/bin/env python3
"""
Verify Role Assignments Match Design Document - H-DCN Cognito Authentication System

This script verifies that the test users have the correct role combinations
as specified in the design document permission matrix.

Design Document Specifications:
- Member Administration: Members_CRUD, Events_Read, Products_Read, Communication_Read, System_User_Management, Regio_All
- National Chairman: Members_Read, Members_Status_Approve, Events_Read, Products_Read, Communication_Read, System_Logs_Read, Regio_All
- Webmaster: Members_Read, Events_CRUD, Products_CRUD, Communication_CRUD, System_User_Management, Regio_All
- Regular Members: hdcnLeden
"""

import boto3
import json
from datetime import datetime
from typing import Dict, List, Set

# Configuration
USER_POOL_ID = "eu-west-1_OAT3oPCIm"
REGION = "eu-west-1"

# Expected role assignments from design document
EXPECTED_ROLE_ASSIGNMENTS = {
    "test.memberadmin@hdcn-test.nl": {
        "role_type": "Member Administration",
        "expected_groups": {
            "Members_CRUD",
            "Events_Read", 
            "Products_Read",
            "Communication_Read",
            "Regio_All",
            "System_User_Management"
        },
        "permissions": [
            "CRUD All member data",
            "Read all events", 
            "Read all products",
            "Read all communication",
            "User management"
        ]
    },
    "test.chairman@hdcn-test.nl": {
        "role_type": "National Chairman",
        "expected_groups": {
            "Members_Read",
            "Members_Status_Approve",
            "Events_Read",
            "Products_Read",
            "Communication_Read", 
            "Regio_All",
            "System_Logs_Read"
        },
        "permissions": [
            "Read all member data + approve status",
            "Read all events",
            "Read all products", 
            "Read all communication",
            "Read system logs"
        ]
    },
    "test.webmaster@hdcn-test.nl": {
        "role_type": "Webmaster",
        "expected_groups": {
            "Members_Read",
            "Events_CRUD",
            "Products_CRUD",
            "Communication_CRUD",  # Note: Using available Communication group
            "System_User_Management",  # Note: Using available System group
            "Regio_All"
        },
        "permissions": [
            "Read all member data",
            "CRUD all events",
            "CRUD all products",
            "CRUD all communication", 
            "System user management"
        ],
        "note": "Updated to use new role structure with Permission + Region combinations"
    },
    "test.regular@hdcn-test.nl": {
        "role_type": "Regular Member",
        "expected_groups": {
            "hdcnLeden"
        },
        "permissions": [
            "Update own personal data only",
            "Read public events",
            "Browse product catalog"
        ]
    }
}

class RoleAssignmentVerifier:
    """Verify that role assignments match design document specifications"""
    
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=REGION)
        self.verification_results = []
        
    def get_user_groups(self, username: str) -> Set[str]:
        """Get current groups assigned to a user"""
        try:
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            return {group['GroupName'] for group in response.get('Groups', [])}
        except Exception as e:
            print(f"Error getting groups for {username}: {e}")
            return set()
    
    def verify_user_role_assignment(self, username: str, expected_data: Dict) -> Dict:
        """Verify a single user's role assignment matches expectations"""
        result = {
            "username": username,
            "role_type": expected_data["role_type"],
            "success": False,
            "details": {},
            "issues": []
        }
        
        try:
            # Get actual groups
            actual_groups = self.get_user_groups(username)
            expected_groups = expected_data["expected_groups"]
            
            # Check if groups match exactly
            groups_match = actual_groups == expected_groups
            
            # Find missing and extra groups
            missing_groups = expected_groups - actual_groups
            extra_groups = actual_groups - expected_groups
            
            result["details"] = {
                "expected_groups": sorted(list(expected_groups)),
                "actual_groups": sorted(list(actual_groups)),
                "groups_match": groups_match,
                "missing_groups": sorted(list(missing_groups)),
                "extra_groups": sorted(list(extra_groups)),
                "permissions": expected_data["permissions"]
            }
            
            # Determine success
            if groups_match:
                result["success"] = True
            else:
                if missing_groups:
                    result["issues"].append(f"Missing groups: {sorted(list(missing_groups))}")
                if extra_groups:
                    result["issues"].append(f"Extra groups: {sorted(list(extra_groups))}")
            
            # Add note if present
            if "note" in expected_data:
                result["note"] = expected_data["note"]
                
        except Exception as e:
            result["issues"].append(f"Error verifying user: {str(e)}")
            
        return result
    
    def verify_all_role_assignments(self) -> List[Dict]:
        """Verify all test users have correct role assignments"""
        print("🔍 Verifying Role Assignments Match Design Document")
        print(f"📍 User Pool ID: {USER_POOL_ID}")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print("=" * 80)
        
        for username, expected_data in EXPECTED_ROLE_ASSIGNMENTS.items():
            print(f"🔄 Verifying: {username} ({expected_data['role_type']})")
            
            result = self.verify_user_role_assignment(username, expected_data)
            self.verification_results.append(result)
            
            if result["success"]:
                print(f"✅ Role assignment correct")
                print(f"   Groups ({len(result['details']['actual_groups'])}): {', '.join(result['details']['actual_groups'])}")
            else:
                print(f"❌ Role assignment issues:")
                for issue in result["issues"]:
                    print(f"   • {issue}")
                if result["details"]["missing_groups"]:
                    print(f"   Missing: {', '.join(result['details']['missing_groups'])}")
                if result["details"]["extra_groups"]:
                    print(f"   Extra: {', '.join(result['details']['extra_groups'])}")
            
            if "note" in result:
                print(f"   📝 Note: {result['note']}")
            
            print()
        
        return self.verification_results
    
    def print_summary(self):
        """Print verification summary"""
        print("=" * 80)
        print("📊 ROLE ASSIGNMENT VERIFICATION SUMMARY")
        print("=" * 80)
        
        successful_verifications = [r for r in self.verification_results if r["success"]]
        failed_verifications = [r for r in self.verification_results if not r["success"]]
        
        print(f"✅ Correct role assignments: {len(successful_verifications)}")
        print(f"❌ Incorrect role assignments: {len(failed_verifications)}")
        print()
        
        if successful_verifications:
            print("✅ CORRECT ROLE ASSIGNMENTS:")
            for result in successful_verifications:
                print(f"  • {result['username']} ({result['role_type']})")
                print(f"    Groups: {', '.join(result['details']['actual_groups'])}")
            print()
        
        if failed_verifications:
            print("❌ INCORRECT ROLE ASSIGNMENTS:")
            for result in failed_verifications:
                print(f"  • {result['username']} ({result['role_type']})")
                for issue in result["issues"]:
                    print(f"    Issue: {issue}")
            print()
        
        # Design document compliance
        total_users = len(self.verification_results)
        compliant_users = len(successful_verifications)
        compliance_rate = (compliant_users / total_users) * 100 if total_users > 0 else 0
        
        print(f"📋 DESIGN DOCUMENT COMPLIANCE: {compliance_rate:.1f}% ({compliant_users}/{total_users})")
        
        if compliance_rate == 100:
            print("🎉 All role assignments match design document specifications!")
            print("✅ Member Administration users have appropriate role combinations")
            print("✅ National Chairman users have correct permissions") 
            print("✅ Webmaster users have full system access")
            print("✅ Test users exist for each role type")
            print()
            print("🔄 Next Steps:")
            print("  1. ✅ Role assignments are correctly configured")
            print("  2. 🔄 Test role-based authentication flows")
            print("  3. 🔄 Verify JWT tokens contain correct groups")
            print("  4. 🔄 Test permission calculations and UI rendering")
        else:
            print("⚠️ Some role assignments need correction to match design document")
            print("❌ Review and fix role assignments before proceeding")
    
    def save_results(self, filename: str = None):
        """Save verification results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"role_assignment_verification_{timestamp}.json"
        
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "user_pool_id": USER_POOL_ID,
            "total_users": len(self.verification_results),
            "compliant_users": len([r for r in self.verification_results if r["success"]]),
            "compliance_rate": f"{(len([r for r in self.verification_results if r['success']]) / len(self.verification_results)) * 100:.1f}%",
            "design_document_compliant": all(r["success"] for r in self.verification_results),
            "verification_results": self.verification_results,
            "expected_assignments": {
                username: {
                    "role_type": data["role_type"],
                    "expected_groups": sorted(list(data["expected_groups"])),
                    "permissions": data["permissions"]
                }
                for username, data in EXPECTED_ROLE_ASSIGNMENTS.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"📄 Verification results saved to: {filename}")

def main():
    """Main verification function"""
    try:
        verifier = RoleAssignmentVerifier()
        
        # Verify all role assignments
        results = verifier.verify_all_role_assignments()
        
        # Print summary
        verifier.print_summary()
        
        # Save results
        verifier.save_results()
        
        # Exit with appropriate code
        all_compliant = all(r["success"] for r in results)
        if all_compliant:
            print("🎉 All role assignments are compliant with design document!")
            return True
        else:
            print("⚠️ Some role assignments need correction")
            return False
            
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)