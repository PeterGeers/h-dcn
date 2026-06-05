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

        # Get optional tenant filter from query params
        query_params = event.get('queryStringParameters') or {}
        tenant_filter = query_params.get('tenant')

        # Query products (parent products only)
        if tenant_filter:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('tenant').eq(tenant_filter) & boto3.dynamodb.conditions.Attr('is_parent').eq(True)
            )
        else:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('is_parent').eq(True)
            )

        products = response.get('Items', [])

        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            if tenant_filter:
                response = table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('tenant').eq(tenant_filter) & boto3.dynamodb.conditions.Attr('is_parent').eq(True),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            else:
                response = table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('is_parent').eq(True),
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
