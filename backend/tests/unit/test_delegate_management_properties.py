"""
Property-Based Tests for Closed Community Booking: Delegate Management

Tests the core delegate management logic using Hypothesis.
Covers:
- Property 9: Delegate Invitation Limit Enforcement
- Property 10: Pending Delegate Email Normalization
- Property 11: Optimistic Locking

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

import os
import sys
import json
import importlib.util
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, note, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws

# --- Environment setup for tests ---

os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['EVENTS_TABLE_NAME'] = 'Events'
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['ORDERS_TABLE_NAME'] = 'Orders'
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'

# --- Load handler modules via importlib (per testing-backend.md steering) ---

_manage_delegates_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'manage_delegates', 'app.py'
    )
)

_update_order_items_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'update_order_items', 'app.py'
    )
)


def _load_manage_delegates():
    """Load manage_delegates handler module by file path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('manage_delegates_app', _manage_delegates_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_update_order_items():
    """Load update_order_items handler module by file path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('update_order_items_app', _update_order_items_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load handlers — extract functions for testing
_delegates_handler = _load_manage_delegates()
_count_current_delegates = _delegates_handler._count_current_delegates
_handle_invite = _delegates_handler._handle_invite

_order_items_handler = _load_update_order_items()


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for valid email local parts (at least 2 chars, no '@')
email_local_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), min_codepoint=48, max_codepoint=122),
    min_size=2,
    max_size=30,
).filter(lambda s: '@' not in s and len(s) >= 2)

email_domain_strategy = st.from_regex(r'[a-z]{2,10}\.[a-z]{2,4}', fullmatch=True)

email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}",
    email_local_strategy,
    email_domain_strategy,
)

# Strategy for event IDs
event_id_strategy = st.from_regex(r'evt_[a-z0-9]{6,12}', fullmatch=True)

# Strategy for order IDs
order_id_strategy = st.from_regex(r'ord_[a-z0-9]{8,12}', fullmatch=True)

# Strategy for member IDs (UUIDs)
member_id_strategy = st.from_regex(
    r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',
    fullmatch=True,
)

# Strategy for max_delegates_per_row (realistic values: 1-5)
max_delegates_strategy = st.integers(min_value=1, max_value=5)

# Strategy for version numbers
version_strategy = st.integers(min_value=1, max_value=100)


# =============================================================================
# Property 9: Delegate Invitation Limit Enforcement
# =============================================================================

class TestProperty9DelegateInvitationLimitEnforcement:
    """
    # Feature: closed-community-booking, Property 9: Delegate Invitation Limit Enforcement

    **Validates: Requirements 5.1, 5.2**

    For any order with a given number of current delegates (primary + secondary)
    and any registry_config.max_delegates_per_row value, a delegate invitation
    SHALL be accepted if and only if the current delegate count is strictly less
    than max_delegates_per_row. Self-invitation (email equals primary delegate
    email) SHALL always be rejected regardless of limit.
    """

    @given(max_delegates=max_delegates_strategy)
    @settings(max_examples=50)
    def test_count_delegates_primary_only(self, max_delegates: int):
        """
        **Validates: Requirements 5.1**

        When only a primary delegate exists (no secondary, no pending),
        the delegate count SHALL be 1.
        """
        delegates = {
            'primary': 'primary@example.com',
            'primary_member_id': 'member-001',
            'secondary_member_id': None,
            'secondary': None,
            'pending_secondary_email': None,
        }
        count = _count_current_delegates(delegates)
        assert count == 1, f"Expected 1 delegate, got {count}"

    @given(
        secondary_email=email_strategy,
        member_id=member_id_strategy,
    )
    @settings(max_examples=50)
    def test_count_delegates_with_linked_secondary(
        self, secondary_email: str, member_id: str
    ):
        """
        **Validates: Requirements 5.1**

        When a secondary delegate is linked, the count SHALL be 2.
        """
        delegates = {
            'primary': 'primary@example.com',
            'primary_member_id': 'member-000',
            'secondary_member_id': member_id,
            'secondary': secondary_email,
            'pending_secondary_email': None,
        }
        count = _count_current_delegates(delegates)
        assert count == 2, f"Expected 2 delegates, got {count}"

    @given(pending_email=email_strategy)
    @settings(max_examples=50)
    def test_count_delegates_with_pending_invitation(self, pending_email: str):
        """
        **Validates: Requirements 5.1**

        When a pending invitation exists, the count SHALL be 2
        (primary + pending counts as filled slot).
        """
        delegates = {
            'primary': 'primary@example.com',
            'primary_member_id': 'member-000',
            'secondary_member_id': None,
            'secondary': None,
            'pending_secondary_email': pending_email.lower(),
        }
        count = _count_current_delegates(delegates)
        assert count == 2, f"Expected 2 delegates, got {count}"

    @given(
        max_delegates=max_delegates_strategy,
        invite_email=email_strategy,
        event_id=event_id_strategy,
        order_id=order_id_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invitation_accepted_when_under_limit(
        self, max_delegates: int, invite_email: str,
        event_id: str, order_id: str,
    ):
        """
        **Validates: Requirements 5.1**

        A delegate invitation SHALL be accepted if the current delegate count
        is strictly less than max_delegates_per_row.
        """
        # Only test when limit > 1 (primary always occupies 1 slot)
        assume(max_delegates > 1)

        primary_email = 'primary@test-club.nl'
        # Ensure invite email is different from primary (not self-invite)
        assume(invite_email.lower() != primary_email.lower())

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            # Create Events table with registry_config
            events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            events_table.put_item(Item={
                'event_id': event_id,
                'registry_config': {'max_delegates_per_row': max_delegates},
            })

            # Create Orders table
            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Create an order with only primary delegate (count = 1)
            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': event_id,
                'status': 'draft',
                'version': 1,
                'delegates': {
                    'primary': primary_email,
                    'primary_member_id': 'member-primary',
                    'secondary_member_id': None,
                    'secondary': None,
                    'pending_secondary_email': None,
                },
            })

            # Rebind handler's table references
            _delegates_handler.events_table = events_table
            _delegates_handler.orders_table = orders_table

            # Call _handle_invite
            order = orders_table.get_item(Key={'order_id': order_id})['Item']
            delegates = order['delegates']
            body = {'action': 'invite', 'email': invite_email}

            response = _handle_invite(order, body, delegates, primary_email)
            status_code = response.get('statusCode', 200)

            # Should be accepted (200) since count(1) < max_delegates
            assert status_code == 200, (
                f"Invitation should be accepted when count(1) < max({max_delegates}), "
                f"got status {status_code}: {response.get('body', '')}"
            )

    @given(
        invite_email=email_strategy,
        event_id=event_id_strategy,
        order_id=order_id_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invitation_rejected_when_at_limit(
        self, invite_email: str, event_id: str, order_id: str,
    ):
        """
        **Validates: Requirements 5.1**

        A delegate invitation SHALL be rejected when the current delegate
        count equals max_delegates_per_row (limit reached).
        """
        primary_email = 'primary@test-club.nl'
        assume(invite_email.lower() != primary_email.lower())

        # max_delegates_per_row = 1 means only primary allowed, no secondary
        max_delegates = 1

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            events_table.put_item(Item={
                'event_id': event_id,
                'registry_config': {'max_delegates_per_row': max_delegates},
            })

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Order with only primary (count = 1), but limit is also 1
            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': event_id,
                'status': 'draft',
                'version': 1,
                'delegates': {
                    'primary': primary_email,
                    'primary_member_id': 'member-primary',
                    'secondary_member_id': None,
                    'secondary': None,
                    'pending_secondary_email': None,
                },
            })

            _delegates_handler.events_table = events_table
            _delegates_handler.orders_table = orders_table

            order = orders_table.get_item(Key={'order_id': order_id})['Item']
            delegates = order['delegates']
            body = {'action': 'invite', 'email': invite_email}

            response = _handle_invite(order, body, delegates, primary_email)
            status_code = response.get('statusCode', 200)

            # Should be rejected (400) since count(1) >= max_delegates(1)
            assert status_code == 400, (
                f"Invitation should be rejected when count(1) >= max({max_delegates}), "
                f"got status {status_code}: {response.get('body', '')}"
            )

    @given(
        primary_email=email_strategy,
        max_delegates=max_delegates_strategy,
        event_id=event_id_strategy,
        order_id=order_id_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_self_invitation_always_rejected(
        self, primary_email: str, max_delegates: int,
        event_id: str, order_id: str,
    ):
        """
        **Validates: Requirements 5.2**

        Self-invitation (email equals primary delegate email) SHALL always
        be rejected regardless of the max_delegates_per_row limit.
        """
        # Even with high limit, self-invite should fail
        assume(max_delegates >= 2)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            events_table.put_item(Item={
                'event_id': event_id,
                'registry_config': {'max_delegates_per_row': max_delegates},
            })

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': event_id,
                'status': 'draft',
                'version': 1,
                'delegates': {
                    'primary': primary_email.lower(),
                    'primary_member_id': 'member-primary',
                    'secondary_member_id': None,
                    'secondary': None,
                    'pending_secondary_email': None,
                },
            })

            _delegates_handler.events_table = events_table
            _delegates_handler.orders_table = orders_table

            order = orders_table.get_item(Key={'order_id': order_id})['Item']
            delegates = order['delegates']

            # Try self-invitation with exact same email
            body = {'action': 'invite', 'email': primary_email}
            response = _handle_invite(order, body, delegates, primary_email)
            status_code = response.get('statusCode', 200)

            assert status_code == 400, (
                f"Self-invitation should always be rejected (400), got {status_code}"
            )

            # Also try with different case
            body_upper = {'action': 'invite', 'email': primary_email.upper()}
            response_upper = _handle_invite(order, body_upper, delegates, primary_email)
            status_code_upper = response_upper.get('statusCode', 200)

            assert status_code_upper == 400, (
                f"Self-invitation (uppercase) should be rejected, got {status_code_upper}"
            )


# =============================================================================
# Property 10: Pending Delegate Email Normalization
# =============================================================================

class TestProperty10PendingDelegateEmailNormalization:
    """
    # Feature: closed-community-booking, Property 10: Pending Delegate Email Normalization

    **Validates: Requirements 5.3, 5.4**

    For any email address provided as a secondary delegate invitation, the stored
    pending_secondary_email SHALL equal the input lowercased. For any
    pending_secondary_email on an order and any onboarding email that matches
    case-insensitively, the auto-link SHALL trigger.
    """

    @given(
        invite_email=email_strategy,
        event_id=event_id_strategy,
        order_id=order_id_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_stored_email_is_always_lowercased(
        self, invite_email: str, event_id: str, order_id: str,
    ):
        """
        **Validates: Requirements 5.3**

        The stored pending_secondary_email SHALL equal the input lowercased,
        regardless of the case of the input email.
        """
        primary_email = 'owner@club.nl'
        assume(invite_email.lower() != primary_email.lower())

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            events_table.put_item(Item={
                'event_id': event_id,
                'registry_config': {'max_delegates_per_row': 3},
            })

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': event_id,
                'status': 'draft',
                'version': 1,
                'delegates': {
                    'primary': primary_email,
                    'primary_member_id': 'member-primary',
                    'secondary_member_id': None,
                    'secondary': None,
                    'pending_secondary_email': None,
                },
            })

            _delegates_handler.events_table = events_table
            _delegates_handler.orders_table = orders_table

            order = orders_table.get_item(Key={'order_id': order_id})['Item']
            delegates = order['delegates']

            # Send invitation with mixed-case email
            mixed_case_email = invite_email.swapcase()
            body = {'action': 'invite', 'email': mixed_case_email}

            response = _handle_invite(order, body, delegates, primary_email)
            status_code = response.get('statusCode', 200)

            assert status_code == 200, (
                f"Invitation should succeed, got {status_code}: {response.get('body', '')}"
            )

            # Verify stored pending email is lowercased
            updated_order = orders_table.get_item(Key={'order_id': order_id})['Item']
            stored_email = updated_order['delegates'].get('pending_secondary_email')

            assert stored_email == mixed_case_email.lower(), (
                f"Stored email '{stored_email}' should equal lowercased input "
                f"'{mixed_case_email.lower()}'"
            )

    @given(
        invite_email=email_strategy,
        event_id=event_id_strategy,
        order_id=order_id_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_case_insensitive_match_triggers_autolink(
        self, invite_email: str, event_id: str, order_id: str,
    ):
        """
        **Validates: Requirements 5.4**

        For any pending_secondary_email on an order and any onboarding email
        that matches case-insensitively, the auto-link SHALL trigger.

        We test this by verifying the stored email is lowercased, so that
        any case variant of the same email will match via case-insensitive
        comparison (email.lower() == pending_secondary_email).
        """
        primary_email = 'owner@club.nl'
        assume(invite_email.lower() != primary_email.lower())

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

            events_table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            events_table.put_item(Item={
                'event_id': event_id,
                'registry_config': {'max_delegates_per_row': 3},
            })

            orders_table = dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            orders_table.put_item(Item={
                'order_id': order_id,
                'event_id': event_id,
                'status': 'draft',
                'version': 1,
                'delegates': {
                    'primary': primary_email,
                    'primary_member_id': 'member-primary',
                    'secondary_member_id': None,
                    'secondary': None,
                    'pending_secondary_email': None,
                },
            })

            _delegates_handler.events_table = events_table
            _delegates_handler.orders_table = orders_table

            order = orders_table.get_item(Key={'order_id': order_id})['Item']
            delegates = order['delegates']
            body = {'action': 'invite', 'email': invite_email}

            response = _handle_invite(order, body, delegates, primary_email)
            assert response.get('statusCode', 200) == 200

            # Read stored pending email
            updated_order = orders_table.get_item(Key={'order_id': order_id})['Item']
            stored_pending = updated_order['delegates'].get('pending_secondary_email')

            # Verify auto-link would trigger for any case variant:
            # The onboard handler does: onboard_email.lower() == pending_secondary_email
            # Since stored_pending is already lowercased, any case variant matches.
            case_variants = [
                invite_email.upper(),
                invite_email.lower(),
                invite_email.swapcase(),
                invite_email.capitalize(),
            ]
            for variant in case_variants:
                assert variant.lower() == stored_pending, (
                    f"Auto-link should trigger: '{variant}'.lower() == '{stored_pending}'"
                )


# =============================================================================
# Property 11: Optimistic Locking
# =============================================================================

class TestProperty11OptimisticLocking:
    """
    # Feature: closed-community-booking, Property 11: Optimistic Locking

    **Validates: Requirements 5.5, 5.6**

    For any order with version V, a save request specifying version V SHALL
    succeed (and increment to V+1), while a save request specifying any
    version ≠ V SHALL be rejected with a version conflict error.
    """

    @given(
        order_id=order_id_strategy,
        version=version_strategy,
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_matching_version_succeeds_and_increments(
        self, order_id: str, version: int,
    ):
        """
        **Validates: Requirements 5.5**

        A save request specifying version V (matching stored version)
        SHALL succeed and increment the version to V+1.
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

            # Create order with specified version
            orders_table.put_item(Item={
                'order_id': order_id,
                'status': 'draft',
                'version': version,
                'user_email': 'user@test.nl',
                'items': [],
                'total_amount': Decimal('0'),
            })

            # Rebind handler's table references
            _order_items_handler.orders_table = orders_table
            _order_items_handler.producten_table = producten_table

            # Build a valid update request with matching version
            event = {
                'httpMethod': 'PUT',
                'pathParameters': {'id': order_id},
                'body': json.dumps({
                    'version': version,
                    'items': [],  # Empty items is valid for draft
                }),
                'headers': {'Authorization': 'Bearer test-token'},
            }

            # Patch auth to bypass permission checks
            with patch.object(
                _order_items_handler, 'extract_user_credentials',
                return_value=('user@test.nl', ['hdcnLeden'], None),
            ), patch.object(
                _order_items_handler, 'validate_permissions_with_regions',
                return_value=(False, None, {}),
            ), patch.object(
                _order_items_handler, 'log_successful_access',
                return_value=None,
            ):
                response = _order_items_handler.lambda_handler(event, None)

            status_code = response.get('statusCode', 500)
            assert status_code == 200, (
                f"Save with matching version {version} should succeed (200), "
                f"got {status_code}: {response.get('body', '')}"
            )

            # Verify version was incremented
            body = json.loads(response['body'])
            assert body['version'] == version + 1, (
                f"Version should increment from {version} to {version + 1}, "
                f"got {body['version']}"
            )

            # Double-check in DynamoDB
            stored = orders_table.get_item(Key={'order_id': order_id})['Item']
            assert int(stored['version']) == version + 1

    @given(
        order_id=order_id_strategy,
        stored_version=version_strategy,
        version_offset=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_mismatching_version_rejected_with_conflict(
        self, order_id: str, stored_version: int, version_offset: int,
    ):
        """
        **Validates: Requirements 5.6**

        A save request specifying any version ≠ V (where V is the stored
        version) SHALL be rejected with a version conflict error (HTTP 409).
        """
        # Create a version that does NOT match stored
        wrong_version = stored_version + version_offset

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

            orders_table.put_item(Item={
                'order_id': order_id,
                'status': 'draft',
                'version': stored_version,
                'user_email': 'user@test.nl',
                'items': [],
                'total_amount': Decimal('0'),
            })

            _order_items_handler.orders_table = orders_table
            _order_items_handler.producten_table = producten_table

            # Build request with WRONG version
            event = {
                'httpMethod': 'PUT',
                'pathParameters': {'id': order_id},
                'body': json.dumps({
                    'version': wrong_version,
                    'items': [],
                }),
                'headers': {'Authorization': 'Bearer test-token'},
            }

            with patch.object(
                _order_items_handler, 'extract_user_credentials',
                return_value=('user@test.nl', ['hdcnLeden'], None),
            ), patch.object(
                _order_items_handler, 'validate_permissions_with_regions',
                return_value=(False, None, {}),
            ), patch.object(
                _order_items_handler, 'log_successful_access',
                return_value=None,
            ):
                response = _order_items_handler.lambda_handler(event, None)

            status_code = response.get('statusCode', 500)
            assert status_code == 409, (
                f"Save with wrong version ({wrong_version} != stored {stored_version}) "
                f"should be rejected (409), got {status_code}: {response.get('body', '')}"
            )

            # Verify stored version is unchanged
            stored = orders_table.get_item(Key={'order_id': order_id})['Item']
            assert int(stored['version']) == stored_version, (
                f"Stored version should remain {stored_version}, got {stored['version']}"
            )

    @given(
        order_id=order_id_strategy,
        stored_version=st.integers(min_value=2, max_value=100),
    )
    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_lower_version_also_rejected(
        self, order_id: str, stored_version: int,
    ):
        """
        **Validates: Requirements 5.6**

        A save request with a version LOWER than the stored version
        SHALL also be rejected (stale client).
        """
        # Version lower than stored
        old_version = stored_version - 1

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

            orders_table.put_item(Item={
                'order_id': order_id,
                'status': 'draft',
                'version': stored_version,
                'user_email': 'user@test.nl',
                'items': [],
                'total_amount': Decimal('0'),
            })

            _order_items_handler.orders_table = orders_table
            _order_items_handler.producten_table = producten_table

            event = {
                'httpMethod': 'PUT',
                'pathParameters': {'id': order_id},
                'body': json.dumps({
                    'version': old_version,
                    'items': [],
                }),
                'headers': {'Authorization': 'Bearer test-token'},
            }

            with patch.object(
                _order_items_handler, 'extract_user_credentials',
                return_value=('user@test.nl', ['hdcnLeden'], None),
            ), patch.object(
                _order_items_handler, 'validate_permissions_with_regions',
                return_value=(False, None, {}),
            ), patch.object(
                _order_items_handler, 'log_successful_access',
                return_value=None,
            ):
                response = _order_items_handler.lambda_handler(event, None)

            status_code = response.get('statusCode', 500)
            assert status_code == 409, (
                f"Save with stale version ({old_version} < stored {stored_version}) "
                f"should be rejected (409), got {status_code}: {response.get('body', '')}"
            )
