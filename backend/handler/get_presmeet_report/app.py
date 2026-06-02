import json
import os

import boto3
from botocore.exceptions import ClientError

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import is_presmeet_admin, has_presmeet_access

    _IMPORTS_AVAILABLE = True
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    try:
        from shared.maintenance_fallback import create_smart_fallback_handler

        _fallback_handler = create_smart_fallback_handler("get_presmeet_report")
    except ImportError:
        _fallback_handler = None
    _IMPORTS_AVAILABLE = False

s3_client = boto3.client("s3")
S3_REPORTS_BUCKET = os.environ.get("S3_REPORTS_BUCKET", "h-dcn-reports")
S3_PREFIX = "presmeet/"

# Valid report types and their file extensions / content types
REPORT_TYPES = {
    "overview": {"file": "overview.json", "content_type": "application/json", "format": "json"},
    "orders": {"file": "orders.json", "content_type": "application/json", "format": "json"},
    "export_submitted": {"file": "export_submitted.csv", "content_type": "text/csv", "format": "csv"},
    "export_all": {"file": "export_all.csv", "content_type": "text/csv", "format": "csv"},
    "metadata": {"file": "metadata.json", "content_type": "application/json", "format": "json"},
}


def lambda_handler(event, context):
    if not _IMPORTS_AVAILABLE:
        if _fallback_handler:
            return _fallback_handler(event, context)
        return {"statusCode": 503, "body": "Service unavailable"}

    try:
        # Handle OPTIONS request
        if event.get("httpMethod") == "OPTIONS":
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Gate: check PresMeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(403, "PresMeet access required")

        # Admin check - only PresMeet admins can access reports
        if not is_presmeet_admin(user_roles):
            return create_error_response(403, "Admin access required")

        # Log successful access
        log_successful_access(user_email, user_roles, "get_presmeet_report")

        # Get report type from query parameters (default: overview)
        query_params = event.get("queryStringParameters") or {}
        report_type = query_params.get("type", "overview")

        # Validate report type
        if report_type not in REPORT_TYPES:
            return create_error_response(
                400,
                f"Invalid report type: {report_type}. Must be one of: {', '.join(REPORT_TYPES.keys())}",
            )

        # Read requested file from S3
        report_config = REPORT_TYPES[report_type]
        s3_key = f"{S3_PREFIX}{report_config['file']}"

        try:
            response = s3_client.get_object(
                Bucket=S3_REPORTS_BUCKET,
                Key=s3_key,
            )
            content = response["Body"].read().decode("utf-8")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("NoSuchKey", "404"):
                return create_error_response(404, "No report generated yet")
            raise

        # Return content with appropriate format
        if report_config["format"] == "json":
            # Parse JSON and return via standard success response
            parsed_content = json.loads(content)
            return create_success_response(parsed_content)
        else:
            # Return raw CSV with text/csv content type
            return {
                "statusCode": 200,
                "headers": {
                    **cors_headers(),
                    "Content-Type": "text/csv",
                },
                "body": content,
            }

    except Exception as e:
        print(f"Error in get_presmeet_report handler: {str(e)}")
        return create_error_response(500, "Internal server error")
