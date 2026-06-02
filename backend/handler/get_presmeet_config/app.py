import json
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
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_presmeet_config")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))


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

        # Log successful access
        log_successful_access(user_email, user_roles, 'get_presmeet_config')

        # Query Producten table for PresMeet config records (source = "presmeet_config")
        config_response = producten_table.scan(
            FilterExpression=Attr('source').eq('presmeet_config')
        )
        config_items = config_response['Items']

        # Handle pagination for large result sets
        while 'LastEvaluatedKey' in config_response:
            config_response = producten_table.scan(
                FilterExpression=Attr('source').eq('presmeet_config'),
                ExclusiveStartKey=config_response['LastEvaluatedKey']
            )
            config_items.extend(config_response['Items'])

        # Query Events table for the active PresMeet event (source = "presmeet")
        events_response = events_table.scan(
            FilterExpression=Attr('source').eq('presmeet')
        )
        event_items = events_response['Items']

        # Handle pagination
        while 'LastEvaluatedKey' in events_response:
            events_response = events_table.scan(
                FilterExpression=Attr('source').eq('presmeet'),
                ExclusiveStartKey=events_response['LastEvaluatedKey']
            )
            event_items.extend(events_response['Items'])

        # Get the active event (first match, or None)
        active_event = None
        if event_items:
            ev = event_items[0]
            active_event = {
                'event_id': ev.get('event_id'),
                'start_date': ev.get('start_date'),
                'end_date': ev.get('end_date'),
                'title': ev.get('title')
            }

        # Build product type configs list
        product_types = convert_decimals(config_items)

        # Build response
        response_body = {
            'product_types': product_types,
            'event': active_event
        }

        return create_success_response(response_body)

    except Exception as e:
        print(f"Error in get_presmeet_config handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
