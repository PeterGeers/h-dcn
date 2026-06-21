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
            'club_id': 'club-abc',
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
            'club_id': 'club-xyz',
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
            'club_id': 'club-abc',
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
            'club_id': 'club-xyz',
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
<body><p>{{INVITER_NAME}} nodigt je uit voor {{CLUB_NAME}} bij {{EVENT_NAME}}.</p>
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
