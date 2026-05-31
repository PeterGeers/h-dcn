import json
import os
import base64
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ORDERS_TABLE = os.environ.get('ORDERS_TABLE', 'Orders')
S3_BUCKET = os.environ.get('S3_BUCKET', 'my-hdcn-bucket')
LOGO_S3_KEY = os.environ.get('LOGO_S3_KEY', 'imagesWebsite/hdcnFavico.png')

# Dutch month names for date formatting
DUTCH_MONTHS = [
    'januari', 'februari', 'maart', 'april', 'mei', 'juni',
    'juli', 'augustus', 'september', 'oktober', 'november', 'december'
]


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


def format_euro(value) -> str:
    """Format a monetary value with euro symbol and 2 decimal places.

    Args:
        value: A numeric value (int, float) or string representation of a number.

    Returns:
        Formatted string like "€12.50"
    """
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return f"\u20ac{amount:.2f}"


def format_dutch_date(iso_timestamp: str) -> str:
    """Format an ISO 8601 timestamp in Dutch locale.

    Produces format: "15 januari 2025, 14:30"

    Args:
        iso_timestamp: ISO 8601 date string (e.g. "2025-01-15T14:30:00Z")

    Returns:
        Dutch-formatted date string.
    """
    from datetime import datetime

    try:
        # Handle both 'Z' suffix and '+00:00' timezone formats
        ts = iso_timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
        day = dt.day
        month = DUTCH_MONTHS[dt.month - 1]
        year = dt.year
        hours = dt.hour
        minutes = dt.minute
        return f"{day} {month} {year}, {hours:02d}:{minutes:02d}"
    except (ValueError, TypeError, IndexError):
        return iso_timestamp or ""


def render_order_html(order: dict, logo_data_uri: Optional[str] = None) -> str:
    """Render order data into an HTML string suitable for PDF generation.

    Builds a complete HTML document with A4-appropriate CSS styling,
    populated with order data including header, customer info, product table,
    delivery info, and totals.

    Args:
        order: Order record dict from DynamoDB.
        logo_data_uri: Base64 data URI for the logo image, or None to omit.

    Returns:
        Complete HTML string ready for WeasyPrint rendering.
    """
    order_id = order.get('order_id', '')
    timestamp = order.get('timestamp', '')
    formatted_date = format_dutch_date(timestamp)

    # Customer info
    customer_info = order.get('customer_info', {})
    customer_name = customer_info.get('name', '')
    customer_straat = customer_info.get('straat', '')
    customer_postcode = customer_info.get('postcode', '')
    customer_woonplaats = customer_info.get('woonplaats', '')
    customer_email = customer_info.get('email')
    customer_phone = customer_info.get('phone')

    # Items
    items = order.get('items', [])

    # Delivery
    delivery_option = order.get('delivery_option')
    delivery_cost = order.get('delivery_cost')

    # Totals
    subtotal_amount = order.get('subtotal_amount', '0.00')
    total_amount = order.get('total_amount', '0.00')

    # Build logo HTML
    logo_html = ''
    if logo_data_uri is not None:
        logo_html = f'<img src="{logo_data_uri}" alt="H-DCN Logo" class="logo" />'

    # Build customer email/phone lines
    customer_extra_html = ''
    if customer_email:
        customer_extra_html += f'<p>{customer_email}</p>\n'
    if customer_phone:
        customer_extra_html += f'<p>{customer_phone}</p>\n'

    # Build product rows
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
                <td>{quantity}</td>
                <td>{format_euro(price)}</td>
                <td>{format_euro(line_total)}</td>
            </tr>
'''

    # Build delivery row (if present)
    delivery_row_html = ''
    if delivery_option:
        delivery_label = delivery_option.get('label', 'Verzending')
        delivery_cost_val = delivery_cost if delivery_cost else '0.00'
        delivery_row_html = f'''            <tr class="delivery-row">
                <td colspan="4">{delivery_label}</td>
                <td>{format_euro(delivery_cost_val)}</td>
            </tr>
'''

    # Build totals section
    totals_html = f'''        <div class="totals">
            <div class="totals-row">
                <span>Subtotaal</span>
                <span>{format_euro(subtotal_amount)}</span>
            </div>
'''
    if delivery_option and delivery_cost:
        totals_html += f'''            <div class="totals-row">
                <span>Verzendkosten</span>
                <span>{format_euro(delivery_cost)}</span>
            </div>
'''
    totals_html += f'''            <div class="totals-row total">
                <span>Totaal</span>
                <span>{format_euro(total_amount)}</span>
            </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8" />
    <title>Orderbevestiging {order_id}</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 12px;
            color: #333;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }}
        .header {{
            display: flex;
            align-items: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 15px;
        }}
        .logo {{
            max-height: 60px;
            margin-right: 20px;
        }}
        .header-title {{
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .order-meta {{
            margin-bottom: 25px;
            background-color: #f8f9fa;
            padding: 12px 15px;
            border-radius: 4px;
        }}
        .order-meta p {{
            margin: 4px 0;
        }}
        .customer-info {{
            margin-bottom: 25px;
        }}
        .customer-info h3 {{
            font-size: 14px;
            color: #2c3e50;
            margin-bottom: 8px;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 5px;
        }}
        .customer-info p {{
            margin: 3px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
        }}
        th {{
            background-color: #2c3e50;
            color: white;
            padding: 10px 8px;
            text-align: left;
            font-size: 11px;
            text-transform: uppercase;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .delivery-row {{
            font-style: italic;
            background-color: #fff3cd;
        }}
        .totals {{
            width: 300px;
            margin-left: auto;
            margin-bottom: 30px;
        }}
        .totals-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #dee2e6;
        }}
        .totals-row.total {{
            font-weight: bold;
            font-size: 14px;
            border-bottom: 2px solid #2c3e50;
            border-top: 2px solid #2c3e50;
            padding: 10px 0;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 11px;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            padding-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="header">
        {logo_html}
        <div class="header-title">H-DCN Webshop / Orderbevestiging</div>
    </div>

    <div class="order-meta">
        <p><strong>Ordernummer:</strong> {order_id}</p>
        <p><strong>Datum:</strong> {formatted_date}</p>
        <p><strong>Status:</strong> Betaald</p>
    </div>

    <div class="customer-info">
        <h3>Klantgegevens</h3>
        <p>{customer_name}</p>
        <p>{customer_straat}</p>
        <p>{customer_postcode} {customer_woonplaats}</p>
        {customer_extra_html}
    </div>

    <table>
        <thead>
            <tr>
                <th>Product</th>
                <th>Optie</th>
                <th>Aantal</th>
                <th>Prijs</th>
                <th>Totaal</th>
            </tr>
        </thead>
        <tbody>
{product_rows_html}{delivery_row_html}        </tbody>
    </table>

{totals_html}

    <div class="footer">
        <p>Bedankt voor uw bestelling bij H-DCN Webshop!</p>
    </div>
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

        # Fetch logo from S3 (graceful degradation: PDF still generated if logo fails)
        logo_data_uri = fetch_logo_as_data_uri(S3_BUCKET, LOGO_S3_KEY)

        # Render HTML template with order data and logo
        html = render_order_html(order, logo_data_uri)

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

        # Return PDF response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="orderbevestiging-{order_id}.pdf"',
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
