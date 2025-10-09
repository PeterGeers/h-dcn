import boto3
import os
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        id = event['pathParameters']['id']
        data = json.loads(event['body']) if event['body'] else {}

        # Dynamically build update expression and attribute values
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        for key, value in data.items():
            if key == 'id':
                continue  # Don't update the primary key

            # Convert image to array if it's a string
            if key == 'image' and isinstance(value, str):
                value = [value]

            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"
            update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value

        update_expression = "SET " + ", ".join(update_expression_parts)

        table.update_item(
            Key={'id': id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': f'Product {id} updated successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",   # of "https://jouwdomein.nl"
        "Access-Control-Allow-Methods": "PUT,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }