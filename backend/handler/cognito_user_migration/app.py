"""
H-DCN Cognito User Migration Lambda Function

This function handles the UserMigration_Authentication trigger for the new Cognito
User Pool. When a user signs in for the first time to the new pool, this Lambda
validates their credentials against the old pool in the personal account and
migrates their user data (attributes and group memberships) transparently.

Trigger: UserMigration_Authentication, UserMigration_ForgotPassword

Cross-account access:
  - The Lambda assumes a role or uses direct permissions to call the old Cognito
    pool (eu-west-1_OAT3oPCIm) in account 344561557829.
"""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
OLD_USER_POOL_ID = os.environ.get('OLD_USER_POOL_ID', 'eu-west-1_OAT3oPCIm')
OLD_USER_POOL_CLIENT_ID = os.environ.get('OLD_USER_POOL_CLIENT_ID', '')
OLD_ACCOUNT_REGION = os.environ.get('OLD_ACCOUNT_REGION', 'eu-west-1')

# Initialize Cognito client for the old pool (same region)
# The Lambda's IAM role has cross-account permissions to call the old pool
cognito_client = boto3.client('cognito-idp', region_name=OLD_ACCOUNT_REGION)


def lambda_handler(event, context):
    """
    AWS Cognito UserMigration Lambda trigger handler.

    Handles two trigger sources:
    - UserMigration_Authentication: User signs in for the first time
    - UserMigration_ForgotPassword: User requests password reset (not yet in new pool)

    Args:
        event: Cognito trigger event containing user credentials
        context: Lambda context object

    Returns:
        Modified event with user attributes for migration
    """
    try:
        logger.info(f"User migration trigger event: {json.dumps(event, default=str)}")

        trigger_source = event.get('triggerSource', '')
        username = event.get('userName', '')

        if trigger_source == 'UserMigration_Authentication':
            return handle_authentication_migration(event, username)
        elif trigger_source == 'UserMigration_ForgotPassword':
            return handle_forgot_password_migration(event, username)
        else:
            logger.warning(f"Unhandled trigger source: {trigger_source}")
            raise Exception(f"Unsupported trigger source: {trigger_source}")

    except Exception as e:
        logger.error(f"Error in user migration handler: {str(e)}")
        # Re-raise to signal Cognito that migration failed
        # This will cause Cognito to return "user not found" to the client
        raise


def handle_authentication_migration(event, username):
    """
    Handle UserMigration_Authentication trigger.

    1. Validate credentials against old pool via AdminInitiateAuth
    2. Retrieve user attributes from old pool
    3. Retrieve group memberships from old pool
    4. Return user data with finalUserStatus=CONFIRMED

    Args:
        event: Cognito trigger event
        username: The username (email) attempting to sign in

    Returns:
        Modified event with user attributes for Cognito to create the user
    """
    password = event.get('request', {}).get('password', '')

    if not password:
        logger.error("No password provided in migration authentication request")
        raise Exception("Password is required for migration authentication")

    # Step 1: Validate credentials against old pool
    logger.info(f"Validating credentials for user {username} against old pool {OLD_USER_POOL_ID}")
    auth_result = authenticate_against_old_pool(username, password)

    if not auth_result:
        logger.info(f"Authentication failed for user {username} against old pool")
        raise Exception("Authentication failed against old user pool")

    logger.info(f"Authentication successful for user {username} against old pool")

    # Step 2: Retrieve user attributes from old pool
    user_attributes = get_user_attributes(username)

    if not user_attributes:
        logger.error(f"Could not retrieve attributes for user {username} from old pool")
        raise Exception("Failed to retrieve user attributes from old pool")

    # Step 3: Retrieve group memberships from old pool
    group_memberships = get_user_groups(username)
    logger.info(f"User {username} groups in old pool: {group_memberships}")

    # Step 4: Build migration response
    event['response']['userAttributes'] = build_user_attributes(user_attributes)
    event['response']['finalUserStatus'] = 'CONFIRMED'
    event['response']['messageAction'] = 'SUPPRESS'
    event['response']['forceAliasCreation'] = False

    # Store group memberships in a custom attribute or client metadata
    # so the post-confirmation trigger can assign groups
    if group_memberships:
        # Store groups as comma-separated string in desiredDeliveryMediums
        # We use clientMetadata to pass group info to post-confirmation trigger
        if 'clientMetadata' not in event['request']:
            event['request']['clientMetadata'] = {}
        event['request']['clientMetadata']['migratedGroups'] = ','.join(group_memberships)

    logger.info(f"Migration response prepared for user {username} with status CONFIRMED")
    return event


