import json
import os
import base64
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional
from datetime import datetime

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
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("generate_order_pdf")
    import sys
    sys.exit(0)

# Import i18n utilities for PDF localization
from shared.i18n.pdf_translations import (
    get_pdf_text,
    format_date_for_locale,
    format_currency_for_locale,
)
from shared.i18n.locale_resolver import resolve_member_locale

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ORDERS_TABLE = os.environ.get('ORDERS_TABLE', 'Orders')
MEMBERS_TABLE = os.environ.get('MEMBERS_TABLE_NAME', 'Members')
S3_BUCKET = os.environ.get('S3_BUCKET', 'my-hdcn-bucket')
LOGO_S3_KEY = os.environ.get('LOGO_S3_KEY', 'imagesWebsite/hdcnFavico.png')


def fetch_logo_as_data_uri(bucket: str, key: str, timeout: int = 5) -> Optional[str]:
    """Fetch S3 image and return as base64 data URI, or None on failure.

    Uses boto3 get_object to fetch the image from S3, reads the ContentType
    from the response metadata, base64-encodes the body, and constructs a
    data URI in the format: data:{content_type};base64,{encoded_data}

    Args:
        bucket: S3 bucket name (e.g. 'my-hdcn-bucket')
        key: S3 object key (e.g. 'imagesWebsite/hdcnFavico.png')
        timeout: Read and connect timeout in seconds (default 5)

    Returns:
        A data URI string if successful, or None on any failure.
    """
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
        data_uri = f"data:{content_type};base64,{encoded_data}"

        return data_uri

    except ClientError as e:
        logger.warning(
            f"S3 ClientError fetching logo s3://{bucket}/{key}: "
            f"{e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        return None
    except BotoCoreError as e:
        logger.warning(
            f"S3 BotoCoreError fetching logo s3://{bucket}/{key}: {str(e)}"
        )
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error fetching logo s3://{bucket}/{key}: {type(e).__name__} - {str(e)}"
        )
        return None


def format_euro(value, locale: str = 'nl') -> str:
    """Format a monetary value using locale-aware currency formatting.

    Args:
        value: A numeric value (int, float) or string representation of a number.
        locale: The locale code for formatting (default: 'nl').

    Returns:
        Locale-formatted EUR currency string.
    """
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return format_currency_for_locale(amount, locale)


def format_date_localized(iso_timestamp: str, locale: str = 'nl') -> str:
    """Format an ISO 8601 timestamp using locale-aware date formatting.

    Args:
        iso_timestamp: ISO 8601 date string (e.g. "2025-01-15T14:30:00Z")
        locale: The locale code for formatting (default: 'nl').

    Returns:
        Locale-formatted date string with time (e.g., "15 januari 2025, 14:30").
    """
    try:
        # Handle both 'Z' suffix and '+00:00' timezone formats
        ts = iso_timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
        # Use locale-aware date formatting for the date part
        date_str = format_date_for_locale(dt, locale)
        # Append time
        hours = dt.hour
        minutes = dt.minute
        return f"{date_str}, {hours:02d}:{minutes:02d}"
    except (ValueError, TypeError, IndexError, AttributeError):
        return iso_timestamp or ""


def build_css() -> str:
    """Build CSS styling that matches the frontend OrderConfirmation layout.

    Uses inline-block for two-column layouts (WeasyPrint-compatible, no flexbox).
    Orange branding (#FF6B35) for H-DCN title, light grey table headers (#F9FAFB).
    """
    return """
        @page { size: A4; margin: 20mm; }
        body {
            font-family: Arial, sans-serif;
            font-size: 12px;
            color: #000;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }

        /* Header with logo and title */
        .header {
            margin-bottom: 24px;
        }
        .header-inner {
            display: inline-block;
            vertical-align: middle;
        }
        .logo {
            width: 80px;
            height: 80px;
            vertical-align: middle;
            margin-right: 20px;
        }
        .header-title {
            font-size: 24px;
            font-weight: bold;
            color: #FF6B35;
            margin: 0 0 8px 0;
        }
        .header-subtitle {
            font-size: 20px;
            font-weight: bold;
            margin: 0;
        }

        /* Order meta info */
        .order-meta {
            margin-bottom: 24px;
        }
        .meta-row {
            margin-bottom: 8px;
        }
        .meta-label {
            font-weight: bold;
        }
        .status-paid {
            color: #22C55E;
            font-weight: bold;
        }

        /* Separator lines */
        .separator {
            border: none;
            border-top: 1px solid #E5E7EB;
            margin: 24px 0;
        }

        /* Two-column address layout */
        .addresses {
            margin-bottom: 24px;
        }
        .address-col {
            display: inline-block;
            width: 48%;
            vertical-align: top;
        }
        .address-col-spacer {
            display: inline-block;
            width: 3%;
        }
        .address-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .address-line {
            margin: 0 0 4px 0;
        }

        /* Delivery section */
        .delivery {
            margin-bottom: 24px;
        }
        .delivery-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .delivery-row {
            margin-bottom: 8px;
        }
        .delivery-label {
            display: inline-block;
        }
        .delivery-cost {
            float: right;
        }

        /* Products table */
        .products-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
        }
        th {
            background-color: #F9FAFB;
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #E5E7EB;
            font-weight: bold;
        }
        th.right {
            text-align: right;
        }
        td {
            padding: 8px;
            border-bottom: 1px solid #E5E7EB;
        }
        td.right {
            text-align: right;
        }

        /* Totals section */
        .totals {
            margin-bottom: 24px;
        }
        .totals-row {
            margin-bottom: 8px;
        }
        .totals-label {
            display: inline-block;
        }
        .totals-value {
            float: right;
        }
        .totals-separator {
            border: none;
            border-top: 1px solid #E5E7EB;
            margin: 8px 0;
        }
        .totals-final {
            font-size: 18px;
            font-weight: bold;
        }
        .totals-final .totals-value {
            font-size: 18px;
            font-weight: bold;
        }
    """


