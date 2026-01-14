import json
import boto3
import sys
import os
from datetime import datetime

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
    lambda_handler = create_smart_fallback_handler("update_product")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
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
        
        # UPDATED: Check for products update permission with new role structure
        # Users now have Products_CRUD + Regio_* instead of deprecated Products_CRUD_All
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Products_CRUD role (which grants products_update permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['products_update']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_product')
        
        # Get product ID and data
        product_id = event['pathParameters']['id']
        data = json.loads(event['body']) if event['body'] else {}

        # Dynamically build update expression and attribute values
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        for key, value in data.items():
            if key == 'id':
                continue  # Don't update the primary key

            # Convert image to array if it's a string
            if key == 'image' and isinstance(value, str):
                value = [value]

            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"
            update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value

        # Add updated timestamp
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = datetime.now().isoformat()

        update_expression = "SET " + ", ".join(update_expression_parts)

        table.update_item(
            Key={'id': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        print(f"Product {product_id} updated by {user_email} with roles {user_roles}")

        return create_success_response({
            'message': f'Product {product_id} updated successfully',
            'updated_fields': list(data.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_product: {str(e)}")
        return create_error_response(500, 'Internal server error')

