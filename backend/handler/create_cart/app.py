import json
import boto3
import uuid
from datetime import datetime

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Carts')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        cart_id = str(uuid.uuid4())
        cart = {
            'cart_id': cart_id,
            'customer_id': body['customer_id'],
            'items': [],
            'total_amount': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        table.put_item(Item=cart)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'cart_id': cart_id, 'message': 'Cart created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }