import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

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
    from shared.club_identity import get_club_id, has_presmeet_access, is_presmeet_admin
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_presmeet_booking")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))


def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


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
        log_successful_access(user_email, user_roles, 'get_presmeet_booking')

        # Determine if user is admin
        is_admin = is_presmeet_admin(user_roles)

        # Determine which club_id to query
        query_params = event.get('queryStringParameters') or {}

        if is_admin and 'club_id' in query_params:
            # Admin can view any club's booking via query parameter
            club_id = query_params['club_id']
        else:
            # Regular user: get club_id from Member record
            club_id = get_club_id(user_email)
            if not club_id:
                return create_error_response(403, 'Missing club assignment')

        # Query Orders table for PresMeet booking matching club_id
        scan_response = orders_table.scan(
            FilterExpression=Attr('source').eq('presmeet') & Attr('tenant').eq('presmeet') & Attr('club_id').eq(club_id)
        )
        items = scan_response['Items']

        # Handle pagination for large result sets
        while 'LastEvaluatedKey' in scan_response:
            scan_response = orders_table.scan(
                FilterExpression=Attr('source').eq('presmeet') & Attr('tenant').eq('presmeet') & Attr('club_id').eq(club_id),
                ExclusiveStartKey=scan_response['LastEvaluatedKey']
            )
            items.extend(scan_response['Items'])

        # Return 404 if no booking exists
        if not items:
            return create_error_response(404, 'Booking not found')

        # Return the first (and expected only) booking for this club
        booking = convert_decimals(items[0])

        return create_success_response(booking)

    except Exception as e:
        print(f"Error in get_presmeet_booking handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
