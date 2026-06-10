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
        validate_variant_schema,
        validate_order_item_fields,
        validate_purchase_rules
    )
    from shared.variant_helpers import (
        generate_variant_combinations,
        create_default_variant
    )
    from shared.variant_sync import (
        sync_schema_to_variants,
        sync_variant_to_schema,
        MaxCombinationsExceeded
    )
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

# Fields allowed to be updated on a product
UPDATABLE_FIELDS = [
    'name', 'description', 'category', 'price', 'active',
    'min_per_club', 'max_per_club', 'required_attributes',
    'image_url', 'event_id', 'groep', 'subgroep', 'images',
    'order_item_fields', 'purchase_rules'
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
        if not existing.get('is_parent', False):
            return create_error_response(
                400,
                'Cannot update a variant with this endpoint. Use the variant update endpoint.'
            )

        # Detect variant action (bottom-up: add/remove variant)
        variant_action = body.pop('variant_action', None)
        variant_attributes = body.pop('variant_attributes', None)

        # Determine if variant_schema is being changed (top-down)
        variant_schema_changed = _has_variant_schema_changed(body, existing)

        # Build update expression for simple fields
        update_parts = []
        expression_values = {}
        expression_names = {}

        for field in UPDATABLE_FIELDS:
            if field in body:
                attr_name = f'#{field}'
                attr_val = f':{field}'
                update_parts.append(f'{attr_name} = {attr_val}')
                expression_names[attr_name] = field
                expression_values[attr_val] = body[field]

        # Handle variant_schema field separately (not in UPDATABLE_FIELDS)
        if 'variant_schema' in body:
            update_parts.append('#variant_schema = :variant_schema')
            expression_names['#variant_schema'] = 'variant_schema'
            expression_values[':variant_schema'] = body['variant_schema']

        # If only a variant action is provided (no other fields), still allow it
        has_field_updates = bool(update_parts)
        if not has_field_updates and not variant_action:
            return create_error_response(400, 'No updatable fields provided')

        # Always update updated_at when there are field updates
        if has_field_updates:
            update_parts.append('#updated_at = :updated_at')
            expression_names['#updated_at'] = 'updated_at'
            expression_values[':updated_at'] = datetime.now(timezone.utc).isoformat()

            update_expression = 'SET ' + ', '.join(update_parts)

            # Update the parent product record
            updated = table.update_item(
                Key={'product_id': product_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            updated_product = updated.get('Attributes', {})
        else:
            updated_product = existing

        # Handle top-down sync: variant_schema changed → sync_schema_to_variants
        sync_result = None
        if variant_schema_changed:
            parent_price = Decimal(str(body.get('price', existing.get('price', 0))))
            try:
                sync_result = sync_schema_to_variants(
                    table, product_id, body['variant_schema'], parent_price
                )
            except MaxCombinationsExceeded as e:
                return create_error_response(400, str(e), {
                    'count': e.count,
                    'max': e.max
                })

        # Handle bottom-up sync: variant add/remove → sync_variant_to_schema
        updated_schema = None
        if variant_action and variant_attributes:
            if variant_action in ('add_variant', 'remove_variant'):
                updated_schema = sync_variant_to_schema(
                    table, product_id, variant_attributes
                )

        result = {
            'product': _convert_decimals(updated_product),
            'message': 'Product updated successfully'
        }
        if sync_result:
            result['variants_synced'] = True
            result['sync_result'] = {
                'created': sync_result.created,
                'preserved': sync_result.preserved,
                'deactivated': sync_result.deactivated,
            }
        if updated_schema is not None:
            result['variant_schema_updated'] = True
            result['variant_schema'] = updated_schema

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
    Validate variant_schema, order_item_fields, and purchase_rules if present.

    Returns a list of structured error dicts, or empty list if valid.
    """
    all_errors = []

    # Validate variant_schema
    variant_schema = body.get('variant_schema')
    if variant_schema is not None:
        # Allow setting to empty dict/None to remove schema
        if variant_schema:
            is_valid, errors = validate_variant_schema(variant_schema)
            if not is_valid:
                all_errors.extend(errors)

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


def _has_variant_schema_changed(body: dict, existing: dict) -> bool:
    """
    Determine whether the variant_schema is being changed.

    Returns True if:
    - variant_schema is in the request body AND differs from existing value
    """
    if 'variant_schema' not in body:
        return False

    new_schema = body.get('variant_schema')
    existing_schema = existing.get('variant_schema')

    # Normalize empty/None values for comparison
    new_normalized = new_schema if new_schema else None
    existing_normalized = existing_schema if existing_schema else None

    return new_normalized != existing_normalized
