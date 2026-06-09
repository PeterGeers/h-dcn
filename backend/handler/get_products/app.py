"""
GET /products — Channel-filtered product listing for webshop buyers.

Returns active parent products filtered by the requested channel parameter,
validated against the user's Cognito group claims.

Query Parameters:
    channel (required): Comma-separated channel values (e.g. "h-dcn" or "h-dcn,presmeet")

Requirements: 7.1–7.7, 2.1–2.3
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    from shared.channel_resolver import resolve_channels, validate_channel_access
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_products")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Derive accessible channels from Cognito group claims.
        # Channel resolution IS the access control for this endpoint:
        # users without any qualifying role get an empty channel set → 403.
        user_channels = resolve_channels(user_roles)

        # Get requested channel from query parameters
        query_params = event.get('queryStringParameters') or {}
        requested_channel = query_params.get('channel')

        # If no channel parameter provided, use all user channels
        if not requested_channel:
            if not user_channels:
                return create_error_response(403, 'No channel access',
                    details={'error': 'channel_access_denied',
                             'details': {'requested_channel': '',
                                         'allowed_channels': []}})
            requested_channel = ','.join(sorted(user_channels))

        # Validate requested channel against user access
        access_error = validate_channel_access(requested_channel, user_channels)
        if access_error:
            return access_error

        # Parse the validated channel values
        channels = [t.strip() for t in requested_channel.split(',') if t.strip()]

        log_successful_access(user_email, user_roles, 'get_products')

        # Build filter: is_parent=true, active=true, channel in requested channels
        if len(channels) == 1:
            filter_expr = (
                Attr('is_parent').eq(True) &
                Attr('active').eq(True) &
                Attr('channel').eq(channels[0])
            )
        else:
            filter_expr = (
                Attr('is_parent').eq(True) &
                Attr('active').eq(True) &
                Attr('channel').is_in(channels)
            )

        # Scan with filter
        response = table.scan(FilterExpression=filter_expr)
        products = response.get('Items', [])

        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            products.extend(response.get('Items', []))

        # Return product list with relevant fields
        result = []
        for product in products:
            item = {
                'product_id': product.get('product_id'),
                'name': product.get('name'),
                'description': product.get('description'),
                'price': product.get('price'),
                'channel': product.get('channel'),
                'groep': product.get('groep'),
                'subgroep': product.get('subgroep'),
                'images': product.get('images', []),
                'variant_schema': product.get('variant_schema'),
                'order_item_fields': product.get('order_item_fields'),
                'purchase_rules': product.get('purchase_rules'),
                'active': product.get('active'),
            }
            result.append(item)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'products': result,
                'total_count': len(result),
                'channels': channels,
            }, default=str)
        }

    except Exception as e:
        print(f"Error retrieving products: {str(e)}")
        return create_error_response(500, 'Internal server error')
