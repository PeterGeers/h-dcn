import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    try:
        response = table.scan()
        memberships = response['Items']
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(memberships, default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }