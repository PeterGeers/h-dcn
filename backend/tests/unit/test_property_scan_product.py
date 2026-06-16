"""
Property-Based Tests for scan_product handler (Properties 6 & 7)

**Validates: Requirements 5.4, 5.5, 9.1, 9.2**

Property 6: scan_product response uses canonical Dutch fields
    For any product record where is_parent is true or absent, the response SHALL
    include product_id, naam, artikelcode, prijs, variant_schema, is_parent,
    event_ids, active, groep, subgroep, images — using legacy 'name' as fallback
    for 'naam' and legacy 'price' as fallback for 'prijs'.

Property 7: scan_product excludes variant and migration records
    The scan_product handler SHALL return only records where is_parent is true or
    absent, AND source is not "migration".
"""

import json
import importlib.util
import os
import sys
import uuid
from decimal import Decimal

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws
from unittest.mock import patch

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Path to the handler module (used for explicit import)
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')
)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

def _load_handler():
    """Load the scan_product handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Helpers
# =============================================================================

def _make_event():
    """Create a mock API Gateway event for GET /scan-product/."""
    return {
        'httpMethod': 'GET',
        'body': None,
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


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def product_id_strategy():
    """Generate product IDs as UUID-like strings."""
    return st.uuids().map(str)


def product_name_strategy():
    """Generate product names (printable, non-empty)."""
    return st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Z')),
        min_size=1, max_size=50
    ).filter(lambda s: s.strip() != '')


def price_strategy():
    """Generate realistic product prices (positive numbers)."""
    return st.integers(min_value=1, max_value=9999)


def variant_schema_strategy():
    """Generate variant schemas as Record<string, list[string]>."""
    axis_name = st.text(
        alphabet=st.characters(whitelist_categories=('L',)),
        min_size=1, max_size=10
    )
    axis_values = st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1, max_size=10
        ),
        min_size=1, max_size=5
    )
    return st.dictionaries(axis_name, axis_values, min_size=1, max_size=3)


@st.composite
def parent_product_strategy(draw):
    """Generate a valid parent product record with mixed field names.

    Some products use canonical Dutch ('naam'/'prijs'), some use legacy English
    ('name'/'price'), and some have both fields present. The handler always
    returns canonical Dutch field names in the response.
    """
    product_id = draw(product_id_strategy())
    name_value = draw(product_name_strategy())
    price_value = draw(price_strategy())
    has_variant_schema = draw(st.booleans())
    has_event_ids = draw(st.booleans())
    is_active = draw(st.booleans())

    # Determine field naming convention in DynamoDB record
    naming = draw(st.sampled_from(['canonical', 'legacy', 'both']))

    record = {
        'product_id': product_id,
        'is_parent': True,
        'active': is_active,
    }

    if naming == 'canonical':
        record['naam'] = name_value
        record['prijs'] = price_value
    elif naming == 'legacy':
        record['name'] = name_value
        record['price'] = price_value
    else:  # both
        record['naam'] = name_value
        record['name'] = f"legacy_{name_value}"
        record['prijs'] = price_value
        record['price'] = price_value + 1  # different to test preference

    if has_variant_schema:
        record['variant_schema'] = draw(variant_schema_strategy())

    if has_event_ids:
        record['event_ids'] = [draw(st.uuids().map(str))]
    else:
        record['event_ids'] = []

    return record


@st.composite
def product_without_is_parent_strategy(draw):
    """Generate a product record without the is_parent attribute (legacy record)."""
    product_id = draw(product_id_strategy())
    name_value = draw(product_name_strategy())
    price_value = draw(price_strategy())

    naming = draw(st.sampled_from(['canonical', 'legacy', 'both']))

    record = {
        'product_id': product_id,
        'active': True,
    }

    if naming == 'canonical':
        record['naam'] = name_value
        record['prijs'] = price_value
    elif naming == 'legacy':
        record['name'] = name_value
        record['price'] = price_value
    else:
        record['naam'] = name_value
        record['name'] = f"legacy_{name_value}"
        record['prijs'] = price_value
        record['price'] = price_value + 5

    return record


@st.composite
def variant_record_strategy(draw):
    """Generate a variant record (is_parent: false)."""
    product_id = draw(product_id_strategy())
    parent_id = draw(product_id_strategy())

    return {
        'product_id': product_id,
        'is_parent': False,
        'parent_id': parent_id,
        'naam': draw(product_name_strategy()),
        'prijs': draw(price_strategy()),
        'variant_attributes': {'Maat': draw(st.sampled_from(['S', 'M', 'L', 'XL']))},
        'stock': draw(st.integers(min_value=0, max_value=100)),
        'allow_oversell': draw(st.booleans()),
    }


@st.composite
def migration_record_strategy(draw):
    """Generate a migration source record."""
    product_id = draw(product_id_strategy())

    return {
        'product_id': product_id,
        'naam': draw(product_name_strategy()),
        'prijs': draw(price_strategy()),
        'source': 'migration',
        'is_parent': draw(st.sampled_from([True, None])),
    }


# =============================================================================
# Property 6: scan_product response uses canonical Dutch fields
# =============================================================================

class TestProperty6ScanProductNormalization:
    """
    **Validates: Requirements 5.4, 9.1, 9.2**

    Property 6: For any product record where is_parent is true or absent,
    the response SHALL include product_id, naam, artikelcode, prijs,
    variant_schema, is_parent, event_ids, active, groep, subgroep, images —
    using legacy 'name' as fallback for 'naam' and legacy 'price' as fallback
    for 'prijs'.
    """

    @given(product=parent_product_strategy())
    @settings(max_examples=100, deadline=None)
    def test_normalized_response_includes_all_required_fields(self, product):
        """
        For any parent product record, the normalized response contains all
        required canonical Dutch fields: product_id, naam, artikelcode, prijs,
        variant_schema, is_parent, event_ids, active, groep, subgroep, images.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Remove None values for DynamoDB (it doesn't accept None as value in put_item)
            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body) == 1

            result = body[0]

            # All required canonical Dutch fields must be present as keys
            required_fields = ['product_id', 'naam', 'artikelcode', 'prijs',
                               'variant_schema', 'is_parent', 'event_ids', 'active',
                               'groep', 'subgroep', 'images']
            for field in required_fields:
                assert field in result, f"Field '{field}' must be present in response"

            # product_id must match
            assert result['product_id'] == product['product_id']

            # is_parent must match
            assert result['is_parent'] == product.get('is_parent')

            # active must match
            assert result['active'] == product.get('active')

    @given(product=parent_product_strategy())
    @settings(max_examples=100, deadline=None)
    def test_naam_fallback_from_legacy_name(self, product):
        """
        The response uses canonical 'naam' field. When 'naam' is present in
        the DB record it is used directly. When only legacy 'name' is present,
        it serves as fallback for the 'naam' response field.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # Response always uses canonical 'naam' key
            assert 'naam' in result

            # If canonical 'naam' was in the record, it should be used
            if 'naam' in product:
                assert result['naam'] == product['naam']
            elif 'name' in product:
                # Legacy 'name' is fallback for 'naam'
                assert result['naam'] == product['name']
            else:
                # Neither present — naam should be None
                assert result['naam'] is None

    @given(product=parent_product_strategy())
    @settings(max_examples=100, deadline=None)
    def test_prijs_fallback_from_legacy_price(self, product):
        """
        The response uses canonical 'prijs' field. When 'prijs' is present in
        the DB record it is used directly. When only legacy 'price' is present,
        it serves as fallback for the 'prijs' response field.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # Response always uses canonical 'prijs' key
            assert 'prijs' in result

            # If canonical 'prijs' was in the record, it should be used
            if 'prijs' in product:
                assert result['prijs'] == product['prijs']
            elif 'price' in product:
                # Legacy 'price' is fallback for 'prijs'
                assert result['prijs'] == product['price']
            else:
                assert result['prijs'] is None

    @given(product=product_without_is_parent_strategy())
    @settings(max_examples=100, deadline=None)
    def test_products_without_is_parent_are_normalized(self, product):
        """
        Products without an is_parent attribute are included in the response
        and normalized with all required canonical Dutch fields.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            item = {k: v for k, v in product.items() if v is not None}
            table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body) == 1

            result = body[0]

            # All required canonical Dutch fields present
            required_fields = ['product_id', 'naam', 'artikelcode', 'prijs',
                               'variant_schema', 'is_parent', 'event_ids', 'active',
                               'groep', 'subgroep', 'images']
            for field in required_fields:
                assert field in result, f"Field '{field}' must be in response"

            # naam fallback works
            if 'naam' in product:
                assert result['naam'] == product['naam']
            elif 'name' in product:
                assert result['naam'] == product['name']

            # prijs fallback works
            if 'prijs' in product:
                assert result['prijs'] == product['prijs']
            elif 'price' in product:
                assert result['prijs'] == product['price']


# =============================================================================
# Property 7: scan_product excludes variant and migration records
# =============================================================================

class TestProperty7ScanProductFiltering:
    """
    **Validates: Requirements 5.5**

    Property 7: The scan_product handler SHALL return only records where
    is_parent is true or the is_parent attribute does not exist, AND source
    is not equal to "migration" — all variant records (is_parent: false) and
    migration-source records SHALL be excluded.
    """

    @given(
        parents=st.lists(parent_product_strategy(), min_size=1, max_size=5,
                         unique_by=lambda p: p['product_id']),
        variants=st.lists(variant_record_strategy(), min_size=1, max_size=5,
                          unique_by=lambda v: v['product_id']),
        migrations=st.lists(migration_record_strategy(), min_size=0, max_size=3,
                            unique_by=lambda m: m['product_id']),
    )
    @settings(max_examples=100, deadline=None)
    def test_only_parent_and_legacy_records_returned(self, parents, variants, migrations):
        """
        Given a table with parents, variants, and migration records, only
        parent products (is_parent=true or is_parent absent) without
        source='migration' are returned.
        """
        # Ensure no ID collisions between the record types
        all_ids = [p['product_id'] for p in parents] + \
                  [v['product_id'] for v in variants] + \
                  [m['product_id'] for m in migrations]
        assume(len(all_ids) == len(set(all_ids)))

        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Insert all records
            for record in parents + variants + migrations:
                item = {k: v for k, v in record.items() if v is not None}
                table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])

            returned_ids = {item['product_id'] for item in body}
            parent_ids = {p['product_id'] for p in parents}

            # All parent IDs should be returned
            assert parent_ids.issubset(returned_ids), (
                f"Missing parent IDs: {parent_ids - returned_ids}"
            )

            # No variant IDs should be returned
            variant_ids = {v['product_id'] for v in variants}
            assert returned_ids.isdisjoint(variant_ids), (
                f"Variant IDs should be excluded: {returned_ids & variant_ids}"
            )

            # No migration IDs should be returned
            migration_ids = {m['product_id'] for m in migrations}
            assert returned_ids.isdisjoint(migration_ids), (
                f"Migration IDs should be excluded: {returned_ids & migration_ids}"
            )

    @given(
        parents=st.lists(parent_product_strategy(), min_size=0, max_size=3,
                         unique_by=lambda p: p['product_id']),
        legacies=st.lists(product_without_is_parent_strategy(), min_size=0, max_size=3,
                          unique_by=lambda p: p['product_id']),
        variants=st.lists(variant_record_strategy(), min_size=1, max_size=5,
                          unique_by=lambda v: v['product_id']),
    )
    @settings(max_examples=100, deadline=None)
    def test_legacy_records_without_is_parent_included(self, parents, legacies, variants):
        """
        Records without the is_parent attribute (legacy products) are included
        alongside records where is_parent=true. Variant records (is_parent=false)
        are always excluded.
        """
        all_ids = [p['product_id'] for p in parents] + \
                  [l['product_id'] for l in legacies] + \
                  [v['product_id'] for v in variants]
        assume(len(all_ids) == len(set(all_ids)))
        # Need at least one expected result
        assume(len(parents) + len(legacies) > 0)

        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            for record in parents + legacies + variants:
                item = {k: v for k, v in record.items() if v is not None}
                table.put_item(Item=item)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])

            returned_ids = {item['product_id'] for item in body}

            # Parents and legacies should all be present
            expected_ids = {p['product_id'] for p in parents} | \
                           {l['product_id'] for l in legacies}
            assert expected_ids == returned_ids, (
                f"Expected IDs {expected_ids}, got {returned_ids}"
            )

            # No variant IDs
            variant_ids = {v['product_id'] for v in variants}
            assert returned_ids.isdisjoint(variant_ids)

    @given(
        num_migration_records=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_migration_source_records_excluded_regardless_of_is_parent(
        self, num_migration_records
    ):
        """
        Records with source='migration' are always excluded, even if they have
        is_parent=true or is_parent absent.
        """
        if 'app' in sys.modules:
            del sys.modules['app']

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Insert a normal parent (should be included)
            normal_id = str(uuid.uuid4())
            table.put_item(Item={
                'product_id': normal_id,
                'naam': 'Normal Product',
                'prijs': 10,
                'is_parent': True,
                'active': True,
            })

            # Insert migration records with is_parent=true (should be excluded)
            migration_ids = []
            for i in range(num_migration_records):
                mid = str(uuid.uuid4())
                migration_ids.append(mid)
                table.put_item(Item={
                    'product_id': mid,
                    'naam': f'Migration Product {i}',
                    'prijs': 15,
                    'is_parent': True,
                    'source': 'migration',
                    'active': True,
                })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])

            returned_ids = {item['product_id'] for item in body}

            # Normal product is included
            assert normal_id in returned_ids

            # Migration records are excluded
            for mid in migration_ids:
                assert mid not in returned_ids, (
                    f"Migration record {mid} should be excluded"
                )
