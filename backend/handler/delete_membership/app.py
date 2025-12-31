import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers()}
    
    try:
        membership_id = event['pathParameters']['id']
        
        table.delete_item(Key={'membership_type_id': membership_id})
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Membership deleted successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }