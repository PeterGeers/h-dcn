import json
import os
import base64
import time
import io
import boto3
from PIL import Image

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    from shared.event_access import get_registry_row_id
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("upload_registry_logo")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

# Constants
MAX_IMAGE_SIZE = 5_242_880  # 5MB in bytes
MAX_DIMENSIONS = (200, 200)
ALLOWED_CONTENT_TYPES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
ADMIN_ROLES = {'Products_CRUD', 'Webshop_Management'}

# AWS resources
s3_client = boto3.client('s3')
FRONTEND_BUCKET_NAME = os.environ.get('FRONTEND_BUCKET_NAME', 'h-dcn-frontend-506221081911')


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Log successful access
        log_successful_access(user_email, user_roles, 'upload_registry_logo')

        # Extract event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        if not event_id:
            return create_error_response(400, 'Missing required path parameter: event_id')

        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except (json.JSONDecodeError, TypeError):
                return create_error_response(400, 'Invalid JSON in request body')

        # Validate required fields
        image_data = body.get('image_data')
        row_id = body.get('row_id')
        content_type = body.get('content_type')

        if not image_data:
            return create_error_response(400, 'Missing required field: image_data')
        if not row_id:
            return create_error_response(400, 'Missing required field: row_id')
        if not content_type:
            return create_error_response(400, 'Missing required field: content_type')

        # Look up user's registry_row_id from Members table
        user_registry_row_id = get_registry_row_id(user_email)
        if not user_registry_row_id:
            return create_error_response(403, 'No registry row assignment found')

        # Authorization: allow if row_id matches OR user has admin role
        has_admin_role = bool(ADMIN_ROLES.intersection(set(user_roles)))
        if row_id != user_registry_row_id and not has_admin_role:
            return create_error_response(
                403, 'Not authorized to upload logo for this registry row'
            )

        # Validate content_type
        if content_type not in ALLOWED_CONTENT_TYPES:
            return create_error_response(
                400,
                f'Invalid content type. Allowed: {", ".join(sorted(ALLOWED_CONTENT_TYPES))}'
            )

        # Decode base64 image data
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception:
            return create_error_response(400, 'Invalid base64 image data')

        # Validate decoded size
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return create_error_response(413, 'Image too large. Maximum size is 5MB')

        # Open and validate image with Pillow
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()
            # Re-open after verify (verify() can leave the file in unusable state)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return create_error_response(400, f'Invalid image file: {str(e)}')

        # Resize to fit within 200x200 bounding box preserving aspect ratio
        try:
            image.thumbnail(MAX_DIMENSIONS, Image.LANCZOS)
            # Convert to RGB if necessary (e.g., RGBA, P mode)
            if image.mode in ('RGBA', 'LA') or (
                image.mode == 'P' and 'transparency' in image.info
            ):
                # Preserve transparency by converting to RGBA first
                image = image.convert('RGBA')
            elif image.mode != 'RGB' and image.mode != 'RGBA':
                image = image.convert('RGB')

            # Convert to PNG
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG')
            png_bytes = output_buffer.getvalue()
        except Exception as e:
            return create_error_response(400, f'Image processing failed: {str(e)}')

        # Upload to S3 — use event_id in the path for proper scoping
        s3_key = f'assets/presmeet/logos/{row_id}.png'
        try:
            s3_client.put_object(
                Bucket=FRONTEND_BUCKET_NAME,
                Key=s3_key,
                Body=png_bytes,
                ContentType='image/png',
                CacheControl='max-age=0, must-revalidate'
            )
        except Exception as e:
            print(f"S3 upload failed: {str(e)}")
            return create_error_response(500, f'Failed to store logo: {str(e)}')

        # Build logo URL with cache-busting timestamp
        timestamp = int(time.time())
        logo_url = (
            f'https://{FRONTEND_BUCKET_NAME}.s3.eu-west-1.amazonaws.com'
            f'/{s3_key}?t={timestamp}'
        )

        return create_success_response({
            'message': 'Logo uploaded successfully',
            'logo_url': logo_url
        })

    except Exception as e:
        print(f"Error in upload_registry_logo handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
