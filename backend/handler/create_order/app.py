import json
import boto3
import uuid

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table('Orders')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        order_id = str(uuid.uuid4())
        order = {'order_id': order_id, **body}
        
        orders_table.put_item(Item=order)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'order_id': order_id, 'message': 'Order created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }