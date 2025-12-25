#!/usr/bin/env python3
"""Simple validation for email templates"""

import os
import sys
sys.path.append('handler/cognito_custom_message')

# Set environment variables
os.environ['ORGANIZATION_NAME'] = 'Harley-Davidson Club Nederland'
os.environ['ORGANIZATION_WEBSITE'] = 'https://h-dcn.nl'
os.environ['ORGANIZATION_EMAIL'] = 'webhulpje@h-dcn.nl'
os.environ['ORGANIZATION_SHORT_NAME'] = 'H-DCN'

from app import lambda_handler

# Test event
event = {
    'triggerSource': 'CustomMessage_VerifyUserAttribute',
    'userName': 'test@example.com',
    'userPoolId': 'test-pool',
    'request': {
        'userAttributes': {
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User'
        },
        'codeParameter': '123456'
    },
    'response': {}
}

result = lambda_handler(event, {})
print("Email Subject:", result['response']['emailSubject'])
print("Email contains H-DCN:", 'H-DCN' in result['response']['emailMessage'])
print("Email contains website:", 'h-dcn.nl' in result['response']['emailMessage'])
print("Template generation: SUCCESS")