def _resolve_customer_name(customer_info: dict, locale: str = 'nl') -> str:
    """Resolve customer name with fallback logic.

    Priority: name > voornaam+achternaam > localized 'no data' text
    """
    name = customer_info.get('name', '')
    if name:
        return name
    voornaam = customer_info.get('voornaam', '')
    achternaam = customer_info.get('achternaam', '')
    combined = f"{voornaam} {achternaam}".strip()
    if combined:
        return combined
    return get_pdf_text('no_data', locale)


def fetch_member_preferred_language(member_id: str) -> str | None:
    """Fetch a member's preferred_language from the Members table.

    Args:
        member_id: The member's unique identifier.

    Returns:
        The preferred_language value, or None if not found/error.
    """
    if not member_id:
        return None

    try:
        dynamodb = boto3.resource('dynamodb')
        members_table = dynamodb.Table(MEMBERS_TABLE)
        response = members_table.get_item(
            Key={'member_id': member_id},
            ProjectionExpression='preferred_language'
        )
        item = response.get('Item')
        if item:
            return item.get('preferred_language')
        return None
    except Exception as e:
        logger.warning(f"Error fetching member preferred_language for {member_id}: {str(e)}")
        return None


def build_header_html(logo_data_uri: Optional[str], order_id: str,
                      formatted_date: str, customer_name: str,
                      locale: str = 'nl') -> str:
    """Build the header section with logo, title, and order metadata.

    Matches the frontend layout: logo left, title "H-DCN Webshop" in orange,
    subtitle (localized document title), then order meta block below.
    """
    logo_html = ''
    if logo_data_uri is not None:
        logo_html = f'<img src="{logo_data_uri}" alt="H-DCN Logo" class="logo" />'

    document_title = get_pdf_text('document_title', locale)
    order_number_label = get_pdf_text('order_number', locale)
    order_date_label = get_pdf_text('order_date', locale)
    customer_label = get_pdf_text('customer', locale)
    status_label = get_pdf_text('status', locale)
    status_paid = get_pdf_text('status_paid', locale)

    return f'''    <div class="header">
        {logo_html}<div class="header-inner">
            <div class="header-title">H-DCN Webshop</div>
            <div class="header-subtitle">{document_title}</div>
        </div>
    </div>

    <div class="order-meta">
        <div class="meta-row">
            <span class="meta-label">{order_number_label}:</span>
            <span style="float: right;">{order_id}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{order_date_label}:</span>
            <span style="float: right;">{formatted_date}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{customer_label}:</span>
            <span style="float: right;">{customer_name}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{status_label}:</span>
            <span class="status-paid" style="float: right;">{status_paid}</span>
        </div>
    </div>'''


