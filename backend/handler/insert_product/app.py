import boto3
import os
import json
import uuid
from datetime import datetime

table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
region = os.environ.get('REGION_NAME', 'eu-west-1')
dynamodb = boto3.resource('dynamodb', region_name=region)
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        product = json.loads(event['body'])
        
        # Generate product ID
        product_id = str(uuid.uuid4())
        
        # Convert image to array if it's a string
        if 'image' in product and isinstance(product['image'], str):
            product['image'] = [product['image']]
        
        item = {
            'id': product_id,
            'createdAt': datetime.now().isoformat(), 
            **product
        }

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            'headers': cors_headers(),
            "body": json.dumps({
                "id": product_id,
                "message": "Product created successfully"
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': cors_headers(),
            "body": json.dumps({"error": str(e)})
        }
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",   # of "https://jouwdomein.nl"
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }
