import json
import boto3
import base64
import uuid
from datetime import datetime

# Import from shared auth layer (REQUIRED)
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_member_self")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    """
    Get member's own data - allows users to look up their own record
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials from JWT token
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Get Cognito user ID (sub) from JWT token
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization', '')
        jwt_token = auth_header.replace('Bearer ', '')
        
        # Decode JWT to get the Cognito user ID (sub)
        parts = jwt_token.split('.')
        payload_encoded = parts[1]
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        cognito_user_id = payload.get('sub')
        if not cognito_user_id:
            return create_error_response(400, 'Cognito user ID not found in token')
        
        print(f"Cognito user ID from JWT: {cognito_user_id}")
        
        # Get member_id from Cognito user attributes
        try:
            cognito_client = boto3.client('cognito-idp')
            user_pool_id = 'eu-west-1_OAT3oPCIm'
            
            # Get user details from Cognito
            cognito_response = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=cognito_user_id
            )
            
            # Extract member_id from user attributes
            member_id = None
            for attr in cognito_response.get('UserAttributes', []):
                if attr['Name'] == 'custom:member_id':
                    member_id = attr['Value']
                    break
            
            if not member_id:
                return create_error_response(400, 'Member ID not found in user profile. Please contact support.')
            
            print(f"Found member_id: {member_id} for Cognito user: {cognito_user_id}")
            
        except Exception as e:
            print(f"Error getting member_id from Cognito: {str(e)}")
            return create_error_response(500, 'Failed to retrieve user information')
        
        
        # Validate permissions - users need members_self_read permission
        # Both hdcnLeden and verzoek_lid should have this permission
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_self_read'], user_email, {'operation': 'get_member_self'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'get_member_self')
        
        method = event['httpMethod']
        
        if method == 'GET':
            return get_own_member_data(member_id, user_email)
        elif method == 'PUT':
            return update_own_member_data(event, member_id, user_email, user_roles)
        elif method == 'POST':
            return create_own_member_data(event, member_id, user_email, user_roles)
        else:
            return create_error_response(405, f'Method {method} not allowed')
    
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, 'Internal server error')

def get_own_member_data(member_id, user_email):
    """
    Get the user's own member record by member_id
    """
    try:
        # Get the member record directly by member_id (primary key)
        response = table.get_item(Key={'member_id': member_id})
        
        item = response.get('Item')
        
        if not item:
            # No member record found - user may be verzoek_lid without data yet
            return create_success_response({
                'member': None,
                'message': 'No member record found. You may need to complete your membership application.',
                'email': user_email,
                'member_id': member_id
            })
        
        # Convert any Decimal types to regular numbers for JSON serialization
        member_data = convert_decimals(item)
        
        print(f"Found member record for {user_email}: {list(member_data.keys())}")
        
        return create_success_response(member_data)
    
    except Exception as e:
        print(f"Error getting member data: {str(e)}")
        return create_error_response(500, 'Failed to retrieve member data')

def update_own_member_data(event, member_id, user_email, user_roles):
    """
    Update the user's own member record
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # First check if member record exists
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' not in response:
            return create_error_response(404, 'Member record not found')
        
        # Build update expression for allowed fields
        # These fields match the selfService: true permissions in frontend/src/config/memberFields.ts
        # Organized by section groups as defined in MEMBER_MODAL_CONTEXTS
        # System fields like member_id, status, lidmaatschap, regio are protected (admin-only)
        # Email is also protected as it's tied to the Cognito account
        allowed_fields = [
            # Persoonlijke Informatie (personal section)
            'voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 
            'geboortedatum', 'geslacht', 'telefoon', 'minderjarigNaam',
            # Note: 'email' is excluded - tied to Cognito account, not editable via self-service
            # Adresgegevens (address section)
            'straat', 'postcode', 'woonplaats', 'land',
            # Lidmaatschap preferences (membership section - only preferences, not status/type/region)
            'privacy', 'clubblad', 'nieuwsbrief', 'wiewatwaar',
            # Motorgegevens (motor section)
            'motormerk', 'motortype', 'bouwjaar', 'kenteken',
            # Financiële Gegevens (financial section)
            'betaalwijze', 'bankrekeningnummer'
        ]
        
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        updates = []
        for field, value in body.items():
            if field in allowed_fields and value is not None:
                attr_name = f"#{field}"
                attr_value = f":{field}"
                updates.append(f"{attr_name} = {attr_value}")
                expression_attribute_names[attr_name] = field
                expression_attribute_values[attr_value] = value
        
        if not updates:
            return create_error_response(400, 'No valid fields to update')
        
        update_expression += ", ".join(updates)
        
        # Add last modified timestamp
        update_expression += ", #lastModified = :lastModified"
        expression_attribute_names['#lastModified'] = 'lastModified'
        expression_attribute_values[':lastModified'] = datetime.now().isoformat()
        
        # Update the record
        table.update_item(
            Key={'member_id': member_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # Fetch the updated member record to return complete data
        updated_response = table.get_item(Key={'member_id': member_id})
        updated_member = updated_response.get('Item', {})
        
        # Convert any Decimal types to regular numbers for JSON serialization
        updated_member_data = convert_decimals(updated_member)
        
        # Log successful update
        log_successful_access(user_email, user_roles, 'update_member_self', {'fields_updated': list(body.keys())})
        
        return create_success_response(updated_member_data)
    
    except Exception as e:
        print(f"Error updating member data: {str(e)}")
        return create_error_response(500, 'Failed to update member data')

def create_own_member_data(event, member_id, user_email, user_roles):
    """
    Create initial member record for verzoek_lid users
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Check if member record already exists
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' in response:
            return create_error_response(409, 'Member record already exists')
        
        # Create new member record with the member_id from Cognito
        timestamp = datetime.now().isoformat()
        
        member_data = {
            'member_id': member_id,  # Use the member_id from Cognito as primary key
            'email': user_email,
            'voornaam': body.get('voornaam', ''),
            'achternaam': body.get('achternaam', ''),
            'telefoon': body.get('telefoon', ''),
            'adres': body.get('adres', ''),
            'postcode': body.get('postcode', ''),
            'woonplaats': body.get('woonplaats', ''),
            'status': 'verzoek_lid',  # Initial status for new applications
            'created': timestamp,
            'lastModified': timestamp
        }
        
        # Save to database
        table.put_item(Item=member_data)
        
        # Log successful creation
        log_successful_access(user_email, user_roles, 'create_member_self')
        
        return create_success_response(convert_decimals(member_data))
    
    except Exception as e:
        print(f"Error creating member data: {str(e)}")
        return create_error_response(500, 'Failed to create member data')

def convert_decimals(obj):
    """
    Convert DynamoDB Decimal types to regular numbers for JSON serialization
    """
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
        return float(obj)
    else:
        return obj
