import boto3
import os
import json
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    try:
        response = table.scan(Limit=100)
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                Limit=100
            )
            items.extend(response['Items'])

        return {
            "statusCode": 200,
            'headers': cors_headers(),
            "body": json.dumps(items, default=str)
        }
    
    except ClientError as e:
        return {
            "statusCode": 500,
            'headers': cors_headers(),
            "body": json.dumps({"error": str(e)})
        }
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",   # of "https://jouwdomein.nl"
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }