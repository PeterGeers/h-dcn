"""
Property-Based Tests for Closed Community Booking: Event Onboard Logic

Tests the core onboard logic for the event_onboard handler using Hypothesis.
Covers:
- Property 4: Case-Insensitive Email Matching
- Property 5: Atomic Row Claim with Data Integrity
- Property 6: One Claim Per User Per Event
- Property 7: Member Record Creation on Onboard (New User)
- Property 8: Existing Member Event Access Append

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 4.4
"""

import os
import sys
import importlib.util
from datetime import datetime, timezone

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

# --- Load handler module via importlib (per testing-backend.md steering) ---

_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'event_onboard', 'app.py'
    )
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('event_onboard_app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load handler — extract pure functions for testing
_handler = _load_handler()
email_matches_list = _handler.email_matches_list
atomic_claim_row = _handler.atomic_claim_row
check_existing_claim_for_user = _handler.check_existing_claim_for_user
create_member_record = _handler.create_member_record
update_member_event_access = _handler.update_member_event_access


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

# Strategy for row IDs
row_id_strategy = st.from_regex(r'row_[a-z0-9]{4,10}', fullmatch=True)

# Strategy for member IDs (UUIDs)
member_id_strategy = st.from_regex(r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}', fullmatch=True)

# Strategy for person names
name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'Zs'), min_codepoint=65, max_codepoint=122),
    min_size=2,
    max_size=50,
).filter(lambda s: s.strip() != '')


# =============================================================================
# Property 4: Case-Insensitive Email Matching
# =============================================================================

class TestProperty4CaseInsensitiveEmailMatching:
    """
    # Feature: closed-community-booking, Property 4: Case-Insensitive Email Matching

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

    For any email address and any list of allowed_emails, the matching function
    SHALL return true if and only if the email (compared case-insensitively)
    appears in the allowed_emails list.
    """

    @given(email=email_strategy)
    @settings(max_examples=100)
    def test_email_present_matches_regardless_of_case(self, email: str):
        """
        **Validates: Requirements 3.3, 3.4**

        When the email is in the allowed list (in any case variant),
        email_matches_list SHALL return True.
        """
        # Create allowed list with various case variants
        variants = [email.upper(), email.lower(), email.swapcase(), email]
        for variant in variants:
            allowed = [variant]
            assert email_matches_list(email, allowed) is True, (
                f"email_matches_list('{email}', {allowed}) should be True"
            )

    @given(
        email=email_strategy,
        other_emails=st.lists(email_strategy, min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_email_not_in_list_returns_false(self, email: str, other_emails: list):
        """
        **Validates: Requirements 3.3, 3.4**

        When the email is NOT in the allowed list (case-insensitively),
        email_matches_list SHALL return False.
        """
        # Ensure none of the other emails match (case-insensitively)
        assume(all(
            other.lower().strip() != email.lower().strip()
            for other in other_emails
        ))

        assert email_matches_list(email, other_emails) is False, (
            f"email_matches_list('{email}', {other_emails}) should be False"
        )

    @given(email=email_strategy)
    @settings(max_examples=100)
    def test_empty_list_always_returns_false(self, email: str):
        """
        **Validates: Requirements 3.3, 3.4**

        An empty allowed_emails list SHALL never match.
        """
        assert email_matches_list(email, []) is False

    @given(
        email=email_strategy,
        extra_emails=st.lists(email_strategy, min_size=0, max_size=5),
    )
    @settings(max_examples=100)
    def test_whitespace_trimming_does_not_affect_match(self, email: str, extra_emails: list):
        """
        **Validates: Requirements 3.3, 3.4**

        Emails with leading/trailing whitespace SHALL still match
        case-insensitively after trimming.
        """
        padded_email = f"  {email.upper()}  "
        allowed = extra_emails + [padded_email]
        assert email_matches_list(email, allowed) is True


# =============================================================================
# Property 5: Atomic Row Claim with Data Integrity
# =============================================================================

class TestProperty5AtomicRowClaimWithDataIntegrity:
    """
    # Feature: closed-community-booking, Property 5: Atomic Row Claim with Data Integrity

    **Validates: Requirements 3.1, 3.2, 3.5**

    For any event with registry_claims and any unclaimed row_id, a claim attempt
    SHALL either: (a) succeed and store a complete claim object containing
    member_id, email, name, and claimed_at (ISO 8601), or (b) fail with HTTP 409
    if the row was concurrently claimed.
    """

    @given(
        event_id=event_id_strategy,
        row_id=row_id_strategy,
        member_id=member_id_strategy,
        email=email_strategy,
        name=name_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_successful_claim_stores_complete_object(
        self, event_id: str, row_id: str, member_id: str, email: str, name: str
    ):
        """
        **Validates: Requirements 3.1, 3.5**

        (a) A successful claim stores member_id, email, name, and claimed_at
        (ISO 8601) in registry_claims[row_id].
        """
        with mock_aws():
            # Create Events table with registry_claims map
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Seed event with empty registry_claims
            table.put_item(Item={
                'event_id': event_id,
                'registry_claims': {},
            })

            # Rebind the handler's table reference to mocked table
            _handler.events_table = table

            # Attempt claim
            success, conflict_contact = atomic_claim_row(event_id, row_id, member_id, email, name)

            assert success is True, f"Claim should succeed for unclaimed row {row_id}"
            assert conflict_contact is None

            # Verify stored claim data
            response = table.get_item(Key={'event_id': event_id})
            item = response['Item']
            claims = item.get('registry_claims', {})
            claim = claims.get(row_id)

            assert claim is not None, f"Claim not found in registry_claims for {row_id}"
            assert claim['member_id'] == member_id
            assert claim['email'] == email.lower()
            assert claim['name'] == name

            # Verify claimed_at is ISO 8601
            claimed_at = claim['claimed_at']
            assert 'T' in claimed_at, f"claimed_at '{claimed_at}' not ISO 8601"
            # Should be parseable as ISO datetime
            datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))

    @given(
        event_id=event_id_strategy,
        row_id=row_id_strategy,
        member_id_1=member_id_strategy,
        member_id_2=member_id_strategy,
        email_1=email_strategy,
        email_2=email_strategy,
        name_1=name_strategy,
        name_2=name_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_concurrent_claim_returns_conflict(
        self, event_id: str, row_id: str,
        member_id_1: str, member_id_2: str,
        email_1: str, email_2: str,
        name_1: str, name_2: str,
    ):
        """
        **Validates: Requirements 3.2**

        (b) If the row was already claimed, a subsequent claim attempt SHALL
        fail and return a masked contact email of the existing claimant.
        """
        assume(member_id_1 != member_id_2)
        assume(email_1.lower() != email_2.lower())

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table.put_item(Item={
                'event_id': event_id,
                'registry_claims': {},
            })
            _handler.events_table = table

            # First claim succeeds
            success1, _ = atomic_claim_row(event_id, row_id, member_id_1, email_1, name_1)
            assert success1 is True

            # Second claim on same row fails
            success2, conflict_contact = atomic_claim_row(event_id, row_id, member_id_2, email_2, name_2)
            assert success2 is False
            assert conflict_contact is not None
            # Masked email should contain *** pattern
            assert '***@' in conflict_contact


# =============================================================================
# Property 6: One Claim Per User Per Event
# =============================================================================

class TestProperty6OneClaimPerUserPerEvent:
    """
    # Feature: closed-community-booking, Property 6: One Claim Per User Per Event

    **Validates: Requirements 3.6**

    For any event and any user who already holds a claim on one row,
    attempting to claim a different row in the same event SHALL be
    rejected with HTTP 409.
    """

    @given(
        event_id=event_id_strategy,
        row_id_1=row_id_strategy,
        row_id_2=row_id_strategy,
        email=email_strategy,
        member_id=member_id_strategy,
        name=name_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_user_with_existing_claim_is_detected(
        self, event_id: str, row_id_1: str, row_id_2: str,
        email: str, member_id: str, name: str,
    ):
        """
        **Validates: Requirements 3.6**

        check_existing_claim_for_user returns the existing row_id when the
        user already holds a claim, enabling 409 rejection.
        """
        assume(row_id_1 != row_id_2)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Seed event with an existing claim by this user
            table.put_item(Item={
                'event_id': event_id,
                'registry_claims': {
                    row_id_1: {
                        'member_id': member_id,
                        'email': email.lower(),
                        'name': name,
                        'claimed_at': '2025-01-15T10:00:00+00:00',
                    }
                },
            })
            _handler.events_table = table

            # Check for existing claim — should find the user
            existing_row = check_existing_claim_for_user(event_id, email)
            assert existing_row == row_id_1, (
                f"Expected existing claim on '{row_id_1}', got '{existing_row}'"
            )

    @given(
        event_id=event_id_strategy,
        row_id=row_id_strategy,
        email=email_strategy,
        member_id=member_id_strategy,
        name=name_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_case_insensitive_email_detection_in_claims(
        self, event_id: str, row_id: str,
        email: str, member_id: str, name: str,
    ):
        """
        **Validates: Requirements 3.6**

        The existing claim check SHALL match email case-insensitively,
        so User@Example.com and user@example.com are treated as the same user.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Store claim with lowercase email
            table.put_item(Item={
                'event_id': event_id,
                'registry_claims': {
                    row_id: {
                        'member_id': member_id,
                        'email': email.lower(),
                        'name': name,
                        'claimed_at': '2025-01-15T10:00:00+00:00',
                    }
                },
            })
            _handler.events_table = table

            # Check with uppercase variant — should still find
            existing_row = check_existing_claim_for_user(event_id, email.upper())
            assert existing_row == row_id, (
                f"Case-insensitive check failed: expected '{row_id}', got '{existing_row}'"
            )

    @given(
        event_id=event_id_strategy,
        email=email_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_no_existing_claim_returns_none(self, event_id: str, email: str):
        """
        **Validates: Requirements 3.6**

        When the user has no existing claim, check_existing_claim_for_user
        SHALL return None (allowing the claim to proceed).
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Events',
                KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Event with empty claims
            table.put_item(Item={
                'event_id': event_id,
                'registry_claims': {},
            })
            _handler.events_table = table

            existing_row = check_existing_claim_for_user(event_id, email)
            assert existing_row is None


# =============================================================================
# Property 7: Member Record Creation on Onboard (New User)
# =============================================================================

class TestProperty7MemberRecordCreation:
    """
    # Feature: closed-community-booking, Property 7: Member Record Creation on Onboard (New User)

    **Validates: Requirements 4.2**

    For any valid onboard request for a new user, the created Member record
    SHALL have: member_type equal to the event_id, club_id equal to the row_id,
    allowed_events containing exactly the event_id, email matching the input
    email, and name matching the input name.
    """

    @given(
        member_id=member_id_strategy,
        email=email_strategy,
        name=name_strategy,
        event_id=event_id_strategy,
        row_id=row_id_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_created_member_has_correct_fields(
        self, member_id: str, email: str, name: str, event_id: str, row_id: str
    ):
        """
        **Validates: Requirements 4.2**

        The created Member record has member_type=event_id, club_id=row_id,
        allowed_events=[event_id], email=input email (lowercased),
        and name=input name.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            _handler.members_table = table

            success, error = create_member_record(member_id, email, name, event_id, row_id)
            assert success is True, f"Member creation failed: {error}"

            # Verify stored record
            response = table.get_item(Key={'member_id': member_id})
            item = response['Item']

            assert item['member_type'] == event_id, (
                f"member_type should be '{event_id}', got '{item['member_type']}'"
            )
            assert item['club_id'] == row_id, (
                f"club_id should be '{row_id}', got '{item['club_id']}'"
            )
            assert item['allowed_events'] == [event_id], (
                f"allowed_events should be ['{event_id}'], got {item['allowed_events']}"
            )
            assert item['email'] == email.lower(), (
                f"email should be '{email.lower()}', got '{item['email']}'"
            )
            assert item['name'] == name, (
                f"name should be '{name}', got '{item['name']}'"
            )

    @given(
        member_id=member_id_strategy,
        email=email_strategy,
        name=name_strategy,
        event_id=event_id_strategy,
        row_id=row_id_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_created_member_has_timestamps(
        self, member_id: str, email: str, name: str, event_id: str, row_id: str
    ):
        """
        **Validates: Requirements 4.2**

        The created Member record SHALL have created_at and updated_at timestamps.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            _handler.members_table = table

            success, error = create_member_record(member_id, email, name, event_id, row_id)
            assert success is True

            response = table.get_item(Key={'member_id': member_id})
            item = response['Item']

            assert 'created_at' in item, "Missing created_at timestamp"
            assert 'updated_at' in item, "Missing updated_at timestamp"
            # Both should be ISO 8601 parseable
            datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
            datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))


# =============================================================================
# Property 8: Existing Member Event Access Append
# =============================================================================

class TestProperty8ExistingMemberEventAccessAppend:
    """
    # Feature: closed-community-booking, Property 8: Existing Member Event Access Append

    **Validates: Requirements 4.4**

    For any existing member record with arbitrary field values, onboarding
    for a new event SHALL: (a) append the event_id to allowed_events if not
    already present, and (b) leave all other fields completely unchanged.
    """

    @given(
        member_id=member_id_strategy,
        email=email_strategy,
        name=name_strategy,
        original_member_type=st.from_regex(r'[a-z_]{3,10}', fullmatch=True),
        original_club_id=row_id_strategy,
        existing_events=st.lists(event_id_strategy, min_size=0, max_size=3, unique=True),
        new_event_id=event_id_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_append_event_preserves_other_fields(
        self, member_id: str, email: str, name: str,
        original_member_type: str, original_club_id: str,
        existing_events: list, new_event_id: str,
    ):
        """
        **Validates: Requirements 4.4**

        (a) event_id is appended to allowed_events, (b) all other fields
        (member_type, club_id, name, email) remain completely unchanged.
        """
        # Ensure the new event isn't already in the list
        assume(new_event_id not in existing_events)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            _handler.members_table = table

            # Seed existing member with arbitrary fields
            original_item = {
                'member_id': member_id,
                'email': email.lower(),
                'name': name,
                'member_type': original_member_type,
                'club_id': original_club_id,
                'allowed_events': existing_events,
                'created_at': '2024-06-01T10:00:00+00:00',
                'updated_at': '2024-06-01T10:00:00+00:00',
            }
            table.put_item(Item=original_item)

            # Call update
            success, error = update_member_event_access(member_id, new_event_id)
            assert success is True, f"Update failed: {error}"

            # Verify the record
            response = table.get_item(Key={'member_id': member_id})
            item = response['Item']

            # (a) event_id appended to allowed_events
            assert new_event_id in item['allowed_events'], (
                f"'{new_event_id}' not found in allowed_events: {item['allowed_events']}"
            )
            # Original events still present
            for evt in existing_events:
                assert evt in item['allowed_events'], (
                    f"Original event '{evt}' missing from allowed_events"
                )

            # (b) Other fields unchanged
            assert item['member_type'] == original_member_type, (
                f"member_type changed from '{original_member_type}' to '{item['member_type']}'"
            )
            assert item['club_id'] == original_club_id, (
                f"club_id changed from '{original_club_id}' to '{item['club_id']}'"
            )
            assert item['name'] == name, (
                f"name changed from '{name}' to '{item['name']}'"
            )
            assert item['email'] == email.lower(), (
                f"email changed from '{email.lower()}' to '{item['email']}'"
            )
            assert item['created_at'] == '2024-06-01T10:00:00+00:00', (
                "created_at was modified"
            )

    @given(
        member_id=member_id_strategy,
        email=email_strategy,
        name=name_strategy,
        event_id=event_id_strategy,
    )
    @settings(max_examples=25, deadline=None)
    def test_idempotent_when_event_already_present(
        self, member_id: str, email: str, name: str, event_id: str,
    ):
        """
        **Validates: Requirements 4.4**

        If event_id is already in allowed_events, the function SHALL
        succeed without duplicating it.
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            _handler.members_table = table

            # Seed member that already has the event
            table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'name': name,
                'member_type': 'existing_type',
                'club_id': 'existing_club',
                'allowed_events': [event_id],
                'created_at': '2024-06-01T10:00:00+00:00',
                'updated_at': '2024-06-01T10:00:00+00:00',
            })

            # Call update with event_id already present
            success, error = update_member_event_access(member_id, event_id)
            assert success is True, f"Update failed: {error}"

            # Verify no duplication
            response = table.get_item(Key={'member_id': member_id})
            item = response['Item']
            count = item['allowed_events'].count(event_id)
            assert count == 1, (
                f"event_id appears {count} times in allowed_events (expected 1)"
            )
