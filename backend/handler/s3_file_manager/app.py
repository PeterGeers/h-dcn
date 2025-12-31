import json
import boto3
import base64
import os
from botocore.exceptions import ClientError
import uuid
from datetime import datetime

# Import shared authentication utilities from layer
from shared.auth_utils import (
    extract_user_credentials, 
    validate_permissions, 
    cors_headers, 
    create_error_response, 
    create_success_response,
    handle_options_request,
    log_successful_access
)

# Initialize S3 client
s3_client = boto3.client('s3')

def validate_bucket_access(bucket_name):
    """Validate that the bucket is allowed for operations"""
    # Define allowed buckets for security
    allowed_buckets = [
        'my-hdcn-bucket'
    ]
    
    if bucket_name not in allowed_buckets:
        raise ValueError(f'Access denied to bucket: {bucket_name}. Allowed buckets: {allowed_buckets}')

def handle_upload(event):
    """Handle file upload to S3"""
    try:
        request_data = json.loads(event['body'])
        
        # Required parameters
        bucket_name = request_data.get('bucketName')
        file_key = request_data.get('fileKey')
        file_data = request_data.get('fileData')
        
        if not all([bucket_name, file_key, file_data]):
            return create_error_response(400, 'bucketName, fileKey, and fileData are required')
        
        # Validate bucket access
        validate_bucket_access(bucket_name)
        
        # Optional parameters
        content_type = request_data.get('contentType', 'application/octet-stream')
        cache_control = request_data.get('cacheControl', 'no-cache')
        
        # Handle different data formats
        if isinstance(file_data, str):
            # Base64 encoded data
            if file_data.startswith('data:'):
                # Remove data URL prefix
                file_data = file_data.split(',')[1]
            
            try:
                file_bytes = base64.b64decode(file_data)
            except Exception as e:
                return create_error_response(400, f'Invalid base64 data: {str(e)}')
        else:
            # JSON data (for parameters.json etc.)
            file_bytes = json.dumps(file_data, indent=2, ensure_ascii=False).encode('utf-8')
            content_type = 'application/json'
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_bytes,
            ContentType=content_type,
            CacheControl=cache_control
        )
        
        # Generate the public URL
        region = os.environ.get('AWS_REGION', 'eu-west-1')
        file_url = f'https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}'
        
        print(f"✅ Successfully uploaded {file_key} to {bucket_name}")
        
        return create_success_response({
            'message': 'File uploaded successfully',
            'fileUrl': file_url,
            'bucket': bucket_name,
            'key': file_key,
            'size': len(file_bytes)
        })
        
    except ValueError as e:
        return create_error_response(403, str(e))
    except ClientError as e:
        print(f"❌ S3 Error: {e}")
        return create_error_response(500, f'S3 operation failed: {str(e)}')
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return create_error_response(500, f'Upload failed: {str(e)}')

def handle_delete(event):
    """Handle file deletion from S3"""
    try:
        # Parse request body
        if not event.get('body'):
            return create_error_response(400, 'Request body is required for DELETE operation')
        
        request_data = json.loads(event['body'])
        
        # Required parameters
        bucket_name = request_data.get('bucketName')
        file_key = request_data.get('fileKey')
        
        if not all([bucket_name, file_key]):
            return create_error_response(400, 'bucketName and fileKey are required')
        
        # Validate bucket access
        validate_bucket_access(bucket_name)
        
        # Check if file exists first
        try:
            s3_client.head_object(Bucket=bucket_name, Key=file_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return create_error_response(404, f'File not found: {file_key}')
            else:
                raise e
        
        # Delete from S3
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=file_key
        )
        
        print(f"✅ Successfully deleted {file_key} from {bucket_name}")
        
        return create_success_response({
            'message': 'File deleted successfully',
            'bucket': bucket_name,
            'key': file_key
        })
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except ValueError as e:
        return create_error_response(403, str(e))
    except ClientError as e:
        print(f"❌ S3 Error: {e}")
        return create_error_response(500, f'S3 operation failed: {str(e)}')
    except Exception as e:
        print(f"❌ Delete error: {e}")
        return create_error_response(500, f'Delete failed: {str(e)}')

