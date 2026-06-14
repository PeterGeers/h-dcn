"""
User operations for the hdcn_cognito_admin handler.

Functions for user CRUD, bulk import, passwordless signup,
and passkey migration checking.
"""
import json
import os
import secrets
import base64
from datetime import datetime
from botocore.exceptions import ClientError

import boto3

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')
USER_POOL_CLIENT_ID = os.environ.get('COGNITO_USER_POOL_CLIENT_ID', '6jhvk853b0lfg9q1m861qs0cug')


def get_users(headers):
    all_users = []
    pagination_token = None

    while True:
        # Build request parameters
        params = {
            'UserPoolId': USER_POOL_ID,
            'Limit': 60
        }

        # Add pagination token if we have one
        if pagination_token:
            params['PaginationToken'] = pagination_token

        # Make the request
        response = cognito_client.list_users(**params)

        # Add users to our list
        all_users.extend(response.get('Users', []))

        # Check if there are more pages
        pagination_token = response.get('PaginationToken')
        if not pagination_token:
            break

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(all_users, default=str)
    }


def verify_user_exists(event, headers):
    """
    Verify if a user exists in the Cognito User Pool by email
    """
    try:
        body = json.loads(event['body'])
        email = body.get('email')

        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }

        # Search for user by email
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1
        )

        users = response.get('Users', [])

        if not users:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found in H-DCN system'})
            }

        user = users[0]

        # Return basic user info
        user_info = {
            'username': user['Username'],
            'email': email,
            'userStatus': user['UserStatus'],
            'enabled': user['Enabled'],
            'userCreateDate': user['UserCreateDate'],
            'userLastModifiedDate': user['UserLastModifiedDate']
        }

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(user_info, default=str)
        }

    except Exception as e:
        print(f"Error verifying user: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


def create_user(event, headers, requesting_user_email=None):
    """
    Create a new user with role assignment validation.
    Permission is already validated by the routing layer (users_manage permission).
    """
    try:
        # Use the already-validated requesting user from routing layer
        requesting_user = requesting_user_email
        if not requesting_user:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }

        # Parse request body
        data = json.loads(event['body'])

        if not data.get('email'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }

        # Cognito pool requires email as username
        cognito_username = data['email']

        user_attributes = [
            {'Name': 'email', 'Value': data['email']},
            {'Name': 'email_verified', 'Value': 'true'}
        ]

        # Add additional attributes
        for key, value in data.get('attributes', {}).items():
            if value:  # Only add non-empty attributes
                user_attributes.append({'Name': key, 'Value': value})

        # Create user in Cognito (passwordless - no temp password needed)
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=cognito_username,
            UserAttributes=user_attributes,
            MessageAction='SUPPRESS'
        )

        # Immediately confirm the user by setting a random password
        # This moves status from FORCE_CHANGE_PASSWORD to CONFIRMED
        # The password is never used - authentication is via passkey/OTP/Google
        random_password = secrets.token_urlsafe(32) + '!A1a'
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=cognito_username,
            Password=random_password,
            Permanent=True
        )

        # Add user to groups if specified
        groups = data.get('groups', '')
        group_list = []
        group_errors = []

        if groups:
            group_list = [g.strip() for g in groups.split(';') if g.strip()]

            # Validate that all groups exist
            try:
                all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
                existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]

                invalid_groups = [group for group in group_list if group not in existing_groups]
                if invalid_groups:
                    group_errors.append(f"Invalid groups specified: {invalid_groups}")
                    group_list = [group for group in group_list if group in existing_groups]

            except Exception as groups_error:
                print(f"Error validating groups: {str(groups_error)}")
                group_errors.append("Failed to validate groups")

            for group_name in group_list:
                try:
                    cognito_client.admin_add_user_to_group(
                        UserPoolId=USER_POOL_ID,
                        Username=cognito_username,
                        GroupName=group_name
                    )
                except Exception as group_error:
                    error_msg = f"Could not add user {cognito_username} to group {group_name}: {str(group_error)}"
                    print(f"Warning: {error_msg}")
                    group_errors.append(error_msg)

        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'User created successfully',
                'username': cognito_username,
                'groups': group_list,
                'group_errors': group_errors,
                'created_by': requesting_user,
                'created_at': datetime.now().isoformat()
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': 'User with this username already exists'})
        }
    except Exception as e:
        print(f"Error in create_user: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to create user'})
        }


