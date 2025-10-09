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
table = dynamodb.Table('Events')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        if not isinstance(body, dict):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Request body must be a JSON object'})
            }
        
        event_id = str(uuid.uuid4())
        event_item = {'event_id': event_id, 'created_at': datetime.utcnow().isoformat(), **body}
        
        table.put_item(Item=event_item)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'event_id': event_id, 'message': 'Event created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }