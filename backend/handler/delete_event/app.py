import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Events')

def lambda_handler(event, context):
    try:
        event_id = event['pathParameters']['event_id']
        
        table.delete_item(Key={'event_id': event_id})
        
        return {
            'statusCode': 204,
            'headers': cors_headers(),
            'body': ''
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }