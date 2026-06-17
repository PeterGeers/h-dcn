"""
Property-based tests for admin_create_variant handler.

Feature: product-variant-simplification

Property 1: Variant creation preserves submitted attributes
- **Validates: Requirements 3.2, 4.5**

Property 8: Duplicate variant attributes rejected
- **Validates: Requirements 12.1**
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

# Strategy for axis names: non-empty strings (1-15 chars, letters/digits)
axis_name_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=15
)

# Strategy for axis values: non-empty strings (1-10 chars, letters/digits/spaces)
axis_value_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -'),
    min_size=1,
    max_size=10
)

# Strategy for variant_attributes: 1-3 axes with random names and values
variant_attrs_st = st.dictionaries(
    keys=axis_name_st,
    values=axis_value_st,
    min_size=1,
    max_size=3
)

# Strategy for active status (test both active and inactive existing variants)
active_st = st.booleans()


@settings(max_examples=100, deadline=None)
@given(
    variant_attrs=variant_attrs_st,
    is_active=active_st,
)
def test_duplicate_variant_attributes_rejected(variant_attrs, is_active):
    """
    Property 8: Duplicate variant attributes rejected.

    **Validates: Requirements 12.1**

    For any non-empty variant_attributes dict, when that exact dict already
    exists as a variant for a parent product, creating a new variant with the
    same attributes returns 409.
    """
    # Ensure all values are non-whitespace-only
    assume(all(v.strip() for v in variant_attrs.values()))
    assume(all(k.strip() for k in variant_attrs.keys()))

    parent_id = 'prod-dup-test'
    existing_variant_id = 'var_existing_dup'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create parent product (simplified — no variant_schema needed)
        producten.put_item(Item={
            'product_id': parent_id,
            'is_parent': True,
            'naam': 'Test Product',
            'prijs': '10.00',
        })

        # Create an existing variant with the target attributes (directly in DB)
        existing_variant = {
            'product_id': existing_variant_id,
            'parent_id': parent_id,
            'is_parent': False,
            'variant_attributes': variant_attrs,
            'active': is_active,
            'stock': 5,
            'sold_count': 0,
            'allow_oversell': False,
            'prijs': '10.00',
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
        assert stored['active'] == is_active, (
            "Existing variant's active status should be unchanged"
        )


# --- Property 1: Variant creation preserves submitted attributes ---

# Alphanumeric axis names (1-20 chars, non-empty)
alpha_axis_name_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
)

# Alphanumeric axis values (1-20 chars, non-empty)
alpha_attr_value_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20
)

# Strategy for variant attributes: 1-3 alphanumeric axis-value pairs
preservation_attrs_st = st.dictionaries(
    keys=alpha_axis_name_st,
    values=alpha_attr_value_st,
    min_size=1,
    max_size=3
)


@settings(max_examples=100, deadline=None)
@given(variant_attrs=preservation_attrs_st)
def test_variant_creation_preserves_submitted_attributes(variant_attrs):
    """
    Property 1: Variant creation preserves submitted attributes.

    **Validates: Requirements 3.2, 4.5**

    For any non-empty dict of axis name -> value string pairs submitted as
    variant_attributes in a variant creation request, the resulting Variant_Record's
    variant_attributes in the response body contains exactly those same axis-value pairs.
    """
    # Ensure we have at least one key after dedup
    assume(len(variant_attrs) >= 1)

    parent_id = 'prod-preserve-test'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create parent product (no existing variants - fresh product)
        producten.put_item(Item={
            'product_id': parent_id,
            'is_parent': True,
            'naam': 'Test Product',
            'prijs': '10.00',
        })

        # Load handler inside mock context
        handler_module = _load_handler()
        handler_module.table = producten

        # Create variant with the generated attributes
        event = _make_event(parent_id, variant_attrs)
        with _auth_patches():
            response = handler_module.lambda_handler(event, {})

        status_code = response['statusCode']
        body = json.loads(response['body'])

        # Assert: should return 200 (success)
        assert status_code == 200, (
            f"Expected 200 for variant creation, got {status_code}: {body}"
        )

        # Assert: response contains the variant with exactly the submitted attributes
        assert 'variant' in body, (
            f"Response body should contain 'variant' key, got: {list(body.keys())}"
        )
        returned_attrs = body['variant'].get('variant_attributes', {})

        # The returned attributes must be exactly equal to what was submitted
        assert returned_attrs == variant_attrs, (
            f"Returned variant_attributes {returned_attrs} should exactly match "
            f"submitted attributes {variant_attrs}"
        )

        # Also verify the record in DynamoDB matches
        variant_id = body['variant']['product_id']
        db_result = producten.get_item(Key={'product_id': variant_id})
        assert 'Item' in db_result, "Variant should exist in DynamoDB"
        db_attrs = db_result['Item'].get('variant_attributes', {})
        assert db_attrs == variant_attrs, (
            f"DynamoDB variant_attributes {db_attrs} should exactly match "
            f"submitted attributes {variant_attrs}"
        )
