"""
Unit tests for the update_cart_items handler.

Tests the unified cart update logic: variant validation, stock checking,
item_fields_data handling, quantity decrease, and schema evolution.
(Requirements 6.1-6.5, 6.7, 8.3, 8.7, 8.8, 8.9)
"""

import json
import os
import sys
import pytest
import boto3
from decimal import Decimal
from moto import mock_aws

# Add handler path and auth layer to path for direct imports
_handler_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'handler', 'update_cart_items'))
_layers_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Remove any previously cached 'app' module so we import from the correct handler
if 'app' in sys.modules:
    del sys.modules['app']

# Import handler functions (module loaded with shared layer available)
from app import (
    _validate_variant_for_product,
    _check_stock_availability,
    _apply_quantity_decrease,
    _apply_schema_evolution,
    _validate_and_process_items,
    _handle_quantity_decrease_for_existing_cart,
    _calculate_total,
)
import app as handler_module


@pytest.fixture(autouse=True)
def aws_env():
    """Set up AWS mocked environment."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'


@pytest.fixture
def mock_tables():
    """Create mocked DynamoDB Carts and Producten tables and seed data."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Carts table
        carts = dynamodb.create_table(
            TableName='Carts',
            KeySchema=[{'AttributeName': 'cart_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'cart_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create Producten table
        producten = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Seed parent product
        producten.put_item(Item={
            'product_id': 'prod_shirt01',
            'is_parent': True,
            'parent_id': None,
            'tenant': 'h-dcn',
            'name': 'Club T-shirt',
            'price': Decimal('25.00'),
            'active': True,
            'order_item_fields': [
                {'id': 'attendee_name', 'label': 'Naam', 'type': 'text', 'required': True},
                {'id': 'dietary', 'label': 'Dieet', 'type': 'select', 'required': False,
                 'options': ['Geen', 'Vegetarisch']},
            ],
        })

        # Seed variant (Maat=M) with stock
        producten.put_item(Item={
            'product_id': 'var_prod_shirt01_m',
            'is_parent': False,
            'parent_id': 'prod_shirt01',
            'tenant': 'h-dcn',
            'variant_attributes': {'Maat': 'M'},
            'price': Decimal('25.00'),
            'stock': 10,
            'sold_count': 0,
            'allow_oversell': False,
            'active': True,
        })

        # Seed variant with oversell allowed and zero stock
        producten.put_item(Item={
            'product_id': 'var_prod_shirt01_xl',
            'is_parent': False,
            'parent_id': 'prod_shirt01',
            'tenant': 'h-dcn',
            'variant_attributes': {'Maat': 'XL'},
            'price': Decimal('25.00'),
            'stock': 0,
            'sold_count': 0,
            'allow_oversell': True,
            'active': True,
        })

        # Seed cart owned by test user
        carts.put_item(Item={
            'cart_id': 'cart_001',
            'customer_id': 'member_1',
            'user_email': 'buyer@h-dcn.nl',
            'items': [],
            'total_amount': Decimal('0'),
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00',
        })

        # Patch handler module to use mocked tables
        handler_module.carts_table = carts
        handler_module.producten_table = producten

        yield {'carts': carts, 'producten': producten}


class TestVariantValidation:
    """Tests for variant validation logic (Req 6.1-6.5)."""

    def test_valid_variant(self, mock_tables):
        """Variant that exists and belongs to product passes validation."""
        variant, error = _validate_variant_for_product('var_prod_shirt01_m', 'prod_shirt01')
        assert error is None
        assert variant is not None
        assert variant['variant_attributes'] == {'Maat': 'M'}

    def test_variant_not_found(self, mock_tables):
        """Non-existent variant returns variant_not_found error."""
        variant, error = _validate_variant_for_product('var_nonexistent', 'prod_shirt01')
        assert variant is None
        assert error['error'] == 'variant_not_found'
        assert error['details']['product_id'] == 'prod_shirt01'
        assert error['details']['variant_id'] == 'var_nonexistent'

    def test_variant_wrong_parent(self, mock_tables):
        """Variant belonging to different product returns variant_not_found."""
        variant, error = _validate_variant_for_product('var_prod_shirt01_m', 'prod_other')
        assert variant is None
        assert error['error'] == 'variant_not_found'

    def test_parent_record_not_accepted_as_variant(self, mock_tables):
        """A parent product record is not accepted as a variant."""
        variant, error = _validate_variant_for_product('prod_shirt01', 'prod_shirt01')
        assert variant is None
        assert error['error'] == 'variant_not_found'


class TestStockAvailability:
    """Tests for stock checking logic (Req 6.7)."""

    def test_sufficient_stock(self, mock_tables):
        """Variant with enough stock passes check."""
        variant = {'product_id': 'var_m', 'stock': 10, 'allow_oversell': False}
        assert _check_stock_availability(variant, 5) is None

    def test_exact_stock_passes(self, mock_tables):
        """Quantity equal to stock passes check."""
        variant = {'product_id': 'var_m', 'stock': 5, 'allow_oversell': False}
        assert _check_stock_availability(variant, 5) is None

    def test_insufficient_stock(self, mock_tables):
        """Variant with insufficient stock returns error."""
        variant = {'product_id': 'var_m', 'stock': 2, 'allow_oversell': False}
        error = _check_stock_availability(variant, 5)
        assert error is not None
        assert error['error'] == 'insufficient_stock'
        assert error['details']['available'] == 2
        assert error['details']['requested'] == 5
        assert error['details']['variant_id'] == 'var_m'

    def test_oversell_allowed_bypasses_stock_check(self, mock_tables):
        """Variant with allow_oversell=True always passes stock check."""
        variant = {'product_id': 'var_xl', 'stock': 0, 'allow_oversell': True}
        assert _check_stock_availability(variant, 100) is None

    def test_zero_stock_no_oversell_rejected(self, mock_tables):
        """Zero stock with no oversell is rejected."""
        variant = {'product_id': 'var_m', 'stock': 0, 'allow_oversell': False}
        error = _check_stock_availability(variant, 1)
        assert error is not None
        assert error['error'] == 'insufficient_stock'


class TestQuantityDecrease:
    """Tests for quantity decrease item_fields_data trimming (Req 8.8)."""

    def test_decrease_trims_from_end(self):
        """Decreasing quantity removes highest-indexed entries."""
        data = [
            {'attendee_name': 'Jan'},
            {'attendee_name': 'Piet'},
            {'attendee_name': 'Klaas'},
        ]
        result = _apply_quantity_decrease(data, 2)
        assert len(result) == 2
        assert result[0]['attendee_name'] == 'Jan'
        assert result[1]['attendee_name'] == 'Piet'

    def test_decrease_to_one(self):
        """Decreasing to 1 keeps only the first entry."""
        data = [
            {'attendee_name': 'Jan'},
            {'attendee_name': 'Piet'},
        ]
        result = _apply_quantity_decrease(data, 1)
        assert len(result) == 1
        assert result[0]['attendee_name'] == 'Jan'

    def test_decrease_to_zero(self):
        """Decreasing to 0 returns empty list."""
        data = [{'attendee_name': 'Jan'}]
        result = _apply_quantity_decrease(data, 0)
        assert result == []

    def test_empty_data_returns_empty(self):
        """Empty input returns empty list."""
        result = _apply_quantity_decrease([], 2)
        assert result == []

    def test_none_data_returns_empty(self):
        """None input returns empty list."""
        result = _apply_quantity_decrease(None, 2)
        assert result == []


class TestSchemaEvolution:
    """Tests for schema evolution - discarding orphaned field values (Req 8.9)."""

    def test_orphaned_fields_removed(self):
        """Fields not in current definition are discarded."""
        product = {
            'order_item_fields': [
                {'id': 'attendee_name', 'label': 'Naam', 'type': 'text', 'required': True},
            ]
        }
        data = [
            {'attendee_name': 'Jan', 'old_field': 'should_be_removed'},
            {'attendee_name': 'Piet', 'old_field': 'also_removed'},
        ]
        result = _apply_schema_evolution(data, product)
        assert len(result) == 2
        assert 'old_field' not in result[0]
        assert 'old_field' not in result[1]
        assert result[0]['attendee_name'] == 'Jan'
        assert result[1]['attendee_name'] == 'Piet'

    def test_valid_fields_retained(self):
        """Fields that still exist in definition are kept."""
        product = {
            'order_item_fields': [
                {'id': 'name', 'label': 'Name', 'type': 'text', 'required': True},
                {'id': 'dietary', 'label': 'Diet', 'type': 'select', 'required': False},
            ]
        }
        data = [{'name': 'Jan', 'dietary': 'Vegan'}]
        result = _apply_schema_evolution(data, product)
        assert result[0] == {'name': 'Jan', 'dietary': 'Vegan'}

    def test_no_order_item_fields_returns_data_unchanged(self):
        """Products without order_item_fields don't modify data."""
        product = {}
        data = [{'any_field': 'value'}]
        result = _apply_schema_evolution(data, product)
        assert result == data

    def test_field_values_wrapper_format(self):
        """Handles {'field_values': {...}} wrapper format."""
        product = {
            'order_item_fields': [
                {'id': 'name', 'label': 'Name', 'type': 'text', 'required': True},
            ]
        }
        data = [{'field_values': {'name': 'Jan', 'removed_field': 'gone'}}]
        result = _apply_schema_evolution(data, product)
        assert result[0] == {'field_values': {'name': 'Jan'}}

    def test_empty_item_fields_data_returns_unchanged(self):
        """Empty item_fields_data list is returned as-is."""
        product = {
            'order_item_fields': [
                {'id': 'name', 'label': 'Name', 'type': 'text', 'required': True},
            ]
        }
        result = _apply_schema_evolution([], product)
        assert result == []


class TestValidateAndProcessItems:
    """Tests for the full item validation/processing pipeline."""

    def test_valid_items_processed(self, mock_tables):
        """Valid items are processed with variant_attributes populated."""
        items = [{
            'product_id': 'prod_shirt01',
            'variant_id': 'var_prod_shirt01_m',
            'quantity': 2,
        }]
        processed, error = _validate_and_process_items(items)
        assert error is None
        assert len(processed) == 1
        assert processed[0]['variant_id'] == 'var_prod_shirt01_m'
        assert processed[0]['variant_attributes'] == {'Maat': 'M'}
        assert processed[0]['quantity'] == 2
        # No selectedOption field
        assert 'selectedOption' not in processed[0]

    def test_missing_product_id_rejected(self, mock_tables):
        """Item without product_id is rejected."""
        items = [{'variant_id': 'var_x', 'quantity': 1}]
        processed, error = _validate_and_process_items(items)
        assert processed is None
        assert error is not None

    def test_missing_variant_id_rejected(self, mock_tables):
        """Item without variant_id is rejected."""
        items = [{'product_id': 'prod_shirt01', 'quantity': 1}]
        processed, error = _validate_and_process_items(items)
        assert processed is None
        assert error is not None

    def test_invalid_quantity_rejected(self, mock_tables):
        """Item with quantity < 1 is rejected."""
        items = [{
            'product_id': 'prod_shirt01',
            'variant_id': 'var_prod_shirt01_m',
            'quantity': 0,
        }]
        processed, error = _validate_and_process_items(items)
        assert processed is None
        assert error is not None

    def test_insufficient_stock_rejected(self, mock_tables):
        """Item exceeding stock is rejected."""
        items = [{
            'product_id': 'prod_shirt01',
            'variant_id': 'var_prod_shirt01_m',
            'quantity': 999,  # Stock is 10
        }]
        processed, error = _validate_and_process_items(items)
        assert processed is None
        assert error is not None

    def test_oversell_variant_accepted_with_zero_stock(self, mock_tables):
        """Oversell variant is accepted even with zero stock."""
        items = [{
            'product_id': 'prod_shirt01',
            'variant_id': 'var_prod_shirt01_xl',
            'quantity': 50,
        }]
        processed, error = _validate_and_process_items(items)
        assert error is None
        assert len(processed) == 1

    def test_item_fields_data_carried_through(self, mock_tables):
        """item_fields_data is preserved on processed items."""
        items = [{
            'product_id': 'prod_shirt01',
            'variant_id': 'var_prod_shirt01_m',
            'quantity': 2,
            'item_fields_data': [
                {'attendee_name': 'Jan', 'dietary': 'Geen'},
                {'attendee_name': 'Piet', 'dietary': 'Vegetarisch'},
            ],
        }]
        processed, error = _validate_and_process_items(items)
        assert error is None
        assert 'item_fields_data' in processed[0]
        assert len(processed[0]['item_fields_data']) == 2


class TestHandleQuantityDecreaseForExistingCart:
    """Tests for merging existing cart data with new items on quantity decrease."""

    def test_quantity_decrease_trims_existing_fields(self):
        """When quantity decreases, existing item_fields_data is trimmed."""
        existing = [{
            'product_id': 'prod_1',
            'variant_id': 'var_1',
            'quantity': 3,
            'item_fields_data': [
                {'name': 'A'},
                {'name': 'B'},
                {'name': 'C'},
            ],
        }]
        new_items = [{
            'product_id': 'prod_1',
            'variant_id': 'var_1',
            'quantity': 1,
        }]
        result = _handle_quantity_decrease_for_existing_cart(existing, new_items)
        assert 'item_fields_data' in result[0]
        assert len(result[0]['item_fields_data']) == 1
        assert result[0]['item_fields_data'][0]['name'] == 'A'

    def test_quantity_increase_preserves_existing_fields(self):
        """When quantity increases, existing item_fields_data is preserved."""
        existing = [{
            'product_id': 'prod_1',
            'variant_id': 'var_1',
            'quantity': 2,
            'item_fields_data': [
                {'name': 'A'},
                {'name': 'B'},
            ],
        }]
        new_items = [{
            'product_id': 'prod_1',
            'variant_id': 'var_1',
            'quantity': 4,
        }]
        result = _handle_quantity_decrease_for_existing_cart(existing, new_items)
        assert 'item_fields_data' in result[0]
        assert len(result[0]['item_fields_data']) == 2

    def test_new_item_not_in_existing_cart(self):
        """New items not in existing cart are unchanged."""
        existing = []
        new_items = [{
            'product_id': 'prod_1',
            'variant_id': 'var_1',
            'quantity': 2,
        }]
        result = _handle_quantity_decrease_for_existing_cart(existing, new_items)
        assert 'item_fields_data' not in result[0]


class TestCalculateTotal:
    """Tests for cart total calculation."""

    def test_single_item(self):
        """Single item total calculation."""
        items = [{'unit_price': Decimal('25.00'), 'quantity': 2}]
        assert _calculate_total(items) == Decimal('50.00')

    def test_multiple_items(self):
        """Multiple items summed correctly."""
        items = [
            {'unit_price': Decimal('25.00'), 'quantity': 2},
            {'unit_price': Decimal('10.00'), 'quantity': 3},
        ]
        assert _calculate_total(items) == Decimal('80.00')

    def test_no_price_skipped(self):
        """Items without price don't contribute to total."""
        items = [
            {'unit_price': None, 'quantity': 2},
            {'unit_price': Decimal('10.00'), 'quantity': 1},
        ]
        assert _calculate_total(items) == Decimal('10.00')