def build_addresses_html(customer_info: dict, shipping_address: Optional[dict],
                         locale: str = 'nl') -> str:
    """Build two-column address layout with billing and shipping addresses.

    Uses inline-block for WeasyPrint compatibility (no flexbox).
    Falls back to customer_info for shipping address if not provided.
    """
    billing_address_label = get_pdf_text('billing_address', locale)
    delivery_address_label = get_pdf_text('delivery_address', locale)
    no_data_text = get_pdf_text('no_data', locale)

    # Billing address
    billing_name = _resolve_customer_name(customer_info, locale)
    billing_straat = customer_info.get('straat', '')
    billing_postcode = customer_info.get('postcode', '')
    billing_woonplaats = customer_info.get('woonplaats', '')
    billing_email = customer_info.get('email', '')
    billing_phone = customer_info.get('phone', '')

    billing_lines = f'<p class="address-line">{billing_name}</p>\n'
    if billing_straat:
        billing_lines += f'        <p class="address-line">{billing_straat}</p>\n'
    postcode_plaats = f"{billing_postcode} {billing_woonplaats}".strip()
    if postcode_plaats:
        billing_lines += f'        <p class="address-line">{postcode_plaats}</p>\n'
    if billing_email:
        billing_lines += f'        <p class="address-line">{billing_email}</p>\n'
    if billing_phone:
        billing_lines += f'        <p class="address-line">{billing_phone}</p>\n'

    if not customer_info:
        billing_lines = f'<p class="address-line">{no_data_text}</p>\n'

    # Shipping address - fallback to customer_info
    ship = shipping_address if shipping_address else customer_info
    if ship:
        ship_name = ship.get('name', '') or _resolve_customer_name(ship, locale)
        ship_straat = ship.get('straat', '')
        ship_postcode = ship.get('postcode', '')
        ship_woonplaats = ship.get('woonplaats', '')

        shipping_lines = f'<p class="address-line">{ship_name}</p>\n'
        if ship_straat:
            shipping_lines += f'        <p class="address-line">{ship_straat}</p>\n'
        ship_postcode_plaats = f"{ship_postcode} {ship_woonplaats}".strip()
        if ship_postcode_plaats:
            shipping_lines += f'        <p class="address-line">{ship_postcode_plaats}</p>\n'
    else:
        shipping_lines = f'<p class="address-line">{no_data_text}</p>\n'

    return f'''    <hr class="separator" />

    <div class="addresses">
        <div class="address-col">
            <div class="address-title">{billing_address_label}</div>
            {billing_lines.strip()}
        </div><div class="address-col-spacer"></div><div class="address-col">
            <div class="address-title">{delivery_address_label}</div>
            {shipping_lines.strip()}
        </div>
    </div>

    <hr class="separator" />'''


def build_products_table_html(items: list, delivery_option: Optional[dict],
                              delivery_cost: Optional[str],
                              locale: str = 'nl') -> str:
    """Build product table with optional delivery section above it.

    Table has light grey header (#F9FAFB), right-aligned numeric columns.
    Delivery section appears ABOVE the products table when present.
    """
    shipping_label = get_pdf_text('shipping', locale)
    product_label = get_pdf_text('product', locale)
    quantity_label = get_pdf_text('quantity', locale)
    unit_price_label = get_pdf_text('unit_price', locale)
    total_label = get_pdf_text('total', locale)

    # Delivery section (above the table)
    delivery_html = ''
    if delivery_option:
        delivery_label = delivery_option.get('label', shipping_label)
        delivery_cost_val = delivery_cost if delivery_cost else '0.00'
        delivery_html = f'''    <div class="delivery">
        <div class="delivery-title">{shipping_label}</div>
        <div class="delivery-row">
            <span class="delivery-label">{delivery_label}</span>
            <span class="delivery-cost">{format_euro(delivery_cost_val, locale)}</span>
        </div>
    </div>

    <hr class="separator" />

'''

    # Product rows
    product_rows_html = ''
    for item in items:
        item_name = item.get('name') or item.get('naam', '')
        selected_option = item.get('selectedOption') or '-'
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        line_total = float(quantity) * float(price)
        product_rows_html += f'''            <tr>
                <td>{item_name}</td>
                <td>{selected_option}</td>
                <td class="right">{quantity}</td>
                <td class="right">{format_euro(price, locale)}</td>
                <td class="right">{format_euro(line_total, locale)}</td>
            </tr>
'''

    return f'''{delivery_html}    <div class="products-title">{get_pdf_text('ordered_products', locale)}</div>
    <table>
        <thead>
            <tr>
                <th>{product_label}</th>
                <th>{get_pdf_text('option', locale)}</th>
                <th class="right">{quantity_label}</th>
                <th class="right">{unit_price_label}</th>
                <th class="right">{total_label}</th>
            </tr>
        </thead>
        <tbody>
{product_rows_html}        </tbody>
    </table>'''


def build_totals_html(subtotal_amount: str, delivery_cost: Optional[str],
                      total_amount: str, locale: str = 'nl') -> str:
    """Build totals section with subtotal, optional shipping, and bold final total.

    Final total displayed as localized "Total paid:" in 18px bold, matching the frontend.
    """
    subtotal_label = get_pdf_text('subtotal', locale)
    shipping_label = get_pdf_text('shipping', locale)
    total_paid_label = get_pdf_text('total_paid', locale)

    html = f'''    <div class="totals">
        <div class="totals-row">
            <span class="totals-label">{subtotal_label}:</span>
            <span class="totals-value">{format_euro(subtotal_amount, locale)}</span>
        </div>
'''
    if delivery_cost:
        html += f'''        <div class="totals-row">
            <span class="totals-label">{shipping_label}:</span>
            <span class="totals-value">{format_euro(delivery_cost, locale)}</span>
        </div>
'''
    html += f'''        <hr class="totals-separator" />
        <div class="totals-row totals-final">
            <span class="totals-label">{total_paid_label}:</span>
            <span class="totals-value">{format_euro(total_amount, locale)}</span>
        </div>
    </div>'''

    return html