def update_user(username, event, headers):
    data = json.loads(event['body'])

    user_attributes = []
    for key, value in data.get('attributes', {}).items():
        user_attributes.append({'Name': key, 'Value': value})

    cognito_client.admin_update_user_attributes(
        UserPoolId=USER_POOL_ID,
        Username=username,
        UserAttributes=user_attributes
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User updated successfully'})
    }


def delete_user(username, headers):
    cognito_client.admin_delete_user(
        UserPoolId=USER_POOL_ID,
        Username=username
    )

    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'User deleted successfully'})
    }


def import_users(event, headers):
    """
    Bulk import users with role assignment validation
    """
    try:
        # Extract Authorization header for permission check
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header required'})
            }

        # Validate requesting user has permission to create users and assign roles
        requesting_user = None
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.replace('Bearer ', '')

            try:
                # Decode JWT token to get requesting user
                parts = jwt_token.split('.')
                if len(parts) == 3:
                    payload_encoded = parts[1]
                    payload_encoded += '=' * (4 - len(payload_encoded) % 4)
                    payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                    payload = json.loads(payload_decoded)
                    requesting_user = payload.get('username') or payload.get('email')

            except Exception as token_error:
                print(f"Error decoding requesting user token: {str(token_error)}")
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid authorization token'})
                }

        if not requesting_user:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Could not identify requesting user'})
            }

        # Check if requesting user has permission to create users and assign roles
        try:
            requesting_user_groups = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=requesting_user
            )

            requesting_user_roles = [group['GroupName'] for group in requesting_user_groups.get('Groups', [])]

            # Only users with System_User_Management can create users and assign roles
            can_manage_users = 'System_User_Management' in requesting_user_roles

            if not can_manage_users:
                return {
                    'statusCode': 403,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Insufficient permissions to import users and assign roles',
                        'required_roles': ['System_User_Management']
                    })
                }

        except Exception as perm_error:
            print(f"Error checking requesting user permissions: {str(perm_error)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Failed to verify permissions'})
            }

        # Parse request body
        data = json.loads(event['body'])
        users = data.get('users', [])

        if not users:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No users specified for import'})
            }

        created_users = []
        existing_users = []
        errors = []

        for user_data in users:
            username = user_data.get('username')
            email = user_data.get('email')

            if not username or not email:
                errors.append(f"Missing username or email for user: {user_data}")
                continue

            try:
                # Check if user already exists
                cognito_client.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
                existing_users.append(username)
                continue

            except cognito_client.exceptions.UserNotFoundException:
                # User doesn't exist, create it
                try:
                    user_attributes = [
                        {'Name': 'email', 'Value': email},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ]

                    # Add additional attributes
                    for key, value in user_data.items():
                        if key not in ['username', 'email', 'groups', 'tempPassword'] and value:
                            user_attributes.append({'Name': key, 'Value': str(value)})

                    # Create user
                    cognito_client.admin_create_user(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        UserAttributes=user_attributes,
                        MessageAction='SUPPRESS'
                    )

                    # Immediately confirm the user (passwordless - no temp password needed)
                    random_password = secrets.token_urlsafe(32) + '!A1a'
                    cognito_client.admin_set_user_password(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        Password=random_password,
                        Permanent=True
                    )

                    # Add to groups if specified
                    groups = user_data.get('groups', '')
                    if groups:
                        group_list = [g.strip() for g in groups.split(';') if g.strip()]

                        # Validate that all groups exist
                        try:
                            all_groups_response = cognito_client.list_groups(UserPoolId=USER_POOL_ID)
                            existing_groups = [group['GroupName'] for group in all_groups_response.get('Groups', [])]

                            invalid_groups = [group for group in group_list if group not in existing_groups]
                            if invalid_groups:
                                errors.append(f"Invalid groups for user {username}: {invalid_groups}")
                                group_list = [group for group in group_list if group in existing_groups]

                        except Exception as groups_error:
                            print(f"Error validating groups for user {username}: {str(groups_error)}")
                            errors.append(f"Failed to validate groups for user {username}")

                        for group_name in group_list:
                            try:
                                cognito_client.admin_add_user_to_group(
                                    UserPoolId=USER_POOL_ID,
                                    Username=username,
                                    GroupName=group_name
                                )
                            except Exception as group_error:
                                errors.append(f"Failed to add {username} to group {group_name}: {str(group_error)}")

                    created_users.append(username)

                except Exception as create_error:
                    errors.append(f"Failed to create user {username}: {str(create_error)}")

            except Exception as check_error:
                errors.append(f"Error checking user {username}: {str(check_error)}")

        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': f'Import completed. Created {len(created_users)} users, {len(existing_users)} already existed.',
                'created_users': created_users,
                'existing_users': existing_users,
                'errors': errors,
                'imported_by': requesting_user,
                'imported_at': datetime.now().isoformat()
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error in import_users: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to import users'})
        }


