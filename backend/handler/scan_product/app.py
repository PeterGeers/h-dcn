import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import ClientError

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
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("scan_product")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Check for products read permission with new role structure
        # Users now have Products_CRUD + Regio_* or Products_Read + Regio_* (deprecated _All roles removed)
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Products_CRUD or Products_Read role (which grants products_read permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['products_read']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'scan_product')
        
        # Get products from DynamoDB
        table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
        dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1'))
        table = dynamodb.Table(table_name)

        response = table.scan(
            Limit=100,
            FilterExpression=(boto3.dynamodb.conditions.Attr('is_parent').not_exists() |
                           boto3.dynamodb.conditions.Attr('is_parent').ne(False)) &
                           (boto3.dynamodb.conditions.Attr('source').not_exists() |
                           boto3.dynamodb.conditions.Attr('source').ne('migration'))
        )
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                Limit=100,
                FilterExpression=(boto3.dynamodb.conditions.Attr('is_parent').not_exists() |
                               boto3.dynamodb.conditions.Attr('is_parent').ne(False)) &
                               (boto3.dynamodb.conditions.Attr('source').not_exists() |
                               boto3.dynamodb.conditions.Attr('source').ne('migration'))
            )
            items.extend(response['Items'])

        # Return canonical Dutch field names — no normalization.
        # See: docs/decisions/dutch-field-names.md, frontend/src/config/productFields/fields.ts
        normalized_items = []
        for item in items:
            # Use canonical 'prijs'; fall back to legacy 'price' for unmigrated records
            price_value = item.get('prijs') if item.get('prijs') is not None else item.get('price')
            # Convert Decimal to int/float for JSON serialization
            if isinstance(price_value, Decimal):
                price_value = int(price_value) if price_value == int(price_value) else float(price_value)

            normalized = {
                'product_id': item.get('product_id'),
                'naam': item.get('naam') or item.get('name'),
                'artikelcode': item.get('artikelcode'),
                'prijs': price_value,
                'is_parent': item.get('is_parent'),
                'event_ids': item.get('event_ids', []),
                'active': item.get('active'),
                'groep': item.get('groep'),
                'subgroep': item.get('subgroep'),
                'images': item.get('images', []),
                'order_item_fields': item.get('order_item_fields'),
                'purchase_rules': item.get('purchase_rules'),
            }
            normalized_items.append(normalized)

        print(f"Products scanned by {user_email} with roles {user_roles} - returned {len(normalized_items)} items")

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(normalized_items, default=str)
        }
    
    except ClientError as e:
        print(f"DynamoDB error in scan_product: {str(e)}")
        return create_error_response(500, f'Database error: {str(e)}')
    except Exception as e:
        print(f"Unexpected error in scan_product: {str(e)}")
        return create_error_response(500, 'Internal server error')