"""
H-DCN Member Parquet Generation Lambda Function

This Lambda function generates Parquet files from DynamoDB member data for analytics 
and reporting purposes. It implements the hybrid data architecture where DynamoDB 
serves operational needs and Parquet files serve analytics.

ARCHITECTURE: Any user with member permissions can generate/download full parquet file,
frontend handles regional filtering based on user's region roles.

Features:
- Loads all member data from DynamoDB
- Generates optimized Parquet files with raw member data
- Stores files in S3 with proper permissions
- Provides full dataset to any user with member permissions
- Frontend applies regional filtering based on user's region roles
- Includes comprehensive error handling and logging

Note: Calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) 
are computed in the frontend using the existing calculatedFields.ts system to ensure 
consistency and eliminate code duplication.

Usage:
- Triggered by users with any member permission + region role via API Gateway
- Can be scheduled for regular data refresh
- Supports filtering options for different use cases
- Full parquet file provided, regional filtering handled in frontend
"""

import json
import boto3
import io
from datetime import datetime
from typing import Dict, List, Any
import logging
import os
from decimal import Decimal

# Try to import pandas and pyarrow, with comprehensive error handling
try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PANDAS_AVAILABLE = True
    PANDAS_ERROR = None
    print("✅ Successfully imported pandas and pyarrow")
except ImportError as e:
    print(f"⚠️ Failed to import pandas/pyarrow: {e}")
    PANDAS_AVAILABLE = False
    PANDAS_ERROR = str(e)
    # Create fallback variables to prevent NameError
    pd = None
    pa = None
    pq = None
except Exception as e:
    print(f"❌ Unexpected error importing pandas/pyarrow: {e}")
    PANDAS_AVAILABLE = False
    PANDAS_ERROR = f"Unexpected import error: {str(e)}"
    pd = None
    pa = None
    pq = None

# Import authentication utilities from the AuthLayer with enhanced error handling
AUTH_AVAILABLE = False
AUTH_ERROR = None
try:
    from shared.auth_utils import (
        extract_user_credentials, 
        validate_permissions, 
        validate_permissions_with_regions,
        log_successful_access,
        create_success_response, 
        create_error_response,
        cors_headers,
        handle_options_request
    )
    AUTH_AVAILABLE = True
    print("✅ Successfully imported authentication utilities from AuthLayer")
except ImportError as e:
    print(f"⚠️ Failed to import from AuthLayer: {e}")
    AUTH_AVAILABLE = False
    AUTH_ERROR = f"AuthLayer import failed: {str(e)}"
    # Fallback authentication functions with detailed error messages
    def extract_user_credentials(event):
        return None, None, {
            'statusCode': 401, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authentication system not available',
                'details': 'AuthLayer could not be loaded in Docker container',
                'auth_error': AUTH_ERROR,
                'solution': 'Ensure shared auth layer is properly deployed and accessible'
            })
        }
    def validate_permissions(roles, perms, email=None):
        return False, {
            'statusCode': 403, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authorization system not available',
                'details': 'AuthLayer validation functions not accessible',
                'auth_error': AUTH_ERROR
            })
        }
    def validate_permissions_with_regions(roles, perms, email=None, context=None):
        return False, {
            'statusCode': 403, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authorization system not available',
                'details': 'AuthLayer regional validation not accessible',
                'auth_error': AUTH_ERROR
            })
        }, None
    def log_successful_access(user_email, user_roles, operation, resource_context=None):
        print(f"⚠️ Audit log not available - would have logged: {user_email}, {operation}")
    def create_success_response(data, status=200):
        return {
            'statusCode': status, 
            'headers': cors_headers(),
            'body': json.dumps(data)
        }
    def create_error_response(status, msg, details=None):
        return {
            'statusCode': status, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': msg, 
                'details': details,
                'auth_system_status': 'unavailable'
            })
        }
    def cors_headers():
        return {
            "Access-Control-Allow-Origin": "*", 
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS", 
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
        }
    def handle_options_request():
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}
except Exception as e:
    print(f"❌ Unexpected error importing AuthLayer: {e}")
    AUTH_AVAILABLE = False
    AUTH_ERROR = f"Unexpected auth import error: {str(e)}"
    # Same fallback functions as ImportError case
    def extract_user_credentials(event):
        return None, None, {
            'statusCode': 401, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authentication system failure',
                'details': 'Unexpected error loading AuthLayer in Docker container',
                'auth_error': AUTH_ERROR,
                'solution': 'Check Docker container configuration and auth layer deployment'
            })
        }
    def validate_permissions(roles, perms, email=None):
        return False, {
            'statusCode': 403, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authorization system failure',
                'details': 'Unexpected error in AuthLayer validation',
                'auth_error': AUTH_ERROR
            })
        }
    def validate_permissions_with_regions(roles, perms, email=None, context=None):
        return False, {
            'statusCode': 403, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Authorization system failure',
                'details': 'Unexpected error in AuthLayer regional validation',
                'auth_error': AUTH_ERROR
            })
        }, None
    def log_successful_access(user_email, user_roles, operation, resource_context=None):
        print(f"⚠️ Audit log not available - would have logged: {user_email}, {operation}")
    def create_success_response(data, status=200):
        return {
            'statusCode': status, 
            'headers': cors_headers(),
            'body': json.dumps(data)
        }
    def create_error_response(status, msg, details=None):
        return {
            'statusCode': status, 
            'headers': cors_headers(),
            'body': json.dumps({
                'error': msg, 
                'details': details,
                'auth_system_status': 'failed'
            })
        }
    def cors_headers():
        return {
            "Access-Control-Allow-Origin": "*", 
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS", 
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
        }
    def handle_options_request():
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Environment variables
MEMBERS_TABLE_NAME = os.environ.get('MEMBERS_TABLE_NAME', 'Members')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'my-hdcn-bucket')
S3_PREFIX = os.environ.get('S3_PREFIX', 'analytics/parquet/members/')

