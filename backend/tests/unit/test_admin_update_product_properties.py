"""
Property-based tests for admin_update_product handler.

**Validates: Requirements 4.3**

Property 2: Update handler ignores event_id and event_ids
- For any valid product update payload that includes event_id and/or event_ids fields,
  the updated DynamoDB record SHALL NOT have event_id or event_ids modified or added.
"""

import json
import os
import sys
import importlib.util
import boto3
import pytest
from decimal import Decimal
from unittest.mock import patch
from moto import mock_aws
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Set environment before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_update_product', 'app.py')
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


def _make_event(product_id: str, body: dict) -> dict:
    """Create a mock API Gateway PUT event for update-product."""
    return {
        'httpMethod': 'PUT',
        'pathParameters': {'id': product_id},
        'body': json.dumps(body),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Products_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Hypothesis strategies ---

# Random event_id values: strings, None, empty string, or absent
event_id_st = st.one_of(
    st.none(),
    st.text(min_size=0, max_size=50),
    st.just('evt-presmeet-2025'),
    st.just('evt-some-random-event'),
)

# Random event_ids values: lists of strings, empty list, None
event_ids_st = st.one_of(
    st.none(),
    st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=5),
    st.just(['evt-1', 'evt-2', 'evt-3']),
)

# Whether to include a valid updatable field alongside the event fields
# (to ensure the handler processes something and returns 200)
valid_field_st = st.sampled_from([
    {'naam': 'Updated Product Name'},
    {'active': True},
    {'groep': 'TestGroep'},
])


@settings(max_examples=50, deadline=None)
@given(
    event_id=event_id_st,
    event_ids=event_ids_st,
    valid_field=valid_field_st,
)
def test_update_handler_ignores_event_id_and_event_ids(event_id, event_ids, valid_field):
    """
    Property 2: Update handler ignores event_id and event_ids.

    **Validates: Requirements 4.3**

    For any valid product update payload that includes event_id and/or event_ids fields,
    the updated DynamoDB record SHALL NOT have event_id or event_ids modified or added.
    """
    product_id = 'prod-property-test'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Seed a parent product (without event_id or event_ids)
        table.put_item(Item={
            'product_id': product_id,
            'is_parent': True,
            'naam': 'Original Name',
            'prijs': Decimal('25.00'),
            'active': True,
            'created_at': '2024-01-01T00:00:00+00:00',
            'updated_at': '2024-01-01T00:00:00+00:00',
        })

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.table = table

        # Build update payload with event_id/event_ids + a valid field
        body = dict(valid_field)
        if event_id is not None:
            body['event_id'] = event_id
        if event_ids is not None:
            body['event_ids'] = event_ids

        # Execute the update
        api_event = _make_event(product_id, body)
        with _auth_patches():
            response = handler_module.lambda_handler(api_event, {})

        status_code = response['statusCode']

        # The handler should return 200 (the valid_field ensures updatable content)
        assert status_code == 200, (
            f"Expected 200 from update, got {status_code}: {response['body']}"
        )

        # Read the record back from DynamoDB
        result = table.get_item(Key={'product_id': product_id})
        assert 'Item' in result, "Product should still exist after update"

        item = result['Item']

        # Assert: event_id and event_ids must NOT be present in the record
        assert 'event_id' not in item, (
            f"event_id should not be in the DynamoDB record after update, "
            f"but found: {item.get('event_id')}"
        )
        assert 'event_ids' not in item, (
            f"event_ids should not be in the DynamoDB record after update, "
            f"but found: {item.get('event_ids')}"
        )
