"""
Admin batch PDF download handler for H-DCN.

POST /admin/orders/batch-pdf — Generates a single PDF with multiple documents
(one per page) for the given order IDs and document type.

Supports: packing_slip, shipping_label
Event batch: all packing slips for one event in one PDF.

Requirements: 4.2 (Batch PDF download)
"""

import json
import os
import base64
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from decimal import Decimal
from typing import Optional, List

try:
    import weasyprint
except ImportError:
    weasyprint = None

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
    lambda_handler = create_smart_fallback_handler("admin_batch_pdf")
    import sys
    sys.exit(0)

# Import i18n utilities
from shared.i18n.pdf_translations import (
    get_pdf_text,
    format_date_for_locale,
    format_currency_for_locale,
)
from shared.i18n.locale_resolver import resolve_request_locale

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ORDERS_TABLE = os.environ.get('ORDERS_TABLE', 'Orders')
S3_BUCKET = os.environ.get('S3_BUCKET', 'h-dcn-data-506221081911')
LOGO_S3_KEY = os.environ.get('LOGO_S3_KEY', 'imagesWebsite/hdcnFavico.png')
LOGO_PUBLIC_URL = 'https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png'

MAX_BATCH_SIZE = 50
VALID_DOC_TYPES = ('packing_slip', 'shipping_label')


def fetch_logo_as_data_uri(bucket: str, key: str, timeout: int = 5) -> Optional[str]:
    """Fetch S3 image and return as base64 data URI, or None on failure."""
    try:
        s3_config = Config(
            read_timeout=timeout,
            connect_timeout=timeout,
            retries={'max_attempts': 1}
        )
        s3_client = boto3.client('s3', config=s3_config)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content_type = response['ContentType']
        body_bytes = response['Body'].read()
        encoded_data = base64.b64encode(body_bytes).decode('utf-8')
        return f"data:{content_type};base64,{encoded_data}"
    except Exception as e:
        logger.warning(f"Error fetching logo: {e}")
        return None


