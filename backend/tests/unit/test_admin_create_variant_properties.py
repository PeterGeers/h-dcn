"""
Property-based tests for admin_create_variant handler.

**Validates: Requirements 4.4**

Property 8: Duplicate variant creation is rejected
- For any parent product and variant_attributes combination that already exists
  (active or inactive), attempting to create a variant with identical attributes
  SHALL return an error and leave the existing variant unchanged.
"""

import json
import os
import sys
import importlib.util
import boto3
import pytest
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
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_variant', 'app.py')
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


def _make_event(product_id, variant_attributes):
    """Create a mock API Gateway POST event for creating a variant."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id},
        'body': json.dumps({'variant_attributes': variant_attributes}),
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

# Strategy for generating variant attribute keys (size axes)
axis_name_st = st.sampled_from(['Maat', 'Kleur', 'Gender', 'Lengte', 'Stijl'])

# Strategy for generating attribute values
attr_value_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_ '),
    min_size=1,
    max_size=10
)

# Strategy for variant attributes (1-3 axes)
variant_attrs_st = st.dictionaries(
    keys=axis_name_st,
    values=attr_value_st,
    min_size=1,
    max_size=3
)

# Strategy for stock values
stock_st = st.integers(min_value=0, max_value=9999)

# Strategy for active status (test both active and inactive existing variants)
active_st = st.booleans()


@settings(max_examples=100, deadline=None)
@given(
    variant_attrs=variant_attrs_st,
    stock=stock_st,
    is_active=active_st,
)
def test_duplicate_variant_creation_is_rejected(
    variant_attrs, stock, is_active
):
    """
    Property 8: Duplicate variant creation is rejected.

    **Validates: Requirements 4.4**

    For any parent product and variant_attributes combination that already exists
    (active or inactive), attempting to create a variant with identical attributes
    SHALL return an error and leave the existing variant unchanged.
    """
    # Filter out empty attribute values that could cause issues
    assume(all(v.strip() for v in variant_attrs.values()))

    parent_id = 'prod-dup-test'
    existing_variant_id = 'var-existing-dup'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
                {'AttributeName': 'parent_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'parent_id-index',
                    'KeySchema': [{'AttributeName': 'parent_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Build the required_attributes schema from the variant_attrs keys
        # This allows the handler's validate_variant_attributes to pass
        properties = {}
        for key, value in variant_attrs.items():
            properties[key] = {
                'type': 'string',
                'enum': [value, f'{value}_other']  # Include the value so validation passes
            }
        required_attributes = {
            'type': 'object',
            'properties': properties
        }

        # Create parent product with required_attributes that match the variant
        producten.put_item(Item={
            'product_id': parent_id,
            'is_parent': True,
            'variant_schema': {k: [v] for k, v in variant_attrs.items()},
            'required_attributes': required_attributes,
        })

        # Create an existing variant with the same attributes (directly in DB)
        existing_variant = {
            'product_id': existing_variant_id,
            'parent_id': parent_id,
            'is_parent': False,
            'variant_attributes': variant_attrs,
            'active': is_active,
            'stock': stock,
            'sold_count': 0,
            'allow_oversell': False,
            'created_at': '2024-01-01T00:00:00+00:00',
            'updated_at': '2024-01-01T00:00:00+00:00',
        }
        producten.put_item(Item=existing_variant)

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.table = producten

        # Attempt to create a variant with the SAME variant_attributes
        event = _make_event(parent_id, variant_attrs)
        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        status_code = response['statusCode']
        body = json.loads(response['body'])

        # Assert: should return 409 (duplicate) — the variant already exists
        assert status_code == 409, (
            f"Expected 409 (duplicate rejected) when variant with same attributes exists "
            f"(active={is_active}), got {status_code}: {body}"
        )

        # Assert: the existing variant record is unchanged
        result = producten.get_item(Key={'product_id': existing_variant_id})
        assert 'Item' in result, (
            "Existing variant record should still exist after duplicate creation attempt"
        )
        stored = result['Item']
        assert stored['variant_attributes'] == variant_attrs, (
            "Existing variant's attributes should be unchanged"
        )
        assert stored['stock'] == stock, (
            "Existing variant's stock should be unchanged"
        )
        assert stored['active'] == is_active, (
            "Existing variant's active status should be unchanged"
        )
        assert stored['created_at'] == '2024-01-01T00:00:00+00:00', (
            "Existing variant's created_at should be unchanged"
        )
        assert stored['updated_at'] == '2024-01-01T00:00:00+00:00', (
            "Existing variant's updated_at should be unchanged"
        )
