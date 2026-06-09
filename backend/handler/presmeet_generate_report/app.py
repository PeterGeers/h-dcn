"""
PresMeet Generate Report Handler

GET /presmeet/reports/{type}?event_id=X&status=all&payment_status=all&format=json

Generates reports for PresMeet events: attendees, party, tshirts, pickups,
dropoffs, financial, overview.

Requires: Webshop_Management + (Regio_Pressmeet or Regio_All)
"""

import json
import os
import csv
import io
import boto3
from datetime import datetime, timezone
from decimal import Decimal

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
    lambda_handler = create_smart_fallback_handler("presmeet_generate_report")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
events_table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
orders_table = dynamodb.Table(orders_table_name)
events_table = dynamodb.Table(events_table_name)

VALID_REPORT_TYPES = ['attendees', 'party', 'tshirts', 'pickups', 'dropoffs', 'financial', 'overview']
VALID_STATUSES = ['draft', 'submitted', 'locked', 'all']
VALID_PAYMENT_STATUSES = ['unpaid', 'partial', 'paid', 'all']
VALID_FORMATS = ['json', 'csv']


def lambda_handler(event, context):
    """Main Lambda entry point."""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Auth
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Require Webshop_Management + (Regio_Pressmeet or Regio_All)
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Webshop_Management'], user_email, None
        )
        if not is_authorized:
            return permission_error

        # Check for PresMeet regional access
        has_presmeet_access = any(
            role in ['Regio_Pressmeet', 'Regio_All'] for role in user_roles
        )
        if not has_presmeet_access:
            return create_error_response(
                403, 'Access denied: Requires Regio_Pressmeet or Regio_All'
            )

        log_successful_access(user_email, user_roles, 'presmeet_generate_report')

        # Extract path parameters
        path_params = event.get('pathParameters') or {}
        report_type = path_params.get('type', '')

        # Validate report type
        if report_type not in VALID_REPORT_TYPES:
            return create_error_response(
                400,
                f'Invalid report type: {report_type}. '
                f'Valid types: {", ".join(VALID_REPORT_TYPES)}'
            )

        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        event_id = query_params.get('event_id')
        status_filter = query_params.get('status', 'all')
        payment_status_filter = query_params.get('payment_status', 'all')
        output_format = query_params.get('format', 'json')

        # Validate event_id
        if not event_id:
            return create_error_response(400, 'Missing required parameter: event_id')

        # Validate filters
        if status_filter not in VALID_STATUSES:
            return create_error_response(
                400, f'Invalid status filter: {status_filter}. Valid: {", ".join(VALID_STATUSES)}'
            )
        if payment_status_filter not in VALID_PAYMENT_STATUSES:
            return create_error_response(
                400, f'Invalid payment_status filter: {payment_status_filter}. Valid: {", ".join(VALID_PAYMENT_STATUSES)}'
            )
        if output_format not in VALID_FORMATS:
            return create_error_response(
                400, f'Invalid format: {output_format}. Valid: {", ".join(VALID_FORMATS)}'
            )

        # Fetch event metadata
        event_record = get_event(event_id)
        if not event_record:
            return create_error_response(404, f'Event not found: {event_id}')

        # Query orders via GSI
        orders = query_orders_by_event(event_id)

        # Apply filters
        orders = apply_filters(orders, status_filter, payment_status_filter)

        # Build metadata
        metadata = build_metadata(event_record)

        # Generate report data based on type
        report_data = generate_report_data(report_type, orders)

        # Return response
        response_body = {
            'metadata': metadata,
            'data': report_data
        }

        if output_format == 'csv':
            csv_content = format_as_csv(report_type, report_data)
            return {
                'statusCode': 200,
                'headers': {
                    **cors_headers(),
                    'Content-Type': 'text/csv',
                    'Content-Disposition': f'attachment; filename="{report_type}_{event_id}.csv"'
                },
                'body': csv_content
            }

        return create_success_response(response_body)

    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, 'Internal server error')


def get_event(event_id):
    """Fetch event record from Events table."""
    response = events_table.get_item(Key={'event_id': event_id})
    return response.get('Item')


