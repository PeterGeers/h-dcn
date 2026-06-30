"""
Unit tests for shared.event_access module.

Tests has_event_access() and get_member_allowed_events() which provide
data-driven event access control via the allowed_events field on Members records.
"""

import importlib.util
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
os.environ['MEMBERS_TABLE_NAME'] = 'Members'

# Path to the module under test
_module_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python', 'shared', 'event_access.py'
    )
)


def _load_event_access():
    """Load event_access module by file path using importlib.util."""
    module_name = 'shared.event_access'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _module_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def members_table_with_module():
    """
    Create mocked Members table and load the event_access module inside
    the mock_aws context so boto3 resources are intercepted.
    """
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Load the module inside mock context
        module = _load_event_access()

        yield table, module


# ---------------------------------------------------------------------------
# Tests: has_event_access
# ---------------------------------------------------------------------------

class TestHasEventAccess:
    """Tests for has_event_access(member_id, event_id)."""

    def test_returns_true_when_event_in_allowed_events(self, members_table_with_module):
        """has_event_access returns True when event_id is in allowed_events."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': ['event-abc', 'event-def'],
        })

        assert mod.has_event_access('member-1', 'event-abc') is True

    def test_returns_false_when_event_not_in_allowed_events(self, members_table_with_module):
        """has_event_access returns False when event_id is NOT in allowed_events."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': ['event-abc', 'event-def'],
        })

        assert mod.has_event_access('member-1', 'event-xyz') is False

    def test_returns_false_when_member_does_not_exist(self, members_table_with_module):
        """has_event_access returns False when member doesn't exist."""
        _table, mod = members_table_with_module

        assert mod.has_event_access('nonexistent-member', 'event-abc') is False

    def test_returns_false_when_allowed_events_field_missing(self, members_table_with_module):
        """has_event_access returns False when allowed_events field is missing."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'name': 'Test Member',
            # No allowed_events field
        })

        assert mod.has_event_access('member-1', 'event-abc') is False

    def test_returns_false_when_allowed_events_is_empty_list(self, members_table_with_module):
        """has_event_access returns False when allowed_events is empty list."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': [],
        })

        assert mod.has_event_access('member-1', 'event-abc') is False

    def test_handles_multiple_events_correctly(self, members_table_with_module):
        """has_event_access handles multiple events in allowed_events correctly."""
        table, mod = members_table_with_module
        events = ['event-1', 'event-2', 'event-3', 'event-4', 'event-5']
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': events,
        })

        # All listed events should return True
        for event_id in events:
            assert mod.has_event_access('member-1', event_id) is True

        # Unlisted event should return False
        assert mod.has_event_access('member-1', 'event-99') is False


# ---------------------------------------------------------------------------
# Tests: get_member_allowed_events
# ---------------------------------------------------------------------------

class TestGetMemberAllowedEvents:
    """Tests for get_member_allowed_events(member_id)."""

    def test_returns_list_when_member_exists(self, members_table_with_module):
        """get_member_allowed_events returns the list when member exists."""
        table, mod = members_table_with_module
        expected_events = ['event-abc', 'event-def', 'event-ghi']
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': expected_events,
        })

        result = mod.get_member_allowed_events('member-1')
        assert result == expected_events

    def test_returns_empty_list_when_member_does_not_exist(self, members_table_with_module):
        """get_member_allowed_events returns empty list when member doesn't exist."""
        _table, mod = members_table_with_module

        result = mod.get_member_allowed_events('nonexistent-member')
        assert result == []

    def test_returns_empty_list_when_field_is_missing(self, members_table_with_module):
        """get_member_allowed_events returns empty list when field is missing."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'name': 'Test Member',
            # No allowed_events field
        })

        result = mod.get_member_allowed_events('member-1')
        assert result == []


# ---------------------------------------------------------------------------
# Tests: verify_order_event_access
# ---------------------------------------------------------------------------

class TestVerifyOrderEventAccess:
    """Tests for verify_order_event_access(order, member_id) — Req 16.5, 16.7."""

    def test_grants_access_when_event_in_allowed_and_is_primary_delegate(self, members_table_with_module):
        """Access granted: event in allowed_events AND member is primary delegate."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': ['event-abc'],
        })

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'delegates': {
                'primary_member_id': 'member-1',
                'secondary_member_id': None,
            },
        }

        assert mod.verify_order_event_access(order, 'member-1') is True

    def test_grants_access_when_event_in_allowed_and_is_secondary_delegate(self, members_table_with_module):
        """Access granted: event in allowed_events AND member is secondary delegate."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-2',
            'allowed_events': ['event-abc'],
        })

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'delegates': {
                'primary_member_id': 'member-1',
                'secondary_member_id': 'member-2',
            },
        }

        assert mod.verify_order_event_access(order, 'member-2') is True

    def test_denies_access_when_event_not_in_allowed_events(self, members_table_with_module):
        """Access denied: event NOT in allowed_events (even if user is a delegate)."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': ['event-other'],
        })

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'delegates': {
                'primary_member_id': 'member-1',
                'secondary_member_id': None,
            },
        }

        assert mod.verify_order_event_access(order, 'member-1') is False

    def test_denies_access_when_not_a_delegate(self, members_table_with_module):
        """Access denied: event in allowed_events but user is NOT a delegate."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-3',
            'allowed_events': ['event-abc'],
        })

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'delegates': {
                'primary_member_id': 'member-1',
                'secondary_member_id': 'member-2',
            },
        }

        assert mod.verify_order_event_access(order, 'member-3') is False

    def test_grants_access_for_webshop_orders(self, members_table_with_module):
        """Webshop orders (source_id='webshop') skip event access check."""
        _table, mod = members_table_with_module

        order = {
            'order_id': 'order-1',
            'source_id': 'webshop',
            'member_id': 'member-1',
        }

        # No event access setup needed — webshop orders always pass
        assert mod.verify_order_event_access(order, 'member-1') is True

    def test_grants_access_for_orders_without_event_id(self, members_table_with_module):
        """Orders without event_id skip event access check."""
        _table, mod = members_table_with_module

        order = {
            'order_id': 'order-1',
            'member_id': 'member-1',
        }

        assert mod.verify_order_event_access(order, 'member-1') is True

    def test_falls_back_to_member_id_when_no_delegates_field(self, members_table_with_module):
        """Orders without delegates field use member_id for ownership check."""
        table, mod = members_table_with_module
        table.put_item(Item={
            'member_id': 'member-1',
            'allowed_events': ['event-abc'],
        })

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'member_id': 'member-1',
            # No delegates field
        }

        assert mod.verify_order_event_access(order, 'member-1') is True
        assert mod.verify_order_event_access(order, 'member-other') is False

    def test_denies_when_member_does_not_exist(self, members_table_with_module):
        """Access denied when member record doesn't exist (no allowed_events)."""
        _table, mod = members_table_with_module

        order = {
            'order_id': 'order-1',
            'event_id': 'event-abc',
            'source_id': 'event-abc',
            'delegates': {
                'primary_member_id': 'nonexistent',
            },
        }

        assert mod.verify_order_event_access(order, 'nonexistent') is False