def handle_forgot_password_migration(event, username):
    """
    Handle UserMigration_ForgotPassword trigger.

    When a user who exists in the old pool but not the new pool requests
    a password reset, we migrate their account data so Cognito can send
    the reset email.

    Args:
        event: Cognito trigger event
        username: The username (email) requesting password reset

    Returns:
        Modified event with user attributes for Cognito to create the user
    """
    logger.info(f"Handling forgot password migration for user {username}")

    # Retrieve user attributes from old pool (no auth needed for forgot password)
    user_attributes = get_user_attributes(username)

    if not user_attributes:
        logger.error(f"User {username} not found in old pool for forgot password migration")
        raise Exception("User not found in old pool")

    # Retrieve group memberships
    group_memberships = get_user_groups(username)
    logger.info(f"User {username} groups in old pool: {group_memberships}")

    # Build migration response
    event['response']['userAttributes'] = build_user_attributes(user_attributes)
    event['response']['messageAction'] = 'SUPPRESS'
    event['response']['forceAliasCreation'] = False

    # Store group memberships for post-confirmation trigger
    if group_memberships:
        if 'clientMetadata' not in event['request']:
            event['request']['clientMetadata'] = {}
        event['request']['clientMetadata']['migratedGroups'] = ','.join(group_memberships)

    logger.info(f"Forgot password migration response prepared for user {username}")
    return event


def authenticate_against_old_pool(username, password):
    """
    Validate user credentials against the old Cognito User Pool using AdminInitiateAuth.

    Args:
        username: The username (email) to authenticate
        password: The user's password

    Returns:
        dict: Authentication result if successful, None if failed
    """
    try:
        response = cognito_client.admin_initiate_auth(
            UserPoolId=OLD_USER_POOL_ID,
            ClientId=OLD_USER_POOL_CLIENT_ID,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        logger.info(f"AdminInitiateAuth successful for user {username}")
        return response

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ('NotAuthorizedException', 'UserNotFoundException'):
            logger.info(f"Authentication failed for {username}: {error_code}")
            return None
        elif error_code == 'PasswordResetRequiredException':
            logger.info(f"User {username} requires password reset in old pool")
            return None
        elif error_code == 'UserNotConfirmedException':
            logger.info(f"User {username} is not confirmed in old pool")
            return None
        else:
            logger.error(f"Unexpected error authenticating {username}: {error_code} - {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Unexpected error in authenticate_against_old_pool: {str(e)}")
        raise


def get_user_attributes(username):
    """
    Retrieve user attributes from the old Cognito User Pool.

    Args:
        username: The username (email) to look up

    Returns:
        list: User attributes list, or None if user not found
    """
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=OLD_USER_POOL_ID,
            Username=username
        )
        logger.info(f"Retrieved attributes for user {username} from old pool")
        return response.get('UserAttributes', [])

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            logger.info(f"User {username} not found in old pool")
            return None
        else:
            logger.error(f"Error getting user attributes for {username}: {error_code} - {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Unexpected error in get_user_attributes: {str(e)}")
        raise


def get_user_groups(username):
    """
    Retrieve group memberships for a user from the old Cognito User Pool.

    Args:
        username: The username (email) to look up

    Returns:
        list: List of group names the user belongs to (e.g., ['hdcnLeden', 'admin'])
    """
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=OLD_USER_POOL_ID,
            Username=username
        )
        groups = [group['GroupName'] for group in response.get('Groups', [])]
        logger.info(f"User {username} belongs to groups: {groups}")
        return groups

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            logger.info(f"User {username} not found in old pool for group lookup")
            return []
        else:
            logger.error(f"Error getting groups for {username}: {error_code} - {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Unexpected error in get_user_groups: {str(e)}")
        raise


def build_user_attributes(old_attributes):
    """
    Build the user attributes dict for the migration response.

    Cognito expects a flat dict of attribute_name: value for the migration response.
    We map standard attributes and preserve custom attributes.

    Args:
        old_attributes: List of attribute dicts from AdminGetUser response
            [{'Name': 'email', 'Value': 'user@example.com'}, ...]

    Returns:
        dict: Flat dict of attributes for the migration response
    """
    attributes = {}

    # Standard attributes to migrate
    standard_attrs = ['email', 'name', 'given_name', 'family_name', 'phone_number']

    for attr in old_attributes:
        attr_name = attr['Name']
        attr_value = attr['Value']

        if attr_name in standard_attrs:
            attributes[attr_name] = attr_value
        elif attr_name.startswith('custom:'):
            # Preserve custom attributes
            attributes[attr_name] = attr_value
        elif attr_name == 'sub':
            # Skip the sub attribute - new pool will generate its own
            continue
        elif attr_name == 'email_verified':
            # Set email as verified since we confirmed auth against old pool
            attributes['email_verified'] = 'true'
        elif attr_name == 'phone_number_verified':
            attributes['phone_number_verified'] = attr_value

    # Ensure email_verified is set to true for migrated users
    if 'email_verified' not in attributes:
        attributes['email_verified'] = 'true'

    logger.info(f"Built migration attributes: {list(attributes.keys())}")
    return attributes
