"""
Unified create_order handler for H-DCN webshop and PresMeet orders.

POST /orders — Full validation pipeline:
1. Purchase rules enforcement (max_per_order, max_per_member, max_per_club, requires_membership)
2. Item fields validation (required fields, type constraints)
3. Stock availability check (reject if insufficient and allow_oversell=false)

Payment methods:
- "ideal", "creditcard" → Mollie payment, return checkout_url, payment_status="pending"
- "bank_transfer" → order with payment_status="unpaid", return transfer instructions

Persistent order mode (order_mode="persistent"):
- Find existing order for (club_id, product_id), update instead of creating new
- Optimistic locking via version attribute (409 on conflict)

Requirements: 5.7–5.12, 6.6–6.8, 8.4–8.6, 9.1–9.5, 10.1, 10.5–10.7, 12.5–12.13, 16.1–16.7, 17.1–17.5
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
import boto3.dynamodb.conditions
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# Import from shared auth layer
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.i18n.locale_resolver import resolve_request_locale
    from shared.purchase_rules_engine import validate_purchase_rules
    from shared.item_fields_validator import validate_item_fields_data
    from shared.mollie_client import create_payment, MollieError, SUPPORTED_METHODS
    from shared.channel_resolver import resolve_channels
    from shared.club_identity import get_club_id
    print("Using shared auth layer for create_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
memberships_table = dynamodb.Table(os.environ.get('MEMBERSHIPS_TABLE_NAME', 'Memberships'))
carts_table = dynamodb.Table(os.environ.get('CARTS_TABLE_NAME', 'Carts'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

# Mollie configuration
MOLLIE_WEBHOOK_URL = os.environ.get('MOLLIE_WEBHOOK_URL', '')
MOLLIE_REDIRECT_URL = os.environ.get('MOLLIE_REDIRECT_URL', '')


def _build_webhook_url(event):
    """Construct the Mollie webhook URL from the Lambda event's request context.

    This avoids referencing MyApi in the SAM template (which causes circular
    dependency errors) by deriving the URL at runtime from the API Gateway
    request context available in every Lambda invocation.
    """
    request_context = event.get('requestContext', {})
    api_id = request_context.get('apiId', '')
    stage = request_context.get('stage', '')
    region = os.environ.get('AWS_REGION', 'eu-west-1')
    return f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}/mollie-webhook"

# Valid payment methods
VALID_PAYMENT_METHODS = ("ideal", "creditcard", "bank_transfer")

# Bank transfer config
BANK_TRANSFER_IBAN = os.environ.get('BANK_TRANSFER_IBAN', 'NL00BANK0123456789')


def lambda_handler(event, context):
    """Main handler for POST /orders."""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        locale = resolve_request_locale(event)

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: admin OR webshop member (hdcnLeden / Regio_Pressmeet / Regio_All)
        is_admin_authorized, _, _ = validate_permissions_with_regions(
            user_roles, ['products_create'], user_email, None
        )
        has_webshop_access = 'hdcnLeden' in user_roles
        has_presmeet_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All'))

        if not is_admin_authorized and not has_webshop_access and not has_presmeet_access:
            return create_error_response(403, 'Access denied: Requires webshop or PresMeet access', {
                'required_roles': ['hdcnLeden', 'Regio_Pressmeet', 'Regio_All'],
            }, error_key='forbidden', locale=locale)

        log_successful_access(user_email, user_roles, 'create_order')

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        cart_id = body.get('cart_id')
        payment_method = body.get('payment_method')
        items = body.get('items', [])

        # Validate required fields
        if not cart_id:
            return create_error_response(400, 'cart_id is required',
                                         error_key='validation_error', locale=locale)
        if not payment_method:
            return create_error_response(400, 'payment_method is required',
                                         error_key='validation_error', locale=locale)
        if payment_method not in VALID_PAYMENT_METHODS:
            return create_error_response(400, f'Invalid payment_method. Must be one of: {", ".join(VALID_PAYMENT_METHODS)}',
                                         error_key='validation_error', locale=locale)
        if not items:
            return create_error_response(400, 'items array is required and must not be empty',
                                         error_key='validation_error', locale=locale)

        # Validate cart ownership
        cart_data, cart_error = _validate_cart(cart_id, user_email, locale)
        if cart_error:
            return cart_error

        # Resolve member_id
        member_id, member_error = _get_member_id(user_email, locale)
        if member_error:
            return member_error

        # Resolve club_id (for PresMeet orders)
        club_id = cart_data.get('club_id') or get_club_id(user_email)
        channel = cart_data.get('channel', cart_data.get('tenant', 'h-dcn'))

        # Fetch product data for all line items
        products, fetch_error = _fetch_products(items, locale)
        if fetch_error:
            return fetch_error

        # === VALIDATION PIPELINE ===

        # 1. Purchase rules validation
        for idx, item in enumerate(items):
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            product = products.get(product_id, {})
            purchase_rules = product.get('purchase_rules')

            violation = validate_purchase_rules(purchase_rules, {
                'quantity': quantity,
                'product_id': product_id,
                'member_id': member_id,
                'club_id': club_id,
                'orders_table': orders_table,
                'memberships_table': memberships_table,
            })
            if violation:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps(violation, default=_json_serialize),
                }

        # 2. Item fields validation
        for idx, item in enumerate(items):
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            product = products.get(product_id, {})
            order_item_fields = product.get('order_item_fields')

            if order_item_fields:
                item_fields_data = item.get('item_fields_data')
                validation_error = validate_item_fields_data(
                    item_fields_data, order_item_fields, quantity, line_item_index=idx
                )
                if validation_error:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers(),
                        'body': json.dumps(validation_error),
                    }

        # 3. Stock availability validation
        for idx, item in enumerate(items):
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity', 1))

            stock_error = _validate_stock(variant_id, quantity, locale)
            if stock_error:
                return stock_error

        # === ORDER CREATION ===

        # Check for persistent order mode
        persistent_order = None
        is_persistent = False
        for item in items:
            product_id = item.get('product_id')
            product = products.get(product_id, {})
            purchase_rules = product.get('purchase_rules', {}) or {}
            if purchase_rules.get('order_mode') == 'persistent' and club_id:
                is_persistent = True
                persistent_order = _find_persistent_order(club_id, product_id)
                break

        if is_persistent and persistent_order:
            return _update_persistent_order(
                persistent_order, items, products, payment_method,
                member_id, user_email, club_id, channel, body, locale, event
            )

        # Create new order
        return _create_new_order(
            items, products, payment_method, member_id, user_email,
            club_id, channel, cart_id, body, locale, is_persistent, event
        )

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body',
                                     error_key='invalid_input')
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error',
                                     error_key='internal_error')


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_cart(cart_id, user_email, locale):
    """Validate cart exists and belongs to the user. Returns (cart_data, error)."""
    try:
        response = carts_table.get_item(Key={'cart_id': cart_id})
        if 'Item' not in response:
            return None, create_error_response(404, 'Cart not found', {
                'cart_id': cart_id,
            }, error_key='not_found', locale=locale)

        cart = response['Item']
        cart_email = cart.get('user_email', '')
        if cart_email.lower() != user_email.lower():
            logger.warning(f"User {user_email} attempted access to cart {cart_id} owned by {cart_email}")
            return None, create_error_response(403, 'Access denied: cart belongs to another user',
                                               error_key='forbidden', locale=locale)
        return cart, None
    except Exception as e:
        logger.error(f"Error validating cart {cart_id}: {e}")
        return None, create_error_response(500, 'Error validating cart',
                                           error_key='internal_error', locale=locale)


def _get_member_id(user_email, locale):
    """Get member_id from email. Returns (member_id, error)."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='member_id',
        )
        items = response.get('Items', [])
        if not items:
            return None, create_error_response(404, 'Member record not found',
                                               error_key='member_not_found', locale=locale)
        member_id = items[0].get('member_id')
        if not member_id:
            return None, create_error_response(500, 'Member record missing member_id',
                                               error_key='internal_error', locale=locale)
        return member_id, None
    except Exception as e:
        logger.error(f"Error looking up member for {user_email}: {e}")
        return None, create_error_response(500, 'Error looking up member information',
                                           error_key='internal_error', locale=locale)


def _fetch_products(items, locale):
    """Fetch parent product records for all line items. Returns (products_dict, error)."""
    products = {}
    product_ids = {item.get('product_id') for item in items if item.get('product_id')}

    for product_id in product_ids:
        try:
            response = producten_table.get_item(Key={'product_id': product_id})
            if 'Item' not in response:
                return None, create_error_response(404, f'Product not found: {product_id}', {
                    'product_id': product_id,
                }, error_key='not_found', locale=locale)
            products[product_id] = response['Item']
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None, create_error_response(500, 'Error fetching product data',
                                               error_key='internal_error', locale=locale)
    return products, None


def _validate_stock(variant_id, quantity, locale):
    """Validate stock availability for a variant. Returns error response or None."""
    if not variant_id:
        return create_error_response(400, 'variant_id is required for each item',
                                     error_key='validation_error', locale=locale)
    try:
        response = producten_table.get_item(Key={'product_id': variant_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'variant_not_found',
                    'details': {'variant_id': variant_id},
                }),
            }

        variant = response['Item']
        allow_oversell = variant.get('allow_oversell', False)
        stock = int(variant.get('stock', 0))

        if not allow_oversell and stock < quantity:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'insufficient_stock',
                    'details': {
                        'variant_id': variant_id,
                        'available': stock,
                        'requested': quantity,
                    },
                }),
            }
        return None
    except Exception as e:
        logger.error(f"Error checking stock for variant {variant_id}: {e}")
        return create_error_response(500, 'Error checking stock availability',
                                     error_key='internal_error', locale=locale)


# ---------------------------------------------------------------------------
# Order creation
# ---------------------------------------------------------------------------


def _create_new_order(items, products, payment_method, member_id, user_email,
                      club_id, channel, cart_id, body, locale, is_persistent, event=None):
    """Create a new order record and handle payment."""
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Build order items with flattened Item_Fields_Data
    order_items = _build_order_items(items, products)

    # Calculate total
    total_amount = sum(item['line_total'] for item in order_items)

    order = {
        'order_id': order_id,
        'user_email': user_email,
        'member_id': member_id,
        'cart_id': cart_id,
        'channel': channel,
        'source': 'presmeet' if channel == 'presmeet' else 'webshop',
        'status': 'submitted',
        'payment_method': payment_method,
        'items': order_items,
        'total_amount': total_amount,
        'total_paid': Decimal('0'),
        'created_at': now,
        'updated_at': now,
    }

    if club_id:
        order['club_id'] = club_id
    if is_persistent:
        order['version'] = 1

    # Handle payment method
    if payment_method in ('ideal', 'creditcard'):
        return _handle_mollie_payment(order, payment_method, locale, event)
    else:
        return _handle_bank_transfer(order, locale)


def _handle_mollie_payment(order, payment_method, locale, event=None):
    """Create Mollie payment and store order with pending status."""
    order_id = order['order_id']
    total_amount = order['total_amount']

    # Format amount as string with 2 decimal places for Mollie
    amount_str = f"{total_amount:.2f}"
    description = f"Order {order_id}"

    redirect_url = MOLLIE_REDIRECT_URL or f"https://portal.h-dcn.nl/orders/{order_id}/confirmation"
    webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event or {})

    try:
        mollie_result = create_payment(
            amount=amount_str,
            description=description,
            redirect_url=redirect_url,
            webhook_url=webhook_url,
            method=payment_method,
        )
    except MollieError as e:
        logger.error(f"Mollie payment creation failed for order {order_id}: {e.reason}")
        return {
            'statusCode': 502,
            'headers': cors_headers(),
            'body': json.dumps(e.to_error_response()),
        }

    # Store order with pending payment status
    order['payment_status'] = 'pending'
    order['mollie_payment_id'] = mollie_result['mollie_payment_id']

    # Convert Decimals for DynamoDB
    _store_order(order)

    logger.info(f"Order {order_id} created with Mollie payment {mollie_result['mollie_payment_id']}")

    return create_success_response({
        'order_id': order_id,
        'payment_status': 'pending',
        'checkout_url': mollie_result['checkout_url'],
    })


