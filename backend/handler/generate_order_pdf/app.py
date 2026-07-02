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
from shared.i18n.locale_resolver import resolve_member_locale, resolve_request_locale

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ORDERS_TABLE = os.environ.get('ORDERS_TABLE', 'Orders')
MEMBERS_TABLE = os.environ.get('MEMBERS_TABLE_NAME', 'Members')
S3_BUCKET = os.environ.get('S3_BUCKET', 'h-dcn-data-506221081911')
LOGO_S3_KEY = os.environ.get('LOGO_S3_KEY', 'imagesWebsite/hdcnFavico.png')
# Public URL fallback for logo (WeasyPrint can fetch remote images)
LOGO_PUBLIC_URL = 'https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/imagesWebsite/hdcnFavico.png'


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


# Keywords indicating a pickup delivery option (case-insensitive)
_PICKUP_KEYWORDS = ('ophalen', 'afhalen', 'pickup', 'pick-up', 'pick up')


def _is_pickup_delivery(delivery_option: str) -> bool:
    """Determine if a delivery option represents pickup (not shipping).

    Checks if the delivery option name contains pickup-related keywords.
    Returns True for pickup options, False for actual shipping.

    Args:
        delivery_option: The delivery option label/name string.

    Returns:
        True if this is a pickup option, False if it's a shipping option.
    """
    if not delivery_option:
        return False
    option_lower = delivery_option.lower()
    return any(keyword in option_lower for keyword in _PICKUP_KEYWORDS)


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

        /* Header with logo right-aligned */
        .header {
            margin-bottom: 24px;
            position: relative;
        }
        .header-inner {
            display: inline-block;
            vertical-align: middle;
        }
        .logo {
            width: 70px;
            height: 70px;
            position: absolute;
            top: 0;
            right: 0;
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

        /* Order meta info — compact table layout */
        .order-meta {
            margin-bottom: 24px;
            width: 60%;
        }
        .meta-row {
            margin-bottom: 6px;
        }
        .meta-label {
            font-weight: bold;
            display: inline-block;
            width: 130px;
        }
        .meta-value {
            display: inline-block;
        }
        .status-paid {
            color: #22C55E;
            font-weight: bold;
        }
        .status-shipped {
            color: #3B82F6;
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
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 8px;
            color: #374151;
        }
        .address-line {
            margin: 0 0 4px 0;
        }

        /* Products table */
        .products-title {
            font-size: 16px;
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
            margin-bottom: 6px;
        }
        .totals-label {
            display: inline-block;
            width: 180px;
        }
        .totals-value {
            display: inline-block;
            text-align: right;
            width: 100px;
        }
        .totals-separator {
            border: none;
            border-top: 1px solid #E5E7EB;
            margin: 8px 0;
        }
        .totals-final {
            font-size: 16px;
            font-weight: bold;
        }
        .totals-final .totals-value {
            font-size: 16px;
            font-weight: bold;
        }
        .totals-vat {
            font-size: 10px;
            color: #6B7280;
            margin-top: 4px;
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
                      locale: str = 'nl', order_status: str = '') -> str:
    """Build the header section with logo (top-right), title, and order metadata."""
    logo_html = ''
    if logo_data_uri is not None:
        logo_html = f'<img src="{logo_data_uri}" alt="H-DCN Logo" class="logo" />'

    document_title = get_pdf_text('document_title', locale)
    order_number_label = get_pdf_text('order_number', locale)
    order_date_label = get_pdf_text('order_date', locale)
    customer_label = get_pdf_text('customer', locale)
    status_label = get_pdf_text('status', locale)
    status_paid = get_pdf_text('status_paid', locale)

    # Show order status (payment + fulfilment)
    status_display = status_paid
    status_class = 'status-paid'
    if order_status in ('shipped', 'delivered', 'completed'):
        status_display = get_pdf_text(f'status_{order_status}', locale)
        status_class = 'status-shipped'

    return f'''    <div class="header">
        {logo_html}<div class="header-inner">
            <div class="header-title">H-DCN Webshop</div>
            <div class="header-subtitle">{document_title}</div>
        </div>
    </div>

    <div class="order-meta">
        <div class="meta-row">
            <span class="meta-label">{order_number_label}:</span>
            <span class="meta-value">{order_id}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{order_date_label}:</span>
            <span class="meta-value">{formatted_date}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{customer_label}:</span>
            <span class="meta-value">{customer_name}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">{status_label}:</span>
            <span class="meta-value {status_class}">{status_display}</span>
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
        ship_name = ship.get('naam', '') or ship.get('name', '') or _resolve_customer_name(customer_info, locale)
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


def format_variant_attributes(variant_attributes) -> str:
    """Format variant_attributes dict as a readable string for PDF display.

    Args:
        variant_attributes: A dict like {"Maat": "M", "Kleur": "Zwart"} or None.

    Returns:
        Formatted string like "Maat: M, Kleur: Zwart", or '-' if empty/None.
    """
    if not variant_attributes or not isinstance(variant_attributes, dict):
        return '-'
    parts = [f"{key}: {value}" for key, value in variant_attributes.items() if value]
    return ', '.join(parts) if parts else '-'


def build_products_table_html(items: list, delivery_option,
                              delivery_cost: Optional[str],
                              locale: str = 'nl') -> str:
    """Build product table. No separate delivery section (shown in totals only).

    Uses unified field names with backward compatibility:
    - name (fallback: naam)
    - unit_price (fallback: price)
    - variant_attributes (fallback: selectedOption)
    """
    product_label = get_pdf_text('product', locale)
    quantity_label = get_pdf_text('quantity', locale)
    unit_price_label = get_pdf_text('unit_price', locale)
    total_label = get_pdf_text('total', locale)

    # Product rows — unified field names with backward compatibility
    product_rows_html = ''
    for item in items:
        # name with fallback to naam
        item_name = item.get('name') or item.get('naam', '')
        # variant_attributes dict with fallback to selectedOption string
        variant_attrs = item.get('variant_attributes')
        if variant_attrs and isinstance(variant_attrs, dict):
            variant_display = format_variant_attributes(variant_attrs)
        else:
            # Backward compat: fall back to legacy selectedOption
            variant_display = item.get('selectedOption') or '-'
        # unit_price with fallback to price
        unit_price = item.get('unit_price') if item.get('unit_price') is not None else item.get('price', 0)
        quantity = item.get('quantity', 0)
        line_total = float(quantity) * float(unit_price)
        product_rows_html += f'''            <tr>
                <td>{item_name}</td>
                <td>{variant_display}</td>
                <td class="right">{quantity}</td>
                <td class="right">{format_euro(unit_price, locale)}</td>
                <td class="right">{format_euro(line_total, locale)}</td>
            </tr>
'''

    return f'''    <div class="products-title">{get_pdf_text('ordered_products', locale)}</div>
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
                      total_amount: str, items: list, locale: str = 'nl') -> str:
    """Build totals section with subtotal, delivery, total, and VAT line.

    Subtotal is calculated from items if stored value is 0.
    VAT line shows: "BTW (21%) inbegrepen: €X.XX"
    """
    subtotal_label = get_pdf_text('subtotal', locale)
    shipping_label = get_pdf_text('shipping', locale)
    total_paid_label = get_pdf_text('total_paid', locale)

    # Calculate subtotal from items if stored value is 0 or empty
    subtotal_val = 0.0
    try:
        subtotal_val = float(subtotal_amount)
    except (TypeError, ValueError):
        subtotal_val = 0.0

    if subtotal_val == 0.0 and items:
        # Compute from items
        for item in items:
            unit_price = item.get('unit_price') if item.get('unit_price') is not None else item.get('price', 0)
            quantity = item.get('quantity', 0)
            subtotal_val += float(quantity) * float(unit_price)

    # Ensure total_amount is valid
    total_val = 0.0
    try:
        total_val = float(total_amount)
    except (TypeError, ValueError):
        total_val = subtotal_val + float(delivery_cost or 0)

    # Calculate VAT (21% included in total)
    vat_amount = total_val / 121 * 21

    html = f'''    <div class="totals">
        <div class="totals-row">
            <span class="totals-label">{subtotal_label}:</span>
            <span class="totals-value">{format_euro(subtotal_val, locale)}</span>
        </div>
'''
    if delivery_cost:
        try:
            dc_val = float(delivery_cost)
        except (TypeError, ValueError):
            dc_val = 0.0
        if dc_val > 0:
            html += f'''        <div class="totals-row">
            <span class="totals-label">{shipping_label}:</span>
            <span class="totals-value">{format_euro(dc_val, locale)}</span>
        </div>
'''
    html += f'''        <hr class="totals-separator" />
        <div class="totals-row totals-final">
            <span class="totals-label">{total_paid_label}:</span>
            <span class="totals-value">{format_euro(total_val, locale)}</span>
        </div>
        <div class="totals-vat">BTW (21%) inbegrepen: {format_euro(vat_amount, locale)}</div>
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
    # Try multiple date fields (timestamp, created_at, submitted_at)
    timestamp = order.get('timestamp', '') or order.get('submitted_at', '') or order.get('created_at', '')
    formatted_date = format_date_localized(timestamp, locale)
    shipping_address = order.get('shipping_address')
    items = order.get('items', [])
    delivery_option = order.get('delivery_option')
    delivery_cost = order.get('delivery_cost')
    subtotal_amount = order.get('subtotal_amount', '0.00')
    total_amount = order.get('total_amount', '0.00')
    order_status = order.get('status', 'paid')

    # Build customer_info from top-level fields (new format) or legacy customer_info map
    customer_info = order.get('customer_info', {})
    if not customer_info or not customer_info.get('name', ''):
        # Build from top-level order fields (Fase 1 format)
        customer_info = {
            'name': order.get('customer_name', ''),
            'email': order.get('customer_email', order.get('user_email', '')),
            'phone': order.get('customer_phone', ''),
        }
        # Also pull address fields from shipping_address for billing display
        if shipping_address and isinstance(shipping_address, dict):
            customer_info['straat'] = shipping_address.get('straat', '')
            customer_info['postcode'] = shipping_address.get('postcode', '')
            customer_info['woonplaats'] = shipping_address.get('woonplaats', '')

    customer_name = _resolve_customer_name(customer_info, locale)

    # Build HTML sections
    css = build_css()
    document_title = get_pdf_text('document_title', locale)
    header_html = build_header_html(logo_data_uri, order_id, formatted_date,
                                    customer_name, locale, order_status)
    addresses_html = build_addresses_html(customer_info, shipping_address, locale)
    products_html = build_products_table_html(items, delivery_option, delivery_cost, locale)
    totals_html = build_totals_html(subtotal_amount, delivery_cost, total_amount, items, locale)

    # For pickup orders, show delivery option info instead of shipping address
    delivery_opt_raw = order.get('delivery_option', '')
    if isinstance(delivery_opt_raw, dict):
        delivery_opt_name = delivery_opt_raw.get('name', delivery_opt_raw.get('label', ''))
    else:
        delivery_opt_name = str(delivery_opt_raw) if delivery_opt_raw else ''
    if _is_pickup_delivery(delivery_opt_name):
        # Don't show shipping address for pickup orders
        addresses_html = build_addresses_html(customer_info, None, locale)

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


# =============================================================================
# PACKING SLIP RENDERING
# =============================================================================

def build_packing_slip_css() -> str:
    """CSS for packing slip PDF. No prices, prominent address, checkbox column."""
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

        /* Header */
        .header {
            margin-bottom: 24px;
        }
        .header-inner {
            display: inline-block;
            vertical-align: middle;
        }
        .logo {
            width: 60px;
            height: 60px;
            vertical-align: middle;
            margin-right: 16px;
        }
        .header-title {
            font-size: 22px;
            font-weight: bold;
            color: #FF6B35;
            margin: 0 0 4px 0;
        }
        .header-subtitle {
            font-size: 18px;
            font-weight: bold;
            margin: 0;
        }

        /* Order meta */
        .order-meta {
            margin-bottom: 20px;
            font-size: 11px;
        }
        .meta-row {
            margin-bottom: 4px;
        }
        .meta-label {
            font-weight: bold;
        }

        /* Separator */
        .separator {
            border: none;
            border-top: 1px solid #E5E7EB;
            margin: 16px 0;
        }

        /* Address / pickup section */
        .address-block {
            margin-bottom: 20px;
            padding: 12px;
            border: 1px solid #E5E7EB;
            background-color: #F9FAFB;
        }
        .address-title {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .address-line {
            margin: 0 0 3px 0;
            font-size: 13px;
        }
        .club-name {
            font-size: 16px;
            font-weight: bold;
            color: #FF6B35;
            margin-bottom: 4px;
        }

        /* Delivery method */
        .delivery-info {
            margin-bottom: 16px;
            font-size: 11px;
        }
        .delivery-label {
            font-weight: bold;
        }

        /* Products table */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }
        th {
            background-color: #F9FAFB;
            padding: 8px;
            text-align: left;
            border-bottom: 2px solid #E5E7EB;
            font-weight: bold;
            font-size: 11px;
        }
        th.center {
            text-align: center;
            width: 50px;
        }
        th.right {
            text-align: right;
        }
        td {
            padding: 8px;
            border-bottom: 1px solid #E5E7EB;
            font-size: 11px;
        }
        td.center {
            text-align: center;
        }
        td.right {
            text-align: right;
        }

        /* Checkbox column */
        .check-box {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #666;
            vertical-align: middle;
        }
    """


def render_packing_slip_html(order: dict, logo_data_uri: Optional[str] = None,
                             locale: str = 'nl') -> str:
    """Render packing slip HTML for an order.

    Packing slip contains: order number, date, delivery address/pickup location,
    product list (name, variant, quantity) with checkbox column. NO PRICES.
    Event orders show club/member name prominently.

    Args:
        order: Order record dict from DynamoDB.
        logo_data_uri: Base64 data URI for the logo, or None to omit.
        locale: Locale code for translations.

    Returns:
        Complete HTML string ready for WeasyPrint rendering.
    """
    order_id = order.get('order_id', '')
    timestamp = order.get('timestamp', '')
    formatted_date = format_date_localized(timestamp, locale)

    # Determine if this is a pickup or shipping order based on delivery_option
    delivery_option_val = order.get('delivery_option', '')
    if isinstance(delivery_option_val, dict):
        delivery_option_display = delivery_option_val.get('name', delivery_option_val.get('label', ''))
    else:
        delivery_option_display = str(delivery_option_val) if delivery_option_val else ''
    is_pickup = _is_pickup_delivery(delivery_option_display)

    # Resolve customer name
    customer_info = order.get('customer_info', {})
    customer_name = order.get('customer_name', '') or _resolve_customer_name(customer_info, locale)

    # Header
    logo_html = ''
    if logo_data_uri is not None:
        logo_html = f'<img src="{logo_data_uri}" alt="H-DCN Logo" class="logo" />'

    packing_slip_title = get_pdf_text('packing_slip_title', locale)
    order_number_label = get_pdf_text('order_number', locale)
    order_date_label = get_pdf_text('order_date', locale)

    header_html = f'''<div class="header">
    {logo_html}<div class="header-inner">
        <div class="header-title">H-DCN Webshop</div>
        <div class="header-subtitle">{packing_slip_title}</div>
    </div>
