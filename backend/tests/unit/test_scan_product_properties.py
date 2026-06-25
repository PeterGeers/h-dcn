"""
Property-based tests for scan_product handler.

**Validates: Requirements 9.1, 9.2**

Property 6: Scan response excludes event_id and event_ids
- For any product record in DynamoDB (whether or not it has legacy event_id/event_ids
  attributes), the scan_product API response SHALL NOT include event_id or event_ids
  fields in any returned item.
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
from hypothesis import given, settings
from hypothesis import strategies as st

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')
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


def _make_event() -> dict:
    """Create a mock API Gateway GET event for scan_product."""
    return {
        'httpMethod': 'GET',
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Products_Read'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Hypothesis strategies ---

# Random event_id values that might exist as legacy data
event_id_st = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=50),
    st.just('evt-presmeet-2025'),
    st.just('evt-legacy-event'),
)

# Random event_ids values (list of strings) that might exist as legacy data
event_ids_st = st.one_of(
    st.none(),
    st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5),
    st.just(['evt-1', 'evt-2']),
)

# Strategy for generating a product record with optional legacy event fields
product_record_st = st.fixed_dictionaries({
    'product_id': st.text(min_size=5, max_size=20, alphabet=st.characters(
        whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'
    )),
    'naam': st.text(min_size=1, max_size=50),
    'prijs': st.integers(min_value=1, max_value=10000).map(lambda x: Decimal(str(x))),
    'is_parent': st.just(True),
    'active': st.booleans(),
}, optional={
    'event_id': event_id_st,
    'event_ids': event_ids_st,
    'artikelcode': st.text(min_size=1, max_size=20),
    'groep': st.text(min_size=1, max_size=30),
    'subgroep': st.text(min_size=1, max_size=30),
})


@settings(max_examples=50, deadline=None)
@given(
    records=st.lists(product_record_st, min_size=1, max_size=5)
)
def test_scan_response_excludes_event_id_and_event_ids(records):
    """
    Property 6: Scan response excludes event_id and event_ids.

    **Validates: Requirements 9.1, 9.2**

    For any product record in DynamoDB (whether or not it has legacy event_id/event_ids
    attributes), the scan_product API response SHALL NOT include event_id or event_ids
    fields in any returned item.
    """
    # Ensure unique product_ids across records
    seen_ids = set()
    unique_records = []
    for record in records:
        if record['product_id'] not in seen_ids:
            seen_ids.add(record['product_id'])
            unique_records.append(record)

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

        # Seed the table with generated records (including legacy event fields)
        for record in unique_records:
            item = {k: v for k, v in record.items() if v is not None}
            table.put_item(Item=item)

        # Load handler inside mock context
        handler_module = _load_handler()

        # Execute the scan
        api_event = _make_event()
        with _auth_patches():
            response = handler_module.lambda_handler(api_event, {})

        assert response['statusCode'] == 200, (
            f"Expected 200, got {response['statusCode']}: {response['body']}"
        )

        body = json.loads(response['body'])
        assert isinstance(body, list), "Response body should be a list of products"

        # Verify no item in the response contains event_id or event_ids
        for item in body:
            assert 'event_id' not in item, (
                f"event_id should not be in scan response, "
                f"but found in product {item.get('product_id')}: {item.get('event_id')}"
            )
            assert 'event_ids' not in item, (
                f"event_ids should not be in scan response, "
                f"but found in product {item.get('product_id')}: {item.get('event_ids')}"
            )
