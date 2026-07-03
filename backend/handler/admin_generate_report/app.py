import json
import os
import boto3
import boto3.dynamodb.conditions
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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_generate_report")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
movements_table_name = os.environ.get('STOCK_MOVEMENTS_TABLE_NAME', 'StockMovements')
reports_bucket = os.environ.get('REPORTS_BUCKET_NAME', 'h-dcn-webshop-reports')
orders_table = dynamodb.Table(orders_table_name)
movements_table = dynamodb.Table(movements_table_name)


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

        log_successful_access(user_email, user_roles, 'admin_generate_report')

        now = datetime.now(timezone.utc).isoformat()

        # Fetch all orders
        orders_response = orders_table.scan()
        all_orders = orders_response.get('Items', [])
        while 'LastEvaluatedKey' in orders_response:
            orders_response = orders_table.scan(ExclusiveStartKey=orders_response['LastEvaluatedKey'])
            all_orders.extend(orders_response.get('Items', []))

        # Exclude draft and cancelled orders from financial calculations
        orders = [o for o in all_orders if o.get('status') not in ('draft', 'cancelled')]

        # Fetch all stock movements
        movements_response = movements_table.scan()
        movements = movements_response.get('Items', [])
        while 'LastEvaluatedKey' in movements_response:
            movements_response = movements_table.scan(ExclusiveStartKey=movements_response['LastEvaluatedKey'])
            movements.extend(movements_response.get('Items', []))

        # Compute summary
        total_orders = len(orders)
        total_revenue = sum(float(o.get('total_amount', 0)) for o in orders)
        total_paid = sum(float(o.get('amount_paid', 0)) for o in orders)
        total_outstanding = total_revenue - total_paid

        # Per-event_id breakdown
        by_event = {}
        for order in orders:
            event_id = order.get('event_id') or 'webshop'
            if event_id not in by_event:
                by_event[event_id] = {'order_count': 0, 'revenue': 0, 'paid': 0}
            by_event[event_id]['order_count'] += 1
            by_event[event_id]['revenue'] += float(order.get('total_amount', 0))
            by_event[event_id]['paid'] += float(order.get('amount_paid', 0))

        # Per-status breakdown
        status_counts = {}
        for order in orders:
            status = order.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Stock movement summary
        inbound_count = sum(1 for m in movements if m.get('type') == 'inbound')
        sale_count = sum(1 for m in movements if m.get('type') == 'sale')
        total_inbound_qty = sum(int(m.get('quantity', 0)) for m in movements if m.get('type') == 'inbound')

        # Build snapshot
        snapshot = {
            'generated_at': now,
            'generated_by': user_email,
            'summary': {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'total_paid': total_paid,
                'total_outstanding': total_outstanding,
            },
            'by_event': by_event,
            'by_status': status_counts,
            'stock_movements': {
                'inbound_count': inbound_count,
                'sale_count': sale_count,
                'total_inbound_quantity': total_inbound_qty,
            },
            'orders': orders,
            'movements': movements,
        }

        # Convert Decimals to floats for JSON serialization
        snapshot_json = json.dumps(snapshot, default=str)

        # Write to S3
        s3_key = 'reports/latest_snapshot.json'
        s3.put_object(
            Bucket=reports_bucket,
            Key=s3_key,
            Body=snapshot_json,
            ContentType='application/json'
        )

        # Also write timestamped version for history
        timestamped_key = f"reports/snapshot_{now.replace(':', '-').replace('+', '_')}.json"
        s3.put_object(
            Bucket=reports_bucket,
            Key=timestamped_key,
            Body=snapshot_json,
            ContentType='application/json'
        )

        return create_success_response({
            'generated_at': now,
            'summary': snapshot['summary'],
            'by_event': by_event,
            'by_status': status_counts,
            's3_key': s3_key,
            'message': 'Report generated successfully'
        })

    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return create_error_response(500, 'Internal server error')
