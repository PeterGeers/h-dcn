#!/usr/bin/env python3
"""
Test script for H-DCN Cognito email templates

This script tests the custom message Lambda function locally to verify
email template generation works correctly.
"""

import json
import sys
import os

# Add the handler directory to the path
sys.path.append('handler/cognito_custom_message')

# Import the Lambda function
from app import lambda_handler

def test_email_templates():
    """Test various email template scenarios"""
    
    print("Testing H-DCN Cognito Email Templates")
    print("=" * 50)
    
    # Test data
    test_cases = [
        {
            'name': 'Admin Create User',
            'event': {
                'triggerSource': 'CustomMessage_AdminCreateUser',
                'userName': 'test.user@example.com',
                'userPoolId': 'eu-west-1_TestPool',
                'request': {
                    'userAttributes': {
                        'email': 'test.user@example.com',
                        'given_name': 'Test',
                        'family_name': 'User'
                    },
                    'tempPassword': 'TempPass123!'
                },
                'response': {}
            }
        },
        {
            'name': 'Resend Verification Code',
            'event': {
                'triggerSource': 'CustomMessage_ResendCode',
                'userName': 'existing.user@example.com',
                'userPoolId': 'eu-west-1_TestPool',
                'request': {
                    'userAttributes': {
                        'email': 'existing.user@example.com',
                        'given_name': 'Existing',
                        'family_name': 'User'
                    },
                    'codeParameter': '123456'
                },
                'response': {}
            }
        },
        {
            'name': 'Verify User Attribute',
            'event': {
                'triggerSource': 'CustomMessage_VerifyUserAttribute',
                'userName': 'new.member@example.com',
                'userPoolId': 'eu-west-1_TestPool',
                'request': {
                    'userAttributes': {
                        'email': 'new.member@example.com',
                        'given_name': 'New',
                        'family_name': 'Member'
                    },
                    'codeParameter': '789012'
                },
                'response': {}
            }
        },
        {
            'name': 'Authentication Code',
            'event': {
                'triggerSource': 'CustomMessage_Authentication',
                'userName': 'admin.user@h-dcn.nl',
                'userPoolId': 'eu-west-1_TestPool',
                'request': {
                    'userAttributes': {
                        'email': 'admin.user@h-dcn.nl',
                        'given_name': 'Admin',
                        'family_name': 'User'
                    },
                    'codeParameter': '345678'
                },
                'response': {}
            }
        }
    ]
    
    # Set environment variables for testing
    os.environ['ORGANIZATION_NAME'] = 'Harley-Davidson Club Nederland'
    os.environ['ORGANIZATION_WEBSITE'] = 'https://h-dcn.nl'
    os.environ['ORGANIZATION_EMAIL'] = 'webhulpje@h-dcn.nl'
    os.environ['ORGANIZATION_SHORT_NAME'] = 'H-DCN'
    
    # Test each scenario
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Call the Lambda handler
            result = lambda_handler(test_case['event'], {})
            
            # Extract email content
            email_subject = result.get('response', {}).get('emailSubject', 'No subject')
            email_message = result.get('response', {}).get('emailMessage', 'No message')
            
            print(f"Subject: {email_subject}")
            print(f"Message Preview (first 200 chars):")
            print(email_message[:200] + "..." if len(email_message) > 200 else email_message)
            print(f"Message Length: {len(email_message)} characters")
            
            # Validate required elements
            validation_checks = [
                ('Contains organization name', 'H-DCN' in email_message),
                ('Contains website URL', 'h-dcn.nl' in email_message),
                ('Contains contact email', 'webhulpje@h-dcn.nl' in email_message),
                ('Has proper footer', '---' in email_message),
                ('Subject not empty', len(email_subject) > 0),
                ('Message not empty', len(email_message) > 0)
            ]
            
            print("\nValidation Results:")
            for check_name, check_result in validation_checks:
                status = "✓ PASS" if check_result else "✗ FAIL"
                print(f"  {status}: {check_name}")
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
        
        print()
    
    print("Email template testing completed!")

if __name__ == '__main__':
    test_email_templates()