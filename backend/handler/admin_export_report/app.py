import json
import os
import csv
import io
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
    lambda_handler = create_smart_fallback_handler("admin_export_report")
    import sys
    sys.exit(0)

s3 = boto3.client('s3')
reports_bucket = os.environ.get('REPORTS_BUCKET_NAME', 'h-dcn-webshop-reports')

# CSV column definitions for order export
ORDER_CSV_COLUMNS = [
    'order_id', 'tenant', 'customer_name', 'club_name', 'status',
    'payment_status', 'total_amount', 'amount_paid', 'created_at'
]


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Products_Export
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_Export'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_export_report')

        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        tenant_filter = query_params.get('tenant')
        export_format = query_params.get('format', 'json').lower()

        if export_format not in ('json', 'csv'):
            return create_error_response(400, 'format must be "json" or "csv"')

        # Read latest snapshot from S3
        s3_key = 'reports/latest_snapshot.json'
        try:
            response = s3.get_object(Bucket=reports_bucket, Key=s3_key)
            snapshot_data = json.loads(response['Body'].read().decode('utf-8'))
        except Exception:
            return create_error_response(404, 'No report snapshot available. Please generate a report first.')

        # Apply tenant filter
        orders = snapshot_data.get('orders', [])
        if tenant_filter:
            orders = [o for o in orders if o.get('tenant') == tenant_filter]

        if export_format == 'json':
            # Return JSON export
            export_data = {
                'generated_at': snapshot_data.get('generated_at'),
                'exported_at': None,  # Will be set by response
                'tenant_filter': tenant_filter,
                'total_orders': len(orders),
                'orders': orders,
            }
            body = json.dumps(export_data, default=str)
            return {
                'statusCode': 200,
                'headers': {
                    **cors_headers(),
                    'Content-Type': 'application/json',
                    'Content-Disposition': 'attachment; filename="report_export.json"'
                },
                'body': body
            }
        else:
            # Return CSV export
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=ORDER_CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            for order in orders:
                writer.writerow(order)

            csv_content = output.getvalue()
            return {
                'statusCode': 200,
                'headers': {
                    **cors_headers(),
                    'Content-Type': 'text/csv',
                    'Content-Disposition': 'attachment; filename="report_export.csv"'
                },
                'body': csv_content
            }

    except Exception as e:
        print(f"Error exporting report: {str(e)}")
        return create_error_response(500, 'Internal server error')