</div>
<div class="order-meta">
    <div class="meta-row">
        <span class="meta-label">{order_number_label}:</span> {order_id}
    </div>
    <div class="meta-row">
        <span class="meta-label">{order_date_label}:</span> {formatted_date}
    </div>
</div>'''

    # Address or pickup section
    if is_pickup:
        # Pickup order: show customer/club name prominently + pickup location
        pickup_location = order.get('pickup_location', '') or delivery_option_display
        pickup_label = get_pdf_text('pickup_location', locale)
        recipient_label = get_pdf_text('recipient', locale)
        # Use registry_row_label if available (event orders), else customer_name
        row_label = order.get('registry_row_label', '') or customer_name

        address_html = f'''<div class="address-block">
    <div class="address-title">{pickup_label}</div>
    <div class="club-name">{row_label}</div>
    <p class="address-line">{recipient_label}: {customer_name}</p>
    <p class="address-line">{pickup_location}</p>
</div>'''
    else:
        # Shipping order: show delivery address
        shipping_address = order.get('shipping_address', {}) or {}
        delivery_label = get_pdf_text('delivery_address', locale)
        ship_name = shipping_address.get('naam', '') or customer_name
        ship_straat = shipping_address.get('straat', '')
        ship_postcode = shipping_address.get('postcode', '')
        ship_woonplaats = shipping_address.get('woonplaats', '')
        ship_land = shipping_address.get('land', '')

        address_lines = f'<p class="address-line"><strong>{ship_name}</strong></p>\n'
        if ship_straat:
            address_lines += f'    <p class="address-line">{ship_straat}</p>\n'
        postcode_plaats = f"{ship_postcode} {ship_woonplaats}".strip()
        if postcode_plaats:
            address_lines += f'    <p class="address-line">{postcode_plaats}</p>\n'
        if ship_land and ship_land.lower() not in ('nl', 'nederland', 'netherlands'):
            address_lines += f'    <p class="address-line">{ship_land}</p>\n'

        address_html = f'''<div class="address-block">
    <div class="address-title">{delivery_label}</div>
    {address_lines}</div>'''

    # Delivery method
    delivery_method_label = get_pdf_text('delivery_method', locale)
    delivery_html = ''
    if delivery_option_display:
        delivery_html = f'''<div class="delivery-info">
    <span class="delivery-label">{delivery_method_label}:</span> {delivery_option_display}
