import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

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
    lambda_handler = create_smart_fallback_handler("get_variants")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    """
    GET /products/{id}/variants

    Fetches all variant records for a parent product using the
    parent_id-index GSI. Validates channel access before returning results.

    Path parameters:
        id - The parent product_id

    Returns:
        200: List of variant records with stock, variant_attributes,
             allow_oversell, price, and active status
        400: Missing product ID
        403: Channel access denied
        404: Parent product not found
        500: Internal server error
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        log_successful_access(user_email, user_roles, 'get_variants')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Fetch parent product to validate tenant access
        parent_response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in parent_response:
            return create_error_response(404, f'Product {product_id} not found')

        parent = parent_response['Item']

        # Validate that it's actually a parent product
        if parent.get('is_parent') is False:
            return create_error_response(
                400, 'The specified ID is a variant, not a parent product'
            )

        # Resolve user channels from Cognito groups and validate access
        user_channels = resolve_channels(user_roles)
        product_channel = parent.get('channel', parent.get('tenant', 'h-dcn'))

        channel_error = validate_channel_access(product_channel, user_channels)
        if channel_error:
            return channel_error

        # Query variants using parent_id-index GSI
        variants = []
        query_kwargs = {
            'IndexName': 'parent_id-index',
            'KeyConditionExpression': Key('parent_id').eq(product_id),
        }

        response = table.query(**query_kwargs)
        variants.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = table.query(**query_kwargs)
            variants.extend(response.get('Items', []))

        # Shape the response with all variant records
        variant_records = []
        for variant in variants:
            record = {
                'product_id': variant.get('product_id'),
                'parent_id': variant.get('parent_id'),
                'name': variant.get('name', ''),
                'variant_attributes': variant.get('variant_attributes', {}),
                'stock': int(variant.get('stock', 0)),
                'sold_count': int(variant.get('sold_count', 0)),
                'allow_oversell': variant.get('allow_oversell', False),
                'active': variant.get('active', True),
            }
            # Include price (convert Decimal to float for JSON)
            price = variant.get('price')
            if price is not None:
                record['price'] = float(price)
            else:
                record['price'] = None
            variant_records.append(record)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'product_id': product_id,
                'variants': variant_records,
                'total_count': len(variant_records)
            })
        }

    except ClientError as e:
        print(f"DynamoDB error in get_variants: {str(e)}")
        return create_error_response(500, f'Database error: {str(e)}')
    except Exception as e:
        print(f"Unexpected error in get_variants: {str(e)}")
        return create_error_response(500, 'Internal server error')
