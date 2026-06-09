import json
import os
import uuid
import boto3
from datetime import datetime, timezone

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
        generate_variant_combinations,
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


def _batch_write_variants(variants):
    """Write variant records to DynamoDB using batch_writer."""
    with table.batch_writer() as batch:
        for variant in variants:
            batch.put_item(Item=variant)


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
        channel = body.get('channel', body.get('tenant', 'h-dcn'))

        # Build product record (parent)
        product = {
            'product_id': product_id,
            'channel': channel,
            'name': body.get('name'),
            'description': body.get('description', ''),
            'category': body.get('category', ''),
            'is_parent': True,
            'parent_id': None,
            'price': body.get('price'),
            'active': body.get('active', True),
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
        if variant_schema:
            # Generate variants from variant_schema
            variants = generate_variant_combinations(variant_schema, product_id, channel)
            # Inherit price from parent
            if body.get('price') is not None:
                for v in variants:
                    v['price'] = body['price']
            _batch_write_variants(variants)
            variants_created = variants
        else:
            # No variant_schema — create Default_Variant
            default_variant = create_default_variant(product_id, channel)
            # Inherit price from parent if set
            if body.get('price') is not None:
                default_variant['price'] = body['price']
            table.put_item(Item=default_variant)
            variants_created = [default_variant]

        return create_success_response({
            'product': product,
            'variants': variants_created,
            'variant_count': len(variants_created),
            'message': 'Product created successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating product: {str(e)}")
        return create_error_response(500, 'Internal server error')
