"""
hdcn_cognito_admin Lambda handler — thin router.

Dispatches requests to sub-modules based on httpMethod + path.
Sub-modules manage their own Cognito client and USER_POOL_ID internally.
"""
import json

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        log_successful_access
    )
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("hdcn_cognito_admin")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

# --- Sub-module imports ---
from user_operations import (
    get_users,
    verify_user_exists,
    create_user,
    update_user,
    delete_user,
    import_users,
    passwordless_signup,
    passkey_migration_check,
)
from group_operations import (
    get_groups,
    create_group,
    delete_group,
    add_user_to_group,
    remove_user_from_group,
    get_user_groups,
    import_groups,
    assign_user_groups,
    get_users_in_group,
)
from auth_operations import (
    get_auth_login,
    get_auth_permissions,
    get_pool_info,
)
from role_operations import (
    get_user_roles,
    assign_user_roles_auth,
    remove_user_role_auth,
)
from permission_utils import (
    validate_field_permissions,
    get_user_field_permissions,
    check_role_permission,
    get_role_summary,
)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    '/auth/passkey/register/begin',       # Deprecated - returns 410
    '/auth/passkey/register/complete',    # Deprecated - returns 410
    '/auth/passkey/authenticate/begin',   # Deprecated - returns 410
    '/auth/passkey/authenticate/complete',  # Deprecated - returns 410
    '/auth/passkey/migrate',
    '/auth/signup',
    '/cognito/auth/signup',
    '/auth/verify-user',
]

# Deprecated passkey endpoints (return 410 Gone)
DEPRECATED_PASSKEY_REGISTER = {
    '/auth/passkey/register/begin',
    '/auth/passkey/register/complete',
}
DEPRECATED_PASSKEY_AUTH = {
    '/auth/passkey/authenticate/begin',
    '/auth/passkey/authenticate/complete',
}


def lambda_handler(event, context):
    """Main entry point — routes to sub-module functions."""
    headers = cors_headers()

    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        method = event['httpMethod']
        path = event['path']

        # Debug logging
        print(f"Received request: {method} {path}")
        print(f"Event: {json.dumps(event, default=str)}")

        # --- Authentication & Authorization ---
        is_public_endpoint = any(path.startswith(ep) for ep in PUBLIC_ENDPOINTS)
        user_email = None
        user_roles = None

        if not is_public_endpoint:
            user_email, user_roles, auth_error = extract_user_credentials(event)
            if auth_error:
                return auth_error

            is_authorized, error_response, regional_info = validate_permissions_with_regions(
                user_roles, ['users_manage'], user_email, {'operation': 'hdcn_cognito_admin'}
            )
            if not is_authorized:
                return error_response

            log_successful_access(user_email, user_roles, 'hdcn_cognito_admin')

        # --- Route dispatch ---
        response = _dispatch(method, path, event, headers, user_email)
        if response is not None:
            return response

        # No route matched
        print(f"No route matched for: {method} {path}")
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Endpoint not found',
                'path': path,
                'method': method,
                'available_auth_endpoints': ['/auth/signup', '/auth/passkey/register/begin', '/auth/passkey/authenticate/begin']
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }


def _dispatch(method, path, event, headers, user_email):
    """Route the request to the correct sub-module function. Returns None if unmatched."""

    # --- Deprecated passkey endpoints (410 Gone) ---
    if path in DEPRECATED_PASSKEY_REGISTER and method == 'POST':
        return {
            'statusCode': 410,
            'headers': headers,
            'body': json.dumps({
                'error': 'This endpoint is deprecated. Passkey registration is now handled client-side via Cognito native WebAuthn.',
                'code': 'ENDPOINT_DEPRECATED',
                'migration': 'Use Amplify v6 associateWebAuthnCredential() instead.'
            })
        }

    if path in DEPRECATED_PASSKEY_AUTH and method == 'POST':
        return {
            'statusCode': 410,
            'headers': headers,
            'body': json.dumps({
                'error': 'This endpoint is deprecated. Passkey authentication is now handled via Cognito native WebAuthn.',
                'code': 'ENDPOINT_DEPRECATED',
                'migration': 'Use Amplify v6 signIn with preferredChallenge: "WEB_AUTHN" instead.'
            })
        }

    # --- User operations ---
    if path == '/cognito/users':
        if method == 'GET':
            return get_users(headers)
        if method == 'POST':
            return create_user(event, headers, user_email)

    if path == '/cognito/users/import' and method == 'POST':
        return import_users(event, headers)

    if path == '/cognito/users/assign-groups' and method == 'POST':
        return assign_user_groups(event, headers)

    # /cognito/users/{username}/groups/{group_name}
    if '/cognito/users/' in path and '/groups/' in path:
        parts = path.split('/')
        username = parts[3]
        group_name = parts[5]
        if method == 'POST':
            return add_user_to_group(username, group_name, headers)
        if method == 'DELETE':
            return remove_user_from_group(username, group_name, headers)

    # /cognito/users/{username}/groups
    if path.startswith('/cognito/users/') and path.endswith('/groups'):
        username = path.split('/')[3]
        return get_user_groups(username, headers)

    # /cognito/users/{username} — PUT / DELETE
    if path.startswith('/cognito/users/'):
        username = path.split('/')[3]
        if method == 'PUT':
            return update_user(username, event, headers)
        if method == 'DELETE':
            return delete_user(username, headers)

    # --- Group operations ---
    if path == '/cognito/groups':
        if method == 'GET':
            return get_groups(headers)
        if method == 'POST':
            return create_group(event, headers)

    if path == '/cognito/groups/import' and method == 'POST':
        return import_groups(event, headers)

    # /cognito/groups/{group_name}/users
    if path.startswith('/cognito/groups/') and path.endswith('/users'):
        import urllib.parse
        group_name = urllib.parse.unquote(path.split('/')[3])
        return get_users_in_group(group_name, headers)

    # /cognito/groups/{group_name} — DELETE
    if path.startswith('/cognito/groups/'):
        import urllib.parse
        group_name = urllib.parse.unquote(path.split('/')[3])
        if method == 'DELETE':
            return delete_group(group_name, headers)

    # --- Auth / pool info ---
    if path == '/cognito/pool':
        return get_pool_info(headers)

    if path == '/auth/verify-user' and method == 'POST':
        return verify_user_exists(event, headers)

    if path in ('/auth/signup', '/cognito/auth/signup'):
        print(f"Matched auth/signup route with method: {method}")
        if method == 'POST':
            print("Calling passwordless_signup function")
            return passwordless_signup(event, headers)
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': f'Method {method} not allowed for /auth/signup'})
        }

    if path == '/auth/passkey/migrate' and method == 'POST':
        return passkey_migration_check(event, headers)

    if path == '/auth/login' and method == 'GET':
        return get_auth_login(event, headers)

    if path == '/auth/permissions' and method == 'GET':
        return get_auth_permissions(event, headers)

    # --- Role operations ---
    # /auth/users/{user_id}/roles/{role} — DELETE
    if path.startswith('/auth/users/') and '/roles/' in path:
        parts = path.split('/')
        if len(parts) >= 6:
            user_id = parts[3]
            role = parts[5]
            if method == 'DELETE':
                return remove_user_role_auth(user_id, role, event, headers)

    # /auth/users/{user_id}/roles — GET / POST
    if path.startswith('/auth/users/') and path.endswith('/roles'):
        user_id = path.split('/')[3]
        if method == 'GET':
            return get_user_roles(user_id, event, headers)
        if method == 'POST':
            return assign_user_roles_auth(user_id, event, headers)

    return None
