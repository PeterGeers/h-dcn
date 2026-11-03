"""
Property-based tests for the admin_bulk_create_variants handler.

Feature: variant-bulk-generator (single axis)

Target: lambda_handler in backend/handler/admin_bulk_create_variants/app.py

Properties (from design.md):
- P3 Non-duplicate create   -> **Validates: Requirements 5.1, 5.2**
- P4 Record shape           -> **Validates: Requirements 4.1-4.5**
- P5 Single-axis            -> **Validates: Requirements 6.2**
- P6 Idempotence            -> **Validates: Requirements 5.1, 5.4**

Follows testing-backend steering:
- Handler loaded via importlib.util by file path (never `import app` via sys.path).
- Handler loaded INSIDE the mock_aws() context so boto3 resources are intercepted.
- Auth patched on the 'app' module.
- Producten table name comes from PRODUCTEN_TABLE_NAME (test table 'Producten-Test').
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal

import boto3
import pytest
from unittest.mock import patch
from moto import mock_aws
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# --- Environment must be set before the handler module is imported ---
TEST_TABLE_NAME = 'Producten-Test'
os.environ['PRODUCTEN_TABLE_NAME'] = TEST_TABLE_NAME
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading (never import app via sys.path)
_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'admin_bulk_create_variants', 'app.py'
    )
)


def _load_handler():
    """Load the handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _create_table():
    """Create the mocked Producten table (call inside a mock_aws context)."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    return dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'product_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _make_event(product_id, body):
    """Build an API Gateway POST event for the bulk-create endpoint."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id},
        'body': json.dumps(body),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'user@h-dcn.nl',
                    'cognito:groups': 'Products_CRUD',
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'},
    }


def _auth_patches():
    """Patch the auth helpers on the loaded 'app' module."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Hypothesis strategies ---------------------------------------------------

# Axis names: alphanumeric, 1-15 chars, non-empty after trim.
axis_name_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=15,
)

# Axis values: alphanumeric (+ space/hyphen), 1-10 chars, non-empty after trim.
axis_value_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -'),
    min_size=1,
    max_size=10,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# A list of requested values: 1..20 values (respects MAX_VALUES_PER_AXIS=20).
values_list_st = st.lists(axis_value_st, min_size=1, max_size=20)

# A set of pre-existing values (0..10) for a parent.
existing_values_st = st.lists(axis_value_st, min_size=0, max_size=10)


def _seed_parent(table, parent_id, prijs='10.00'):
    """Insert a parent product record."""
    table.put_item(Item={
        'product_id': parent_id,
        'is_parent': True,
        'naam': 'Test Product',
        'prijs': prijs,
    })


def _seed_existing_variants(table, parent_id, axis_name, values):
    """Insert existing variant records for the given axis/values. Returns the set created."""
    created = set()
    for i, value in enumerate(values):
        if value in created:
            continue
        created.add(value)
        table.put_item(Item={
            'product_id': f'var_existing_{i}',
            'parent_id': parent_id,
            'is_parent': False,
            'variant_attributes': {axis_name: value},
            'active': True,
            'stock': 5,
            'sold_count': 0,
            'allow_oversell': False,
            'prijs': '10.00',
            'created_at': '2024-01-01T00:00:00+00:00',
            'updated_at': '2024-01-01T00:00:00+00:00',
        })
    return created


def _scan_variants(table, parent_id):
    """Return all variant records (is_parent == False) for a parent."""
    resp = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq(parent_id)
        & boto3.dynamodb.conditions.Attr('is_parent').eq(False)
    )
    return resp.get('Items', [])


def _normalize(raw_values):
    """Mirror the handler's normalization: trim, drop empties, de-dup, first-seen order."""
    seen = set()
    out = []
    for v in raw_values:
        t = v.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# --- P3: Non-duplicate create ------------------------------------------------

@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    axis_name=axis_name_st,
    requested=values_list_st,
    existing=existing_values_st,
)
def test_p3_creates_exactly_non_duplicate_values(axis_name, requested, existing):
    """
    P3: Generation creates exactly the non-duplicate values.

    **Validates: Requirements 5.1, 5.2**

    For any set of existing variants for a parent and any list of requested values,
    the backend creates one Variant_Record for each normalized requested value whose
    variant_attributes is not already present, and creates none for values that
    already exist.
    """
    parent_id = 'prod-p3'
    normalized_requested = _normalize(requested)
    assume(normalized_requested)  # at least one value survives normalization

    with mock_aws():
        table = _create_table()
        _seed_parent(table, parent_id)
        existing_set = _seed_existing_variants(table, parent_id, axis_name, existing)

        handler = _load_handler()

        event = _make_event(parent_id, {'axis_name': axis_name, 'values': requested})
        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200, response['body']
        body = json.loads(response['body'])

        expected_created = [v for v in normalized_requested if v not in existing_set]
        expected_skipped = [v for v in normalized_requested if v in existing_set]

        assert body['created'] == len(expected_created), (
            f"created={body['created']} expected {len(expected_created)} "
            f"(requested={normalized_requested}, existing={sorted(existing_set)})"
        )
        assert sorted(body['skipped']) == sorted(expected_skipped), (
            f"skipped={body['skipped']} expected {expected_skipped}"
        )

        # DynamoDB reflects: every expected created value now has a variant record,
        # and the total count of values for the axis equals the union.
        variants = _scan_variants(table, parent_id)
        stored_values = {
            v['variant_attributes'][axis_name]
            for v in variants
            if axis_name in (v.get('variant_attributes') or {})
        }
        assert stored_values == (existing_set | set(expected_created))