def _handle_bank_transfer(order, locale):
    """Store order with unpaid status and return transfer instructions."""
    order_id = order['order_id']
    total_amount = order['total_amount']

    order['payment_status'] = 'unpaid'

    _store_order(order)

    # Generate transfer reference
    reference = _generate_transfer_reference(order_id)

    logger.info(f"Order {order_id} created with bank_transfer, status=unpaid")

    return create_success_response({
        'order_id': order_id,
        'payment_status': 'unpaid',
        'transfer_instructions': {
            'reference': reference,
            'iban': BANK_TRANSFER_IBAN,
            'amount': float(total_amount),
        },
    })


# ---------------------------------------------------------------------------
# Persistent order logic
# ---------------------------------------------------------------------------


def _find_persistent_order(club_id, product_id):
    """Find an existing persistent order for a club and product."""
    try:
        filter_expr = (
            Attr('club_id').eq(club_id)
            & Attr('status').is_in(['draft', 'submitted'])
        )
        response = orders_table.scan(FilterExpression=filter_expr)
        orders = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = orders_table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            orders.extend(response.get('Items', []))

        # Find order containing the specific product
        for order in orders:
            for item in order.get('items', []):
                if item.get('product_id') == product_id:
                    return order
        return None
    except Exception as e:
        logger.error(f"Error finding persistent order for club {club_id}, product {product_id}: {e}")
        return None


def _update_persistent_order(existing_order, items, products, payment_method,
                             member_id, user_email, club_id, channel, body, locale, event=None):
    """Update an existing persistent order with optimistic locking."""
    order_id = existing_order['order_id']
    current_version = int(existing_order.get('version', 1))
    request_version = body.get('version')

    # If client sends a version, validate it matches current
    if request_version is not None and int(request_version) != current_version:
        return {
            'statusCode': 409,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'version_conflict',
                'details': {
                    'order_id': order_id,
                    'current_version': current_version,
                },
            }),
        }

    now = datetime.now(timezone.utc).isoformat()
    order_items = _build_order_items(items, products)
    total_amount = sum(item['line_total'] for item in order_items)
    new_version = current_version + 1

    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET #items = :items, total_amount = :total, '
                'updated_at = :now, #ver = :new_ver, '
                'payment_method = :pm, member_id = :mid'
            ),
            ConditionExpression=Attr('version').eq(current_version),
            ExpressionAttributeNames={
                '#items': 'items',
                '#ver': 'version',
            },
            ExpressionAttributeValues={
                ':items': order_items,
                ':total': total_amount,
                ':now': now,
                ':new_ver': new_version,
                ':pm': payment_method,
                ':mid': member_id,
            },
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 409,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'version_conflict',
                    'details': {
                        'order_id': order_id,
                        'current_version': current_version,
                    },
                }),
            }
        raise

    logger.info(f"Persistent order {order_id} updated to version {new_version}")

    # Handle payment for the updated order
    if payment_method in ('ideal', 'creditcard'):
        # Calculate difference from what's already paid
        total_paid = Decimal(str(existing_order.get('total_paid', 0)))
        difference = total_amount - total_paid
        if difference > 0:
            amount_str = f"{difference:.2f}"
            redirect_url = MOLLIE_REDIRECT_URL or f"https://portal.h-dcn.nl/orders/{order_id}/confirmation"
            webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event or {})

            try:
                mollie_result = create_payment(
                    amount=amount_str,
                    description=f"Order {order_id} (supplement)",
                    redirect_url=redirect_url,
                    webhook_url=webhook_url,
                    method=payment_method,
                )
                # Update payment info on order
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression='SET mollie_payment_id = :mpid, payment_status = :ps',
                    ExpressionAttributeValues={
                        ':mpid': mollie_result['mollie_payment_id'],
                        ':ps': 'pending',
                    },
                )
                return create_success_response({
                    'order_id': order_id,
                    'payment_status': 'pending',
                    'checkout_url': mollie_result['checkout_url'],
                    'version': new_version,
                })
            except MollieError as e:
                logger.error(f"Mollie payment failed for persistent order {order_id}: {e.reason}")
                return {
                    'statusCode': 502,
                    'headers': cors_headers(),
                    'body': json.dumps(e.to_error_response()),
                }
        else:
            # No additional payment needed (items removed/reduced)
            return create_success_response({
                'order_id': order_id,
                'payment_status': existing_order.get('payment_status', 'unpaid'),
                'version': new_version,
            })
    else:
        # Bank transfer for persistent order
        reference = _generate_transfer_reference(order_id)
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET payment_status = :ps',
            ExpressionAttributeValues={':ps': 'unpaid'},
        )
        return create_success_response({
            'order_id': order_id,
            'payment_status': 'unpaid',
            'version': new_version,
            'transfer_instructions': {
                'reference': reference,
                'iban': BANK_TRANSFER_IBAN,
                'amount': float(total_amount),
            },
        })


