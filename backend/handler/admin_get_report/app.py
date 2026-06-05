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

        # Get optional tenant filter from query params
        query_params = event.get('queryStringParameters') or {}
        tenant_filter = query_params.get('tenant')

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

        # Apply tenant filter if specified
        if tenant_filter:
            # Filter orders by tenant
            orders = snapshot_data.get('orders', [])
            filtered_orders = [o for o in orders if o.get('tenant') == tenant_filter]

            # Filter movements by tenant
            movements = snapshot_data.get('movements', [])
            filtered_movements = [m for m in movements if m.get('tenant') == tenant_filter]

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
            snapshot_data['filtered_by_tenant'] = tenant_filter

            # Filter by_tenant to only include the requested tenant
            by_tenant = snapshot_data.get('by_tenant', {})
            if tenant_filter in by_tenant:
                snapshot_data['by_tenant'] = {tenant_filter: by_tenant[tenant_filter]}
            else:
                snapshot_data['by_tenant'] = {}

        # Remove raw orders/movements from response for lighter payload
        result = {
            'generated_at': snapshot_data.get('generated_at'),
            'summary': snapshot_data.get('summary', {}),
            'by_tenant': snapshot_data.get('by_tenant', {}),
            'by_status': snapshot_data.get('by_status', {}),
            'stock_movements': snapshot_data.get('stock_movements', {}),
        }

        if tenant_filter:
            result['filtered_by_tenant'] = tenant_filter

        return create_success_response(result)

    except Exception as e:
        print(f"Error retrieving report: {str(e)}")
        return create_error_response(500, 'Internal server error')
