"""
Property-Based Tests for scan_product handler (Properties 6 & 7)

**Validates: Requirements 5.4, 5.5, 9.1, 9.2**

Property 6: scan_product response normalization
    For any product record where is_parent is true or absent, the response SHALL
    include product_id, name, price, variant_schema, is_parent, event_id, active —
    using naam as fallback for name and prijs as fallback for price.

Property 7: scan_product excludes variant and migration records
    The scan_product handler SHALL return only records where is_parent is true or
    absent, AND source is not "migration".
"""

import json
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

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


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

    Some products use 'name'/'price' (unified), some use 'naam'/'prijs' (legacy),
    and some have both fields present.
    """
    product_id = draw(product_id_strategy())
    name_value = draw(product_name_strategy())
    price_value = draw(price_strategy())
    has_variant_schema = draw(st.booleans())
    has_event_id = draw(st.booleans())
    is_active = draw(st.booleans())

    # Determine field naming convention
    naming = draw(st.sampled_from(['unified', 'legacy', 'both']))

    record = {
        'product_id': product_id,
        'is_parent': True,
        'active': is_active,
    }

    if naming == 'unified':
        record['name'] = name_value
        record['price'] = price_value
    elif naming == 'legacy':
        record['naam'] = name_value
        record['prijs'] = price_value
    else:  # both
        record['name'] = name_value
        record['naam'] = f"legacy_{name_value}"
        record['price'] = price_value
        record['prijs'] = price_value + 1  # different to test preference

    if has_variant_schema:
        record['variant_schema'] = draw(variant_schema_strategy())

    if has_event_id:
        record['event_id'] = draw(st.uuids().map(str))
    else:
        record['event_id'] = None

    return record


@st.composite
def product_without_is_parent_strategy(draw):
    """Generate a product record without the is_parent attribute (legacy record)."""
    product_id = draw(product_id_strategy())
    name_value = draw(product_name_strategy())
    price_value = draw(price_strategy())

    naming = draw(st.sampled_from(['unified', 'legacy', 'both']))

    record = {
        'product_id': product_id,
        'active': True,
    }

    if naming == 'unified':
        record['name'] = name_value
        record['price'] = price_value
    elif naming == 'legacy':
        record['naam'] = name_value
        record['prijs'] = price_value
    else:
        record['name'] = name_value
        record['naam'] = f"legacy_{name_value}"
        record['price'] = price_value
        record['prijs'] = price_value + 5

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
        'name': draw(product_name_strategy()),
        'price': draw(price_strategy()),
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
        'name': draw(product_name_strategy()),
        'price': draw(price_strategy()),
        'source': 'migration',
        'is_parent': draw(st.sampled_from([True, None])),
    }


# =============================================================================
# Property 6: scan_product response normalization
# =============================================================================

class TestProperty6ScanProductNormalization:
    """
    **Validates: Requirements 5.4, 9.1, 9.2**

    Property 6: For any product record where is_parent is true or absent,
    the response SHALL include product_id, name, price, variant_schema,
    is_parent, event_id, active — using naam as fallback for name and prijs
    as fallback for price.
    """

    @given(product=parent_product_strategy())
    @settings(max_examples=100, deadline=None)
    def test_normalized_response_includes_all_required_fields(self, product):
        """
        For any parent product record, the normalized response contains all
        required fields: product_id, name, price, variant_schema, is_parent,
        event_id, active.
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

            # Ensure handler path is first
            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body) == 1

            result = body[0]

            # All required fields must be present as keys
            required_fields = ['product_id', 'name', 'price', 'variant_schema',
                               'is_parent', 'event_id', 'active']
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
    def test_naam_fallback_for_name(self, product):
        """
        The response uses 'naam' as fallback for 'name' when 'name' is not
        present. When 'name' is present, it takes precedence over 'naam'.
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

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # If 'name' was in the record, it should be used
            if 'name' in product:
                assert result['name'] == product['name']
            elif 'naam' in product:
                # naam is fallback
                assert result['name'] == product['naam']
            else:
                # Neither present — name should be None
                assert result['name'] is None

    @given(product=parent_product_strategy())
    @settings(max_examples=100, deadline=None)
    def test_prijs_fallback_for_price(self, product):
        """
        The response uses 'prijs' as fallback for 'price' when 'price' is not
        present. When 'price' is present, it takes precedence over 'prijs'.
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

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            body = json.loads(response['body'])
            result = body[0]

            # If 'price' was in the record, it should be used
            if 'price' in product:
                assert result['price'] == product['price']
            elif 'prijs' in product:
                # prijs is fallback
                assert result['price'] == product['prijs']
            else:
                assert result['price'] is None

    @given(product=product_without_is_parent_strategy())
    @settings(max_examples=100, deadline=None)
    def test_products_without_is_parent_are_normalized(self, product):
        """
        Products without an is_parent attribute are included in the response
        and normalized with all required fields.
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

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event(), {})

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert len(body) == 1

            result = body[0]

            # All required fields present
            required_fields = ['product_id', 'name', 'price', 'variant_schema',
                               'is_parent', 'event_id', 'active']
            for field in required_fields:
                assert field in result, f"Field '{field}' must be in response"

            # name fallback works
            if 'name' in product:
                assert result['name'] == product['name']
            elif 'naam' in product:
                assert result['name'] == product['naam']

            # price fallback works
            if 'price' in product:
                assert result['price'] == product['price']
            elif 'prijs' in product:
                assert result['price'] == product['prijs']


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

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

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

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

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
                'name': 'Normal Product',
                'price': 10,
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
                    'name': f'Migration Product {i}',
                    'price': 15,
                    'is_parent': True,
                    'source': 'migration',
                    'active': True,
                })

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module

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
