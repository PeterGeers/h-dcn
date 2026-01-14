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
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers()}
    
    try:
        data = json.loads(event['body'])
        
        membership_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'membership_type_id': membership_id,
            'created_at': timestamp,
            'updated_at': timestamp,
            **data
        }
        
        table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps(item, default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }