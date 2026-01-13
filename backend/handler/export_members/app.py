"""
H-DCN Member Export Lambda Function

Simple JSON export of member data for reporting purposes.
Much simpler than parquet files - just returns JSON data directly.

Features:
- Authentication via AuthLayer (Members_Read or Members_CRUD permissions)
- Regional filtering based on user roles
- Calculated fields included in response
- Standard JSON API response
"""

import json
import boto3
import os
from datetime import datetime
import logging
from decimal import Decimal

# Import authentication utilities from the AuthLayer
try:
    from shared.auth_utils import (
        extract_user_credentials, 
        validate_permissions_with_regions,
        create_success_response, 
        create_error_response,
        cors_headers,
        handle_options_request,
        log_successful_access
    )
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("export_members")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)
    )
    print("✅ Successfully imported authentication utilities from AuthLayer")
except ImportError as e:
    print(f"⚠️ Failed to import from AuthLayer: {e}")
    # Fallback authentication functions
    def extract_user_credentials(event):
        return None, None, {'statusCode': 401, 'headers': cors_headers(), 'body': json.dumps({'error': 'Authentication not available'})}
    def validate_permissions_with_regions(roles, perms, email=None, resource_context=None):
        return False, {'statusCode': 403, 'headers': cors_headers(), 'body': json.dumps({'error': 'Authorization not available'})}, None
    def create_success_response(data, status=200):
        return {'statusCode': status, 'headers': cors_headers(), 'body': json.dumps(data)}
    def create_error_response(status, msg, details=None):
        return {'statusCode': status, 'headers': cors_headers(), 'body': json.dumps({'error': msg})}
    def cors_headers():
        return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"}
    def handle_options_request():
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}
    def log_successful_access(email, roles, operation, context=None):
        print(f"ACCESS: {email} ({roles}) - {operation}")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
MEMBERS_TABLE_NAME = os.environ.get('MEMBERS_TABLE_NAME', 'Members')

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

def calculate_age(birth_date_str):
    """Calculate age from birth date string"""
    if not birth_date_str:
        return None
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    except:
        return None

def calculate_membership_years(start_date_str):
    """Calculate years of membership"""
    if not start_date_str:
        return None
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        today = datetime.now()
        years = today.year - start_date.year
        if today.month < start_date.month or (today.month == start_date.month and today.day < start_date.day):
            years -= 1
        return max(0, years)
    except:
        return None

def add_calculated_fields(member):
    """Add calculated fields to member data"""
    # Calculate age
    if member.get('geboortedatum'):
        member['leeftijd'] = calculate_age(member['geboortedatum'])
    
    # Calculate membership years
    if member.get('lid_sinds'):
        member['jaren_lid'] = calculate_membership_years(member['lid_sinds'])
    
    # Full name
    voornaam = member.get('voornaam', '').strip()
    achternaam = member.get('achternaam', '').strip()
    if voornaam and achternaam:
        member['volledige_naam'] = f"{voornaam} {achternaam}"
    elif voornaam:
        member['volledige_naam'] = voornaam
    elif achternaam:
        member['volledige_naam'] = achternaam
    else:
        member['volledige_naam'] = ''
    
    return member

def get_all_members():
    """Get all members from DynamoDB"""
    try:
        table = dynamodb.Table(MEMBERS_TABLE_NAME)
        
        # Scan all members
        response = table.scan()
        members = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            members.extend(response.get('Items', []))
        
        logger.info(f"Retrieved {len(members)} members from DynamoDB")
        
        # Convert Decimal objects and add calculated fields
        processed_members = []
        for member in members:
            # Convert Decimal objects to float
            member = decimal_to_float(member)
            # Add calculated fields
            member = add_calculated_fields(member)
            processed_members.append(member)
        
        return processed_members
        
    except Exception as e:
        logger.error(f"Error retrieving members: {str(e)}")
        raise

def apply_regional_filtering(members, user_roles):
    """Apply regional filtering based on user roles"""
    # Check if user has full access
    if any(role in user_roles for role in ['System_User_Management', 'Regio_All']):
        return members
    
    # Get user's regional access
    user_regions = []
    for role in user_roles:
        if role.startswith('Regio_') and role != 'Regio_All':
            # Extract region name (e.g., 'Regio_Noord-Holland' -> 'Noord-Holland')
            region = role.replace('Regio_', '')
            user_regions.append(region)
    
    if not user_regions:
        # No regional access specified
        return []
    
    # Filter members by region
    filtered_members = []
    for member in members:
        member_region = member.get('regio', '')
        if member_region in user_regions:
            filtered_members.append(member)
    
    logger.info(f"Regional filtering: {len(members)} -> {len(filtered_members)} members (regions: {user_regions})")
    return filtered_members

def lambda_handler(event, context):
    """
    Main Lambda handler for member data export
    
    Returns JSON array of member data with calculated fields
    """
    logger.info(f"Member export request. Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials and validate authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            logger.warning(f"Authentication failed: {auth_error}")
            return auth_error
        
        # Validate permissions - need Members_Read, Members_Export, or Members_CRUD
        # Any user with member access can export (frontend handles regional filtering)
        required_permissions = ['members_read', 'members_export']
        
        is_authorized, auth_error, regional_info = validate_permissions_with_regions(
            user_roles, 
            required_permissions, 
            user_email, 
            resource_context={'operation': 'member_export'}
        )
        
        if not is_authorized:
            logger.warning(f"Permission denied for user {user_email} with roles {user_roles}")
            return auth_error
        
        logger.info(f"✅ Authentication successful: User {user_email} with roles {user_roles} authorized for member export")
        
        # Get all members from DynamoDB
        all_members = get_all_members()
        
        # No regional filtering in backend - frontend handles filtering
        filtered_members = all_members
        
        # Log successful access for audit trail
        log_successful_access(
            user_email, 
            user_roles, 
            f"member_export",
            {
                'total_members': len(all_members),
                'exported_members': len(filtered_members),
                'filtering': 'frontend_only'
            }
        )
        
        logger.info(f"📊 AUDIT: User {user_email} (roles: {user_roles}) exported {len(filtered_members)} members (no backend filtering)")
        
        # Return member data as JSON
        return create_success_response({
            'success': True,
            'data': filtered_members,
            'metadata': {
                'total_count': len(filtered_members),
                'export_date': datetime.now().isoformat(),
                'user_email': user_email,
                'applied_filters': {
                    'regional': False  # No backend filtering - frontend handles this
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in member export: {str(e)}", exc_info=True)
        
        return create_error_response(500, 'Internal server error', {
            'message': str(e)
        })