def convert_dynamodb_to_python(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DynamoDB item to Python native types
    Handles Decimal conversion and other DynamoDB-specific types
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
            converted[key] = [convert_dynamodb_to_python(v) if isinstance(v, dict) else v for v in value]
        else:
            converted[key] = value
    return converted

def load_members_from_dynamodb() -> List[Dict[str, Any]]:
    """
    Load all member records from DynamoDB
    Returns list of raw member dictionaries (no calculated fields)
    """
    logger.info(f"Loading members from DynamoDB table: {MEMBERS_TABLE_NAME}")
    
    try:
        table = dynamodb.Table(MEMBERS_TABLE_NAME)
        
        # Scan all members (for 1500 members this is acceptable)
        response = table.scan()
        members = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            members.extend(response['Items'])
        
        logger.info(f"Loaded {len(members)} members from DynamoDB")
        
        # Convert DynamoDB types to Python native types
        converted_members = [convert_dynamodb_to_python(member) for member in members]
        
        logger.info(f"Converted {len(converted_members)} members to Python native types")
        return converted_members
        
    except Exception as e:
        logger.error(f"Error loading members from DynamoDB: {str(e)}")
        raise

def create_parquet_schema():
    """
    Define the Parquet schema for raw member data
    Ensures consistent data types and optimizes for analytics queries
    Note: Calculated fields are computed in frontend using calculatedFields.ts
    """
    if not PANDAS_AVAILABLE:
        error_details = {
            'error': 'PyArrow library not available',
            'pandas_error': PANDAS_ERROR,
            'required_libraries': ['pandas', 'pyarrow'],
            'solution': 'Ensure PandasLayer is properly configured in Docker container',
            'docker_context': True
        }
        logger.error(f"Schema creation failed: {error_details}")
        raise RuntimeError(f"PyArrow is required for schema creation but is not available. Details: {PANDAS_ERROR}")
    
    if pa is None:
        error_details = {
            'error': 'PyArrow module is None after import',
            'pandas_available': PANDAS_AVAILABLE,
            'pandas_error': PANDAS_ERROR,
            'solution': 'Check PyArrow installation in Docker container'
        }
        logger.error(f"Schema creation failed: {error_details}")
        raise RuntimeError("PyArrow module is None - library import may have failed partially")
    
    try:
        return pa.schema([
            # Core member fields - lidnummer as string since it comes from DynamoDB as string
            ('lidnummer', pa.string()),
            ('voornaam', pa.string()),
            ('tussenvoegsel', pa.string()),
            ('achternaam', pa.string()),
            ('geboortedatum', pa.string()),
            ('tijdstempel', pa.string()),
            ('status', pa.string()),
            ('regio', pa.string()),
            ('lidmaatschap', pa.string()),
            ('clubblad', pa.string()),
            
            # Contact information
            ('email', pa.string()),
            ('telefoon', pa.string()),
            ('straat', pa.string()),
            ('postcode', pa.string()),
            ('woonplaats', pa.string()),
            ('land', pa.string()),
            
            # Additional member fields that may exist in DynamoDB
            ('motor_merk', pa.string()),
            ('motor_type', pa.string()),
            ('motor_bouwjaar', pa.string()),
            ('motor_kenteken', pa.string()),
            
            # Metadata
            ('generated_at', pa.timestamp('ms')),
        ])
    except Exception as e:
        error_details = {
            'error': 'PyArrow schema creation failed',
            'exception': str(e),
            'pandas_available': PANDAS_AVAILABLE,
            'pyarrow_available': pa is not None,
            'solution': 'Check PyArrow version compatibility in Docker container'
        }
        logger.error(f"Schema creation failed: {error_details}")
        raise RuntimeError(f"Failed to create PyArrow schema: {str(e)}")

def cleanup_old_parquet_files(exclude_key: str = None):
    """
    Clean up old Parquet files in S3, excluding the specified key
    This ensures we don't accumulate old files and the download API always serves the latest
    
    Args:
        exclude_key: S3 key to exclude from deletion (the newly created file)
    """
    try:
        logger.info(f"Cleaning up old Parquet files in s3://{S3_BUCKET_NAME}/{S3_PREFIX}")
        
        # List all objects in the analytics/parquet/members/ prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=S3_PREFIX
        )
        
        if 'Contents' not in response:
            logger.info("No existing Parquet files found to clean up")
            return
        
        # Get all parquet files except the one we want to keep
        parquet_files = [
            obj for obj in response['Contents'] 
            if obj['Key'].endswith('.parquet') and obj['Key'] != exclude_key
        ]
        
        if not parquet_files:
            logger.info("No old Parquet files found to clean up")
            return
        
        logger.info(f"Found {len(parquet_files)} old Parquet files to delete")
        
        # Delete all old parquet files
        delete_objects = [{'Key': obj['Key']} for obj in parquet_files]
        
        if delete_objects:
            s3_client.delete_objects(
                Bucket=S3_BUCKET_NAME,
                Delete={
                    'Objects': delete_objects,
                    'Quiet': True
                }
            )
            
            deleted_files = [obj['Key'] for obj in delete_objects]
            logger.info(f"Successfully deleted {len(deleted_files)} old Parquet files: {deleted_files}")
        
    except Exception as e:
        logger.error(f"Error cleaning up old Parquet files: {str(e)}")
        # Don't fail the entire process if cleanup fails
        pass

def generate_parquet_file(members: List[Dict[str, Any]], options: Dict[str, Any] = None) -> str:
    """
    Generate Parquet file from raw member data and upload to S3
    Returns the S3 key of the generated file
    """
    if not PANDAS_AVAILABLE:
        error_details = {
            'error': 'Pandas and PyArrow libraries not available',
            'pandas_error': PANDAS_ERROR,
            'required_libraries': ['pandas', 'pyarrow'],
            'solution': 'Ensure PandasLayer is properly configured in Docker container',
            'docker_context': True,
            'member_count': len(members) if members else 0
        }
        logger.error(f"Parquet generation failed: {error_details}")
        raise RuntimeError(f"Pandas and PyArrow libraries are required but not available. Details: {PANDAS_ERROR}")
    
    if pd is None or pa is None or pq is None:
        error_details = {
            'error': 'One or more required modules are None after import',
            'pandas_available': pd is not None,
            'pyarrow_available': pa is not None,
            'parquet_available': pq is not None,
            'pandas_error': PANDAS_ERROR,
            'solution': 'Check library installation and import process in Docker container'
        }
        logger.error(f"Parquet generation failed: {error_details}")
        raise RuntimeError("Required modules (pandas/pyarrow/parquet) are None - library imports may have failed partially")
    
    if not members:
        raise ValueError("No member data provided for Parquet generation")
    
    options = options or {}
    logger.info(f"Generating Parquet file for {len(members)} members with options: {options}")
    
    try:
        # Add generation timestamp to all records
        timestamp = datetime.utcnow()
        for member in members:
            member['generated_at'] = timestamp
        
        # Apply filtering options
        filtered_members = apply_filters(members, options)
        logger.info(f"After filtering: {len(filtered_members)} members")
        
        # Convert to pandas DataFrame
        try:
            df = pd.DataFrame(filtered_members)
        except Exception as e:
            error_details = {
                'error': 'Failed to create pandas DataFrame',
                'exception': str(e),
                'member_count': len(filtered_members),
                'solution': 'Check data format and pandas installation'
            }
            logger.error(f"DataFrame creation failed: {error_details}")
            raise RuntimeError(f"Failed to create pandas DataFrame: {str(e)}")
        
        # Ensure all expected columns exist with proper defaults
        expected_columns = [
            'lidnummer', 'voornaam', 'tussenvoegsel', 'achternaam', 'geboortedatum',
            'tijdstempel', 'status', 'regio', 'lidmaatschap', 'clubblad',
            'email', 'telefoon', 'straat', 'postcode', 'woonplaats', 'land',
            'motor_merk', 'motor_type', 'motor_bouwjaar', 'motor_kenteken',
            'generated_at'
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ''    # All columns are strings except generated_at
        
        # Reorder columns to match schema
        df = df[expected_columns]
        
        # Convert timestamp to milliseconds for PyArrow compatibility
        try:
            df['generated_at'] = pd.to_datetime(df['generated_at']).astype('datetime64[ms]')
        except Exception as e:
            error_details = {
                'error': 'Failed to convert timestamp for PyArrow',
                'exception': str(e),
                'solution': 'Check pandas datetime conversion compatibility'
            }
            logger.error(f"Timestamp conversion failed: {error_details}")
            raise RuntimeError(f"Failed to convert timestamp for PyArrow: {str(e)}")
        
        # Convert to PyArrow Table with schema
        try:
            schema = create_parquet_schema()
            table = pa.Table.from_pandas(df, schema=schema)
        except Exception as e:
            error_details = {
                'error': 'Failed to create PyArrow table',
                'exception': str(e),
                'dataframe_shape': df.shape if 'df' in locals() else 'unknown',
                'solution': 'Check PyArrow compatibility and data types'
            }
            logger.error(f"PyArrow table creation failed: {error_details}")
            raise RuntimeError(f"Failed to create PyArrow table: {str(e)}")
        
        # Generate S3 key with timestamp
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        s3_key = f"{S3_PREFIX}members_{timestamp_str}.parquet"
        
        # Write Parquet file to memory buffer
        buffer = io.BytesIO()
        try:
            pq.write_table(table, buffer, compression='snappy')
            buffer.seek(0)
        except Exception as e:
            error_details = {
                'error': 'Failed to write Parquet data to buffer',
                'exception': str(e),
                'table_schema': str(table.schema) if 'table' in locals() else 'unknown',
                'solution': 'Check PyArrow parquet writer compatibility'
            }
            logger.error(f"Parquet writing failed: {error_details}")
            raise RuntimeError(f"Failed to write Parquet data: {str(e)}")
        
        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/octet-stream',
                Metadata={
                    'generated_at': timestamp.isoformat(),
                    'record_count': str(len(filtered_members)),
                    'source': 'hdcn-member-parquet-generator',
                    'version': '2.0',
                    'data_type': 'raw_member_data'
                }
            )
            
            logger.info(f"Successfully uploaded Parquet file to s3://{S3_BUCKET_NAME}/{s3_key}")
            
            # Clean up old Parquet files after successful upload
            cleanup_old_parquet_files(exclude_key=s3_key)
            
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading Parquet file to S3: {str(e)}")
            raise
            
    except Exception as e:
        # Log comprehensive error details for debugging
        error_details = {
            'error': 'Parquet generation process failed',
            'exception': str(e),
            'pandas_available': PANDAS_AVAILABLE,
            'pandas_error': PANDAS_ERROR,
            'member_count': len(members) if members else 0,
            'options': options,
            'docker_context': True
        }
        logger.error(f"Complete parquet generation failed: {error_details}")
        raise

