#!/usr/bin/env python3
"""
H-DCN SES Email Delivery Configuration Test

This script tests email delivery configuration for the H-DCN Cognito authentication system.
It verifies both Cognito default email service and SES configuration capabilities.

Test scenarios:
1. Cognito default email service verification
2. SES configuration validation
3. Email template rendering and delivery
4. Email delivery performance and reliability
5. Bounce and complaint handling setup
"""

import json
import boto3
import logging
import os
import sys
import time
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
AWS_REGION = 'eu-west-1'
ORGANIZATION_EMAIL = 'webhulpje@h-dcn.nl'
TEST_EMAIL = 'webmaster@h-dcn.nl'  # Use a verified email for testing

class SESEmailDeliveryTester:
    """Test SES email delivery configuration for H-DCN Cognito authentication"""
    
    def __init__(self):
        """Initialize the SES email delivery tester"""
        self.region = AWS_REGION
        self.organization_email = ORGANIZATION_EMAIL
        self.test_email = TEST_EMAIL
        
        # Initialize AWS clients
        try:
            self.ses_client = boto3.client('ses', region_name=self.region)
            self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
            self.sts_client = boto3.client('sts')
            logger.info("AWS clients initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            sys.exit(1)
    
    def test_aws_credentials(self):
        """Test AWS credentials and permissions"""
        logger.info("Testing AWS credentials and permissions...")
        
        try:
            # Test STS access
            identity = self.sts_client.get_caller_identity()
            logger.info(f"✓ AWS Identity: {identity.get('Arn', 'Unknown')}")
            logger.info(f"✓ Account ID: {identity.get('Account', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ AWS credentials test failed: {str(e)}")
            return False
    
    def test_ses_service_availability(self):
        """Test SES service availability and permissions"""
        logger.info("Testing SES service availability...")
        
        try:
            # Test SES access by getting sending quota
            quota = self.ses_client.get_send_quota()
            logger.info(f"✓ SES service accessible")
            logger.info(f"✓ Daily sending quota: {quota.get('Max24HourSend', 'Unknown')}")
            logger.info(f"✓ Emails sent in last 24h: {quota.get('SentLast24Hours', 'Unknown')}")
            logger.info(f"✓ Max send rate: {quota.get('MaxSendRate', 'Unknown')} emails/second")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                logger.error("✗ SES access denied. Check IAM permissions for SES.")
            else:
                logger.error(f"✗ SES service error: {error_code} - {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"✗ SES service test failed: {str(e)}")
            return False
    
    def test_email_identity_verification(self):
        """Test email identity verification status"""
        logger.info("Testing email identity verification...")
        
        try:
            # Check verification status of organization email
            identities = self.ses_client.list_verified_email_addresses()
            verified_emails = identities.get('VerifiedEmailAddresses', [])
            
            logger.info(f"Verified email addresses: {len(verified_emails)}")
            
            if self.organization_email in verified_emails:
                logger.info(f"✓ Organization email {self.organization_email} is verified")
                org_email_verified = True
            else:
                logger.warning(f"⚠ Organization email {self.organization_email} is NOT verified")
                org_email_verified = False
            
            if self.test_email in verified_emails:
                logger.info(f"✓ Test email {self.test_email} is verified")
                test_email_verified = True
            else:
                logger.warning(f"⚠ Test email {self.test_email} is NOT verified")
                test_email_verified = False
            
            # List all verified emails for reference
            if verified_emails:
                logger.info("All verified email addresses:")
                for email in verified_emails:
                    logger.info(f"  - {email}")
            else:
                logger.warning("No verified email addresses found")
            
            return org_email_verified, test_email_verified, verified_emails
            
        except Exception as e:
            logger.error(f"✗ Email identity verification test failed: {str(e)}")
            return False, False, []
    
    def test_cognito_user_pool_configuration(self):
        """Test current Cognito User Pool email configuration"""
        logger.info("Testing Cognito User Pool email configuration...")
        
        try:
            # List user pools to find H-DCN pool
            user_pools = self.cognito_client.list_user_pools(MaxResults=50)
            
            hdcn_pool = None
            for pool in user_pools.get('UserPools', []):
                if 'H-DCN' in pool.get('Name', '') or 'hdcn' in pool.get('Name', '').lower():
                    hdcn_pool = pool
                    break
            
            if not hdcn_pool:
                logger.error("✗ H-DCN Cognito User Pool not found")
                return False
            
            pool_id = hdcn_pool['Id']
            logger.info(f"✓ Found H-DCN User Pool: {hdcn_pool['Name']} ({pool_id})")
            
            # Get detailed pool configuration
            pool_details = self.cognito_client.describe_user_pool(UserPoolId=pool_id)
            pool_config = pool_details['UserPool']
            
            # Check email configuration
            email_config = pool_config.get('EmailConfiguration', {})
            email_sending_account = email_config.get('EmailSendingAccount', 'COGNITO_DEFAULT')
            
            logger.info(f"Email sending account: {email_sending_account}")
            
            if email_sending_account == 'COGNITO_DEFAULT':
                logger.info("✓ Using Cognito default email service")
                logger.info("  - No SES configuration required")
                logger.info("  - Limited to 50 emails per day")
                logger.info("  - Emails sent from no-reply@verificationemail.com")
            elif email_sending_account == 'DEVELOPER':
                logger.info("✓ Using custom SES configuration")
                source_arn = email_config.get('SourceArn', 'Not configured')
                reply_to = email_config.get('ReplyToEmailAddress', 'Not configured')
                logger.info(f"  - Source ARN: {source_arn}")
                logger.info(f"  - Reply-to address: {reply_to}")
            
            # Check other email settings
            auto_verified_attributes = pool_config.get('AutoVerifiedAttributes', [])
            logger.info(f"Auto-verified attributes: {auto_verified_attributes}")
            
            # Check MFA configuration
            mfa_config = pool_config.get('MfaConfiguration', 'OFF')
            logger.info(f"MFA configuration: {mfa_config}")
            
            return True, pool_id, email_config
            
        except Exception as e:
            logger.error(f"✗ Cognito User Pool configuration test failed: {str(e)}")
            return False, None, {}
    
    def test_email_template_rendering(self):
        """Test email template rendering using the custom message Lambda"""
        logger.info("Testing email template rendering...")
        
        # Add the handler directory to the path for testing
        sys.path.append('handler/cognito_custom_message')
        
        try:
            from app import lambda_handler
            
            # Set environment variables for testing
            os.environ['ORGANIZATION_NAME'] = 'Harley-Davidson Club Nederland'
            os.environ['ORGANIZATION_WEBSITE'] = 'https://h-dcn.nl'
            os.environ['ORGANIZATION_EMAIL'] = 'webhulpje@h-dcn.nl'
            os.environ['ORGANIZATION_SHORT_NAME'] = 'H-DCN'
            
            # Test different email scenarios
            test_scenarios = [
                {
                    'name': 'Email Verification',
                    'event': {
                        'triggerSource': 'CustomMessage_VerifyUserAttribute',
                        'userName': 'test.member@example.com',
                        'userPoolId': 'eu-west-1_TestPool',
                        'request': {
                            'userAttributes': {
                                'email': 'test.member@example.com',
                                'given_name': 'Test',
                                'family_name': 'Member'
                            },
                            'codeParameter': '123456'
                        },
                        'response': {}
                    }
                },
                {
                    'name': 'Passwordless Recovery',
                    'event': {
                        'triggerSource': 'CustomMessage_ForgotPassword',
                        'userName': 'existing.member@h-dcn.nl',
                        'userPoolId': 'eu-west-1_TestPool',
                        'request': {
                            'userAttributes': {
                                'email': 'existing.member@h-dcn.nl',
                                'given_name': 'Existing',
                                'family_name': 'Member'
                            },
                            'codeParameter': '789012'
                        },
                        'response': {}
                    }
                }
            ]
            
            template_results = []
            
            for scenario in test_scenarios:
                logger.info(f"Testing template: {scenario['name']}")
                
                try:
                    result = lambda_handler(scenario['event'], {})
                    
                    email_subject = result.get('response', {}).get('emailSubject', '')
                    email_message = result.get('response', {}).get('emailMessage', '')
                    
                    if email_subject and email_message:
                        logger.info(f"✓ Template rendered successfully")
                        logger.info(f"  Subject: {email_subject}")
                        logger.info(f"  Message length: {len(email_message)} characters")
                        
                        template_results.append({
                            'scenario': scenario['name'],
                            'success': True,
                            'subject': email_subject,
                            'message': email_message
                        })
                    else:
                        logger.error(f"✗ Template rendering failed - empty content")
                        template_results.append({
                            'scenario': scenario['name'],
                            'success': False,
                            'error': 'Empty email content'
                        })
                        
                except Exception as e:
                    logger.error(f"✗ Template rendering failed: {str(e)}")
                    template_results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'error': str(e)
                    })
            
            return template_results
            
        except ImportError as e:
            logger.error(f"✗ Cannot import Lambda handler: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"✗ Email template rendering test failed: {str(e)}")
            return []
    
    def test_ses_email_sending(self, verified_emails):
        """Test actual email sending through SES"""
        logger.info("Testing SES email sending...")
        
        if not verified_emails:
            logger.warning("⚠ No verified email addresses available for sending test")
            return False
        
        # Use the first verified email as sender
        sender_email = verified_emails[0]
        recipient_email = self.test_email if self.test_email in verified_emails else sender_email
        
        logger.info(f"Sending test email from {sender_email} to {recipient_email}")
        
        try:
            # Create test email content
            subject = "H-DCN SES Email Delivery Test"
            body_text = f"""H-DCN SES Email Delivery Test

This is a test email to verify SES email delivery configuration for the H-DCN Cognito authentication system.

Test Details:
- Timestamp: {datetime.now().isoformat()}
- Sender: {sender_email}
- Recipient: {recipient_email}
- Region: {self.region}

If you receive this email, SES email delivery is working correctly.

---
Harley-Davidson Club Nederland
Website: https://h-dcn.nl
E-mail: webhulpje@h-dcn.nl"""
            
            body_html = f"""<html>
<head></head>
<body>
<h2>H-DCN SES Email Delivery Test</h2>
<p>This is a test email to verify SES email delivery configuration for the H-DCN Cognito authentication system.</p>

<h3>Test Details:</h3>
<ul>
<li><strong>Timestamp:</strong> {datetime.now().isoformat()}</li>
<li><strong>Sender:</strong> {sender_email}</li>
<li><strong>Recipient:</strong> {recipient_email}</li>
<li><strong>Region:</strong> {self.region}</li>
</ul>

<p>If you receive this email, SES email delivery is working correctly.</p>

<hr>
<p><strong>Harley-Davidson Club Nederland</strong><br>
Website: <a href="https://h-dcn.nl">https://h-dcn.nl</a><br>
E-mail: <a href="mailto:webhulpje@h-dcn.nl">webhulpje@h-dcn.nl</a></p>
</body>
</html>"""
            
            # Send email
            response = self.ses_client.send_email(
                Source=sender_email,
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': body_text,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': body_html,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            message_id = response.get('MessageId', 'Unknown')
            logger.info(f"✓ Test email sent successfully")
            logger.info(f"  Message ID: {message_id}")
            logger.info(f"  From: {sender_email}")
            logger.info(f"  To: {recipient_email}")
            
            return True, message_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"✗ SES email sending failed: {error_code} - {error_message}")
            
            if error_code == 'MessageRejected':
                logger.error("  Email was rejected. Check email addresses and content.")
            elif error_code == 'SendingPausedException':
                logger.error("  SES sending is paused. Check SES console.")
            elif error_code == 'MailFromDomainNotVerifiedException':
                logger.error("  Mail-from domain not verified.")
            
            return False, None
            
        except Exception as e:
            logger.error(f"✗ SES email sending test failed: {str(e)}")
            return False, None
    
    def test_bounce_and_complaint_handling(self):
        """Test bounce and complaint handling configuration"""
        logger.info("Testing bounce and complaint handling configuration...")
        
        try:
            # Check if there are any configuration sets
            config_sets = self.ses_client.list_configuration_sets()
            
            if config_sets.get('ConfigurationSets'):
                logger.info("✓ Configuration sets found:")
                for config_set in config_sets['ConfigurationSets']:
                    logger.info(f"  - {config_set['Name']}")
            else:
                logger.warning("⚠ No configuration sets found")
                logger.info("  Consider creating configuration sets for bounce/complaint handling")
            
            # Check reputation tracking
            try:
                reputation = self.ses_client.get_reputation()
                logger.info(f"✓ Account reputation tracking enabled")
                logger.info(f"  Bounce rate: {reputation.get('BounceRate', 'Unknown')}")
                logger.info(f"  Complaint rate: {reputation.get('ComplaintRate', 'Unknown')}")
            except:
                logger.info("  Reputation tracking information not available")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Bounce and complaint handling test failed: {str(e)}")
            return False
    
    def generate_recommendations(self, test_results):
        """Generate recommendations based on test results"""
        logger.info("Generating SES configuration recommendations...")
        
        recommendations = []
        
        # Check if SES is properly configured
        if not test_results.get('ses_available', False):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'SES Setup',
                'title': 'Enable SES Service',
                'description': 'SES service is not accessible. Ensure IAM permissions include SES actions.',
                'action': 'Add SES permissions to Lambda execution role'
            })
        
        # Check email verification
        org_verified, test_verified, verified_emails = test_results.get('email_verification', (False, False, []))
        
        if not org_verified:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Email Verification',
                'title': 'Verify Organization Email',
                'description': f'Organization email {self.organization_email} is not verified in SES.',
                'action': f'Verify {self.organization_email} in SES console'
            })
        
        if len(verified_emails) < 2:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Email Verification',
                'title': 'Verify Additional Email Addresses',
                'description': 'Consider verifying additional email addresses for testing and backup.',
                'action': 'Verify webmaster@h-dcn.nl and other admin emails'
            })
        
        # Check Cognito configuration
        cognito_config = test_results.get('cognito_config', {})
        if cognito_config.get('EmailSendingAccount') == 'COGNITO_DEFAULT':
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Cognito Configuration',
                'title': 'Consider SES Integration',
                'description': 'Currently using Cognito default email (50 emails/day limit).',
                'action': 'Configure Cognito to use SES for higher email limits and custom sender'
            })
        
        # Email sending test results
        if not test_results.get('email_sent', False):
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Email Delivery',
                'title': 'Fix Email Sending Issues',
                'description': 'Test email sending failed. Check SES configuration and permissions.',
                'action': 'Review SES sending quota, verified emails, and IAM permissions'
            })
        
        # Template rendering
        template_results = test_results.get('template_results', [])
        failed_templates = [t for t in template_results if not t.get('success', False)]
        if failed_templates:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Email Templates',
                'title': 'Fix Email Template Issues',
                'description': f'{len(failed_templates)} email templates failed to render.',
                'action': 'Review Lambda function code and environment variables'
            })
        
        # Bounce handling
        if not test_results.get('bounce_handling', False):
            recommendations.append({
                'priority': 'LOW',
                'category': 'Email Management',
                'title': 'Set Up Bounce Handling',
                'description': 'No configuration sets found for bounce/complaint handling.',
                'action': 'Create SES configuration sets with SNS notifications for bounces'
            })
        
        return recommendations
    
    def run_comprehensive_test(self):
        """Run comprehensive SES email delivery test"""
        logger.info("=" * 60)
        logger.info("H-DCN SES Email Delivery Configuration Test")
        logger.info("=" * 60)
        
        test_results = {}
        
        # Test 1: AWS Credentials
        logger.info("\n1. Testing AWS Credentials...")
        test_results['credentials'] = self.test_aws_credentials()
        
        if not test_results['credentials']:
            logger.error("Cannot proceed without valid AWS credentials")
            return test_results
        
        # Test 2: SES Service Availability
        logger.info("\n2. Testing SES Service Availability...")
        test_results['ses_available'] = self.test_ses_service_availability()
        
        # Test 3: Email Identity Verification
        logger.info("\n3. Testing Email Identity Verification...")
        test_results['email_verification'] = self.test_email_identity_verification()
        
        # Test 4: Cognito User Pool Configuration
        logger.info("\n4. Testing Cognito User Pool Configuration...")
        cognito_result = self.test_cognito_user_pool_configuration()
        if cognito_result[0]:
            test_results['cognito_config'] = cognito_result[2]
            test_results['user_pool_id'] = cognito_result[1]
        
        # Test 5: Email Template Rendering
        logger.info("\n5. Testing Email Template Rendering...")
        test_results['template_results'] = self.test_email_template_rendering()
        
        # Test 6: SES Email Sending (if SES is available and emails are verified)
        if test_results.get('ses_available') and test_results.get('email_verification', (False, False, []))[2]:
            logger.info("\n6. Testing SES Email Sending...")
            verified_emails = test_results['email_verification'][2]
            email_result = self.test_ses_email_sending(verified_emails)
            test_results['email_sent'] = email_result[0]
            if email_result[0]:
                test_results['message_id'] = email_result[1]
        else:
            logger.info("\n6. Skipping SES Email Sending Test (prerequisites not met)")
            test_results['email_sent'] = False
        
        # Test 7: Bounce and Complaint Handling
        if test_results.get('ses_available'):
            logger.info("\n7. Testing Bounce and Complaint Handling...")
            test_results['bounce_handling'] = self.test_bounce_and_complaint_handling()
        
        # Generate Recommendations
        logger.info("\n8. Generating Recommendations...")
        recommendations = self.generate_recommendations(test_results)
        
        # Print Summary
        self.print_test_summary(test_results, recommendations)
        
        return test_results, recommendations
    
    def print_test_summary(self, test_results, recommendations):
        """Print comprehensive test summary"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        # Overall status
        critical_failures = [
            not test_results.get('credentials', False),
            not test_results.get('ses_available', False)
        ]
        
        if any(critical_failures):
            logger.error("❌ CRITICAL ISSUES FOUND - Email delivery may not work")
        elif test_results.get('email_sent', False):
            logger.info("✅ EMAIL DELIVERY WORKING - All critical tests passed")
        else:
            logger.warning("⚠️  PARTIAL SUCCESS - Some issues need attention")
        
        # Test results summary
        logger.info("\nTest Results:")
        logger.info(f"  AWS Credentials: {'✓' if test_results.get('credentials') else '✗'}")
        logger.info(f"  SES Service: {'✓' if test_results.get('ses_available') else '✗'}")
        
        org_verified, test_verified, verified_count = test_results.get('email_verification', (False, False, []))
        logger.info(f"  Email Verification: {len(verified_count) if isinstance(verified_count, list) else 0} verified")
        
        logger.info(f"  Cognito Configuration: {'✓' if 'cognito_config' in test_results else '✗'}")
        
        template_results = test_results.get('template_results', [])
        successful_templates = len([t for t in template_results if t.get('success', False)])
        logger.info(f"  Email Templates: {successful_templates}/{len(template_results)} working")
        
        logger.info(f"  Email Sending: {'✓' if test_results.get('email_sent') else '✗'}")
        logger.info(f"  Bounce Handling: {'✓' if test_results.get('bounce_handling') else '✗'}")
        
        # Recommendations summary
        if recommendations:
            logger.info(f"\nRecommendations: {len(recommendations)} items")
            
            high_priority = [r for r in recommendations if r['priority'] == 'HIGH']
            medium_priority = [r for r in recommendations if r['priority'] == 'MEDIUM']
            low_priority = [r for r in recommendations if r['priority'] == 'LOW']
            
            if high_priority:
                logger.warning(f"  🔴 HIGH Priority: {len(high_priority)} items")
                for rec in high_priority:
                    logger.warning(f"    - {rec['title']}")
            
            if medium_priority:
                logger.info(f"  🟡 MEDIUM Priority: {len(medium_priority)} items")
                for rec in medium_priority:
                    logger.info(f"    - {rec['title']}")
            
            if low_priority:
                logger.info(f"  🟢 LOW Priority: {len(low_priority)} items")
                for rec in low_priority:
                    logger.info(f"    - {rec['title']}")
        else:
            logger.info("\n✅ No recommendations - Configuration looks good!")
        
        logger.info("\n" + "=" * 60)

def main():
    """Main function to run SES email delivery tests"""
    try:
        tester = SESEmailDeliveryTester()
        test_results, recommendations = tester.run_comprehensive_test()
        
        # Save results to file for reference
        results_file = f"ses_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'test_results': test_results,
                'recommendations': recommendations
            }, f, indent=2, default=str)
        
        logger.info(f"\nDetailed results saved to: {results_file}")
        
        return test_results, recommendations
        
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()