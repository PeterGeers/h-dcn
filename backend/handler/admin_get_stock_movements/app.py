import json
import os
import boto3
from boto3.dynamodb.conditions import Key

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
    lambda_handler = create_smart_fallback_handler("admin_get_stock_movements")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
movements_table_name = os.environ.get('STOCK_MOVEMENTS_TABLE_NAME', 'StockMovements')
movements_table = dynamodb.Table(movements_table_name)


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

        log_successful_access(user_email, user_roles, 'admin_get_stock_movements')

        # Get path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        variant_id = path_params.get('vid')
        if not product_id or not variant_id:
            return create_error_response(400, 'Product ID and Variant ID are required')

        # Query stock movements using GSI variant_id-index
        response = movements_table.query(
            IndexName='variant_id-index',
            KeyConditionExpression=Key('variant_id').eq(variant_id),
            ScanIndexForward=False  # Most recent first
        )

        movements = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = movements_table.query(
                IndexName='variant_id-index',
                KeyConditionExpression=Key('variant_id').eq(variant_id),
                ScanIndexForward=False,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            movements.extend(response.get('Items', []))

        return create_success_response({
            'movements': movements,
            'total_count': len(movements),
            'variant_id': variant_id
        })

    except Exception as e:
        print(f"Error retrieving stock movements: {str(e)}")
        return create_error_response(500, 'Internal server error')