def apply_filters(members: List[Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Apply filtering options to member data
    Supports various filtering criteria for different use cases
    """
    filtered = members.copy()
    
    # Filter by active status only
    if options.get('activeOnly', False):
        filtered = [m for m in filtered if m.get('status') == 'Actief']
    
    # Filter by members with motor information
    if options.get('withMotors', False):
        filtered = [m for m in filtered if m.get('motor_merk') or m.get('motor_type')]
    
    # Date range filtering
    if options.get('dateRange'):
        date_range = options['dateRange']
        from_date = date_range.get('from')
        to_date = date_range.get('to')
        
        if from_date or to_date:
            filtered = filter_by_date_range(filtered, from_date, to_date)
    
    # Regional filtering (for regional administrators)
    if options.get('region'):
        region = options['region']
        filtered = [m for m in filtered if m.get('regio') == region]
    
    # Anonymization (remove PII for external analysis)
    if options.get('anonymize', False):
        filtered = anonymize_member_data(filtered)
    
    return filtered

def filter_by_date_range(members: List[Dict[str, Any]], from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Filter members by tijdstempel (membership start date) range"""
    filtered = []
    
    for member in members:
        tijdstempel = member.get('tijdstempel')
        if not tijdstempel:
            continue
        
        try:
            member_date = datetime.strptime(tijdstempel, '%Y-%m-%d').date()
            
            include = True
            if from_date:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                if member_date < from_date_obj:
                    include = False
            
            if to_date and include:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                if member_date > to_date_obj:
                    include = False
            
            if include:
                filtered.append(member)
                
        except (ValueError, TypeError):
            # Skip members with invalid dates
            continue
    
    return filtered

def anonymize_member_data(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Anonymize sensitive personal information for external analysis
    Keeps statistical relevance while protecting privacy
    """
    anonymized = []
    
    for member in members:
        anon_member = member.copy()
        
        # Remove direct identifiers
        anon_member['voornaam'] = 'ANON'
        anon_member['achternaam'] = 'MEMBER'
        anon_member['tussenvoegsel'] = ''
        anon_member['email'] = ''
        anon_member['telefoon'] = ''
        anon_member['straat'] = ''
        
        # Keep statistical fields (geboortedatum, tijdstempel, regio, lidmaatschap, etc.)
        # These are needed for analytics but don't identify individuals
        # Calculated fields will be computed in frontend from these raw fields
        
        anonymized.append(anon_member)
    
    return anonymized

def lambda_handler(event, context):
    """
    Main Lambda handler for Parquet generation
    Supports both API Gateway requests and direct invocation
    
    ARCHITECTURE: Only Members_CRUD users can generate parquet files
    
    Required permissions: Members_CRUD + region role combination
    """
    logger.info(f"Parquet generation started. Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials and validate authentication FIRST
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            # Enhanced authentication error logging for Docker container context
            auth_error_details = {
                'authentication_failed': True,
                'auth_system_available': AUTH_AVAILABLE,
                'auth_error': AUTH_ERROR if not AUTH_AVAILABLE else 'Authentication validation failed',
                'docker_context': True,
                'troubleshooting': {
                    'check_auth_layer': 'Verify shared auth layer is accessible in Docker container',
                    'check_jwt_token': 'Verify JWT token is properly formatted and valid',
                    'check_headers': 'Verify Authorization header is present and correct',
                    'check_permissions': 'Verify user has required roles for this operation'
                }
            }
            logger.warning(f"Authentication failed in Docker container: {auth_error_details}")
            
            # If auth system is not available, enhance the error response
            if not AUTH_AVAILABLE:
                enhanced_auth_error = auth_error.copy()
                if 'body' in enhanced_auth_error:
                    try:
                        body_data = json.loads(enhanced_auth_error['body'])
                        body_data.update(auth_error_details)
                        enhanced_auth_error['body'] = json.dumps(body_data)
                    except (json.JSONDecodeError, KeyError):
                        pass
                return enhanced_auth_error
            
            return auth_error
        
        # Validate permissions using enhanced validation with regional support
        # CRITICAL REQUIREMENT: Only Members_CRUD can generate parquet files
        # Members_Read and Members_Export should NOT be able to generate parquet files
        
        # First check if user has Members_CRUD role specifically
        has_members_crud = 'Members_CRUD' in user_roles
        has_system_admin = any(role in user_roles for role in ['System_CRUD', 'System_User_Management'])
        
        logger.info(f"🔍 PERMISSION CHECK: User {user_email} with roles {user_roles}")
        logger.info(f"🔍 Has Members_CRUD: {has_members_crud}")
        logger.info(f"🔍 Has System Admin: {has_system_admin}")
        
        if not (has_members_crud or has_system_admin):
            permission_error_details = {
                'permission_denied': True,
                'required_roles': ['Members_CRUD', 'System_CRUD', 'System_User_Management'],
                'user_roles': user_roles,
                'user_email': user_email,
                'operation': 'parquet_generation',
                'docker_context': True,
                'auth_system_available': AUTH_AVAILABLE,
                'troubleshooting': {
                    'verify_roles': 'Check user has Members_CRUD or System admin roles in Cognito',
                    'verify_jwt': 'Verify JWT token contains correct group claims',
                    'verify_mapping': 'Check role mapping in authentication system',
                    'contact_admin': 'Contact system administrator to assign required roles'
                }
            }
            logger.warning(f"Permission denied for parquet generation: {permission_error_details}")
            return create_error_response(403, 'Access denied: Parquet generation requires Members_CRUD permissions', permission_error_details)
        
        # Now validate regional access - only for Members_CRUD users
        # CRITICAL: Parquet generation requires Regio_All (national access), not regional access
        # This is because parquet files contain full dataset, regional filtering happens in frontend
        if not has_system_admin and 'Regio_All' not in user_roles:
            regional_error_details = {
                'regional_access_denied': True,
                'required_structure': 'Members_CRUD + Regio_All (national access required)',
                'user_roles': user_roles,
                'user_email': user_email,
                'reason': 'Parquet files contain full dataset, regional filtering handled in frontend',
                'docker_context': True,
                'troubleshooting': {
                    'verify_regio_all': 'Check user has Regio_All role in Cognito for national access',
                    'understand_architecture': 'Parquet generation requires national access, frontend handles regional filtering',
                    'contact_admin': 'Contact system administrator to assign Regio_All role',
                    'alternative': 'Use regional export features instead of parquet generation'
                }
            }
            logger.warning(f"Regional access denied for parquet generation: {regional_error_details}")
            return create_error_response(403, 'Access denied: Parquet generation requires national access', regional_error_details)
        
        # Check if pandas is available AFTER authentication passes
        if not PANDAS_AVAILABLE:
            error_details = {
                'error': 'Required analytics libraries not available',
                'pandas_error': PANDAS_ERROR,
                'required_libraries': ['pandas', 'pyarrow'],
                'docker_context': True,
                'solution': 'Ensure PandasLayer is properly configured in Docker container',
                'troubleshooting': {
                    'check_layer': 'Verify PandasLayer is attached to Lambda function',
                    'check_imports': 'Verify pandas and pyarrow are installed in layer',
                    'check_permissions': 'Verify Lambda has access to layer resources',
                    'check_memory': 'Ensure sufficient memory allocation for pandas operations'
                }
            }
            logger.error(f"Pandas/PyArrow not available: {error_details}")
            return create_error_response(500, 'Analytics libraries not available', error_details)
        
        # Determine regional access info
        regional_info = {
            'has_full_access': 'Regio_All' in user_roles or has_system_admin,
            'allowed_regions': ['all'] if ('Regio_All' in user_roles or has_system_admin) else [role.replace('Regio_', '') for role in region_roles],
            'access_type': 'admin' if has_system_admin else ('national' if 'Regio_All' in user_roles else 'regional')
        }
        
        # Log successful authorization with regional access info
        logger.info(f"✅ Authorization successful: User {user_email} with roles {user_roles}")
        logger.info(f"✅ Regional access: {regional_info}")
        
        # Store regional info for potential filtering (if needed in future)
        user_regional_access = regional_info
        
        logger.info(f"✅ Authentication successful: User {user_email} with roles {user_roles} authorized for Parquet generation")
        
        # Log successful access for audit trail
        log_successful_access(
            user_email=user_email,
            user_roles=user_roles,
            operation='parquet_generation',
            resource_context={
                'regional_access': regional_info,
                'operation_type': 'member_data_export'
            }
        )
        
        # Parse request body for options
        options = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
                options = body.get('options', {})
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in request body, using default options")
        
        # Load member data from DynamoDB
        members = load_members_from_dynamodb()
        
        if not members:
            return create_error_response(404, 'No member data found', {
                'message': 'The Members table appears to be empty'
            })
        
        # Generate Parquet file
        s3_key = generate_parquet_file(members, options)
        
        # Log successful generation for audit trail with regional access info
        logger.info(f"📊 AUDIT: User {user_email} (roles: {user_roles}) generated Parquet file {s3_key} with {len(members)} raw records")
        logger.info(f"📊 AUDIT: Regional access info: {user_regional_access}")
        
        # Log detailed audit information
        log_successful_access(
            user_email=user_email,
            user_roles=user_roles,
            operation='parquet_file_generated',
            resource_context={
                's3_key': s3_key,
                'record_count': len(members),
                'regional_access': user_regional_access,
                'options_applied': options,
                'data_type': 'raw_member_data'
            }
        )
        
        # Prepare response with regional access information
        response_data = {
            'success': True,
            'message': 'Parquet file with raw member data generated successfully',
            'data': {
                's3_bucket': S3_BUCKET_NAME,
                's3_key': s3_key,
                'record_count': len(members),
                'generated_at': datetime.utcnow().isoformat(),
                'generated_by': user_email,
                'regional_access': user_regional_access,
                'options_applied': options,
                'format': 'parquet',
                'data_type': 'raw_member_data',
                'note': 'Calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) are computed in frontend'
            }
        }
        
        logger.info(f"Parquet generation completed successfully: {s3_key}")
        
        return create_success_response(response_data)
        
    except Exception as e:
        # Enhanced error handling for Docker container context
        error_details = {
            'error': 'Internal server error in Docker container',
            'exception': str(e),
            'exception_type': type(e).__name__,
            'docker_context': True,
            'pandas_available': PANDAS_AVAILABLE,
            'pandas_error': PANDAS_ERROR,
            'auth_available': AUTH_AVAILABLE,
            'auth_error': AUTH_ERROR,
            'troubleshooting': {
                'check_logs': 'Review CloudWatch logs for detailed error information',
                'check_dependencies': 'Verify all required libraries are available in Docker container',
                'check_permissions': 'Verify Lambda execution role has required permissions',
                'check_environment': 'Verify environment variables are properly configured',
                'check_memory': 'Ensure sufficient memory allocation for pandas operations'
            }
        }
        
        logger.error(f"Error in Docker container Parquet generation: {error_details}", exc_info=True)
        
        # Provide specific error messages based on error type
        if 'pandas' in str(e).lower() or 'pyarrow' in str(e).lower():
            error_details['specific_issue'] = 'Analytics library error'
            error_details['solution'] = 'Check PandasLayer configuration and library versions'
        elif 'auth' in str(e).lower() or 'permission' in str(e).lower():
            error_details['specific_issue'] = 'Authentication/authorization error'
            error_details['solution'] = 'Check user permissions and authentication system'
        elif 'dynamodb' in str(e).lower():
            error_details['specific_issue'] = 'Database access error'
            error_details['solution'] = 'Check DynamoDB permissions and table configuration'
        elif 's3' in str(e).lower():
            error_details['specific_issue'] = 'S3 storage error'
            error_details['solution'] = 'Check S3 permissions and bucket configuration'
        
        return create_error_response(500, 'Internal server error in Docker container', error_details)