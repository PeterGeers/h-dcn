"""
Integration tests for admin product management endpoints.

Tests shared module functions with moto-mocked DynamoDB and S3 to verify
full lifecycle behavior without needing to mock the Lambda auth layer.
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# sys.path setup: ensure we can import from handler/ and handler/shared/
# ---------------------------------------------------------------------------
_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_handler_path = os.path.join(_backend_root, 'handler')
_shared_path = os.path.join(_handler_path, 'shared')

for p in [_handler_path, _shared_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# Environment variables (must be set BEFORE importing modules that read them)
# ---------------------------------------------------------------------------
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['STOCK_MOVEMENTS_TABLE_NAME'] = 'StockMovements'
os.environ['REPORTS_BUCKET_NAME'] = 'h-dcn-webshop-reports'

# ---------------------------------------------------------------------------
# Imports from shared modules under test
# ---------------------------------------------------------------------------
from order_state_machine import is_valid_transition, get_next_valid_states
from variant_helpers import (
    create_default_variant,
    generate_variant_combinations,
    should_remove_default_variant,
)
from product_validation import validate_product, validate_variant_attributes
from payment_helpers import compute_payment_aggregates
from stock_helpers import reserve_stock, create_inbound_movement


# ===========================================================================
# FIXTURES (Task 22.1)
# ===========================================================================


@pytest.fixture
def aws_env():
    """Set up mocked AWS environment with DynamoDB tables and S3 bucket."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        s3 = boto3.client('s3', region_name='eu-west-1')

        # --- Producten table (PK: product_id) ---
        producten_table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # --- Orders table (PK: order_id) ---
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'order_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # --- StockMovements table (PK: movement_id) with GSIs ---
        movements_table = dynamodb.create_table(
            TableName='StockMovements',
            KeySchema=[{'AttributeName': 'movement_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'movement_id', 'AttributeType': 'S'},
                {'AttributeName': 'variant_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'variant_id-index',
                    'KeySchema': [
                        {'AttributeName': 'variant_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # --- S3 reports bucket ---
        s3.create_bucket(
            Bucket='h-dcn-webshop-reports',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )

        yield {
            'dynamodb': dynamodb,
            's3': s3,
            'producten_table': producten_table,
            'orders_table': orders_table,
            'movements_table': movements_table,
        }


# ===========================================================================
# Task 22.2: Integration test for full order lifecycle
# ===========================================================================


class TestOrderLifecycle:
    """Full order lifecycle: create → submit → lock → paid (stock reserved) → shipped → delivered → completed."""

    def test_full_order_lifecycle_with_stock_reservation(self, aws_env):
        """Test the complete order lifecycle including stock reservation on paid transition."""
        producten_table = aws_env['producten_table']
        orders_table = aws_env['orders_table']
        movements_table = aws_env['movements_table']

        # --- Setup: Create a product + default variant ---
        product_id = 'prod_lifecycle_001'
        variant_id = f'var_{product_id}_default'
        event_id = 'evt-presmeet-2025'

        # Parent product
        producten_table.put_item(Item={
            'product_id': product_id,
            'event_id': event_id,
            'name': 'Meeting Ticket',
            'price': Decimal('150'),
            'is_parent': True,
            'parent_id': None,
            'active': True,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
        })

        # Default variant with stock
        producten_table.put_item(Item={
            'product_id': variant_id,
            'parent_id': product_id,
            'event_id': event_id,
            'name': 'Default Variant',
            'is_parent': False,
            'variant_attributes': {},
            'price': None,
            'stock': Decimal('50'),
            'sold_count': Decimal('0'),
            'allow_oversell': False,
            'active': True,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
        })

        # --- Setup: Create an order ---
        order_id = 'ord_lifecycle_001'
        order = {
            'order_id': order_id,
            'event_id': event_id,
            'customer_name': 'Jan de Vries',
            'club_name': 'H-DCN Regio Noord',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('300'),
            'amount_paid': Decimal('0'),
            'items': [
                {
                    'product_id': product_id,
                    'variant_id': variant_id,
                    'name': 'Meeting Ticket',
                    'quantity': 2,
                    'unit_price': Decimal('150'),
                }
            ],
            'status_history': [],
            'created_at': '2024-06-01T10:00:00Z',
        }
        orders_table.put_item(Item=order)

        # --- Test transitions ---
        transitions = [
            ('draft', 'submitted'),
            ('submitted', 'locked'),
            ('locked', 'order_received'),
            ('order_received', 'paid'),
            ('paid', 'shipped'),
            ('shipped', 'delivered'),
            ('delivered', 'completed'),
        ]

        current_status = 'draft'
        status_history = []

        for from_status, to_status in transitions:
            # Validate transition is allowed
            assert is_valid_transition(from_status, to_status), (
                f"Transition {from_status} → {to_status} should be valid"
            )

            # If transitioning to 'paid', reserve stock
            if to_status == 'paid':
                order_items = [
                    {'variant_id': variant_id, 'quantity': 2}
                ]
                reserve_stock(
                    order_items, producten_table, movements_table,
                    order_id
                )

            # Record status transition
            status_history.append({
                'from_status': from_status,
                'to_status': to_status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'triggered_by': 'admin@h-dcn.nl',
            })

            # Update order status in DynamoDB
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression='SET #s = :status, status_history = :history',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': to_status,
                    ':history': status_history,
                },
            )

            current_status = to_status

        # --- Verify final state ---
        final_order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert final_order['status'] == 'completed'
        assert len(final_order['status_history']) == 7

        # Verify stock was decremented
        variant = producten_table.get_item(Key={'product_id': variant_id})['Item']
        assert variant['stock'] == Decimal('48')  # 50 - 2
        assert variant['sold_count'] == Decimal('2')  # 0 + 2

        # Verify sale movement was created
        response = movements_table.scan()
        sale_movements = [m for m in response['Items'] if m['type'] == 'sale']
        assert len(sale_movements) == 1
        assert sale_movements[0]['variant_id'] == variant_id
        assert sale_movements[0]['quantity'] == -2
        assert sale_movements[0]['order_id'] == order_id

    def test_unlock_transition(self, aws_env):
        """Test the special locked → submitted (unlock) backward transition."""
        assert is_valid_transition('locked', 'submitted') is True

    def test_invalid_backward_transition(self, aws_env):
        """Test that backward transitions (other than unlock) are rejected."""
        assert is_valid_transition('paid', 'submitted') is False
        assert is_valid_transition('shipped', 'locked') is False
        assert is_valid_transition('completed', 'draft') is False

    def test_payment_failed_is_terminal(self, aws_env):
        """Test that payment_failed is a terminal state with no exits."""
        assert is_valid_transition('payment_failed', 'paid') is False
        assert is_valid_transition('payment_failed', 'submitted') is False
        assert get_next_valid_states('payment_failed') == []


# ===========================================================================
# Task 22.3: Integration test for product CRUD
# ===========================================================================


class TestProductCRUD:
    """Test product creation, validation, variant generation, and Default_Variant logic."""

    def test_create_default_variant_creates_correct_record(self, aws_env):
        """Test that create_default_variant produces a well-formed record."""
        product_id = 'prod_test_001'

        variant = create_default_variant(product_id)

        assert variant['product_id'] == f'var_{product_id}_default'
        assert variant['parent_id'] == product_id
        assert variant['name'] == 'Default Variant'
        assert variant['is_parent'] is False
        assert variant['variant_attributes'] == {}
        assert variant['price'] is None
        assert variant['stock'] == 0
        assert variant['sold_count'] == 0
        assert variant['allow_oversell'] is False
        assert variant['active'] is True
        assert 'created_at' in variant
        assert 'updated_at' in variant

    def test_generate_variant_combinations_correct_count(self, aws_env):
        """Test that generate_variant_combinations produces the correct cartesian product."""
        required_attributes = {
            'type': 'object',
            'properties': {
                'gender': {'type': 'string', 'enum': ['male', 'female']},
                'size': {'type': 'string', 'enum': ['S', 'M', 'L', 'XL']},
            },
        }

        combos = generate_variant_combinations(required_attributes)

        # 2 genders × 4 sizes = 8 combinations
        assert len(combos) == 8

        # Each combination should have both attributes
        for combo in combos:
            assert 'gender' in combo
            assert 'size' in combo
            assert combo['gender'] in ['male', 'female']
            assert combo['size'] in ['S', 'M', 'L', 'XL']

        # All combinations should be unique
        combo_tuples = [tuple(sorted(c.items())) for c in combos]
        assert len(set(combo_tuples)) == 8

    def test_generate_variant_combinations_empty_schema(self, aws_env):
        """Test generate_variant_combinations with None/empty schema."""
        assert generate_variant_combinations(None) == []
        assert generate_variant_combinations({}) == []
        assert generate_variant_combinations({'properties': {}}) == []

    def test_should_remove_default_variant_logic(self, aws_env):
        """Test should_remove_default_variant returns True only when appropriate."""
        default_variant = [{'variant_attributes': {}}]
        real_variant = [{'variant_attributes': {'size': 'M'}}]
        mixed_existing = [
            {'variant_attributes': {}},
            {'variant_attributes': {'size': 'S'}},
        ]

        # Only default exists + adding real variants → remove
        assert should_remove_default_variant(default_variant, real_variant) is True

        # Only default exists + adding another default → don't remove
        assert should_remove_default_variant(default_variant, default_variant) is False

        # Mixed existing (has real variants already) + adding real → don't remove
        assert should_remove_default_variant(mixed_existing, real_variant) is False

        # Empty inputs → don't remove
        assert should_remove_default_variant([], real_variant) is False
        assert should_remove_default_variant(default_variant, []) is False

    def test_validate_product_accepts_valid_payloads(self, aws_env):
        """Test validate_product accepts well-formed payloads."""
        valid_payload = {
            'name': 'Test Product',
            'price': 25.0,
            'min_per_club': 1,
            'max_per_club': 5,
            'required_attributes': {
                'type': 'object',
                'properties': {
                    'size': {'type': 'string', 'enum': ['S', 'M', 'L']},
                },
            },
        }

        is_valid, errors = validate_product(valid_payload)
        assert is_valid is True
        assert errors == []

    def test_validate_product_rejects_invalid_min_max(self, aws_env):
        """Test validate_product rejects min_per_club > max_per_club."""
        invalid_payload = {
            'name': 'Bad Product',
            'min_per_club': 10,
            'max_per_club': 3,
        }

        is_valid, errors = validate_product(invalid_payload)
        assert is_valid is False
        assert any('min_per_club' in e for e in errors)

    def test_validate_product_rejects_invalid_schema(self, aws_env):
        """Test validate_product rejects malformed required_attributes."""
        invalid_payload = {
            'name': 'Bad Schema',
            'required_attributes': {'type': 'array'},  # wrong type
        }

        is_valid, errors = validate_product(invalid_payload)
        assert is_valid is False
        assert any('type' in e and 'object' in e for e in errors)

    def test_validate_variant_attributes_valid(self, aws_env):
        """Test validate_variant_attributes accepts conforming values."""
        parent_schema = {
            'type': 'object',
            'properties': {
                'gender': {'type': 'string', 'enum': ['male', 'female']},
                'size': {'type': 'string', 'enum': ['S', 'M', 'L']},
            },
        }

        is_valid, errors = validate_variant_attributes(
            {'gender': 'male', 'size': 'L'}, parent_schema
        )
        assert is_valid is True
        assert errors == []

    def test_validate_variant_attributes_invalid_value(self, aws_env):
        """Test validate_variant_attributes rejects values not in parent enums."""
        parent_schema = {
            'type': 'object',
            'properties': {
                'size': {'type': 'string', 'enum': ['S', 'M', 'L']},
            },
        }

        is_valid, errors = validate_variant_attributes(
            {'size': 'XL'}, parent_schema
        )
        assert is_valid is False
        assert any('XL' in e for e in errors)

    def test_validate_variant_attributes_missing_required(self, aws_env):
        """Test validate_variant_attributes rejects missing attributes."""
        parent_schema = {
            'type': 'object',
            'properties': {
                'gender': {'type': 'string', 'enum': ['male', 'female']},
                'size': {'type': 'string', 'enum': ['S', 'M', 'L']},
            },
        }

        # Only provide 'size', missing 'gender'
        is_valid, errors = validate_variant_attributes(
            {'size': 'M'}, parent_schema
        )
        assert is_valid is False
        assert any('gender' in e for e in errors)


# ===========================================================================
# Task 22.4: Integration test for manual payment recording
# ===========================================================================


class TestPaymentRecording:
    """Test payment aggregate computation and partial payment logic."""

    def test_compute_payment_aggregates_multiple_orders(self, aws_env):
        """Test compute_payment_aggregates with multiple orders."""
        orders = [
            {'total_amount': 300, 'amount_paid': 300},   # fully paid
            {'total_amount': 150, 'amount_paid': 75},    # partially paid
            {'total_amount': 500, 'amount_paid': 0},     # unpaid
        ]

        result = compute_payment_aggregates(orders)

        assert result['total_charged'] == 950
        assert result['total_paid'] == 375
        assert result['total_outstanding'] == 575

    def test_compute_payment_aggregates_empty_list(self, aws_env):
        """Test compute_payment_aggregates with empty order list."""
        result = compute_payment_aggregates([])

        assert result['total_charged'] == 0
        assert result['total_paid'] == 0
        assert result['total_outstanding'] == 0

    def test_partial_payment_updates_order_correctly(self, aws_env):
        """Test that recording a partial payment updates order amount_paid and payment_status."""
        orders_table = aws_env['orders_table']

        # Create an order with total_amount
        order_id = 'ord_payment_001'
        orders_table.put_item(Item={
            'order_id': order_id,
            'event_id': 'evt-presmeet-2025',
            'status': 'order_received',
            'total_amount': Decimal('500'),
            'amount_paid': Decimal('0'),
            'payment_status': 'unpaid',
        })

        # Record a partial payment (simulate what admin_record_payment does)
        payment_amount = Decimal('200')
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET amount_paid = amount_paid + :amt, payment_status = :ps',
            ExpressionAttributeValues={
                ':amt': payment_amount,
                ':ps': 'partial',
            },
        )

        # Verify
        updated_order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert updated_order['amount_paid'] == Decimal('200')
        assert updated_order['payment_status'] == 'partial'

        # Record another payment to fully pay
        remaining = Decimal('300')
        new_total_paid = updated_order['amount_paid'] + remaining
        new_status = 'paid' if new_total_paid >= updated_order['total_amount'] else 'partial'

        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET amount_paid = amount_paid + :amt, payment_status = :ps',
            ExpressionAttributeValues={
                ':amt': remaining,
                ':ps': new_status,
            },
        )

        final_order = orders_table.get_item(Key={'order_id': order_id})['Item']
        assert final_order['amount_paid'] == Decimal('500')
        assert final_order['payment_status'] == 'paid'

    def test_aggregate_with_real_dynamo_orders(self, aws_env):
        """Test compute_payment_aggregates using orders fetched from mocked DynamoDB."""
        orders_table = aws_env['orders_table']

        # Seed orders
        test_orders = [
            {'order_id': 'agg_001', 'event_id': 'evt-presmeet-2025', 'total_amount': Decimal('100'), 'amount_paid': Decimal('100'), 'status': 'paid'},
            {'order_id': 'agg_002', 'event_id': 'evt-presmeet-2025', 'total_amount': Decimal('200'), 'amount_paid': Decimal('50'), 'status': 'order_received'},
            {'order_id': 'agg_003', 'event_id': 'evt-presmeet-2025', 'total_amount': Decimal('300'), 'amount_paid': Decimal('0'), 'status': 'submitted'},
        ]
        for order in test_orders:
            orders_table.put_item(Item=order)

        # Scan and compute aggregates (simulating what admin_get_payments does)
        response = orders_table.scan()
        all_orders = response['Items']

        # Convert Decimal to float for compute_payment_aggregates
        orders_for_aggregation = [
            {'total_amount': float(o['total_amount']), 'amount_paid': float(o['amount_paid'])}
            for o in all_orders
        ]

        result = compute_payment_aggregates(orders_for_aggregation)

        assert result['total_charged'] == 600.0
        assert result['total_paid'] == 150.0
        assert result['total_outstanding'] == 450.0


# ===========================================================================
# Task 22.5: Integration test for report generation and export
# ===========================================================================


class TestReportGeneration:
    """Test stock movement creation and report data via mocked tables."""

    def test_reserve_stock_creates_sale_movements(self, aws_env):
        """Test that reserve_stock creates sale movement records in StockMovements table."""
        producten_table = aws_env['producten_table']
        movements_table = aws_env['movements_table']

        # Create a variant
        variant_id = 'var_report_test_001'
        producten_table.put_item(Item={
            'product_id': variant_id,
            'parent_id': 'prod_report_001',
            'event_id': None,
            'is_parent': False,
            'stock': Decimal('100'),
            'sold_count': Decimal('0'),
            'active': True,
        })

        # Reserve stock (simulates order → paid transition)
        order_items = [{'variant_id': variant_id, 'quantity': 5}]
        reserve_stock(order_items, producten_table, movements_table, 'ord_rpt_001')

        # Verify movement was created
        response = movements_table.scan()
        movements = response['Items']
        assert len(movements) == 1

        mov = movements[0]
        assert mov['variant_id'] == variant_id
        assert mov['type'] == 'sale'
        assert mov['quantity'] == -5
        assert mov['order_id'] == 'ord_rpt_001'
        assert mov['recorded_by'] == 'system'
        assert 'created_at' in mov

        # Verify variant stock was decremented
        variant = producten_table.get_item(Key={'product_id': variant_id})['Item']
        assert variant['stock'] == Decimal('95')
        assert variant['sold_count'] == Decimal('5')

    def test_create_inbound_movement_writes_to_table(self, aws_env):
        """Test that create_inbound_movement writes correct record to StockMovements table."""
        movements_table = aws_env['movements_table']

        # Use Decimal for DynamoDB compatibility (boto3 rejects floats)
        movement = create_inbound_movement(
            variant_id='var_inbound_001',
            quantity=25,
            purchase_price_per_unit=Decimal('8.50'),
            supplier_name='Textile BV',
            recorded_by='admin@h-dcn.nl',
            reference='PO-2024-001',
            movements_table=movements_table,
        )

        # Verify returned record
        assert movement['variant_id'] == 'var_inbound_001'
        assert movement['type'] == 'inbound'
        assert movement['quantity'] == 25
        assert movement['purchase_price_per_unit'] == Decimal('8.50')
        assert movement['total_cost'] == Decimal('212.50')  # 25 × 8.50
        assert movement['supplier_name'] == 'Textile BV'
        assert movement['recorded_by'] == 'admin@h-dcn.nl'
        assert movement['reference'] == 'PO-2024-001'
        assert movement['order_id'] is None
        assert 'created_at' in movement
        assert movement['movement_id'].startswith('mov_')

        # Verify it was persisted in DynamoDB
        response = movements_table.scan()
        assert len(response['Items']) == 1
        stored = response['Items'][0]
        assert stored['movement_id'] == movement['movement_id']

    def test_report_snapshot_to_s3(self, aws_env):
        """Test writing and reading a report snapshot from S3."""
        s3 = aws_env['s3']
        orders_table = aws_env['orders_table']
        movements_table = aws_env['movements_table']

        # Seed some orders
        orders_table.put_item(Item={
            'order_id': 'rpt_ord_001',
            'event_id': 'evt-presmeet-2025',
            'status': 'paid',
            'total_amount': Decimal('300'),
            'amount_paid': Decimal('300'),
        })
        orders_table.put_item(Item={
            'order_id': 'rpt_ord_002',
            'event_id': 'evt-presmeet-2025',
            'status': 'submitted',
            'total_amount': Decimal('150'),
            'amount_paid': Decimal('0'),
        })

        # Seed stock movements
        movements_table.put_item(Item={
            'movement_id': 'mov_rpt_001',
            'variant_id': 'var_rpt_v1',
            'event_id': 'evt-presmeet-2025',
            'type': 'inbound',
            'quantity': 50,
            'purchase_price_per_unit': Decimal('10'),
            'total_cost': Decimal('500'),
            'supplier_name': 'Supplier A',
            'recorded_by': 'admin@h-dcn.nl',
            'created_at': '2024-06-01T10:00:00Z',
        })

        # Generate report snapshot (simulates admin_generate_report logic)
        orders_response = orders_table.scan()
        all_orders = orders_response['Items']
        movements_response = movements_table.scan()
        all_movements = movements_response['Items']

        # Build report data
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_orders': len(all_orders),
                'total_revenue': float(sum(o.get('total_amount', 0) for o in all_orders)),
                'total_paid': float(sum(o.get('amount_paid', 0) for o in all_orders)),
                'total_outstanding': float(
                    sum(o.get('total_amount', 0) for o in all_orders)
                    - sum(o.get('amount_paid', 0) for o in all_orders)
                ),
                'total_inbound_cost': float(
                    sum(m.get('total_cost', 0) for m in all_movements if m.get('type') == 'inbound')
                ),
            },
        }

        # Write to S3
        s3.put_object(
            Bucket='h-dcn-webshop-reports',
            Key='reports/latest.json',
            Body=json.dumps(report, default=str),
            ContentType='application/json',
        )

        # Read back from S3
        response = s3.get_object(
            Bucket='h-dcn-webshop-reports',
            Key='reports/latest.json',
        )
        stored_report = json.loads(response['Body'].read().decode('utf-8'))

        assert stored_report['summary']['total_orders'] == 2
        assert stored_report['summary']['total_revenue'] == 450.0
        assert stored_report['summary']['total_paid'] == 300.0
        assert stored_report['summary']['total_outstanding'] == 150.0
        assert stored_report['summary']['total_inbound_cost'] == 500.0

    def test_report_export_csv_format(self, aws_env):
        """Test generating a CSV export from report data."""
        import csv
        import io

        orders_table = aws_env['orders_table']

        # Seed orders with items
        orders_table.put_item(Item={
            'order_id': 'csv_ord_001',
            'event_id': None,
            'customer_name': 'Test Customer',
            'status': 'paid',
            'total_amount': Decimal('50'),
            'amount_paid': Decimal('50'),
            'items': [
                {
                    'product_id': 'prod_csv_001',
                    'variant_id': 'var_csv_001',
                    'name': 'H-DCN Pin Badge',
                    'quantity': 10,
                    'unit_price': Decimal('5'),
                }
            ],
        })

        # Scan and build CSV (simulates admin_export_report logic)
        response = orders_table.scan()
        orders = [o for o in response['Items'] if not o.get('event_id')]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['order_id', 'customer_name', 'status', 'product_name', 'quantity', 'unit_price', 'total_amount'])

        for order in orders:
            for item in order.get('items', []):
                writer.writerow([
                    order['order_id'],
                    order.get('customer_name', ''),
                    order['status'],
                    item['name'],
                    item['quantity'],
                    float(item['unit_price']),
                    float(order['total_amount']),
                ])

        csv_content = output.getvalue()
        lines = csv_content.strip().split('\n')

        # Header + 1 data row
        assert len(lines) == 2
        assert 'order_id' in lines[0]
        assert 'csv_ord_001' in lines[1]
        assert 'H-DCN Pin Badge' in lines[1]

    def test_multiple_sale_movements_from_multi_item_order(self, aws_env):
        """Test that reserve_stock handles multiple line items correctly."""
        producten_table = aws_env['producten_table']
        movements_table = aws_env['movements_table']

        # Create two variants
        for i, vid in enumerate(['var_multi_001', 'var_multi_002']):
            producten_table.put_item(Item={
                'product_id': vid,
                'parent_id': f'prod_multi_{i}',
                'event_id': 'evt-presmeet-2025',
                'is_parent': False,
                'stock': Decimal('30'),
                'sold_count': Decimal('0'),
                'active': True,
            })

        # Reserve stock for multi-item order
        order_items = [
            {'variant_id': 'var_multi_001', 'quantity': 3},
            {'variant_id': 'var_multi_002', 'quantity': 7},
        ]
        reserve_stock(order_items, producten_table, movements_table, 'ord_multi_001')

        # Verify both movements created
        response = movements_table.scan()
        movements = response['Items']
        assert len(movements) == 2

        # Verify each variant's stock
        v1 = producten_table.get_item(Key={'product_id': 'var_multi_001'})['Item']
        v2 = producten_table.get_item(Key={'product_id': 'var_multi_002'})['Item']
        assert v1['stock'] == Decimal('27')  # 30 - 3
        assert v1['sold_count'] == Decimal('3')
        assert v2['stock'] == Decimal('23')  # 30 - 7
        assert v2['sold_count'] == Decimal('7')
