"""
H-DCN Cognito Post-Authentication Lambda Function

This function handles post-authentication actions for users logging in.
It ensures users have appropriate roles assigned, especially for Google SSO users
who bypass the post-confirmation trigger.

Trigger: PostAuthentication_Authentication
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

# Initialize DynamoDB client for member status checking
dynamodb = boto3.resource('dynamodb')

# Get organization details from environment variables
ORGANIZATION_NAME = os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland')
ORGANIZATION_SHORT_NAME = os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN')
MEMBERS_TABLE_NAME = os.environ.get('MEMBERS_TABLE_NAME', 'Members')

def lambda_handler(event, context):
    """
    AWS Cognito Post-Authentication Lambda trigger handler
    
    Args:
        event: Cognito trigger event containing user data
        context: Lambda context object
        
    Returns:
        Original event (required by Cognito)
    """
    try:
        logger.info(f"Cognito Post-Authentication trigger event: {json.dumps(event, default=str)}")
        
        # Extract event information
        trigger_source = event.get('triggerSource')
        user_attributes = event.get('request', {}).get('userAttributes', {})
        username = event.get('userName', '')
        user_pool_id = event.get('userPoolId', '')
        
        # Extract user information
        email = user_attributes.get('email', username)
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        
        logger.info(f"Processing post-authentication for trigger: {trigger_source}, user: {email}")
        
        # Handle post-authentication
        if trigger_source == 'PostAuthentication_Authentication':
            handle_user_authentication(user_pool_id, username, email, given_name, family_name)
        else:
            logger.warning(f"Unhandled trigger source: {trigger_source}")
        
        logger.info("Post-authentication processing completed successfully")
        return event
        
    except Exception as e:
        logger.error(f"Error in post-authentication handler: {str(e)}")
        # Return original event to prevent authentication failure
        # Log error but don't block user authentication
        return event

def handle_user_authentication(user_pool_id, username, email, given_name, family_name):
    """
    Handle post-authentication actions for user login
    
    This function ensures users have appropriate roles assigned,
    especially important for Google SSO users who bypass post-confirmation.
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username (usually email)
        email: User's email address
        given_name: User's first name
        family_name: User's last name
    """
    try:
        logger.info(f"Processing post-authentication for user: {email}")
        
        # Get user's current groups
        current_groups = get_user_groups(user_pool_id, username)
        logger.info(f"User {email} current groups: {current_groups}")
        
        # Check if user only has the auto-generated Google group
        # or has no meaningful roles assigned
        needs_role_assignment = should_assign_roles(current_groups, email)
        
        if needs_role_assignment:
            logger.info(f"User {email} needs role assignment")
            
            # Check member status and assign appropriate roles
            member_status = check_member_status(email)
            
            if member_status:
                logger.info(f"User {email} found in Members table with status: {member_status}")
                
                # If user is approved, assign default role
                approved_statuses = ['active', 'approved']
                if member_status in approved_statuses:
                    default_group = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')
                    logger.info(f"User {email} is approved member, adding to group: {default_group}")
                    add_user_to_group(user_pool_id, username, default_group)
                    logger.info(f"Successfully added existing approved member {email} to group {default_group}")
                else:
                    logger.info(f"User {email} is not approved (status: {member_status}), no additional role assigned")
            else:
                logger.info(f"User {email} not found in Members table - no additional role assigned")
            
            # Log the role assignment decision for audit
            log_role_assignment_decision(email, member_status, given_name, family_name, current_groups)
        else:
            logger.info(f"User {email} already has appropriate roles assigned")
        
    except Exception as e:
        logger.error(f"Error in authentication handler: {str(e)}")
        raise

def get_user_groups(user_pool_id, username):
    """
    Get current groups for a user
    
    Args:
        user_pool_id: Cognito User Pool ID
        username: User's username
        
    Returns:
        List of group names
    """
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        return [group['GroupName'] for group in response.get('Groups', [])]
    except Exception as e:
        logger.error(f"Error getting user groups for {username}: {str(e)}")
        return []

def should_assign_roles(current_groups, email):
    """
    Determine if user needs role assignment
    
    Args:
        current_groups: List of current group names
        email: User's email address
        
    Returns:
        Boolean indicating if roles should be assigned
    """
    # If user has no groups, they need assignment
    if not current_groups:
        return True
    
    # If user only has auto-generated federated identity groups, they need assignment
    federated_groups = [group for group in current_groups if '_Google' in group or '_Facebook' in group or '_SAML' in group]
    meaningful_groups = [group for group in current_groups if group not in federated_groups]
    
    # If they only have federated groups and no meaningful business groups
    if federated_groups and not meaningful_groups:
        logger.info(f"User {email} only has federated groups: {federated_groups}, needs role assignment")
        return True
    
    # If they don't have basic member role or applicant role, they might need it
    if 'hdcnLeden' not in current_groups and 'Verzoek_lid' not in current_groups:
        logger.info(f"User {email} missing member or applicant role, checking if they should have it")
        return True
    
    return False

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

def log_role_assignment_decision(email, member_status, given_name, family_name, current_groups):
    """
    Log the role assignment decision for audit purposes
    
    Args:
        email (str): User's email address
        member_status (str or None): Member status from database
        given_name (str): User's first name
        family_name (str): User's last name
        current_groups (list): User's current groups before assignment
    """
    try:
        from datetime import datetime
        
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
            reason = 'No member record found'
            role_assigned = None
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'POST_AUTHENTICATION_ROLE_DECISION',
            'user_email': email,
            'display_name': display_name,
            'member_status': member_status,
            'current_groups': current_groups,
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