import json
import os
import boto3

# Import shared authentication utilities with fallback support
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
    from shared.club_identity import has_presmeet_access
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_club_registry")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

s3 = boto3.client('s3')
BUCKET = os.environ.get('REPORTS_BUCKET_NAME', 'h-dcn-reports')
CLUB_REGISTRY_KEY = 'presmeet/club_registry.json'


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - Club_User level access (events_read covers hdcnLeden members)
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Gate: check Regio_Pressmeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(403, 'PresMeet access required')

        # Log successful access
        log_successful_access(user_email, user_roles, 'get_club_registry')

        # Read club registry from S3
        obj = s3.get_object(Bucket=BUCKET, Key=CLUB_REGISTRY_KEY)
        registry = json.loads(obj['Body'].read().decode('utf-8'))
        return create_success_response(registry)

    except s3.exceptions.NoSuchKey:
        return create_error_response(404, 'Club registry not configured')
    except Exception as e:
        print(f"Error reading club registry: {e}")
        return create_error_response(500, 'Internal server error')
