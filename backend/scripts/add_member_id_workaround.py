#!/usr/bin/env python3
"""
Workaround script to add member_id to Cognito users without custom attribute.

Since we cannot add custom:member_id to an existing Cognito User Pool,
this script uses an alternative approach by storing the member_id in 
an existing custom attribute or as user metadata.

Options:
1. Use custom:email field (if not used for email)
2. Use custom:given_name or custom:family_name if available
3. Store in user's "name" field with a prefix
4. Use the profile field with JSON data

This script implements option 4 (profile field with JSON) as the safest approach.
"""

import boto3
import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitoMemberIdWorkaround:
    """
    Workaround to store member_id in Cognito users using existing attributes.
    Uses the 'profile' field to store JSON data including member_id.
    """
    
    def __init__(self, user_pool_id: str = 'eu-west-1_OAT3oPCIm', region: str = 'eu-west-1'):
        """Initialize the workaround with AWS clients and configuration."""
        try:
            self.cognito = boto3.client('cognito-idp', region_name=region)
            self.user_pool_id = user_pool_id
            self.region = region
            logger.info(f"Initialized CognitoMemberIdWorkaround for user pool: {user_pool_id} in region: {region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def get_user_profile_data(self, username: str) -> Dict:
        """
        Get current profile data for a user.
        
        Args:
            username: Cognito username
            
        Returns:
            Dict: Current profile data (parsed from JSON if exists)
        """
        try:
            response = self.cognito.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Look for existing profile attribute
            for attr in response.get('UserAttributes', []):
                if attr['Name'] == 'profile':
                    try:
                        return json.loads(attr['Value'])
                    except json.JSONDecodeError:
                        # If not valid JSON, treat as string and wrap it
                        return {'original_profile': attr['Value']}
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get user profile for {username}: {str(e)}")
            return {}
    
    def update_user_with_member_id(self, username: str, member_id: str, email: str = None) -> Tuple[bool, str]:
        """
        Update user's profile with member_id using JSON in profile field.
        
        Args:
            username: Cognito username
            member_id: Member ID to store
            email: User email for logging
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            # Get current profile data
            current_profile = self.get_user_profile_data(username)
            
            # Add member_id to profile data
            current_profile['member_id'] = member_id
            current_profile['member_id_added'] = datetime.now().isoformat()
            
            # Convert to JSON string
            profile_json = json.dumps(current_profile)
            
            # Update user attributes
            self.cognito.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'profile',
                        'Value': profile_json
                    }
                ]
            )
            
            logger.info(f"✅ Successfully added member_id to {email or username} -> member_id: {member_id}")
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to update user {email or username}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_member_id_from_user(self, username: str) -> Optional[str]:
        """
        Extract member_id from user's profile data.
        
        Args:
            username: Cognito username
            
        Returns:
            Optional[str]: Member ID if found, None otherwise
        """
        profile_data = self.get_user_profile_data(username)
        return profile_data.get('member_id')
    
    def link_users_from_analysis(self, analysis_file: str, dry_run: bool = True) -> Dict:
        """
        Link users using the workaround method based on analysis file.
        
        Args:
            analysis_file: Path to analysis JSON file
            dry_run: If True, only show what would be done
            
        Returns:
            Dict: Results summary
        """
        try:
            # Load analysis file
            with open(analysis_file, 'r') as f:
                analysis = json.load(f)
            
            matched_users = analysis.get('matched_users', [])
            users_to_link = [u for u in matched_users if not u.get('current_member_id')]
            
            if dry_run:
                print(f"\n{'='*60}")
                print("DRY RUN MODE - WORKAROUND METHOD")
                print("Using 'profile' field to store member_id as JSON")
                print(f"{'='*60}")
                
                if not users_to_link:
                    print("No users need linking.")
                    return {'total_processed': 0, 'successful': 0, 'errors': 0}
                
                print(f"\nThe following {len(users_to_link)} users would be linked:")
                print("-" * 60)
                
                for i, user in enumerate(users_to_link, 1):
                    email = user.get('email', 'unknown')
                    member_id = user.get('matched_member_id', 'unknown')
                    member_name = user.get('member_name', 'N/A')
                    
                    print(f"{i:3d}. {email:<30} -> member_id: {member_id} ({member_name})")
                
                print("-" * 60)
                print(f"\nTo execute for real, add --execute flag")
                return {'total_processed': len(users_to_link), 'successful': 0, 'errors': 0}
            
            # Execute actual linking
            print(f"\nLinking {len(users_to_link)} users using workaround method...")
            print("-" * 60)
            
            successful_links = []
            failed_links = []
            
            for i, user in enumerate(users_to_link, 1):
                email = user.get('email', 'unknown')
                username = user.get('username')
                member_id = str(user.get('matched_member_id', ''))
                
                print(f"Processing {i}/{len(users_to_link)}: {email}")
                
                success, error_msg = self.update_user_with_member_id(username, member_id, email)
                
                if success:
                    successful_links.append(user)
                    print(f"  ✅ Success")
                else:
                    failed_links.append({
                        'user': user,
                        'error': error_msg
                    })
                    print(f"  ❌ Failed: {error_msg}")
            
            results = {
                'total_processed': len(users_to_link),
                'successful': len(successful_links),
                'errors': len(failed_links),
                'successful_links': successful_links,
                'failed_links': failed_links,
                'method': 'profile_json_workaround'
            }
            
            print("-" * 60)
            print(f"Linking complete!")
            print(f"  Successful: {results['successful']}")
            print(f"  Errors: {results['errors']}")
            
            if failed_links:
                print(f"\nFailed links:")
                for failed in failed_links:
                    user_email = failed['user'].get('email', 'unknown')
                    print(f"  - {user_email}: {failed['error']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Fatal error in link_users_from_analysis: {str(e)}")
            raise


def main():
    """Main function to handle command line arguments and execute linking."""
    
    if len(sys.argv) < 2:
        print("Usage: python add_member_id_workaround.py <analysis_file> [--execute]")
        print("\nThis script uses a workaround method to store member_id in the 'profile' field")
        print("since custom:member_id cannot be added to existing Cognito User Pools.")
        print("\nOptions:")
        print("  analysis_file    Path to the analysis JSON file")
        print("  --execute        Actually perform the linking (default is dry run)")
        print("\nExample:")
        print("  python add_member_id_workaround.py cognito_member_analysis_20260112_153447.json")
        print("  python add_member_id_workaround.py cognito_member_analysis_20260112_153447.json --execute")
        sys.exit(1)
    
    analysis_file = sys.argv[1]
    dry_run = '--execute' not in sys.argv
    
    try:
        # Initialize the workaround
        workaround = CognitoMemberIdWorkaround()
        
        # Execute linking with workaround method
        results = workaround.link_users_from_analysis(analysis_file, dry_run)
        
        if not dry_run:
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = f'cognito_workaround_results_{timestamp}.json'
            
            results_with_metadata = {
                'timestamp': timestamp,
                'source_analysis_file': analysis_file,
                'method': 'profile_json_workaround',
                **results
            }
            
            with open(results_file, 'w') as f:
                json.dump(results_with_metadata, f, indent=2, default=str)
            
            print(f"\nResults saved to: {results_file}")
            
            if results['errors'] > 0:
                print(f"\n⚠️  Completed with {results['errors']} errors.")
                sys.exit(1)
            else:
                print(f"\n✅ All {results['successful']} users linked successfully using workaround method!")
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()