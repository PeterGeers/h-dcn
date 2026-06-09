import boto3
import os
import json
import logging
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from decimal import Decimal

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
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_variants")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

table_name = str(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
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

        # Log successful access
        log_successful_access(user_email, user_roles, 'get_variants')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Verify parent product exists
        parent_response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in parent_response:
            return create_error_response(404, 'Product not found')

        parent = parent_response['Item']

        # Verify this is a parent product, not a variant
        if parent.get('is_parent') is False:
            return create_error_response(400, 'Cannot get variants for a variant record. Use the parent product ID.')

        # Scan for variant records with parent_id matching the product_id
        variants = []
        scan_kwargs = {
            'FilterExpression': Attr('parent_id').eq(product_id)
        }

        while True:
            response = table.scan(**scan_kwargs)
            variants.extend(response.get('Items', []))

            # Handle pagination
            if 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                break

        logger.info(f"Found {len(variants)} variants for product {product_id}")

        return create_success_response(convert_decimals({
            'product_id': product_id,
            'variants': variants,
            'total_count': len(variants)
        }))

    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return create_error_response(500, f'Database error: {str(e)}')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_response(500, 'Internal server error')
