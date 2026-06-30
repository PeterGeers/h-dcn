"""
Unit tests for send_delegate_invitation handler.

Tests:
- Successful email send (initial + resend)
- Auth: only primary delegate or admin can send
- Error: no pending_secondary_email
- Error: order not found
- Error: SES failure returns 500
"""

import json
import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

# --- Environment setup ---
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['EMAIL_TEMPLATES_BUCKET'] = 'hdcn-email-templates'
os.environ['SENDER_EMAIL'] = 'noreply@h-dcn.nl'
os.environ['PORTAL_BASE_URL'] = 'https://testportal.h-dcn.nl'
os.environ['ORGANIZATION_NAME'] = 'Harley-Davidson Club Nederland'
os.environ['ORGANIZATION_WEBSITE'] = 'https://testportal.h-dcn.nl'
os.environ['ORGANIZATION_EMAIL'] = 'webhulpje@h-dcn.nl'
os.environ['ORGANIZATION_SHORT_NAME'] = 'H-DCN'

# --- Handler loading ---
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'send_delegate_invitation', 'app.py')
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


# --- Auth patching ---
def _auth_patches():
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('primary@test.nl', ['event_participant'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _admin_auth_patches():
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['admin', 'events_crud'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


# --- Fixtures ---

@pytest.fixture
def tables_and_handler():
    """Create DynamoDB tables, seed data, and load handler inside mock_aws."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        # Create Orders table
        orders_table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create Events table
        events_table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Create Members table
        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed event
        events_table.put_item(Item={
            'event_id': 'evt-001',
            'name': 'H-DCN Treffen 2027',
            'slug': 'hdcn-treffen-2027',
            'registry_config': {
                'row_label': 'club',
                'claim_mode': 'first_come_first_served',
                'max_delegates_per_row': 2,
            },
            'registry_claims': {
                'club-abc': {
                    'member_id': 'member-001',
                    'email': 'primary@test.nl',
                    'name': 'Jan Delegaat',
                    'claimed_at': '2027-01-15T10:00:00Z',
                },
            },
        })

        # Seed order with pending invitation
        orders_table.put_item(Item={
            'order_id': 'order-001',
            'event_id': 'evt-001',
            'registry_row_id': 'club-abc',
            'registry_row_label': 'Riders Amsterdam',
            'registry_row_logo_url': None,
            'status': 'draft',
            'delegates': {
                'primary': 'primary@test.nl',
                'primary_member_id': 'member-001',
                'pending_secondary_email': 'invitee@test.nl',
            },
            'version': Decimal('1'),
        })

        # Seed order without pending invitation
        orders_table.put_item(Item={
            'order_id': 'order-002',
            'event_id': 'evt-001',
            'registry_row_id': 'club-xyz',
            'registry_row_label': 'Thunder Crew',
            'registry_row_logo_url': None,
            'status': 'draft',
            'delegates': {
                'primary': 'other@test.nl',
                'primary_member_id': 'member-002',
            },
            'version': Decimal('1'),
        })

        # Seed primary member
        members_table.put_item(Item={
            'member_id': 'member-001',
            'email': 'primary@test.nl',
            'name': 'Jan Delegaat',
            'registry_row_id': 'club-abc',
        })

        # Seed admin member
        members_table.put_item(Item={
            'member_id': 'member-admin',
            'email': 'admin@h-dcn.nl',
            'name': 'Admin User',
        })

        # Seed another member (not primary)
        members_table.put_item(Item={
            'member_id': 'member-002',
            'email': 'other@test.nl',
            'name': 'Other User',
            'registry_row_id': 'club-xyz',
        })

        # Create S3 bucket for email templates
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='hdcn-email-templates',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
        )

        # Upload a template
        template_html = """<!DOCTYPE html>
<html><head><title>H-DCN — Uitnodiging voor {{EVENT_NAME}}</title></head>
<body><p>{{INVITER_NAME}} nodigt je uit voor {{ROW_LABEL}}: {{ROW_NAME}} bij {{EVENT_NAME}}.</p>
<a href="{{REGISTRATION_LINK}}">Registreren</a></body></html>"""
        s3.put_object(
            Bucket='hdcn-email-templates',
            Key='templates/nl/delegate-invitation.html',
            Body=template_html.encode('utf-8'),
        )

        # Load handler inside mock context
        handler_module = _load_handler()

        yield {
            'orders_table': orders_table,
            'events_table': events_table,
            'members_table': members_table,
            'handler': handler_module,
        }


def _make_event(order_id: str, body: dict | None = None) -> dict:
    """Build a mock API Gateway event."""
    return {
        'httpMethod': 'POST',
        'pathParameters': {'id': order_id},
        'body': json.dumps(body) if body else '{}',
        'headers': {'Authorization': 'Bearer test-token'},
    }


# --- Tests ---

class TestSendDelegateInvitation:
    """Tests for the send_delegate_invitation handler."""

    def test_successful_send(self, tables_and_handler):
        """Primary delegate can send invitation email to pending secondary."""
        handler = tables_and_handler['handler']

        with _auth_patches():
            # Patch SES since moto SES requires verified identity
            with patch.object(handler.ses_client, 'send_email', return_value={'MessageId': 'msg-123'}):
                result = handler.lambda_handler(_make_event('order-001'), None)

        body = json.loads(result['body'])
        assert result['statusCode'] == 200
        assert 'invitee@test.nl' in body['message']
        assert body['recipient'] == 'invitee@test.nl'

    def test_successful_send_with_locale(self, tables_and_handler):
        """Locale is passed and accepted."""
        handler = tables_and_handler['handler']

        with _auth_patches():
            with patch.object(handler.ses_client, 'send_email', return_value={'MessageId': 'msg-456'}) as mock_send:
                result = handler.lambda_handler(
                    _make_event('order-001', {'locale': 'en'}), None
                )

        assert result['statusCode'] == 200
        # Verify SES was called
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]['Destination']['ToAddresses'] == ['invitee@test.nl']

    def test_resend_same_endpoint(self, tables_and_handler):
        """Calling the endpoint again (resend) works the same way."""
        handler = tables_and_handler['handler']

        with _auth_patches():
            with patch.object(handler.ses_client, 'send_email', return_value={'MessageId': 'msg-789'}):
                result1 = handler.lambda_handler(_make_event('order-001'), None)
                result2 = handler.lambda_handler(_make_event('order-001'), None)

        assert result1['statusCode'] == 200
        assert result2['statusCode'] == 200

    def test_no_pending_invitation(self, tables_and_handler):
        """Returns 400 when no pending_secondary_email exists."""
        handler = tables_and_handler['handler']

        # Use auth as 'other@test.nl' who is primary on order-002
        with patch.multiple(
            'app',
            extract_user_credentials=lambda event: ('other@test.nl', ['event_participant'], None),
            validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
            log_successful_access=lambda *a, **kw: None,
        ):
            result = handler.lambda_handler(_make_event('order-002'), None)

        body = json.loads(result['body'])
        assert result['statusCode'] == 400
        assert 'pending' in body.get('error', body.get('message', '')).lower()

    def test_order_not_found(self, tables_and_handler):
        """Returns 404 when order doesn't exist."""
        handler = tables_and_handler['handler']

        with _auth_patches():
            result = handler.lambda_handler(_make_event('nonexistent'), None)

        assert result['statusCode'] == 404

    def test_non_primary_non_admin_rejected(self, tables_and_handler):
        """Non-primary, non-admin user cannot send invitation email."""
        handler = tables_and_handler['handler']

        # Auth as someone who is NOT primary on order-001 and NOT admin
        with patch.multiple(
            'app',
            extract_user_credentials=lambda event: ('other@test.nl', ['event_participant'], None),
            validate_permissions_with_regions=lambda roles, perms, email, region: (False, None, {}),
            log_successful_access=lambda *a, **kw: None,
        ):
            result = handler.lambda_handler(_make_event('order-001'), None)

        assert result['statusCode'] == 403

    def test_admin_can_send(self, tables_and_handler):
        """Admin can send invitation email even if not primary delegate."""
        handler = tables_and_handler['handler']

        with _admin_auth_patches():
            with patch.object(handler.ses_client, 'send_email', return_value={'MessageId': 'msg-admin'}):
                result = handler.lambda_handler(_make_event('order-001'), None)

        body = json.loads(result['body'])
        assert result['statusCode'] == 200
        assert body['recipient'] == 'invitee@test.nl'

    def test_ses_failure_returns_500(self, tables_and_handler):
        """SES send failure returns 500 error."""
        handler = tables_and_handler['handler']
        from botocore.exceptions import ClientError

        ses_error = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email sending disabled'}},
            'SendEmail',
        )

        with _auth_patches():
            with patch.object(handler.ses_client, 'send_email', side_effect=ses_error):
                result = handler.lambda_handler(_make_event('order-001'), None)

        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'failed' in body.get('error', body.get('message', '')).lower()

    def test_options_request(self, tables_and_handler):
        """OPTIONS request returns CORS preflight response."""
        handler = tables_and_handler['handler']

        with patch('app.handle_options_request', return_value={'statusCode': 200, 'body': ''}):
            result = handler.lambda_handler(
                {'httpMethod': 'OPTIONS', 'pathParameters': {'id': 'order-001'}},
                None,
            )

        assert result['statusCode'] == 200


# =============================================================================
# Task 7.4 — Delegate email template context resolution tests
# Requirements: 7.1, 7.2, 7.3, 7.4
# =============================================================================


class TestResolveRowLabel:
    """Tests for _resolve_row_label() helper — Requirement 7.1."""

    def test_resolves_row_label_from_registry_config(self, tables_and_handler):
        """Should return row_label from event.registry_config.row_label."""
        handler = tables_and_handler['handler']
        event = {
            'registry_config': {'row_label': 'club', 'claim_mode': 'first_come_first_served'},
        }
        assert handler._resolve_row_label(event) == 'club'

    def test_resolves_team_label(self, tables_and_handler):
        """Should return 'team' when registry_config.row_label is 'team'."""
        handler = tables_and_handler['handler']
        event = {
            'registry_config': {'row_label': 'team'},
        }
        assert handler._resolve_row_label(event) == 'team'

    def test_resolves_school_label(self, tables_and_handler):
        """Should return 'school' when registry_config.row_label is 'school'."""
        handler = tables_and_handler['handler']
        event = {
            'registry_config': {'row_label': 'school'},
        }
        assert handler._resolve_row_label(event) == 'school'

    def test_fallback_to_group_when_row_label_empty(self, tables_and_handler):
        """Should fallback to 'group' when row_label is empty string."""
        handler = tables_and_handler['handler']
        event = {
            'registry_config': {'row_label': ''},
        }
        assert handler._resolve_row_label(event) == 'group'

    def test_fallback_to_group_when_row_label_absent(self, tables_and_handler):
        """Should fallback to 'group' when row_label key is absent."""
        handler = tables_and_handler['handler']
        event = {
            'registry_config': {'claim_mode': 'first_come_first_served'},
        }
        assert handler._resolve_row_label(event) == 'group'

    def test_fallback_to_group_when_registry_config_absent(self, tables_and_handler):
        """Should fallback to 'group' when registry_config is absent."""
        handler = tables_and_handler['handler']
        event = {}
        assert handler._resolve_row_label(event) == 'group'

    def test_fallback_to_group_when_registry_config_none(self, tables_and_handler):
        """Should fallback to 'group' when registry_config is None."""
        handler = tables_and_handler['handler']
        event = {'registry_config': None}
        assert handler._resolve_row_label(event) == 'group'


class TestResolveRowName:
    """Tests for _resolve_row_name() helper — Requirements 7.2, 7.4."""

    def test_resolves_from_order_registry_row_label(self, tables_and_handler):
        """Should return order.registry_row_label as first priority."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'club-abc', 'registry_row_label': 'Riders Amsterdam'}
        event = {'registry_claims': {}}
        assert handler._resolve_row_name(order, event) == 'Riders Amsterdam'

    def test_fallback_to_registry_claims_label(self, tables_and_handler):
        """Should fallback to event.registry_claims[row_id].label when order label absent."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'club-abc', 'registry_row_label': ''}
        event = {
            'registry_claims': {
                'club-abc': {'label': 'Claim Label', 'member_id': 'm-1'},
            },
        }
        assert handler._resolve_row_name(order, event) == 'Claim Label'

    def test_fallback_to_registry_row_id(self, tables_and_handler):
        """Should fallback to registry_row_id when no label available anywhere."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'club-abc', 'registry_row_label': ''}
        event = {'registry_claims': {}}
        assert handler._resolve_row_name(order, event) == 'club-abc'

    def test_fallback_empty_when_no_row_id(self, tables_and_handler):
        """Should return empty string when registry_row_id is also absent."""
        handler = tables_and_handler['handler']
        order = {}
        event = {'registry_claims': {}}
        assert handler._resolve_row_name(order, event) == ''

    def test_order_label_takes_priority_over_claims(self, tables_and_handler):
        """Order label should take priority even if claims has different label."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'club-abc', 'registry_row_label': 'Order Label'}
        event = {
            'registry_claims': {
                'club-abc': {'label': 'Claims Label'},
            },
        }
        assert handler._resolve_row_name(order, event) == 'Order Label'

    def test_claims_label_used_when_order_label_none(self, tables_and_handler):
        """Claims label used when order has registry_row_label missing (key not present)."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'club-abc'}
        event = {
            'registry_claims': {
                'club-abc': {'label': 'From Claims'},
            },
        }
        assert handler._resolve_row_name(order, event) == 'From Claims'

    def test_claims_with_empty_label_falls_through_to_row_id(self, tables_and_handler):
        """If claims entry has empty label, should fall through to registry_row_id."""
        handler = tables_and_handler['handler']
        order = {'registry_row_id': 'row-xyz', 'registry_row_label': ''}
        event = {
            'registry_claims': {
                'row-xyz': {'label': '', 'member_id': 'm-1'},
            },
        }
        assert handler._resolve_row_name(order, event) == 'row-xyz'
