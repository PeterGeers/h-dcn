"""
H-DCN Cognito Pre Sign-Up Lambda Function

Links federated (Google) identities to existing native Cognito users
so that a single user can log in with either method and share the same
attributes, groups, and custom:member_id.

Trigger: PreSignUp_ExternalProvider
"""

import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client('cognito-idp')


def lambda_handler(event, context):
    """
    Pre Sign-Up trigger handler.
    
    When a Google user signs up, check if a native user with the same email
    already exists. If so, link the Google identity to the native user and
    auto-confirm/verify the email.
    """
    try:
        logger.info(f"Pre Sign-Up trigger: {json.dumps(event, default=str)}")

        trigger_source = event.get('triggerSource', '')
        user_pool_id = event['userPoolId']
        user_attributes = event['request'].get('userAttributes', {})
        email = user_attributes.get('email', '')

        # Only act on external provider sign-ups (Google, Facebook, etc.)
        if trigger_source != 'PreSignUp_ExternalProvider':
            logger.info(f"Not an external provider sign-up ({trigger_source}), passing through")
            return event

        if not email:
            logger.warning("No email in external provider sign-up, passing through")
            return event

        logger.info(f"External provider sign-up for email: {email}")

        # Check if a native (non-federated) user with this email already exists
        native_user = find_native_user(user_pool_id, email)

        if native_user:
            native_username = native_user['Username']
            logger.info(f"Found existing native user {native_username} for {email}, linking provider")

            # Extract provider info from the federated username
            # Format: "Google_<id>" or "Facebook_<id>"
            federated_username = event['userName']
            provider_name, provider_user_id = parse_federated_username(federated_username)

            if provider_name and provider_user_id:
                # Link the federated identity to the existing native user
                try:
                    cognito_client.admin_link_provider_for_user(
                        UserPoolId=user_pool_id,
                        DestinationUser={
                            'ProviderName': 'Cognito',
                            'ProviderAttributeValue': native_username
                        },
                        SourceUser={
                            'ProviderName': provider_name,
                            'ProviderAttributeName': 'Cognito_Subject',
                            'ProviderAttributeValue': provider_user_id
                        }
                    )
                    logger.info(f"Successfully linked {provider_name} identity to native user {native_username}")
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'InvalidParameterException':
                        logger.warning(f"Provider already linked or invalid params: {str(e)}")
                    else:
                        logger.error(f"Error linking provider: {error_code} - {str(e)}")
                        raise
            else:
                logger.warning(f"Could not parse provider info from username: {federated_username}")
        else:
            logger.info(f"No existing native user found for {email}, allowing new sign-up")

        # Auto-confirm and verify email for external provider users
        event['response']['autoConfirmUser'] = True
        event['response']['autoVerifyEmail'] = True

        return event

    except Exception as e:
        logger.error(f"Error in pre-signup handler: {str(e)}")
        # Return event to avoid blocking sign-up
        return event


def find_native_user(user_pool_id, email):
    """
    Find a native (non-federated) Cognito user by email.
    Returns the user dict if found, None otherwise.
    """
    try:
        response = cognito_client.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"'
        )

        for user in response.get('Users', []):
            username = user['Username']
            # Native users have a UUID-style username, not "Google_xxx"
            if not any(username.startswith(prefix) for prefix in ['Google_', 'Facebook_', 'SAML_', 'LoginWithAmazon_']):
                logger.info(f"Found native user: {username} for email {email}")
                return user

        return None

    except Exception as e:
        logger.error(f"Error finding native user for {email}: {str(e)}")
        return None


def parse_federated_username(username):
    """
    Parse provider name and user ID from federated username.
    E.g. 'Google_112283382738141445724' -> ('Google', '112283382738141445724')
    """
    providers = ['Google', 'Facebook', 'SAML', 'LoginWithAmazon']
    for provider in providers:
        prefix = f"{provider}_"
        if username.startswith(prefix):
            user_id = username[len(prefix):]
            return provider, user_id
    return None, None
