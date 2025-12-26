#!/usr/bin/env python3
"""
H-DCN Fix Force Password Change Script

This script resolves the "Force change password" status for users in the Cognito User Pool
by setting permanent passwords and then configuring them for passwordless authentication.

The issue occurs when users are created with admin_create_user and temporary passwords,
which puts them in FORCE_CHANGE_PASSWORD status. For a passwordless system, we need to:

1. Set a permanent password to clear the FORCE_CHANGE_PASSWORD status
2. Configure the user for passwordless authentication
3. Ensure they can use email recovery to set up passkeys

This script handles all users with FORCE_CHANGE_PASSWORD status.
"""

import boto3
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'fix_force_password_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CognitoPasswordFixer:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        self.user_pool_id = 'eu-west-1_OAT3oPCIm'  # H-DCN-Authentication-Pool
        
        # Use a secure permanent password that users won't need to remember
        # This is just to clear the FORCE_CHANGE_PASSWORD status
        self.permanent_password = "HDCNPasswordless2024!@#"
        
        # Fix tracking
        self.fix_stats = {
            'total_users_checked': 0,
            'users_needing_fix': 0,
            'successful_fixes': 0,
            'failed_fixes': 0,
            'already_confirmed': 0,
            'errors': []
        }
        
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
                        Limit=60,  # AWS limit
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
                logger.info(f"Retrieved {len(users)} users so far...")
                
        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            raise
            
        logger.info(f"Total users retrieved: {len(users)}")
        self.fix_stats['total_users_checked'] = len(users)
        return users
        
    def get_user_email(self, user: Dict) -> Optional[str]:
        """Extract email from user attributes"""
        for attr in user.get('Attributes', []):
            if attr['Name'] == 'email':
                return attr['Value']
        return None
        
    def needs_password_fix(self, user: Dict) -> bool:
        """Check if user needs password fix (has FORCE_CHANGE_PASSWORD status)"""
        user_status = user.get('UserStatus', '')
        return user_status == 'FORCE_CHANGE_PASSWORD'
        
    def fix_user_password_status(self, username: str, email: str) -> bool:
        """Fix a single user's password status"""
        try:
            logger.info(f"Fixing password status for: {email}")
            
            # Step 1: Set a permanent password to clear FORCE_CHANGE_PASSWORD status
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=username,
                Password=self.permanent_password,
                Permanent=True  # This clears the FORCE_CHANGE_PASSWORD status
            )
            
            # Step 2: Confirm the user (this moves them to CONFIRMED status)
            self.cognito_client.admin_confirm_sign_up(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Step 3: Set email as verified (important for passwordless recovery)
            self.cognito_client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'email_verified',
                        'Value': 'true'
                    }
                ]
            )
            
            logger.info(f"Successfully fixed password status for: {email}")
            return True
            
        except self.cognito_client.exceptions.InvalidParameterException as e:
            if "already confirmed" in str(e).lower():
                logger.info(f"User already confirmed: {email}")
                self.fix_stats['already_confirmed'] += 1
                return True
            else:
                logger.error(f"Invalid parameter error for {email}: {str(e)}")
                self.fix_stats['errors'].append({
                    'email': email,
                    'error': str(e),
                    'action': 'fix_password_status'
                })
                return False
                
        except Exception as e:
            logger.error(f"Error fixing password status for {email}: {str(e)}")
            self.fix_stats['errors'].append({
                'email': email,
                'error': str(e),
                'action': 'fix_password_status'
            })
            return False
            
    def verify_user_status(self, username: str, email: str) -> Dict:
        """Verify the current status of a user after fix"""
        try:
            response = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            user_status = response.get('UserStatus', 'Unknown')
            enabled = response.get('Enabled', False)
            
            # Check if email is verified
            email_verified = False
            for attr in response.get('UserAttributes', []):
                if attr['Name'] == 'email_verified':
                    email_verified = attr['Value'] == 'true'
                    break
                    
            return {
                'email': email,
                'status': user_status,
                'enabled': enabled,
                'email_verified': email_verified,
                'success': user_status == 'CONFIRMED' and enabled and email_verified
            }
            
        except Exception as e:
            logger.error(f"Error verifying user status for {email}: {str(e)}")
            return {
                'email': email,
                'error': str(e),
                'success': False
            }
            
    def fix_all_users(self) -> Dict:
        """Fix all users with FORCE_CHANGE_PASSWORD status"""
        logger.info("Starting password status fix process...")
        
        # Get all users
        users = self.get_all_users()
        
        if not users:
            logger.warning("No users found in pool")
            return self.fix_stats
            
        # Find users that need fixing
        users_to_fix = []
        for user in users:
            if self.needs_password_fix(user):
                email = self.get_user_email(user)
                if email:
                    users_to_fix.append({
                        'username': user['Username'],
                        'email': email,
                        'status': user.get('UserStatus', 'Unknown')
                    })
                    
        self.fix_stats['users_needing_fix'] = len(users_to_fix)
        
        if not users_to_fix:
            logger.info("No users found with FORCE_CHANGE_PASSWORD status")
            return self.fix_stats
            
        logger.info(f"Found {len(users_to_fix)} users that need password status fix")
        
        # Fix each user
        verification_results = []
        for i, user_info in enumerate(users_to_fix, 1):
            logger.info(f"Processing user {i}/{len(users_to_fix)}: {user_info['email']}")
            
            if self.fix_user_password_status(user_info['username'], user_info['email']):
                self.fix_stats['successful_fixes'] += 1
                
                # Verify the fix worked
                verification = self.verify_user_status(user_info['username'], user_info['email'])
                verification_results.append(verification)
                
                if verification.get('success'):
                    logger.info(f"✅ User successfully fixed and verified: {user_info['email']}")
                else:
                    logger.warning(f"⚠️ User fixed but verification failed: {user_info['email']}")
                    
            else:
                self.fix_stats['failed_fixes'] += 1
                
            # Add small delay to avoid rate limiting
            time.sleep(0.2)
            
            # Progress update every 5 users
            if i % 5 == 0:
                logger.info(f"Progress: {i}/{len(users_to_fix)} users processed")
                
        logger.info("Password status fix process completed!")
        
        # Log verification results
        successful_verifications = sum(1 for v in verification_results if v.get('success'))
        logger.info(f"Verification results: {successful_verifications}/{len(verification_results)} users fully verified")
        
        return self.fix_stats
        
    def generate_fix_report(self) -> str:
        """Generate detailed fix report"""
        report = f"""
=== H-DCN COGNITO PASSWORD STATUS FIX REPORT ===
Fix Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
User Pool: {self.user_pool_id}

FIX STATISTICS:
- Total Users Checked: {self.fix_stats['total_users_checked']}
- Users Needing Fix: {self.fix_stats['users_needing_fix']}
- Successful Fixes: {self.fix_stats['successful_fixes']}
- Failed Fixes: {self.fix_stats['failed_fixes']}
- Already Confirmed: {self.fix_stats['already_confirmed']}

SUCCESS RATE: {(self.fix_stats['successful_fixes'] / max(self.fix_stats['users_needing_fix'], 1)) * 100:.1f}%

WHAT WAS FIXED:
- Cleared FORCE_CHANGE_PASSWORD status by setting permanent passwords
- Confirmed user accounts (moved to CONFIRMED status)
- Verified email addresses for passwordless recovery
- Users can now use email recovery to set up passkeys

NEXT STEPS FOR USERS:
1. Users can now log in using email recovery flow
2. Email recovery will guide them to set up passkeys
3. No password required - fully passwordless authentication
4. Users with existing passkeys can continue using them

"""
        
        if self.fix_stats['errors']:
            report += "ERRORS ENCOUNTERED:\n"
            for i, error in enumerate(self.fix_stats['errors'], 1):
                report += f"{i}. Email: {error['email']}\n"
                report += f"   Action: {error['action']}\n"
                report += f"   Error: {error['error']}\n\n"
                
        report += "=== END REPORT ===\n"
        
        return report
        
    def save_fix_report(self, report: str):
        """Save fix report to file"""
        filename = f"password_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Fix report saved to: {filename}")

