import json
import boto3
import base64
import uuid
from datetime import datetime

# Import authentication utilities from shared layer or fallback
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
except ImportError:
    # Fallback to local auth_fallback.py
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("⚠️ Using fallback auth - ensure auth_fallback.py is updated")

# Import field validation utilities
try:
    from role_permissions import (
        can_edit_field, 
        PERSONAL_FIELDS, 
        MOTORCYCLE_FIELDS, 
        ADMINISTRATIVE_FIELDS
    )
    print("✅ Using role_permissions for field validation")
except ImportError:
    print("⚠️ role_permissions not available - using basic field validation")
    # Basic fallback field definitions
    PERSONAL_FIELDS = [
        'voornaam', 'achternaam', 'tussenvoegsel', 'initialen',
        'telefoon', 'straat', 'postcode', 'woonplaats', 'land',
        'email', 'nieuwsbrief', 'geboortedatum', 'geslacht', 'wiewatwaar'
    ]
    MOTORCYCLE_FIELDS = ['bouwjaar', 'motormerk', 'motortype', 'kenteken']
    ADMINISTRATIVE_FIELDS = [
        'member_id', 'lidnummer', 'lidmaatschap', 'status', 'tijdstempel',
        'aanmeldingsjaar', 'regio', 'clubblad', 'bankrekeningnummer',
        'datum_ondertekening', 'created_at', 'updated_at'
    ]
    
    def can_edit_field(roles, field_name, is_own_record=False):
        """Basic fallback field validation"""
        # Admin roles can edit everything
        admin_roles = ['System_CRUD', 'System_User_Management', 'Members_CRUD']
        if any(role in roles for role in admin_roles):
            return True
        
        # Administrative fields require admin permissions
        if field_name in ADMINISTRATIVE_FIELDS:
            return False
        
        # Personal and motorcycle fields can be edited by user for own record
        if is_own_record and 'hdcnLeden' in roles:
            if field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS:
                return True
        
        return False

# Field definitions for new applicant creation
APPLICANT_REQUIRED_FIELDS = [
    'voornaam',           # First name
    'achternaam',         # Last name
    'geboortedatum',      # Birth date
    'geslacht',           # Gender (M/V/X/N)
    'telefoon',           # Phone number
    'straat',             # Street address + house number
    'postcode',           # Postal code
    'woonplaats',         # City
    'lidmaatschap',       # Membership type
    'regio',              # Region
    'privacy',            # Privacy consent (must be 'Ja')
]

APPLICANT_OPTIONAL_FIELDS = [
    'initialen',          # Initials
    'tussenvoegsel',      # Name prefix
    'minderjarigNaam',    # Parent/guardian name (required if under 18)
    'land',               # Country (default: Nederland)
    'motormerk',          # Motor brand
    'motortype',          # Motor type/model
    'bouwjaar',           # Build year
    'kenteken',           # License plate
    'wiewatwaar',         # How did you find us
    'clubblad',           # Magazine preference
    'nieuwsbrief',        # Newsletter subscription
    'betaalwijze',        # Payment method
    'bankrekeningnummer', # IBAN
]

APPLICANT_ALLOWED_FIELDS = APPLICANT_REQUIRED_FIELDS + APPLICANT_OPTIONAL_FIELDS

# Default values for new applicants
APPLICANT_DEFAULTS = {
    'status': 'Aangemeld',        # Application status
    'land': 'Nederland',          # Default country
    'clubblad': 'Digitaal',       # Default magazine preference
    'nieuwsbrief': 'Ja',          # Default newsletter subscription
    'betaalwijze': 'Incasso',     # Default payment method
}

