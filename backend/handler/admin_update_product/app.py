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

# Maximum batch size for DynamoDB batch_write_item
_DYNAMO_BATCH_SIZE = 25


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

        # Determine if variant_schema is being changed
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

        if not update_parts:
            return create_error_response(400, 'No updatable fields provided')

        # Always update updated_at
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

        # Handle variant regeneration if variant_schema changed
        variants_regenerated = False
        new_variants = []
        if variant_schema_changed:
            new_variants = _regenerate_variants(
                product_id, body.get('variant_schema')
            )
            variants_regenerated = True

        result = {
            'product': _convert_decimals(updated_product),
            'message': 'Product updated successfully'
        }
        if variants_regenerated:
            result['variants_regenerated'] = True
            result['variant_count'] = len(new_variants)

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


def _regenerate_variants(product_id: str, new_schema) -> list:
    """
    Delete all existing variants for a product and regenerate from new schema.

    If new_schema is empty/None, creates a Default_Variant.
    Otherwise generates variants from the schema with stock reset to 0.

    Returns the list of new variant records created.
    """
    # 1. Find and delete all existing variants for this parent
    _delete_existing_variants(product_id)

    # 2. Generate new variants
    if new_schema:
        new_variants = generate_variant_combinations(
            new_schema, product_id
        )
    else:
        # No schema = create Default_Variant
        new_variants = [create_default_variant(product_id)]

    # 3. Batch write new variants
    _batch_write_variants(new_variants)

    return new_variants


def _delete_existing_variants(product_id: str) -> None:
    """
    Query and delete all variant records for a parent product.

    Uses scan with filter on parent_id (variants have is_parent=False
    and parent_id set to the parent product_id).
    """
    # Query variants by scanning for parent_id match
    # Note: In production, a GSI on parent_id would be more efficient
    variants_to_delete = []
    scan_kwargs = {
        'FilterExpression': boto3.dynamodb.conditions.Attr('parent_id').eq(product_id)
    }

    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        variants_to_delete.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey')
        if not start_key:
            done = True

    # Batch delete existing variants
    if variants_to_delete:
        _batch_delete_variants(variants_to_delete)


def _batch_delete_variants(variants: list) -> None:
    """Delete variant records in batches of 25."""
    for i in range(0, len(variants), _DYNAMO_BATCH_SIZE):
        batch = variants[i:i + _DYNAMO_BATCH_SIZE]
        with table.batch_writer() as writer:
            for variant in batch:
                writer.delete_item(
                    Key={'product_id': variant['product_id']}
                )


def _batch_write_variants(variants: list) -> None:
    """Write variant records in batches of 25."""
    for i in range(0, len(variants), _DYNAMO_BATCH_SIZE):
        batch = variants[i:i + _DYNAMO_BATCH_SIZE]
        with table.batch_writer() as writer:
            for variant in batch:
                writer.put_item(Item=variant)