def query_orders_by_event(event_id):
    """Query orders using the event-club-index GSI."""
    orders = []
    response = orders_table.query(
        IndexName='event-club-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('event_id').eq(event_id)
    )
    orders.extend(response.get('Items', []))

    while 'LastEvaluatedKey' in response:
        response = orders_table.query(
            IndexName='event-club-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('event_id').eq(event_id),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        orders.extend(response.get('Items', []))

    return orders


def apply_filters(orders, status_filter, payment_status_filter):
    """Apply optional status and payment_status filters."""
    filtered = orders
    if status_filter != 'all':
        filtered = [o for o in filtered if o.get('status') == status_filter]
    if payment_status_filter != 'all':
        filtered = [o for o in filtered if o.get('payment_status') == payment_status_filter]
    return filtered


def build_metadata(event_record):
    """Build event metadata for the response."""
    return {
        'event_name': event_record.get('name', ''),
        'event_location': event_record.get('location', ''),
        'event_dates': {
            'start': event_record.get('start_date', ''),
            'end': event_record.get('end_date', '')
        },
        'generated_at': datetime.now(timezone.utc).isoformat()
    }


def generate_report_data(report_type, orders):
    """Generate report data based on report type."""
    generators = {
        'attendees': generate_attendees_report,
        'party': generate_party_report,
        'tshirts': generate_tshirts_report,
        'pickups': generate_pickups_report,
        'dropoffs': generate_dropoffs_report,
        'financial': generate_financial_report,
        'overview': generate_overview_report,
    }
    return generators[report_type](orders)


def generate_attendees_report(orders):
    """List meeting ticket holders with name, role, club."""
    attendees = []
    for order in orders:
        club_id = order.get('club_id', '')
        for item in order.get('items', []):
            if _is_product_type(item, 'meeting_ticket', 'meeting'):
                fields = item.get('item_fields_data', {})
                attendees.append({
                    'name': fields.get('name', ''),
                    'role': fields.get('role', ''),
                    'club': club_id,
                    'order_id': order.get('order_id', ''),
                    'status': order.get('status', '')
                })
    return attendees


def generate_party_report(orders):
    """List party ticket holders with name, person_type, club."""
    party_guests = []
    for order in orders:
        club_id = order.get('club_id', '')
        for item in order.get('items', []):
            if _is_product_type(item, 'party_ticket', 'party'):
                fields = item.get('item_fields_data', {})
                party_guests.append({
                    'name': fields.get('name', ''),
                    'person_type': fields.get('person_type', ''),
                    'club': club_id,
                    'order_id': order.get('order_id', ''),
                    'status': order.get('status', '')
                })
    return party_guests


def generate_tshirts_report(orders):
    """List t-shirt orders with person_name, variant, club."""
    tshirts = []
    for order in orders:
        club_id = order.get('club_id', '')
        for item in order.get('items', []):
            if _is_product_type(item, 'tshirt', 'tshirt'):
                fields = item.get('item_fields_data', {})
                tshirts.append({
                    'person_name': fields.get('person_name', ''),
                    'variant': item.get('variant_id', ''),
                    'club': club_id,
                    'order_id': order.get('order_id', ''),
                    'status': order.get('status', '')
                })
    return tshirts


def generate_pickups_report(orders):
    """List airport transfers with direction=Pickup."""
    return _generate_transfer_report(orders, 'Pickup')


def generate_dropoffs_report(orders):
    """List airport transfers with direction=Dropoff."""
    return _generate_transfer_report(orders, 'Dropoff')


def _generate_transfer_report(orders, direction):
    """List airport transfers filtered by direction (from variant)."""
    transfers = []
    for order in orders:
        club_id = order.get('club_id', '')
        for item in order.get('items', []):
            if _is_product_type(item, 'airport_transfer', 'transfer'):
                variant_id = item.get('variant_id', '')
                # Variant encodes direction (e.g. "Pickup-AMS", "Dropoff-RTM")
                if direction.lower() in variant_id.lower():
                    fields = item.get('item_fields_data', {})
                    transfers.append({
                        'flight': fields.get('flight_number', fields.get('flight', '')),
                        'date': fields.get('date', ''),
                        'time': fields.get('time', ''),
                        'persons': _to_int(fields.get('persons', 0)),
                        'club': club_id,
                        'order_id': order.get('order_id', ''),
                        'status': order.get('status', '')
                    })
    return transfers


def generate_financial_report(orders):
    """Calculate total_charged, total_paid, total_outstanding per club + grand totals."""
    clubs = {}
    for order in orders:
        club_id = order.get('club_id', '')
        if club_id not in clubs:
            clubs[club_id] = {
                'club': club_id,
                'total_charged': Decimal('0'),
                'total_paid': Decimal('0'),
                'total_outstanding': Decimal('0')
            }
        charged = Decimal(str(order.get('total_amount', 0)))
        paid = Decimal(str(order.get('total_paid', 0)))
        clubs[club_id]['total_charged'] += charged
        clubs[club_id]['total_paid'] += paid
        clubs[club_id]['total_outstanding'] += (charged - paid)

    # Convert Decimals to floats for JSON serialization
    club_list = []
    for club_data in clubs.values():
        club_list.append({
            'club': club_data['club'],
            'total_charged': float(club_data['total_charged']),
            'total_paid': float(club_data['total_paid']),
            'total_outstanding': float(club_data['total_outstanding'])
        })

    grand_charged = sum(c['total_charged'] for c in club_list)
    grand_paid = sum(c['total_paid'] for c in club_list)
    grand_outstanding = sum(c['total_outstanding'] for c in club_list)

    return {
        'clubs': club_list,
        'totals': {
            'total_charged': grand_charged,
            'total_paid': grand_paid,
            'total_outstanding': grand_outstanding
        }
    }


def generate_overview_report(orders):
    """Summary counts per product type + payment status breakdown."""
    product_type_counts = {}
    payment_breakdown = {'unpaid': 0, 'partial': 0, 'paid': 0}
    status_breakdown = {'draft': 0, 'submitted': 0, 'locked': 0}

    for order in orders:
        # Payment status breakdown
        ps = order.get('payment_status', 'unpaid')
        if ps in payment_breakdown:
            payment_breakdown[ps] += 1

        # Order status breakdown
        s = order.get('status', 'draft')
        if s in status_breakdown:
            status_breakdown[s] += 1

        # Product type counts - use product_type when available, fallback to product_id
        for item in order.get('items', []):
            key = item.get('product_type') or item.get('product_id', 'unknown')
            product_type_counts[key] = product_type_counts.get(key, 0) + 1

    return {
        'total_orders': len(orders),
        'product_counts': product_type_counts,
        'payment_status_breakdown': payment_breakdown,
        'order_status_breakdown': status_breakdown
    }


def format_as_csv(report_type, report_data):
    """Format report data as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'financial':
        # Financial has a special structure
        writer.writerow(['club', 'total_charged', 'total_paid', 'total_outstanding'])
        for club in report_data.get('clubs', []):
            writer.writerow([
                club['club'],
                club['total_charged'],
                club['total_paid'],
                club['total_outstanding']
            ])
        # Grand totals row
        totals = report_data.get('totals', {})
        writer.writerow([
            'TOTAL',
            totals.get('total_charged', 0),
            totals.get('total_paid', 0),
            totals.get('total_outstanding', 0)
        ])
    elif report_type == 'overview':
        # Overview: summary stats as key-value pairs
        writer.writerow(['metric', 'value'])
        writer.writerow(['total_orders', report_data.get('total_orders', 0)])
        for product_id, count in report_data.get('product_counts', {}).items():
            writer.writerow([f'product:{product_id}', count])
        for ps, count in report_data.get('payment_status_breakdown', {}).items():
            writer.writerow([f'payment_status:{ps}', count])
        for s, count in report_data.get('order_status_breakdown', {}).items():
            writer.writerow([f'order_status:{s}', count])
    else:
        # List-type reports (attendees, party, tshirts, pickups, dropoffs)
        if not report_data:
            writer.writerow(_get_headers_for_type(report_type))
        else:
            headers = list(report_data[0].keys())
            writer.writerow(headers)
            for row in report_data:
                writer.writerow([row.get(h, '') for h in headers])

    return output.getvalue()


def _get_headers_for_type(report_type):
    """Return CSV headers for empty report of given type."""
    headers_map = {
        'attendees': ['name', 'role', 'club', 'order_id', 'status'],
        'party': ['name', 'person_type', 'club', 'order_id', 'status'],
        'tshirts': ['person_name', 'variant', 'club', 'order_id', 'status'],
        'pickups': ['flight', 'date', 'time', 'persons', 'club', 'order_id', 'status'],
        'dropoffs': ['flight', 'date', 'time', 'persons', 'club', 'order_id', 'status'],
    }
    return headers_map.get(report_type, [])


def _is_product_type(item, product_type_value, fallback_keyword):
    """Check if an order item matches a product type.

    Uses the `product_type` field as the primary identifier.
    Falls back to string-matching on `product_id` for backward compatibility
    with orders that don't have product_type set.
    """
    # Primary: use product_type field
    item_product_type = item.get('product_type', '')
    if item_product_type:
        return item_product_type == product_type_value

    # Fallback: string-match on product_id for legacy orders without product_type
    product_id = item.get('product_id', '')
    return fallback_keyword in product_id.lower()


def _to_int(value):
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
