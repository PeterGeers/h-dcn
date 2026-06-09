"""
Unit Tests for presmeet_submit_order Lambda Handler.

Tests the presmeet_submit_order handler:
- Authentication and authorization flows
- Rejection when order is locked
- Rejection when event is not open
- Fetching products for the event
- Fetching all event orders via GSI
- Calling validation module and handling errors
- On success: setting status=submitted, recording submitted_at
- On failure: returning all errors, keeping status as draft

Requirements: 3, 6
"""

import json
import pytest
import base64
from unittest.mock import patch, MagicMock
from decimal import Decimal
import sys
import os

# Ensure the layers path and backend root are on sys.path
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear any previously cached shared modules
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env vars before importing
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events')
os.environ.setdefault('PRODUCTEN_TABLE_NAME', 'Producten')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')

import handler.presmeet_submit_order.app as app
from handler.presmeet_submit_order.app import lambda_handler


def create_jwt_token(email="delegate@club.nl", groups=None):
    """Helper to create JWT tokens for testing."""
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
    signature = "test_signature"

    return f"{header}.{payload_encoded}.{signature}"


def make_event(token=None, path_params=None, method='POST'):
    """Helper to create an API Gateway event."""
    event = {
        'httpMethod': method,
        'headers': {},
        'pathParameters': path_params,
        'body': None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


# Sample data fixtures
SAMPLE_ORDER = {
    'order_id': 'ord-1',
    'club_id': 'club-123',
    'event_id': 'evt-1',
    'event_type': 'presmeet',
    'channel': 'presmeet',
    'status': 'draft',
    'payment_status': 'unpaid',
    'total_amount': Decimal('100.00'),
    'total_paid': Decimal('0.00'),
    'items': [
        {
            'product_id': 'prod-meeting',
            'variant_id': None,
            'item_fields_data': {'name': 'Jan de Vries', 'role': 'President', 'attend_party': 'yes'},
            'unit_price': Decimal('50.00'),
            'line_total': Decimal('50.00'),
        },
        {
            'product_id': 'prod-meeting',
            'variant_id': None,
            'item_fields_data': {'name': 'Piet Jansen', 'role': 'Secretary', 'attend_party': 'no'},
            'unit_price': Decimal('50.00'),
            'line_total': Decimal('50.00'),
        },
    ],
    'delegates': {'primary': 'delegate@club.nl', 'secondary': None},
    'version': 2,
    'status_history': [],
    'created_at': '2027-01-10T08:00:00+00:00',
    'updated_at': '2027-01-12T09:00:00+00:00',
    'created_by': 'delegate@club.nl',
}

SAMPLE_EVENT = {
    'event_id': 'evt-1',
    'event_type': 'presmeet',
    'name': 'PresMeet 2027',
    'status': 'open',
    'constraints': [
        {
            'key': 'max_meeting_attendees',
            'label': 'Maximum vergaderdeelnemers',
            'max': 150,
            'counting_rule': 'count_items_by_product',
            'product_id': 'prod-meeting',
        }
    ],
    'product_ids': ['prod-meeting', 'prod-party'],
}

SAMPLE_PRODUCTS = {
    'prod-meeting': {
        'product_id': 'prod-meeting',
        'name': 'Meeting Ticket PM2027',
        'channel': 'presmeet',
        'event_type': 'presmeet',
        'price': Decimal('50.00'),
        'order_item_fields': [
            {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
            {'id': 'role', 'label': 'Functie', 'type': 'text', 'required': True},
            {'id': 'attend_party', 'label': 'Feest bijwonen', 'type': 'select', 'required': True, 'options': ['yes', 'no']},
        ],
        'purchase_rules': {'min_per_club': 1, 'max_per_club': 3, 'order_mode': 'persistent'},
    },
    'prod-party': {
        'product_id': 'prod-party',
        'name': 'Party Ticket PM2027',
        'channel': 'presmeet',
        'event_type': 'presmeet',
        'price': Decimal('25.00'),
        'order_item_fields': [
            {'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True},
            {'id': 'person_type', 'label': 'Type', 'type': 'select', 'required': True, 'options': ['delegate', 'guest']},
        ],
        'purchase_rules': {'max_per_club': 13, 'order_mode': 'persistent'},
    },
}


class TestOptionsRequest:
    """Test CORS preflight handling."""

    def test_options_returns_200(self):
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200


class TestAuthentication:
    """Test authentication and authorization."""

    def test_missing_auth_header_returns_401(self):
        event = make_event(path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    def test_no_presmeet_access_returns_403(self):
        """User without Regio_Pressmeet or Regio_All should be rejected."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'PresMeet access required' in body['error']


class TestMissingOrderId:
    """Test missing order ID."""

    def test_missing_order_id_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params={})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_null_path_params_returns_400(self):
        token = create_jwt_token()
        event = make_event(token=token, path_params=None)
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400


class TestOrderNotFound:
    """Test order not found."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=None)
    def test_order_not_found_returns_404(self, mock_order, mock_club):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'nonexistent'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestAuthorizationChecks:
    """Test delegate and club-based authorization."""

    @patch.object(app, 'get_club_id', return_value=None)
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    def test_no_club_id_returns_403(self, mock_order, mock_club):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'club' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-other')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    def test_wrong_club_returns_403(self, mock_order, mock_club):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'different club' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    def test_non_delegate_returns_403(self, mock_order, mock_club):
        token = create_jwt_token(email="intruder@other.nl")
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'delegate' in body['error'].lower()


class TestLockedOrderRejection:
    """Test that locked orders are rejected."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    def test_locked_order_returns_403(self, mock_order, mock_club):
        locked_order = {**SAMPLE_ORDER, 'status': 'locked'}
        mock_order.return_value = locked_order

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'locked' in body['error'].lower()


class TestEventNotOpen:
    """Test rejection when event is not in open status."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event')
    def test_closed_event_returns_403(self, mock_event, mock_order, mock_club):
        mock_event.return_value = {**SAMPLE_EVENT, 'status': 'closed'}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not active' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event')
    def test_draft_event_returns_403(self, mock_event, mock_order, mock_club):
        mock_event.return_value = {**SAMPLE_EVENT, 'status': 'draft'}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'not active' in body['error'].lower()

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=None)
    def test_event_not_found_returns_404(self, mock_event, mock_order, mock_club):
        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'not found' in body['error'].lower()


class TestValidationFailure:
    """Test that validation errors are returned and status remains draft."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission')
    def test_validation_errors_return_400(
        self, mock_validate, mock_orders, mock_products, mock_event, mock_order, mock_club
    ):
        validation_errors = [
            {'item_index': 0, 'field': 'name', 'message': "Veld 'Naam' is verplicht"},
            {'item_index': None, 'field': 'prod-meeting', 'message': 'Maximum 3 items toegestaan'},
        ]
        mock_validate.return_value = validation_errors

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Validation failed' in body['error']
        assert 'errors' in body
        assert len(body['errors']) == 2
        assert body['error_count'] == 2

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission')
    def test_validation_errors_include_item_index_and_field(
        self, mock_validate, mock_orders, mock_products, mock_event, mock_order, mock_club
    ):
        validation_errors = [
            {'item_index': 1, 'field': 'role', 'message': "Veld 'Functie' is verplicht"},
        ]
        mock_validate.return_value = validation_errors

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        errors = body['errors']
        assert errors[0]['item_index'] == 1
        assert errors[0]['field'] == 'role'


class TestSubmissionSuccess:
    """Test successful submission flow."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_successful_submit_returns_200(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        # Simulate DynamoDB update response
        updated_order = {
            **SAMPLE_ORDER,
            'status': 'submitted',
            'submitted_at': '2027-01-15T10:30:00+00:00',
            'updated_at': '2027-01-15T10:30:00+00:00',
        }
        mock_update.return_value = {'Attributes': updated_order}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'submitted'
        assert 'submitted_at' in body

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_submit_records_status_history(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        mock_update.return_value = {'Attributes': {**SAMPLE_ORDER, 'status': 'submitted'}}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        lambda_handler(event, None)

        # Verify the update_item call contains status_history
        call_kwargs = mock_update.call_args[1]
        expr_values = call_kwargs['ExpressionAttributeValues']
        history_entry = expr_values[':history_entry'][0]
        assert history_entry['from'] == 'draft'
        assert history_entry['to'] == 'submitted'
        assert history_entry['by'] == 'delegate@club.nl'
        assert history_entry['source'] == 'delegate'

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_submit_sets_status_to_submitted(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        mock_update.return_value = {'Attributes': {**SAMPLE_ORDER, 'status': 'submitted'}}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        lambda_handler(event, None)

        call_kwargs = mock_update.call_args[1]
        expr_values = call_kwargs['ExpressionAttributeValues']
        assert expr_values[':submitted'] == 'submitted'


class TestValidationModuleIntegration:
    """Test that the validation module is called with correct parameters."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_validation_called_with_correct_args(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        mock_update.return_value = {'Attributes': {**SAMPLE_ORDER, 'status': 'submitted'}}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        lambda_handler(event, None)

        # Verify validate_submission was called with correct args
        mock_validate.assert_called_once_with(
            SAMPLE_ORDER, SAMPLE_EVENT, SAMPLE_PRODUCTS, []
        )


class TestSecondaryDelegateCanSubmit:
    """Test that secondary delegate can submit."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_secondary_delegate_submit_succeeds(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        order_with_secondary = {
            **SAMPLE_ORDER,
            'delegates': {'primary': 'jan@club.nl', 'secondary': 'piet@club.nl'},
        }
        mock_order.return_value = order_with_secondary
        mock_update.return_value = {'Attributes': {**order_with_secondary, 'status': 'submitted'}}

        token = create_jwt_token(email="piet@club.nl")
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200


class TestAdminCanSubmit:
    """Test that admin can submit any order."""

    @patch.object(app, 'is_presmeet_admin', return_value=True)
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_admin_submit_succeeds(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_admin
    ):
        mock_update.return_value = {'Attributes': {**SAMPLE_ORDER, 'status': 'submitted'}}

        token = create_jwt_token(
            email="admin@h-dcn.nl",
            groups=["Webshop_Management", "Regio_Pressmeet"]
        )
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200


class TestEventOrdersFetching:
    """Test that all event orders are fetched and passed to validation."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order', return_value=SAMPLE_ORDER)
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders')
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_other_event_orders_passed_to_validation(
        self, mock_update, mock_validate, mock_all_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        other_orders = [
            {'order_id': 'ord-2', 'club_id': 'club-456', 'status': 'submitted', 'items': []},
            {'order_id': 'ord-3', 'club_id': 'club-789', 'status': 'locked', 'items': []},
        ]
        mock_all_orders.return_value = other_orders
        mock_update.return_value = {'Attributes': {**SAMPLE_ORDER, 'status': 'submitted'}}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        lambda_handler(event, None)

        # Verify all_event_orders passed to validate_submission
        mock_validate.assert_called_once_with(
            SAMPLE_ORDER, SAMPLE_EVENT, SAMPLE_PRODUCTS, other_orders
        )


class TestResubmission:
    """Test submitting an already-submitted order (re-submission)."""

    @patch.object(app, 'get_club_id', return_value='club-123')
    @patch.object(app, '_get_order')
    @patch.object(app, '_get_event', return_value=SAMPLE_EVENT)
    @patch.object(app, '_get_event_products', return_value=SAMPLE_PRODUCTS)
    @patch.object(app, '_get_all_event_orders', return_value=[])
    @patch.object(app, 'validate_submission', return_value=[])
    @patch.object(app.orders_table, 'update_item')
    def test_submitted_order_can_be_resubmitted(
        self, mock_update, mock_validate, mock_orders, mock_products,
        mock_event, mock_order, mock_club
    ):
        """A submitted order (reverted to draft by editing) can be re-submitted."""
        submitted_then_edited = {**SAMPLE_ORDER, 'status': 'draft'}
        mock_order.return_value = submitted_then_edited
        mock_update.return_value = {'Attributes': {**submitted_then_edited, 'status': 'submitted'}}

        token = create_jwt_token()
        event = make_event(token=token, path_params={'id': 'ord-1'})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
