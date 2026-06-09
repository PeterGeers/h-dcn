"""
Unit tests for the channel-to-event_id transformation in the product migration script.

Tests the logic that replaces `channel`/`tenant` fields with `event_id` on product
records and removes `channel` from cart records.

Requirements: 1.16, 1.18, 10.12, 12.1
"""

import importlib
import sys
import os
import pytest
import boto3
from moto import mock_aws

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))


@pytest.fixture(autouse=True)
def _clear_module_cache():
    """Clear cached migrate_products module before each test."""
    if 'migrate_products' in sys.modules:
        del sys.modules['migrate_products']
    yield
    if 'migrate_products' in sys.modules:
        del sys.modules['migrate_products']


@pytest.fixture
def aws_env():
    """Set up mocked AWS environment."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'


@pytest.fixture
def dynamodb_tables(aws_env):
    """Create mocked DynamoDB tables for Producten, Events, and Carts."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Events table
        events = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'event_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Carts table
        carts = dynamodb.create_table(
            TableName='Carts',
            KeySchema=[{'AttributeName': 'cart_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'cart_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        yield {
            'producten': producten,
            'events': events,
            'carts': carts,
            'dynamodb': dynamodb,
        }


class TestBuildProductToEventMap:
    """Tests for _build_product_to_event_map."""

    def test_builds_map_from_events(self, dynamodb_tables):
        from migrate_products import _build_product_to_event_map

        events_table = dynamodb_tables['events']

        # Seed events with product_ids
        events_table.put_item(Item={
            'event_id': 'evt-001',
            'name': 'PresMeet 2025',
            'product_ids': ['prod_ticket_1', 'prod_party_1'],
        })
        events_table.put_item(Item={
            'event_id': 'evt-002',
            'name': 'Rally 2025',
            'product_ids': ['prod_rally_ticket'],
        })

        result = _build_product_to_event_map(events_table)

        assert result == {
            'prod_ticket_1': 'evt-001',
            'prod_party_1': 'evt-001',
            'prod_rally_ticket': 'evt-002',
        }

    def test_empty_events_table(self, dynamodb_tables):
        from migrate_products import _build_product_to_event_map

        result = _build_product_to_event_map(dynamodb_tables['events'])
        assert result == {}

    def test_event_without_product_ids(self, dynamodb_tables):
        from migrate_products import _build_product_to_event_map

        events_table = dynamodb_tables['events']
        events_table.put_item(Item={
            'event_id': 'evt-003',
            'name': 'Empty Event',
        })

        result = _build_product_to_event_map(events_table)
        assert result == {}

    def test_event_with_empty_product_ids(self, dynamodb_tables):
        from migrate_products import _build_product_to_event_map

        events_table = dynamodb_tables['events']
        events_table.put_item(Item={
            'event_id': 'evt-004',
            'name': 'No Products Event',
            'product_ids': [],
        })

        result = _build_product_to_event_map(events_table)
        assert result == {}


class TestResolveEventIdForProduct:
    """Tests for _resolve_event_id_for_product."""

    def test_hdcn_channel_returns_none(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_1', 'channel': 'h-dcn'}
        result = _resolve_event_id_for_product(product, {})
        assert result is None

    def test_no_channel_returns_none(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_1'}
        result = _resolve_event_id_for_product(product, {})
        assert result is None

    def test_empty_channel_returns_none(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_1', 'channel': ''}
        result = _resolve_event_id_for_product(product, {})
        assert result is None

    def test_presmeet_channel_with_linked_event(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_ticket_1', 'channel': 'presmeet'}
        product_to_event = {'prod_ticket_1': 'evt-001'}
        result = _resolve_event_id_for_product(product, product_to_event)
        assert result == 'evt-001'

    def test_presmeet_channel_with_legacy_id_fallback(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'new-uuid', 'id': 'old-legacy-id', 'channel': 'presmeet'}
        product_to_event = {'old-legacy-id': 'evt-002'}
        result = _resolve_event_id_for_product(product, product_to_event)
        assert result == 'evt-002'

    def test_presmeet_channel_not_found_in_events(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_orphan', 'channel': 'presmeet'}
        result = _resolve_event_id_for_product(product, {})
        assert result is None

    def test_unknown_channel_returns_none(self):
        from migrate_products import _resolve_event_id_for_product

        product = {'product_id': 'prod_1', 'channel': 'unknown_channel'}
        result = _resolve_event_id_for_product(product, {})
        assert result is None


class TestTransformChannelsToEventIds:
    """Integration tests for transform_channels_to_event_ids."""

    def test_transforms_presmeet_product(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        # Seed event with product link
        events.put_item(Item={
            'event_id': 'evt-presmeet-2025',
            'name': 'PresMeet 2025',
            'product_ids': ['prod_meeting_ticket'],
        })

        # Seed presmeet product
        producten.put_item(Item={
            'product_id': 'prod_meeting_ticket',
            'name': 'Meeting Ticket',
            'channel': 'presmeet',
            'tenant': 'presmeet',
            'is_parent': True,
            'active': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        assert result['channel_transformations'] == 1
        assert len(result['errors']) == 0

        # Verify the product was updated
        item = producten.get_item(Key={'product_id': 'prod_meeting_ticket'})['Item']
        assert item['event_id'] == 'evt-presmeet-2025'
        assert 'channel' not in item
        assert 'tenant' not in item

    def test_transforms_hdcn_product(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        # Seed h-dcn product
        producten.put_item(Item={
            'product_id': 'prod_tshirt',
            'name': 'Club T-shirt',
            'channel': 'h-dcn',
            'tenant': 'h-dcn',
            'is_parent': True,
            'active': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        assert result['channel_transformations'] == 1

        item = producten.get_item(Key={'product_id': 'prod_tshirt'})['Item']
        assert item.get('event_id') is None
        assert 'channel' not in item
        assert 'tenant' not in item

    def test_skips_products_without_channel(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        # Seed product without channel
        producten.put_item(Item={
            'product_id': 'prod_already_migrated',
            'name': 'Already Clean',
            'event_id': 'evt-001',
            'is_parent': True,
            'active': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        assert result['channel_transformations'] == 0

        # Verify it was untouched
        item = producten.get_item(Key={'product_id': 'prod_already_migrated'})['Item']
        assert item['event_id'] == 'evt-001'

    def test_presmeet_product_not_in_any_event(self, dynamodb_tables):
        """Products with channel=presmeet but not in any event get event_id=null."""
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        # No events with this product
        producten.put_item(Item={
            'product_id': 'prod_orphan_presmeet',
            'name': 'Orphan Presmeet Product',
            'channel': 'presmeet',
            'is_parent': True,
            'active': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        assert result['channel_transformations'] == 1

        item = producten.get_item(Key={'product_id': 'prod_orphan_presmeet'})['Item']
        assert item.get('event_id') is None
        assert 'channel' not in item

    def test_dry_run_does_not_modify(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        producten.put_item(Item={
            'product_id': 'prod_dry',
            'name': 'Dry Run Product',
            'channel': 'h-dcn',
            'tenant': 'h-dcn',
            'is_parent': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=True, carts_table=carts
        )

        assert result['channel_transformations'] == 1

        # Verify not modified
        item = producten.get_item(Key={'product_id': 'prod_dry'})['Item']
        assert item['channel'] == 'h-dcn'
        assert item['tenant'] == 'h-dcn'
        assert 'event_id' not in item

    def test_multiple_products_mixed_channels(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        events.put_item(Item={
            'event_id': 'evt-pm-2025',
            'name': 'PresMeet 2025',
            'product_ids': ['prod_pm_ticket'],
        })

        # h-dcn product
        producten.put_item(Item={
            'product_id': 'prod_webshop',
            'name': 'Webshop Item',
            'channel': 'h-dcn',
            'is_parent': True,
        })
        # presmeet product linked to event
        producten.put_item(Item={
            'product_id': 'prod_pm_ticket',
            'name': 'PresMeet Ticket',
            'channel': 'presmeet',
            'tenant': 'presmeet',
            'is_parent': True,
        })
        # product without channel (already clean)
        producten.put_item(Item={
            'product_id': 'prod_clean',
            'name': 'Clean Product',
            'is_parent': True,
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        # 2 products had channel field
        assert result['channel_transformations'] == 2

        # Verify webshop product
        item1 = producten.get_item(Key={'product_id': 'prod_webshop'})['Item']
        assert item1.get('event_id') is None
        assert 'channel' not in item1

        # Verify presmeet product
        item2 = producten.get_item(Key={'product_id': 'prod_pm_ticket'})['Item']
        assert item2['event_id'] == 'evt-pm-2025'
        assert 'channel' not in item2
        assert 'tenant' not in item2

        # Verify clean product untouched
        item3 = producten.get_item(Key={'product_id': 'prod_clean'})['Item']
        assert 'event_id' not in item3
        assert 'channel' not in item3


class TestRemoveChannelFromCarts:
    """Tests for removing channel from cart records."""

    def test_removes_channel_from_carts(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        # Seed carts with channel
        carts.put_item(Item={
            'cart_id': 'cart-001',
            'channel': 'h-dcn',
            'items': [],
        })
        carts.put_item(Item={
            'cart_id': 'cart-002',
            'channel': 'presmeet',
            'items': [],
        })
        carts.put_item(Item={
            'cart_id': 'cart-003',
            'items': [],  # no channel
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=False, carts_table=carts
        )

        assert result['cart_channel_removals'] == 2

        # Verify carts were updated
        cart1 = carts.get_item(Key={'cart_id': 'cart-001'})['Item']
        assert 'channel' not in cart1

        cart2 = carts.get_item(Key={'cart_id': 'cart-002'})['Item']
        assert 'channel' not in cart2

        # Cart without channel should be untouched
        cart3 = carts.get_item(Key={'cart_id': 'cart-003'})['Item']
        assert 'channel' not in cart3

    def test_dry_run_does_not_modify_carts(self, dynamodb_tables):
        from migrate_products import transform_channels_to_event_ids

        producten = dynamodb_tables['producten']
        events = dynamodb_tables['events']
        carts = dynamodb_tables['carts']

        carts.put_item(Item={
            'cart_id': 'cart-dry',
            'channel': 'h-dcn',
            'items': [],
        })

        result = transform_channels_to_event_ids(
            producten, events, dry_run=True, carts_table=carts
        )

        assert result['cart_channel_removals'] == 1

        # Verify not modified
        cart = carts.get_item(Key={'cart_id': 'cart-dry'})['Item']
        assert cart['channel'] == 'h-dcn'
