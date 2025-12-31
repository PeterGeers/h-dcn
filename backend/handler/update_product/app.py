import json
import boto3
import sys
import os
from datetime import datetime
from shared.auth_utils import require_auth, create_success_response, create_error_response

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
table = dynamodb.Table(table_name)

@require_auth(['Products_CRUD_All', 'Webshop_Management', 'hdcnAdmins', 'System_CRUD_All', 'Webmaster'])
def lambda_handler(event, context):
    try:
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

        print(f"Product {product_id} updated by {event['auth_user']} with roles {event['auth_roles']}")

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

