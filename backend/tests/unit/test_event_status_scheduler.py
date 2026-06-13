"""
Unit tests for the event_status_scheduler handler.

Tests cover:
- 12.1: Scheduled Lambda checks event dates
- 12.2: Transition draft → open when registration_open <= today
- 12.3: Transition open → closed when registration_close <= today
- 12.4: On close transition: auto-lock submitted orders with status_history entry
- 12.5: SAM template addition (documented, not code-tested)

Requirements: 4.4, 4.5, 4.6
"""

import json
import os
import sys
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws
from datetime import date

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'event_status_scheduler')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


@pytest.fixture
def tables():
    """Create mocked Events and Orders DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create Orders table with GSI event-member-index
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
                {'AttributeName': 'source_id', 'AttributeType': 'S'},
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'event-member-index',
                    'KeySchema': [
                        {'AttributeName': 'source_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'member_id', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Ensure handler uses our mocked tables
        if _handler_path in sys.path:
            sys.path.remove(_handler_path)
        sys.path.insert(0, _handler_path)

        if 'app' in sys.modules:
            del sys.modules['app']

        import app as handler_module
        handler_module.events_table = events_table
        handler_module.orders_table = orders_table

        yield {'events': events_table, 'orders': orders_table}


def _put_event(table, event_id, status, reg_open=None, reg_close=None):
    """Helper to insert an event record."""
    item = {
        'event_id': event_id,
        'name': f'Test Event {event_id}',
        'event_type': 'presmeet',
        'status': status,
    }
    if reg_open:
        item['registration_open'] = reg_open
    if reg_close:
        item['registration_close'] = reg_close
    table.put_item(Item=item)


def _put_order(table, order_id, event_id, member_id, status, status_history=None):
    """Helper to insert an order record."""
    item = {
        'order_id': order_id,
        'source_id': event_id,
        'member_id': member_id,
        'status': status,
        'total_amount': 100,
        'items': [],
    }
    if status_history:
        item['status_history'] = status_history
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# Tests: draft → open transition (12.2, Req 4.4)
# ---------------------------------------------------------------------------

class TestDraftToOpen:
    """Test automatic transition from draft to open when registration_open <= today."""

    def test_draft_event_transitions_to_open_when_reg_open_is_today(self, tables):
        """Event in draft with registration_open = today should become open."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-1', 'draft', reg_open=today)

        result = handler_module.lambda_handler({}, {})

        assert 'evt-1' in result['opened']
        item = tables['events'].get_item(Key={'event_id': 'evt-1'})['Item']
        assert item['status'] == 'open'

    def test_draft_event_transitions_to_open_when_reg_open_is_past(self, tables):
        """Event in draft with registration_open in the past should become open."""
        import app as handler_module

        _put_event(tables['events'], 'evt-2', 'draft', reg_open='2020-01-01')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-2' in result['opened']
        item = tables['events'].get_item(Key={'event_id': 'evt-2'})['Item']
        assert item['status'] == 'open'

    def test_draft_event_stays_draft_when_reg_open_is_future(self, tables):
        """Event in draft with registration_open in the future should stay draft."""
        import app as handler_module

        _put_event(tables['events'], 'evt-3', 'draft', reg_open='2099-12-31')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-3' not in result['opened']
        item = tables['events'].get_item(Key={'event_id': 'evt-3'})['Item']
        assert item['status'] == 'draft'

    def test_draft_event_without_reg_open_stays_draft(self, tables):
        """Event in draft without registration_open set should stay draft."""
        import app as handler_module

        _put_event(tables['events'], 'evt-4', 'draft')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-4' not in result['opened']
        item = tables['events'].get_item(Key={'event_id': 'evt-4'})['Item']
        assert item['status'] == 'draft'


# ---------------------------------------------------------------------------
# Tests: open → closed transition (12.3, Req 4.5)
# ---------------------------------------------------------------------------

class TestOpenToClosed:
    """Test automatic transition from open to closed when registration_close <= today."""

    def test_open_event_transitions_to_closed_when_reg_close_is_today(self, tables):
        """Event in open with registration_close = today should become closed."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-5', 'open', reg_close=today)

        result = handler_module.lambda_handler({}, {})

        assert 'evt-5' in result['closed']
        item = tables['events'].get_item(Key={'event_id': 'evt-5'})['Item']
        assert item['status'] == 'closed'

    def test_open_event_transitions_to_closed_when_reg_close_is_past(self, tables):
        """Event in open with registration_close in the past should become closed."""
        import app as handler_module

        _put_event(tables['events'], 'evt-6', 'open', reg_close='2020-01-01')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-6' in result['closed']
        item = tables['events'].get_item(Key={'event_id': 'evt-6'})['Item']
        assert item['status'] == 'closed'

    def test_open_event_stays_open_when_reg_close_is_future(self, tables):
        """Event in open with registration_close in the future should stay open."""
        import app as handler_module

        _put_event(tables['events'], 'evt-7', 'open', reg_close='2099-12-31')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-7' not in result['closed']
        item = tables['events'].get_item(Key={'event_id': 'evt-7'})['Item']
        assert item['status'] == 'open'

    def test_open_event_without_reg_close_stays_open(self, tables):
        """Event in open without registration_close set should stay open."""
        import app as handler_module

        _put_event(tables['events'], 'evt-8', 'open')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-8' not in result['closed']
        item = tables['events'].get_item(Key={'event_id': 'evt-8'})['Item']
        assert item['status'] == 'open'


# ---------------------------------------------------------------------------
# Tests: Auto-lock orders on close (12.4, Req 4.6)
# ---------------------------------------------------------------------------

class TestAutoLockOrders:
    """Test that submitted orders are locked when event closes."""

    def test_submitted_orders_are_locked_on_close(self, tables):
        """When event closes, submitted orders should be locked."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-close', 'open', reg_close=today)
        _put_order(tables['orders'], 'ord-1', 'evt-close', 'member-a', 'submitted')
        _put_order(tables['orders'], 'ord-2', 'evt-close', 'member-b', 'submitted')

        result = handler_module.lambda_handler({}, {})

        assert result['orders_locked'] == 2

        ord1 = tables['orders'].get_item(Key={'order_id': 'ord-1'})['Item']
        assert ord1['status'] == 'locked'

        ord2 = tables['orders'].get_item(Key={'order_id': 'ord-2'})['Item']
        assert ord2['status'] == 'locked'

    def test_locked_orders_have_status_history_entry(self, tables):
        """Auto-locked orders get a status_history entry with correct fields."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-hist', 'open', reg_close=today)
        _put_order(tables['orders'], 'ord-hist', 'evt-hist', 'member-c', 'submitted')

        handler_module.lambda_handler({}, {})

        order = tables['orders'].get_item(Key={'order_id': 'ord-hist'})['Item']
        assert len(order['status_history']) == 1

        entry = order['status_history'][0]
        assert entry['from'] == 'submitted'
        assert entry['to'] == 'locked'
        assert entry['by'] == 'system'
        assert entry['source'] == 'auto_close'
        assert 'at' in entry

    def test_draft_orders_are_not_locked_on_close(self, tables):
        """Draft orders should not be locked when event closes."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-draft', 'open', reg_close=today)
        _put_order(tables['orders'], 'ord-draft', 'evt-draft', 'member-d', 'draft')

        result = handler_module.lambda_handler({}, {})

        assert result['orders_locked'] == 0
        order = tables['orders'].get_item(Key={'order_id': 'ord-draft'})['Item']
        assert order['status'] == 'draft'

    def test_already_locked_orders_are_not_relocked(self, tables):
        """Orders already locked should not be affected."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-already', 'open', reg_close=today)
        _put_order(tables['orders'], 'ord-locked', 'evt-already', 'member-e', 'locked',
                   status_history=[{'from': 'submitted', 'to': 'locked', 'at': '2024-01-01', 'by': 'admin', 'source': 'manual'}])

        result = handler_module.lambda_handler({}, {})

        # Should not try to lock an already-locked order
        assert result['orders_locked'] == 0
        order = tables['orders'].get_item(Key={'order_id': 'ord-locked'})['Item']
        assert order['status'] == 'locked'
        # Original status_history preserved
        assert len(order['status_history']) == 1

    def test_existing_status_history_is_preserved(self, tables):
        """Existing status_history entries are preserved when locking."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-pres', 'open', reg_close=today)
        existing_history = [
            {'from': 'draft', 'to': 'submitted', 'at': '2024-01-10', 'by': 'user@club.nl', 'source': 'delegate'}
        ]
        _put_order(tables['orders'], 'ord-pres', 'evt-pres', 'member-f', 'submitted',
                   status_history=existing_history)

        handler_module.lambda_handler({}, {})

        order = tables['orders'].get_item(Key={'order_id': 'ord-pres'})['Item']
        assert len(order['status_history']) == 2
        assert order['status_history'][0] == existing_history[0]
        assert order['status_history'][1]['from'] == 'submitted'
        assert order['status_history'][1]['to'] == 'locked'

    def test_no_orders_for_event_results_in_zero_locked(self, tables):
        """Event with no orders still transitions, with 0 orders locked."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-empty', 'open', reg_close=today)

        result = handler_module.lambda_handler({}, {})

        assert 'evt-empty' in result['closed']
        assert result['orders_locked'] == 0


# ---------------------------------------------------------------------------
# Tests: Events not affected (filter correctness)
# ---------------------------------------------------------------------------

class TestNonAffectedEvents:
    """Test that closed/archived events and non-matching events are not touched."""

    def test_closed_events_are_not_scanned(self, tables):
        """Events already in closed status are not processed."""
        import app as handler_module

        _put_event(tables['events'], 'evt-closed', 'closed', reg_close='2020-01-01')

        result = handler_module.lambda_handler({}, {})

        assert result['opened'] == []
        assert result['closed'] == []

    def test_multiple_events_processed_correctly(self, tables):
        """Multiple events in different states are handled independently."""
        import app as handler_module

        today = date.today().isoformat()
        _put_event(tables['events'], 'evt-a', 'draft', reg_open=today)
        _put_event(tables['events'], 'evt-b', 'open', reg_close=today)
        _put_event(tables['events'], 'evt-c', 'draft', reg_open='2099-01-01')
        _put_event(tables['events'], 'evt-d', 'open', reg_close='2099-01-01')

        _put_order(tables['orders'], 'ord-b1', 'evt-b', 'member-x', 'submitted')

        result = handler_module.lambda_handler({}, {})

        assert 'evt-a' in result['opened']
        assert 'evt-b' in result['closed']
        assert 'evt-c' not in result['opened']
        assert 'evt-d' not in result['closed']
        assert result['orders_locked'] == 1

    def test_scheduler_returns_today_date(self, tables):
        """Result includes today's date for logging/debugging."""
        import app as handler_module

        result = handler_module.lambda_handler({}, {})

        assert result['today'] == date.today().isoformat()
