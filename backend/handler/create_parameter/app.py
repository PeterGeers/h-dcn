import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Parameters')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        
        parameter_id = str(uuid.uuid4())
        parameter = {'parameter_id': parameter_id, 'created_at': datetime.utcnow().isoformat(), **body}
        
        table.put_item(Item=parameter)
        
        return {
            'statusCode': 201,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE'
            },
            'body': json.dumps({'parameter_id': parameter_id, 'message': 'Parameter created successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE'
            },
            'body': json.dumps({'error': str(e)})
        }