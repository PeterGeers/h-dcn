"""
Admin Preparation PDF handler.

GET /admin/events/{event_id}/preparation-pdf

Query params:
  mode       = by_order | by_guest (required)
  product_filter = product_id (optional)

Generates a PDF for event preparation:
  - by_order: one page per registry row/order, sorted alphabetically by row label
  - by_guest: one page per person, sorted by last word of guest name

Only includes submitted and locked orders.

Auth: admin roles (Products_CRUD, Regio_All, System_CRUD, Events_CRUD).

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8
"""

import json
import os
import base64
import logging
from datetime import date
from decimal import Decimal
from typing import TypedDict, NotRequired

import boto3
from boto3.dynamodb.conditions import Attr

try:
    import weasyprint
except ImportError:
    weasyprint = None

# Import shared authentication utilities with fallback support
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
    print("Using shared auth layer for generate_preparation_pdf")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("generate_preparation_pdf")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
products_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# S3 client for registry file and logos
s3 = boto3.client('s3', region_name='eu-west-1')
REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')

# Admin roles that grant access
ADMIN_ROLES = {'Products_CRUD', 'Regio_All', 'System_CRUD', 'Events_CRUD'}


# --- Helpers ---

def _has_admin_access(user_roles: list[str]) -> bool:
    """Check if user has any admin role that grants PDF access."""
    return bool(set(user_roles) & ADMIN_ROLES)


def _scan_qualifying_orders(event_id: str) -> list[dict]:
    """Scan orders for event_id with status submitted or locked."""
    filter_expr = (
        Attr('event_id').eq(event_id)
        & (Attr('status').eq('submitted') | Attr('status').eq('locked'))
    )

    response = orders_table.scan(FilterExpression=filter_expr)
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = orders_table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return items


def _fetch_registry_rows(s3_path: str) -> dict[str, dict]:
    """Fetch the invitee registry from S3 and return rows keyed by row_id."""
    try:
        response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
        registry_data = json.loads(response['Body'].read().decode('utf-8'))
        rows = registry_data.get('rows', [])
        return {row['row_id']: row for row in rows if 'row_id' in row}
    except Exception as e:
        logger.error(f"Error fetching registry from S3: {e}")
        return {}


def _fetch_products_map(event_id: str) -> dict[str, dict]:
    """Fetch all products linked to the event, keyed by product_id."""
    filter_expr = Attr('event_id').eq(event_id)

    response = products_table.scan(
        FilterExpression=filter_expr,
        ProjectionExpression='product_id, #n, variant_schema',
        ExpressionAttributeNames={'#n': 'name'},
    )
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = products_table.scan(
            FilterExpression=filter_expr,
            ProjectionExpression='product_id, #n, variant_schema',
            ExpressionAttributeNames={'#n': 'name'},
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return {item['product_id']: item for item in items}


def _get_last_word(name: str) -> str:
    """Extract the last word from a name for sorting purposes."""
    parts = name.strip().split()
    return parts[-1] if parts else ''


def _sort_key_row_label(name: str) -> str:
    """Sort key for by_order mode: case-insensitive row label."""
    return name.lower() if name else ''


def _sort_key_guest_name(name: str) -> tuple[str, str]:
    """Sort key for by_guest mode: last word first, then rest of name."""
    last = _get_last_word(name).lower()
    # Secondary sort: everything except the last word (first name)
    parts = name.strip().split()
    first = ' '.join(parts[:-1]).lower() if len(parts) > 1 else ''
    return (last, first)


def _to_float(value) -> float:
    """Safely convert a DynamoDB Decimal or string to float."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _format_euro(value) -> str:
    """Format a monetary value as EUR."""
    amount = _to_float(value)
    return f"€{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _get_variant_display(item: dict, products_map: dict[str, dict]) -> str:
    """Get a display string for variant info on an item."""
    variant_attrs = item.get('variant_attributes')
    if variant_attrs and isinstance(variant_attrs, dict):
        parts = [f"{k}: {v}" for k, v in variant_attrs.items() if v]
        if parts:
            return ', '.join(parts)
    # Fallback to variant_id
    variant_id = item.get('variant_id')
    if variant_id:
        return str(variant_id)
    return ''


def _get_item_fields_display(item: dict) -> str:
    """Get display string for extra item fields (excluding name)."""
    fields = item.get('item_fields_data', {})
    if not fields or not isinstance(fields, dict):
        return ''
    parts = []
    for key, value in fields.items():
        if key == 'name':
            continue
        if value:
            parts.append(f"{key}: {value}")
    return ', '.join(parts)


# --- PDF rendering ---

def _build_css() -> str:
    """CSS styling for the preparation PDF."""
    return """
        @page {
            size: A4;
            margin: 15mm 20mm 25mm 20mm;
            @bottom-center {
                content: none;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 11px;
            color: #222;
            line-height: 1.4;
            margin: 0;
            padding: 0;
        }
        .page {
            page-break-after: always;
        }
        .page:last-child {
            page-break-after: avoid;
        }

        /* Header per page */
        .page-header {
            margin-bottom: 16px;
            border-bottom: 2px solid #FF6B35;
            padding-bottom: 12px;
        }
        .row-logo {
            width: 50px;
            height: 50px;
            vertical-align: middle;
            margin-right: 12px;
        }
        .row-name {
            font-size: 20px;
            font-weight: bold;
            vertical-align: middle;
        }
        .guest-name {
            font-size: 18px;
            font-weight: bold;
            vertical-align: middle;
        }

        /* Delegates section */
        .delegates {
            margin-bottom: 12px;
            font-size: 10px;
            color: #555;
        }

        /* Items table */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12px;
        }
        th {
            background-color: #F9FAFB;
            padding: 6px 8px;
            text-align: left;
            border-bottom: 1px solid #E5E7EB;
            font-weight: bold;
            font-size: 10px;
        }
        th.right {
            text-align: right;
        }
        td {
            padding: 5px 8px;
            border-bottom: 1px solid #F3F4F6;
            font-size: 10px;
        }
        td.right {
            text-align: right;
        }

        /* Totals row */
        .totals-row td {
            font-weight: bold;
            border-top: 2px solid #E5E7EB;
            padding-top: 8px;
        }

        /* Payment status */
        .payment-status {
            margin-top: 8px;
            font-size: 10px;
        }
        .status-paid { color: #22C55E; font-weight: bold; }
        .status-partial { color: #F59E0B; font-weight: bold; }
        .status-unpaid { color: #EF4444; font-weight: bold; }

        /* Footer */
        .page-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 8px 20mm;
            font-size: 9px;
            color: #888;
            border-top: 1px solid #E5E7EB;
            text-align: center;
        }
    """


def _build_by_order_page(
    order: dict,
    registry_rows: dict[str, dict],
    products_map: dict[str, dict],
    page_num: int,
    total_pages: int,
    event_name: str,
    generation_date: str,
    row_label_prefix: str = 'row',
) -> str:
    """Build one page for by_order mode (one page per registry row/order)."""
    row_id = order.get('registry_row_id', '')
    row_data = registry_rows.get(row_id, {})
    row_label = row_data.get('label', row_id)
    logo_url = row_data.get('logo_url')

    # Header with row logo and label in format "{row_label_prefix}: {name}"
    logo_html = ''
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="" class="row-logo" />'

    header_text = f"{row_label_prefix}: {row_label}"

    # Delegates
    delegates = order.get('delegates', {})
    primary_email = delegates.get('primary', '') if isinstance(delegates, dict) else ''
    secondary_email = delegates.get('secondary', '') if isinstance(delegates, dict) else ''
    delegate_parts = []
    if primary_email:
        delegate_parts.append(f"Primary: {primary_email}")
    if secondary_email:
        delegate_parts.append(f"Secondary: {secondary_email}")
    delegates_html = ', '.join(delegate_parts)

    # Build guests table
    items = order.get('items', [])
    rows_html = ''
    for item in items:
        guest_name = item.get('item_fields_data', {}).get('name', '') if isinstance(item.get('item_fields_data'), dict) else ''
        product_id = item.get('product_id', '')
        product_info = products_map.get(product_id, {})
        product_name = product_info.get('name', product_id)
        variant = _get_variant_display(item, products_map)
        fields = _get_item_fields_display(item)
        unit_price = _format_euro(item.get('unit_price', 0))
        line_total = _format_euro(item.get('line_total', 0))

        rows_html += f"""            <tr>
                <td>{guest_name}</td>
                <td>{product_name}</td>
                <td>{variant}</td>
                <td>{fields}</td>
                <td class="right">{unit_price}</td>
                <td class="right">{line_total}</td>
            </tr>
"""

    # Totals
    total_amount = _format_euro(order.get('total_amount', 0))
    payment_status = order.get('payment_status', 'unpaid')
    status_class = f"status-{payment_status}"

    return f"""<div class="page">
    <div class="page-header">
        {logo_html}<span class="row-name">{header_text}</span>
    </div>
    <div class="delegates">{delegates_html}</div>
    <table>
        <thead>
            <tr>
                <th>Guest</th>
                <th>Product</th>
                <th>Variant</th>
                <th>Fields</th>
                <th class="right">Unit price</th>
                <th class="right">Line total</th>
            </tr>
        </thead>
        <tbody>
{rows_html}            <tr class="totals-row">
                <td colspan="4"></td>
                <td class="right">Total:</td>
                <td class="right">{total_amount}</td>
            </tr>
        </tbody>
    </table>
    <div class="payment-status">Payment: <span class="{status_class}">{payment_status}</span></div>
    <div class="page-footer">{event_name} | {generation_date} | Page {page_num} of {total_pages}</div>
</div>
"""


def _build_by_guest_page(
    guest_name: str,
    guest_items: list[dict],
    row_id: str,
    registry_rows: dict[str, dict],
    products_map: dict[str, dict],
    page_num: int,
    total_pages: int,
    event_name: str,
    generation_date: str,
    row_label_prefix: str = 'row',
) -> str:
    """Build one page for by_guest mode (one page per person)."""
    row_data = registry_rows.get(row_id, {})
    row_label = row_data.get('label', row_id)
    logo_url = row_data.get('logo_url')

    # Header with row logo, row label, and guest name
    logo_html = ''
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="" class="row-logo" />'

    header_text = f"{row_label_prefix}: {row_label}"

    # Build items table
    rows_html = ''
    for item in guest_items:
        product_id = item.get('product_id', '')
        product_info = products_map.get(product_id, {})
        product_name = product_info.get('name', product_id)
        variant = _get_variant_display(item, products_map)
        fields = _get_item_fields_display(item)
        unit_price = _format_euro(item.get('unit_price', 0))

        rows_html += f"""            <tr>
                <td>{product_name}</td>
                <td>{variant}</td>
                <td>{fields}</td>
                <td class="right">{unit_price}</td>
            </tr>
"""

    return f"""<div class="page">
    <div class="page-header">
        {logo_html}<span class="row-name">{header_text}</span>
    </div>
    <div class="guest-name">{guest_name}</div>
    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th>Variant</th>
                <th>Fields</th>
                <th class="right">Unit price</th>
            </tr>
        </thead>
        <tbody>
{rows_html}        </tbody>
    </table>
    <div class="page-footer">{event_name} | {generation_date} | Page {page_num} of {total_pages}</div>
</div>
"""


def build_by_order_pdf(
    orders: list[dict],
    registry_rows: dict[str, dict],
    products_map: dict[str, dict],
    event_name: str,
    product_filter: str | None = None,
    row_label_prefix: str = 'row',
) -> str:
    """Build full HTML for by_order mode."""
    generation_date = date.today().isoformat()

    # Apply product filter: include only orders that have at least one matching line
    filtered_orders = []
    for order in orders:
        if product_filter:
            matching_items = [
                item for item in order.get('items', [])
                if item.get('product_id') == product_filter
            ]
            if not matching_items:
                continue
            # Create a copy with only matching items
            filtered_order = {**order, 'items': matching_items}
            filtered_orders.append(filtered_order)
        else:
            filtered_orders.append(order)

    if not filtered_orders:
        return ''

    # Sort alphabetically by row label (case-insensitive)
    def sort_key(order: dict) -> str:
        row_id = order.get('registry_row_id', '')
        row_data = registry_rows.get(row_id, {})
        row_label = row_data.get('label', row_id)
        return _sort_key_row_label(row_label)

    filtered_orders.sort(key=sort_key)

    total_pages = len(filtered_orders)
    pages_html = ''
    for i, order in enumerate(filtered_orders, 1):
        pages_html += _build_by_order_page(
            order, registry_rows, products_map, i, total_pages, event_name, generation_date,
            row_label_prefix,
        )

    css = _build_css()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Preparation PDF - {event_name}</title>
    <style>{css}
    </style>
</head>
<body>
{pages_html}
</body>
</html>"""


def build_by_guest_pdf(
    orders: list[dict],
    registry_rows: dict[str, dict],
    products_map: dict[str, dict],
    event_name: str,
    product_filter: str | None = None,
    row_label_prefix: str = 'row',
) -> str:
    """Build full HTML for by_guest mode."""
    generation_date = date.today().isoformat()

    # Collect all guests across all orders
    guests: list[dict] = []  # Each entry: {name, row_id, items}
    for order in orders:
        row_id = order.get('registry_row_id', '')
        items = order.get('items', [])

        # Group items by person name (item_fields_data.name)
        persons: dict[str, list[dict]] = {}
        for item in items:
            ifd = item.get('item_fields_data', {})
            person_name = ifd.get('name', '') if isinstance(ifd, dict) else ''
            if not person_name:
                person_name = '(unnamed)'
            if person_name not in persons:
                persons[person_name] = []
            persons[person_name].append(item)

        for person_name, person_items in persons.items():
            if product_filter:
                matching = [it for it in person_items if it.get('product_id') == product_filter]
                if not matching:
                    continue
                guests.append({
                    'name': person_name,
                    'row_id': row_id,
                    'items': matching,
                })
            else:
                guests.append({
                    'name': person_name,
                    'row_id': row_id,
                    'items': person_items,
                })

    if not guests:
        return ''

    # Sort by last word of name (case-insensitive), secondary sort by first name
    guests.sort(key=lambda g: _sort_key_guest_name(g['name']))

    total_pages = len(guests)
    pages_html = ''
    for i, guest in enumerate(guests, 1):
        pages_html += _build_by_guest_page(
            guest['name'],
            guest['items'],
            guest['row_id'],
            registry_rows,
            products_map,
            i,
            total_pages,
            event_name,
            generation_date,
            row_label_prefix,
        )

    css = _build_css()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Preparation PDF - {event_name}</title>
    <style>{css}
    </style>
</head>
<body>
{pages_html}
</body>
</html>"""


# --- Main handler ---

def lambda_handler(event, context):
    """Main handler for GET /admin/events/{event_id}/preparation-pdf."""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Authorization: admin roles only
        if not _has_admin_access(user_roles):
            return create_error_response(403, 'Access denied: insufficient permissions')

        log_successful_access(user_email, user_roles, 'generate_preparation_pdf')

        # Get event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        if not event_id:
            return create_error_response(400, 'Missing event_id parameter')

        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        mode = query_params.get('mode', '')
        product_filter = query_params.get('product_filter') or None

        if mode not in ('by_order', 'by_guest'):
            return create_error_response(
                400, 'Invalid mode parameter. Must be "by_order" or "by_guest".'
            )

        # Fetch Event record
        event_response = events_table.get_item(Key={'event_id': event_id})
        if 'Item' not in event_response:
            return create_error_response(404, 'Event not found')

        event_record = event_response['Item']
        event_name = event_record.get('name', 'Event')

        # Fetch qualifying orders (submitted/locked)
        orders = _scan_qualifying_orders(event_id)

        # Req 15.8: No qualifying orders → return message
        if not orders:
            return create_success_response({
                'message': 'No submitted or locked orders available for PDF generation.',
                'pdf': None,
            })

        # Fetch registry rows for logos and labels
        registry_config = event_record.get('registry_config', {})
        s3_path = registry_config.get('s3_path', '')
        registry_rows = _fetch_registry_rows(s3_path) if s3_path else {}

        # Resolve row_label prefix from registry_config (fallback: "row")
        row_label_prefix = registry_config.get('row_label', '') or 'row'

        # Fetch products for product names
        products_map = _fetch_products_map(event_id)

        # Build HTML for the PDF
        if mode == 'by_order':
            html = build_by_order_pdf(
                orders, registry_rows, products_map, event_name, product_filter,
                row_label_prefix,
            )
        else:
            html = build_by_guest_pdf(
                orders, registry_rows, products_map, event_name, product_filter,
                row_label_prefix,
            )

        # If filtering removed all pages, return empty-state message
        if not html:
            return create_success_response({
                'message': 'No orders match the specified product filter.',
                'pdf': None,
            })

        # Render PDF with WeasyPrint
        try:
            if weasyprint is None:
                raise ImportError("weasyprint is not installed")
            pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        except Exception as e:
            logger.error(f"WeasyPrint rendering error: {type(e).__name__} - {str(e)}")
            return create_error_response(500, 'PDF rendering failed')

        # Base64-encode for API Gateway binary response
        base64_encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        filename = f"preparation-{mode}-{event_id}.pdf"

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="{filename}"',
                **cors_headers(),
            },
            "body": base64_encoded_pdf,
            "isBase64Encoded": True,
        }

    except Exception as e:
        logger.error(f"Error in generate_preparation_pdf: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
