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
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        # Generate member_id and timestamps
        member_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Start with required fields
        item = {
            'member_id': member_id,
            'created_at': now,
            'updated_at': now
        }
        
        # Add all fields from request body
        for key, value in body.items():
            item[key] = value
        
        table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'member_id': member_id,
                'message': 'Member created successfully'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }
