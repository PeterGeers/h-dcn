"""
H-DCN Cognito Role Assignment Lambda Function

This function handles automatic role assignment based on member status changes.
It ensures that:
1. New applicants get NO roles until approved
2. Approved members automatically receive the hdcnLeden role
3. Role changes are properly audited and logged

This function can be triggered by:
- DynamoDB streams when member status changes
- Direct invocation from update_member handler
- Manual administrative actions
"""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("cognito_role_assignment")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Get configuration from environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'eu-west-1_OAT3oPCIm')
MEMBERS_TABLE_NAME = os.environ.get('MEMBERS_TABLE_NAME', 'Members')
DEFAULT_MEMBER_GROUP = os.environ.get('DEFAULT_MEMBER_GROUP', 'hdcnLeden')

def lambda_handler(event, context):
    """
    AWS Lambda handler for role assignment based on member status changes
    
    Args:
        event: Lambda event (can be DynamoDB stream, direct invocation, etc.)
        context: Lambda context object
        
    Returns:
        dict: Response with status and details
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Check if this is a DynamoDB stream event (no auth needed for system triggers)
        if 'Records' in event and event['Records'][0].get('eventSource') == 'aws:dynamodb':
            logger.info("Processing DynamoDB stream event (no auth required)")
            return handle_dynamodb_stream(event)
        
        # For direct API invocations, require authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions - only system admins can manage roles
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['users_manage'], user_email, {'operation': 'cognito_role_assignment'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'cognito_role_assignment')
        
        logger.info(f"Role assignment event: {json.dumps(event, default=str)}")
        
        # Handle different event types
        if 'member_id' in event and 'status_change' in event:
            # Direct invocation for status change
            return handle_status_change_event(event)
        elif 'member_email' in event and 'action' in event:
            # Direct invocation for specific member
            return handle_member_action_event(event)
        else:
            logger.warning(f"Unhandled event type: {event}")
            return create_error_response(400, 'Unhandled event type')
        
    except Exception as e:
        logger.error(f"Error in role assignment handler: {str(e)}")
        return create_error_response(500, str(e))

def handle_dynamodb_stream(event):
    """
    Handle DynamoDB stream events for member status changes
    
    Args:
        event: DynamoDB stream event
        
    Returns:
        dict: Processing results
    """
    results = []
    
    for record in event['Records']:
        try:
            if record['eventName'] in ['INSERT', 'MODIFY']:
                # Extract old and new member data
                old_image = record.get('dynamodb', {}).get('OldImage', {})
                new_image = record.get('dynamodb', {}).get('NewImage', {})
                
                # Convert DynamoDB format to regular dict
                old_member = dynamodb_to_dict(old_image) if old_image else {}
                new_member = dynamodb_to_dict(new_image) if new_image else {}
                
                # Check if status changed
                old_status = old_member.get('status')
                new_status = new_member.get('status')
                
                if old_status != new_status:
                    member_id = new_member.get('member_id')
                    member_email = new_member.get('email')
                    
                    logger.info(f"Status change detected for member {member_id}: {old_status} -> {new_status}")
                    
                    result = process_status_change(
                        member_id=member_id,
                        member_email=member_email,
                        old_status=old_status,
                        new_status=new_status,
                        member_data=new_member
                    )
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error processing DynamoDB record: {str(e)}")
            results.append({
                'success': False,
                'error': str(e),
                'record': record.get('dynamodb', {}).get('Keys', {})
            })
    
    return create_success_response({
        'processed_records': len(results),
        'results': results
    })

def handle_status_change_event(event):
    """
    Handle direct invocation for status change
    
    Args:
        event: Event with member_id and status_change details
        
    Returns:
        dict: Processing result
    """
    member_id = event['member_id']
    status_change = event['status_change']
    old_status = status_change.get('old_status')
    new_status = status_change.get('new_status')
    
    # Get member data from DynamoDB
    members_table = dynamodb.Table(MEMBERS_TABLE_NAME)
    response = members_table.get_item(Key={'member_id': member_id})
    
    if 'Item' not in response:
        return create_error_response(404, 'Member not found')
    
    member_data = response['Item']
    member_email = member_data.get('email')
    
    result = process_status_change(
        member_id=member_id,
        member_email=member_email,
        old_status=old_status,
        new_status=new_status,
        member_data=member_data
    )
    
    return create_success_response(result)

def handle_member_action_event(event):
    """
    Handle direct invocation for specific member actions
    
    Args:
        event: Event with member_email and action details
        
    Returns:
        dict: Processing result
    """
    member_email = event['member_email']
    action = event['action']
    
    if action == 'assign_default_role':
        result = assign_default_member_role(member_email)
    elif action == 'remove_all_roles':
        result = remove_all_member_roles(member_email)
    elif action == 'verify_role_assignment':
        result = verify_member_role_assignment(member_email)
    else:
        return create_error_response(400, f'Unknown action: {action}')
    
    return create_success_response(result)

def process_status_change(member_id, member_email, old_status, new_status, member_data):
    """
    Process member status change and update Cognito roles accordingly
    
    Args:
        member_id (str): Member ID
        member_email (str): Member email (Cognito username)
        old_status (str): Previous status
        new_status (str): New status
        member_data (dict): Complete member data
        
    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"Processing status change for {member_email}: {old_status} -> {new_status}")
        
        # Determine required role changes based on status change
        role_changes = determine_role_changes(old_status, new_status)
        
        if not role_changes:
            logger.info(f"No role changes required for status change: {old_status} -> {new_status}")
            return {
                'success': True,
                'action': 'no_change',
                'member_id': member_id,
                'member_email': member_email,
                'status_change': f"{old_status} -> {new_status}"
            }
        
        # Apply role changes
        results = []
        for change in role_changes:
            if change['action'] == 'add_role':
                result = add_user_to_cognito_group(member_email, change['role'])
            elif change['action'] == 'remove_role':
                result = remove_user_from_cognito_group(member_email, change['role'])
            else:
                result = {'success': False, 'error': f"Unknown action: {change['action']}"}
            
            results.append({
                'action': change['action'],
                'role': change['role'],
                'result': result
            })
        
        # Log the role assignment change
        log_role_assignment_change(
            member_id=member_id,
            member_email=member_email,
            old_status=old_status,
            new_status=new_status,
            role_changes=role_changes,
            results=results
        )
        
        return {
            'success': True,
            'member_id': member_id,
            'member_email': member_email,
            'status_change': f"{old_status} -> {new_status}",
            'role_changes': results
        }
        
    except Exception as e:
        logger.error(f"Error processing status change for {member_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'member_id': member_id,
            'member_email': member_email
        }

def determine_role_changes(old_status, new_status):
    """
    Determine what role changes are needed based on status change
    
    Args:
        old_status (str): Previous status
        new_status (str): New status
        
    Returns:
        list: List of role change actions
    """
    changes = []
    
    # Define status categories
    approved_statuses = ['active', 'approved']
    unapproved_statuses = ['new_applicant', 'pending', 'rejected', 'suspended', 'inactive']
    
    # Determine if member should have default role
    old_should_have_role = old_status in approved_statuses if old_status else False
    new_should_have_role = new_status in approved_statuses if new_status else False
    
    # Add role if newly approved
    if not old_should_have_role and new_should_have_role:
        changes.append({
            'action': 'add_role',
            'role': DEFAULT_MEMBER_GROUP,
            'reason': f'Member approved (status: {old_status} -> {new_status})'
        })
    
    # Remove role if no longer approved
    elif old_should_have_role and not new_should_have_role:
        changes.append({
            'action': 'remove_role',
            'role': DEFAULT_MEMBER_GROUP,
            'reason': f'Member no longer approved (status: {old_status} -> {new_status})'
        })
    
    return changes

def add_user_to_cognito_group(username, group_name):
    """
    Add user to Cognito User Pool group
    
    Args:
        username (str): Cognito username (usually email)
        group_name (str): Name of the group to add user to
        
    Returns:
        dict: Result of the operation
    """
    try:
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        
        logger.info(f"Successfully added user {username} to group {group_name}")
        return {
            'success': True,
            'action': 'added_to_group',
            'username': username,
            'group': group_name
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ResourceNotFoundException':
            if 'Group' in error_message:
                logger.error(f"Group {group_name} not found in user pool {USER_POOL_ID}")
            else:
                logger.error(f"User {username} not found in user pool {USER_POOL_ID}")
        elif error_code == 'UserNotFoundException':
            logger.error(f"User {username} not found in user pool {USER_POOL_ID}")
        else:
            logger.error(f"Error adding user to group: {error_code} - {error_message}")
        
        return {
            'success': False,
            'error': f"{error_code}: {error_message}",
            'username': username,
            'group': group_name
        }
    except Exception as e:
        logger.error(f"Unexpected error adding user to group: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'username': username,
            'group': group_name
        }

def remove_user_from_cognito_group(username, group_name):
    """
    Remove user from Cognito User Pool group
    
    Args:
        username (str): Cognito username (usually email)
        group_name (str): Name of the group to remove user from
        
    Returns:
        dict: Result of the operation
    """
    try:
        response = cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        
        logger.info(f"Successfully removed user {username} from group {group_name}")
        return {
            'success': True,
            'action': 'removed_from_group',
            'username': username,
            'group': group_name
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ResourceNotFoundException':
            logger.warning(f"User {username} or group {group_name} not found - may already be removed")
        elif error_code == 'UserNotFoundException':
            logger.warning(f"User {username} not found in user pool {USER_POOL_ID}")
        else:
            logger.error(f"Error removing user from group: {error_code} - {error_message}")
        
        return {
            'success': False,
            'error': f"{error_code}: {error_message}",
            'username': username,
            'group': group_name
        }
    except Exception as e:
        logger.error(f"Unexpected error removing user from group: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'username': username,
            'group': group_name
        }

def assign_default_member_role(member_email):
    """
    Assign default member role to a user
    
    Args:
        member_email (str): Member email (Cognito username)
        
    Returns:
        dict: Result of the operation
    """
    return add_user_to_cognito_group(member_email, DEFAULT_MEMBER_GROUP)

def remove_all_member_roles(member_email):
    """
    Remove all roles from a member (for new applicants)
    
    Args:
        member_email (str): Member email (Cognito username)
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Get user's current groups
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=member_email
        )
        
        current_groups = [group['GroupName'] for group in response.get('Groups', [])]
        
        if not current_groups:
            return {
                'success': True,
                'action': 'no_groups_to_remove',
                'username': member_email,
                'message': 'User has no groups assigned'
            }
        
        # Remove user from all groups
        results = []
        for group_name in current_groups:
            result = remove_user_from_cognito_group(member_email, group_name)
            results.append(result)
        
        return {
            'success': True,
            'action': 'removed_all_groups',
            'username': member_email,
            'removed_groups': current_groups,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error removing all roles from {member_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'username': member_email
        }

def verify_member_role_assignment(member_email):
    """
    Verify that a member's Cognito roles match their member status
    
    Args:
        member_email (str): Member email (Cognito username)
        
    Returns:
        dict: Verification result with recommendations
    """
    try:
        # Get member data from DynamoDB
        members_table = dynamodb.Table(MEMBERS_TABLE_NAME)
        response = members_table.scan(
            FilterExpression='email = :email',
            ExpressionAttributeValues={':email': member_email}
        )
        
        if not response.get('Items'):
            return {
                'success': False,
                'error': 'Member not found in database',
                'member_email': member_email
            }
        
        member_data = response['Items'][0]
        member_status = member_data.get('status', 'unknown')
        
        # Get user's current Cognito groups
        cognito_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=member_email
        )
        
        current_groups = [group['GroupName'] for group in cognito_response.get('Groups', [])]
        
        # Determine expected roles based on status
        approved_statuses = ['active', 'approved']
        should_have_default_role = member_status in approved_statuses
        has_default_role = DEFAULT_MEMBER_GROUP in current_groups
        
        # Check if roles match expected state
        roles_correct = should_have_default_role == has_default_role
        
        verification_result = {
            'success': True,
            'member_email': member_email,
            'member_status': member_status,
            'should_have_default_role': should_have_default_role,
            'has_default_role': has_default_role,
            'current_groups': current_groups,
            'roles_correct': roles_correct
        }
        
        # Add recommendations if roles are incorrect
        if not roles_correct:
            if should_have_default_role and not has_default_role:
                verification_result['recommendation'] = f'Add user to {DEFAULT_MEMBER_GROUP} group'
                verification_result['action_needed'] = 'add_default_role'
            elif not should_have_default_role and has_default_role:
                verification_result['recommendation'] = f'Remove user from {DEFAULT_MEMBER_GROUP} group'
                verification_result['action_needed'] = 'remove_default_role'
        
        return verification_result
        
    except Exception as e:
        logger.error(f"Error verifying role assignment for {member_email}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'member_email': member_email
        }

def log_role_assignment_change(member_id, member_email, old_status, new_status, role_changes, results):
    """
    Log role assignment changes for audit purposes
    
    Args:
        member_id (str): Member ID
        member_email (str): Member email
        old_status (str): Previous status
        new_status (str): New status
        role_changes (list): List of role changes made
        results (list): Results of role change operations
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ROLE_ASSIGNMENT_CHANGE',
        'member_id': member_id,
        'member_email': member_email,
        'status_change': {
            'old_status': old_status,
            'new_status': new_status
        },
        'role_changes': role_changes,
        'results': results,
        'success_count': len([r for r in results if r.get('result', {}).get('success', False)]),
        'failure_count': len([r for r in results if not r.get('result', {}).get('success', False)])
    }
    
    # Log as structured JSON for monitoring systems
    logger.info(f"ROLE_ASSIGNMENT_AUDIT: {json.dumps(log_entry)}")
    
    # Human-readable log
    successful_changes = [r for r in results if r.get('result', {}).get('success', False)]
    failed_changes = [r for r in results if not r.get('result', {}).get('success', False)]
    
    if successful_changes:
        success_summary = ', '.join([f"{r['action']} {r['role']}" for r in successful_changes])
        logger.info(f"Role assignment success for {member_email}: {success_summary} (status: {old_status} -> {new_status})")
    
    if failed_changes:
        failure_summary = ', '.join([f"{r['action']} {r['role']}" for r in failed_changes])
        logger.error(f"Role assignment failures for {member_email}: {failure_summary} (status: {old_status} -> {new_status})")

def dynamodb_to_dict(dynamodb_item):
    """
    Convert DynamoDB item format to regular Python dict
    
    Args:
        dynamodb_item (dict): DynamoDB item in stream format
        
    Returns:
        dict: Regular Python dictionary
    """
    result = {}
    for key, value in dynamodb_item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = value['N']
        elif 'BOOL' in value:
            result[key] = value['BOOL']
        elif 'NULL' in value:
            result[key] = None
        # Add more type conversions as needed
    return result