def passwordless_signup(event, headers):
    """
    Create a new user account for passwordless authentication.

    Uses Cognito sign_up + admin_confirm_sign_up so that the PostConfirmation
    Lambda trigger fires and receives clientMetadata (event_id, source, locale).
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')
        given_name = data.get('given_name')
        family_name = data.get('family_name')
        locale = data.get('locale', 'nl')
        event_id = data.get('event_id')
        source = data.get('source')

        if not email or not given_name or not family_name:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email, given_name, and family_name are required'})
            }

        # Check if user already exists
        try:
            cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            return {
                'statusCode': 409,
                'headers': headers,
                'body': json.dumps({'error': 'User with this email already exists'})
            }
        except cognito_client.exceptions.UserNotFoundException:
            # User doesn't exist, proceed with creation
            pass

        # Build clientMetadata to pass through to PostConfirmation trigger
        client_metadata = {'locale': locale}
        if event_id:
            client_metadata['event_id'] = event_id
        if source:
            client_metadata['source'] = source

        # Create user via sign_up API (triggers PreSignUp Lambda)
        # A random password is used since authentication is passwordless (passkey/OTP/Google)
        random_password = secrets.token_urlsafe(32) + '!A1a'

        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'given_name', 'Value': given_name},
            {'Name': 'family_name', 'Value': family_name},
        ]

        cognito_client.sign_up(
            ClientId=USER_POOL_CLIENT_ID,
            Username=email,
            Password=random_password,
            UserAttributes=user_attributes,
            ClientMetadata=client_metadata,
        )

        # Confirm the user via admin API — this triggers PostConfirmation Lambda
        # which receives the clientMetadata (event_id, source) and handles
        # event_participant creation or regular signup flow
        cognito_client.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=email,
            ClientMetadata=client_metadata,
        )

        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'Account created successfully. Check your email for verification instructions.',
                'username': email,
                'user_status': 'CONFIRMED'
            })
        }

    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 409,
            'headers': headers,
            'body': json.dumps({'error': 'User with this email already exists'})
        }
    except Exception as e:
        print(f"Error in passwordless signup: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"User Pool ID: {USER_POOL_ID}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Failed to create account. Please try again.',
                'debug_info': str(e) if os.environ.get('DEBUG') == 'true' else None
            })
        }


# --- Passkey Registration & Authentication ---
# NOTE: Passkey registration and authentication are now handled client-side
# via Amplify v6 using Cognito's native WebAuthn support.
# - Registration: associateWebAuthnCredential()
# - Authentication: signIn() with preferredChallenge: "WEB_AUTHN"
# The old DIY endpoints (/auth/passkey/register/*, /auth/passkey/authenticate/*)
# now return HTTP 410 Gone with migration guidance.


def passkey_migration_check(event, headers):
    """
    POST /auth/passkey/migrate

    Detects users with old custom:passkey_cred_ids attribute from the
    previous DIY passkey implementation and returns re-enrollment guidance.

    Users with old credentials need to re-register their passkeys using
    Cognito's native WebAuthn flow (via Amplify v6 associateWebAuthnCredential).
    """
    try:
        data = json.loads(event['body'])
        email = data.get('email')

        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email is required'})
            }

        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'User not found'})
            }

        # Check for old DIY passkey attributes
        user_attributes = user_response.get('UserAttributes', [])
        has_old_passkey = False
        old_cred_ids = []

        for attr in user_attributes:
            if attr['Name'] == 'custom:passkey_registered' and attr['Value'] == 'true':
                has_old_passkey = True
            elif attr['Name'] == 'custom:passkey_cred_ids':
                try:
                    old_cred_ids = json.loads(attr['Value'])
                except (json.JSONDecodeError, TypeError):
                    old_cred_ids = []

        if has_old_passkey:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'needsMigration': True,
                    'message': 'Your passkey was registered with an older system. '
                               'Please re-register your passkey to continue using passwordless login.',
                    'oldCredentialCount': len(old_cred_ids),
                    'action': 'RE_ENROLL',
                    'instructions': 'Use the "Register new passkey" button to set up a new passkey '
                                    'via the updated system. Your old passkey will no longer work.'
                })
            }
        else:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'needsMigration': False,
                    'message': 'No migration needed. You can register a new passkey.'
                })
            }

    except Exception as e:
        print(f"Error in passkey_migration_check: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to check passkey migration status'})
        }
