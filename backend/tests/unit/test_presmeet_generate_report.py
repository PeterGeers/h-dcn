"""
Unit Tests for PresMeet Generate Report Handler

Tests for GET /presmeet/reports/{type}?event_id=X&status=all&payment_status=all&format=json

Covers:
- Auth validation (Webshop_Management + Regio_Pressmeet/Regio_All)
- Report type validation
- Event_id validation
- Filter validation
- All 7 report types: attendees, party, tshirts, pickups, dropoffs, financial, overview
- JSON and CSV output formats
- Event metadata in response
"""

import sys
import os
import json
import csv
import io
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest

# Add handler path
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'presmeet_generate_report')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set env vars before import
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events')


def _make_event(http_method='GET', path_params=None, query_params=None,
                user_email='admin@h-dcn.nl',
                user_roles=None):
    """Build a Lambda event dict."""
    if user_roles is None:
        user_roles = ['Webshop_Management', 'Regio_Pressmeet']

    return {
        'httpMethod': http_method,
        'pathParameters': path_params or {},
        'queryStringParameters': query_params or {},
        'headers': {
            'Authorization': 'Bearer fake.jwt.token'
        },
        '_test_user_email': user_email,
        '_test_user_roles': user_roles,
    }


def _sample_event_record():
    """Return a sample event record."""
    return {
        'event_id': 'evt-001',
        'event_type': 'presmeet',
        'name': 'Presidents Meeting 2027',
        'location': 'Hotel Amersfoort',
        'start_date': '2027-06-20',
        'end_date': '2027-06-22',
        'registration_open': '2027-01-01',
        'registration_close': '2027-05-01',
        'status': 'open',
    }


def _sample_orders():
    """Return sample order records for testing report generation."""
    return [
        {
            'order_id': 'ord-001',
            'club_id': 'club-alpha',
            'event_id': 'evt-001',
            'event_type': 'presmeet',
            'status': 'submitted',
            'payment_status': 'paid',
            'total_amount': Decimal('150.00'),
            'total_paid': Decimal('150.00'),
            'items': [
                {
                    'product_id': 'prod-meeting-2027',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Jan de Vries', 'role': 'President'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                },
                {
                    'product_id': 'prod-party-2027',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Jan de Vries', 'person_type': 'delegate'},
                    'unit_price': Decimal('25.00'),
                    'line_total': Decimal('25.00'),
                },
                {
                    'product_id': 'prod-tshirt-2027',
                    'variant_id': 'L-Male',
                    'item_fields_data': {'person_name': 'Jan de Vries'},
                    'unit_price': Decimal('25.00'),
                    'line_total': Decimal('25.00'),
                },
                {
                    'product_id': 'prod-transfer-2027',
                    'variant_id': 'Pickup-AMS',
                    'item_fields_data': {
                        'flight_number': 'KL1234',
                        'date': '2027-06-20',
                        'time': '14:00',
                        'persons': 2,
                    },
                    'unit_price': Decimal('25.00'),
                    'line_total': Decimal('50.00'),
                },
            ],
        },
        {
            'order_id': 'ord-002',
            'club_id': 'club-beta',
            'event_id': 'evt-001',
            'event_type': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('100.00'),
            'total_paid': Decimal('0'),
            'items': [
                {
                    'product_id': 'prod-meeting-2027',
                    'variant_id': None,
                    'item_fields_data': {'name': 'Piet Jansen', 'role': 'Secretary'},
                    'unit_price': Decimal('50.00'),
                    'line_total': Decimal('50.00'),
                },
                {
                    'product_id': 'prod-transfer-2027',
                    'variant_id': 'Dropoff-RTM',
                    'item_fields_data': {
                        'flight_number': 'BA5678',
                        'date': '2027-06-22',
                        'time': '16:00',
                        'persons': 1,
                    },
                    'unit_price': Decimal('25.00'),
                    'line_total': Decimal('25.00'),
                },
            ],
        },
    ]


# ============================================================
# Test helper functions directly (without Lambda context/auth)
# ============================================================

class TestReportHelpers:
    """Test internal report generation helpers."""

    def test_apply_filters_status(self):
        from app import apply_filters
        orders = _sample_orders()
        filtered = apply_filters(orders, 'submitted', 'all')
        assert len(filtered) == 1
        assert filtered[0]['order_id'] == 'ord-001'

    def test_apply_filters_payment_status(self):
        from app import apply_filters
        orders = _sample_orders()
        filtered = apply_filters(orders, 'all', 'unpaid')
        assert len(filtered) == 1
        assert filtered[0]['order_id'] == 'ord-002'

    def test_apply_filters_all_all(self):
        from app import apply_filters
        orders = _sample_orders()
        filtered = apply_filters(orders, 'all', 'all')
        assert len(filtered) == 2

    def test_apply_filters_combined(self):
        from app import apply_filters
        orders = _sample_orders()
        # submitted + paid → only ord-001
        filtered = apply_filters(orders, 'submitted', 'paid')
        assert len(filtered) == 1
        assert filtered[0]['order_id'] == 'ord-001'

    def test_apply_filters_no_match(self):
        from app import apply_filters
        orders = _sample_orders()
        filtered = apply_filters(orders, 'locked', 'all')
        assert len(filtered) == 0

    def test_build_metadata(self):
        from app import build_metadata
        event_record = _sample_event_record()
        meta = build_metadata(event_record)
        assert meta['event_name'] == 'Presidents Meeting 2027'
        assert meta['event_location'] == 'Hotel Amersfoort'
        assert meta['event_dates']['start'] == '2027-06-20'
        assert meta['event_dates']['end'] == '2027-06-22'
        assert 'generated_at' in meta

    def test_generate_attendees_report(self):
        from app import generate_attendees_report
        orders = _sample_orders()
        result = generate_attendees_report(orders)
        # 2 meeting tickets across both orders
        assert len(result) == 2
        names = [r['name'] for r in result]
        assert 'Jan de Vries' in names
        assert 'Piet Jansen' in names
        # Check structure
        for entry in result:
            assert 'name' in entry
            assert 'role' in entry
            assert 'club' in entry
            assert 'order_id' in entry
            assert 'status' in entry

    def test_generate_party_report(self):
        from app import generate_party_report
        orders = _sample_orders()
        result = generate_party_report(orders)
        # Only 1 party ticket (from ord-001)
        assert len(result) == 1
        assert result[0]['name'] == 'Jan de Vries'
        assert result[0]['person_type'] == 'delegate'
        assert result[0]['club'] == 'club-alpha'

    def test_generate_tshirts_report(self):
        from app import generate_tshirts_report
        orders = _sample_orders()
        result = generate_tshirts_report(orders)
        assert len(result) == 1
        assert result[0]['person_name'] == 'Jan de Vries'
        assert result[0]['variant'] == 'L-Male'
        assert result[0]['club'] == 'club-alpha'

    def test_generate_pickups_report(self):
        from app import generate_pickups_report
        orders = _sample_orders()
        result = generate_pickups_report(orders)
        # Only Pickup-AMS (from ord-001)
        assert len(result) == 1
        assert result[0]['flight'] == 'KL1234'
        assert result[0]['persons'] == 2
        assert result[0]['club'] == 'club-alpha'

    def test_generate_dropoffs_report(self):
        from app import generate_dropoffs_report
        orders = _sample_orders()
        result = generate_dropoffs_report(orders)
        # Only Dropoff-RTM (from ord-002)
        assert len(result) == 1
        assert result[0]['flight'] == 'BA5678'
        assert result[0]['persons'] == 1
        assert result[0]['club'] == 'club-beta'

    def test_generate_financial_report(self):
        from app import generate_financial_report
        orders = _sample_orders()
        result = generate_financial_report(orders)
        assert 'clubs' in result
        assert 'totals' in result
        assert len(result['clubs']) == 2

        # Check totals
        assert result['totals']['total_charged'] == 250.00
        assert result['totals']['total_paid'] == 150.00
        assert result['totals']['total_outstanding'] == 100.00

        # Check per-club
        club_map = {c['club']: c for c in result['clubs']}
        assert club_map['club-alpha']['total_charged'] == 150.00
        assert club_map['club-alpha']['total_paid'] == 150.00
        assert club_map['club-alpha']['total_outstanding'] == 0.00
        assert club_map['club-beta']['total_charged'] == 100.00
        assert club_map['club-beta']['total_paid'] == 0.00
        assert club_map['club-beta']['total_outstanding'] == 100.00

    def test_generate_overview_report(self):
        from app import generate_overview_report
        orders = _sample_orders()
        result = generate_overview_report(orders)
        assert result['total_orders'] == 2
        assert 'product_counts' in result
        assert 'payment_status_breakdown' in result
        assert 'order_status_breakdown' in result
        # Check counts
        assert result['payment_status_breakdown']['paid'] == 1
        assert result['payment_status_breakdown']['unpaid'] == 1
        assert result['order_status_breakdown']['submitted'] == 1
        assert result['order_status_breakdown']['draft'] == 1


class TestCsvFormat:
    """Test CSV output formatting."""

    def test_csv_attendees(self):
        from app import format_as_csv, generate_attendees_report
        orders = _sample_orders()
        data = generate_attendees_report(orders)
        csv_output = format_as_csv('attendees', data)
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        # Header + 2 data rows
        assert len(rows) == 3
        assert rows[0] == ['name', 'role', 'club', 'order_id', 'status']

    def test_csv_financial(self):
        from app import format_as_csv, generate_financial_report
        orders = _sample_orders()
        data = generate_financial_report(orders)
        csv_output = format_as_csv('financial', data)
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        # Header + 2 clubs + 1 TOTAL row
        assert len(rows) == 4
        assert rows[0] == ['club', 'total_charged', 'total_paid', 'total_outstanding']
        # Last row is TOTAL
        assert rows[-1][0] == 'TOTAL'

    def test_csv_overview(self):
        from app import format_as_csv, generate_overview_report
        orders = _sample_orders()
        data = generate_overview_report(orders)
        csv_output = format_as_csv('overview', data)
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        # Header row is ['metric', 'value']
        assert rows[0] == ['metric', 'value']
        # Should have total_orders row
        metrics = [row[0] for row in rows[1:]]
        assert 'total_orders' in metrics

    def test_csv_empty_report(self):
        from app import format_as_csv
        csv_output = format_as_csv('attendees', [])
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        # Just the header
        assert len(rows) == 1
        assert rows[0] == ['name', 'role', 'club', 'order_id', 'status']

    def test_csv_pickups_headers(self):
        from app import format_as_csv
        csv_output = format_as_csv('pickups', [])
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        assert rows[0] == ['flight', 'date', 'time', 'persons', 'club', 'order_id', 'status']


class TestLambdaHandler:
    """Test the full lambda_handler with mocked auth and DynamoDB."""

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_successful_json_report(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'metadata' in body
        assert 'data' in body
        assert body['metadata']['event_name'] == 'Presidents Meeting 2027'
        assert len(body['data']) == 2  # 2 meeting attendees

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_csv_format_response(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001', 'format': 'csv'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        assert 'text/csv' in response['headers']['Content-Type']
        assert 'Content-Disposition' in response['headers']
        # Body should be CSV text
        reader = csv.reader(io.StringIO(response['body']))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 data rows

    @patch('app.extract_user_credentials')
    def test_auth_failure(self, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = (None, None, {
            'statusCode': 401,
            'headers': {},
            'body': json.dumps({'error': 'Unauthorized'})
        })

        event = _make_event(path_params={'type': 'attendees'}, query_params={'event_id': 'evt-001'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    def test_permission_denied_no_webshop_management(self, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('user@h-dcn.nl', ['hdcnLeden'], None)
        mock_validate.return_value = (False, {
            'statusCode': 403,
            'headers': {},
            'body': json.dumps({'error': 'Access denied'})
        }, None)

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001'},
            user_roles=['hdcnLeden']
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    def test_permission_denied_no_regio_pressmeet(self, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001'},
            user_roles=['Webshop_Management']  # Missing Regio_Pressmeet
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Regio_Pressmeet' in body['error']

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_report_type(self, mock_log, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'invalid_type'},
            query_params={'event_id': 'evt-001'}
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid report type' in body['error']

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_missing_event_id(self, mock_log, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={}  # No event_id
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'event_id' in body['error']

    @patch('app.events_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_event_not_found(self, mock_log, mock_validate, mock_extract, mock_events):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})
        mock_events.get_item.return_value = {}  # No item

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'nonexistent'}
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_status_filter(self, mock_log, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001', 'status': 'invalid'}
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid status filter' in body['error']

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_payment_status_filter(self, mock_log, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001', 'payment_status': 'bogus'}
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid payment_status filter' in body['error']

    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_invalid_format(self, mock_log, mock_validate, mock_extract):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001', 'format': 'xml'}
        )
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid format' in body['error']

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_financial_report_json(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'financial'},
            query_params={'event_id': 'evt-001'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'metadata' in body
        assert 'data' in body
        data = body['data']
        assert 'clubs' in data
        assert 'totals' in data
        assert data['totals']['total_charged'] == 250.00
        assert data['totals']['total_paid'] == 150.00
        assert data['totals']['total_outstanding'] == 100.00

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_overview_report_json(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'overview'},
            query_params={'event_id': 'evt-001'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        data = body['data']
        assert data['total_orders'] == 2

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_status_filter_applied(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        """Test that status filter correctly filters orders before report generation."""
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'attendees'},
            query_params={'event_id': 'evt-001', 'status': 'submitted'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Only ord-001 is submitted, which has 1 meeting attendee
        assert len(body['data']) == 1
        assert body['data'][0]['name'] == 'Jan de Vries'

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_payment_status_filter_applied(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        """Test that payment_status filter correctly filters orders."""
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': _sample_orders()}

        event = _make_event(
            path_params={'type': 'financial'},
            query_params={'event_id': 'evt-001', 'payment_status': 'unpaid'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Only club-beta (unpaid)
        assert len(body['data']['clubs']) == 1
        assert body['data']['clubs'][0]['club'] == 'club-beta'

    def test_options_request(self):
        from app import lambda_handler

        event = _make_event(http_method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_regio_all_grants_access(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        """Test that Regio_All also grants access (not just Regio_Pressmeet)."""
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_All'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}
        mock_orders.query.return_value = {'Items': []}

        event = _make_event(
            path_params={'type': 'overview'},
            query_params={'event_id': 'evt-001'},
            user_roles=['Webshop_Management', 'Regio_All']
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200

    @patch('app.events_table')
    @patch('app.orders_table')
    @patch('app.extract_user_credentials')
    @patch('app.validate_permissions_with_regions')
    @patch('app.log_successful_access')
    def test_paginated_query(self, mock_log, mock_validate, mock_extract, mock_orders, mock_events):
        """Test that handler properly handles paginated GSI query responses."""
        from app import lambda_handler

        mock_extract.return_value = ('admin@h-dcn.nl', ['Webshop_Management', 'Regio_Pressmeet'], None)
        mock_validate.return_value = (True, None, {'has_full_access': True})

        mock_events.get_item.return_value = {'Item': _sample_event_record()}

        # Simulate pagination: first call returns items + LastEvaluatedKey, second returns rest
        first_page = _sample_orders()[:1]
        second_page = _sample_orders()[1:]
        mock_orders.query.side_effect = [
            {'Items': first_page, 'LastEvaluatedKey': {'event_id': 'evt-001', 'club_id': 'club-alpha'}},
            {'Items': second_page},
        ]

        event = _make_event(
            path_params={'type': 'overview'},
            query_params={'event_id': 'evt-001'}
        )

        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['data']['total_orders'] == 2


class TestProductTypeField:
    """Test that product_type field is used as the primary identifier."""

    def test_product_type_takes_priority_over_product_id(self):
        """When product_type is set, it should be used regardless of product_id value."""
        from app import generate_attendees_report
        orders = [{
            'order_id': 'ord-100',
            'club_id': 'club-x',
            'status': 'submitted',
            'items': [
                {
                    'product_id': 'a1b2c3d4-uuid-no-keywords',
                    'product_type': 'meeting_ticket',
                    'item_fields_data': {'name': 'Alice', 'role': 'President'},
                },
            ],
        }]
        result = generate_attendees_report(orders)
        assert len(result) == 1
        assert result[0]['name'] == 'Alice'

    def test_product_type_prevents_false_positive_from_product_id(self):
        """When product_type is set to something else, product_id string match should NOT apply."""
        from app import generate_attendees_report
        orders = [{
            'order_id': 'ord-101',
            'club_id': 'club-x',
            'status': 'submitted',
            'items': [
                {
                    # product_id contains 'meeting' but product_type says it's a party_ticket
                    'product_id': 'prod-meeting-legacy',
                    'product_type': 'party_ticket',
                    'item_fields_data': {'name': 'Bob', 'role': 'Delegate'},
                },
            ],
        }]
        result = generate_attendees_report(orders)
        # Should NOT match as attendee since product_type is party_ticket
        assert len(result) == 0

    def test_fallback_to_product_id_when_no_product_type(self):
        """When product_type is missing, fallback to product_id string matching."""
        from app import generate_party_report
        orders = [{
            'order_id': 'ord-102',
            'club_id': 'club-y',
            'status': 'submitted',
            'items': [
                {
                    'product_id': 'prod-party-2027',
                    # No product_type field
                    'item_fields_data': {'name': 'Charlie', 'person_type': 'guest'},
                },
            ],
        }]
        result = generate_party_report(orders)
        assert len(result) == 1
        assert result[0]['name'] == 'Charlie'

    def test_product_type_tshirt(self):
        """product_type 'tshirt' identifies t-shirt items correctly."""
        from app import generate_tshirts_report
        orders = [{
            'order_id': 'ord-103',
            'club_id': 'club-z',
            'status': 'submitted',
            'items': [
                {
                    'product_id': 'uuid-no-keywords',
                    'product_type': 'tshirt',
                    'variant_id': 'XL-Female',
                    'item_fields_data': {'person_name': 'Dana'},
                },
            ],
        }]
        result = generate_tshirts_report(orders)
        assert len(result) == 1
        assert result[0]['person_name'] == 'Dana'
        assert result[0]['variant'] == 'XL-Female'

    def test_product_type_airport_transfer(self):
        """product_type 'airport_transfer' identifies transfer items correctly."""
        from app import generate_pickups_report
        orders = [{
            'order_id': 'ord-104',
            'club_id': 'club-w',
            'status': 'submitted',
            'items': [
                {
                    'product_id': 'uuid-no-keywords',
                    'product_type': 'airport_transfer',
                    'variant_id': 'Pickup-AMS',
                    'item_fields_data': {'flight_number': 'LH999', 'date': '2027-06-20', 'time': '10:00', 'persons': 3},
                },
            ],
        }]
        result = generate_pickups_report(orders)
        assert len(result) == 1
        assert result[0]['flight'] == 'LH999'
        assert result[0]['persons'] == 3

    def test_overview_report_groups_by_product_type(self):
        """Overview report uses product_type when available for grouping counts."""
        from app import generate_overview_report
        orders = [{
            'order_id': 'ord-105',
            'club_id': 'club-v',
            'status': 'submitted',
            'payment_status': 'paid',
            'items': [
                {'product_id': 'uuid-1', 'product_type': 'meeting_ticket'},
                {'product_id': 'uuid-2', 'product_type': 'meeting_ticket'},
                {'product_id': 'uuid-3', 'product_type': 'party_ticket'},
            ],
        }]
        result = generate_overview_report(orders)
        assert result['product_counts']['meeting_ticket'] == 2
        assert result['product_counts']['party_ticket'] == 1
