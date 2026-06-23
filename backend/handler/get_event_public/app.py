"""
H-DCN Public Event API Endpoint

Returns public event information by slug for landing pages.
NO authentication required — this is a public endpoint.

Returns: event name, dates, location, landing_page config, registration status.
Excludes: constraints, product_ids, order counts, internal IDs.
"""

import json
import os
from decimal import Decimal

import boto3

# Import shared utilities (CORS helpers only — no auth for public endpoint)
try:
    from shared.auth_utils import (
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_event_public")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))


def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _resolve_event_by_slug(slug):
    """
    Scan the Events table for an event whose landing_page.slug matches.
    Returns the event item or None.
    """
    response = events_table.scan(
        FilterExpression='landing_page.slug = :slug AND landing_page.enabled = :enabled',
        ExpressionAttributeValues={
            ':slug': slug,
            ':enabled': True,
        },
    )
    items = response.get('Items', [])
    return items[0] if items else None


def _determine_registration_status(event_item):
    """
    Determine if registration is open based on publication status + date fields.

    Rules:
    - status 'draft' or 'archived' → always closed
    - status 'published' (or 'open' for backward compat, or missing) → check dates
    - registration_open/close determine the registration window
    - If dates are not set, that boundary is not enforced
    """
    from datetime import date

    status = event_item.get('status', '')

    # Draft and archived: never allow registration
    if status in ('draft', 'archived', 'closed', 'locked'):
        return 'closed'

    # Published (or 'open' backward compat, or no status field): check dates
    today = date.today().isoformat()  # yyyy-mm-dd
    reg_open = event_item.get('registration_open', '')
    reg_close = event_item.get('registration_close', '')

    if reg_open and today < reg_open[:10]:
        return 'closed'  # Registration not yet open
    if reg_close and today > reg_close[:10]:
        return 'closed'  # Registration past deadline

    return 'open'


def _build_public_response(event_item):
    """
    Build the public-safe response, excluding sensitive fields.
    Includes: event_id, name, dates, location, landing_page config, registration status,
              has_event_password (bool), landing_page_enabled (bool).
    Excludes: constraints, product_ids, order counts, order_scope, actual password hash.
    """
    landing_page = event_item.get('landing_page', {})

    # Expose whether a password gate exists (not the hash itself)
    has_event_password = bool(event_item.get('event_password'))
    landing_page_enabled = bool(landing_page.get('enabled', False))

    return {
        'event_id': event_item.get('event_id', ''),
        'name': event_item.get('name', ''),
        'event_type': event_item.get('event_type', ''),
        'start_date': event_item.get('start_date', ''),
        'end_date': event_item.get('end_date', ''),
        'location': event_item.get('location', ''),
        'registration_status': _determine_registration_status(event_item),
        'has_event_password': has_event_password,
        'landing_page_enabled': landing_page_enabled,
        'landing_page': {
            'slug': landing_page.get('slug', ''),
            'hero_image_url': landing_page.get('hero_image_url', ''),
            'tagline': landing_page.get('tagline', ''),
            'registration_label': landing_page.get('registration_label', ''),
            'logos': landing_page.get('logos', []),
            'sections': landing_page.get('sections', []),
        },
    }


def lambda_handler(event, context):
    """
    Public event endpoint — no auth required.
    GET /events/public/{slug}
    """
    try:
        # Handle OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract slug from path parameters
        path_params = event.get('pathParameters') or {}
        slug = path_params.get('slug')

        if not slug:
            return create_error_response(400, 'Missing slug parameter')

        # Resolve event by slug
        event_item = _resolve_event_by_slug(slug)

        if not event_item:
            return create_error_response(404, 'Event not found or landing page is disabled')

        # Build public response (excludes sensitive data)
        public_data = _build_public_response(event_item)
        public_data = convert_decimals(public_data)

        return create_success_response(public_data)

    except Exception as e:
        print(f"Error in get_event_public handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}')
