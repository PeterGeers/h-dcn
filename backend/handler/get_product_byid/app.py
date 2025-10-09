import boto3
import os
import json
import logging
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

table_name = str(os.environ.get('DYNAMODB_TABLE', 'Producten'))
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        if not event.get('pathParameters') or 'id' not in event['pathParameters']:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing product ID'})
            }

        id = event['pathParameters']['id']
        logger.info(f"Fetching product with ID: {id}")

                # Use id as the key (existing table schema)
        response = table.get_item(
            Key={'id': id}
        )

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': f'Product {id} not found'})
            }

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(response['Item'], default=str)
        }

    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Database error'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",   # of "https://jouwdomein.nl"
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
        }