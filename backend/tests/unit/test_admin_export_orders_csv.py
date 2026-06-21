"""
Unit tests for admin_export_orders_csv handler.

Tests CSV export of all orders for a given event_id, including:
- Order items with product names, variants, quantities, prices
- Delegate info (name, email)
- Person names from item_fields_data
- Order status, payment status, order total

Requirements: 14.6
"""

import os
import sys
import csv
import io
import json
import base64
import importlib.util
from decimal import Decimal
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws

# Set environment before loading handler
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_export_orders_csv', 'app.py')
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


def _auth_patches():
    """Patch auth functions for admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD', 'System_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _create_tables(dynamodb):
    """Create Orders and Producten tables for testing."""
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

    return orders_table, producten_table


def _make_event(event_id: str) -> dict:
    """Build an API Gateway event for GET /admin/events/{event_id}/export-csv."""
    return {
        'httpMethod': 'GET',
        'pathParameters': {'event_id': event_id},
        'queryStringParameters': None,
        'headers': {'Authorization': 'Bearer test-token'},
        'requestContext': {},
    }


def _parse_csv_response(response: dict) -> list[dict]:
    """Parse CSV from base64-encoded response body."""
    assert response['isBase64Encoded'] is True
    csv_bytes = base64.b64decode(response['body'])
    csv_text = csv_bytes.decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)


class TestAdminExportOrdersCsv:
    """Tests for admin CSV export endpoint."""

    def test_empty_event_returns_csv_headers_only(self):
        """An event with no orders returns a CSV with headers only."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-empty'), None)

        assert response['statusCode'] == 200
        assert 'text/csv' in response['headers']['Content-Type']
        assert response['isBase64Encoded'] is True

        rows = _parse_csv_response(response)
        assert len(rows) == 0

    def test_export_with_order_items(self):
        """Orders with items produce correct CSV rows with product names."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            orders_table, producten_table = _create_tables(dynamodb)

            # Add a product
            producten_table.put_item(Item={
                'product_id': 'prod-1',
                'name': 'Dinner Ticket',
            })

            # Add an order with items
            orders_table.put_item(Item={
                'order_id': 'ord-001',
                'event_id': 'evt-test',
                'club_id': 'club-1',
                'club_name': 'HD Amsterdam',
                'status': 'submitted',
                'payment_status': 'unpaid',
                'total_amount': Decimal('150.00'),
                'delegates': {
                    'primary': 'jan@club.nl',
                    'primary_name': 'Jan de Vries',
                },
                'items': [
                    {
                        'product_id': 'prod-1',
                        'variant_id': '',
                        'quantity': Decimal('1'),
                        'unit_price': Decimal('75.00'),
                        'line_total': Decimal('75.00'),
                        'item_fields_data': {'name': 'Alice'},
                    },
                    {
                        'product_id': 'prod-1',
                        'variant_id': '',
                        'quantity': Decimal('1'),
                        'unit_price': Decimal('75.00'),
                        'line_total': Decimal('75.00'),
                        'item_fields_data': {'name': 'Bob'},
                    },
                ],
            })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-test'), None)

        assert response['statusCode'] == 200
        rows = _parse_csv_response(response)
        assert len(rows) == 2

        # First row
        assert rows[0]['order_id'] == 'ord-001'
        assert rows[0]['club_name'] == 'HD Amsterdam'
        assert rows[0]['delegate_name'] == 'Jan de Vries'
        assert rows[0]['delegate_email'] == 'jan@club.nl'
        assert rows[0]['person_name'] == 'Alice'
        assert rows[0]['product_name'] == 'Dinner Ticket'
        assert rows[0]['quantity'] == '1'
        assert rows[0]['unit_price'] == '75.00'
        assert rows[0]['line_total'] == '75.00'
        assert rows[0]['order_status'] == 'submitted'
        assert rows[0]['payment_status'] == 'unpaid'
        assert rows[0]['order_total'] == '150.00'

        # Second row
        assert rows[1]['person_name'] == 'Bob'

    def test_export_with_variants(self):
        """Order items with variants show variant info in CSV."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            orders_table, producten_table = _create_tables(dynamodb)

            producten_table.put_item(Item={
                'product_id': 'prod-shirt',
                'name': 'Event T-Shirt',
            })

            orders_table.put_item(Item={
                'order_id': 'ord-002',
                'event_id': 'evt-test',
                'club_id': 'club-2',
                'club_name': 'HD Rotterdam',
                'status': 'draft',
                'payment_status': 'unpaid',
                'total_amount': Decimal('45.00'),
                'delegates': {
                    'primary': 'kees@club.nl',
                    'primary_name': 'Kees Bakker',
                },
                'items': [
                    {
                        'product_id': 'prod-shirt',
                        'variant_id': 'size-xl',
                        'variant_label': 'XL',
                        'quantity': Decimal('1'),
                        'unit_price': Decimal('45.00'),
                        'line_total': Decimal('45.00'),
                        'item_fields_data': {'name': 'Kees Bakker'},
                    },
                ],
            })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-test'), None)

        assert response['statusCode'] == 200
        rows = _parse_csv_response(response)
        assert len(rows) == 1
        assert rows[0]['variant'] == 'XL'
        assert rows[0]['product_name'] == 'Event T-Shirt'

    def test_export_order_with_no_items(self):
        """An order with no items still appears in the export."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            orders_table, producten_table = _create_tables(dynamodb)

            orders_table.put_item(Item={
                'order_id': 'ord-003',
                'event_id': 'evt-test',
                'club_id': 'club-3',
                'club_name': 'HD Utrecht',
                'status': 'draft',
                'payment_status': 'unpaid',
                'total_amount': Decimal('0'),
                'delegates': {
                    'primary': 'pieter@club.nl',
                    'primary_name': 'Pieter Smit',
                },
                'items': [],
            })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-test'), None)

        assert response['statusCode'] == 200
        rows = _parse_csv_response(response)
        assert len(rows) == 1
        assert rows[0]['order_id'] == 'ord-003'
        assert rows[0]['club_name'] == 'HD Utrecht'
        assert rows[0]['delegate_name'] == 'Pieter Smit'
        assert rows[0]['product_name'] == ''
        assert rows[0]['person_name'] == ''

    def test_only_exports_orders_for_specified_event(self):
        """Only orders matching the event_id in the path are exported."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            orders_table, producten_table = _create_tables(dynamodb)

            # Order for target event
            orders_table.put_item(Item={
                'order_id': 'ord-target',
                'event_id': 'evt-target',
                'club_id': 'club-1',
                'club_name': 'Target Club',
                'status': 'submitted',
                'payment_status': 'paid',
                'total_amount': Decimal('100.00'),
                'delegates': {'primary': 'a@b.nl', 'primary_name': 'A'},
                'items': [],
            })

            # Order for different event
            orders_table.put_item(Item={
                'order_id': 'ord-other',
                'event_id': 'evt-other',
                'club_id': 'club-2',
                'club_name': 'Other Club',
                'status': 'submitted',
                'payment_status': 'paid',
                'total_amount': Decimal('200.00'),
                'delegates': {'primary': 'x@y.nl', 'primary_name': 'X'},
                'items': [],
            })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-target'), None)

        assert response['statusCode'] == 200
        rows = _parse_csv_response(response)
        assert len(rows) == 1
        assert rows[0]['order_id'] == 'ord-target'

    def test_missing_event_id_returns_400(self):
        """Missing event_id in path returns 400 error."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            handler_module = _load_handler()

            event = {
                'httpMethod': 'GET',
                'pathParameters': {},
                'queryStringParameters': None,
                'headers': {'Authorization': 'Bearer test-token'},
                'requestContext': {},
            }

            with _auth_patches():
                response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 400

    def test_unauthorized_access_returns_error(self):
        """Non-admin users get permission denied."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            handler_module = _load_handler()

            with patch.multiple(
                'app',
                extract_user_credentials=lambda event: ('user@club.nl', ['event_participant'], None),
                validate_permissions_with_regions=lambda roles, perms, email, region: (
                    False,
                    {'statusCode': 403, 'body': json.dumps({'error': 'Forbidden'})},
                    {},
                ),
                log_successful_access=lambda *a, **kw: None,
            ):
                response = handler_module.lambda_handler(_make_event('evt-test'), None)

        assert response['statusCode'] == 403

    def test_csv_content_disposition_header(self):
        """Response includes Content-Disposition header with filename."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-123'), None)

        assert response['statusCode'] == 200
        assert 'orders_export_evt-123.csv' in response['headers']['Content-Disposition']

    def test_options_request(self):
        """OPTIONS request returns CORS preflight response."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            handler_module = _load_handler()

            event = {
                'httpMethod': 'OPTIONS',
                'pathParameters': {'event_id': 'evt-test'},
                'headers': {},
                'requestContext': {},
            }

            response = handler_module.lambda_handler(event, None)

        assert response['statusCode'] == 200

    def test_multiple_orders_multiple_products(self):
        """Multiple orders with multiple products produce correct row count."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            orders_table, producten_table = _create_tables(dynamodb)

            producten_table.put_item(Item={'product_id': 'p1', 'name': 'Product A'})
            producten_table.put_item(Item={'product_id': 'p2', 'name': 'Product B'})

            # Order 1: 2 items
            orders_table.put_item(Item={
                'order_id': 'ord-a',
                'event_id': 'evt-multi',
                'club_id': 'c1',
                'club_name': 'Club 1',
                'status': 'submitted',
                'payment_status': 'paid',
                'total_amount': Decimal('200.00'),
                'delegates': {'primary': 'a@b.nl', 'primary_name': 'Person A'},
                'items': [
                    {'product_id': 'p1', 'quantity': Decimal('1'), 'unit_price': Decimal('100.00'), 'line_total': Decimal('100.00'), 'item_fields_data': {'name': 'Guest 1'}},
                    {'product_id': 'p2', 'quantity': Decimal('1'), 'unit_price': Decimal('100.00'), 'line_total': Decimal('100.00'), 'item_fields_data': {'name': 'Guest 2'}},
                ],
            })

            # Order 2: 1 item
            orders_table.put_item(Item={
                'order_id': 'ord-b',
                'event_id': 'evt-multi',
                'club_id': 'c2',
                'club_name': 'Club 2',
                'status': 'locked',
                'payment_status': 'partial',
                'total_amount': Decimal('50.00'),
                'delegates': {'primary': 'c@d.nl', 'primary_name': 'Person C'},
                'items': [
                    {'product_id': 'p1', 'quantity': Decimal('1'), 'unit_price': Decimal('50.00'), 'line_total': Decimal('50.00'), 'item_fields_data': {'name': 'Guest 3'}},
                ],
            })

            handler_module = _load_handler()

            with _auth_patches():
                response = handler_module.lambda_handler(_make_event('evt-multi'), None)

        assert response['statusCode'] == 200
        rows = _parse_csv_response(response)
        assert len(rows) == 3  # 2 items from order 1 + 1 item from order 2

        # Verify product names resolved
        product_names_in_csv = {r['product_name'] for r in rows}
        assert 'Product A' in product_names_in_csv
        assert 'Product B' in product_names_in_csv
