"""
H-DCN Parquet Download Lambda Function

This Lambda function provides secure access to generated Parquet files for users with
any member permissions. It handles authentication, serves parquet files through API Gateway,
and follows the architecture where any user with member permissions can download the full
parquet file, with regional filtering handled in the frontend.

ARCHITECTURE: Any user with member permissions can download full parquet file,
frontend handles regional filtering based on user's region roles.

Features:
- Authentication via AuthLayer (any member permission + region role)
- Secure S3 file access through API proxy
- Proper CORS headers for frontend integration
- Audit logging for file access
- Support for both direct download and pre-signed URLs

Usage:
- GET /analytics/download-parquet/{filename}
- Requires valid JWT token with any member permission + region role
- Returns parquet file content or pre-signed URL
- Frontend applies regional filtering based on user's region roles
"""

import json
import boto3
import base64
import os
from datetime import datetime
import logging

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
s3_client = boto3.client('s3')

# Environment variables
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'my-hdcn-bucket')
S3_PREFIX = os.environ.get('S3_PREFIX', 'analytics/parquet/members/')

def get_latest_parquet_file():
    """
    Get the latest (most recently created) Parquet file from S3
    
    Returns:
        tuple: (success, s3_key_or_error)
    """
    try:
        logger.info(f"Looking for latest Parquet file in s3://{S3_BUCKET_NAME}/{S3_PREFIX}")
        
        # List all objects in the analytics/parquet/members/ prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=S3_PREFIX
        )
        
        if 'Contents' not in response:
            return False, "No Parquet files found"
        
        # Get all parquet files
        parquet_files = [
            obj for obj in response['Contents'] 
            if obj['Key'].endswith('.parquet')
        ]
        
        if not parquet_files:
            return False, "No Parquet files found"
        
        # Sort by LastModified to get the latest file
        latest_file = max(parquet_files, key=lambda x: x['LastModified'])
        
        logger.info(f"Found latest Parquet file: {latest_file['Key']} (modified: {latest_file['LastModified']})")
        return True, latest_file['Key']
        
    except Exception as e:
        logger.error(f"Error finding latest Parquet file: {str(e)}")
        return False, f"Error finding latest file: {str(e)}"

def validate_filename(filename):
    """
    Validate filename to prevent path traversal attacks
    Only allow parquet files with safe naming patterns
    """
    if not filename:
        return False, "Filename is required"
    
    # Only allow .parquet files
    if not filename.endswith('.parquet'):
        return False, "Only .parquet files are allowed"
    
    # Prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename format"
    
    # Only allow alphanumeric, dash, underscore, and dot
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.')
    if not all(c in allowed_chars for c in filename):
        return False, "Filename contains invalid characters"
    
    return True, None

