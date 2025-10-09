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
table = dynamodb.Table('Payments')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        payment_id = str(uuid.uuid4())
        payment = {'payment_id': payment_id, 'payment_date': datetime.now().isoformat(), **body}
        
        table.put_item(Item=payment)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'payment_id': payment_id, 'message': 'Payment created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }