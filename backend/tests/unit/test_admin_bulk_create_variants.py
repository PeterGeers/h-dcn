"""
Unit tests for the admin_bulk_create_variants handler.

Target: lambda_handler in backend/handler/admin_bulk_create_variants/app.py

Covers the single-axis bulk variant generator contract:
- Skips existing values, creates the rest (created count + skipped list)
- Rejects a differing axis with 400 (product already uses a different axis)
- Rejects > 20 values with 400
- Removes the Default_Variant when applicable (var_{product_id}_default deleted;
  default_variant_removed=true)
- prijs inherits the parent when no override is provided
- Guard rails: missing product_id (400), parent not found (404), non-parent
  product (400), empty axis_name (400), empty values (400), invalid prijs (400)

Follows backend testing steering: importlib.util handler load (no bare
`import app`), handler loaded inside the mock_aws() context, auth patched on the
'app' module.
"""

import json
import os
import sys
import importlib.util
import pytest
import boto3
from decimal import Decimal
from unittest.mock import patch
from moto import mock_aws

# Set environment before importing the handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten-Test'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'admin_bulk_create_variants', 'app.py'
    )
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


def _make_event(product_id='prod-1', body=None, raw_body=None):
    """Create a mock API Gateway POST event for bulk variant creation."""
    if raw_body is not None:
        event_body = raw_body
    else:
        event_body = json.dumps(body or {})

    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': product_id} if product_id else None,
        'body': event_body,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'user@h-dcn.nl',
                    'cognito:groups': 'Products_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions on the handler."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten-Test DynamoDB table and load the handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten-Test',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        yield table, handler_module


def _put_parent(table, product_id='prod-1', prijs='25', is_parent=True):
    """Insert a parent product into the mocked table."""
    item = {
        'product_id': product_id,
        'naam': 'Club T-shirt',
        'is_parent': is_parent,
        'active': True,
    }
    if prijs is not None:
        item['prijs'] = Decimal(str(prijs))
    table.put_item(Item=item)


def _put_variant(table, variant_id, parent_id, variant_attributes, active=True):
    """Insert a variant record into the mocked table."""
    table.put_item(Item={
        'product_id': variant_id,
        'parent_id': parent_id,
        'naam': '',
        'is_parent': False,
        'variant_attributes': variant_attributes,
        'stock': Decimal('0'),
        'sold_count': Decimal('0'),
        'allow_oversell': False,
        'active': active,
    })


def _variant_items(table):
    """Return all non-parent variant records in the table."""
    items = table.scan().get('Items', [])
    return [i for i in items if i.get('is_parent') is False]


class TestBulkCreateVariantsCore:
    """Core bulk-generation behaviour."""

    def test_skips_existing_creates_rest(self, producten_table):
        """Values that already exist are skipped; the rest are created."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')
        # Existing variant for value "M" on the "Maat" axis
        _put_variant(table, 'var-existing-m', 'prod-1', {'Maat': 'M'})

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['S', 'M', 'L'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        resp = json.loads(response['body'])
        # The handler wraps payload; find created/skipped regardless of nesting
        payload = resp.get('data', resp)
        assert payload['created'] == 2
        assert payload['skipped'] == ['M']

        # DynamoDB now has the existing M plus two new (S, L) = 3 variants
        created_values = sorted(
            v['variant_attributes']['Maat'] for v in _variant_items(table)
        )
        assert created_values == ['L', 'M', 'S']

    def test_rejects_differing_axis_400(self, producten_table):
        """A request whose axis differs from the existing axis is rejected 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')
        # Parent already uses the "Maat" axis
        _put_variant(table, 'var-existing-m', 'prod-1', {'Maat': 'M'})

        event = _make_event('prod-1', body={
            'axis_name': 'Kleur',
            'values': ['Rood', 'Blauw'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'different axis' in resp['error'].lower()
        # Nothing new created
        assert len(_variant_items(table)) == 1

    def test_rejects_more_than_20_values_400(self, producten_table):
        """More than 20 values in a single request is rejected 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')

        values = [f'V{i}' for i in range(21)]  # 21 distinct values
        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': values,
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'maximum' in resp['error'].lower() or '20' in resp['error']
        assert len(_variant_items(table)) == 0

    def test_removes_default_variant_when_applicable(self, producten_table):
        """When only a Default_Variant exists, adding real variants removes it."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')
        # Only a Default_Variant (empty variant_attributes) exists
        default_id = 'var_prod-1_default'
        _put_variant(table, default_id, 'prod-1', {})

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['S', 'M'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        payload = json.loads(response['body'])
        payload = payload.get('data', payload)
        assert payload['created'] == 2
        assert payload['default_variant_removed'] is True

        # Default_Variant deleted from DynamoDB
        remaining = {v['product_id'] for v in _variant_items(table)}
        assert default_id not in remaining
        # Only the two new real variants remain
        assert len(remaining) == 2

    def test_prijs_inherits_parent_when_no_override(self, producten_table):
        """Created variants inherit the parent's prijs when no override is given."""
        table, handler = producten_table
        _put_parent(table, 'prod-1', prijs='25')

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['S'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 200
        created = _variant_items(table)
        assert len(created) == 1
        assert created[0]['prijs'] == Decimal('25')


class TestBulkCreateVariantsGuards:
    """Validation and guard-rail behaviour."""

    def test_missing_product_id_returns_400(self, producten_table):
        """Missing product ID in path returns 400."""
        table, handler = producten_table

        event = _make_event(product_id=None, body={
            'axis_name': 'Maat',
            'values': ['S'],
        })
        # pathParameters is None → product_id missing
        event['pathParameters'] = {}

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'required' in resp['error'].lower()

    def test_parent_not_found_returns_404(self, producten_table):
        """Bulk create for a non-existent parent returns 404."""
        table, handler = producten_table

        event = _make_event('nonexistent', body={
            'axis_name': 'Maat',
            'values': ['S'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 404
        resp = json.loads(response['body'])
        assert 'not found' in resp['error'].lower()

    def test_non_parent_product_returns_400(self, producten_table):
        """Targeting a non-parent product returns 400."""
        table, handler = producten_table
        # Product explicitly marked as not a parent
        _put_parent(table, 'prod-1', is_parent=False)

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['S'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'non-parent' in resp['error'].lower()

    def test_empty_axis_name_returns_400(self, producten_table):
        """Empty/whitespace axis_name returns 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')

        event = _make_event('prod-1', body={
            'axis_name': '   ',
            'values': ['S'],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'axis_name' in resp['error'].lower()

    def test_empty_values_returns_400(self, producten_table):
        """Empty values list returns 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': [],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'values' in resp['error'].lower()

    def test_values_all_whitespace_returns_400(self, producten_table):
        """A values list that is non-empty but normalizes to empty returns 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['   ', ''],
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'values' in resp['error'].lower()

    def test_invalid_prijs_override_returns_400(self, producten_table):
        """A non-numeric prijs override returns 400."""
        table, handler = producten_table
        _put_parent(table, 'prod-1')

        event = _make_event('prod-1', body={
            'axis_name': 'Maat',
            'values': ['S'],
            'prijs': 'not-a-number',
        })

        with _auth_patches():
            response = handler.lambda_handler(event, {})

        assert response['statusCode'] == 400
        resp = json.loads(response['body'])
        assert 'prijs' in resp['error'].lower()
        # Nothing created
        assert len(_variant_items(table)) == 0
