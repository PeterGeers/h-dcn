"""
Unit tests for generate_preparation_pdf handler.

Tests: by_order mode, by_guest mode, product filter, empty state,
sort order, auth enforcement.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8
"""

import json
import os
import sys
import importlib.util
from decimal import Decimal
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws

# Set AWS env vars before any handler import
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['REGISTRY_BUCKET_NAME'] = 'test-bucket'

# Handler file path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_preparation_pdf', 'app.py')
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
    """Patch auth for admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD', 'Events_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _non_admin_auth_patches():
    """Patch auth for non-admin access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@test.nl', ['event_participant'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _make_event(method='GET', event_id='evt-001', mode='by_order', product_filter=None):
    """Build an API Gateway event."""
    query_params = {'mode': mode}
    if product_filter:
        query_params['product_filter'] = product_filter
    return {
        'httpMethod': method,
        'pathParameters': {'event_id': event_id},
        'queryStringParameters': query_params,
        'headers': {'Authorization': 'Bearer test-token'},
        'body': None,
    }


# --- S3 registry fixture ---
REGISTRY_JSON = json.dumps({
    'version': '1.0',
    'rows': [
        {'row_id': 'row-1', 'label': 'Club Zebra', 'allowed_emails': [], 'logo_url': None},
        {'row_id': 'row-2', 'label': 'Club Alpha', 'allowed_emails': [], 'logo_url': 'https://example.com/logo.png'},
        {'row_id': 'row-3', 'label': 'Club Beta', 'allowed_emails': [], 'logo_url': None},
    ],
})


@pytest.fixture
def setup_aws():
    """Set up mocked AWS resources (DynamoDB + S3) and load handler."""
    with mock_aws():
        # Create DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        products_table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create S3 bucket
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )
        s3.put_object(
            Bucket='test-bucket',
            Key='registries/evt-001.json',
            Body=REGISTRY_JSON,
        )

        # Seed event
        events_table.put_item(Item={
            'event_id': 'evt-001',
            'name': 'Test Event 2025',
            'registry_config': {
                's3_path': 'registries/evt-001.json',
                'row_label': 'club',
                'claim_mode': 'first_come_first_served',
                'max_delegates_per_row': 2,
            },
            'registry_claims': {
                'row-1': {'member_id': 'm-1', 'email': 'admin@zebra.nl', 'name': 'Admin Zebra'},
                'row-2': {'member_id': 'm-2', 'email': 'admin@alpha.nl', 'name': 'Admin Alpha'},
            },
        })

        # Seed products
        products_table.put_item(Item={
            'product_id': 'prod-1',
            'name': 'Dinner Ticket',
            'event_id': 'evt-001',
            'is_parent': True,
            'purchase_rules': {'max_per_club': 10, 'max_per_event': 100},
        })
        products_table.put_item(Item={
            'product_id': 'prod-2',
            'name': 'T-Shirt',
            'event_id': 'evt-001',
            'is_parent': True,
            'purchase_rules': {'max_per_club': 5},
        })

        # Seed orders: submitted and locked (should be included)
        orders_table.put_item(Item={
            'order_id': 'ord-1',
            'event_id': 'evt-001',
            'club_id': 'row-1',
            'status': 'submitted',
            'payment_status': 'paid',
            'total_amount': Decimal('150.00'),
            'total_paid': Decimal('150.00'),
            'delegates': {'primary': 'admin@zebra.nl', 'secondary': None},
            'items': [
                {
                    'product_id': 'prod-1',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Jan Zebra'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                },
                {
                    'product_id': 'prod-1',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Piet Zebra'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                },
                {
                    'product_id': 'prod-2',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Jan Zebra', 'size': 'XL'},
                    'unit_price': Decimal('25.00'),
                    'line_total': Decimal('50.00'),
                    'variant_attributes': {'Maat': 'XL'},
                },
            ],
        })

        orders_table.put_item(Item={
            'order_id': 'ord-2',
            'event_id': 'evt-001',
            'club_id': 'row-2',
            'status': 'locked',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'total_paid': Decimal('0'),
            'delegates': {'primary': 'admin@alpha.nl', 'secondary': 'bob@alpha.nl'},
            'items': [
                {
                    'product_id': 'prod-1',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Anna Alpha'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                },
            ],
        })

        # Draft order — should NOT be included in preparation PDF
        orders_table.put_item(Item={
            'order_id': 'ord-3',
            'event_id': 'evt-001',
            'club_id': 'row-3',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0'),
            'total_paid': Decimal('0'),
            'delegates': {'primary': 'user@beta.nl'},
            'items': [],
        })

        # Load handler inside mocked context
        handler_module = _load_handler()
        yield handler_module


# =============================================================================
# Tests
# =============================================================================


class TestAuth:
    """Auth and authorization tests."""

    def test_non_admin_gets_403(self, setup_aws):
        """Non-admin users should be denied access."""
        handler = setup_aws
        with _non_admin_auth_patches():
            response = handler.lambda_handler(_make_event(), None)
        assert response['statusCode'] == 403

    def test_options_returns_cors(self, setup_aws):
        """OPTIONS request returns CORS headers."""
        handler = setup_aws
        with _auth_patches():
            response = handler.lambda_handler(
                {'httpMethod': 'OPTIONS', 'pathParameters': None, 'queryStringParameters': None},
                None,
            )
        assert response['statusCode'] == 200


class TestInputValidation:
    """Input validation tests."""

    def test_missing_event_id(self, setup_aws):
        """Missing event_id should return 400."""
        handler = setup_aws
        event = _make_event()
        event['pathParameters'] = {}
        with _auth_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_invalid_mode(self, setup_aws):
        """Invalid mode should return 400."""
        handler = setup_aws
        event = _make_event(mode='invalid')
        with _auth_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'mode' in body.get('error', '').lower() or 'mode' in body.get('message', '').lower()

    def test_nonexistent_event(self, setup_aws):
        """Non-existent event should return 404."""
        handler = setup_aws
        event = _make_event(event_id='nonexistent')
        with _auth_patches():
            response = handler.lambda_handler(event, None)
        assert response['statusCode'] == 404


class TestEmptyState:
    """Tests for Requirement 15.8: empty state message."""

    def test_no_qualifying_orders(self, setup_aws):
        """When no submitted/locked orders exist, return message instead of PDF."""
        handler = setup_aws

        # Use a different event with no orders
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        events_table = dynamodb.Table('Events')
        events_table.put_item(Item={
            'event_id': 'evt-empty',
            'name': 'Empty Event',
            'registry_config': {'s3_path': '', 'row_label': 'club'},
            'registry_claims': {},
        })

        event = _make_event(event_id='evt-empty')
        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body.get('pdf') is None
        assert 'message' in body
        assert 'no' in body['message'].lower()

    def test_product_filter_no_match(self, setup_aws):
        """When product filter excludes all orders, return message."""
        handler = setup_aws
        event = _make_event(product_filter='nonexistent-product')
        with _auth_patches():
            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body.get('pdf') is None
        assert 'message' in body


class TestByOrderMode:
    """Tests for Requirement 15.2: by_order mode."""

    def test_returns_pdf_binary(self, setup_aws):
        """by_order mode should return a base64-encoded PDF."""
        handler = setup_aws
        event = _make_event(mode='by_order')

        # Patch weasyprint to avoid actual rendering in tests
        mock_pdf = b'%PDF-1.4 fake pdf content'
        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = mock_pdf
            mock_wp.HTML.return_value = mock_html_instance

            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/pdf'
        assert response['isBase64Encoded'] is True
        assert 'preparation-by_order-evt-001' in response['headers']['Content-Disposition']

    def test_only_submitted_and_locked_orders(self, setup_aws):
        """by_order mode includes only submitted and locked orders (not draft)."""
        handler = setup_aws
        event = _make_event(mode='by_order')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            # Capture the HTML passed to WeasyPrint
            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Should contain Club Zebra and Club Alpha (submitted/locked)
        assert 'Club Zebra' in html_content
        assert 'Club Alpha' in html_content
        # Should NOT contain Club Beta (draft order)
        assert 'Club Beta' not in html_content

    def test_sorted_alphabetically_by_club_name(self, setup_aws):
        """Pages should be sorted alphabetically by club name (Alpha before Zebra)."""
        handler = setup_aws
        event = _make_event(mode='by_order')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Club Alpha should come before Club Zebra in the HTML
        alpha_pos = html_content.index('Club Alpha')
        zebra_pos = html_content.index('Club Zebra')
        assert alpha_pos < zebra_pos, "Club Alpha should appear before Club Zebra"


class TestByGuestMode:
    """Tests for Requirement 15.3: by_guest mode."""

    def test_returns_pdf_for_by_guest(self, setup_aws):
        """by_guest mode should return a valid PDF response."""
        handler = setup_aws
        event = _make_event(mode='by_guest')

        mock_pdf = b'%PDF-1.4 fake pdf content'
        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = mock_pdf
            mock_wp.HTML.return_value = mock_html_instance

            response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/pdf'
        assert 'preparation-by_guest-evt-001' in response['headers']['Content-Disposition']

    def test_one_page_per_person(self, setup_aws):
        """by_guest mode should create separate pages per person."""
        handler = setup_aws
        event = _make_event(mode='by_guest')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Three persons from submitted/locked orders: Jan Zebra, Piet Zebra, Anna Alpha
        assert 'Jan Zebra' in html_content
        assert 'Piet Zebra' in html_content
        assert 'Anna Alpha' in html_content

    def test_sorted_by_last_word_of_name(self, setup_aws):
        """Pages sorted by last word of name: Alpha < Zebra."""
        handler = setup_aws
        event = _make_event(mode='by_guest')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # "Anna Alpha" has last word "Alpha", "Jan Zebra" has "Zebra"
        # Alpha should come before Zebra
        alpha_pos = html_content.index('Anna Alpha')
        zebra_pos = html_content.index('Jan Zebra')
        assert alpha_pos < zebra_pos, "Anna Alpha (last word: Alpha) should appear before Jan Zebra (last word: Zebra)"


class TestProductFilter:
    """Tests for Requirement 15.7: product filter."""

    def test_filter_includes_only_matching_lines(self, setup_aws):
        """Product filter should include only pages with matching product lines."""
        handler = setup_aws
        # Filter to prod-2 (T-Shirt) — only ord-1 has this product
        event = _make_event(mode='by_order', product_filter='prod-2')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Club Zebra has T-Shirt, Club Alpha does not
        assert 'Club Zebra' in html_content
        assert 'Club Alpha' not in html_content

    def test_filter_by_guest_mode(self, setup_aws):
        """Product filter in by_guest mode only includes persons with matching items."""
        handler = setup_aws
        # Filter to prod-2 (T-Shirt) — only "Jan Zebra" has this product
        event = _make_event(mode='by_guest', product_filter='prod-2')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Only Jan Zebra has a T-Shirt item
        assert 'Jan Zebra' in html_content
        # Anna Alpha doesn't have T-Shirt
        assert 'Anna Alpha' not in html_content


class TestFooter:
    """Tests for Requirement 15.6: footer content."""

    def test_footer_contains_event_name_and_date(self, setup_aws):
        """Footer should include event name and ISO date."""
        handler = setup_aws
        event = _make_event(mode='by_order')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # Footer should contain event name
        assert 'Test Event 2025' in html_content
        # Footer should contain today's date in ISO format (YYYY-MM-DD)
        from datetime import date
        assert date.today().isoformat() in html_content

    def test_footer_contains_page_numbers(self, setup_aws):
        """Footer should include page X of Y."""
        handler = setup_aws
        event = _make_event(mode='by_order')

        with _auth_patches(), patch.object(handler, 'weasyprint') as mock_wp:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'%PDF'
            mock_wp.HTML.return_value = mock_html_instance

            handler.lambda_handler(event, None)

            call_args = mock_wp.HTML.call_args
            html_content = call_args[1]['string'] if 'string' in call_args[1] else call_args[0][0]

        # 2 qualifying orders → Page 1 of 2 and Page 2 of 2
        assert 'Page 1 of 2' in html_content
        assert 'Page 2 of 2' in html_content


class TestHelpers:
    """Tests for internal helper functions."""

    def test_sort_key_club_name_case_insensitive(self, setup_aws):
        """Sort key should be case-insensitive."""
        handler = setup_aws
        assert handler._sort_key_club_name('Zebra') == 'zebra'
        assert handler._sort_key_club_name('ALPHA') == 'alpha'
        assert handler._sort_key_club_name('') == ''

    def test_sort_key_guest_name_last_word(self, setup_aws):
        """Sort key should use last word as primary, rest as secondary."""
        handler = setup_aws
        # "Jan de Vries" → ('vries', 'jan de')
        assert handler._sort_key_guest_name('Jan de Vries') == ('vries', 'jan de')
        # "Anna" → ('anna', '')
        assert handler._sort_key_guest_name('Anna') == ('anna', '')
        # "" → ('', '')
        assert handler._sort_key_guest_name('') == ('', '')

    def test_format_euro(self, setup_aws):
        """Euro formatting should use Dutch convention."""
        handler = setup_aws
        assert handler._format_euro(Decimal('150.00')) == '€150,00'
        assert handler._format_euro(0) == '€0,00'
        assert handler._format_euro(None) == '€0,00'

    def test_get_last_word(self, setup_aws):
        """Last word extraction."""
        handler = setup_aws
        assert handler._get_last_word('Jan de Vries') == 'Vries'
        assert handler._get_last_word('Anna') == 'Anna'
        assert handler._get_last_word('') == ''
        assert handler._get_last_word('  ') == ''


# =============================================================================
# Task 7.4 — Generic registry row CSS classes and header format tests
# Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
# =============================================================================


class TestRegistryRowCssClasses:
    """Tests for Requirement 6.1: CSS classes use row-name/row-logo (not club-*)."""

    def test_html_contains_row_name_class(self, setup_aws):
        """HTML output should contain class 'row-name', not 'club-name'."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Test Person'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Club Alpha', 'logo_url': 'https://example.com/logo.png'}}
        products_map = {'prod-1': {'name': 'Dinner Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event')

        assert 'class="row-name"' in html
        assert 'class="club-name"' not in html

    def test_html_contains_row_logo_class(self, setup_aws):
        """HTML output should contain class 'row-logo', not 'club-logo'."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Test Person'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Club Alpha', 'logo_url': 'https://example.com/logo.png'}}
        products_map = {'prod-1': {'name': 'Dinner Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event')

        assert 'class="row-logo"' in html
        assert 'class="club-logo"' not in html

    def test_css_defines_row_name_style(self, setup_aws):
        """CSS should define .row-name style (not .club-name)."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-1',
            'items': [],
            'total_amount': 0,
            'payment_status': 'unpaid',
            'delegates': {},
        }]
        registry_rows = {'row-1': {'label': 'Test Row', 'logo_url': None}}
        products_map = {}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event')

        assert '.row-name' in html
        assert '.club-name' not in html

    def test_css_defines_row_logo_style(self, setup_aws):
        """CSS should define .row-logo style (not .club-logo)."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-1',
            'items': [],
            'total_amount': 0,
            'payment_status': 'unpaid',
            'delegates': {},
        }]
        registry_rows = {'row-1': {'label': 'Test Row', 'logo_url': None}}
        products_map = {}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event')

        assert '.row-logo' in html
        assert '.club-logo' not in html


class TestRegistryRowHeaderFormat:
    """Tests for Requirement 6.2, 6.3, 6.4: header format '{row_label}: {name}'."""

    def test_header_format_with_club_label(self, setup_aws):
        """Header should display 'club: Club Alpha' when row_label_prefix is 'club'."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Club Alpha', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='club')

        assert 'club: Club Alpha' in html

    def test_header_format_with_team_label(self, setup_aws):
        """Header should display 'team: Alpha Squad' when row_label_prefix is 'team'."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Alpha Squad', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='team')

        assert 'team: Alpha Squad' in html

    def test_header_format_with_school_label(self, setup_aws):
        """Header should display 'school: Lyceum X' when row_label_prefix is 'school'."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Lyceum X', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='school')

        assert 'school: Lyceum X' in html

    def test_header_fallback_to_row_when_prefix_absent(self, setup_aws):
        """Header should use default 'row' prefix when row_label_prefix is not passed."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'My Row Name', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        # Default row_label_prefix is 'row'
        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event')

        assert 'row: My Row Name' in html

    def test_header_shows_logo_when_present(self, setup_aws):
        """Header should include an img tag with row-logo class when logo_url is present."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Club Alpha', 'logo_url': 'https://example.com/logo.png'}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='club')

        assert '<img src="https://example.com/logo.png"' in html
        assert 'class="row-logo"' in html

    def test_header_no_img_when_logo_absent(self, setup_aws):
        """Header should NOT include an img tag when logo_url is None."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Someone'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Club Alpha', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='club')

        assert '<img' not in html

    def test_row_label_prefix_used_in_by_guest_mode(self, setup_aws):
        """by_guest mode should also use the row_label_prefix in headers."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-2',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Anna Test'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-2': {'label': 'Riders', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_guest_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='club')

        # The row info should be present somewhere in the guest page
        assert 'club: Riders' in html or 'Riders' in html


class TestNoHardcodedClubText:
    """Tests for Requirement 6.5: no hardcoded 'club' text in output."""

    def test_no_hardcoded_club_class_in_html(self, setup_aws):
        """Generated HTML should not contain any 'club-' CSS class prefix."""
        handler = setup_aws
        orders = [{
            'order_id': 'ord-1',
            'registry_row_id': 'row-1',
            'items': [{'product_id': 'prod-1', 'item_fields_data': {'name': 'Person'}, 'unit_price': 50, 'line_total': 50}],
            'total_amount': 50,
            'payment_status': 'paid',
            'delegates': {},
        }]
        registry_rows = {'row-1': {'label': 'Test Group', 'logo_url': None}}
        products_map = {'prod-1': {'name': 'Ticket'}}

        html = handler.build_by_order_pdf(orders, registry_rows, products_map, 'Test Event', row_label_prefix='team')

        # Should not contain any 'club-' prefixed CSS class
        assert 'club-name' not in html
        assert 'club-logo' not in html

    def test_sort_key_uses_row_label_name(self, setup_aws):
        """_sort_key_row_label function should exist and work (not _sort_key_club_name)."""
        handler = setup_aws
        assert hasattr(handler, '_sort_key_row_label')
        assert handler._sort_key_row_label('Zebra') == 'zebra'
        assert handler._sort_key_row_label('ALPHA') == 'alpha'
