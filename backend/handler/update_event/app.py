import json
import boto3
from datetime import datetime
from shared.auth_utils import require_auth, create_success_response, create_error_response

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Events')

@require_auth(['events_update', 'events_create'])
def lambda_handler(event, context):
    try:
        event_id = event['pathParameters']['event_id']
        body = json.loads(event['body'])
        
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in body.items():
            if key != 'event_id':
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_params = {
            'Key': {'event_id': event_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        table.update_item(**update_params)
        
        print(f"Event {event_id} updated by {event['auth_user']} with roles {event['auth_roles']}")
        
        return create_success_response({
            'message': 'Event updated successfully',
            'updated_fields': list(body.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_event: {str(e)}")
        return create_error_response(500, 'Internal server error')