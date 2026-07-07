"""
H-DCN Google Calendar Sync Lambda Handler

Syncs events to Google Calendar based on status changes:
- Status → 'published': create or update Google Calendar event
- Status → 'archived' / delete: remove from Google Calendar
- Field change (name, date, location) while published: update Google Calendar event

Uses a service account (credentials from SSM Parameter Store).
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

GOOGLE_CREDENTIALS_PARAMETER: str = os.environ.get(
    'GOOGLE_CREDENTIALS_PARAMETER', '/h-dcn/google-credentials'
)
EVENTS_TABLE_NAME: str = os.environ.get('EVENTS_TABLE_NAME', 'Events')

# Calendar ID routing by event_type
CALENDAR_INTERNATIONAAL: str = 'h-dcn.nl_tdqsqddtask5sa8hola0sga4a0@group.calendar.google.com'
CALENDAR_NATIONAAL: str = 'h-dcn.nl_0pth567r0u62j086o4m3urio84@group.calendar.google.com'
CALENDAR_DIVERSEN: str = 'h-dcn.nl_voetgs35u59e808nhr9t35bidc@group.calendar.google.com'

# Module-level cache for Google credentials (persists across warm starts)
_cached_credentials_json: str | None = None

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
# Google Calendar Service
# ---------------------------------------------------------------------------

def _get_google_credentials_json() -> str:
    """Fetch Google service account credentials JSON from SSM Parameter Store."""
    global _cached_credentials_json
    if _cached_credentials_json is not None:
        return _cached_credentials_json

    response = ssm_client.get_parameter(
        Name=GOOGLE_CREDENTIALS_PARAMETER,
        WithDecryption=True,
    )
    _cached_credentials_json = response['Parameter']['Value']
    return _cached_credentials_json


def _build_calendar_service() -> Any:
    """
    Build a Google Calendar API service using service account credentials.

    Returns a googleapiclient.discovery.Resource for the Calendar API v3.
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds_json: str = _get_google_credentials_json()
    creds_dict: dict[str, Any] = json.loads(creds_json)

    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/calendar'],
    )

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
        else:  # action == 'delete'
            result = delete_event(event_id, event_data)

        # Store the google_calendar_event_id back on the DynamoDB record
        _update_gcal_id_on_event(event_id, result['google_calendar_event_id'])

        return create_success_response(result)

    except Exception as e:
        logger.error(f"Unexpected error in sync_google_calendar: {str(e)}", exc_info=True)
        return create_error_response(500, f'Internal server error: {str(e)}')