def format_euro(value, locale: str = 'nl') -> str:
    """Format a monetary value as EUR currency."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return format_currency_for_locale(amount, locale)


# Keywords indicating a pickup delivery option
_PICKUP_KEYWORDS = ('ophalen', 'afhalen', 'pickup', 'pick-up', 'pick up')


def _is_pickup_delivery(delivery_option: str) -> bool:
    """Check if delivery option is pickup."""
    if not delivery_option:
        return False
    return any(kw in delivery_option.lower() for kw in _PICKUP_KEYWORDS)


def _build_packing_slip_html(order: dict, logo_uri: str, locale: str) -> str:
    """Build packing slip HTML for a single order (page-break ready)."""
    t = lambda key, **kw: get_pdf_text(key, locale, **kw)

    order_id = order.get('order_id', '')
    order_number = order.get('order_number', order_id[:12])
    customer_name = order.get('customer_name', order.get('user_email', ''))
    delivery_option = order.get('delivery_option', '')
    is_pickup = _is_pickup_delivery(delivery_option)

    # Address section
    if is_pickup:
        pickup_location = order.get('pickup_location', delivery_option)
        address_html = f"""
        <div class="address-block">
            <strong>{t('pickup_location')}:</strong><br>
            {pickup_location}<br>
            <strong>{customer_name}</strong>
        </div>
        """
    else:
        addr = order.get('shipping_address') or {}
        address_html = f"""
        <div class="address-block">
            <strong>{addr.get('naam', customer_name)}</strong><br>
            {addr.get('straat', '')}<br>
            {addr.get('postcode', '')} {addr.get('woonplaats', '')}<br>
            {addr.get('land', 'Nederland')}
        </div>
        """

    # Items table
    items = order.get('items', [])
    rows = ''
    for item in items:
        name = item.get('name', item.get('product_id', ''))
        variant_attrs = item.get('variant_attributes', {})
        variant_str = ', '.join(f"{v}" for v in variant_attrs.values()) if variant_attrs else ''
        qty = item.get('quantity', 1)
        rows += f"""
        <tr>
            <td class="check-cell">☐</td>
            <td>{name}</td>
            <td>{variant_str}</td>
            <td class="qty-cell">{qty}</td>
        </tr>
        """

    return f"""
    <div class="page">
        <div class="header">
            <img src="{logo_uri}" class="logo" alt="H-DCN" />
            <div>
                <h2>{t('packing_slip')}</h2>
                <p>{t('order_number')}: <strong>{order_number}</strong></p>
            </div>
        </div>
        {address_html}
        <table class="items-table">
            <thead>
                <tr>
                    <th class="check-cell">✓</th>
                    <th>{t('product')}</th>
                    <th>{t('variant')}</th>
                    <th class="qty-cell">{t('quantity')}</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <div class="delivery-info">
            <strong>{t('delivery_option')}:</strong> {delivery_option}
        </div>
    </div>
    """


def _build_shipping_label_html(order: dict, locale: str) -> str:
    """Build shipping label HTML for a single order (page-break ready)."""
    t = lambda key, **kw: get_pdf_text(key, locale, **kw)

    order_id = order.get('order_id', '')
    order_number = order.get('order_number', order_id[:12])
    customer_name = order.get('customer_name', order.get('user_email', ''))
    addr = order.get('shipping_address') or {}

    naam = addr.get('naam', customer_name)
    straat = addr.get('straat', '')
    postcode = addr.get('postcode', '')
    woonplaats = addr.get('woonplaats', '')
    land = addr.get('land', 'Nederland')

    return f"""
    <div class="label-page">
        <div class="label-content">
            <p class="label-name">{naam}</p>
            <p class="label-address">{straat}</p>
            <p class="label-address">{postcode} {woonplaats}</p>
            <p class="label-address">{land}</p>
            <p class="label-ref">{t('order_number')}: {order_number}</p>
        </div>
    </div>
    """


def _build_batch_css(doc_type: str) -> str:
    """Build CSS for batch document with page breaks between orders."""
    if doc_type == 'shipping_label':
        return """
            @page { size: 100mm 150mm; margin: 5mm; }
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .label-page { page-break-after: always; height: 140mm; display: flex; align-items: center; justify-content: center; }
            .label-page:last-child { page-break-after: avoid; }
            .label-content { text-align: center; }
            .label-name { font-size: 18px; font-weight: bold; margin-bottom: 8px; }
            .label-address { font-size: 16px; margin: 4px 0; }
            .label-ref { font-size: 12px; color: #666; margin-top: 16px; }
        """
    else:
        # Packing slip
        return """
            @page { size: A4; margin: 15mm; }
            body { font-family: Arial, sans-serif; font-size: 12px; color: #000; margin: 0; padding: 0; }
            .page { page-break-after: always; }
            .page:last-child { page-break-after: avoid; }
            .header { position: relative; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #FF6B35; }
            .header h2 { margin: 0; color: #FF6B35; }
            .header p { margin: 4px 0 0 0; }
            .logo { width: 50px; height: 50px; position: absolute; top: 0; right: 0; }
            .address-block { margin: 12px 0; padding: 8px; background: #f9f9f9; border: 1px solid #eee; }
            .items-table { width: 100%; border-collapse: collapse; margin: 12px 0; }
            .items-table th, .items-table td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
            .items-table th { background: #f5f5f5; font-weight: bold; }
            .check-cell { width: 30px; text-align: center; }
            .qty-cell { width: 50px; text-align: center; }
            .delivery-info { margin-top: 12px; font-size: 11px; color: #666; }
        """


def lambda_handler(event, context):
    """Main handler for POST /admin/orders/batch-pdf."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - admin only
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_batch_pdf')

        # Parse request body
        body = json.loads(event.get('body') or '{}')
        order_ids: List[str] = body.get('order_ids', [])
        document_type: str = body.get('document_type', '')

        # Validate input
        if not order_ids:
            return create_error_response(400, 'order_ids is required and must be non-empty')
        if document_type not in VALID_DOC_TYPES:
            return create_error_response(
                400, f'document_type must be one of: {", ".join(VALID_DOC_TYPES)}'
            )
        if not isinstance(order_ids, list):
            return create_error_response(400, 'order_ids must be an array')
        if len(order_ids) > MAX_BATCH_SIZE:
            return create_error_response(400, f'Maximum batch size is {MAX_BATCH_SIZE} orders')

        # Resolve locale from request
        locale = resolve_request_locale(event)

        # Fetch all orders
        dynamodb_resource = boto3.resource('dynamodb')
        table = dynamodb_resource.Table(ORDERS_TABLE)

        orders = []
        not_found = []
        for order_id in order_ids:
            response = table.get_item(Key={'order_id': order_id})
            if 'Item' in response:
                orders.append(response['Item'])
            else:
                not_found.append(order_id)

        if not orders:
            return create_error_response(404, 'No orders found for the given IDs')

        # Fetch logo for packing slips
        logo_uri = LOGO_PUBLIC_URL
        if document_type == 'packing_slip':
            fetched_logo = fetch_logo_as_data_uri(S3_BUCKET, LOGO_S3_KEY)
            if fetched_logo:
                logo_uri = fetched_logo

        # Build combined HTML document
        css = _build_batch_css(document_type)
        pages_html = ''

        for order in orders:
            if document_type == 'packing_slip':
                pages_html += _build_packing_slip_html(order, logo_uri, locale)
            else:
                pages_html += _build_shipping_label_html(order, locale)

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><style>{css}</style></head>
        <body>{pages_html}</body>
        </html>
        """

        # Generate PDF with WeasyPrint
        if weasyprint is None:
            return create_error_response(500, 'PDF rendering not available')

        try:
            pdf_bytes = weasyprint.HTML(string=full_html).write_pdf()
        except Exception as e:
            logger.error(f"WeasyPrint batch rendering error: {type(e).__name__} - {str(e)}")
            return create_error_response(500, 'PDF rendering failed')

        # Base64-encode for API Gateway binary response
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        # Build filename
        doc_label = 'pakbonnen' if document_type == 'packing_slip' else 'verzendlabels'
        filename = f"batch-{doc_label}-{len(orders)}.pdf"

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="{filename}"',
                **cors_headers()
            },
            "body": base64_pdf,
            "isBase64Encoded": True
        }

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Unexpected error in batch PDF: {type(e).__name__} - {str(e)}")
        return create_error_response(500, 'Internal server error')
