"""
H-DCN Public Events List API Endpoint

Returns a list of published, future events for the public calendar grid.
NO authentication required — this is a public endpoint.

Filters:
- status = 'published'
- end_date >= today
- event_type != 'webshop'

Optional query params:
- type: filter by event_type
- regio: filter by linked_regio
- from: start_date >= value
- to: start_date <= value

Returns: public-safe fields only (no cost, revenue, allowed_events, constraints).
"""

import json
import os
from datetime import date
from decimal import Decimal
from typing import Any

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
    lambda_handler = create_smart_fallback_handler("get_events_public")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

# Public-safe fields whitelist — excludes admin fields like cost, revenue, constraints
PUBLIC_FIELDS: list[str] = [
    'event_id',
    'name',
    'slug',
    'event_type',
    'location',
    'start_date',
    'end_date',
    'poster_url',
    'description',
    'landing_page',
    'linked_regio',
    'participation',
    'registration_open',
    'registration_close',
    'payment_deadline',
]


def _convert_decimals(obj: Any) -> Any:
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _strip_to_public_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Return only public-safe fields from an event item."""
    return {key: item[key] for key in PUBLIC_FIELDS if key in item}


def _build_filter_expression(
    today_str: str,
    query_params: dict[str, str] | None,
) -> tuple[str, dict[str, Any], dict[str, str]]:
    """
    Build DynamoDB FilterExpression with base filters + optional query params.

    Returns (filter_expression, expression_attribute_values, expression_attribute_names).
    """
    # Base filters: published, future, not webshop
    conditions: list[str] = [
        '#status_field = :published',
        'end_date >= :today',
        'event_type <> :webshop',
    ]
    expr_values: dict[str, Any] = {
        ':published': 'published',
        ':today': today_str,
        ':webshop': 'webshop',
    }
    expr_names: dict[str, str] = {
        '#status_field': 'status',
    }

    if query_params:
        # Filter by event_type
        if query_params.get('type'):
            conditions.append('event_type = :type_filter')
            expr_values[':type_filter'] = query_params['type']

        # Filter by linked_regio
        if query_params.get('regio'):
            conditions.append('linked_regio = :regio_filter')
            expr_values[':regio_filter'] = query_params['regio']

        # Filter by from date (start_date >= from)
        if query_params.get('from'):
            conditions.append('start_date >= :from_date')
            expr_values[':from_date'] = query_params['from']

        # Filter by to date (start_date <= to)
        if query_params.get('to'):
            conditions.append('start_date <= :to_date')
            expr_values[':to_date'] = query_params['to']

    filter_expression = ' AND '.join(conditions)
    return filter_expression, expr_values, expr_names


def _scan_all_pages(
    filter_expression: str,
    expr_values: dict[str, Any],
    expr_names: dict[str, str],
) -> list[dict[str, Any]]:
    """Scan DynamoDB with pagination to retrieve all matching items."""
    all_items: list[dict[str, Any]] = []
    scan_kwargs: dict[str, Any] = {
        'FilterExpression': filter_expression,
        'ExpressionAttributeValues': expr_values,
        'ExpressionAttributeNames': expr_names,
    }

    while True:
        response = events_table.scan(**scan_kwargs)
        all_items.extend(response.get('Items', []))

        # Check for pagination
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        scan_kwargs['ExclusiveStartKey'] = last_key

    return all_items


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Public events list endpoint — no auth required.
    GET /events-public
    """
    try:
        # Handle OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Get today's date for filtering
        today_str: str = date.today().isoformat()

        # Parse optional query parameters
        query_params: dict[str, str] | None = event.get('queryStringParameters')

        # Build filter expression
        filter_expression, expr_values, expr_names = _build_filter_expression(
            today_str, query_params
        )

        # Scan with pagination
        items = _scan_all_pages(filter_expression, expr_values, expr_names)

        # Strip to public-safe fields only
        public_items = [_strip_to_public_fields(item) for item in items]

        # Sort by start_date ascending
        public_items.sort(key=lambda x: x.get('start_date', ''))

        # Convert Decimals for JSON serialization
        public_items = _convert_decimals(public_items)

        # Return raw array (frontend expects JSON array, not wrapped object)
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(public_items),
        }

    except Exception as e:
        print(f"Error in get_events_public handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}')
