"""
Unit Tests for get_order Lambda Handler.

Tests the unified get_order handler:
- Returns 400 when source_id is missing
- Webshop source: returns 403 when user doesn't have hdcnLeden group
- Webshop source: creates draft order when no existing order
- Webshop source: returns existing order when one exists
- Event source: returns 404 when event doesn't exist
- Event source: returns 403 when member doesn't have event access
- Event source (member scope): creates draft order for new member
- Event source (member scope): returns existing order
- Event source (registry_row scope): creates draft order with member as primary delegate
- Event source (registry_row scope): returns 403 when member has no registry_row_id
- Event source (registry_row scope): returns existing row order when member is delegate
- Event source (registry_row scope): returns 403 when member is not a delegate
"""

import importlib.util
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Environment setup (must be set before module import)
# ---------------------------------------------------------------------------

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-registry-bucket'

# Path to the handler under test
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_order', 'app.py')
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

TEST_EVENT_ID = 'evt-12345678-1234-1234-1234-123456789abc'
TEST_MEMBER_ID = 'mem-001'
TEST_MEMBER_EMAIL = 'user@h-dcn.nl'
TEST_REGISTRY_ROW_ID = 'row-nl-001'
TEST_REGISTRY_S3_PATH = 'events/test-event/invitee_registry.json'


def _make_event(query_params=None, method='GET'):
    """Create a minimal API Gateway event."""
    return {
        'httpMethod': method,
        'headers': {'Authorization': 'Bearer test-token'},
        'queryStringParameters': query_params,
        'pathParameters': None,
        'body': None,
    }


# ---------------------------------------------------------------------------
# Auth patches helper
# ---------------------------------------------------------------------------

def _auth_patches(email=TEST_MEMBER_EMAIL, roles=None):
    """Return a patch.multiple context for auth functions."""
    if roles is None:
        roles = ['hdcnLeden']
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: (email, roles, None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_tables():
    """
    Create mocked DynamoDB tables with correct schemas and GSI,
    seed test data, and load handler inside mock_aws context.
    """
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Orders table with GSI event-member-index
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

        # Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed test member
        members_table.put_item(Item={
            'member_id': TEST_MEMBER_ID,
            'email': TEST_MEMBER_EMAIL,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'registry_row_id': TEST_REGISTRY_ROW_ID,
        })

        # Seed test event (member-scoped, no registry_config)
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Test Rally 2025',
            'status': 'published',
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'events': events_table,
            'members': members_table,
            'handler': handler,
        }


@pytest.fixture
def setup_tables_registry_row_scope():
    """
    Same as setup_tables but with a registry-row-scoped event (has registry_config).
    Includes S3 mock with registry data.
    """
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Orders table with GSI
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

        # Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # S3 bucket with registry file
        s3_client = boto3.client('s3', region_name='eu-west-1')
        s3_client.create_bucket(
            Bucket='test-registry-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        registry_data = json.dumps({
            'rows': [
                {'row_id': TEST_REGISTRY_ROW_ID, 'label': 'H-DCN Nederland', 'logo_url': 'https://cdn.example.com/logo.png'},
                {'row_id': 'row-nl-002', 'label': 'H-DCN Belgium'},
            ]
        })
        s3_client.put_object(
            Bucket='test-registry-bucket',
            Key=TEST_REGISTRY_S3_PATH,
            Body=registry_data.encode('utf-8'),
        )

        # Seed member WITH registry_row_id
        members_table.put_item(Item={
            'member_id': TEST_MEMBER_ID,
            'email': TEST_MEMBER_EMAIL,
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'registry_row_id': TEST_REGISTRY_ROW_ID,
        })

        # Seed member WITHOUT registry_row_id
        members_table.put_item(Item={
            'member_id': 'mem-no-row',
            'email': 'norowuser@h-dcn.nl',
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
        })

        # Seed registry-row-scoped event (has registry_config)
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Presidents Meeting 2025',
            'status': 'published',
            'participation': 'closed',
            'registry_config': {
                's3_path': TEST_REGISTRY_S3_PATH,
                'row_label': 'club',
            },
        })

        # Load handler inside mock context
        handler = _load_handler()

        yield {
            'orders': orders_table,
            'events': events_table,
            'members': members_table,
            'handler': handler,
        }


# ---------------------------------------------------------------------------
# Tests: Missing parameters
# ---------------------------------------------------------------------------

