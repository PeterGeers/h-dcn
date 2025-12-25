#!/usr/bin/env python3
"""
H-DCN Organization Email Verification Script

This script helps verify the organization email address (webhulpje@h-dcn.nl) in AWS SES.
This is required to send emails from the official H-DCN email address.
"""

import boto3
import logging
import sys
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
AWS_REGION = 'eu-west-1'
ORGANIZATION_EMAIL = 'webhulpje@h-dcn.nl'

def verify_email_address():
    """Verify the organization email address in SES"""
    
    try:
        # Initialize SES client
        ses_client = boto3.client('ses', region_name=AWS_REGION)
        
        logger.info(f"Verifying email address: {ORGANIZATION_EMAIL}")
        
        # Check if email is already verified
        verified_emails = ses_client.list_verified_email_addresses()
        if ORGANIZATION_EMAIL in verified_emails.get('VerifiedEmailAddresses', []):
            logger.info(f"✅ Email {ORGANIZATION_EMAIL} is already verified!")
            return True
        
        # Verify the email address
        response = ses_client.verify_email_identity(EmailAddress=ORGANIZATION_EMAIL)
        
        logger.info(f"✅ Verification email sent to {ORGANIZATION_EMAIL}")
        logger.info("📧 Please check the email inbox and click the verification link")
        logger.info("⏰ Verification link expires in 24 hours")
        
        # Provide instructions
        logger.info("\n" + "="*60)
        logger.info("NEXT STEPS:")
        logger.info("="*60)
        logger.info("1. Check the email inbox for webhulpje@h-dcn.nl")
        logger.info("2. Look for email from 'Amazon Web Services'")
        logger.info("3. Click the verification link in the email")
        logger.info("4. Run this script again to confirm verification")
        logger.info("5. Update Cognito configuration to use verified email")
        logger.info("="*60)
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'InvalidParameterValue':
            logger.error(f"❌ Invalid email address: {ORGANIZATION_EMAIL}")
        elif error_code == 'LimitExceededException':
            logger.error("❌ Too many verification requests. Wait before trying again.")
        else:
            logger.error(f"❌ SES error: {error_code} - {error_message}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False

def check_verification_status():
    """Check the current verification status of the organization email"""
    
    try:
        ses_client = boto3.client('ses', region_name=AWS_REGION)
        
        # Get all verified email addresses
        verified_emails = ses_client.list_verified_email_addresses()
        all_verified = verified_emails.get('VerifiedEmailAddresses', [])
        
        logger.info(f"Checking verification status for: {ORGANIZATION_EMAIL}")
        
        if ORGANIZATION_EMAIL in all_verified:
            logger.info(f"✅ {ORGANIZATION_EMAIL} is VERIFIED")
            
            # Show next steps for Cognito integration
            logger.info("\n" + "="*60)
            logger.info("COGNITO INTEGRATION NEXT STEPS:")
            logger.info("="*60)
            logger.info("1. Update backend/template.yaml:")
            logger.info("   Uncomment the SourceArn line in EmailConfiguration")
            logger.info("2. Deploy the updated SAM template:")
            logger.info("   sam build && sam deploy")
            logger.info("3. Test email delivery with new configuration")
            logger.info("="*60)
            
            return True
        else:
            logger.warning(f"⚠️  {ORGANIZATION_EMAIL} is NOT verified")
            
            # Show all verified emails
            if all_verified:
                logger.info("Currently verified email addresses:")
                for email in all_verified:
                    logger.info(f"  ✅ {email}")
            else:
                logger.warning("No email addresses are currently verified")
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking verification status: {str(e)}")
        return False

def main():
    """Main function"""
    
    logger.info("="*60)
    logger.info("H-DCN Organization Email Verification")
    logger.info("="*60)
    
    # First check current status
    logger.info("\n1. Checking current verification status...")
    is_verified = check_verification_status()
    
    if is_verified:
        logger.info(f"\n🎉 {ORGANIZATION_EMAIL} is already verified!")
        logger.info("You can now configure Cognito to use SES with this email address.")
        return
    
    # Ask user if they want to send verification email
    logger.info(f"\n2. {ORGANIZATION_EMAIL} needs to be verified.")
    
    try:
        response = input("\nSend verification email? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            logger.info("\n3. Sending verification email...")
            success = verify_email_address()
            
            if success:
                logger.info("\n✅ Verification process initiated successfully!")
            else:
                logger.error("\n❌ Failed to initiate verification process")
                sys.exit(1)
        else:
            logger.info("\nVerification cancelled by user.")
            logger.info("Run this script again when ready to verify the email address.")
            
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(0)

if __name__ == '__main__':
    main()