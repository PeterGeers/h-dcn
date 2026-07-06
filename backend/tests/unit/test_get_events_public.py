"""
Unit Tests for get_events_public Lambda Handler.

Tests the public events list endpoint:
- Returns only published events (draft/archived excluded)
- Excludes webshop event_type
- Excludes past events (end_date < today)
- Filters by type query param
- Filters by regio query param
- Filters by from/to date range
- Returns only public-safe fields (no cost, revenue, etc.)
- Handles OPTIONS preflight
- Returns empty array when no events match
- Sorts by start_date ascending
"""

import importlib.util
import json
import os
import sys
from datetime import date, timedelta

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_events_public', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def _future_date(days_ahead: int = 30) -> str:
    """Return a date string days_ahead in the future."""
    return (date.today() + timedelta(days=days_ahead)).isoformat()


def _past_date(days_ago: int = 30) -> str:
    """Return a date string days_ago in the past."""
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _make_event(method: str = 'GET', query_params: dict | None = None) -> dict:
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': query_params,
        'pathParameters': None,
        'body': None,
    }


def _seed_event(
    events_table,
    event_id: str,
    name: str = 'Test Event',
    status: str = 'published',
    event_type: str = 'nationaal',
    start_date: str | None = None,
    end_date: str | None = None,
    linked_regio: str = 'noord',
    extra_fields: dict | None = None,
) -> dict:
    """Seed an event into the test table."""
    item = {
        'event_id': event_id,
        'name': name,
        'slug': name.lower().replace(' ', '-'),
        'status': status,
        'event_type': event_type,
        'start_date': start_date or _future_date(10),
        'end_date': end_date or _future_date(12),
        'location': 'Amsterdam',
        'linked_regio': linked_regio,
        'poster_url': 'https://s3.example.com/poster.jpg',
        'description': 'A test event description',
        'participation': 'open',
        'landing_page': {'enabled': True, 'slug': name.lower().replace(' ', '-')},
        # Admin-only fields (should NOT appear in response)
        'cost': 1500,
        'revenue': 3000,
        'allowed_events': ['evt-other'],
        'constraints': [{'type': 'max_per_club', 'value': 2}],
        'product_ids': ['prod-001'],
    }
    if extra_fields:
        item.update(extra_fields)
    events_table.put_item(Item=item)
    return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """Create mocked DynamoDB tables and load handler inside mock_aws context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        handler_module = _load_handler()
        yield events_table, handler_module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetEventsPublic:
    """Tests for the public events list endpoint."""

    def test_options_request(self, setup_tables):
        """CORS preflight returns 200."""
        _, handler = setup_tables
        event = _make_event(method='OPTIONS')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_returns_empty_array_when_no_events(self, setup_tables):
        """Returns empty JSON array when no events match."""
        _, handler = setup_tables
        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body == []

    def test_returns_only_published_events(self, setup_tables):
        """Draft and archived events are excluded."""
        events_table, handler = setup_tables

        # Seed: 1 published, 1 draft, 1 archived
        _seed_event(events_table, 'evt-pub-1', name='Published Event', status='published')
        _seed_event(events_table, 'evt-draft-1', name='Draft Event', status='draft')
        _seed_event(events_table, 'evt-arch-1', name='Archived Event', status='archived')

        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'Published Event'

    def test_excludes_webshop_event_type(self, setup_tables):
        """Events with event_type='webshop' are excluded."""
        events_table, handler = setup_tables

        _seed_event(events_table, 'evt-nat-1', name='National Event', event_type='nationaal')
        _seed_event(events_table, 'evt-web-1', name='Webshop Event', event_type='webshop')

        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'National Event'

    def test_excludes_past_events(self, setup_tables):
        """Events with end_date < today are excluded."""
        events_table, handler = setup_tables

        _seed_event(
            events_table, 'evt-future-1', name='Future Event',
            start_date=_future_date(5), end_date=_future_date(7),
        )
        _seed_event(
            events_table, 'evt-past-1', name='Past Event',
            start_date=_past_date(10), end_date=_past_date(5),
        )

        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'Future Event'

    def test_filters_by_type_query_param(self, setup_tables):
        """Filters results when ?type= is provided."""
        events_table, handler = setup_tables

        _seed_event(events_table, 'evt-nat-1', name='National', event_type='nationaal')
        _seed_event(events_table, 'evt-int-1', name='International', event_type='internationaal')

        event = _make_event(query_params={'type': 'nationaal'})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'National'

    def test_filters_by_regio_query_param(self, setup_tables):
        """Filters results when ?regio= is provided."""
        events_table, handler = setup_tables

        _seed_event(events_table, 'evt-n-1', name='Noord Event', linked_regio='noord')
        _seed_event(events_table, 'evt-z-1', name='Zuid Event', linked_regio='zuid')

        event = _make_event(query_params={'regio': 'noord'})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'Noord Event'

    def test_filters_by_from_to_date_range(self, setup_tables):
        """Filters by from/to date range on start_date."""
        events_table, handler = setup_tables

        # Event starting in 5 days
        early_start = _future_date(5)
        _seed_event(
            events_table, 'evt-early-1', name='Early Event',
            start_date=early_start, end_date=_future_date(7),
        )
        # Event starting in 60 days
        late_start = _future_date(60)
        _seed_event(
            events_table, 'evt-late-1', name='Late Event',
            start_date=late_start, end_date=_future_date(62),
        )

        # Filter: from=today to the early event start + 1 day
        from_date = date.today().isoformat()
        to_date = _future_date(10)

        event = _make_event(query_params={'from': from_date, 'to': to_date})
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        assert body[0]['name'] == 'Early Event'

    def test_returns_only_public_safe_fields(self, setup_tables):
        """Admin fields (cost, revenue, allowed_events, constraints, product_ids) are excluded."""
        events_table, handler = setup_tables

        _seed_event(events_table, 'evt-pub-1', name='Public Event')

        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 1
        item = body[0]

        # Public fields present
        assert 'event_id' in item
        assert 'name' in item
        assert 'slug' in item
        assert 'start_date' in item
        assert 'end_date' in item
        assert 'location' in item
        assert 'event_type' in item
        assert 'poster_url' in item
        assert 'description' in item
        assert 'linked_regio' in item
        assert 'participation' in item

        # Admin fields excluded
        assert 'cost' not in item
        assert 'revenue' not in item
        assert 'allowed_events' not in item
        assert 'constraints' not in item
        assert 'product_ids' not in item

    def test_sorts_by_start_date_ascending(self, setup_tables):
        """Results are sorted by start_date ascending."""
        events_table, handler = setup_tables

        _seed_event(
            events_table, 'evt-later', name='Later Event',
            start_date=_future_date(30), end_date=_future_date(32),
        )
        _seed_event(
            events_table, 'evt-sooner', name='Sooner Event',
            start_date=_future_date(5), end_date=_future_date(7),
        )
        _seed_event(
            events_table, 'evt-mid', name='Mid Event',
            start_date=_future_date(15), end_date=_future_date(17),
        )

        event = _make_event()
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert len(body) == 3
        assert body[0]['name'] == 'Sooner Event'
        assert body[1]['name'] == 'Mid Event'
        assert body[2]['name'] == 'Later Event'

    def test_no_auth_required(self, setup_tables):
        """Endpoint works without Authorization header (public)."""
        events_table, handler = setup_tables
        _seed_event(events_table, 'evt-pub-1', name='Public Event')

        # Event with no auth headers at all
        event = {
            'httpMethod': 'GET',
            'headers': {},
            'queryStringParameters': None,
            'pathParameters': None,
            'body': None,
        }
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
