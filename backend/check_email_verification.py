#!/usr/bin/env python3
"""
H-DCN Email Verification Status Checker

This script checks if webhulpje@h-dcn.nl has been verified in SES
and provides next steps for completing the email sender configuration.
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

def check_email_verification_status():
    """Check if the organization email is verified in SES"""
    
    try:
        ses_client = boto3.client('ses', region_name=AWS_REGION)
        
        # Get all verified email addresses
        verified_emails = ses_client.list_verified_email_addresses()
        all_verified = verified_emails.get('VerifiedEmailAddresses', [])
        
        logger.info(f"Checking verification status for: {ORGANIZATION_EMAIL}")
        
        if ORGANIZATION_EMAIL in all_verified:
            logger.info(f"✅ {ORGANIZATION_EMAIL} is VERIFIED!")
            return True
        else:
            logger.warning(f"⚠️  {ORGANIZATION_EMAIL} is NOT yet verified")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking verification status: {str(e)}")
        return False

def show_next_steps(is_verified):
    """Show appropriate next steps based on verification status"""
    
    logger.info("\n" + "="*60)
    
    if is_verified:
        logger.info("🎉 EMAIL VERIFICATION COMPLETE!")
        logger.info("="*60)
        logger.info("✅ webhulpje@h-dcn.nl is verified and ready to use")
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Deploy the updated SAM template:")
        logger.info("   cd backend")
        logger.info("   sam build")
        logger.info("   sam deploy")
        logger.info("")
        logger.info("2. Test email delivery:")
        logger.info("   python test_ses_email_delivery.py")
        logger.info("")
        logger.info("3. Verify Cognito email configuration:")
        logger.info("   - Check AWS Console → Cognito → User Pools")
        logger.info("   - Verify EmailSendingAccount is set to DEVELOPER")
        logger.info("   - Verify SourceArn points to webhulpje@h-dcn.nl")
        logger.info("")
        logger.info("BENEFITS OF SES INTEGRATION:")
        logger.info("• Higher email limits (200+ emails/day)")
        logger.info("• Custom sender address (webhulpje@h-dcn.nl)")
        logger.info("• Better deliverability and monitoring")
        logger.info("• Enhanced branding and trust")
        
    else:
        logger.info("⏳ EMAIL VERIFICATION PENDING")
        logger.info("="*60)
        logger.info("The verification email has been sent to webhulpje@h-dcn.nl")
        logger.info("")
        logger.info("TO COMPLETE VERIFICATION:")
        logger.info("1. Check the email inbox for webhulpje@h-dcn.nl")
        logger.info("2. Look for email from 'Amazon Web Services'")
        logger.info("3. Click the verification link in the email")
        logger.info("4. Run this script again to confirm verification")
        logger.info("")
        logger.info("VERIFICATION LINK EXPIRES IN 24 HOURS")
        logger.info("")
        logger.info("If you don't see the email:")
        logger.info("• Check spam/junk folder")
        logger.info("• Verify email address is correct")
        logger.info("• Run verify_organization_email.py to resend")
    
    logger.info("="*60)

def main():
    """Main function"""
    
    logger.info("="*60)
    logger.info("H-DCN Email Verification Status Check")
    logger.info("="*60)
    
    # Check verification status
    is_verified = check_email_verification_status()
    
    # Show appropriate next steps
    show_next_steps(is_verified)
    
    # Return appropriate exit code
    if is_verified:
        logger.info("\n✅ Email verification complete - ready for deployment!")
        sys.exit(0)
    else:
        logger.info("\n⏳ Waiting for email verification completion...")
        sys.exit(1)

if __name__ == '__main__':
    main()