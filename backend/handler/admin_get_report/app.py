import json
import os
import boto3

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
    lambda_handler = create_smart_fallback_handler("admin_get_report")
    import sys
    sys.exit(0)

s3 = boto3.client('s3')
reports_bucket = os.environ.get('REPORTS_BUCKET_NAME', 'h-dcn-webshop-reports')


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Products_Read
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_Read'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_get_report')

        # Get optional filters from query params
        query_params = event.get('queryStringParameters') or {}
        event_id_filter = query_params.get('event_id')
        report_type = query_params.get('report_type', 'financial')
        order_status_filter = query_params.get('order_status')
        payment_status_filter = query_params.get('payment_status')

        # Read latest snapshot from S3
        s3_key = 'reports/latest_snapshot.json'
        try:
            response = s3.get_object(Bucket=reports_bucket, Key=s3_key)
            snapshot_data = json.loads(response['Body'].read().decode('utf-8'))
        except s3.exceptions.NoSuchKey:
            return create_error_response(404, 'No report snapshot available. Please generate a report first.')
        except Exception as s3_err:
            print(f"Error reading S3 snapshot: {str(s3_err)}")
            return create_error_response(404, 'No report snapshot available. Please generate a report first.')

        # Apply event_id filter if specified
        if event_id_filter:
            # Filter orders by event_id
            orders = snapshot_data.get('orders', [])
            if event_id_filter == 'null':
                filtered_orders = [o for o in orders if not o.get('event_id')]
            else:
                filtered_orders = [o for o in orders if o.get('event_id') == event_id_filter]

            # Filter movements by event_id
            movements = snapshot_data.get('movements', [])
            if event_id_filter == 'null':
                filtered_movements = [m for m in movements if not m.get('event_id')]
            else:
                filtered_movements = [m for m in movements if m.get('event_id') == event_id_filter]

            # Recalculate summary for filtered data
            total_revenue = sum(float(o.get('total_amount', 0)) for o in filtered_orders)
            total_paid = sum(float(o.get('amount_paid', 0)) for o in filtered_orders)

            snapshot_data['orders'] = filtered_orders
            snapshot_data['movements'] = filtered_movements
            snapshot_data['summary'] = {
                'total_orders': len(filtered_orders),
                'total_revenue': total_revenue,
                'total_paid': total_paid,
                'total_outstanding': total_revenue - total_paid,
            }
            snapshot_data['filtered_by_event_id'] = event_id_filter

            # Filter by_event to only include the requested event
            by_event = snapshot_data.get('by_event', {})
            event_key = event_id_filter if event_id_filter != 'null' else 'webshop'
            if event_key in by_event:
                snapshot_data['by_event'] = {event_key: by_event[event_key]}
            else:
                snapshot_data['by_event'] = {}

        # Remove raw orders/movements from response for lighter payload
        # Unless report_type needs them
        orders_list = snapshot_data.get('orders', [])
        movements_list = snapshot_data.get('movements', [])

        # Exclude draft and cancelled from order lists
        orders_list = [o for o in orders_list if o.get('status') not in ('draft', 'cancelled')]

        # Apply order_status filter
        if order_status_filter and order_status_filter != 'all':
            orders_list = [o for o in orders_list if o.get('status') == order_status_filter]

        # Apply payment_status filter
        if payment_status_filter and payment_status_filter != 'all':
            orders_list = [o for o in orders_list if o.get('payment_status') == payment_status_filter]

        result = {
            'generated_at': snapshot_data.get('generated_at'),
            'summary': snapshot_data.get('summary', {}),
            'by_event': snapshot_data.get('by_event', {}),
            'by_status': snapshot_data.get('by_status', {}),
            'stock_movements': snapshot_data.get('stock_movements', {}),
        }

        # Include orders for orders/financial report types
        if report_type in ('orders', 'financial'):
            result['orders'] = orders_list

        # Include movements for stock_movements report type
        if report_type == 'stock_movements':
            result['movements'] = movements_list

        if event_id_filter:
            result['filtered_by_event_id'] = event_id_filter

        return create_success_response(result)

    except Exception as e:
        print(f"Error retrieving report: {str(e)}")
        return create_error_response(500, 'Internal server error')
