"""
Integration Tests for PresMeet v3 Order Lifecycle.

End-to-end flow tests that call multiple handlers in sequence with moto-mocked
DynamoDB tables (including the event-club-index GSI).

Tests cover:
- Full order lifecycle: create → edit → submit → pay → lock
- Event constraint validation with multiple clubs
- Optimistic locking conflict resolution
- Auto-lock on event close (scheduler)
- Authorization: delegate access, admin access, cross-club rejection
- Channel rename compatibility (old records without `channel` field)

Requirements: All
"""

import json
import os
import sys
import uuid
import pytest
import base64
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import boto3
from moto import mock_aws

# ─── Path setup ────────────────────────────────────────────────────────────────
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# ─── Environment variables ─────────────────────────────────────────────────────
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['PAYMENTS_TABLE_NAME'] = 'Payments'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['PAYMENT_REDIRECT_URL'] = 'https://portal.h-dcn.nl/presmeet'
os.environ['MOLLIE_WEBHOOK_URL'] = 'https://api.h-dcn.nl/webhooks/mollie'


# ─── Auth helpers ──────────────────────────────────────────────────────────────

def create_jwt_token(email="delegate@club.nl", groups=None):
    """Create a fake JWT token for testing."""
    if groups is None:
        groups = ["hdcnLeden", "Regio_Pressmeet"]

    payload = {
        "email": email,
        "cognito:groups": groups,
        "exp": 9999999999,
        "iat": 1000000000,
    }

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')

    return f"{header}.{payload_encoded}.test_signature"


def make_event(token=None, method='GET', path_params=None, query_params=None, body=None):
    """Create an API Gateway event dict."""
    event = {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': query_params,
        'pathParameters': path_params,
        'body': json.dumps(body) if body else None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


# ─── DynamoDB setup ────────────────────────────────────────────────────────────

def create_tables(dynamodb):
    """Create all required DynamoDB tables with GSIs for integration testing."""
    # Orders table with event-club-index GSI
    dynamodb.create_table(
        TableName='Orders',
        KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'order_id', 'AttributeType': 'S'},
            {'AttributeName': 'event_id', 'AttributeType': 'S'},
            {'AttributeName': 'club_id', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[{
            'IndexName': 'event-club-index',
            'KeySchema': [
                {'AttributeName': 'event_id', 'KeyType': 'HASH'},
                {'AttributeName': 'club_id', 'KeyType': 'RANGE'},
            ],
            'Projection': {'ProjectionType': 'ALL'},
        }],
        BillingMode='PAY_PER_REQUEST',
    )

    # Events table
    dynamodb.create_table(
        TableName='Events',
        KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'event_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    # Producten table
    dynamodb.create_table(
        TableName='Producten',
        KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'product_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    # Payments table
    dynamodb.create_table(
        TableName='Payments',
        KeySchema=[{'AttributeName': 'payment_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'payment_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    # Members table
    dynamodb.create_table(
        TableName='Members',
        KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'member_id', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def seed_event(events_table, event_id='evt-pm2027', status='open'):
    """Create a test event in the Events table."""
    today = date.today()
    events_table.put_item(Item={
        'event_id': event_id,
        'event_type': 'presmeet',
        'name': 'Presidents Meeting 2027',
        'location': 'Hotel Amersfoort',
        'status': status,
        'start_date': (today + timedelta(days=90)).isoformat(),
        'end_date': (today + timedelta(days=92)).isoformat(),
        'registration_open': (today - timedelta(days=30)).isoformat(),
        'registration_close': (today + timedelta(days=60)).isoformat(),
        'payment_deadline': (today + timedelta(days=75)).isoformat(),
        'product_ids': ['prod-meeting', 'prod-party'],
        'constraints': [
            {
                'key': 'max_meeting_attendees',
                'label': 'Maximum vergaderdeelnemers',
                'max': Decimal('5'),
                'counting_rule': 'count_items_by_product',
                'product_id': 'prod-meeting',
            },
            {
                'key': 'max_party_guests',
                'label': 'Maximum feestgangers',
                'max': Decimal('10'),
                'counting_rule': 'count_items_by_product',
                'product_id': 'prod-party',
            },
        ],
        'created_at': '2026-12-01T08:00:00Z',
        'created_by': 'admin@h-dcn.nl',
    })


def seed_products(producten_table):
    """Create test products in the Producten table."""
    producten_table.put_item(Item={
        'product_id': 'prod-meeting',
        'name': 'Meeting Ticket PM2027',
        'channel': 'presmeet',
        'event_type': 'presmeet',
        'price': Decimal('50.00'),
        'order_item_fields': [
            {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
            {'id': 'role', 'label': 'Functie', 'type': 'text', 'required': True},
        ],
        'purchase_rules': {
            'min_per_club': Decimal('1'),
            'max_per_club': Decimal('3'),
            'order_mode': 'persistent',
        },
    })

    producten_table.put_item(Item={
        'product_id': 'prod-party',
        'name': 'Party Ticket PM2027',
        'channel': 'presmeet',
        'event_type': 'presmeet',
        'price': Decimal('30.00'),
        'order_item_fields': [
            {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
        ],
        'purchase_rules': {
            'max_per_club': Decimal('5'),
            'order_mode': 'persistent',
        },
    })


def seed_member(members_table, email, club_id):
    """Create a member record with a club assignment."""
    members_table.put_item(Item={
        'member_id': str(uuid.uuid4()),
        'email': email,
        'club_id': club_id,
        'firstName': 'Test',
        'lastName': 'User',
        'status': 'active',
    })


# ─── Fixture: reload handlers within moto context ─────────────────────────────

def _clear_handler_modules():
    """Clear cached handler modules so they re-import with fresh DynamoDB connections."""
    modules_to_clear = [m for m in sys.modules if (
        m.startswith('handler.presmeet_')
        or m.startswith('handler.admin_lock')
        or m.startswith('handler.admin_unlock')
        or m.startswith('handler.event_status_scheduler')
        or m.startswith('handler.get_products')
        or m == 'shared' or m.startswith('shared.')
    )]
    for mod in modules_to_clear:
        del sys.modules[mod]


# ═══════════════════════════════════════════════════════════════════════════════
# 29.1 Full Order Lifecycle: create → edit → submit → pay → lock
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullOrderLifecycle:
    """Integration test for the complete order lifecycle."""

    @mock_aws
    def test_create_edit_submit_pay_lock(self):
        """Test full lifecycle: get (create) → upsert (edit) → submit → pay → lock."""
        # Setup DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        events_table = dynamodb.Table('Events')
        producten_table = dynamodb.Table('Producten')
        members_table = dynamodb.Table('Members')

        seed_event(events_table)
        seed_products(producten_table)
        seed_member(members_table, 'delegate@club-a.nl', 'club-a')

        # Clear and re-import handlers within moto context
        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app
        import handler.presmeet_upsert_order.app as upsert_app
        import handler.presmeet_submit_order.app as submit_app
        import handler.presmeet_create_payment.app as payment_app
        import handler.admin_lock_orders.app as lock_app

        token = create_jwt_token(email="delegate@club-a.nl", groups=["hdcnLeden", "Regio_Pressmeet"])

        # ─── Step 1: GET order (auto-create draft) ─────────────────────────
        event = make_event(token=token, query_params={'event_id': 'evt-pm2027'})
        response = get_order_app.lambda_handler(event, None)

        assert response['statusCode'] == 201, f"Expected 201, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        order_id = body['order_id']
        assert body['status'] == 'draft'
        assert body['version'] == 1
        assert body['delegates']['primary'] == 'delegate@club-a.nl'

        # ─── Step 2: PUT upsert (edit items) ──────────────────────────────
        # Note: use int for unit_price since DynamoDB rejects Python floats
        # In production, API Gateway serializes JSON to string which is
        # then json.loads'd — but boto3 resource needs Decimal/int, not float.
        items = [
            {
                'product_id': 'prod-meeting',
                'variant_id': None,
                'item_fields_data': {'name': 'Jan de Vries', 'role': 'President'},
                'unit_price': 50,
            },
            {
                'product_id': 'prod-party',
                'variant_id': None,
                'item_fields_data': {'name': 'Jan de Vries'},
                'unit_price': 30,
            },
        ]

        event = make_event(
            token=token,
            method='PUT',
            path_params={'id': order_id},
            body={'items': items, 'version': 1},
        )
        response = upsert_app.lambda_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['version'] == 2
        assert body['total_amount'] == 80.0

        # ─── Step 3: POST submit ──────────────────────────────────────────
        event = make_event(
            token=token,
            method='POST',
            path_params={'id': order_id},
        )
        response = submit_app.lambda_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert 'submitted_at' in body

        # ─── Step 4: POST pay ─────────────────────────────────────────────
        with patch.object(payment_app, 'create_payment') as mock_mollie:
            mock_mollie.return_value = {
                'mollie_payment_id': 'tr_test123',
                'checkout_url': 'https://mollie.com/pay/test123',
            }

            event = make_event(
                token=token,
                method='POST',
                path_params={'id': order_id},
                body={'method': 'ideal'},
            )
            response = payment_app.lambda_handler(event, None)

        assert response['statusCode'] == 201, f"Expected 201, got {response['statusCode']}: {response['body']}"
        pay_body = json.loads(response['body'])
        assert 'checkout_url' in pay_body
        assert pay_body['amount'] == 80.0

        # ─── Step 5: POST lock (admin) ────────────────────────────────────
        admin_token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(
            token=admin_token,
            method='POST',
            path_params={'id': order_id},
        )
        response = lock_app.lambda_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        lock_body = json.loads(response['body'])
        assert lock_body['order']['status'] == 'locked'
        assert lock_body['transition']['source'] == 'manual'


# ═══════════════════════════════════════════════════════════════════════════════
# 29.2 Event Constraint Validation with Multiple Clubs
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventConstraintValidation:
    """Test event-level capacity constraints across multiple clubs."""

    @mock_aws
    def test_constraint_blocks_over_capacity(self):
        """
        When multiple clubs fill capacity, further submissions are blocked.
        max_meeting_attendees = 5, each club submits 3 meeting tickets.
        Second club's submission should be rejected (3+3 > 5).
        """
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        events_table = dynamodb.Table('Events')
        producten_table = dynamodb.Table('Producten')
        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_event(events_table)
        seed_products(producten_table)
        seed_member(members_table, 'delegate-a@club-a.nl', 'club-a')
        seed_member(members_table, 'delegate-b@club-b.nl', 'club-b')

        # Pre-create a submitted order for club-a with 3 meeting tickets
        orders_table.put_item(Item={
            'order_id': 'ord-club-a',
            'club_id': 'club-a',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('150.00'),
            'total_paid': Decimal('0.00'),
            'items': [
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'A1', 'role': 'Pres'}, 'unit_price': Decimal('50.00')},
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'A2', 'role': 'VP'}, 'unit_price': Decimal('50.00')},
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'A3', 'role': 'Sec'}, 'unit_price': Decimal('50.00')},
            ],
            'delegates': {'primary': 'delegate-a@club-a.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-15T10:30:00Z',
            'created_by': 'delegate-a@club-a.nl',
        })

        # Pre-create a draft order for club-b with 3 meeting tickets
        orders_table.put_item(Item={
            'order_id': 'ord-club-b',
            'club_id': 'club-b',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('150.00'),
            'total_paid': Decimal('0.00'),
            'items': [
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'B1', 'role': 'Pres'}, 'unit_price': Decimal('50.00')},
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'B2', 'role': 'VP'}, 'unit_price': Decimal('50.00')},
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'B3', 'role': 'Sec'}, 'unit_price': Decimal('50.00')},
            ],
            'delegates': {'primary': 'delegate-b@club-b.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-15T10:30:00Z',
            'created_by': 'delegate-b@club-b.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_submit_order.app as submit_app

        # Club B tries to submit: 3 (club-a submitted) + 3 (club-b) = 6 > max 5
        token_b = create_jwt_token(email="delegate-b@club-b.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(
            token=token_b,
            method='POST',
            path_params={'id': 'ord-club-b'},
        )
        response = submit_app.lambda_handler(event, None)

        assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert 'errors' in body
        # Should contain a constraint violation for max_meeting_attendees
        constraint_errors = [e for e in body['errors'] if 'constraint' in str(e).lower() or 'capacity' in str(e).lower() or 'max' in str(e).lower()]
        assert len(constraint_errors) > 0, f"Expected constraint error, got: {body['errors']}"


# ═══════════════════════════════════════════════════════════════════════════════
# 29.3 Optimistic Locking Conflict Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimisticLocking:
    """Test optimistic locking conflict detection and resolution."""

    @mock_aws
    def test_version_conflict_returns_409(self):
        """When two updates use the same version, the second should fail with 409."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'delegate@club-a.nl', 'club-a')

        # Create an existing draft order at version 2
        orders_table.put_item(Item={
            'order_id': 'ord-conflict',
            'club_id': 'club-a',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'total_paid': Decimal('0.00'),
            'items': [
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'Jan', 'role': 'Pres'}, 'unit_price': Decimal('50.00')},
            ],
            'delegates': {'primary': 'delegate@club-a.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-12T09:00:00Z',
            'created_by': 'delegate@club-a.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_upsert_order.app as upsert_app

        token = create_jwt_token(email="delegate@club-a.nl", groups=["hdcnLeden", "Regio_Pressmeet"])

        # First update: version=2 → succeeds, version becomes 3
        items_v1 = [
            {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'Jan Updated', 'role': 'Pres'}, 'unit_price': 50},
        ]
        event = make_event(
            token=token,
            method='PUT',
            path_params={'id': 'ord-conflict'},
            body={'items': items_v1, 'version': 2},
        )
        response = upsert_app.lambda_handler(event, None)
        assert response['statusCode'] == 200, f"First update failed: {response['body']}"
        body = json.loads(response['body'])
        assert body['version'] == 3

        # Second update: same version=2 → should fail with 409
        items_v2 = [
            {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'Piet Conflict', 'role': 'VP'}, 'unit_price': 50},
        ]
        event = make_event(
            token=token,
            method='PUT',
            path_params={'id': 'ord-conflict'},
            body={'items': items_v2, 'version': 2},
        )
        response = upsert_app.lambda_handler(event, None)

        assert response['statusCode'] == 409, f"Expected 409, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['current_version'] == 3
        assert 'version_conflict' in body.get('error', '')


# ═══════════════════════════════════════════════════════════════════════════════
# 29.4 Auto-Lock on Event Close (Scheduler)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoLockOnEventClose:
    """Test the event status scheduler auto-locking submitted orders."""

    @mock_aws
    def test_scheduler_closes_event_and_locks_orders(self):
        """
        When registration_close is in the past, scheduler transitions event
        to closed and auto-locks all submitted orders.
        """
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        events_table = dynamodb.Table('Events')
        orders_table = dynamodb.Table('Orders')

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        last_week = (date.today() - timedelta(days=7)).isoformat()

        # Event with registration_close in the past
        events_table.put_item(Item={
            'event_id': 'evt-closing',
            'event_type': 'presmeet',
            'name': 'PresMeet Closing',
            'status': 'open',
            'registration_open': last_week,
            'registration_close': yesterday,
            'start_date': (date.today() + timedelta(days=30)).isoformat(),
            'end_date': (date.today() + timedelta(days=32)).isoformat(),
        })

        # Create submitted orders for this event
        orders_table.put_item(Item={
            'order_id': 'ord-submitted-1',
            'club_id': 'club-x',
            'event_id': 'evt-closing',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('100.00'),
            'total_paid': Decimal('0.00'),
            'items': [{'product_id': 'prod-meeting', 'item_fields_data': {'name': 'X1', 'role': 'P'}, 'unit_price': Decimal('50.00')}],
            'delegates': {'primary': 'x@club-x.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-15T10:30:00Z',
        })

        orders_table.put_item(Item={
            'order_id': 'ord-submitted-2',
            'club_id': 'club-y',
            'event_id': 'evt-closing',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'total_paid': Decimal('0.00'),
            'items': [{'product_id': 'prod-meeting', 'item_fields_data': {'name': 'Y1', 'role': 'VP'}, 'unit_price': Decimal('50.00')}],
            'delegates': {'primary': 'y@club-y.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-15T10:30:00Z',
        })

        # A draft order (should NOT be locked)
        orders_table.put_item(Item={
            'order_id': 'ord-draft-1',
            'club_id': 'club-z',
            'event_id': 'evt-closing',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'z@club-z.nl', 'secondary': None},
            'version': Decimal('1'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-10T08:00:00Z',
        })

        _clear_handler_modules()
        import handler.event_status_scheduler.app as scheduler_app

        # Run the scheduler
        result = scheduler_app.lambda_handler({}, None)

        assert 'evt-closing' in result['closed']
        assert result['orders_locked'] == 2

        # Verify event status changed to closed
        event_record = events_table.get_item(Key={'event_id': 'evt-closing'})['Item']
        assert event_record['status'] == 'closed'

        # Verify submitted orders are locked
        order1 = orders_table.get_item(Key={'order_id': 'ord-submitted-1'})['Item']
        assert order1['status'] == 'locked'
        assert len(order1['status_history']) == 1
        assert order1['status_history'][0]['source'] == 'auto_close'

        order2 = orders_table.get_item(Key={'order_id': 'ord-submitted-2'})['Item']
        assert order2['status'] == 'locked'

        # Draft order should remain draft
        draft_order = orders_table.get_item(Key={'order_id': 'ord-draft-1'})['Item']
        assert draft_order['status'] == 'draft'


# ═══════════════════════════════════════════════════════════════════════════════
# 29.5 Authorization: delegate access, admin access, cross-club rejection
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthorization:
    """Test authorization flows across handlers."""

    @mock_aws
    def test_delegate_can_access_own_order(self):
        """Primary delegate can access their club's order."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'primary@club-a.nl', 'club-a')

        orders_table.put_item(Item={
            'order_id': 'ord-auth-1',
            'club_id': 'club-a',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'primary@club-a.nl', 'secondary': 'secondary@club-a.nl'},
            'version': Decimal('1'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-10T08:00:00Z',
            'created_by': 'primary@club-a.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app

        token = create_jwt_token(email="primary@club-a.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'event_id': 'evt-pm2027'})
        response = get_order_app.lambda_handler(event, None)

        assert response['statusCode'] == 200

    @mock_aws
    def test_secondary_delegate_can_access(self):
        """Secondary delegate can access the order."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'secondary@club-a.nl', 'club-a')

        orders_table.put_item(Item={
            'order_id': 'ord-auth-2',
            'club_id': 'club-a',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'primary@club-a.nl', 'secondary': 'secondary@club-a.nl'},
            'version': Decimal('1'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-10T08:00:00Z',
            'created_by': 'primary@club-a.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app

        token = create_jwt_token(email="secondary@club-a.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'event_id': 'evt-pm2027'})
        response = get_order_app.lambda_handler(event, None)

        assert response['statusCode'] == 200

    @mock_aws
    def test_admin_can_access_any_club_order(self):
        """Admin with Webshop_Management + Regio_Pressmeet can access any club."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')

        orders_table.put_item(Item={
            'order_id': 'ord-auth-3',
            'club_id': 'club-other',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('100.00'),
            'total_paid': Decimal('0.00'),
            'items': [{'product_id': 'prod-meeting', 'item_fields_data': {'name': 'X', 'role': 'P'}, 'unit_price': Decimal('50.00')}],
            'delegates': {'primary': 'someone@club-other.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-12T09:00:00Z',
            'created_by': 'someone@club-other.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app

        admin_token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(
            token=admin_token,
            query_params={'event_id': 'evt-pm2027', 'club_id': 'club-other'},
        )
        response = get_order_app.lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['club_id'] == 'club-other'

    @mock_aws
    def test_cross_club_rejection(self):
        """A delegate from club-b cannot access club-a's order."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'intruder@club-b.nl', 'club-b')

        # Order belongs to club-a
        orders_table.put_item(Item={
            'order_id': 'ord-auth-4',
            'club_id': 'club-a',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'delegate@club-a.nl', 'secondary': None},
            'version': Decimal('1'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-10T08:00:00Z',
            'created_by': 'delegate@club-a.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_upsert_order.app as upsert_app

        # club-b delegate tries to edit club-a's order
        token = create_jwt_token(email="intruder@club-b.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(
            token=token,
            method='PUT',
            path_params={'id': 'ord-auth-4'},
            body={'items': [], 'version': 1},
        )
        response = upsert_app.lambda_handler(event, None)

        assert response['statusCode'] == 403, f"Expected 403, got {response['statusCode']}: {response['body']}"

    @mock_aws
    def test_user_without_presmeet_role_rejected(self):
        """User without Regio_Pressmeet or Regio_All is rejected."""
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app

        token = create_jwt_token(email="nopresmeet@club.nl", groups=["hdcnLeden"])
        event = make_event(token=token, query_params={'event_id': 'evt-pm2027'})
        response = get_order_app.lambda_handler(event, None)

        assert response['statusCode'] == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 29.6 Channel Rename Compatibility (old records without `channel` field)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChannelRenameCompatibility:
    """Test backward compatibility with records using old `tenant` field."""

    @mock_aws
    def test_get_order_reads_old_records_without_channel(self):
        """
        Old orders created with `tenant` field instead of `channel` should
        still be readable by handlers. The handler doesn't filter by channel,
        so old records in the GSI query should still be found.
        """
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'legacy@club-old.nl', 'club-old')

        # Insert an order with 'tenant' field (old format) — no 'channel' field
        orders_table.put_item(Item={
            'order_id': 'ord-legacy',
            'club_id': 'club-old',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'tenant': 'presmeet',  # Old field name
            # No 'channel' field!
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('100.00'),
            'total_paid': Decimal('0.00'),
            'items': [
                {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'Legacy User', 'role': 'President'}, 'unit_price': Decimal('50.00')},
            ],
            'delegates': {'primary': 'legacy@club-old.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2026-06-01T08:00:00Z',
            'updated_at': '2026-06-15T10:30:00Z',
            'created_by': 'legacy@club-old.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_get_order.app as get_order_app

        token = create_jwt_token(email="legacy@club-old.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token, query_params={'event_id': 'evt-pm2027'})
        response = get_order_app.lambda_handler(event, None)

        # Handler queries by event_id + club_id via GSI, not by channel
        # So old records should still be found
        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['order_id'] == 'ord-legacy'
        assert body['status'] == 'submitted'

    @mock_aws
    def test_admin_lock_handles_old_tenant_field(self):
        """
        admin_lock_orders bulk lock scans for 'channel' OR 'tenant' field
        when filtering by channel.
        """
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')

        # Create an order with old 'tenant' field
        orders_table.put_item(Item={
            'order_id': 'ord-old-tenant',
            'club_id': 'club-legacy',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'tenant': 'presmeet',  # Old field name
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'total_paid': Decimal('0.00'),
            'items': [{'product_id': 'prod-meeting', 'item_fields_data': {'name': 'Old', 'role': 'P'}, 'unit_price': Decimal('50.00')}],
            'delegates': {'primary': 'old@club.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-12T09:00:00Z',
        })

        # Create an order with new 'channel' field
        orders_table.put_item(Item={
            'order_id': 'ord-new-channel',
            'club_id': 'club-new',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'channel': 'presmeet',
            'status': 'submitted',
            'payment_status': 'unpaid',
            'total_amount': Decimal('50.00'),
            'total_paid': Decimal('0.00'),
            'items': [{'product_id': 'prod-meeting', 'item_fields_data': {'name': 'New', 'role': 'P'}, 'unit_price': Decimal('50.00')}],
            'delegates': {'primary': 'new@club.nl', 'secondary': None},
            'version': Decimal('2'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-12T09:00:00Z',
        })

        _clear_handler_modules()
        import handler.admin_lock_orders.app as lock_app

        admin_token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )

        # Bulk lock with channel filter — should find both old (tenant) and new (channel)
        event = make_event(
            token=admin_token,
            method='POST',
            body={'channel': 'presmeet'},
        )
        response = lock_app.lambda_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['locked_count'] == 2

    @mock_aws
    def test_upsert_works_on_old_record_without_channel(self):
        """
        Updating an old record (with tenant instead of channel) should still
        work via the upsert handler since it finds by order_id primary key.
        """
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        create_tables(dynamodb)

        orders_table = dynamodb.Table('Orders')
        members_table = dynamodb.Table('Members')

        seed_member(members_table, 'delegate@legacy.nl', 'club-legacy')

        # Old record with tenant field
        orders_table.put_item(Item={
            'order_id': 'ord-legacy-edit',
            'club_id': 'club-legacy',
            'event_id': 'evt-pm2027',
            'event_type': 'presmeet',
            'tenant': 'presmeet',  # Old field
            'status': 'draft',
            'payment_status': 'unpaid',
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'items': [],
            'delegates': {'primary': 'delegate@legacy.nl', 'secondary': None},
            'version': Decimal('1'),
            'status_history': [],
            'created_at': '2027-01-10T08:00:00Z',
            'updated_at': '2027-01-10T08:00:00Z',
            'created_by': 'delegate@legacy.nl',
        })

        _clear_handler_modules()
        import handler.presmeet_upsert_order.app as upsert_app

        token = create_jwt_token(email="delegate@legacy.nl", groups=["hdcnLeden", "Regio_Pressmeet"])
        items = [
            {'product_id': 'prod-meeting', 'variant_id': None, 'item_fields_data': {'name': 'Updated', 'role': 'Pres'}, 'unit_price': 50},
        ]
        event = make_event(
            token=token,
            method='PUT',
            path_params={'id': 'ord-legacy-edit'},
            body={'items': items, 'version': 1},
        )
        response = upsert_app.lambda_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}: {response['body']}"
        body = json.loads(response['body'])
        assert body['version'] == 2
        assert body['total_amount'] == 50.0
