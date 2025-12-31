import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    try:
        member_id = event['pathParameters']['id']
        
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Member not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(response['Item'], default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }