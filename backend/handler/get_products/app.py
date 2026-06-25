"""
GET /products — Batch-get products by explicit IDs.

Returns product records matching the requested product_ids.
Callers obtain product IDs from the event's product_ids array.

Query Parameters:
    product_ids (required): Comma-separated list of product IDs to fetch.
                            Empty string returns empty list (200).
                            Missing param returns 400.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import json
import os
import boto3

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

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)


def _chunk_list(items: list, chunk_size: int = 100) -> list[list]:
    """Split list into chunks of chunk_size for DynamoDB batch limits."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def _batch_get_products(product_ids: list[str]) -> list[dict]:
    """Fetch products by ID using DynamoDB BatchGetItem, handling 100-item limit."""
    if not product_ids:
        return []

    all_products = []
    for chunk in _chunk_list(product_ids):
        keys = [{'product_id': pid} for pid in chunk]
        response = dynamodb.batch_get_item(
            RequestItems={
                table_name: {'Keys': keys}
            }
        )
        items = response.get('Responses', {}).get(table_name, [])
        all_products.extend(items)

        # Handle unprocessed keys (DynamoDB throttling)
        unprocessed = response.get('UnprocessedKeys', {}).get(table_name, {})
        while unprocessed:
            response = dynamodb.batch_get_item(
                RequestItems={table_name: unprocessed}
            )
            items = response.get('Responses', {}).get(table_name, [])
            all_products.extend(items)
            unprocessed = response.get('UnprocessedKeys', {}).get(table_name, {})

    return all_products


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
        has_event_booking_access = any(
            r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant')
        )

        if not has_webshop_access and not has_event_booking_access:
            return create_error_response(403, 'No product access',
                details={'error': 'access_denied',
                         'details': {'message': 'No qualifying role for product access'}})

        # Get product_ids from query parameters
        query_params = event.get('queryStringParameters') or {}

        if 'product_ids' not in query_params:
            return create_error_response(400, 'product_ids parameter is required')

        raw_product_ids = query_params.get('product_ids', '')

        # Empty string → empty list → 200 with empty products
        if not raw_product_ids.strip():
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({
                    'products': [],
                    'total_count': 0,
                }, default=str)
            }

        # Parse comma-separated IDs and deduplicate
        product_ids = list(set(
            pid.strip() for pid in raw_product_ids.split(',') if pid.strip()
        ))

        log_successful_access(user_email, user_roles, 'get_products')

        # Batch-get products from DynamoDB
        products = _batch_get_products(product_ids)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'products': products,
                'total_count': len(products),
            }, default=str)
        }

    except Exception as e:
        print(f"Error retrieving products: {str(e)}")
        return create_error_response(500, 'Internal server error')
