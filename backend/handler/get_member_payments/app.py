import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Payments')

def lambda_handler(event, context):
    try:
        member_id = event['pathParameters']['member_id']
        
        response = table.query(
            IndexName='MemberPaymentsIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('member_id').eq(member_id)
        )
        
        payments = response['Items']
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(payments, default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }