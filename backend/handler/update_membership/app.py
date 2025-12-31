import json
import boto3
from datetime import datetime

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers()}
    
    try:
        membership_id = event['pathParameters']['id']
        data = json.loads(event['body'])
        
        update_expression = "SET #updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        expression_names = {'#updated_at': 'updated_at'}
        
        for key, value in data.items():
            update_expression += f", #{key} = :{key}"
            expression_values[f":{key}"] = value
            expression_names[f"#{key}"] = key
        
        table.update_item(
            Key={'membership_type_id': membership_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Membership updated successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }