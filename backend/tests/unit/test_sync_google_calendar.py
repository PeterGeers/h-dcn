"""
Unit tests for the sync_google_calendar handler.

Tests Google Calendar sync operations (create, update, delete) with
mocked Google Calendar API calls. Verifies idempotent behavior and
graceful error handling.
"""

import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


# ---------------------------------------------------------------------------
# Handler path setup (importlib pattern per testing conventions)
# ---------------------------------------------------------------------------

_handler_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'sync_google_calendar')
)
_handler_file = os.path.join(_handler_dir, 'app.py')

# Expose _handler_path for conftest.py cleanup
_handler_path = _handler_dir


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
# Environment setup
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['GOOGLE_CREDENTIALS_PARAMETER'] = '/h-dcn/google-credentials'
os.environ['GOOGLE_CALENDAR_ID'] = 'test-calendar-id'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def events_table():
    """Create a mocked DynamoDB Events table and load the handler within mock context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Insert a test event
        table.put_item(Item={
            'event_id': 'evt-123',
            'name': 'Test Event',
            'start_date': '2026-06-15',
            'end_date': '2026-06-16',
            'status': 'published',
        })

        # Load handler inside the mock context so DynamoDB resource is mocked
        handler_module = _load_handler()

        # Point the handler's table reference at the mocked table
        handler_module.events_table = table

        yield table, handler_module


@pytest.fixture
def mock_google_service():
    """Mock Google Calendar API service."""
    mock_service = MagicMock()
    mock_events = MagicMock()
    mock_service.events.return_value = mock_events

    # Default successful responses
    mock_events.insert.return_value.execute.return_value = {
        'id': 'gcal-new-event-id-123',
        'status': 'confirmed',
    }
    mock_events.update.return_value.execute.return_value = {
        'id': 'gcal-existing-id-456',
        'status': 'confirmed',
    }
    mock_events.delete.return_value.execute.return_value = None

    return mock_service, mock_events


# ---------------------------------------------------------------------------
# Helper to build API Gateway event
# ---------------------------------------------------------------------------

def _make_event(body: dict) -> dict:
    """Build a minimal API Gateway event."""
    return {
        'httpMethod': 'POST',
        'body': json.dumps(body),
        'headers': {'Content-Type': 'application/json'},
    }


def _make_options_event() -> dict:
    """Build a CORS preflight request."""
    return {
        'httpMethod': 'OPTIONS',
        'headers': {},
    }


# ---------------------------------------------------------------------------
# Tests: OPTIONS preflight
# ---------------------------------------------------------------------------

class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self, events_table):
        """OPTIONS request should return 200 with CORS headers."""
        _, handler_module = events_table
        response = handler_module.lambda_handler(_make_options_event(), None)
        assert response['statusCode'] == 200


# ---------------------------------------------------------------------------
# Tests: Sync action (create new event)
# ---------------------------------------------------------------------------

class TestSyncCreate:
    """Test creating a new Google Calendar event (no existing gcal_id)."""

    def test_sync_creates_event_when_no_gcal_id(self, events_table, mock_google_service):
        """When no google_calendar_event_id exists, should create a new Calendar event."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'sync',
            'event_data': {
                'name': 'Toerweekend 2026',
                'start_date': '2026-06-15',
                'end_date': '2026-06-16',
                'location': 'Amsterdam',
                'description': 'Annual touring weekend',
                'google_calendar_event_id': None,
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] == 'gcal-new-event-id-123'

        # Verify insert was called with correct body
        mock_events.insert.assert_called_once_with(
            calendarId='test-calendar-id',
            body={
                'summary': 'Toerweekend 2026',
                'start': {'date': '2026-06-15'},
                'end': {'date': '2026-06-16'},
                'location': 'Amsterdam',
                'description': 'Annual touring weekend',
            },
        )

    def test_sync_creates_event_without_optional_fields(self, events_table, mock_google_service):
        """Sync should work with minimal required fields (no location/description)."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'sync',
            'event_data': {
                'name': 'ALV Maart 2027',
                'start_date': '2027-03-10',
                'end_date': '2027-03-10',
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] == 'gcal-new-event-id-123'

        # Verify insert was called with empty defaults for optional fields
        mock_events.insert.assert_called_once_with(
            calendarId='test-calendar-id',
            body={
                'summary': 'ALV Maart 2027',
                'start': {'date': '2027-03-10'},
                'end': {'date': '2027-03-10'},
                'location': '',
                'description': '',
            },
        )


# ---------------------------------------------------------------------------
# Tests: Sync action (update existing event)
# ---------------------------------------------------------------------------

class TestSyncUpdate:
    """Test updating an existing Google Calendar event (gcal_id present)."""

    def test_sync_updates_event_when_gcal_id_present(self, events_table, mock_google_service):
        """When google_calendar_event_id exists, should update the Calendar event."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'sync',
            'event_data': {
                'name': 'Updated Toerweekend 2026',
                'start_date': '2026-06-20',
                'end_date': '2026-06-21',
                'location': 'Rotterdam',
                'description': 'Updated description',
                'google_calendar_event_id': 'gcal-existing-id-456',
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] == 'gcal-existing-id-456'

        # Verify update was called (not insert)
        mock_events.update.assert_called_once_with(
            calendarId='test-calendar-id',
            eventId='gcal-existing-id-456',
            body={
                'summary': 'Updated Toerweekend 2026',
                'start': {'date': '2026-06-20'},
                'end': {'date': '2026-06-21'},
                'location': 'Rotterdam',
                'description': 'Updated description',
            },
        )
        mock_events.insert.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Delete action
# ---------------------------------------------------------------------------

class TestDelete:
    """Test deleting a Google Calendar event."""

    def test_delete_removes_event_from_google_calendar(self, events_table, mock_google_service):
        """Delete action should call events().delete() and return null gcal_id."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'delete',
            'event_data': {
                'name': 'Old Event',
                'start_date': '2026-01-01',
                'end_date': '2026-01-01',
                'google_calendar_event_id': 'gcal-to-delete-789',
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] is None

        # Verify delete was called
        mock_events.delete.assert_called_once_with(
            calendarId='test-calendar-id',
            eventId='gcal-to-delete-789',
        )

    def test_delete_noop_when_no_gcal_id(self, events_table, mock_google_service):
        """Delete with no gcal_id should be a no-op (no API call)."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'delete',
            'event_data': {
                'name': 'Event Without GCal',
                'start_date': '2026-01-01',
                'end_date': '2026-01-01',
                'google_calendar_event_id': None,
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] is None

        # No API calls should have been made
        mock_events.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Test graceful error handling when Google Calendar API fails."""

    def test_sync_handles_google_api_failure_gracefully(self, events_table, mock_google_service):
        """Google API failure should be logged but not crash the handler."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        # Simulate Google API error
        mock_events.insert.return_value.execute.side_effect = Exception(
            'Google Calendar API quota exceeded'
        )

        body = {
            'event_id': 'evt-123',
            'action': 'sync',
            'event_data': {
                'name': 'Event That Fails Sync',
                'start_date': '2026-07-01',
                'end_date': '2026-07-01',
                'google_calendar_event_id': None,
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        # Should still return 200 — error is logged, not raised
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        # Returns the original gcal_id (None) since sync failed
        assert response_body['google_calendar_event_id'] is None

    def test_delete_handles_google_api_failure_gracefully(self, events_table, mock_google_service):
        """Delete failure should still return null gcal_id (cleared)."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        # Simulate Google API error on delete
        mock_events.delete.return_value.execute.side_effect = Exception(
            'Event not found in Google Calendar'
        )

        body = {
            'event_id': 'evt-123',
            'action': 'delete',
            'event_data': {
                'name': 'Event To Delete',
                'start_date': '2026-01-01',
                'end_date': '2026-01-01',
                'google_calendar_event_id': 'gcal-already-gone',
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            response = handler_module.lambda_handler(_make_event(body), None)

        # Should still return 200 with null gcal_id
        assert response['statusCode'] == 200
        response_body = json.loads(response['body'])
        assert response_body['google_calendar_event_id'] is None


# ---------------------------------------------------------------------------
# Tests: Validation
# ---------------------------------------------------------------------------

class TestValidation:
    """Test request validation."""

    def test_missing_body_returns_400(self, events_table):
        """Missing request body should return 400."""
        _, handler_module = events_table
        event = {'httpMethod': 'POST', 'body': None}
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_invalid_json_returns_400(self, events_table):
        """Invalid JSON body should return 400."""
        _, handler_module = events_table
        event = {'httpMethod': 'POST', 'body': 'not json'}
        response = handler_module.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_missing_event_id_returns_400(self, events_table):
        """Missing event_id should return 400."""
        _, handler_module = events_table
        body = {'action': 'sync', 'event_data': {'name': 'X', 'start_date': '2026-01-01', 'end_date': '2026-01-01'}}
        response = handler_module.lambda_handler(_make_event(body), None)
        assert response['statusCode'] == 400

    def test_invalid_action_returns_400(self, events_table):
        """Invalid action should return 400."""
        _, handler_module = events_table
        body = {'event_id': 'evt-1', 'action': 'invalid', 'event_data': {'name': 'X'}}
        response = handler_module.lambda_handler(_make_event(body), None)
        assert response['statusCode'] == 400

    def test_missing_name_for_sync_returns_400(self, events_table):
        """Sync without event_data.name should return 400."""
        _, handler_module = events_table
        body = {
            'event_id': 'evt-1',
            'action': 'sync',
            'event_data': {'start_date': '2026-01-01', 'end_date': '2026-01-01'},
        }
        response = handler_module.lambda_handler(_make_event(body), None)
        assert response['statusCode'] == 400

    def test_missing_start_date_for_sync_returns_400(self, events_table):
        """Sync without event_data.start_date should return 400."""
        _, handler_module = events_table
        body = {
            'event_id': 'evt-1',
            'action': 'sync',
            'event_data': {'name': 'Test', 'end_date': '2026-01-01'},
        }
        response = handler_module.lambda_handler(_make_event(body), None)
        assert response['statusCode'] == 400


# ---------------------------------------------------------------------------
# Tests: DynamoDB update of gcal_id
# ---------------------------------------------------------------------------

class TestDynamoDBUpdate:
    """Test that google_calendar_event_id is stored back on the event record."""

    def test_sync_stores_gcal_id_on_dynamodb_event(self, events_table, mock_google_service):
        """After successful sync, the gcal_id should be stored on the DynamoDB record."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        body = {
            'event_id': 'evt-123',
            'action': 'sync',
            'event_data': {
                'name': 'Sync Test',
                'start_date': '2026-08-01',
                'end_date': '2026-08-01',
                'google_calendar_event_id': None,
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            handler_module.lambda_handler(_make_event(body), None)

        # Check DynamoDB was updated
        item = table.get_item(Key={'event_id': 'evt-123'})['Item']
        assert item['google_calendar_event_id'] == 'gcal-new-event-id-123'

    def test_delete_removes_gcal_id_from_dynamodb_event(self, events_table, mock_google_service):
        """After successful delete, the gcal_id should be removed from DynamoDB record."""
        table, handler_module = events_table
        mock_service, mock_events = mock_google_service

        # First set a gcal_id on the event
        table.update_item(
            Key={'event_id': 'evt-123'},
            UpdateExpression='SET google_calendar_event_id = :gcal_id',
            ExpressionAttributeValues={':gcal_id': 'gcal-to-remove'},
        )

        body = {
            'event_id': 'evt-123',
            'action': 'delete',
            'event_data': {
                'name': 'Delete Test',
                'start_date': '2026-01-01',
                'end_date': '2026-01-01',
                'google_calendar_event_id': 'gcal-to-remove',
            },
        }

        with patch.object(handler_module, '_build_calendar_service', return_value=mock_service):
            handler_module.lambda_handler(_make_event(body), None)

        # Check DynamoDB: gcal_id should be removed
        item = table.get_item(Key={'event_id': 'evt-123'})['Item']
        assert 'google_calendar_event_id' not in item