def check_file_exists(s3_key):
    """
    Check if the parquet file exists in S3
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True, None
    except s3_client.exceptions.NoSuchKey:
        return False, "Parquet file not found"
    except Exception as e:
        logger.error(f"Error checking file existence: {str(e)}")
        return False, f"Error accessing file: {str(e)}"

def get_file_metadata(s3_key):
    """
    Get metadata about the parquet file
    """
    try:
        response = s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return {
            'size': response.get('ContentLength', 0),
            'last_modified': response.get('LastModified', '').isoformat() if response.get('LastModified') else '',
            'content_type': response.get('ContentType', 'application/octet-stream'),
            'metadata': response.get('Metadata', {})
        }
    except Exception as e:
        logger.error(f"Error getting file metadata: {str(e)}")
        return {}

def download_parquet_file(s3_key, return_content=True):
    """
    Download parquet file from S3
    
    Args:
        s3_key: S3 key for the parquet file
        return_content: If True, return file content; if False, return pre-signed URL
    
    Returns:
        tuple: (success, data_or_error)
    """
    try:
        if return_content:
            # Download file content directly
            response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            file_content = response['Body'].read()
            
            # Encode as base64 for API Gateway binary response
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            return True, {
                'content': encoded_content,
                'content_type': 'application/octet-stream',
                'filename': os.path.basename(s3_key),
                'size': len(file_content)
            }
        else:
            # Generate pre-signed URL (alternative approach)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=3600  # 1 hour expiration
            )
            
            return True, {
                'download_url': presigned_url,
                'expires_in': 3600,
                'filename': os.path.basename(s3_key)
            }
            
    except Exception as e:
        logger.error(f"Error downloading parquet file: {str(e)}")
        return False, f"Error downloading file: {str(e)}"

def apply_regional_filtering(user_roles, user_email, filename):
    """
    Apply regional filtering if user is a regional administrator
    
    Args:
        user_roles: List of user roles
        user_email: User email
        filename: Requested filename
    
    Returns:
        tuple: (is_allowed, error_message)
    """
    # Check if user has full access roles
    full_access_roles = ['System_User_Management']
    if any(role in user_roles for role in full_access_roles):
        return True, None
    
    # For regional administrators, we would need to implement regional file filtering
    # This is a placeholder for future regional partitioning implementation
    # For now, allow access to all files for users with member permissions
    
    # TODO: Implement regional filtering when parquet files are partitioned by region
    # Example: if filename contains region info, check if user has access to that region
    
    return True, None

def lambda_handler(event, context):
    """
    Main Lambda handler for parquet file downloads
    
    ARCHITECTURE: Any user with member permissions can download full parquet file,
    frontend handles regional filtering based on user's region roles.
    
    Required permissions: Any member permission + region role combination:
    - members_read, members_export, members_create, members_update, or members_delete
    - Plus any region role (Regio_All, Regio_Utrecht, etc.)
    """
    logger.info(f"Parquet download request. Event: {json.dumps(event, default=str)}")
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials and validate authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            logger.warning(f"Authentication failed: {auth_error}")
            return auth_error
        
        # Validate permissions using enhanced validation with regional support
        # NEW ROLE STRUCTURE: Any user with member permissions can download full parquet file
        # Frontend handles regional filtering based on user's region roles
        # Required: Any member permission + region role combination
        required_permissions = ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete']
        
        is_authorized, auth_error, regional_info = validate_permissions_with_regions(
            user_roles, 
            required_permissions, 
            user_email, 
            resource_context={'operation': 'parquet_download'}
        )
        
        if not is_authorized:
            logger.warning(f"Permission denied for user {user_email} with roles {user_roles}")
            logger.warning(f"Required: Any member permission (members_read, members_export, members_create, members_update, members_delete) + region role")
            return auth_error
        
        logger.info(f"✅ Authentication successful: User {user_email} with roles {user_roles} authorized for parquet download")
        
        # Extract filename from path parameters
        filename = event.get('pathParameters', {}).get('filename')
        if not filename:
            return create_error_response(400, 'Filename parameter is required')
        
        # Handle special "latest" filename to get the most recent file
        if filename.lower() == 'latest' or filename.lower() == 'latest.parquet':
            logger.info("Requesting latest Parquet file")
            success, latest_key_or_error = get_latest_parquet_file()
            if not success:
                return create_error_response(404, f'No latest file found: {latest_key_or_error}')
            
            # Use the latest file's S3 key directly
            s3_key = latest_key_or_error
            filename = os.path.basename(s3_key)  # Extract filename for logging
        else:
            # Validate filename for security
            is_valid, validation_error = validate_filename(filename)
            if not is_valid:
                logger.warning(f"Invalid filename '{filename}': {validation_error}")
                return create_error_response(400, f'Invalid filename: {validation_error}')
            
            # Construct S3 key
            s3_key = f"{S3_PREFIX}{filename}"
        
        # Check if file exists
        file_exists, existence_error = check_file_exists(s3_key)
        if not file_exists:
            logger.warning(f"File not found: {s3_key}")
            return create_error_response(404, f'File not found: {existence_error}')
        
        # Get file metadata
        file_metadata = get_file_metadata(s3_key)
        
        # Determine download method based on file size
        file_size = file_metadata.get('size', 0)
        use_presigned_url = file_size > 5 * 1024 * 1024  # Use pre-signed URL for files > 5MB
        
        # Download the file
        success, download_result = download_parquet_file(s3_key, return_content=not use_presigned_url)
        if not success:
            logger.error(f"Download failed for {s3_key}: {download_result}")
            return create_error_response(500, f'Download failed: {download_result}')
        
        # Log successful access for audit trail
        log_successful_access(
            user_email, 
            user_roles, 
            f"parquet_download:{filename}",
            {
                'filename': filename,
                's3_key': s3_key,
                'file_size': file_size,
                'download_method': 'presigned_url' if use_presigned_url else 'direct_content'
            }
        )
        
        logger.info(f"📊 AUDIT: User {user_email} (roles: {user_roles}) downloaded parquet file {filename} ({file_size} bytes)")
        
        if use_presigned_url:
            # Return pre-signed URL for large files
            return create_success_response({
                'success': True,
                'download_method': 'presigned_url',
                'data': download_result,
                'metadata': file_metadata,
                'message': f'Pre-signed URL generated for {filename}'
            })
        else:
            # Return file content directly for small files
            return {
                'statusCode': 200,
                'headers': {
                    **cors_headers(),
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{filename}"'
                },
                'body': download_result['content'],
                'isBase64Encoded': True
            }
        
    except Exception as e:
        logger.error(f"Error in parquet download: {str(e)}", exc_info=True)
        
        return create_error_response(500, 'Internal server error', {
            'message': str(e)
        })