# ---------------------------------------------------------------------------
# Item building helpers
# ---------------------------------------------------------------------------


def _build_order_items(items, products):
    """Build order line items with flattened Item_Fields_Data."""
    order_items = []

    for item in items:
        product_id = item.get('product_id')
        variant_id = item.get('variant_id')
        quantity = int(item.get('quantity', 1))
        product = products.get(product_id, {})

        unit_price = Decimal(str(product.get('price', 0)))
        line_total = unit_price * quantity

        order_item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_price': unit_price,
            'line_total': line_total,
        }

        # Include variant_attributes for display
        variant_attrs = item.get('variant_attributes')
        if variant_attrs:
            order_item['variant_attributes'] = variant_attrs

        # Flatten Item_Fields_Data into the format:
        # [{item_index, field_id, field_label, value}]
        item_fields_data = item.get('item_fields_data')
        order_item_fields = product.get('order_item_fields')

        if item_fields_data and order_item_fields:
            flattened = _flatten_item_fields_data(item_fields_data, order_item_fields)
            order_item['item_fields_data'] = flattened

        order_items.append(order_item)

    return order_items


def _flatten_item_fields_data(item_fields_data, order_item_fields):
    """
    Flatten item_fields_data into the storage format:
    [{item_index: 1, field_id: "name", field_label: "Naam", value: "Jan"}, ...]

    item_fields_data is a list (one entry per item unit), each containing field_values.
    order_item_fields is the product's field definitions with id and label.
    """
    flattened = []
    # Build a lookup from field_id to label
    field_labels = {f['id']: f.get('label', f['id']) for f in order_item_fields}

    for item_index, entry in enumerate(item_fields_data, start=1):
        # Support both {"field_values": {...}} and direct dict
        if isinstance(entry, dict) and 'field_values' in entry:
            field_values = entry['field_values']
        else:
            field_values = entry if isinstance(entry, dict) else {}

        for field_def in order_item_fields:
            field_id = field_def['id']
            value = field_values.get(field_id, '')
            flattened.append({
                'item_index': item_index,
                'field_id': field_id,
                'field_label': field_labels.get(field_id, field_id),
                'value': value if value is not None else '',
            })

    return flattened


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _store_order(order):
    """Persist order to DynamoDB, converting floats to Decimal."""
    item = _convert_to_dynamodb(order)
    orders_table.put_item(Item=item)


def _convert_to_dynamodb(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, dict):
        return {k: _convert_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dynamodb(v) for v in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj


def _generate_transfer_reference(order_id):
    """Generate a human-readable transfer reference from order ID."""
    # Use first 8 chars of UUID to create a short reference
    short_id = order_id.replace('-', '')[:8].upper()
    year = datetime.now(timezone.utc).year
    return f"ORD-{year}-{short_id}"


def _json_serialize(obj):
    """Custom JSON serializer for objects not serializable by default json."""
    if isinstance(obj, Decimal):
        # Return int if no decimal places, else float
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
