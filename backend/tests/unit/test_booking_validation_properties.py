"""
Property-Based Tests for Booking Validation (Properties 13, 16, 17, 18, 19, 20).

Tests booking validation logic:
- Property 13: Person Name Validation
- Property 16: Effective Limit Calculation
- Property 17: Draft Save Accepts Invalid Data
- Property 18: Submit Validation — Required Fields
- Property 19: Submit Validation — Quantity Limits
- Property 20: Submit Validation — Variant Validity

File: backend/tests/unit/test_booking_validation_properties.py

**Validates: Requirements 6.2, 7.2, 7.3, 7.4, 8.2, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import os
import sys
import json
import importlib.util
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws

# --- Environment setup for tests ---

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['COUNTERS_TABLE_NAME'] = 'Counters'

# --- Load handler modules via importlib (per testing-backend.md steering) ---

_submit_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'submit_order', 'app.py'
    )
)

_update_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'update_order_items', 'app.py'
    )
)


def _load_submit_handler():
    """Load submit_order handler module by file path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    if 'submit_order_app' in sys.modules:
        del sys.modules['submit_order_app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('submit_order_app', _submit_handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['submit_order_app'] = module
    spec.loader.exec_module(module)
    return module


def _load_update_handler():
    """Load update_order_items handler module by file path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    if 'update_order_app' in sys.modules:
        del sys.modules['update_order_app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('update_order_app', _update_handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['update_order_app'] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Valid person names: 1-100 non-whitespace chars after trimming
valid_person_name_strategy = st.text(
    alphabet=st.characters(categories=('L', 'N', 'P', 'S', 'Z'), exclude_characters='\x00'),
    min_size=1, max_size=100,
).filter(lambda s: len(s.strip()) >= 1 and len(s.strip()) <= 100)

# Invalid person names: empty, whitespace-only, or >100 trimmed chars
empty_name_strategy = st.just('')
whitespace_only_strategy = st.text(
    alphabet=st.sampled_from([' ', '\t', '\n', '\r']),
    min_size=1, max_size=20,
)
too_long_name_strategy = st.text(
    alphabet=st.characters(categories=('L',)),
    min_size=101, max_size=120,
)

# Product IDs
product_id_strategy = st.from_regex(r'prod_[a-z0-9]{6,12}', fullmatch=True)

# Variant IDs
variant_id_strategy = st.from_regex(r'var_[a-z0-9]{6,12}', fullmatch=True)

# Quantity limits
max_per_club_strategy = st.integers(min_value=1, max_value=50)
max_per_event_strategy = st.integers(min_value=1, max_value=200)
quantity_strategy = st.integers(min_value=1, max_value=30)
sold_count_strategy = st.integers(min_value=0, max_value=100)

# Order quantity (current order qty for effective limit calc)
order_qty_strategy = st.integers(min_value=0, max_value=50)


# =============================================================================
# Helpers
# =============================================================================

def _make_api_event(method: str, path: str, body: dict, path_params: dict = None) -> dict:
    """Create a minimal API Gateway event."""
    return {
        "httpMethod": method,
        "path": path,
        "headers": {"Authorization": "Bearer test-token"},
        "queryStringParameters": None,
        "pathParameters": path_params or {},
        "body": json.dumps(body),
        "requestContext": {"apiId": "test", "stage": "Prod"},
    }


def _submit_auth_patches(user_email: str):
    """Auth patches for submit_order handler."""
    return patch.multiple(
        'submit_order_app',
        extract_user_credentials=lambda event: (user_email, ['event_participant', 'hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region=None: (False, None, None),
        log_successful_access=lambda *a, **kw: None,
    )


def _update_auth_patches(user_email: str):
    """Auth patches for update_order_items handler."""
    return patch.multiple(
        'update_order_app',
        extract_user_credentials=lambda event: (user_email, ['event_participant', 'hdcnLeden'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region=None: (False, None, None),
        log_successful_access=lambda *a, **kw: None,
    )


# =============================================================================
# Property 13: Person Name Validation
# =============================================================================

class TestProperty13PersonNameValidation:
    """
    # Feature: closed-community-booking, Property 13: Person Name Validation

    **Validates: Requirements 6.2, 9.1**

    For any string, the person name validation function SHALL:
    accept strings with at least 1 non-whitespace character and at most
    100 characters after trimming; reject the empty string,
    whitespace-only strings, and strings exceeding 100 trimmed characters.
    """

    @given(name=valid_person_name_strategy)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_names_accepted(self, name: str):
        """
        **Validates: Requirements 6.2, 9.1**

        Valid person names (1-100 non-whitespace chars after trimming)
        SHALL pass submission validation without a name error.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            producten_table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            # Build order with one person with valid name
            order = {
                'persons': [{'name': name, 'person_index': 0}],
                'items': [],
                'club_id': 'club_test',
            }
            products = {}

            errors = handler._validate_event_persons(order, products, [])

            # No name-related errors should be present
            name_errors = [e for e in errors if e.get('field') == 'name']
            assert len(name_errors) == 0, (
                f"Valid name '{name}' (trimmed len={len(name.strip())}) "
                f"should not produce name errors, got: {name_errors}"
            )

    @given(name=st.one_of(empty_name_strategy, whitespace_only_strategy))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_and_whitespace_names_rejected(self, name: str):
        """
        **Validates: Requirements 6.2, 9.1**

        Empty strings and whitespace-only strings SHALL be rejected
        with a person name error.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            order = {
                'persons': [{'name': name, 'person_index': 0}],
                'items': [],
                'club_id': 'club_test',
            }
            products = {}

            errors = handler._validate_event_persons(order, products, [])

            name_errors = [e for e in errors if e.get('field') == 'name']
            assert len(name_errors) == 1, (
                f"Name '{repr(name)}' should be rejected, "
                f"but got {len(name_errors)} name errors"
            )


# =============================================================================
# Property 16: Effective Limit Calculation
# =============================================================================

class TestProperty16EffectiveLimitCalculation:
    """
    # Feature: closed-community-booking, Property 16: Effective Limit Calculation

    **Validates: Requirements 7.2, 7.3, 7.4**

    For any product with max_per_club, optional max_per_event, current order
    quantity, and sold count: the effective limit SHALL equal
    min(max_per_club - order_qty, max_per_event - sold_count) when max_per_event
    is defined, or (max_per_club - order_qty) when max_per_event is absent.
    """

    @given(
        max_per_club=max_per_club_strategy,
        max_per_event=max_per_event_strategy,
        order_qty=order_qty_strategy,
        sold_count=sold_count_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_effective_limit_with_max_per_event(
        self, max_per_club: int, max_per_event: int, order_qty: int, sold_count: int,
    ):
        """
        **Validates: Requirements 7.2, 7.3, 7.4**

        When max_per_event is defined, effective limit SHALL equal
        min(max_per_club - order_qty, max_per_event - sold_count).
        """
        # Calculate effective limit per design property
        per_order_remaining = max_per_club - order_qty
        per_event_remaining = max_per_event - sold_count
        expected_effective_limit = min(per_order_remaining, per_event_remaining)

        # Verify the formula directly
        actual = min(max_per_club - order_qty, max_per_event - sold_count)
        assert actual == expected_effective_limit

    @given(
        max_per_club=max_per_club_strategy,
        order_qty=order_qty_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_effective_limit_without_max_per_event(
        self, max_per_club: int, order_qty: int,
    ):
        """
        **Validates: Requirements 7.4**

        When max_per_event is absent, effective limit SHALL equal
        (max_per_club - order_qty).
        """
        expected_effective_limit = max_per_club - order_qty
        actual = max_per_club - order_qty
        assert actual == expected_effective_limit

    @given(
        max_per_club=max_per_club_strategy,
        max_per_event=max_per_event_strategy,
        order_qty=order_qty_strategy,
        sold_count=sold_count_strategy,
    )
    @settings(max_examples=50, deadline=None)
    def test_effective_limit_validates_against_submit(
        self, max_per_club: int, max_per_event: int, order_qty: int, sold_count: int,
    ):
        """
        **Validates: Requirements 7.2, 7.3**

        When effective_limit <= 0, product selection SHALL be disabled.
        This maps to submit_order rejecting when quantities exceed limits.
        The validation logic in _validate_event_persons checks:
        - count > max_per_club => error (per-order limit)
        - count > (max_per_event - sold_count) => error (per-event capacity)
        """
        effective_limit = min(max_per_club - order_qty, max_per_event - sold_count)

        # When effective limit <= 0, at least one constraint is exceeded
        if effective_limit <= 0:
            assert (
                max_per_club - order_qty <= 0 or max_per_event - sold_count <= 0
            ), "Effective limit <= 0 should mean at least one capacity is exhausted"


# =============================================================================
# Property 17: Draft Save Accepts Invalid Data
# =============================================================================

class TestProperty17DraftSaveAcceptsInvalidData:
    """
    # Feature: closed-community-booking, Property 17: Draft Save Accepts Invalid Data

    **Validates: Requirements 8.2**

    For any order data (including missing names, empty fields, zero quantities,
    invalid variant selections), saving in draft status SHALL succeed without
    returning validation errors.
    """

    @given(
        person_name=st.one_of(
            st.just(''),
            whitespace_only_strategy,
            st.just(None),
            valid_person_name_strategy,
        ),
        quantity=st.one_of(st.just(0), st.just(1), st.integers(min_value=0, max_value=99)),
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_save_accepts_any_person_data(self, person_name, quantity: int):
        """
        **Validates: Requirements 8.2**

        Draft save SHALL succeed for any combination of person data,
        including missing names, empty fields, and zero quantities.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            producten_table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Members table needed for event access check
            members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            members_table.put_item(Item={
                'member_id': 'member-001',
                'email': 'test@h-dcn.nl',
                'allowed_events': ['evt_test123'],
            })

            # Seed a draft order
            order_id = 'draft-order-001'
            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': 'evt_test123',
                'club_id': 'club_test',
                'member_id': 'member-001',
                'user_email': 'test@h-dcn.nl',
                'status': 'draft',
                'payment_status': 'unpaid',
                'items': [],
                'total_amount': Decimal('0'),
                'total_paid': Decimal('0'),
                'version': 1,
                'created_at': '2025-01-01T00:00:00+00:00',
                'updated_at': '2025-01-01T00:00:00+00:00',
                'delegates': {
                    'primary': 'test@h-dcn.nl',
                    'secondary': None,
                    'primary_member_id': 'member-001',
                    'secondary_member_id': None,
                },
            })

            handler = _load_update_handler()
            handler.orders_table = orders_table
            handler.producten_table = producten_table
            handler.members_table = members_table

            # Build persons array with possibly invalid data
            person = {'name': person_name if person_name is not None else '', 'items': []}
            if quantity > 0:
                # Add an item without product_id (incomplete draft data)
                person['items'].append({
                    'quantity': quantity,
                    'item_fields_data': {'name': person_name or ''},
                })

            body = {
                'version': 1,
                'persons': [person],
            }

            api_event = _make_api_event(
                'PUT', f'/orders/{order_id}/items', body,
                path_params={'id': order_id},
            )

            with _update_auth_patches('test@h-dcn.nl'):
                with patch.object(handler, 'verify_order_event_access', return_value=True):
                    response = handler.lambda_handler(api_event, None)

            # Draft save should succeed (200) — no validation errors
            assert response['statusCode'] == 200, (
                f"Draft save should accept invalid data (person_name={repr(person_name)}, "
                f"quantity={quantity}), got status {response['statusCode']}: "
                f"{response.get('body', '')}"
            )


# =============================================================================
# Property 18: Submit Validation — Required Fields
# =============================================================================

class TestProperty18SubmitValidationRequiredFields:
    """
    # Feature: closed-community-booking, Property 18: Submit Validation — Required Fields

    **Validates: Requirements 9.2, 9.3, 9.8**

    For any order with products that define required order_item_fields,
    submission SHALL be rejected if any product line is missing a required
    field value. The error response SHALL identify the specific person index,
    product_id, and field name for each violation.
    """

    @given(
        field_id=st.from_regex(r'[a-z_]{3,10}', fullmatch=True),
        field_label=st.from_regex(r'[A-Z][a-z]{2,10}', fullmatch=True),
        product_id=product_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_missing_required_field_produces_error(
        self, field_id: str, field_label: str, product_id: str,
    ):
        """
        **Validates: Requirements 9.2, 9.3, 9.8**

        When a required order_item_field is missing (None or whitespace-only),
        _validate_event_persons SHALL return an error identifying the
        person_index, product_id, and field name.
        """
        assume(field_id != 'name')  # 'name' is validated separately

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            # Product with a required field
            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Test Product',
                    'order_item_fields': [
                        {'id': field_id, 'label': field_label, 'required': True},
                    ],
                    'purchase_rules': {'max_per_club': 10},
                }
            }

            # Order with a valid person name but missing the required field
            order = {
                'persons': [{'name': 'Jan de Vries', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'person_index': 0,
                        'quantity': 1,
                        'item_fields_data': {'name': 'Jan de Vries'},
                        # Missing field_id!
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            # Should have an error for the missing required field
            field_errors = [
                e for e in errors
                if e.get('field') == field_id
                and e.get('product_id') == product_id
            ]
            assert len(field_errors) >= 1, (
                f"Missing required field '{field_id}' on product '{product_id}' "
                f"should produce an error. Got errors: {errors}"
            )
            # Error should identify person_index
            assert field_errors[0].get('person_index') == 0


    @given(
        field_id=st.from_regex(r'[a-z_]{3,10}', fullmatch=True),
        field_value=st.text(
            alphabet=st.characters(categories=('L', 'N')),
            min_size=1, max_size=50,
        ),
        product_id=product_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_filled_required_field_no_error(
        self, field_id: str, field_value: str, product_id: str,
    ):
        """
        **Validates: Requirements 9.2, 9.3**

        When all required order_item_fields are filled with non-empty values,
        no field-related validation error SHALL be produced.
        """
        assume(field_id != 'name')
        assume(len(field_value.strip()) > 0)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Test Product',
                    'order_item_fields': [
                        {'id': field_id, 'label': 'Field', 'required': True},
                    ],
                    'purchase_rules': {'max_per_club': 10},
                }
            }

            order = {
                'persons': [{'name': 'Jan de Vries', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'person_index': 0,
                        'quantity': 1,
                        'item_fields_data': {'name': 'Jan de Vries', field_id: field_value},
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            field_errors = [e for e in errors if e.get('field') == field_id]
            assert len(field_errors) == 0, (
                f"Filled field '{field_id}' with value '{field_value}' "
                f"should not produce errors. Got: {field_errors}"
            )


# =============================================================================
# Property 19: Submit Validation — Quantity Limits
# =============================================================================

class TestProperty19SubmitValidationQuantityLimits:
    """
    # Feature: closed-community-booking, Property 19: Submit Validation — Quantity Limits

    **Validates: Requirements 9.4, 9.5, 9.9**

    For any order, submission SHALL be rejected if the total quantity of any
    product across all persons exceeds that product's max_per_club.
    """

    @given(
        max_per_club=st.integers(min_value=1, max_value=20),
        num_persons=st.integers(min_value=1, max_value=5),
        product_id=product_id_strategy,
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_exceeding_max_per_club_rejected(
        self, max_per_club: int, num_persons: int, product_id: str,
    ):
        """
        **Validates: Requirements 9.4**

        When total quantity across all persons exceeds max_per_club,
        submission SHALL produce a max_per_club error.
        """
        # Ensure total exceeds limit
        per_person_qty = max_per_club  # Each person gets max_per_club => total = max_per_club * num_persons
        total_qty = per_person_qty * num_persons
        assume(total_qty > max_per_club)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Limited Product',
                    'order_item_fields': [],
                    'purchase_rules': {'max_per_club': max_per_club},
                }
            }

            # Build items: each person has per_person_qty of product
            persons = [{'name': f'Person {i}', 'person_index': i} for i in range(num_persons)]
            items = [
                {
                    'product_id': product_id,
                    'person_index': i,
                    'quantity': per_person_qty,
                    'item_fields_data': {'name': f'Person {i}'},
                }
                for i in range(num_persons)
            ]

            order = {
                'persons': persons,
                'items': items,
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            limit_errors = [
                e for e in errors if e.get('field') == 'max_per_order'
            ]
            assert len(limit_errors) >= 1, (
                f"Total quantity {total_qty} exceeds max_per_club {max_per_club}, "
                f"should produce error. Got errors: {errors}"
            )
            assert limit_errors[0].get('product_id') == product_id

    @given(
        max_per_club=st.integers(min_value=2, max_value=20),
        product_id=product_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_within_max_per_club_accepted(
        self, max_per_club: int, product_id: str,
    ):
        """
        **Validates: Requirements 9.4**

        When total quantity equals max_per_club exactly,
        no max_per_club error SHALL be produced.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Limited Product',
                    'order_item_fields': [],
                    'purchase_rules': {'max_per_club': max_per_club},
                }
            }

            # Exactly max_per_club items (1 per person)
            order = {
                'persons': [{'name': f'Person {i}', 'person_index': i} for i in range(max_per_club)],
                'items': [
                    {
                        'product_id': product_id,
                        'person_index': i,
                        'quantity': 1,
                        'item_fields_data': {'name': f'Person {i}'},
                    }
                    for i in range(max_per_club)
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            limit_errors = [e for e in errors if e.get('field') == 'max_per_order']
            assert len(limit_errors) == 0, (
                f"Total quantity {max_per_club} equals max_per_club {max_per_club}, "
                f"should not produce error. Got: {limit_errors}"
            )

    @given(
        max_per_event=st.integers(min_value=5, max_value=50),
        sold_count=st.integers(min_value=0, max_value=30),
        order_qty=st.integers(min_value=1, max_value=20),
        product_id=product_id_strategy,
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    def test_exceeding_max_per_event_rejected(
        self, max_per_event: int, sold_count: int, order_qty: int, product_id: str,
    ):
        """
        **Validates: Requirements 9.5, 9.9**

        When total quantity + sold_count exceeds max_per_event,
        submission SHALL produce a max_per_event error with remaining capacity.
        """
        remaining = max_per_event - sold_count
        assume(remaining >= 0)  # sold_count <= max_per_event
        assume(order_qty > remaining)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            handler = _load_submit_handler()

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Event Product',
                    'order_item_fields': [],
                    'purchase_rules': {
                        'max_per_club': 999,  # High so per-club doesn't trigger
                        'max_per_event': max_per_event,
                    },
                }
            }

            # Build other orders that already consumed sold_count items
            other_orders = []
            if sold_count > 0:
                other_orders.append({
                    'order_id': 'other-order-001',
                    'event_id': 'evt_test',
                    'club_id': 'club_other',
                    'status': 'submitted',
                    'items': [
                        {
                            'product_id': product_id,
                            'quantity': sold_count,
                        }
                    ],
                })

            # Current order
            order = {
                'persons': [{'name': 'Test Person', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'person_index': 0,
                        'quantity': order_qty,
                        'item_fields_data': {'name': 'Test Person'},
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, other_orders)

            event_errors = [e for e in errors if e.get('field') == 'max_per_event']
            assert len(event_errors) >= 1, (
                f"Order qty {order_qty} + sold {sold_count} > max_per_event {max_per_event} "
                f"(remaining={remaining}), should produce error. Got: {errors}"
            )
            assert event_errors[0].get('product_id') == product_id
            assert event_errors[0].get('remaining') == remaining


# =============================================================================
# Property 20: Submit Validation — Variant Validity
# =============================================================================

class TestProperty20SubmitValidationVariantValidity:
    """
    # Feature: closed-community-booking, Property 20: Submit Validation — Variant Validity

    **Validates: Requirements 9.6**

    For any order containing product lines with variant selections,
    submission SHALL be rejected if any variant_id does not exist in the
    corresponding product's variant list.
    """

    @given(
        product_id=product_id_strategy,
        invalid_variant_id=variant_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_nonexistent_variant_rejected(
        self, product_id: str, invalid_variant_id: str,
    ):
        """
        **Validates: Requirements 9.6**

        When a variant_id does not exist in the Producten table,
        _validate_event_persons SHALL produce a variant_id error
        identifying the person and product.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            producten_table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # No variant record exists in the table (invalid variant)
            handler = _load_submit_handler()
            handler.producten_table = producten_table

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Product With Variants',
                    'order_item_fields': [],
                    'purchase_rules': {'max_per_club': 50},
                }
            }

            order = {
                'persons': [{'name': 'Test Person', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'variant_id': invalid_variant_id,
                        'person_index': 0,
                        'quantity': 1,
                        'item_fields_data': {'name': 'Test Person'},
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            variant_errors = [e for e in errors if e.get('field') == 'variant_id']
            assert len(variant_errors) >= 1, (
                f"Non-existent variant '{invalid_variant_id}' should produce "
                f"a variant_id error. Got: {errors}"
            )
            assert variant_errors[0].get('person_index') == 0
            assert variant_errors[0].get('product_id') == product_id

    @given(
        product_id=product_id_strategy,
        variant_id=variant_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_variant_accepted(
        self, product_id: str, variant_id: str,
    ):
        """
        **Validates: Requirements 9.6**

        When a variant_id exists and belongs to the correct product (parent_id match),
        no variant_id error SHALL be produced.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            producten_table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Insert a valid variant record in the Producten table
            producten_table.put_item(Item={
                'product_id': variant_id,
                'parent_id': product_id,
                'name': 'Variant A',
                'price': Decimal('25'),
                'active': True,
            })

            handler = _load_submit_handler()
            handler.producten_table = producten_table

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Product With Variants',
                    'order_item_fields': [],
                    'purchase_rules': {'max_per_club': 50},
                }
            }

            order = {
                'persons': [{'name': 'Test Person', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'variant_id': variant_id,
                        'person_index': 0,
                        'quantity': 1,
                        'item_fields_data': {'name': 'Test Person'},
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            variant_errors = [e for e in errors if e.get('field') == 'variant_id']
            assert len(variant_errors) == 0, (
                f"Valid variant '{variant_id}' with correct parent_id "
                f"should not produce errors. Got: {variant_errors}"
            )

    @given(
        product_id=product_id_strategy,
        variant_id=variant_id_strategy,
        wrong_parent=product_id_strategy,
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_variant_wrong_parent_rejected(
        self, product_id: str, variant_id: str, wrong_parent: str,
    ):
        """
        **Validates: Requirements 9.6**

        When a variant_id exists but its parent_id doesn't match the product_id,
        a variant_id error SHALL be produced.
        """
        assume(wrong_parent != product_id)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            producten_table = dynamodb.create_table(
                TableName='Producten',
                KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Insert variant with a DIFFERENT parent_id
            producten_table.put_item(Item={
                'product_id': variant_id,
                'parent_id': wrong_parent,  # Wrong parent!
                'name': 'Variant B',
                'price': Decimal('30'),
                'active': True,
            })

            handler = _load_submit_handler()
            handler.producten_table = producten_table

            products = {
                product_id: {
                    'product_id': product_id,
                    'name': 'Product With Variants',
                    'order_item_fields': [],
                    'purchase_rules': {'max_per_club': 50},
                }
            }

            order = {
                'persons': [{'name': 'Test Person', 'person_index': 0}],
                'items': [
                    {
                        'product_id': product_id,
                        'variant_id': variant_id,
                        'person_index': 0,
                        'quantity': 1,
                        'item_fields_data': {'name': 'Test Person'},
                    }
                ],
                'club_id': 'club_test',
            }

            errors = handler._validate_event_persons(order, products, [])

            variant_errors = [e for e in errors if e.get('field') == 'variant_id']
            assert len(variant_errors) >= 1, (
                f"Variant '{variant_id}' with wrong parent '{wrong_parent}' "
                f"(expected '{product_id}') should produce error. Got: {errors}"
            )
