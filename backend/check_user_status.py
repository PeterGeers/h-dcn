#!/usr/bin/env python3
"""
H-DCN Check User Status Script

This script checks the current status of all users in the Cognito User Pool
and provides a detailed report of user statuses, particularly focusing on
users with "Force change password" status.
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitoUserStatusChecker:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        self.user_pool_id = 'eu-west-1_OAT3oPCIm'  # H-DCN-Authentication-Pool
        
    def get_all_users(self) -> List[Dict]:
        """Retrieve all users from the Cognito User Pool"""
        logger.info(f"Retrieving users from pool: {self.user_pool_id}")
        
        users = []
        pagination_token = None
        
        try:
            while True:
                if pagination_token:
                    response = self.cognito_client.list_users(
                        UserPoolId=self.user_pool_id,
                        Limit=60,
                        PaginationToken=pagination_token
                    )
                else:
                    response = self.cognito_client.list_users(
                        UserPoolId=self.user_pool_id,
                        Limit=60
                    )
                
                users.extend(response['Users'])
                
                if 'PaginationToken' not in response:
                    break
                    
                pagination_token = response['PaginationToken']
                
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            raise
            
        logger.info(f"Total users retrieved: {len(users)}")
        return users
        
    def extract_user_info(self, user: Dict) -> Dict:
        """Extract relevant information from user object"""
        # Basic info
        username = user.get('Username', 'Unknown')
        user_status = user.get('UserStatus', 'Unknown')
        enabled = user.get('Enabled', False)
        created = user.get('UserCreateDate', 'Unknown')
        modified = user.get('UserLastModifiedDate', 'Unknown')
        
        # Extract attributes
        email = None
        email_verified = False
        given_name = None
        family_name = None
        
        for attr in user.get('Attributes', []):
            name = attr['Name']
            value = attr['Value']
            
            if name == 'email':
                email = value
            elif name == 'email_verified':
                email_verified = value == 'true'
            elif name == 'given_name':
                given_name = value
            elif name == 'family_name':
                family_name = value
                
        # Determine display name
        if given_name and family_name:
            display_name = f"{given_name} {family_name}"
        elif given_name:
            display_name = given_name
        else:
            display_name = email or username
            
        return {
            'username': username,
            'email': email or 'No email',
            'display_name': display_name,
            'user_status': user_status,
            'enabled': enabled,
            'email_verified': email_verified,
            'created': created,
            'modified': modified,
            'needs_password_fix': user_status == 'FORCE_CHANGE_PASSWORD'
        }
        
    def analyze_users(self, users: List[Dict]) -> Dict:
        """Analyze user statuses and generate statistics"""
        user_info_list = []
        status_counts = defaultdict(int)
        
        for user in users:
            user_info = self.extract_user_info(user)
            user_info_list.append(user_info)
            status_counts[user_info['user_status']] += 1
            
        # Calculate additional statistics
        total_users = len(user_info_list)
        enabled_users = sum(1 for u in user_info_list if u['enabled'])
        verified_emails = sum(1 for u in user_info_list if u['email_verified'])
        needs_fix = sum(1 for u in user_info_list if u['needs_password_fix'])
        
        return {
            'user_info_list': user_info_list,
            'total_users': total_users,
            'enabled_users': enabled_users,
            'verified_emails': verified_emails,
            'needs_password_fix': needs_fix,
            'status_counts': dict(status_counts)
        }
        
    def generate_status_report(self, analysis: Dict) -> str:
        """Generate detailed status report"""
        user_info_list = analysis['user_info_list']
        
        report = f"""
=== H-DCN COGNITO USER STATUS REPORT ===
Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
User Pool: {self.user_pool_id}

SUMMARY STATISTICS:
- Total Users: {analysis['total_users']}
- Enabled Users: {analysis['enabled_users']}
- Verified Email Addresses: {analysis['verified_emails']}
- Users Needing Password Fix: {analysis['needs_password_fix']}

USER STATUS BREAKDOWN:
"""
        
        for status, count in analysis['status_counts'].items():
            percentage = (count / analysis['total_users']) * 100
            report += f"- {status}: {count} users ({percentage:.1f}%)\n"
            
        if analysis['needs_password_fix'] > 0:
            report += f"""
⚠️  ATTENTION: {analysis['needs_password_fix']} users have FORCE_CHANGE_PASSWORD status
This prevents them from using passwordless authentication.

USERS NEEDING PASSWORD FIX:
"""
            
            force_change_users = [u for u in user_info_list if u['needs_password_fix']]
            for i, user in enumerate(force_change_users, 1):
                report += f"{i:3d}. {user['email']}\n"
                report += f"     Name: {user['display_name']}\n"
                report += f"     Status: {user['user_status']} | Enabled: {user['enabled']}\n"
                report += f"     Email Verified: {user['email_verified']}\n"
                report += "\n"
                
            report += f"""
RECOMMENDED ACTION:
Run the fix script to resolve FORCE_CHANGE_PASSWORD status:
    python backend/fix_force_password_change.py

This will:
1. Clear the FORCE_CHANGE_PASSWORD status
2. Confirm user accounts
3. Verify email addresses
4. Enable passwordless authentication via email recovery
"""
        else:
            report += "\n✅ All users are ready for passwordless authentication!\n"
            
        report += "\n=== DETAILED USER LIST ===\n"
        
        for i, user in enumerate(user_info_list, 1):
            status_icon = "⚠️" if user['needs_password_fix'] else "✅"
            report += f"{i:3d}. {status_icon} {user['email']}\n"
            report += f"     Name: {user['display_name']}\n"
            report += f"     Status: {user['user_status']} | Enabled: {user['enabled']}\n"
            report += f"     Email Verified: {user['email_verified']}\n"
            if user['needs_password_fix']:
                report += f"     ⚠️  NEEDS PASSWORD FIX\n"
            report += "\n"
            
        report += "=== END REPORT ===\n"
        
        return report
        
    def save_status_report(self, report: str):
        """Save status report to file"""
        filename = f"user_status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Status report saved to: {filename}")
        return filename

def main():
    """Main function to check user statuses"""
    print("=== H-DCN Cognito User Status Check ===")
    print("Checking all users in the H-DCN Authentication Pool...")
    print()
    
    try:
        # Initialize checker
        checker = CognitoUserStatusChecker()
        
        # Get all users
        users = checker.get_all_users()
        
        if not users:
            print("No users found in the pool.")
            return
            
        # Analyze users
        analysis = checker.analyze_users(users)
        
        # Generate and display report
        report = checker.generate_status_report(analysis)
        print(report)
        
        # Save report to file
        filename = checker.save_status_report(report)
        
        # Summary
        print(f"Status check completed!")
        print(f"Report saved to: {filename}")
        
        if analysis['needs_password_fix'] > 0:
            print(f"\n⚠️  ACTION REQUIRED: {analysis['needs_password_fix']} users need password status fix")
            print("Run: python backend/fix_force_password_change.py")
        else:
            print("\n✅ All users are ready for passwordless authentication!")
            
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        print(f"Status check failed: {str(e)}")

if __name__ == "__main__":
    main()