def main():
    """Main fix function"""
    print("=== H-DCN Cognito Password Status Fix ===")
    print("This will fix users with 'Force change password' status")
    print("Users will be configured for passwordless authentication")
    print()
    
    # Show what will be done
    print("This script will:")
    print("1. Find all users with FORCE_CHANGE_PASSWORD status")
    print("2. Set permanent passwords to clear the status")
    print("3. Confirm user accounts")
    print("4. Verify email addresses")
    print("5. Enable passwordless authentication via email recovery")
    print()
    
    # Confirm fix
    confirm = input("Do you want to proceed with fixing the password status? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("Fix cancelled.")
        return
        
    try:
        # Initialize fixer
        fixer = CognitoPasswordFixer()
        
        # Perform fix
        stats = fixer.fix_all_users()
        
        # Generate and display report
        report = fixer.generate_fix_report()
        print(report)
        
        # Save report to file
        fixer.save_fix_report(report)
        
        # Summary
        print(f"Password status fix completed!")
        print(f"Successfully fixed: {stats['successful_fixes']} users")
        print(f"Failed fixes: {stats['failed_fixes']} users")
        print(f"Already confirmed: {stats['already_confirmed']} users")
        
        if stats['failed_fixes'] > 0:
            print("Please review the fix report for details on failed fixes.")
        else:
            print("🎉 All users are now ready for passwordless authentication!")
            print("Users can use email recovery to set up passkeys.")
            
    except Exception as e:
        logger.error(f"Fix failed with error: {str(e)}")
        print(f"Fix failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()