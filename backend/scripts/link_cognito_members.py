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

class CognitoMemberLinker:
    """
    Links Cognito users to member records by adding custom:member_id attribute.
    Provides comprehensive error handling and validation.
    """
    
    def __init__(self, user_pool_id: str = 'eu-west-1_OAT3oPCIm', region: str = 'eu-west-1'):
        """Initialize the linker with AWS clients and configuration."""
        try:
            self.cognito = boto3.client('cognito-idp', region_name=region)
            self.user_pool_id = user_pool_id
            self.region = region
            logger.info(f"Initialized CognitoMemberLinker for user pool: {user_pool_id} in region: {region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def validate_analysis_file(self, analysis_file: str) -> Dict:
        """
        Validate and load the analysis file.
        
        Args:
            analysis_file: Path to the analysis JSON file
            
        Returns:
            Dict: Loaded analysis data
            
        Raises:
            FileNotFoundError: If analysis file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            ValueError: If required fields are missing
        """
        try:
            with open(analysis_file, 'r') as f:
                analysis = json.load(f)
            
            # Validate required fields
            required_fields = ['matched_users', 'summary']
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Analysis file missing required field: {field}")
            
            logger.info(f"Successfully loaded analysis file: {analysis_file}")
            return analysis
            
        except FileNotFoundError:
            logger.error(f"Analysis file not found: {analysis_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in analysis file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading analysis file: {str(e)}")
            raise
    
    def get_users_to_link(self, analysis: Dict) -> List[Dict]:
        """
        Extract users that need linking from analysis data.
        
        Args:
            analysis: Analysis data dictionary
            
        Returns:
            List[Dict]: Users that need member_id linking
        """
        matched_users = analysis.get('matched_users', [])
        users_to_link = []
        
        for user in matched_users:
            # Skip users that already have member_id
            if user.get('current_member_id'):
                logger.debug(f"User {user.get('email')} already has member_id: {user.get('current_member_id')}")
                continue
            
            # Validate required fields
            required_fields = ['username', 'email', 'matched_member_id']
            if all(field in user and user[field] for field in required_fields):
                users_to_link.append(user)
            else:
                logger.warning(f"Skipping user with missing data: {user}")
        
        logger.info(f"Found {len(users_to_link)} users that need linking")
        return users_to_link
    
    def validate_user_pool_access(self) -> bool:
        """
        Validate that we have access to the Cognito User Pool.
        
        Returns:
            bool: True if access is valid, False otherwise
        """
        try:
            # Try to describe the user pool to validate access
            self.cognito.describe_user_pool(UserPoolId=self.user_pool_id)
            logger.info("Successfully validated Cognito User Pool access")
            return True
        except Exception as e:
            logger.error(f"Failed to access Cognito User Pool: {str(e)}")
            return False
    
    def link_single_user(self, user: Dict) -> Tuple[bool, str]:
        """
        Link a single user to their member record.
        
        Args:
            user: User dictionary with username, email, and matched_member_id
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            username = user['username']
            member_id = str(user['matched_member_id'])
            email = user['email']
            
            # Validate member_id is not empty
            if not member_id or member_id == 'None':
                return False, f"Invalid member_id for user {email}: {member_id}"
            
            # Update user attributes
            self.cognito.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'custom:member_id',
                        'Value': member_id
                    }
                ]
            )
            
            logger.info(f"✅ Successfully linked {email} -> member_id: {member_id}")
            return True, ""
            
        except self.cognito.exceptions.UserNotFoundException:
            error_msg = f"User not found in Cognito: {user.get('username', 'unknown')}"
            logger.error(error_msg)
            return False, error_msg
        except self.cognito.exceptions.InvalidParameterException as e:
            error_msg = f"Invalid parameter for user {user.get('email', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error linking user {user.get('email', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def perform_dry_run(self, users_to_link: List[Dict]) -> None:
        """
        Perform a dry run showing what would be linked.
        
        Args:
            users_to_link: List of users to be linked
        """
        print("\n" + "="*50)
        print("DRY RUN MODE - NO CHANGES WILL BE MADE")
        print("="*50)
        
        if not users_to_link:
            print("No users need linking.")
            return
        
        print(f"\nThe following {len(users_to_link)} users would be linked:")
        print("-" * 60)
        
        for i, user in enumerate(users_to_link, 1):
            email = user.get('email', 'unknown')
            member_id = user.get('matched_member_id', 'unknown')
            member_name = user.get('member_name', 'N/A')
            
            print(f"{i:3d}. {email:<30} -> member_id: {member_id} ({member_name})")
        
        print("-" * 60)
        print(f"\nTo execute for real, add --execute flag to the command")
    
    def execute_linking(self, users_to_link: List[Dict]) -> Dict:
        """
        Execute the actual linking process.
        
        Args:
            users_to_link: List of users to be linked
            
        Returns:
            Dict: Results summary with success/error counts and details
        """
        if not users_to_link:
            logger.info("No users need linking.")
            return {
                'total_processed': 0,
                'successful': 0,
                'errors': 0,
                'successful_links': [],
                'failed_links': []
            }
        
        print(f"\nLinking {len(users_to_link)} users...")
        print("-" * 50)
        
        successful_links = []
        failed_links = []
        
        for i, user in enumerate(users_to_link, 1):
            email = user.get('email', 'unknown')
            print(f"Processing {i}/{len(users_to_link)}: {email}")
            
            success, error_msg = self.link_single_user(user)
            
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
            'failed_links': failed_links
        }
        
        print("-" * 50)
        print(f"Linking complete!")
        print(f"  Successful: {results['successful']}")
        print(f"  Errors: {results['errors']}")
        
        if failed_links:
            print(f"\nFailed links:")
            for failed in failed_links:
                user_email = failed['user'].get('email', 'unknown')
                print(f"  - {user_email}: {failed['error']}")
        
        return results
    
    def save_results(self, results: Dict, analysis_file: str) -> str:
        """
        Save linking results to a timestamped file.
        
        Args:
            results: Results dictionary from execute_linking
            analysis_file: Original analysis file name for reference
            
        Returns:
            str: Path to the saved results file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'cognito_linking_results_{timestamp}.json'
        
        # Add metadata to results
        results_with_metadata = {
            'timestamp': timestamp,
            'source_analysis_file': analysis_file,
            **results
        }
        
        try:
            with open(results_file, 'w') as f:
                json.dump(results_with_metadata, f, indent=2, default=str)
            
            logger.info(f"Results saved to {results_file}")
            print(f"\nResults saved to: {results_file}")
            return results_file
            
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            print(f"Warning: Could not save results to file: {str(e)}")
            return ""


def main():
    """Main function to handle command line arguments and execute linking."""
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python link_cognito_members.py <analysis_file> [--execute]")
        print("\nOptions:")
        print("  analysis_file    Path to the analysis JSON file from analyze_cognito_member_links.py")
        print("  --execute        Actually perform the linking (default is dry run)")
        print("\nExample:")
        print("  python link_cognito_members.py cognito_member_analysis_20260112_153447.json")
        print("  python link_cognito_members.py cognito_member_analysis_20260112_153447.json --execute")
        sys.exit(1)
    
    analysis_file = sys.argv[1]
    dry_run = '--execute' not in sys.argv
    
    try:
        # Initialize the linker
        linker = CognitoMemberLinker()
        
        # Validate Cognito access
        if not linker.validate_user_pool_access():
            print("❌ Cannot access Cognito User Pool. Check your AWS credentials and permissions.")
            sys.exit(1)
        
        # Load and validate analysis file
        print(f"Loading analysis file: {analysis_file}")
        analysis = linker.validate_analysis_file(analysis_file)
        
        # Get users that need linking
        users_to_link = linker.get_users_to_link(analysis)
        
        if dry_run:
            # Perform dry run
            linker.perform_dry_run(users_to_link)
        else:
            # Execute actual linking
            print("⚠️  EXECUTING REAL LINKING - This will modify Cognito user attributes!")
            print("Press Ctrl+C within 5 seconds to cancel...")
            
            import time
            for i in range(5, 0, -1):
                print(f"Starting in {i}...", end='\r')
                time.sleep(1)
            print("Starting now!     ")
            
            results = linker.execute_linking(users_to_link)
            linker.save_results(results, analysis_file)
            
            # Exit with error code if there were failures
            if results['errors'] > 0:
                print(f"\n⚠️  Completed with {results['errors']} errors. Check the results file for details.")
                sys.exit(1)
            else:
                print(f"\n✅ All {results['successful']} users linked successfully!")
    
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()