"""
H-DCN Member Parquet Generation Lambda Function

This Lambda function generates Parquet files from DynamoDB member data for analytics 
and reporting purposes. It implements the hybrid data architecture where DynamoDB 
serves operational needs and Parquet files serve analytics.

Features:
- Loads all member data from DynamoDB
- Generates optimized Parquet files with raw member data
- Stores files in S3 with proper permissions
- Handles regional partitioning for access control
- Includes comprehensive error handling and logging

Note: Calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) 
are computed in the frontend using the existing calculatedFields.ts system to ensure 
consistency and eliminate code duplication.

Usage:
- Triggered by Members_CRUD_All users via API Gateway
- Can be scheduled for regular data refresh
- Supports filtering options for different use cases
"""

import json
import boto3
import io
from datetime import datetime
from typing import Dict, List, Any
import logging
import os
from decimal import Decimal

# Try to import pandas and pyarrow, with fallback
try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PANDAS_AVAILABLE = True
    print("✅ Successfully imported pandas and pyarrow")
except ImportError as e:
    print(f"⚠️ Failed to import pandas/pyarrow: {e}")
    PANDAS_AVAILABLE = False
    # We'll handle this in the lambda_handler

# Import authentication utilities from the AuthLayer
try:
    from shared.auth_utils import (
        extract_user_credentials, 
        validate_permissions, 
        create_success_response, 
        create_error_response,
        cors_headers,
        handle_options_request
    )
    print("✅ Successfully imported authentication utilities from AuthLayer")
except ImportError as e:
    print(f"⚠️ Failed to import from AuthLayer: {e}")
    # Fallback authentication functions
    def extract_user_credentials(event):
        return None, None, {'statusCode': 401, 'headers': cors_headers(), 'body': json.dumps({'error': 'Authentication not available'})}
    def validate_permissions(roles, perms, email=None):
        return False, {'statusCode': 403, 'headers': cors_headers(), 'body': json.dumps({'error': 'Authorization not available'})}
    def create_success_response(data, status=200):
        return {'statusCode': status, 'headers': cors_headers(), 'body': json.dumps(data)}
    def create_error_response(status, msg, details=None):
        return {'statusCode': status, 'headers': cors_headers(), 'body': json.dumps({'error': msg})}
    def cors_headers():
        return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"}
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

def create_parquet_schema() -> pa.Schema:
    """
    Define the Parquet schema for raw member data
    Ensures consistent data types and optimizes for analytics queries
    Note: Calculated fields are computed in frontend using calculatedFields.ts
    """
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

def generate_parquet_file(members: List[Dict[str, Any]], options: Dict[str, Any] = None) -> str:
    """
    Generate Parquet file from raw member data and upload to S3
    Returns the S3 key of the generated file
    """
    if not members:
        raise ValueError("No member data provided")
    
    options = options or {}
    logger.info(f"Generating Parquet file for {len(members)} members with options: {options}")
    
    # Add generation timestamp to all records
    timestamp = datetime.utcnow()
    for member in members:
        member['generated_at'] = timestamp
    
    # Apply filtering options
    filtered_members = apply_filters(members, options)
    logger.info(f"After filtering: {len(filtered_members)} members")
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(filtered_members)
    
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
    df['generated_at'] = pd.to_datetime(df['generated_at']).astype('datetime64[ms]')
    
    # Convert to PyArrow Table with schema
    schema = create_parquet_schema()
    table = pa.Table.from_pandas(df, schema=schema)
    
    # Generate S3 key with timestamp
    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
    s3_key = f"{S3_PREFIX}members_{timestamp_str}.parquet"
    
    # Write Parquet file to memory buffer
    buffer = io.BytesIO()
    pq.write_table(table, buffer, compression='snappy')
    buffer.seek(0)
    
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
        return s3_key
        
    except Exception as e:
        logger.error(f"Error uploading Parquet file to S3: {str(e)}")
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
    Requires Members_Read_All or Members_CRUD_All permissions
    """
    logger.info(f"Parquet generation started. Event: {json.dumps(event, default=str)}")
    
    # Check if pandas is available
    if not PANDAS_AVAILABLE:
        error_msg = "Pandas and PyArrow libraries are not available. Please ensure the PandasLayer is properly configured."
        logger.error(error_msg)
        return create_error_response(500, error_msg, {
            'message': 'Required analytics libraries are missing',
            'solution': 'Configure PandasLayer with pandas and pyarrow libraries'
        })
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials and validate authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            logger.warning(f"Authentication failed: {auth_error}")
            return auth_error
        
        # Validate permissions - require Members_CRUD, Members_Read, Members_Export, or System_User_Management
        required_permissions = ['Members_CRUD', 'Members_Read', 'Members_Export', 'System_User_Management']
        has_permission, permission_error = validate_permissions(
            user_roles, 
            required_permissions, 
            user_email
        )
        if not has_permission:
            logger.warning(f"Permission denied for user {user_email} with roles {user_roles}")
            return permission_error
        
        logger.info(f"✅ Authentication successful: User {user_email} with roles {user_roles} authorized for Parquet generation")
        
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
        
        # Log successful generation for audit trail
        logger.info(f"📊 AUDIT: User {user_email} (roles: {user_roles}) generated Parquet file {s3_key} with {len(members)} raw records")
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Parquet file with raw member data generated successfully',
            'data': {
                's3_bucket': S3_BUCKET_NAME,
                's3_key': s3_key,
                'record_count': len(members),
                'generated_at': datetime.utcnow().isoformat(),
                'generated_by': user_email,
                'options_applied': options,
                'format': 'parquet',
                'data_type': 'raw_member_data',
                'note': 'Calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) are computed in frontend'
            }
        }
        
        logger.info(f"Parquet generation completed successfully: {s3_key}")
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error in Parquet generation: {str(e)}", exc_info=True)
        
        return create_error_response(500, 'Internal server error', {
            'message': str(e)
        })