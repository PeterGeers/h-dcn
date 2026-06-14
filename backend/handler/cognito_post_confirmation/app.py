"""
H-DCN Cognito Post-Confirmation Lambda Function

This function handles post-confirmation actions for newly verified users.
It automatically assigns the default member role (hdcnLeden) to new users
and can perform additional setup tasks.

For event landing page signups (source='event_landing'), it creates an
event_participant member record with limited permissions instead.

Trigger: PostConfirmation_ConfirmSignUp, PostConfirmation_ConfirmForgotPassword
"""

import json
import logging
import os
import uuid
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')

# Initialize DynamoDB client for member status checking
dynamodb = boto3.resource('dynamodb')

# Get organization details from environment variables
ORGANIZATION_NAME = os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland')
ORGANIZATION_WEBSITE = os.environ.get('ORGANIZATION_WEBSITE', 'https://h-dcn.nl')
ORGANIZATION_EMAIL = os.environ.get('ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl')
ORGANIZATION_SHORT_NAME = os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN')
MEMBERS_TABLE_NAME = os.environ.get('MEMBERS_TABLE_NAME', 'Members')

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
            # Pass clientMetadata to the signup handler via function attribute
            client_metadata = event.get('request', {}).get('clientMetadata', {})
            handle_signup_confirmation._client_metadata = client_metadata
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
    Handle post-confirmation actions for new user signup.
    
    Two paths:
    1. Event landing page signup (clientMetadata.source == 'event_landing'):
       - Create Members record with member_type='event_participant'
       - Add user to 'event_participant' Cognito group (NOT hdcnLeden)
       - Grant access to the specified event via allowed_events
    
    2. Regular signup (no event context):
       - Check if user already exists in Members table
       - If user is approved, assign default member role (hdcnLeden)
       - Otherwise, no role assigned until manual approval
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username (usually email)
        email: User's email address
        given_name: User's first name
        family_name: User's last name
    """
    try:
        logger.info(f"Processing post-confirmation for new user: {email}")
        
        # Check for event landing page context in clientMetadata
        # Note: clientMetadata is accessed from the outer event in lambda_handler
        # We pass it via a module-level variable set in lambda_handler
        client_metadata = getattr(handle_signup_confirmation, '_client_metadata', {}) or {}
        event_id = client_metadata.get('event_id')
        source = client_metadata.get('source')
        
        if source == 'event_landing' and event_id:
            # --- Event landing page registration path ---
            logger.info(f"Event landing page signup for {email}, event_id={event_id}")
            _handle_event_landing_signup(user_pool_id, username, email, given_name, family_name, event_id)
        else:
            # --- Regular H-DCN signup path (existing logic) ---
            _handle_regular_signup(user_pool_id, username, email, given_name, family_name)
        
    except Exception as e:
        logger.error(f"Error in signup confirmation handler: {str(e)}")
        raise


def _handle_event_landing_signup(user_pool_id, username, email, given_name, family_name, event_id):
    """
    Handle signup from an event landing page.
    Creates an event_participant member record and adds to event_participant group.
    """
    # Create Members record with event_participant type
    members_table = dynamodb.Table(MEMBERS_TABLE_NAME)
    member_id = str(uuid.uuid4())
    
    member_record = {
        'member_id': member_id,
        'email': email,
        'given_name': given_name or '',
        'family_name': family_name or '',
        'member_type': 'event_participant',
        'allowed_events': [event_id],
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'created_via': 'event_landing',
    }
    
    members_table.put_item(Item=member_record)
    logger.info(f"Created event_participant member record: {member_id} for {email}")
    
    # Add user to event_participant Cognito group (NOT hdcnLeden)
    add_user_to_group(user_pool_id, username, 'event_participant')
    logger.info(f"Added {email} to event_participant group")
    
    # Send admin notification
    send_admin_notification(email, given_name, family_name, 'event_landing_signup')
    
    # Log the decision
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'POST_CONFIRMATION_EVENT_LANDING',
        'user_email': email,
        'member_id': member_id,
        'event_id': event_id,
        'member_type': 'event_participant',
        'group_assigned': 'event_participant',
        'organization': ORGANIZATION_SHORT_NAME,
    }
    logger.info(f"EVENT_LANDING_SIGNUP: {json.dumps(log_entry)}")


def _handle_regular_signup(user_pool_id, username, email, given_name, family_name):
    """
    Handle regular H-DCN signup (no event context).
    Existing logic: check member status, assign hdcnLeden if approved.
    """
    # Check if user already exists in Members table
    member_status = check_member_status(email)
    
    if member_status:
        logger.info(f"User {email} found in Members table with status: {member_status}")
        
        # If user is already approved, assign default role
        approved_statuses = ['active', 'approved']
        if member_status in approved_statuses:
            default_group = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')
            logger.info(f"User {email} is approved member, adding to group: {default_group}")
            add_user_to_group(user_pool_id, username, default_group)
            logger.info(f"Successfully added existing approved member {email} to group {default_group}")
        else:
            logger.info(f"User {email} is not approved (status: {member_status}), no role assigned")
    else:
        logger.info(f"User {email} not found in Members table - new applicant, no role assigned")
    
    # Send admin notification about new signup
    send_admin_notification(email, given_name, family_name, 'new_signup')
    
    # Log the role assignment decision for audit
    log_role_assignment_decision(email, member_status, given_name, family_name)

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
        elif event_type == 'event_landing_signup':
            logger.info(f"ADMIN_NOTIFICATION: Event landing page signup - {display_name} ({email}) for {ORGANIZATION_SHORT_NAME}")
        
        # In a production environment, you could:
        # 1. Send email to administrators using SES
        # 2. Post to Slack/Teams channel
        # 3. Create tickets in support system
        # 4. Update external CRM systems
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")
        # Don't raise exception for notification failures

def check_member_status(email):
    """
    Check if user exists in Members table and return their status
    
    Args:
        email (str): User's email address
        
    Returns:
        str or None: Member status if found, None if not found
    """
    try:
        members_table = dynamodb.Table(MEMBERS_TABLE_NAME)
        
        # Scan for member with matching email
        response = members_table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        if response.get('Items'):
            member = response['Items'][0]
            status = member.get('status')
            logger.info(f"Found member {email} with status: {status}")
            return status
        else:
            logger.info(f"No member record found for email: {email}")
            return None
            
    except Exception as e:
        logger.error(f"Error checking member status for {email}: {str(e)}")
        return None

def log_role_assignment_decision(email, member_status, given_name, family_name):
    """
    Log the role assignment decision for audit purposes
    
    Args:
        email (str): User's email address
        member_status (str or None): Member status from database
        given_name (str): User's first name
        family_name (str): User's last name
    """
    try:
        # Create display name
        if given_name or family_name:
            display_name = f"{given_name} {family_name}".strip()
        else:
            display_name = email.split('@')[0]
        
        # Determine role assignment decision
        approved_statuses = ['active', 'approved']
        if member_status and member_status in approved_statuses:
            decision = 'ROLE_ASSIGNED'
            reason = f'Existing approved member (status: {member_status})'
            role_assigned = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')
        elif member_status:
            decision = 'NO_ROLE_ASSIGNED'
            reason = f'Member exists but not approved (status: {member_status})'
            role_assigned = None
        else:
            decision = 'NO_ROLE_ASSIGNED'
            reason = 'New applicant - no member record found'
            role_assigned = None
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'POST_CONFIRMATION_ROLE_DECISION',
            'user_email': email,
            'display_name': display_name,
            'member_status': member_status,
            'decision': decision,
            'reason': reason,
            'role_assigned': role_assigned,
            'organization': ORGANIZATION_SHORT_NAME
        }
        
        # Log as structured JSON for monitoring systems
        logger.info(f"ROLE_ASSIGNMENT_DECISION: {json.dumps(log_entry)}")
        
        # Human-readable log
        logger.info(f"Role assignment decision for {display_name} ({email}): {decision} - {reason}")
        
    except Exception as e:
        logger.error(f"Error logging role assignment decision: {str(e)}")
        # Don't raise exception for logging failures