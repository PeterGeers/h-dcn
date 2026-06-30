import json
import os
import boto3
from datetime import datetime, timezone
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
    from shared.product_validation import (
        validate_product,
        validate_order_item_fields,
        validate_purchase_rules
    )
    from shared.price_validation import validate_price_field
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_update_product")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

# Fields allowed to be updated on a product.
# Derived from the productFields registry (frontend/src/config/productFields/fields.ts).
# Only fields where editable !== false are included.
# See: docs/decisions/dutch-field-names.md
UPDATABLE_FIELDS = [
    # identity
    'naam',
    'artikelcode',
    # pricing
    'prijs',
    # categorization
    'groep',
    'subgroep',
    # media
    'images',
    # metadata
    'active',
    # ordering
    'order_item_fields',
    'purchase_rules',
]


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Products_CRUD
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_update_product')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate legacy product payload (min/max per club, required_attributes)
        is_valid, errors = validate_product(body)
        if not is_valid:
            return create_error_response(400, 'Validation failed', {'errors': errors})

        # Validate new unified model fields if present
        validation_errors = _validate_new_fields(body)
        if validation_errors:
            return create_error_response(400, 'Validation failed', {'errors': validation_errors})

        # Check product exists and is a parent
        response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in response:
            return create_error_response(404, 'Product not found')

        existing = response['Item']
        # Block updates only for explicit variants (is_parent=False).
        # Products without is_parent set are regular products, not variants.
        if existing.get('is_parent') is False:
            return create_error_response(
                400,
                'Cannot update a variant with this endpoint. Use the variant update endpoint.'
            )

        # Reject variant_schema if included in request body (field is removed)
        if 'variant_schema' in body:
            return create_error_response(400, 'variant_schema field is no longer supported')

        # Validate price field if provided
        if 'prijs' in body:
            price_val, price_err = validate_price_field(body['prijs'], 'prijs')
            if price_err:
                return create_error_response(400, price_err)
            if price_val is not None:
                body['prijs'] = price_val

        # Build update expression for simple fields
        update_parts = []
        expression_values = {}
        expression_names = {}
        remove_parts = []

        for field in UPDATABLE_FIELDS:
            if field in body:
                value = body[field]
                # Empty list/None/null → REMOVE the field from DynamoDB
                if value is None or (isinstance(value, list) and len(value) == 0):
                    remove_parts.append(f'#{field}')
                    expression_names[f'#{field}'] = field
                else:
                    attr_name = f'#{field}'
                    attr_val = f':{field}'
                    update_parts.append(f'{attr_name} = {attr_val}')
                    expression_names[attr_name] = field
                    expression_values[attr_val] = value

        if not update_parts and not remove_parts:
            return create_error_response(400, 'No updatable fields provided')

        # Always update updated_at
        update_parts.append('#updated_at = :updated_at')
        expression_names['#updated_at'] = 'updated_at'
        expression_values[':updated_at'] = datetime.now(timezone.utc).isoformat()

        update_expression = 'SET ' + ', '.join(update_parts)
        if remove_parts:
            update_expression += ' REMOVE ' + ', '.join(remove_parts)

        # Update the parent product record
        updated = table.update_item(
            Key={'product_id': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        updated_product = updated.get('Attributes', {})

        result = {
            'product': _convert_decimals(updated_product),
            'message': 'Product updated successfully'
        }

        return create_success_response(result)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating product: {str(e)}")
        return create_error_response(500, 'Internal server error')


def _convert_decimals(obj):
    """
    Recursively convert Decimal values in a dict/list to int or float.

    DynamoDB returns Decimal types which are not JSON serializable by default.
    """
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def _validate_new_fields(body: dict) -> list:
    """
    Validate order_item_fields and purchase_rules if present.

    Returns a list of structured error dicts, or empty list if valid.
    """
    all_errors = []

    # Validate order_item_fields
    order_item_fields = body.get('order_item_fields')
    if order_item_fields is not None:
        # Allow setting to empty list/None to remove fields
        if order_item_fields:
            is_valid, errors = validate_order_item_fields(order_item_fields)
            if not is_valid:
                all_errors.extend(errors)

    # Validate purchase_rules
    purchase_rules = body.get('purchase_rules')
    if purchase_rules is not None:
        # Allow setting to empty dict/None to remove rules
        if purchase_rules:
            is_valid, errors = validate_purchase_rules(purchase_rules)
            if not is_valid:
                all_errors.extend(errors)

    return all_errors