class TestMissingParameters:
    """Tests for missing required parameters."""

    def test_returns_400_when_source_id_is_missing(self, setup_tables):
        """Handler returns 400 when source_id query parameter is not provided."""
        handler = setup_tables['handler']

        with _auth_patches():
            event = _make_event(query_params=None)
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'source_id' in body.get('error', '').lower()


# ---------------------------------------------------------------------------
# Tests: Webshop source
# ---------------------------------------------------------------------------

class TestWebshopSource:
    """Tests for source_id = 'webshop'."""

    def test_returns_403_when_user_not_in_hdcnleden_group(self, setup_tables):
        """Webshop access requires hdcnLeden group membership."""
        handler = setup_tables['handler']

        # User with event_participant role only (no hdcnLeden)
        with _auth_patches(roles=['event_participant']):
            event = _make_event(query_params={'source_id': 'webshop'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'member access' in body.get('error', '').lower()

    def test_creates_draft_order_when_no_existing_order(self, setup_tables):
        """Webshop creates a new draft order when member has no existing webshop order."""
        handler = setup_tables['handler']

        with _auth_patches():
            event = _make_event(query_params={'source_id': 'webshop'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['status'] == 'draft'
        assert body['source_id'] == 'webshop'
        assert body['member_id'] == TEST_MEMBER_ID
        assert 'order_id' in body

    def test_returns_existing_order_when_one_exists(self, setup_tables):
        """Webshop returns existing order for member instead of creating new one."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed an existing webshop order
        orders_table.put_item(Item={
            'order_id': 'existing-order-001',
            'source_id': 'webshop',
            'member_id': TEST_MEMBER_ID,
            'status': 'draft',
            'items': [],
            'version': 1,
        })

        with _auth_patches():
            event = _make_event(query_params={'source_id': 'webshop'})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'existing-order-001'
        assert body['source_id'] == 'webshop'


# ---------------------------------------------------------------------------
# Tests: Event source
# ---------------------------------------------------------------------------

class TestEventSource:
    """Tests for source_id = event UUID."""

    def test_returns_404_when_event_does_not_exist(self, setup_tables):
        """Returns 404 when event UUID is not found in Events table."""
        handler = setup_tables['handler']

        non_existent_event_id = 'evt-does-not-exist-000'
        with _auth_patches():
            event = _make_event(query_params={'source_id': non_existent_event_id})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body.get('error', '').lower()

    def test_returns_403_when_member_has_no_event_access(self, setup_tables):
        """Returns 403 when member doesn't have the event in allowed_events (closed event)."""
        handler = setup_tables['handler']
        members_table = setup_tables['members']
        events_table = setup_tables['events']

        # Update event to closed participation
        events_table.put_item(Item={
            'event_id': TEST_EVENT_ID,
            'name': 'Test Rally 2025',
            'status': 'published',
            'participation': 'closed',
        })

        # Create a member WITHOUT access to the test event
        members_table.put_item(Item={
            'member_id': 'mem-no-access',
            'email': 'noaccess@h-dcn.nl',
            'member_type': 'hdcn_member',
            'allowed_events': [],  # No event access
        })

        with _auth_patches(email='noaccess@h-dcn.nl'):
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body.get('error_code') == 'EVENT_ACCESS_DENIED'


# ---------------------------------------------------------------------------
# Tests: Event source - member scope
# ---------------------------------------------------------------------------

class TestEventMemberScope:
    """Tests for event source with order_scope = 'member'."""

    def test_creates_draft_order_for_new_member(self, setup_tables):
        """Creates a new draft order when member has no existing order for this event."""
        handler = setup_tables['handler']

        with _auth_patches():
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['status'] == 'draft'
        assert body['source_id'] == TEST_EVENT_ID
        assert body['member_id'] == TEST_MEMBER_ID
        assert 'order_id' in body
        # Member-scoped orders should NOT have registry_row_id or delegates
        assert 'delegates' not in body

    def test_returns_existing_order(self, setup_tables):
        """Returns existing member order instead of creating a new one."""
        handler = setup_tables['handler']
        orders_table = setup_tables['orders']

        # Seed an existing event order
        orders_table.put_item(Item={
            'order_id': 'evt-order-001',
            'source_id': TEST_EVENT_ID,
            'member_id': TEST_MEMBER_ID,
            'status': 'submitted',
            'items': [{'product_id': 'prod-1', 'quantity': 1}],
            'version': 2,
        })

        with _auth_patches():
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'evt-order-001'
        assert body['status'] == 'submitted'


# ---------------------------------------------------------------------------
# Tests: Event source - registry_row scope
# ---------------------------------------------------------------------------

class TestEventRegistryRowScope:
    """Tests for event source with registry_config (row-scoped)."""

    def test_creates_draft_order_with_member_as_primary_delegate(self, setup_tables_registry_row_scope):
        """Creates a new row-scoped draft with requesting member as primary delegate."""
        handler = setup_tables_registry_row_scope['handler']

        with _auth_patches():
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['status'] == 'draft'
        assert body['source_id'] == TEST_EVENT_ID
        assert body['member_id'] == TEST_MEMBER_ID
        assert body['registry_row_id'] == TEST_REGISTRY_ROW_ID
        assert body['registry_row_label'] == 'H-DCN Nederland'
        assert body['registry_row_logo_url'] == 'https://cdn.example.com/logo.png'
        assert body['delegates']['primary_member_id'] == TEST_MEMBER_ID

    def test_returns_403_when_member_has_no_registry_row_id(self, setup_tables_registry_row_scope):
        """Returns 403 with REGISTRY_ROW_REQUIRED when member has no registry_row_id."""
        handler = setup_tables_registry_row_scope['handler']

        with _auth_patches(email='norowuser@h-dcn.nl'):
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body.get('error_code') == 'REGISTRY_ROW_REQUIRED'

    def test_returns_existing_row_order_when_member_is_delegate(self, setup_tables_registry_row_scope):
        """Returns existing row order when requesting member is a delegate."""
        handler = setup_tables_registry_row_scope['handler']
        orders_table = setup_tables_registry_row_scope['orders']

        # Seed an existing registry-row-scoped order
        orders_table.put_item(Item={
            'order_id': 'row-order-001',
            'source_id': TEST_EVENT_ID,
            'member_id': TEST_MEMBER_ID,
            'registry_row_id': TEST_REGISTRY_ROW_ID,
            'registry_row_label': 'H-DCN Nederland',
            'registry_row_logo_url': 'https://cdn.example.com/logo.png',
            'status': 'draft',
            'items': [],
            'version': 1,
            'delegates': {
                'primary_member_id': TEST_MEMBER_ID,
            },
        })

        with _auth_patches():
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['order_id'] == 'row-order-001'
        assert body['registry_row_id'] == TEST_REGISTRY_ROW_ID

    def test_returns_403_when_member_is_not_a_delegate(self, setup_tables_registry_row_scope):
        """Returns 403 when existing row order exists but member is not a delegate."""
        handler = setup_tables_registry_row_scope['handler']
        orders_table = setup_tables_registry_row_scope['orders']
        members_table = setup_tables_registry_row_scope['members']

        # Create another member from the same row (different member_id)
        members_table.put_item(Item={
            'member_id': 'mem-other',
            'email': 'other@h-dcn.nl',
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'registry_row_id': TEST_REGISTRY_ROW_ID,  # Same row
        })

        # Seed an existing row order where mem-001 is the primary delegate
        orders_table.put_item(Item={
            'order_id': 'row-order-002',
            'source_id': TEST_EVENT_ID,
            'member_id': TEST_MEMBER_ID,
            'registry_row_id': TEST_REGISTRY_ROW_ID,
            'registry_row_label': 'H-DCN Nederland',
            'registry_row_logo_url': 'https://cdn.example.com/logo.png',
            'status': 'draft',
            'items': [],
            'version': 1,
            'delegates': {
                'primary_member_id': TEST_MEMBER_ID,
                # 'other' is NOT listed as secondary
            },
        })

        # Request as the other member (not a delegate)
        with _auth_patches(email='other@h-dcn.nl'):
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'delegate' in body.get('error', '').lower()

    def test_stores_null_logo_url_when_absent(self, setup_tables_registry_row_scope):
        """Creates order with registry_row_logo_url=null when row has no logo."""
        handler = setup_tables_registry_row_scope['handler']
        members_table = setup_tables_registry_row_scope['members']

        # Create a member mapped to row-nl-002 (which has no logo_url in registry)
        members_table.put_item(Item={
            'member_id': 'mem-no-logo',
            'email': 'nologo@h-dcn.nl',
            'member_type': 'hdcn_member',
            'allowed_events': [TEST_EVENT_ID],
            'registry_row_id': 'row-nl-002',
        })

        with _auth_patches(email='nologo@h-dcn.nl'):
            event = _make_event(query_params={'source_id': TEST_EVENT_ID})
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['registry_row_id'] == 'row-nl-002'
        assert body['registry_row_label'] == 'H-DCN Belgium'
        # logo_url should be explicitly null (not omitted)
        assert 'registry_row_logo_url' in body
        assert body['registry_row_logo_url'] is None
