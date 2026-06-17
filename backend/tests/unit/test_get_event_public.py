"""
Unit Tests for get_event_public Lambda Handler.

Tests the public event endpoint:
- Returns 400 when slug is missing
- Returns 404 when no event matches the slug
- Returns 404 when landing page is disabled
- Returns event data with landing page config when found
- Excludes sensitive data (constraints, product_ids, order counts)
- Returns correct registration status (open/closed)
"""

import importlib.util
import json
import os
import sys

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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_event_public', 'app.py')
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
# Test data
# ---------------------------------------------------------------------------

TEST_EVENT_ID = 'evt-public-1234-5678-abcd'
TEST_SLUG = 'presmeet-2027'


def _make_event(slug=None, method='GET'):
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': None,
        'pathParameters': {'slug': slug} if slug else None,
        'body': None,
    }


def _seed_event(events_table, slug=TEST_SLUG, enabled=True, status='open', extra_fields=None):
    """Seed an event with landing page config."""
    item = {
        'event_id': TEST_EVENT_ID,
        'name': 'Presidents Meeting 2027',
        'event_type': 'presmeet',
        'status': status,
        'start_date': '2027-05-15',
        'end_date': '2027-05-17',
        'location': 'Amsterdam, Netherlands',
        'landing_page': {
            'enabled': enabled,
            'slug': slug,
            'hero_image_url': 'https://s3.example.com/hero.jpg',
            'tagline': 'Join HD clubs from across Europe',
            'registration_label': 'Register Now',
            'logos': [
                {'name': 'H-DCN', 'logo_url': 'https://s3.example.com/hdcn.png'},
            ],
            'sections': [
                {'type': 'text', 'title': 'Program', 'content': 'Day 1: Welcome...'},
            ],
        },
        # Sensitive fields that should NOT appear in response
        'constraints': [{'type': 'max_per_club', 'value': 2}],
        'product_ids': ['prod-001', 'prod-002'],
        'order_scope': 'club',
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

        # Events table
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

class TestGetEventPublic:
    """Tests for the public event endpoint."""

    def test_options_request(self, setup_tables):
        """CORS preflight returns 200."""
        _, handler = setup_tables
        event = _make_event(method='OPTIONS')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

    def test_missing_slug_returns_400(self, setup_tables):
        """Returns 400 when no slug path parameter is provided."""
        _, handler = setup_tables
        event = _make_event(slug=None)
        event['pathParameters'] = None
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Missing slug' in body['error']

    def test_nonexistent_slug_returns_404(self, setup_tables):
        """Returns 404 when no event matches the slug."""
        _, handler = setup_tables
        event = _make_event(slug='nonexistent-event')
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()

    def test_disabled_landing_page_returns_404(self, setup_tables):
        """Returns 404 when the landing page exists but is disabled."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=False)

        event = _make_event(slug=TEST_SLUG)
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 404

    def test_returns_event_data_for_valid_slug(self, setup_tables):
        """Returns event data with landing page config for a valid slug."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=True, status='open')

        event = _make_event(slug=TEST_SLUG)
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['name'] == 'Presidents Meeting 2027'
        assert body['start_date'] == '2027-05-15'
        assert body['end_date'] == '2027-05-17'
        assert body['location'] == 'Amsterdam, Netherlands'
        assert body['registration_status'] == 'open'
        assert body['landing_page']['slug'] == TEST_SLUG
        assert body['landing_page']['tagline'] == 'Join HD clubs from across Europe'
        assert len(body['landing_page']['logos']) == 1
        assert len(body['landing_page']['sections']) == 1

    def test_excludes_sensitive_data(self, setup_tables):
        """Sensitive fields are NOT included in the response, but event_id IS (needed for booking redirect)."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=True)

        event = _make_event(slug=TEST_SLUG)
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        # These sensitive fields should not appear
        assert 'constraints' not in body
        assert 'product_ids' not in body
        assert 'order_scope' not in body
        # event_id IS included (needed for authenticated booking redirect)
        assert body['event_id'] == TEST_EVENT_ID

    def test_registration_status_closed(self, setup_tables):
        """Returns registration_status='closed' when event status is not 'open'."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=True, status='closed')

        event = _make_event(slug=TEST_SLUG)
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['registration_status'] == 'closed'

    def test_registration_status_locked(self, setup_tables):
        """Returns registration_status='closed' when event status is 'locked'."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=True, status='locked')

        event = _make_event(slug=TEST_SLUG)
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200

        body = json.loads(response['body'])
        assert body['registration_status'] == 'closed'

    def test_no_auth_required(self, setup_tables):
        """Endpoint works without Authorization header (public)."""
        events_table, handler = setup_tables
        _seed_event(events_table, slug=TEST_SLUG, enabled=True)

        # Event with no auth headers at all
        event = {
            'httpMethod': 'GET',
            'headers': {},
            'queryStringParameters': None,
            'pathParameters': {'slug': TEST_SLUG},
            'body': None,
        }
        response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 200
