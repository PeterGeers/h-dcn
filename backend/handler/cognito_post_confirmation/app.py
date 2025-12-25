"""
H-DCN Cognito Post-Confirmation Lambda Function

This function handles post-confirmation actions for newly verified users.
It automatically assigns the default member role (hdcnLeden) to new users
and can perform additional setup tasks.

Trigger: PostConfirmation_ConfirmSignUp, PostConfirmation_ConfirmForgotPassword
"""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')

# Get organization details from environment variables
ORGANIZATION_NAME = os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland')
ORGANIZATION_WEBSITE = os.environ.get('ORGANIZATION_WEBSITE', 'https://h-dcn.nl')
ORGANIZATION_EMAIL = os.environ.get('ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl')
ORGANIZATION_SHORT_NAME = os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN')

def lambda_handler(event, context):
    """
    AWS Cognito Post-Confirmation Lambda trigger handler
    
    Args:
        event: Cognito trigger event containing user data
        context: Lambda context object
        
    Returns:
        Original event (required by Cognito)
    """
    try:
        logger.info(f"Cognito Post-Confirmation trigger event: {json.dumps(event, default=str)}")
        
        # Extract event information
        trigger_source = event.get('triggerSource')
        user_attributes = event.get('request', {}).get('userAttributes', {})
        username = event.get('userName', '')
        user_pool_id = event.get('userPoolId', '')
        
        # Extract user information
        email = user_attributes.get('email', username)
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        
        logger.info(f"Processing post-confirmation for trigger: {trigger_source}, user: {email}")
        
        # Handle different trigger sources
        if trigger_source == 'PostConfirmation_ConfirmSignUp':
            handle_signup_confirmation(user_pool_id, username, email, given_name, family_name)
        elif trigger_source == 'PostConfirmation_ConfirmForgotPassword':
            handle_password_recovery_confirmation(user_pool_id, username, email)
        else:
            logger.warning(f"Unhandled trigger source: {trigger_source}")
        
        logger.info("Post-confirmation processing completed successfully")
        return event
        
    except Exception as e:
        logger.error(f"Error in post-confirmation handler: {str(e)}")
        # Return original event to prevent authentication failure
        # Log error but don't block user confirmation
        return event

def handle_signup_confirmation(user_pool_id, username, email, given_name, family_name):
    """
    Handle post-confirmation actions for new user signup
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username (usually email)
        email: User's email address
        given_name: User's first name
        family_name: User's last name
    """
    try:
        # Get default member group from environment variable
        default_group = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')
        
        logger.info(f"Adding new user {email} to default group: {default_group}")
        
        # Add user to default member group
        add_user_to_group(user_pool_id, username, default_group)
        
        # Log successful group assignment
        logger.info(f"Successfully added user {email} to group {default_group}")
        
        # Additional setup tasks can be added here:
        # - Send welcome email to administrators
        # - Create user profile in external systems
        # - Initialize user preferences
        
        send_admin_notification(email, given_name, family_name, 'new_signup')
        
    except Exception as e:
        logger.error(f"Error in signup confirmation handler: {str(e)}")
        raise

def handle_password_recovery_confirmation(user_pool_id, username, email):
    """
    Handle post-confirmation actions for password recovery
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username
        email: User's email address
    """
    try:
        logger.info(f"Processing password recovery confirmation for user: {email}")
        
        # Log password recovery event for security monitoring
        logger.info(f"Password recovery completed for user: {email}")
        
        # Send security notification to administrators
        send_admin_notification(email, '', '', 'password_recovery')
        
    except Exception as e:
        logger.error(f"Error in password recovery confirmation handler: {str(e)}")
        raise

def add_user_to_group(user_pool_id, username, group_name):
    """
    Add user to a Cognito User Pool group
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username
        group_name: Name of the group to add user to
    """
    try:
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=group_name
        )
        logger.info(f"Successfully added user {username} to group {group_name}")
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Group {group_name} not found in user pool {user_pool_id}")
        elif error_code == 'UserNotFoundException':
            logger.error(f"User {username} not found in user pool {user_pool_id}")
        else:
            logger.error(f"Error adding user to group: {error_code} - {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error adding user to group: {str(e)}")
        raise

def send_admin_notification(email, given_name, family_name, event_type):
    """
    Send notification to administrators about user events
    
    Args:
        email: User's email address
        given_name: User's first name
        family_name: User's last name
        event_type: Type of event (new_signup, password_recovery)
    """
    try:
        # Create display name
        if given_name or family_name:
            display_name = f"{given_name} {family_name}".strip()
        else:
            display_name = email.split('@')[0]
        
        # Log admin notification (in production, this could send actual emails)
        if event_type == 'new_signup':
            logger.info(f"ADMIN_NOTIFICATION: New user signup - {display_name} ({email}) for {ORGANIZATION_SHORT_NAME}")
        elif event_type == 'password_recovery':
            logger.info(f"ADMIN_NOTIFICATION: Password recovery completed - {display_name} ({email}) for {ORGANIZATION_SHORT_NAME}")
        
        # In a production environment, you could:
        # 1. Send email to administrators using SES
        # 2. Post to Slack/Teams channel
        # 3. Create tickets in support system
        # 4. Update external CRM systems
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")
        # Don't raise exception for notification failures