def render_order_html(order: dict, logo_data_uri: Optional[str] = None,
                      locale: str = 'nl') -> str:
    """Render order data into an HTML string matching the frontend layout.

    Builds a complete HTML document with A4-appropriate CSS styling,
    using orange branding (#FF6B35), two-column address layout,
    light grey table headers, and WeasyPrint-compatible CSS.

    Args:
        order: Order record dict from DynamoDB.
        logo_data_uri: Base64 data URI for the logo image, or None to omit.
        locale: Locale code for translations and formatting (default: 'nl').

    Returns:
        Complete HTML string ready for WeasyPrint rendering.
    """
    # Extract data from order
    order_id = order.get('order_id', '')
    timestamp = order.get('timestamp', '')
    formatted_date = format_date_localized(timestamp, locale)
    customer_info = order.get('customer_info', {})
    shipping_address = order.get('shipping_address')
    items = order.get('items', [])
    delivery_option = order.get('delivery_option')
    delivery_cost = order.get('delivery_cost')
    subtotal_amount = order.get('subtotal_amount', '0.00')
    total_amount = order.get('total_amount', '0.00')

    customer_name = _resolve_customer_name(customer_info, locale)

    # Build HTML sections
    css = build_css()
    document_title = get_pdf_text('document_title', locale)
    header_html = build_header_html(logo_data_uri, order_id, formatted_date,
                                    customer_name, locale)
    addresses_html = build_addresses_html(customer_info, shipping_address, locale)
    products_html = build_products_table_html(items, delivery_option, delivery_cost, locale)
    totals_html = build_totals_html(subtotal_amount, delivery_cost, total_amount, locale)

    html = f'''<!DOCTYPE html>
<html lang="{locale}">
<head>
    <meta charset="UTF-8" />
    <title>{document_title} {order_id}</title>
    <style>{css}
    </style>
</head>
<body>
{header_html}

{addresses_html}

{products_html}

{totals_html}
</body>
</html>'''

    return html


def lambda_handler(event, context):
    """Lambda handler for generating order confirmation PDFs."""
    try:
        # Handle OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials via shared auth layer
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Extract and validate order_id from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('order_id', '')

        if not order_id or not order_id.strip():
            return create_error_response(400, 'Invalid order_id format')

        # Fetch order from DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(ORDERS_TABLE)

        response = table.get_item(Key={'order_id': order_id})
        order = response.get('Item')

        if not order:
            return create_error_response(404, 'Order not found')

        # Validate ownership or admin permissions
        order_email = order.get('user_email', '')
        is_owner = user_email.lower() == order_email.lower() if user_email and order_email else False

        # Check if user has admin permission (products_create via Products_CRUD, Webshop_Management, or System_CRUD)
        admin_roles = ['Products_CRUD', 'Webshop_Management', 'System_CRUD']
        has_admin = any(role in user_roles for role in admin_roles)

        if not is_owner and not has_admin:
            return create_error_response(403, 'Access denied: You can only access your own orders')

        # Log successful access
        log_successful_access(user_email, user_roles, 'generate_order_pdf', {'order_id': order_id})

        # Resolve locale from member's preferred_language
        member_id = order.get('member_id', '')
        preferred_language = fetch_member_preferred_language(member_id) if member_id else None
        locale = resolve_member_locale(preferred_language)

        # Fetch logo from S3 (graceful degradation: PDF still generated if logo fails)
        logo_data_uri = fetch_logo_as_data_uri(S3_BUCKET, LOGO_S3_KEY)

        # Render HTML template with order data, logo, and locale
        html = render_order_html(order, logo_data_uri, locale)

        # Generate PDF with WeasyPrint
        try:
            if weasyprint is None:
                raise ImportError("weasyprint is not installed")
            pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        except Exception as e:
            logger.error(f"WeasyPrint rendering error for order {order_id}: {type(e).__name__} - {str(e)}")
            return create_error_response(500, 'PDF rendering failed')

        # Base64-encode PDF bytes for API Gateway binary response
        base64_encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        # Use localized filename
        document_title = get_pdf_text('document_title', locale).lower().replace(' ', '-')
        filename = f"{document_title}-{order_id}.pdf"

        # Return PDF response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="{filename}"',
                **cors_headers()
            },
            "body": base64_encoded_pdf,
            "isBase64Encoded": True
        }

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return create_error_response(500, 'Internal server error')
    except Exception as e:
        logger.error(f"Unexpected error in generate_order_pdf: {type(e).__name__} - {str(e)}")
        return create_error_response(500, 'Internal server error')
