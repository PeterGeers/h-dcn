import json
import os
import boto3

# Import from shared auth layer (REQUIRED)
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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_get_products")
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

        # Validate permissions - requires Products_Read
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_Read'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_get_products')

        # Get optional event_id filter from query params
        query_params = event.get('queryStringParameters') or {}
        event_id_filter = query_params.get('event_id')

        # Query products (parent products only)
        filter_expr = boto3.dynamodb.conditions.Attr('is_parent').eq(True)
        if event_id_filter == 'null':
            # Webshop products: event_id is null or not set
            filter_expr = filter_expr & (
                boto3.dynamodb.conditions.Attr('event_id').not_exists()
                | boto3.dynamodb.conditions.Attr('event_id').eq(None)
            )
        elif event_id_filter:
            # Event-linked products: filter by specific event_id
            filter_expr = filter_expr & boto3.dynamodb.conditions.Attr('event_id').eq(event_id_filter)

        response = table.scan(FilterExpression=filter_expr)
        products = response.get('Items', [])

        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            products.extend(response.get('Items', []))

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'products': products, 'total_count': len(products)}, default=str)
        }

    except Exception as e:
        print(f"Error retrieving admin products: {str(e)}")
        return create_error_response(500, 'Internal server error')
