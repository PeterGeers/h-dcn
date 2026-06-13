"""
GET /products — Event-filtered product listing for webshop buyers.

Returns active parent products filtered by event_id parameter.
Products with event_id=null are webshop products, products with a specific
event_id are event-linked products.

Query Parameters:
    event_id (optional): Filter by event_id. Use "null" for webshop products,
                         or a specific event_id for event-linked products.
                         If omitted, returns all accessible products.

Requirements: 7.1–7.7, 2.1–2.3, 12.2
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

        # Access control: user must have at least one qualifying role
        has_webshop_access = 'hdcnLeden' in user_roles
        has_event_booking_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant'))

        if not has_webshop_access and not has_event_booking_access:
            return create_error_response(403, 'No product access',
                details={'error': 'access_denied',
                         'details': {'message': 'No qualifying role for product access'}})

        # Get event_id filter from query parameters
        query_params = event.get('queryStringParameters') or {}
        requested_event_id = query_params.get('event_id')

        log_successful_access(user_email, user_roles, 'get_products')

        # Build filter: is_parent=true, active!=false (includes products without active field)
        # Products with active=false are excluded; products with active=true OR no active field are included
        filter_expr = (
            Attr('is_parent').eq(True) &
            (Attr('active').ne(False) | Attr('active').not_exists())
        )

        if requested_event_id is not None:
            if requested_event_id == 'null' or requested_event_id == '':
                # Webshop products: event_id is null or not set
                filter_expr = filter_expr & (
                    Attr('event_id').not_exists() | Attr('event_id').eq(None)
                )
            else:
                # Event-linked products: filter by specific event_id
                filter_expr = filter_expr & Attr('event_id').eq(requested_event_id)

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
                'event_id': product.get('event_id'),
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
                'event_id': requested_event_id,
            }, default=str)
        }

    except Exception as e:
        print(f"Error retrieving products: {str(e)}")
        return create_error_response(500, 'Internal server error')
