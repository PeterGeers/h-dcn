"""
H-DCN Google Calendar Sync Lambda Handler

Syncs events to Google Calendar based on status changes:
- Status → 'published': create or update Google Calendar event
- Status → 'archived' / delete: remove from Google Calendar
- Field change (name, date, location) while published: update Google Calendar event

Uses Workload Identity Federation (WIF) for Google authentication:
Lambda's AWS IAM execution role → Google token exchange → Calendar API access.
Error handling: log failures but NEVER block the DynamoDB update.

POST /sync-google-calendar (admin-only / internal invocation)

Input:
    {
        "event_id": "...",
        "action": "sync" | "delete",
        "event_data": {
            "name": "...",
            "start_date": "2026-05-15",
            "end_date": "2026-05-16",
            "location": "...",
            "description": "...",
            "poster_url": "..." | null,
            "google_calendar_event_id": "..." | null
        }
    }

Returns:
    {"google_calendar_event_id": "..."} on sync success
    {"google_calendar_event_id": null} on delete success
    {"google_calendar_event_id": <unchanged>} on failure (logged, not raised)
"""

import json
import logging
import os
from typing import Any, TypedDict, NotRequired

import boto3

try:
    from shared.auth_utils import (
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("sync_google_calendar")
    import sys
    sys.exit(0)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class EventData(TypedDict):
    name: str
    start_date: str
    end_date: str
    event_type: NotRequired[str]
    location: NotRequired[str]
    description: NotRequired[str]
    poster_url: NotRequired[str]
    google_calendar_event_id: NotRequired[str | None]


class SyncRequest(TypedDict):
    event_id: str
    action: str  # 'sync' | 'delete'
    event_data: EventData


class SyncResult(TypedDict):
    google_calendar_event_id: str | None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GOOGLE_PHOTOS_OAUTH_PARAMETER: str = os.environ.get(
    'GOOGLE_PHOTOS_OAUTH_PARAMETER', '/h-dcn/google-photos-oauth'
)
EVENTS_TABLE_NAME: str = os.environ.get('EVENTS_TABLE_NAME', 'Events')

# WIF configuration
WIF_AUDIENCE: str = os.environ.get(
    'WIF_AUDIENCE',
    '//iam.googleapis.com/projects/1081576340476/locations/global/workloadIdentityPools/h-dcn-aws-pool/providers/aws-lambda-provider'
)
WIF_SERVICE_ACCOUNT_EMAIL: str = os.environ.get(
    'WIF_SERVICE_ACCOUNT_EMAIL',
    'hdcn-portal@hdcn-portal.iam.gserviceaccount.com'
)

# Calendar ID routing by event_type
CALENDAR_INTERNATIONAAL: str = 'h-dcn.nl_tdqsqddtask5sa8hola0sga4a0@group.calendar.google.com'
CALENDAR_NATIONAAL: str = 'h-dcn.nl_0pth567r0u62j086o4m3urio84@group.calendar.google.com'
CALENDAR_DIVERSEN: str = 'h-dcn.nl_voetgs35u59e808nhr9t35bidc@group.calendar.google.com'

# Module-level cache for Google Photos OAuth (persists across warm starts)
_cached_photos_oauth: dict[str, str] | None = None

ssm_client = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')
events_table = dynamodb.Table(EVENTS_TABLE_NAME)


def _get_calendar_id(event_type: str) -> str:
    """
    Determine which Google Calendar to sync to based on event_type.

    - internationaal_treffen → Internationaal calendar
    - other, presmeet → Diversen calendar
    - everything else → Nationaal calendar
    """
    if event_type == 'internationaal_treffen':
        return CALENDAR_INTERNATIONAAL
    elif event_type in ('other', 'presmeet'):
        return CALENDAR_DIVERSEN
    else:
        return CALENDAR_NATIONAAL


# ---------------------------------------------------------------------------
# Google Calendar Service (Workload Identity Federation)
# ---------------------------------------------------------------------------

def _build_wif_credentials() -> Any:
    """
    Build Google credentials via Workload Identity Federation.

    Uses the Lambda's AWS IAM execution role to obtain a short-lived
    Google OAuth 2.0 access token via WIF (AWS → Google token exchange).

    No static service account key required — authentication is based on
    the Lambda's IAM role identity.

    Raises Exception on failure — caller must handle (no fallback to SSM).
    """
    from google.auth import identity_pool

    credentials = identity_pool.Credentials(
        audience=WIF_AUDIENCE,
        subject_token_type="urn:ietf:params:aws:token-type:aws4_request",
        token_url="https://sts.googleapis.com/v1/token",
        credential_source={
            "environment_id": "aws1",
            "region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
            "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
            "regional_cred_verification_url": "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15",
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
        service_account_impersonation_url=(
            f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{WIF_SERVICE_ACCOUNT_EMAIL}:generateAccessToken"
        ),
    )
    return credentials


def _build_calendar_service() -> Any:
    """
    Build a Google Calendar API service using WIF credentials.

    Returns a googleapiclient.discovery.Resource for the Calendar API v3.
    Raises on WIF failure — no fallback to SSM parameter.
    """
    from googleapiclient.discovery import build

    credentials = _build_wif_credentials()
    service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
    return service


# ---------------------------------------------------------------------------
# Calendar Event Body
# ---------------------------------------------------------------------------

def _build_calendar_event_body(event_data: EventData) -> dict[str, Any]:
    """
    Map DynamoDB event fields to a Google Calendar event body.

    Uses all-day event format (date only, no dateTime).
    """
    start_date: str = event_data['start_date'][:10]
    end_date: str = event_data.get('end_date', start_date)[:10]

    # Google Calendar all-day events: 'end' is exclusive (day after last day)
    # If start == end (single-day event), end should be the next day
    # But Google API also accepts same date for single-day — we pass as-is
    # since the UI shows it correctly either way.

    description: str = event_data.get('description', '')
    poster_url: str = event_data.get('poster_url', '')
    if poster_url:
        description = f"{description}\n\n<a href=\"{poster_url}\">Poster</a>".strip()

    return {
        'summary': event_data['name'],
        'start': {'date': start_date},
        'end': {'date': end_date},
        'location': event_data.get('location', ''),
        'description': description,
    }


# ---------------------------------------------------------------------------
# Sync Operations
# ---------------------------------------------------------------------------

def sync_event(event_id: str, event_data: EventData) -> SyncResult:
    """
    Create or update a Google Calendar event.

    Idempotent:
    - If google_calendar_event_id exists → update
    - If not → create

    Routes to the correct calendar based on event_type.
    On failure: logs the error and returns the existing gcal_id unchanged.
    """
    gcal_id: str | None = event_data.get('google_calendar_event_id')
    calendar_body: dict[str, Any] = _build_calendar_event_body(event_data)
    event_type: str = event_data.get('event_type', '')
    calendar_id: str = _get_calendar_id(event_type)

    try:
        service = _build_calendar_service()
    except Exception as e:
        # WIF authentication failure — no fallback, raise to caller
        error_msg = f"Google authentication failed (WIF): {str(e)}"
        logger.error(f"{error_msg} for event {event_id}", exc_info=True)
        raise RuntimeError(error_msg) from e

    try:
        if gcal_id:
            # Update existing event
            result = service.events().update(
                calendarId=calendar_id,
                eventId=gcal_id,
                body=calendar_body,
            ).execute()
            logger.info(f"Updated Google Calendar event {gcal_id} for event {event_id} (calendar: {calendar_id})")
            return SyncResult(google_calendar_event_id=result['id'])
        else:
            # Create new event
            result = service.events().insert(
                calendarId=calendar_id,
                body=calendar_body,
            ).execute()
            new_gcal_id: str = result['id']
            logger.info(f"Created Google Calendar event {new_gcal_id} for event {event_id} (calendar: {calendar_id})")
            return SyncResult(google_calendar_event_id=new_gcal_id)

    except Exception as e:
        logger.error(
            f"Google Calendar sync failed for event {event_id}: {str(e)}",
            exc_info=True,
        )
        # Return existing ID unchanged — don't block the caller
        return SyncResult(google_calendar_event_id=gcal_id)
        # Return existing ID unchanged — don't block the caller
        return SyncResult(google_calendar_event_id=gcal_id)


def delete_event(event_id: str, event_data: EventData) -> SyncResult:
    """
    Delete a Google Calendar event.

    If no google_calendar_event_id exists, this is a no-op.
    Routes to the correct calendar based on event_type.
    On failure: logs the error and returns None (cleared).
    """
    gcal_id: str | None = event_data.get('google_calendar_event_id')

    if not gcal_id:
        logger.info(f"No Google Calendar event to delete for event {event_id}")
        return SyncResult(google_calendar_event_id=None)

    event_type: str = event_data.get('event_type', '')
    calendar_id: str = _get_calendar_id(event_type)

    try:
        service = _build_calendar_service()
    except Exception as e:
        # WIF authentication failure — no fallback, raise to caller
        error_msg = f"Google authentication failed (WIF): {str(e)}"
        logger.error(f"{error_msg} for event {event_id}", exc_info=True)
        raise RuntimeError(error_msg) from e

    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=gcal_id,
        ).execute()
        logger.info(f"Deleted Google Calendar event {gcal_id} for event {event_id} (calendar: {calendar_id})")
    except Exception as e:
        logger.error(
            f"Google Calendar delete failed for event {event_id} (gcal_id={gcal_id}): {str(e)}",
            exc_info=True,
        )

    # Always clear the gcal_id after a delete attempt
    return SyncResult(google_calendar_event_id=None)


# ---------------------------------------------------------------------------
# DynamoDB Update (store gcal_id back)
# ---------------------------------------------------------------------------

def _update_gcal_id_on_event(event_id: str, gcal_id: str | None) -> None:
    """
    Store the google_calendar_event_id back on the DynamoDB event record.

    This is best-effort — if it fails, log and move on.
    """
    try:
        if gcal_id:
            events_table.update_item(
                Key={'event_id': event_id},
                UpdateExpression='SET google_calendar_event_id = :gcal_id',
                ExpressionAttributeValues={':gcal_id': gcal_id},
            )
        else:
            events_table.update_item(
                Key={'event_id': event_id},
                UpdateExpression='REMOVE google_calendar_event_id',
            )
        logger.info(f"Updated DynamoDB event {event_id} with gcal_id={gcal_id}")
    except Exception as e:
        logger.error(
            f"Failed to update google_calendar_event_id on event {event_id}: {str(e)}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Google Photos Museum Upload
# ---------------------------------------------------------------------------

def _get_photos_oauth() -> dict[str, str]:
    """Fetch Google Photos OAuth credentials from SSM (cached)."""
    global _cached_photos_oauth
    if _cached_photos_oauth is not None:
        return _cached_photos_oauth

    response = ssm_client.get_parameter(
        Name=GOOGLE_PHOTOS_OAUTH_PARAMETER,
        WithDecryption=True,
    )
    _cached_photos_oauth = json.loads(response['Parameter']['Value'])
    return _cached_photos_oauth


def _get_photos_access_token() -> str:
    """Get a Google Photos access token using the OAuth refresh token."""
    import requests as http_requests

    oauth = _get_photos_oauth()
    resp = http_requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': oauth['client_id'],
        'client_secret': oauth['client_secret'],
        'refresh_token': oauth['refresh_token'],
        'grant_type': 'refresh_token',
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()['access_token']


def _upload_poster_to_photos(event_data: EventData) -> None:
    """
    Upload a poster image to Google Photos (webmaster's library).

    Best-effort: logs failures but never blocks the sync response.
    Only uploads if poster_url points to an S3 image (not PDFs).
    """
    import requests as http_requests

    poster_url: str = event_data.get('poster_url', '')
    if not poster_url:
        return

    # Only upload image files (skip PDFs)
    lower_url = poster_url.lower()
    if not any(lower_url.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        logger.info(f"Skipping Photos upload for non-image: {poster_url}")
        return

    event_name: str = event_data.get('name', 'Unknown Event')
    start_date: str = event_data.get('start_date', '')[:10]

    try:
        # Download poster from S3 URL
        img_resp = http_requests.get(poster_url, timeout=30)
        img_resp.raise_for_status()
        image_bytes: bytes = img_resp.content

        if not image_bytes:
            logger.warning(f"Empty image from {poster_url}")
            return

        # Get access token
        access_token = _get_photos_access_token()

        # Determine filename
        ext = '.jpg'
        for e in ('.png', '.webp', '.gif', '.jpeg'):
            if lower_url.endswith(e):
                ext = e
                break
        filename = f"{event_name} - {start_date}{ext}"

        # Upload bytes to Google Photos
        upload_resp = http_requests.post(
            'https://photoslibrary.googleapis.com/v1/uploads',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/octet-stream',
                'X-Goog-Upload-File-Name': filename,
                'X-Goog-Upload-Protocol': 'raw',
            },
            data=image_bytes,
            timeout=60,
        )
        upload_resp.raise_for_status()
        upload_token: str = upload_resp.text

        # Create media item (no album — lands in library)
        create_resp = http_requests.post(
            'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json={
                'newMediaItems': [{
                    'description': f'{event_name} | {start_date}',
                    'simpleMediaItem': {
                        'uploadToken': upload_token,
                        'fileName': filename,
                    }
                }]
            },
            timeout=30,
        )
        create_resp.raise_for_status()
        result = create_resp.json()

        status_msg = result.get('newMediaItemResults', [{}])[0].get('status', {}).get('message', '?')
        logger.info(f"Google Photos upload for '{event_name}': {status_msg}")

    except Exception as e:
        logger.error(f"Google Photos upload failed for '{event_name}': {str(e)}", exc_info=True)


# ---------------------------------------------------------------------------
# Request Validation
# ---------------------------------------------------------------------------

def _validate_request(body: dict[str, Any]) -> tuple[SyncRequest | None, str | None]:
    """Validate the incoming request body. Returns (parsed_request, error_msg)."""
    event_id: str | None = body.get('event_id')
    if not event_id:
        return None, 'event_id is required'

    action: str | None = body.get('action')
    if action not in ('sync', 'delete'):
        return None, "action must be 'sync' or 'delete'"

    event_data: dict[str, Any] | None = body.get('event_data')
    if not event_data:
        return None, 'event_data is required'

    if action == 'sync':
        if not event_data.get('name'):
            return None, 'event_data.name is required for sync'
        if not event_data.get('start_date'):
            return None, 'event_data.start_date is required for sync'
        if not event_data.get('end_date'):
            return None, 'event_data.end_date is required for sync'

    return SyncRequest(
        event_id=event_id,
        action=action,
        event_data=event_data,
    ), None


# ---------------------------------------------------------------------------
# Lambda Handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Google Calendar sync endpoint.

    POST /sync-google-calendar

    Body (JSON):
        - event_id: DynamoDB event ID
        - action: 'sync' | 'delete'
        - event_data: { name, start_date, end_date, location?, description?, google_calendar_event_id? }

    Returns:
        { google_calendar_event_id: "..." | null }
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

        # Validate request
        request, error = _validate_request(body)
        if error or request is None:
            return create_error_response(400, error or 'Invalid request')

        # Execute action
        event_id: str = request['event_id']
        action: str = request['action']
        event_data: EventData = request['event_data']

        if action == 'sync':
            result: SyncResult = sync_event(event_id, event_data)
            # Upload poster to Google Photos museum (best-effort, only if new/changed)
            poster_url = event_data.get('poster_url', '')
            if poster_url:
                # Check if this poster was already uploaded (stored on the event record)
                try:
                    event_record = events_table.get_item(Key={'event_id': event_id}).get('Item', {})
                    already_uploaded = event_record.get('poster_uploaded_to_photos', '')
                    if already_uploaded != poster_url:
                        _upload_poster_to_photos(event_data)
                        # Mark as uploaded
                        events_table.update_item(
                            Key={'event_id': event_id},
                            UpdateExpression='SET poster_uploaded_to_photos = :url',
                            ExpressionAttributeValues={':url': poster_url},
                        )
                    else:
                        logger.info(f"Poster already in Google Photos for event {event_id}, skipping")
                except Exception as e:
                    logger.error(f"Photos dedup check failed: {e}")
        else:  # action == 'delete'
            result = delete_event(event_id, event_data)

        # Store the google_calendar_event_id back on the DynamoDB record
        _update_gcal_id_on_event(event_id, result['google_calendar_event_id'])

        return create_success_response(result)

    except Exception as e:
        logger.error(f"Unexpected error in sync_google_calendar: {str(e)}", exc_info=True)
        return create_error_response(500, f'Internal server error: {str(e)}')