def validate_field_permissions(user_roles, user_email, member_record, fields_to_update):
    """
    Validate user has permission to modify the requested fields for self-service
    
    Args:
        user_roles (list): List of user's roles from JWT token
        user_email (str): User's email from JWT token
        member_record (dict): The member record being updated
        fields_to_update (dict): Dictionary of fields and values to update
        
    Returns:
        tuple: (is_valid, error_response, forbidden_fields)
               If valid: (True, None, [])
               If invalid: (False, error_response_dict, list_of_forbidden_fields)
    """
    try:
        member_email = member_record.get('email', '')
        is_own_record = (user_email.lower() == member_email.lower())
        
        # For /members/me endpoint, this should always be the user's own record
        if not is_own_record:
            return False, create_error_response(403, 
                'Access denied: /members/me endpoint can only be used to update your own record'), []
        
        # Check permissions for each field
        forbidden_fields = []
        
        # Special case: verzoek_lid users can update their own application data
        if 'verzoek_lid' in user_roles and member_record.get('status') == 'Aangemeld':
            # Allow verzoek_lid users to update their application fields
            allowed_application_fields = [
                # Personal fields
                'voornaam', 'achternaam', 'initialen', 'tussenvoegsel', 'geboortedatum', 
                'geslacht', 'telefoon', 'straat', 'postcode', 'woonplaats', 'land',
                'minderjarigNaam', 'privacy',
                # Membership fields  
                'lidmaatschap', 'regio', 'clubblad', 'nieuwsbrief', 'wiewatwaar',
                # Motor fields
                'motormerk', 'motortype', 'bouwjaar', 'kenteken',
                # Financial fields
                'betaalwijze', 'bankrekeningnummer'
            ]
            
            for field_name in fields_to_update.keys():
                if field_name not in allowed_application_fields:
                    forbidden_fields.append(field_name)
        else:
            # Use standard permission system for other users
            for field_name in fields_to_update.keys():
                if not can_edit_field(user_roles, field_name, is_own_record):
                    forbidden_fields.append(field_name)
        
        # If there are forbidden fields, return error with details
        if forbidden_fields:
            # Categorize forbidden fields for better error messages
            admin_fields = [f for f in forbidden_fields if f in ADMINISTRATIVE_FIELDS]
            other_fields = [f for f in forbidden_fields if f not in ADMINISTRATIVE_FIELDS]
            
            error_parts = []
            if admin_fields:
                error_parts.append(f"Administrative fields ({', '.join(admin_fields)}) require admin privileges")
            if other_fields:
                error_parts.append(f"Fields ({', '.join(other_fields)}) cannot be modified via self-service")
            
            error_message = f"Access denied: {'; '.join(error_parts)}"
            
            return False, create_error_response(403, error_message, {
                'forbidden_fields': forbidden_fields,
                'allowed_fields': PERSONAL_FIELDS + MOTORCYCLE_FIELDS
            }), forbidden_fields
        
        return True, None, []
        
    except Exception as e:
        print(f"Error validating field permissions: {str(e)}")
        return False, create_error_response(500, 'Error validating permissions'), []

