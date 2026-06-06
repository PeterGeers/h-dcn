"""
GET /products — Tenant-filtered product listing for webshop buyers.

Returns active parent products filtered by the requested tenant parameter,
validated against the user's Cognito group claims.

Query Parameters:
    tenant (required): Comma-separated tenant values (e.g. "h-dcn" or "h-dcn,presmeet")

Requirements: 7.1–7.7, 2.1–2.3
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    from shared.tenant_resolver import resolve_tenants, validate_tenant_access
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_products")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Derive accessible tenants from Cognito group claims.
        # Tenant resolution IS the access control for this endpoint:
        # users without any qualifying role get an empty tenant set → 403.
        user_tenants = resolve_tenants(user_roles)

        # Get requested tenant from query parameters
        query_params = event.get('queryStringParameters') or {}
        requested_tenant = query_params.get('tenant')

        # If no tenant parameter provided, use all user tenants
        if not requested_tenant:
            if not user_tenants:
                return create_error_response(403, 'No tenant access',
                    details={'error': 'tenant_access_denied',
                             'details': {'requested_tenant': '',
                                         'allowed_tenants': []}})
            requested_tenant = ','.join(sorted(user_tenants))

        # Validate requested tenant against user access
        access_error = validate_tenant_access(requested_tenant, user_tenants)
        if access_error:
            return access_error

        # Parse the validated tenant values
        tenants = [t.strip() for t in requested_tenant.split(',') if t.strip()]

        log_successful_access(user_email, user_roles, 'get_products')

        # Build filter: is_parent=true, active=true, tenant in requested tenants
        if len(tenants) == 1:
            filter_expr = (
                Attr('is_parent').eq(True) &
                Attr('active').eq(True) &
                Attr('tenant').eq(tenants[0])
            )
        else:
            filter_expr = (
                Attr('is_parent').eq(True) &
                Attr('active').eq(True) &
                Attr('tenant').is_in(tenants)
            )

        # Scan with filter
        response = table.scan(FilterExpression=filter_expr)
        products = response.get('Items', [])

        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            products.extend(response.get('Items', []))

        # Return product list with relevant fields
        result = []
        for product in products:
            item = {
                'product_id': product.get('product_id'),
                'name': product.get('name'),
                'description': product.get('description'),
                'price': product.get('price'),
                'tenant': product.get('tenant'),
                'groep': product.get('groep'),
                'subgroep': product.get('subgroep'),
                'images': product.get('images', []),
                'variant_schema': product.get('variant_schema'),
                'order_item_fields': product.get('order_item_fields'),
                'purchase_rules': product.get('purchase_rules'),
                'active': product.get('active'),
            }
            result.append(item)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'products': result,
                'total_count': len(result),
                'tenants': tenants,
            }, default=str)
        }

    except Exception as e:
        print(f"Error retrieving products: {str(e)}")
        return create_error_response(500, 'Internal server error')
