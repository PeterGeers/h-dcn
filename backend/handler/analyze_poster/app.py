"""
H-DCN Poster Analysis Lambda Handler

Accepts a poster image (base64 or S3 key) and calls the Gemini Vision API
to extract event metadata: name, start_date, end_date, location, info.

NO authentication required — public endpoint for event creation workflow.

API key is fetched from SSM Parameter Store (/h-dcn/gemini-api-key) and
cached in module scope for Lambda warm starts.
"""

import base64
import json
import os
from typing import Any, TypedDict

import boto3
import requests

# Import shared utilities (CORS helpers only — no auth for this endpoint)
try:
    from shared.auth_utils import (
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("analyze_poster")
    import sys
    sys.exit(0)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class AnalysisResult(TypedDict):
    name: str
    start_date: str
    end_date: str
    location: str
    info: str


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_MODEL_URL: str = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.0-flash:generateContent"
)

SSM_PARAMETER_NAME: str = os.environ.get(
    'GEMINI_API_KEY_PARAMETER', '/h-dcn/gemini-api-key'
)

DATA_BUCKET: str = os.environ.get('DATA_BUCKET', 'h-dcn-data-506221081911')

# Module-level cache for API key (persists across warm starts)
_cached_api_key: str | None = None


# ---------------------------------------------------------------------------
# SSM Parameter Store
# ---------------------------------------------------------------------------

ssm_client = boto3.client('ssm')
s3_client = boto3.client('s3')


def _get_gemini_api_key() -> str:
    """Fetch Gemini API key from SSM Parameter Store (cached for warm starts)."""
    global _cached_api_key
    if _cached_api_key is not None:
        return _cached_api_key

    response = ssm_client.get_parameter(
        Name=SSM_PARAMETER_NAME,
        WithDecryption=True,
    )
    _cached_api_key = response['Parameter']['Value']
    return _cached_api_key


# ---------------------------------------------------------------------------
# Image retrieval
# ---------------------------------------------------------------------------

def _get_image_from_s3(s3_key: str) -> tuple[str, str]:
    """
    Download image from S3 and return (base64_data, mime_type).

    Raises ValueError if the S3 object cannot be retrieved.
    """
    try:
        response = s3_client.get_object(Bucket=DATA_BUCKET, Key=s3_key)
        image_bytes: bytes = response['Body'].read()
        content_type: str = response.get('ContentType', 'image/jpeg')
        base64_data: str = base64.b64encode(image_bytes).decode('utf-8')
        return base64_data, content_type
    except Exception as e:
        raise ValueError(f"Failed to retrieve image from S3: {str(e)}")


# ---------------------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT: str = """Analyze this event poster image and extract the following information.
Return ONLY a valid JSON object with these fields:
- "name": the event name/title
- "start_date": start date in YYYY-MM-DD format (if visible)
- "end_date": end date in YYYY-MM-DD format (if visible, same as start_date if single day event)
- "location": the event location/venue
- "info": any additional relevant information (description, organizer, price, etc.)

If a field cannot be determined from the poster, use an empty string "".
Do NOT include any markdown formatting, code fences, or extra text — only the JSON object."""


def _call_gemini_api(base64_image: str, mime_type: str) -> AnalysisResult:
    """
    Call Gemini Vision API with the poster image and return structured analysis.

    Raises RuntimeError on API failure.
    """
    api_key: str = _get_gemini_api_key()

    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"text": ANALYSIS_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_image,
                        }
                    },
                ]
            }
        ]
    }

    url: str = f"{GEMINI_MODEL_URL}?key={api_key}"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to connect to Gemini API: {str(e)}")

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini API returned status {response.status_code}: "
            f"{response.text[:500]}"
        )

    # Parse Gemini response
    try:
        gemini_data: dict[str, Any] = response.json()
        text_content: str = (
            gemini_data["candidates"][0]["content"]["parts"][0]["text"]
        )
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Unexpected Gemini response format: {str(e)}")

    # Parse the JSON from Gemini's text response
    try:
        # Strip any markdown code fences if present
        cleaned: str = text_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        result: dict[str, str] = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Gemini returned invalid JSON: {str(e)}. Raw: {text_content[:200]}"
        )

    # Normalize to expected fields
    return AnalysisResult(
        name=result.get("name", ""),
        start_date=result.get("start_date", ""),
        end_date=result.get("end_date", ""),
        location=result.get("location", ""),
        info=result.get("info", ""),
    )


# ---------------------------------------------------------------------------
# Lambda Handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Analyze a poster image and extract event metadata.

    POST /analyze-poster

    Body (JSON):
        - image_data: base64-encoded image string
        - mime_type: MIME type of the image (default: image/jpeg)
        - s3_key: S3 object key (alternative to image_data)

    Returns:
        JSON with name, start_date, end_date, location, info
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Parse request body
        body_str: str | None = event.get('body')
        if not body_str:
            return create_error_response(400, 'Request body is required')

        try:
            body: dict[str, Any] = json.loads(body_str)
        except json.JSONDecodeError:
            return create_error_response(400, 'Invalid JSON in request body')

        # Get image data — either from base64 or S3 key
        image_data: str | None = body.get('image_data')
        s3_key: str | None = body.get('s3_key')
        mime_type: str = body.get('mime_type', 'image/jpeg')

        if not image_data and not s3_key:
            return create_error_response(
                400, 'Either image_data (base64) or s3_key is required'
            )

        if s3_key:
            try:
                image_data, mime_type = _get_image_from_s3(s3_key)
            except ValueError as e:
                return create_error_response(400, str(e))

        # Validate base64 data is not empty
        if not image_data:
            return create_error_response(400, 'Image data is empty')

        # Call Gemini API for analysis
        try:
            result: AnalysisResult = _call_gemini_api(image_data, mime_type)
        except RuntimeError as e:
            return create_error_response(502, f'Poster analysis failed: {str(e)}')

        return create_success_response(result)

    except Exception as e:
        print(f"Error in analyze_poster handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}')
