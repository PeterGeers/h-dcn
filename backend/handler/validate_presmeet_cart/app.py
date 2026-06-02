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
    from shared.presmeet_validation import (
        extract_club_id,
        validate_attributes,
        validate_product_type,
        DEFAULT_ATTRIBUTE_SCHEMAS,
    )
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("validate_presmeet_cart")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))


def load_product_type_configs():
    """Load Product_Type_Config records from Producten table.

    Returns a dict mapping product_type to its config record.
    Falls back to DEFAULT_ATTRIBUTE_SCHEMAS if no configs are found.
    """
    try:
        response = producten_table.scan(
            FilterExpression=Attr('source').eq('presmeet_config')
        )
        config_items = response['Items']

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = producten_table.scan(
                FilterExpression=Attr('source').eq('presmeet_config'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            config_items.extend(response['Items'])

        if not config_items:
            return {}

        # Build lookup by product_type
        configs = {}
        for item in config_items:
            pt = item.get('product_type')
            if pt:
                configs[pt] = item

        return configs

    except Exception as e:
        print(f"Error loading product type configs: {str(e)}")
        return {}


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - Club_User level access
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'validate_presmeet_cart')

        # Extract club_id from Cognito groups
        club_id = extract_club_id(user_roles)
        if not club_id:
            return create_error_response(403, 'Missing club assignment')

        # Parse request body
        body_str = event.get('body')
        if not body_str:
            return create_error_response(400, 'Invalid JSON in request body')

        try:
            body = json.loads(body_str)
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, 'Invalid JSON in request body')

        # Validate that 'items' field is present and is a list
        if not isinstance(body, dict) or 'items' not in body:
            return create_error_response(400, 'Missing required field: items')

        items = body['items']
        if not isinstance(items, list):
            return create_error_response(400, 'Field "items" must be an array')

        # Load product type configs from Producten table
        configs = load_product_type_configs()

        # Validate each item
        errors = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append({
                    'item_id': f'item_{i}',
                    'field': '_item',
                    'message': 'Each item must be a JSON object',
                    'constraint': 'type',
                })
                continue

            item_id = item.get('item_id', f'item_{i}')
            product_type = item.get('product_type')
            attributes = item.get('attributes', {})

            # Validate product_type
            if not product_type:
                errors.append({
                    'item_id': item_id,
                    'field': 'product_type',
                    'message': 'Product type is required',
                    'constraint': 'required',
                })
                continue

            is_valid, error_msg = validate_product_type(product_type)
            if not is_valid:
                errors.append({
                    'item_id': item_id,
                    'field': 'product_type',
                    'message': error_msg,
                    'constraint': 'enum',
                })
                continue

            # Get config for this product_type (from DB or fallback to defaults)
            type_config = configs.get(product_type, {})

            # Validate attributes against schema
            attr_errors = validate_attributes(product_type, attributes, type_config)
            for err in attr_errors:
                errors.append({
                    'item_id': item_id,
                    'field': err['field'],
                    'message': err['message'],
                    'constraint': err['constraint'],
                })

        # Build response
        if errors:
            return create_success_response({
                'valid': False,
                'errors': errors,
            })
        else:
            return create_success_response({
                'valid': True,
                'errors': [],
            })

    except Exception as e:
        print(f"Error in validate_presmeet_cart handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