def handle_list(event):
    """Handle listing files in S3 bucket"""
    try:
        # Get parameters from query string
        query_params = event.get('queryStringParameters') or {}
        bucket_name = query_params.get('bucketName')
        prefix = query_params.get('prefix', '')
        max_keys = int(query_params.get('maxKeys', '1000'))  # Default to 1000, max AWS allows
        recursive = query_params.get('recursive', 'true').lower() == 'true'
        
        if not bucket_name:
            return create_error_response(400, 'bucketName query parameter is required')
        
        # Validate bucket access
        validate_bucket_access(bucket_name)
        
        # List objects in S3
        list_params = {
            'Bucket': bucket_name,
            'MaxKeys': min(max_keys, 1000)  # AWS limit
        }
        
        if prefix:
            list_params['Prefix'] = prefix
        
        # If not recursive, use delimiter to group by "folders"
        if not recursive:
            list_params['Delimiter'] = '/'
        
        response = s3_client.list_objects_v2(**list_params)
        
        files = []
        folders = []
        
        # Process files
        if 'Contents' in response:
            for obj in response['Contents']:
                file_info = {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'lastModified': obj['LastModified'].isoformat(),
                    'url': f"https://{bucket_name}.s3.{os.environ.get('AWS_REGION', 'eu-west-1')}.amazonaws.com/{obj['Key']}",
                    'type': 'file'
                }
                
                # Add file extension and name
                if '/' in obj['Key']:
                    file_info['folder'] = '/'.join(obj['Key'].split('/')[:-1]) + '/'
                    file_info['name'] = obj['Key'].split('/')[-1]
                else:
                    file_info['folder'] = ''
                    file_info['name'] = obj['Key']
                
                if '.' in file_info['name']:
                    file_info['extension'] = file_info['name'].split('.')[-1].lower()
                
                files.append(file_info)
        
        # Process folders (common prefixes) if not recursive
        if not recursive and 'CommonPrefixes' in response:
            for prefix_info in response['CommonPrefixes']:
                folder_prefix = prefix_info['Prefix']
                folders.append({
                    'key': folder_prefix,
                    'name': folder_prefix.rstrip('/').split('/')[-1],
                    'type': 'folder',
                    'url': f"https://{bucket_name}.s3.{os.environ.get('AWS_REGION', 'eu-west-1')}.amazonaws.com/{folder_prefix}"
                })
        
        # Sort files and folders
        files.sort(key=lambda x: x['key'])
        folders.sort(key=lambda x: x['key'])
        
        # Combine results
        all_items = folders + files
        
        print(f"✅ Successfully listed {len(files)} files and {len(folders)} folders from {bucket_name}")
        
        result = {
            'message': 'Files listed successfully',
            'bucket': bucket_name,
            'prefix': prefix,
            'recursive': recursive,
            'files': files,
            'folders': folders,
            'items': all_items,
            'counts': {
                'files': len(files),
                'folders': len(folders),
                'total': len(all_items)
            },
            'truncated': response.get('IsTruncated', False)
        }
        
        if response.get('IsTruncated'):
            result['nextContinuationToken'] = response.get('NextContinuationToken')
            result['message'] += f' (truncated - use continuationToken for more results)'
        
        return create_success_response(result)
        
    except ValueError as e:
        return create_error_response(403, str(e))
    except ClientError as e:
        print(f"❌ S3 Error: {e}")
        return create_error_response(500, f'S3 operation failed: {str(e)}')
    except Exception as e:
        print(f"❌ List error: {e}")
        return create_error_response(500, f'List failed: {str(e)}')

def lambda_handler(event, context):
    """
    Generic S3 file manager with shared authentication
    Supports upload, delete, and list operations
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials using shared auth layer
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions for S3 operations using shared auth layer
        required_permissions = ['products_create', 'products_update', 'products_delete']  # S3 file operations
        has_permission, permission_error = validate_permissions(
            user_roles, 
            required_permissions, 
            user_email,
            resource_context={'operation': 's3_file_management', 'bucket': 'my-hdcn-bucket'}
        )
        if not has_permission:
            return permission_error
        
        # Log successful access
        log_successful_access(
            user_email, 
            user_roles, 
            f"s3_file_manager_{event.get('httpMethod', 'UNKNOWN').lower()}",
            resource_context={'bucket': 'my-hdcn-bucket'}
        )
        
        # Route based on HTTP method
        method = event.get('httpMethod', '').upper()
        
        if method == 'POST':
            # Upload file
            return handle_upload(event)
        elif method == 'DELETE':
            # Delete file
            return handle_delete(event)
        elif method == 'GET':
            # List files
            return handle_list(event)
        else:
            return create_error_response(405, f'Method {method} not allowed')
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return create_error_response(500, f'Internal server error: {str(e)}')