</div>'''

    # Products table (no prices)
    items = order.get('items', [])
    product_label = get_pdf_text('product', locale)
    option_label = get_pdf_text('option', locale)
    quantity_label = get_pdf_text('quantity', locale)
    pick_check_label = get_pdf_text('pick_check', locale)

    product_rows = ''
    for item in items:
        item_name = item.get('name') or item.get('naam', '')
        variant_attrs = item.get('variant_attributes')
        if variant_attrs and isinstance(variant_attrs, dict):
            variant_display = format_variant_attributes(variant_attrs)
        else:
            variant_display = item.get('selectedOption') or '-'
        quantity = item.get('quantity', 1)

        product_rows += f'''        <tr>
            <td><span class="check-box"></span></td>
            <td>{item_name}</td>
            <td>{variant_display}</td>
            <td class="right">{quantity}</td>
        </tr>
'''

    products_html = f'''<table>
    <thead>
        <tr>
            <th class="center">{pick_check_label}</th>
            <th>{product_label}</th>
            <th>{option_label}</th>
            <th class="right">{quantity_label}</th>
        </tr>
    </thead>
    <tbody>
{product_rows}    </tbody>
</table>'''

    # Assemble full HTML
    css = build_packing_slip_css()

    return f'''<!DOCTYPE html>
<html lang="{locale}">
<head>
    <meta charset="UTF-8" />
    <title>{packing_slip_title} {order_id}</title>
    <style>{css}
    </style>
</head>
<body>
{header_html}

<hr class="separator" />

{address_html}

{delivery_html}

{products_html}
</body>
</html>'''


# =============================================================================
# SHIPPING LABEL RENDERING
# =============================================================================

def build_shipping_label_css() -> str:
    """CSS for shipping label PDF. Format: 10x15cm (standard shipping label)."""
    return """
        @page { size: 100mm 150mm; margin: 8mm; }
        body {
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #000;
            line-height: 1.4;
            margin: 0;
            padding: 0;
        }

        /* Sender (small, top) */
        .sender {
            font-size: 9px;
            color: #666;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #CCC;
        }

        /* Recipient (large, prominent) */
        .recipient {
            margin-top: 16px;
        }
        .recipient-name {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .recipient-line {
            font-size: 16px;
            margin: 0 0 4px 0;
        }
        .recipient-postcode {
            font-size: 18px;
            font-weight: bold;
            margin: 8px 0 4px 0;
        }
        .recipient-country {
            font-size: 14px;
            font-weight: bold;
            text-transform: uppercase;
            margin-top: 8px;
        }

        /* Order reference */
        .order-ref {
            margin-top: 20px;
            padding-top: 8px;
            border-top: 1px solid #CCC;
            font-size: 11px;
            color: #666;
        }
        .order-ref-label {
            font-weight: bold;
        }
    """


def render_shipping_label_html(order: dict, locale: str = 'nl') -> str:
    """Render shipping label HTML (10x15cm format).

    Shows: recipient name, full address, order number as reference.
    Only for webshop orders (event orders use pickup).

    Args:
        order: Order record dict from DynamoDB.
        locale: Locale code for translations.

    Returns:
        Complete HTML string ready for WeasyPrint rendering.
    """
    order_id = order.get('order_id', '')
    customer_info = order.get('customer_info', {})
    customer_name = order.get('customer_name', '') or _resolve_customer_name(customer_info, locale)
    shipping_address = order.get('shipping_address', {}) or {}

    ship_name = shipping_address.get('naam', '') or customer_name
    ship_straat = shipping_address.get('straat', '')
    ship_postcode = shipping_address.get('postcode', '')
    ship_woonplaats = shipping_address.get('woonplaats', '')
    ship_land = shipping_address.get('land', '')

    shipping_label_title = get_pdf_text('shipping_label_title', locale)
    order_ref_label = get_pdf_text('order_ref', locale)

    # Sender info (H-DCN)
    sender_html = '''<div class="sender">
    H-DCN &mdash; Harley-Davidson Club Nederland
