"""
Property-based tests for admin_create_product handler.

**Validates: Requirements 3.1, 3.2**

Property 1: Create handler never persists event_id or event_ids
- For any valid product creation payload that includes event_id and/or event_ids fields,
  the resulting DynamoDB record SHALL NOT contain an event_id or event_ids attribute.
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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_product', 'app.py')
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


def _make_event(body: dict) -> dict:
    """Create a mock API Gateway POST event for create-product."""
    return {
        'httpMethod': 'POST',
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

# Random event_id values: strings, None, or absent (we'll handle inclusion below)
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

# Valid product names to ensure the handler accepts the payload
product_name_st = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('L', 'N', 'Z'),
    whitelist_characters=' -_'
))


@settings(max_examples=50, deadline=None)
@given(
    event_id=event_id_st,
    event_ids=event_ids_st,
    product_name=product_name_st,
)
def test_create_handler_never_persists_event_id_or_event_ids(event_id, event_ids, product_name):
    """
    Property 1: Create handler never persists event_id or event_ids.

    **Validates: Requirements 3.1, 3.2**

    For any valid product creation payload that includes event_id and/or event_ids fields,
    the resulting DynamoDB record SHALL NOT contain an event_id or event_ids attribute.
    """
    # Ensure we have at least one event field to test stripping
    assume(event_id is not None or event_ids is not None)
    # Ensure product name is non-empty after strip
    assume(product_name.strip())

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

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.table = table

        # Build create payload with required 'name' field + event_id/event_ids
        body = {'name': product_name}
        if event_id is not None:
            body['event_id'] = event_id
        if event_ids is not None:
            body['event_ids'] = event_ids

        # Execute the create
        api_event = _make_event(body)
        with _auth_patches():
            response = handler_module.lambda_handler(api_event, {})

        status_code = response['statusCode']

        # The handler should return 200 for a valid payload
        assert status_code == 200, (
            f"Expected 200 from create, got {status_code}: {response['body']}"
        )

        # Extract the created product_id from response
        response_body = json.loads(response['body'])
        product_id = response_body['product']['product_id']

        # Read the record back from DynamoDB
        result = table.get_item(Key={'product_id': product_id})
        assert 'Item' in result, "Product should exist after creation"

        item = result['Item']

        # Assert: event_id and event_ids must NOT be present in the record
        assert 'event_id' not in item, (
            f"event_id should not be in the DynamoDB record after creation, "
            f"but found: {item.get('event_id')}"
        )
        assert 'event_ids' not in item, (
            f"event_ids should not be in the DynamoDB record after creation, "
            f"but found: {item.get('event_ids')}"
        )