# --- P4: Record shape --------------------------------------------------------

@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    axis_name=axis_name_st,
    requested=values_list_st,
)
def test_p4_created_records_have_expected_shape(axis_name, requested):
    """
    P4: Each generated record has the submitted axis/value and default fields.

    **Validates: Requirements 4.1-4.5**

    For any created Variant_Record, its variant_attributes equals {axis_name: value}
    and its stock, allow_oversell, active, sold_count, is_parent, parent_id equal the
    specified defaults (no overrides supplied).
    """
    parent_id = 'prod-p4'
    normalized_requested = _normalize(requested)
    assume(normalized_requested)

    with mock_aws():
        table = _create_table()
        _seed_parent(table, parent_id)

        handler = _load_handler()

        event = _make_event(parent_id, {'axis_name': axis_name, 'values': requested})
        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200, response['body']
        body = json.loads(response['body'])
        assert body['created'] == len(normalized_requested)

        # Inspect every created variant record in the DB.
        created_variants = [
            v for v in _scan_variants(table, parent_id)
            if (v.get('variant_attributes') or {}) != {}
        ]
        assert len(created_variants) == len(normalized_requested)

        created_values = set()
        for v in created_variants:
            attrs = v['variant_attributes']
            # Exactly one key-value pair: {axis_name: value}
            assert list(attrs.keys()) == [axis_name], attrs
            value = attrs[axis_name]
            created_values.add(value)

            # Defaults (Requirements 4.1, 4.2, 4.4)
            assert v['stock'] == 0
            assert v['allow_oversell'] is False
            assert v['active'] is True
            assert v['sold_count'] == 0
            assert v['is_parent'] is False
            assert v['parent_id'] == parent_id

        assert created_values == set(normalized_requested)


# --- P5: Single-axis enforcement ---------------------------------------------

@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    existing_axis=axis_name_st,
    new_axis=axis_name_st,
    existing=st.lists(axis_value_st, min_size=1, max_size=5),
    requested=values_list_st,
)
def test_p5_differing_axis_rejected_and_creates_nothing(
    existing_axis, new_axis, existing, requested
):
    """
    P5: Single-axis enforcement.

    **Validates: Requirements 6.2**

    For any request whose axis_name differs from an existing axis on the parent,
    the backend returns 400 and creates nothing.
    """
    assume(existing_axis != new_axis)  # the axes must actually differ

    parent_id = 'prod-p5'
    with mock_aws():
        table = _create_table()
        _seed_parent(table, parent_id)
        _seed_existing_variants(table, parent_id, existing_axis, existing)

        before = _scan_variants(table, parent_id)
        before_ids = {v['product_id'] for v in before}

        handler = _load_handler()

        event = _make_event(parent_id, {'axis_name': new_axis, 'values': requested})
        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400, (
            f"Expected 400 for differing axis ({existing_axis!r} vs {new_axis!r}), "
            f"got {response['statusCode']}: {response['body']}"
        )

        # Nothing created: the variant set is unchanged.
        after = _scan_variants(table, parent_id)
        after_ids = {v['product_id'] for v in after}
        assert after_ids == before_ids, "No variant records should be created on 400"


# --- P6: Idempotence ---------------------------------------------------------

@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    axis_name=axis_name_st,
    requested=values_list_st,
)
def test_p6_second_run_creates_nothing_and_skips_all(axis_name, requested):
    """
    P6: Idempotence.

    **Validates: Requirements 5.1, 5.4**

    For any request, running it twice creates records only on the first run; the
    second run creates zero and reports all values as skipped.
    """
    parent_id = 'prod-p6'
    normalized_requested = _normalize(requested)
    assume(normalized_requested)

    with mock_aws():
        table = _create_table()
        _seed_parent(table, parent_id)

        handler = _load_handler()
        event = _make_event(parent_id, {'axis_name': axis_name, 'values': requested})

        # First run: creates all normalized values.
        with _auth_patches():
            first = handler.lambda_handler(event, {})
        assert first['statusCode'] == 200, first['body']
        first_body = json.loads(first['body'])
        assert first_body['created'] == len(normalized_requested)
        assert first_body['skipped'] == []

        variants_after_first = _scan_variants(table, parent_id)

        # Second run: identical request creates nothing, skips everything.
        with _auth_patches():
            second = handler.lambda_handler(event, {})
        assert second['statusCode'] == 200, second['body']
        second_body = json.loads(second['body'])
        assert second_body['created'] == 0
        assert sorted(second_body['skipped']) == sorted(normalized_requested)

        # The variant set is identical after the second run.
        variants_after_second = _scan_variants(table, parent_id)
        assert (
            {v['product_id'] for v in variants_after_second}
            == {v['product_id'] for v in variants_after_first}
        )
