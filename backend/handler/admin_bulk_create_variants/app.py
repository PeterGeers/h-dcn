import json
import os
import uuid
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
    from shared.variant_helpers import should_remove_default_variant
    from shared.price_validation import validate_price_field
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_bulk_create_variants")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

# Single-axis decision: a product supports exactly one variant axis at a time.
MAX_AXES = 1
MAX_VALUES_PER_AXIS = 20


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

        log_successful_access(user_email, user_roles, 'admin_bulk_create_variants')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Get parent product
        parent_response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in parent_response:
            return create_error_response(404, 'Parent product not found')

        parent = parent_response['Item']
        # Only allow variant creation for parent products
        if parent.get('is_parent') is False:
            return create_error_response(400, 'Cannot add variants to a non-parent product')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate axis_name (non-empty after trim)
        axis_name = body.get('axis_name')
        if not isinstance(axis_name, str) or not axis_name.strip():
            return create_error_response(400, 'axis_name is required')
        axis_name = axis_name.strip()

        # Validate values: must be a non-empty list; trim, drop empties, de-dup
        raw_values = body.get('values')
        if not isinstance(raw_values, list) or not raw_values:
            return create_error_response(400, 'values must be a non-empty list')

        cleaned_values = _normalize_values(raw_values)
        if not cleaned_values:
            return create_error_response(400, 'values must contain at least one non-empty value')

        if len(cleaned_values) > MAX_VALUES_PER_AXIS:
            return create_error_response(
                400, f'Too many values: maximum {MAX_VALUES_PER_AXIS} values per axis'
            )

        # Scan existing variants for the parent
        existing_variants_response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq(product_id)
            & boto3.dynamodb.conditions.Attr('is_parent').eq(False)
        )
        existing_variants = existing_variants_response.get('Items', [])

        # Derive existing axis name(s) from existing variant_attributes keys
        existing_axes = set()
        for existing in existing_variants:
            for key in (existing.get('variant_attributes') or {}).keys():
                existing_axes.add(key)

        # Single-axis enforcement: reject a differing axis
        if existing_axes and axis_name not in existing_axes:
            return create_error_response(
                400, 'This product already uses a different axis'
            )

        # Build the set of existing values for the target axis
        existing_values = set()
        for existing in existing_variants:
            attrs = existing.get('variant_attributes') or {}
            if axis_name in attrs:
                existing_values.add(attrs[axis_name])

        # Optional overrides
        raw_prijs = body.get('prijs')
        if raw_prijs is not None:
            prijs_val, prijs_err = validate_price_field(raw_prijs, 'prijs')
            if prijs_err:
                return create_error_response(400, prijs_err)
        else:
            prijs_val = parent.get('prijs')

        stock = body.get('stock', 0)
        allow_oversell = body.get('allow_oversell', False)

        now = datetime.now(timezone.utc).isoformat()

        # Create a variant record for each value not already present
        created = []
        skipped = []
        for value in cleaned_values:
            if value in existing_values:
                skipped.append(value)
                continue

            variant_id = f"var_{uuid.uuid4().hex[:12]}"
            variant = {
                'product_id': variant_id,
                'parent_id': product_id,
                'naam': '',
                'is_parent': False,
                'variant_attributes': {axis_name: value},
                'prijs': prijs_val,
                'stock': stock,
                'sold_count': 0,
                'allow_oversell': allow_oversell,
                'active': True,
                'created_at': now,
                'updated_at': now,
            }
            table.put_item(Item=variant)
            created.append(variant)

        # Remove the Default_Variant if real variants were added to a default-only product
        removed_default = False
        if should_remove_default_variant(existing_variants, created):
            default_variant_id = f"var_{product_id}_default"
            try:
                table.delete_item(Key={'product_id': default_variant_id})
                removed_default = True
            except Exception as del_err:
                print(f"Warning: Could not remove Default_Variant: {str(del_err)}")

        return create_success_response(_serialize_response({
            'created': len(created),
            'skipped': skipped,
            'default_variant_removed': removed_default,
            'message': f'{len(created)} variant(s) created, {len(skipped)} skipped'
        }))

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error bulk creating variants: {str(e)}")
        return create_error_response(500, 'Internal server error')


def _normalize_values(raw_values):
    """Trim values, drop empty/whitespace-only, de-dup case-sensitively, first-seen order."""
    seen = set()
    cleaned = []
    for value in raw_values:
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    return cleaned


def _serialize_response(data):
    """Convert response dict for JSON (Decimal → int/float)."""
    return json.loads(json.dumps(data, default=_json_serialize))


def _json_serialize(obj):
    """Custom JSON serializer for Decimal."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