</div>'''

    # Recipient address
    address_lines = ''
    if ship_straat:
        address_lines += f'<p class="recipient-line">{ship_straat}</p>\n'

    postcode_html = ''
    if ship_postcode or ship_woonplaats:
        postcode_plaats = f"{ship_postcode}  {ship_woonplaats}".strip()
        postcode_html = f'<p class="recipient-postcode">{postcode_plaats}</p>\n'

    country_html = ''
    if ship_land and ship_land.lower() not in ('nl', 'nederland', 'netherlands'):
        country_html = f'<p class="recipient-country">{ship_land}</p>\n'

    recipient_html = f'''<div class="recipient">
    <div class="recipient-name">{ship_name}</div>
    {address_lines}    {postcode_html}    {country_html}</div>'''

    # Order reference
    ref_html = f'''<div class="order-ref">
    <span class="order-ref-label">{order_ref_label}:</span> {order_id}
</div>'''

    css = build_shipping_label_css()

    return f'''<!DOCTYPE html>
<html lang="{locale}">
<head>
    <meta charset="UTF-8" />
    <title>{shipping_label_title} {order_id}</title>
    <style>{css}
    </style>
</head>
<body>
{sender_html}

{recipient_html}

{ref_html}
</body>
</html>'''


def lambda_handler(event, context):
    """Lambda handler for generating order PDFs (confirmation, packing slip, shipping label)."""
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
        order_id = path_params.get('id') or path_params.get('order_id', '')

        if not order_id or not order_id.strip():
            return create_error_response(400, 'Invalid order_id format')

        # Determine document type from path
        resource_path = event.get('resource', '') or event.get('path', '')
        doc_type = _resolve_doc_type(resource_path)

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

        # Packing slip and shipping label are admin-only
        if doc_type in ('packing_slip', 'shipping_label') and not has_admin:
            return create_error_response(403, 'Access denied: Admin permissions required')

        # Log successful access
        log_successful_access(user_email, user_roles, 'generate_order_pdf', {'order_id': order_id, 'doc_type': doc_type})

        # Resolve locale based on who is requesting:
        # - Owner (end-user): use member's preferred_language (their language)
        # - Admin: use Accept-Language header (admin's portal language)
        if is_owner:
            member_id = order.get('member_id', '')
            preferred_language = fetch_member_preferred_language(member_id) if member_id else None
            locale = resolve_member_locale(preferred_language)
        else:
            locale = resolve_request_locale(event)

        # Fetch logo from S3 (fallback to public URL if S3 API fails)
        logo_data_uri = fetch_logo_as_data_uri(S3_BUCKET, LOGO_S3_KEY)
        if not logo_data_uri:
            # Fallback: use public HTTPS URL directly (WeasyPrint can fetch it)
            logo_data_uri = LOGO_PUBLIC_URL

        # Render HTML based on document type
        if doc_type == 'packing_slip':
            html = render_packing_slip_html(order, logo_data_uri, locale)
        elif doc_type == 'shipping_label':
            html = render_shipping_label_html(order, locale)
        else:
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
        filename = _build_filename(doc_type, order_id, locale)

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


def _resolve_doc_type(resource_path: str) -> str:
    """Determine document type from API Gateway resource path.

    Returns 'confirmation', 'packing_slip', or 'shipping_label'.
    """
    if 'packing-slip' in resource_path:
        return 'packing_slip'
    elif 'shipping-label' in resource_path:
        return 'shipping_label'
    return 'confirmation'


def _build_filename(doc_type: str, order_id: str, locale: str) -> str:
    """Build a localized filename for the PDF download."""
    if doc_type == 'packing_slip':
        title = get_pdf_text('packing_slip_title', locale).lower().replace(' ', '-')
    elif doc_type == 'shipping_label':
        title = get_pdf_text('shipping_label_title', locale).lower().replace(' ', '-')
    else:
        title = get_pdf_text('document_title', locale).lower().replace(' ', '-')
    return f"{title}-{order_id}.pdf"
