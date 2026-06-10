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
    from shared.variant_helpers import (
        create_default_variant,
    )
    from shared.variant_sync import (
        sync_schema_to_variants,
        MaxCombinationsExceeded,
    )
    from shared.product_validation import (
        validate_product,
        validate_variant_schema,
        validate_order_item_fields,
        validate_purchase_rules,
    )
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_create_product")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

# Max images allowed on a parent product
_MAX_IMAGES = 10
_MAX_GROEP_LENGTH = 50
_MAX_SUBGROEP_LENGTH = 50


def _validate_catalog_fields(body):
    """Validate groep, subgroep, and images fields."""
    errors = []

    groep = body.get('groep')
    if groep is not None:
        if not isinstance(groep, str):
            errors.append('groep must be a string')
        elif len(groep) > _MAX_GROEP_LENGTH:
            errors.append(
                f'groep exceeds maximum length of {_MAX_GROEP_LENGTH} characters'
            )

    subgroep = body.get('subgroep')
    if subgroep is not None:
        if not isinstance(subgroep, str):
            errors.append('subgroep must be a string')
        elif len(subgroep) > _MAX_SUBGROEP_LENGTH:
            errors.append(
                f'subgroep exceeds maximum length of {_MAX_SUBGROEP_LENGTH} characters'
            )

    images = body.get('images')
    if images is not None:
        if not isinstance(images, list):
            errors.append('images must be an array')
        elif len(images) > _MAX_IMAGES:
            errors.append(
                f'images exceeds maximum of {_MAX_IMAGES} items'
            )
        else:
            for idx, img in enumerate(images):
                if not isinstance(img, str) or not img.strip():
                    errors.append(f'images[{idx}] must be a non-empty string URL')

    return errors


def _json_serialize(obj):
    """Custom JSON serializer for Decimal and other non-standard types."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _serialize_response(data):
    """Convert response dict for JSON (Decimal → int/float)."""
    return json.loads(json.dumps(data, default=_json_serialize))


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

        log_successful_access(user_email, user_roles, 'admin_create_product')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate base product payload (legacy validation: min/max per club, required_attributes)
        is_valid, errors = validate_product(body)
        if not is_valid:
            return create_error_response(400, 'Validation failed', {'errors': errors})

        # Validate new unified model fields (if provided)
        all_field_errors = []

        variant_schema = body.get('variant_schema')
        if variant_schema is not None:
            schema_valid, schema_errors = validate_variant_schema(variant_schema)
            if not schema_valid:
                all_field_errors.extend(schema_errors)

        order_item_fields = body.get('order_item_fields')
        if order_item_fields is not None:
            fields_valid, fields_errors = validate_order_item_fields(order_item_fields)
            if not fields_valid:
                all_field_errors.extend(fields_errors)

        purchase_rules = body.get('purchase_rules')
        if purchase_rules is not None:
            rules_valid, rules_errors = validate_purchase_rules(purchase_rules)
            if not rules_valid:
                all_field_errors.extend(rules_errors)

        # Validate catalog fields (groep, subgroep, images)
        catalog_errors = _validate_catalog_fields(body)
        if catalog_errors:
            all_field_errors.extend(
                [{'field': 'catalog', 'message': e} for e in catalog_errors]
            )

        if all_field_errors:
            return create_error_response(400, 'Validation failed', {'errors': all_field_errors})

        # Generate product ID
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        event_id = body.get('event_id', None)

        # Ensure price is stored as numeric Decimal
        raw_price = body.get('price')
        price = Decimal(str(raw_price)) if raw_price is not None else None

        # Build product record (parent)
        product = {
            'product_id': product_id,
            'event_id': event_id,
            'name': body.get('name'),
            'description': body.get('description', ''),
            'category': body.get('category', ''),
            'is_parent': True,
            'parent_id': None,
            'price': price,
            'active': True,
            'min_per_club': body.get('min_per_club'),
            'max_per_club': body.get('max_per_club'),
            'required_attributes': body.get('required_attributes'),
            'image_url': body.get('image_url'),
            # New unified model fields
            'variant_schema': variant_schema,
            'order_item_fields': order_item_fields,
            'purchase_rules': purchase_rules,
            # Catalog fields
            'groep': body.get('groep'),
            'subgroep': body.get('subgroep'),
            'images': body.get('images'),
            # Metadata
            'created_by': user_email,
            'created_at': now,
            'updated_at': now,
        }

        # Remove None values
        product = {k: v for k, v in product.items() if v is not None}

        # Write product to DynamoDB
        table.put_item(Item=product)

        # Generate variants based on variant_schema or create Default_Variant
        variants_created = []
        sync_result = None
        if variant_schema:
            # Use variant_sync to generate and write variants (top-down sync)
            try:
                parent_price = price if price is not None else Decimal('0')
                sync_result = sync_schema_to_variants(
                    table, product_id, variant_schema, parent_price
                )
            except MaxCombinationsExceeded as e:
                # Product was already written, but variants failed — clean up
                table.delete_item(Key={'product_id': product_id})
                return create_error_response(400, 'Too many variant combinations', {
                    'count': e.count,
                    'max': e.max,
                })
        else:
            # No variant_schema — create Default_Variant
            default_variant = create_default_variant(product_id)
            # Inherit price from parent if set
            if price is not None:
                default_variant['price'] = price
            table.put_item(Item=default_variant)
            variants_created = [default_variant]

        response_data = {
            'product': product,
            'message': 'Product created successfully',
        }
        if sync_result:
            response_data['variant_sync'] = {
                'created': sync_result.created,
                'preserved': sync_result.preserved,
                'deactivated': sync_result.deactivated,
            }
            response_data['variant_count'] = sync_result.created
        else:
            response_data['variants'] = variants_created
            response_data['variant_count'] = len(variants_created)

        return create_success_response(_serialize_response(response_data))

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating product: {str(e)}")
        return create_error_response(500, 'Internal server error')
