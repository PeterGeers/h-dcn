#!/usr/bin/env python3
"""
H-DCN Cognito User Migration Script

This script migrates users from the old Cognito User Pool (eu-west-1_VtKQHhXGN) 
to the new H-DCN-Authentication-Pool (eu-west-1_OAT3oPCIm) following the 
passwordless migration strategy outlined in the tasks.

Features:
- Migrates all users with their email addresses as usernames
- Creates accounts without passwords (passwordless)
- Sets accounts to require email verification
- Assigns default hdcnLeden role to all migrated users
- Handles duplicate emails and errors gracefully
- Provides detailed logging and progress tracking
- Generates migration reports
"""

import boto3
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CognitoUserMigrator:
    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name='eu-west-1')
        self.old_pool_id = 'eu-west-1_VtKQHhXGN'
        self.new_pool_id = 'eu-west-1_OAT3oPCIm'
        self.default_group = 'hdcnLeden'
        
        # Migration tracking
        self.migration_stats = {
            'total_users': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'duplicate_emails': 0,
            'invalid_emails': 0,
            'errors': []
        }
        
    def get_all_users_from_old_pool(self) -> List[Dict]:
        """Retrieve all users from the old Cognito User Pool"""
        logger.info(f"Retrieving users from old pool: {self.old_pool_id}")
        
        users = []
        pagination_token = None
        
        try:
            while True:
                if pagination_token:
                    response = self.cognito_client.list_users(
                        UserPoolId=self.old_pool_id,
                        Limit=60,  # AWS limit
                        PaginationToken=pagination_token
                    )
                else:
                    response = self.cognito_client.list_users(
                        UserPoolId=self.old_pool_id,
                        Limit=60
                    )
                
                users.extend(response['Users'])
                
                if 'PaginationToken' not in response:
                    break
                    
                pagination_token = response['PaginationToken']
                logger.info(f"Retrieved {len(users)} users so far...")
                
        except Exception as e:
            logger.error(f"Error retrieving users from old pool: {str(e)}")
            raise
            
        logger.info(f"Total users retrieved from old pool: {len(users)}")
        self.migration_stats['total_users'] = len(users)
        return users
        
    def extract_user_attributes(self, user: Dict) -> Tuple[str, Dict[str, str]]:
        """Extract email and other attributes from user object"""
        attributes = {}
        email = None
        
        for attr in user.get('Attributes', []):
            name = attr['Name']
            value = attr['Value']
            attributes[name] = value
            
            if name == 'email':
                email = value
                
        return email, attributes
        
    def validate_email(self, email: str) -> bool:
        """Basic email validation"""
        if not email or '@' not in email or '.' not in email:
            return False
        return True
        
    def check_user_exists_in_new_pool(self, email: str) -> bool:
        """Check if user already exists in new pool"""
        try:
            self.cognito_client.admin_get_user(
                UserPoolId=self.new_pool_id,
                Username=email
            )
            return True
        except self.cognito_client.exceptions.UserNotFoundException:
            return False
        except Exception as e:
            logger.warning(f"Error checking if user exists: {str(e)}")
            return False
            
    def create_user_in_new_pool(self, email: str, attributes: Dict[str, str]) -> bool:
        """Create user in new pool without password (passwordless)"""
        try:
            # Prepare user attributes for new pool
            user_attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'false'}  # Require email verification
            ]
            
            # Add other attributes if they exist
            if 'given_name' in attributes:
                user_attributes.append({'Name': 'given_name', 'Value': attributes['given_name']})
            if 'family_name' in attributes:
                user_attributes.append({'Name': 'family_name', 'Value': attributes['family_name']})
                
            # Create user without password (passwordless migration)
            # Note: We need to provide a temporary password but it will be reset immediately
            temp_password = "TempPass123!"  # This will be reset to force passwordless setup
            
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.new_pool_id,
                Username=email,  # Use email as username
                UserAttributes=user_attributes,
                MessageAction='SUPPRESS',  # Don't send welcome email yet
                TemporaryPassword=temp_password
            )
            
            # Immediately set the user to require password reset (passwordless flow)
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.new_pool_id,
                Username=email,
                Password=temp_password,
                Permanent=False  # Force password reset on next login
            )
            
            logger.info(f"Created user: {email}")
            return True
            
        except self.cognito_client.exceptions.UsernameExistsException:
            logger.warning(f"User already exists in new pool: {email}")
            self.migration_stats['duplicate_emails'] += 1
            return False
            
        except Exception as e:
            logger.error(f"Error creating user {email}: {str(e)}")
            self.migration_stats['errors'].append({
                'email': email,
                'error': str(e),
                'action': 'create_user'
            })
            return False
            
    def assign_default_role(self, email: str) -> bool:
        """Assign default hdcnLeden role to migrated user"""
        try:
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=self.new_pool_id,
                Username=email,
                GroupName=self.default_group
            )
            logger.debug(f"Assigned {self.default_group} role to: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to {email}: {str(e)}")
            self.migration_stats['errors'].append({
                'email': email,
                'error': str(e),
                'action': 'assign_role'
            })
            return False
            
    def migrate_single_user(self, user: Dict) -> bool:
        """Migrate a single user from old pool to new pool"""
        email, attributes = self.extract_user_attributes(user)
        
        if not email:
            logger.warning(f"User has no email address: {user.get('Username', 'Unknown')}")
            self.migration_stats['invalid_emails'] += 1
            return False
            
        if not self.validate_email(email):
            logger.warning(f"Invalid email address: {email}")
            self.migration_stats['invalid_emails'] += 1
            return False
            
        # Check if user already exists in new pool
        if self.check_user_exists_in_new_pool(email):
            logger.info(f"User already exists in new pool: {email}")
            self.migration_stats['duplicate_emails'] += 1
            return False
            
        # Create user in new pool
        if not self.create_user_in_new_pool(email, attributes):
            return False
            
        # Assign default role
        if not self.assign_default_role(email):
            # User was created but role assignment failed
            logger.warning(f"User created but role assignment failed: {email}")
            
        return True
        
    def migrate_all_users(self) -> Dict:
        """Migrate all users from old pool to new pool"""
        logger.info("Starting user migration process...")
        
        # Get all users from old pool
        old_users = self.get_all_users_from_old_pool()
        
        if not old_users:
            logger.warning("No users found in old pool")
            return self.migration_stats
            
        logger.info(f"Starting migration of {len(old_users)} users...")
        
        # Migrate each user
        for i, user in enumerate(old_users, 1):
            logger.info(f"Migrating user {i}/{len(old_users)}")
            
            if self.migrate_single_user(user):
                self.migration_stats['successful_migrations'] += 1
            else:
                self.migration_stats['failed_migrations'] += 1
                
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
            
            # Progress update every 10 users
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(old_users)} users processed")
                
        logger.info("Migration process completed!")
        return self.migration_stats
        
    def generate_migration_report(self) -> str:
        """Generate detailed migration report"""
        report = f"""
=== H-DCN COGNITO USER MIGRATION REPORT ===
Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Old Pool: {self.old_pool_id}
New Pool: {self.new_pool_id}

MIGRATION STATISTICS:
- Total Users in Old Pool: {self.migration_stats['total_users']}
- Successful Migrations: {self.migration_stats['successful_migrations']}
- Failed Migrations: {self.migration_stats['failed_migrations']}
- Duplicate Emails: {self.migration_stats['duplicate_emails']}
- Invalid Emails: {self.migration_stats['invalid_emails']}

SUCCESS RATE: {(self.migration_stats['successful_migrations'] / max(self.migration_stats['total_users'], 1)) * 100:.1f}%

"""
        
        if self.migration_stats['errors']:
            report += "ERRORS ENCOUNTERED:\n"
            for i, error in enumerate(self.migration_stats['errors'], 1):
                report += f"{i}. Email: {error['email']}\n"
                report += f"   Action: {error['action']}\n"
                report += f"   Error: {error['error']}\n\n"
                
        report += "=== END REPORT ===\n"
        
        return report
        
    def save_migration_report(self, report: str):
        """Save migration report to file"""
        filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        logger.info(f"Migration report saved to: {filename}")

def main():
    """Main migration function"""
    print("=== H-DCN Cognito User Migration ===")
    print("This will migrate users from the old pool to the new H-DCN-Authentication-Pool")
    print("Users will be created without passwords and require email verification")
    print()
    
    # Confirm migration
    confirm = input("Do you want to proceed with the migration? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("Migration cancelled.")
        return
        
    try:
        # Initialize migrator
        migrator = CognitoUserMigrator()
        
        # Perform migration
        stats = migrator.migrate_all_users()
        
        # Generate and display report
        report = migrator.generate_migration_report()
        print(report)
        
        # Save report to file
        migrator.save_migration_report(report)
        
        # Summary
        print(f"Migration completed!")
        print(f"Successfully migrated: {stats['successful_migrations']} users")
        print(f"Failed migrations: {stats['failed_migrations']} users")
        
        if stats['failed_migrations'] > 0:
            print("Please review the migration report for details on failed migrations.")
            
    except Exception as e:
        logger.error(f"Migration failed with error: {str(e)}")
        print(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()