def update_member_self_record(member_record, fields_to_update, user_email):
    """
    Update the member record with validated fields
    
    Args:
        member_record (dict): Current member record
        fields_to_update (dict): Fields to update
        user_email (str): Email of user making the update
        
    Returns:
        tuple: (success, error_response, updated_record)
    """
    try:
        member_id = member_record['member_id']
        
        # Build update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in fields_to_update.items():
            if key not in ['member_id', 'updated_at']:  # Exclude protected fields
                # Use ExpressionAttributeNames for all keys to avoid reserved keyword issues
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_params = {
            'Key': {'member_id': member_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        # Perform the update
        response = table.update_item(**update_params)
        updated_record = response['Attributes']
        
        # Log successful update
        print(f"✅ Self-service update successful for {user_email}: updated fields {list(fields_to_update.keys())}")
        
        return True, None, updated_record
        
    except Exception as e:
        print(f"Error updating member record: {str(e)}")
        return False, create_error_response(500, 'Error updating member record'), None

def validate_new_member_data(user_roles, user_email, member_data):
    """
    Validate data for creating a new member record
    
    Args:
        user_roles (list): List of user's roles from JWT token
        user_email (str): User's email from JWT token
        member_data (dict): Data for new member record
        
    Returns:
        tuple: (is_valid, error_response, validated_data)
    """
    try:
        # Check if user has permission to create member records
        if 'members_self_create' not in get_user_permissions(user_roles):
            return False, create_error_response(403, 'Access denied: You do not have permission to create member records'), None
        
        # Validate required fields
        missing_fields = []
        for field in APPLICANT_REQUIRED_FIELDS:
            if field not in member_data or not member_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return False, create_error_response(400, f'Missing required fields: {", ".join(missing_fields)}'), None
        
        # Validate privacy field is provided (both 'Ja' and 'Nee' are valid)
        privacy_value = member_data.get('privacy')
        if not privacy_value or privacy_value not in ['Ja', 'Nee']:
            return False, create_error_response(400, 'Privacy keuze is verplicht (privacy moet "Ja" of "Nee" zijn)'), None
        
        # Check for forbidden fields - allow email and status for verzoek_lid users
        forbidden_fields = []
        allowed_fields = APPLICANT_ALLOWED_FIELDS.copy()
        
        # Allow email and status fields for verzoek_lid users (self-service applications)
        if 'verzoek_lid' in user_roles:
            allowed_fields.extend(['email', 'status'])
        
        for field in member_data.keys():
            if field not in allowed_fields:
                forbidden_fields.append(field)
        
        if forbidden_fields:
            return False, create_error_response(400, f'Forbidden fields for new applicants: {", ".join(forbidden_fields)}'), None
        
        # Validate conditional requirements
        age = None
        if 'geboortedatum' in member_data:
            try:
                birth_date = datetime.strptime(member_data['geboortedatum'], '%Y-%m-%d')
                age = (datetime.now() - birth_date).days // 365
            except ValueError:
                return False, create_error_response(400, 'Invalid birth date format. Use YYYY-MM-DD'), None
        
        # Check if parent/guardian name is required for minors
        if age and age < 18 and not member_data.get('minderjarigNaam'):
            return False, create_error_response(400, 'Parent/guardian name (minderjarigNaam) is required for members under 18'), None
        
        # Check if IBAN is required for direct debit
        if member_data.get('betaalwijze') == 'Incasso' and not member_data.get('bankrekeningnummer'):
            return False, create_error_response(400, 'IBAN (bankrekeningnummer) is required for direct debit payment'), None
        
        # Validate gender values
        valid_genders = ['M', 'V', 'X', 'N']
        if member_data.get('geslacht') not in valid_genders:
            return False, create_error_response(400, f'Invalid gender. Must be one of: {", ".join(valid_genders)}'), None
        
        # Build validated data with defaults
        validated_data = APPLICANT_DEFAULTS.copy()
        validated_data.update(member_data)
        
        # For verzoek_lid users, handle email and status if provided
        if 'verzoek_lid' in user_roles:
            # If email is provided, validate it matches the JWT token email
            if 'email' in member_data:
                if member_data['email'].lower() != user_email.lower():
                    return False, create_error_response(400, 'Email in form data must match your login email'), None
            else:
                # If not provided, use email from JWT token
                validated_data['email'] = user_email
            
            # If status is provided, validate it's appropriate for new applications
            if 'status' in member_data:
                valid_statuses = ['Aangemeld']  # Only allow Aangemeld for new applications
                if member_data['status'] not in valid_statuses:
                    return False, create_error_response(400, f'Invalid status for new applications. Must be one of: {", ".join(valid_statuses)}'), None
            else:
                # If not provided, set default status
                validated_data['status'] = 'Aangemeld'
        else:
            # For non-verzoek_lid users, always use email from JWT token and default status
            validated_data['email'] = user_email
            validated_data['status'] = 'Aangemeld'
        
        return True, None, validated_data
        
    except Exception as e:
        print(f"Error validating new member data: {str(e)}")
        return False, create_error_response(500, 'Error validating member data'), None

def create_new_member_record(validated_data, user_email):
    """
    Create a new member record in the database
    
    Args:
        validated_data (dict): Validated member data
        user_email (str): Email of user creating the record
        
    Returns:
        tuple: (success, error_response, created_record)
    """
    try:
        # Generate new member_id
        member_id = str(uuid.uuid4())
        
        # Add system fields
        now = datetime.now().isoformat()
        validated_data.update({
            'member_id': member_id,
            'created_at': now,
            'updated_at': now,
        })
        
        # Create the record
        table.put_item(Item=validated_data)
        
        print(f"✅ New member record created for {user_email} with member_id: {member_id}")
        
        return True, None, validated_data
        
    except Exception as e:
        print(f"Error creating member record: {str(e)}")
        return False, create_error_response(500, 'Error creating member record'), None

def update_cognito_member_id(user_email, member_id):
    """
    Update the user's Cognito profile with the new member_id
    
    Args:
        user_email (str): User's email
        member_id (str): The new member_id to store
        
    Returns:
        tuple: (success, error_message)
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = 'eu-west-1_OAT3oPCIm'  # Your user pool ID
        
        # Find the user by email
        response = cognito.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{user_email}"'
        )
        
        if not response['Users']:
            return False, f"Cognito user not found for email: {user_email}"
        
        username = response['Users'][0]['Username']
        
        # Update the custom:member_id attribute
        cognito.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'custom:member_id',
                    'Value': member_id
                }
            ]
        )
        
        print(f"✅ Updated Cognito custom:member_id for {user_email} -> {member_id}")
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to update Cognito member_id: {str(e)}"
        print(f"⚠️ {error_msg}")
        return False, error_msg

def get_user_permissions(user_roles):
    """
    Get all permissions for the given user roles
    
    Args:
        user_roles (list): List of user roles
        
    Returns:
        set: Set of permissions
    """
    # Import the role permissions mapping
    try:
        from shared.auth_utils import ROLE_PERMISSIONS
        role_permissions = ROLE_PERMISSIONS
    except ImportError:
        # Fallback role permissions
        role_permissions = {
            'hdcnLeden': ['profile_read', 'profile_update_own', 'events_read', 'products_read', 'webshop_access', 'members_self_read'],
            'verzoek_lid': ['members_self_read', 'members_self_create'],
            'Members_CRUD': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
        }
    
    permissions = set()
    for role in user_roles:
        if role in role_permissions:
            permissions.update(role_permissions[role])
    
    return permissions

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def extract_member_id_from_jwt(event):
    """
    Helper function to extract custom:member_id from JWT token
    
    This function safely extracts the member_id without interfering with
    the existing extract_user_credentials function used throughout the app.
    
    Args:
        event: Lambda event containing headers
        
    Returns:
        str or None: member_id if found, None otherwise
    """
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        # Extract and decode JWT token
        jwt_token = auth_header.replace('Bearer ', '')
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode payload (second part of JWT)
        payload_encoded = parts[1]
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        # Extract custom:member_id
        member_id = payload.get('custom:member_id')
        if member_id:
            print(f"🔍 Found custom:member_id in JWT: {member_id}")
        else:
            print(f"⚠️ No custom:member_id found in JWT token")
        
        return member_id
        
    except Exception as e:
        print(f"⚠️ Failed to extract member_id from JWT: {str(e)}")
        return None

def lambda_handler(event, context):
    """
    Get/Update member self handler - allows users to look up and update their own member record
    
    GET: Uses members_self_read permission for self-lookup functionality
    PUT: Uses members_self_read permission for self-update functionality (personal fields only)
    
    Optimized to use custom:member_id from JWT token when available for direct lookup
    """
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials using existing auth system
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Required permission for self-service operations
        if event.get('httpMethod') == 'POST':
            required_permissions = ['members_self_create']
        else:
            required_permissions = ['members_self_read']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, {'operation': 'get_member_self'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, f'{event.get("httpMethod", "GET")}_member_self')
        
        # Get the member record first (needed for GET and PUT, optional for POST)
        member_record = None
        
        # OPTIMIZATION: Try to extract custom:member_id for direct lookup
        member_id_from_token = extract_member_id_from_jwt(event)
        
        # Try direct lookup by member_id first (most efficient)
        if member_id_from_token:
            try:
                print(f"🚀 Attempting direct lookup by member_id: {member_id_from_token}")
                response = table.get_item(Key={'member_id': member_id_from_token})
                
                if 'Item' in response:
                    potential_record = response['Item']
                    
                    # Verify the member record belongs to the authenticated user
                    if potential_record.get('email', '').lower() == user_email.lower():
                        member_record = potential_record
                        print(f"✅ Direct member_id lookup successful for {user_email}")
                    else:
                        print(f"⚠️ Member record email mismatch: token={user_email}, record={potential_record.get('email')}")
                        # Continue to email lookup for security
                else:
                    print(f"⚠️ No member found with member_id: {member_id_from_token}")
                    # Continue to email lookup
                    
            except Exception as direct_lookup_error:
                print(f"⚠️ Direct member_id lookup failed: {str(direct_lookup_error)}")
                # Continue to email lookup
        
        # Fallback to email lookup if direct lookup didn't work
        if not member_record:
            print(f"🔄 Falling back to email lookup for {user_email}")
            
            # Query member by email (self-lookup only)
            try:
                # Try using GSI first (if email-index exists)
                response = table.query(
                    IndexName='email-index',
                    KeyConditionExpression='email = :email',
                    ExpressionAttributeValues={':email': user_email}
                )
                
                if response['Items']:
                    member_record = response['Items'][0]
                    print(f"✅ Email lookup successful via GSI for {user_email}")
                else:
                    print(f"⚠️ No member record found for {user_email}")
                    # For POST requests, this is expected (new member creation)
                    # For GET/PUT requests, this is an error
                    
            except Exception as gsi_error:
                print(f"GSI query failed, falling back to scan: {str(gsi_error)}")
                
                # Fallback to scan with filter
                response = table.scan(
                    FilterExpression='email = :email',
                    ExpressionAttributeValues={':email': user_email}
                )
                
                if response['Items']:
                    member_record = response['Items'][0]
                    print(f"✅ Email lookup successful via scan for {user_email}")
                else:
                    print(f"⚠️ No member record found for {user_email}")
                    # For POST requests, this is expected (new member creation)
                    # For GET/PUT requests, this is an error
        
        # Handle GET request - return member data
        if event.get('httpMethod') == 'GET':
            if not member_record:
                return create_error_response(404, 'Member record not found for your account')
            
            print(f"✅ Self-lookup successful for user {user_email} with roles {user_roles}")
            return create_success_response(member_record)
        
        # Handle PUT request - update member data
        elif event.get('httpMethod') == 'PUT':
            if not member_record:
                return create_error_response(404, 'Member record not found for your account')
            
            try:
                # Parse request body
                if not event.get('body'):
                    return create_error_response(400, 'Request body is required for updates')
                
                body = json.loads(event['body'])
                if not body:
                    return create_error_response(400, 'Request body cannot be empty')
                
                print(f"🔄 Processing self-service update for {user_email}: fields {list(body.keys())}")
                
                # Validate field permissions for self-service
                is_valid, permission_error, forbidden_fields = validate_field_permissions(
                    user_roles, user_email, member_record, body
                )
                if not is_valid:
                    return permission_error
                
                # Update the member record
                success, update_error, updated_record = update_member_self_record(
                    member_record, body, user_email
                )
                if not success:
                    return update_error
                
                print(f"✅ Self-service update completed for {user_email}")
                return create_success_response({
                    'message': 'Member record updated successfully',
                    'updated_fields': list(body.keys()),
                    'member': updated_record
                })
                
            except json.JSONDecodeError:
                return create_error_response(400, 'Invalid JSON in request body')
            except Exception as put_error:
                print(f"Error in PUT operation: {str(put_error)}")
                return create_error_response(500, 'Error updating member record')
        
        # Handle POST request - create new member record
        elif event.get('httpMethod') == 'POST':
            try:
                # Check if member record already exists
                if member_record:
                    return create_error_response(409, 'Member record already exists for your account')
                
                # Parse request body
                if not event.get('body'):
                    return create_error_response(400, 'Request body is required for member creation')
                
                body = json.loads(event['body'])
                if not body:
                    return create_error_response(400, 'Request body cannot be empty')
                
                print(f"🔄 Processing new member creation for {user_email}: fields {list(body.keys())}")
                
                # Validate new member data
                is_valid, validation_error, validated_data = validate_new_member_data(
                    user_roles, user_email, body
                )
                if not is_valid:
                    return validation_error
                
                # Create the new member record
                success, creation_error, created_record = create_new_member_record(
                    validated_data, user_email
                )
                if not success:
                    return creation_error
                
                # Update Cognito with the new member_id
                cognito_success, cognito_error = update_cognito_member_id(
                    user_email, created_record['member_id']
                )
                if not cognito_success:
                    # Log the error but don't fail the request - the member record was created successfully
                    print(f"⚠️ Member record created but Cognito update failed: {cognito_error}")
                
                print(f"✅ New member creation completed for {user_email}")
                return create_success_response({
                    'message': 'Member record created successfully',
                    'member_id': created_record['member_id'],
                    'member': created_record,
                    'cognito_updated': cognito_success
                })
                
            except json.JSONDecodeError:
                return create_error_response(400, 'Invalid JSON in request body')
            except Exception as post_error:
                print(f"Error in POST operation: {str(post_error)}")
                return create_error_response(500, 'Error creating member record')
        
        # Unsupported HTTP method
        else:
            return create_error_response(405, f'Method {event.get("httpMethod")} not allowed')
        
    except Exception as e:
        print(f"Error in get_member_self: {str(e)}")
        return create_error_response(500, 'Internal server error')