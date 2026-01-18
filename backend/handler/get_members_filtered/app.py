"""
Regional Filtering Lambda Handler for Member Reporting Performance

This handler implements backend regional filtering to improve member reporting performance.
It replaces the S3 Parquet system with a simpler, faster approach:
- Filters members by user's regional permissions BEFORE sending to frontend
- Returns only data the user is authorized to access
- Frontend caches in browser session storage

Key Features:
- JWT-based authentication and authorization
- Regional permission validation (Regio_All or Regio_xxxx)
- DynamoDB scan with Decimal conversion for JSON serialization
- No status filtering (returns all statuses for authorized regions)
- Comprehensive error handling and logging

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal

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
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_members_filtered")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
MEMBERS_TABLE_NAME = 'Members'
table = dynamodb.Table(MEMBERS_TABLE_NAME)


def convert_dynamodb_to_python(item):
    """
    Convert DynamoDB item to Python native types
    
    CRITICAL: Handles Decimal conversion to avoid JSON serialization errors
    DynamoDB returns numbers as Decimal objects which cannot be JSON serialized.
    This function converts Decimals to int or float as appropriate.
    
    Args:
        item: DynamoDB item dictionary
        
    Returns:
        Dictionary with Python native types
        
    Requirements: 1.5
    """
    converted = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            # Convert Decimal to int or float
            if value % 1 == 0:
                converted[key] = int(value)
            else:
                converted[key] = float(value)
        elif isinstance(value, dict):
            converted[key] = convert_dynamodb_to_python(value)
        elif isinstance(value, list):
            converted[key] = [
                convert_dynamodb_to_python(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            converted[key] = value
    return converted


def load_members_from_dynamodb():
    """
    Scan all members from DynamoDB with pagination support
    
    Returns:
        List of member dictionaries with Python native types
        
    Requirements: 1.4, 1.5
    """
    try:
        print(f"[LOAD_MEMBERS] Starting DynamoDB scan of table: {MEMBERS_TABLE_NAME}")
        start_time = datetime.now()
        
        response = table.scan()
        members = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            print(f"[LOAD_MEMBERS] Paginating... Current count: {len(members)}")
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            members.extend(response['Items'])
        
        # CRITICAL: Convert Decimal types to int/float for JSON serialization
        members = [convert_dynamodb_to_python(member) for member in members]
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"[LOAD_MEMBERS] Loaded {len(members)} members in {elapsed:.2f}s")
        
        return members
        
    except Exception as e:
        print(f"[LOAD_MEMBERS] Error loading members from DynamoDB: {str(e)}")
        raise


def filter_members_by_region(members, regional_info):
    """
    Filter members based on user's regional permissions
    
    Regional users only see members from their assigned region.
    Regio_All users see all members from all regions.
    
    IMPORTANT: No status filtering is applied. All statuses are included
    (Actief, Inactief, Opgezegd, Verwijderd, etc.) for authorized regions.
    
    Args:
        members: List of all member dictionaries
        regional_info: Dict with regional access information from auth layer
                      Example: {'region': 'Utrecht', 'has_full_access': False}
                      Example: {'region': 'All', 'has_full_access': True}
        
    Returns:
        List of filtered member dictionaries
        
    Requirements: 1.2, 1.3
    """
    # Regio_All users get all members (no filtering)
    if regional_info.get('has_full_access', False):
        print(f"[FILTER] User has full access - returning all {len(members)} members")
        return members
    
    # Extract allowed regions from regional_info
    allowed_regions = regional_info.get('allowed_regions', [])
    
    # If 'all' is in allowed_regions, return all members
    if 'all' in [r.lower() for r in allowed_regions]:
        print(f"[FILTER] User has 'all' in allowed_regions - returning all {len(members)} members")
        return members
    
    # Regional users get only their region's members
    if not allowed_regions:
        print(f"[FILTER] No allowed regions found - returning empty list")
        return []
    
    print(f"[FILTER] Filtering members for regions: {allowed_regions}")
    
    filtered = [
        m for m in members
        if m.get('regio') in allowed_regions
    ]
    
    print(f"[FILTER] Filtered {len(members)} members to {len(filtered)} members for regions: {allowed_regions}")
    
    return filtered


def lambda_handler(event, context):
    """
    Main handler for regional member data API
    
    Endpoint: GET /api/members
    
    Authentication: JWT token required in Authorization header
    Authorization: Any member permission required (members_read, members_export, 
                   members_create, members_update, members_delete)
    
    Response:
        Success (200):
            {
                "success": true,
                "data": [...member objects...],
                "metadata": {
                    "total_count": 187,
                    "region": "Utrecht",
                    "timestamp": "2026-01-17T10:30:00Z"
                }
            }
        
        Error (401/403/500):
            {
                "error": "Error message",
                "details": "Additional details"
            }
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    try:
        print(f"[HANDLER] Regional filtering API called - Method: {event.get('httpMethod')}")
        
        # Handle OPTIONS request for CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # 1. Extract user credentials from JWT
        print("[HANDLER] Step 1: Extracting user credentials")
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            print(f"[HANDLER] Authentication failed for request")
            return auth_error
        
        print(f"[HANDLER] User authenticated: {user_email}, Roles: {user_roles}")
        
        # 2. Validate permissions (any member permission required)
        print("[HANDLER] Step 2: Validating permissions")
        required_permissions = [
            'members_read',
            'members_export',
            'members_create',
            'members_update',
            'members_delete'
        ]
        
        is_authorized, auth_error, regional_info = validate_permissions_with_regions(
            user_roles,
            required_permissions,
            user_email,
            {'operation': 'get_members_filtered'}
        )
        
        if not is_authorized:
            print(f"[HANDLER] Authorization failed for user: {user_email}")
            return auth_error
        
        print(f"[HANDLER] User authorized: {user_email}, Regional info: {regional_info}")
        
        # 3. Load all members from DynamoDB
        print("[HANDLER] Step 3: Loading members from DynamoDB")
        members = load_members_from_dynamodb()
        
        # 4. Filter by user's region
        print("[HANDLER] Step 4: Filtering members by region")
        filtered_members = filter_members_by_region(members, regional_info)
        
        # 5. Prepare response metadata
        region_display = 'All' if regional_info.get('has_full_access', False) else ', '.join(regional_info.get('allowed_regions', []))
        
        metadata = {
            'total_count': len(filtered_members),
            'region': region_display,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # 6. Log successful access
        log_successful_access(
            user_email,
            user_roles,
            'get_members_filtered',
            {
                'regional_access': regional_info,
                'members_returned': len(filtered_members),
                'total_members': len(members)
            }
        )
        
        print(f"[HANDLER] Success: Returning {len(filtered_members)} members to user {user_email}")
        
        # 7. Return filtered data
        return create_success_response({
            'success': True,
            'data': filtered_members,
            'metadata': metadata
        })
        
    except Exception as e:
        print(f"[HANDLER] Error in get_members_filtered: {str(e)}")
        import traceback
        print(f"[HANDLER] Traceback: {traceback.format_exc()}")
        
        return create_error_response(
            500,
            'Internal server error',
            {
                'details': 'Failed to load member data',
                'error_type': type(e).__name__
            }
        )
