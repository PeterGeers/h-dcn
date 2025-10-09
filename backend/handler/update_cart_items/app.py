import json
import boto3

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Carts')

def lambda_handler(event, context):
    try:
        cart_id = event['pathParameters']['cart_id']
        body = json.loads(event['body'])
        
        update_expression = "SET"
        expression_values = {}
        expression_names = {}
        
        for key, value in body.items():
            if key != 'cart_id':
                attr_name = f"#{key}"
                update_expression += f" {attr_name} = :{key},"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_expression = update_expression.rstrip(',')
        
        update_params = {
            'Key': {'cart_id': cart_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        table.update_item(**update_params)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Cart updated successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }