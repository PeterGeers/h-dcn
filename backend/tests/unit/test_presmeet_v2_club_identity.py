"""
Property-based tests for PresMeet v2 club identity resolution.
Tests Property 12 and Property 13 from the PresMeet v2 design document.
"""

import sys
import os
import uuid
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Add the auth layer to the path so we can import shared.club_identity
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))


# --- Strategies ---

# Strategy for valid email addresses
email_local_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='._-'),
    min_size=1,
    max_size=20,
).filter(lambda s: len(s.strip()) > 0 and not s.startswith('.') and not s.endswith('.'))

email_domain_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-'),
    min_size=1,
    max_size=15,
).filter(lambda s: len(s.strip()) > 0 and not s.startswith('-') and not s.endswith('-'))

email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}.nl",
    local=email_local_strategy,
    domain=email_domain_strategy,
)

# Strategy for club_ids (non-empty alphanumeric + hyphens/underscores)
club_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
    min_size=1,
    max_size=30,
).filter(lambda s: len(s.strip()) > 0)

# Strategy for member statuses that are NOT 'presmeet'
non_presmeet_status_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20,
).filter(lambda s: s != 'presmeet' and len(s.strip()) > 0)


# --- Fixtures ---

@pytest.fixture
def members_table():
    """Create a mocked DynamoDB Members table and patch club_identity to use it."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
    os.environ['MEMBERS_TABLE_NAME'] = 'Members'

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[
                {'AttributeName': 'member_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'member_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='Members')

        # Patch the members_table in the club_identity module
        with patch('shared.club_identity.members_table', table):
            yield table


# --- Property 12: Club identity resolution ---

class TestProperty12ClubIdentityResolution:
    """Feature: presmeet, Property 12: Club identity resolution

    **Validates: Requirements 2.1, 11.4**
    """

    @given(
        email=email_strategy,
        club_id=club_id_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property12_presmeet_member_with_club_id_returns_club_id(
        self, members_table, email, club_id
    ):
        """Feature: presmeet, Property 12: Club identity resolution

        If a member exists with matching email AND status='presmeet' AND has a club_id,
        get_club_id(email) SHALL return that club_id.

        **Validates: Requirements 2.1, 11.4**
        """
        from shared.club_identity import get_club_id

        member_id = str(uuid.uuid4())

        # Insert a presmeet member with a club_id
        members_table.put_item(Item={
            'member_id': member_id,
            'email': email,
            'status': 'presmeet',
            'club_id': club_id,
        })

        result = get_club_id(email)
        assert result == club_id, (
            f"Expected get_club_id('{email}') to return '{club_id}', got '{result}'"
        )

        # Clean up for next hypothesis example
        members_table.delete_item(Key={'member_id': member_id})

    @given(
        email=email_strategy,
        other_email=email_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property12_no_matching_member_returns_none(
        self, members_table, email, other_email
    ):
        """Feature: presmeet, Property 12: Club identity resolution

        If no member matches the email, get_club_id(email) SHALL return None.

        **Validates: Requirements 2.1, 11.4**
        """
        from shared.club_identity import get_club_id

        # Ensure the two emails are different
        assume(email.lower() != other_email.lower())

        member_id = str(uuid.uuid4())

        # Insert a member with a DIFFERENT email
        members_table.put_item(Item={
            'member_id': member_id,
            'email': other_email,
            'status': 'presmeet',
            'club_id': 'some-club',
        })

        result = get_club_id(email)
        assert result is None, (
            f"Expected get_club_id('{email}') to return None when no matching member "
            f"exists, got '{result}'"
        )

        # Clean up
        members_table.delete_item(Key={'member_id': member_id})

    @given(
        email=email_strategy,
        club_id=club_id_strategy,
        status=non_presmeet_status_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property12_non_presmeet_status_returns_club_id(
        self, members_table, email, club_id, status
    ):
        """Feature: presmeet, Property 12: Club identity resolution

        get_club_id(email) returns club_id for any member who has one assigned,
        regardless of status. Access gating is handled at handler level by
        has_presmeet_access() checking Cognito groups.

        **Validates: Requirements 2.1, 11.4**
        """
        from shared.club_identity import get_club_id

        member_id = str(uuid.uuid4())

        # Insert a member with matching email and any status
        members_table.put_item(Item={
            'member_id': member_id,
            'email': email,
            'status': status,
            'club_id': club_id,
        })

        result = get_club_id(email)
        assert result == club_id, (
            f"Expected get_club_id('{email}') to return '{club_id}' "
            f"(club_id is returned regardless of status), got '{result}'"
        )

        # Clean up
        members_table.delete_item(Key={'member_id': member_id})

    @given(
        email=email_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property12_presmeet_member_without_club_id_returns_none(
        self, members_table, email
    ):
        """Feature: presmeet, Property 12: Club identity resolution

        If a member matches with status='presmeet' but has no club_id field,
        get_club_id(email) SHALL return None.

        **Validates: Requirements 2.1, 11.4**
        """
        from shared.club_identity import get_club_id

        member_id = str(uuid.uuid4())

        # Insert a presmeet member WITHOUT a club_id field
        members_table.put_item(Item={
            'member_id': member_id,
            'email': email,
            'status': 'presmeet',
            # No club_id field
        })

        result = get_club_id(email)
        assert result is None, (
            f"Expected get_club_id('{email}') to return None when member has no "
            f"club_id field, got '{result}'"
        )

        # Clean up
        members_table.delete_item(Key={'member_id': member_id})


# --- Property 13: Club assignment uniqueness ---

# Add handler path to sys.path for importing assign_club handler
_backend_path = os.path.join(os.path.dirname(__file__), '..', '..')
if _backend_path not in sys.path:
    sys.path.insert(1, os.path.abspath(_backend_path))

# Strategy for non-admin roles (no management role + region combo)
non_admin_roles_strategy = st.lists(
    st.sampled_from([
        'hdcnLeden', 'Regio_Pressmeet', 'events_read',
        'Leden_Read', 'Leden_CRUD',
    ]),
    min_size=1,
    max_size=4,
).filter(lambda roles: 'Regio_Pressmeet' in roles and not any(
    r in roles for r in ('Products_CRUD', 'Products_Read', 'Webshop_Management')
))

# Strategy for admin roles (always has management + region)
admin_roles_strategy = st.builds(
    lambda mgmt, extra: [mgmt, 'Regio_Pressmeet'] + extra,
    mgmt=st.sampled_from(['Products_CRUD', 'Products_Read', 'Webshop_Management']),
    extra=st.lists(
        st.sampled_from(['hdcnLeden', 'events_read', 'Leden_Read']),
        min_size=0,
        max_size=2,
    ),
)


class TestProperty13ClubAssignmentUniqueness:
    """Feature: presmeet, Property 13: Club assignment uniqueness

    Tests that non-admin cannot assign an already-assigned club (gets 409),
    admin CAN reassign, and after admin reassignment the previous member's
    club_id is cleared.

    **Validates: Requirements 2.4, 2.7**
    """

    @pytest.fixture(autouse=True)
    def setup_aws(self):
        """Set up mocked DynamoDB and S3 for each test."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        os.environ['REPORTS_BUCKET_NAME'] = 'h-dcn-reports'

        with mock_aws():
            # Create Members table
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            self.members_table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[
                    {'AttributeName': 'member_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'member_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            self.members_table.meta.client.get_waiter('table_exists').wait(
                TableName='Members'
            )

            # Create S3 bucket
            self.s3 = boto3.client('s3', region_name='eu-west-1')
            self.s3.create_bucket(
                Bucket='h-dcn-reports',
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'}
            )

            # Patch handler module's resources
            with patch('handler.assign_club.app.members_table', self.members_table), \
                 patch('handler.assign_club.app.s3', self.s3):
                yield

    def _put_club_registry(self, clubs):
        """Upload a club registry JSON to mock S3."""
        import json as _json
        registry = {
            'version': '1.0',
            'updated_at': '2025-01-01T00:00:00Z',
            'clubs': clubs,
        }
        self.s3.put_object(
            Bucket='h-dcn-reports',
            Key='presmeet/club_registry.json',
            Body=_json.dumps(registry),
            ContentType='application/json',
        )

    def _create_member(self, member_id, email, club_id=None):
        """Insert a presmeet member into DynamoDB."""
        item = {
            'member_id': member_id,
            'email': email,
            'status': 'presmeet',
            'lidmaatschap': 'overig',
            'tenant': 'presmeet',
        }
        if club_id:
            item['club_id'] = club_id
        self.members_table.put_item(Item=item)

    def _make_event(self, body, user_email='user@club.nl'):
        """Create a Lambda event for the assign_club handler."""
        import json as _json
        return {
            'httpMethod': 'POST',
            'body': _json.dumps(body) if body else None,
            'headers': {'Authorization': 'Bearer mock-token'},
            'queryStringParameters': None,
            'pathParameters': None,
        }

    def _mock_auth(self, user_email, user_roles):
        """Return patches that mock authentication for the handler."""
        return (
            patch(
                'handler.assign_club.app.extract_user_credentials',
                return_value=(user_email, user_roles, None),
            ),
            patch(
                'handler.assign_club.app.validate_permissions_with_regions',
                return_value=(True, None, {}),
            ),
            patch('handler.assign_club.app.log_successful_access'),
        )

    @given(
        club_id=club_id_strategy,
        requester_email=email_strategy,
        existing_email=email_strategy,
        user_roles=non_admin_roles_strategy,
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property13_non_admin_cannot_assign_already_assigned_club(
        self, club_id, requester_email, existing_email, user_roles
    ):
        """Feature: presmeet, Property 13: Club assignment uniqueness

        For any club that has assigned_member_id != None, a non-admin user
        SHALL receive a 409 Conflict response when attempting to assign that club.

        **Validates: Requirements 2.4, 2.7**
        """
        import json as _json
        from handler.assign_club.app import lambda_handler

        # Ensure requester is different from existing assignee
        assume(requester_email.lower() != existing_email.lower())

        existing_member_id = str(uuid.uuid4())
        requester_member_id = str(uuid.uuid4())

        # Set up: club already assigned to existing member
        self._put_club_registry([{
            'club_id': club_id,
            'club_name': f'Club {club_id}',
            'logo_url': None,
            'assigned_member_id': existing_member_id,
            'assigned_contact': existing_email,
            'assigned_at': '2025-01-01T00:00:00Z',
        }])

        # Create requester's member record
        self._create_member(requester_member_id, requester_email)
        # Create existing assignee's member record
        self._create_member(existing_member_id, existing_email, club_id=club_id)

        # Attempt assignment as non-admin
        event = self._make_event({'club_id': club_id}, user_email=requester_email)
        auth_patches = self._mock_auth(requester_email, user_roles)
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(event, None)

        assert response['statusCode'] == 409, (
            f"Expected 409 for non-admin assigning already-assigned club '{club_id}', "
            f"got {response['statusCode']}: {response.get('body')}"
        )

        # Verify existing member's club_id is unchanged
        existing_record = self.members_table.get_item(
            Key={'member_id': existing_member_id}
        )['Item']
        assert existing_record.get('club_id') == club_id

        # Clean up
        self.members_table.delete_item(Key={'member_id': existing_member_id})
        self.members_table.delete_item(Key={'member_id': requester_member_id})

    @given(
        club_id=club_id_strategy,
        admin_email=email_strategy,
        new_member_email=email_strategy,
        existing_email=email_strategy,
        admin_roles=admin_roles_strategy,
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property13_admin_can_reassign_already_assigned_club(
        self, club_id, admin_email, new_member_email, existing_email, admin_roles
    ):
        """Feature: presmeet, Property 13: Club assignment uniqueness

        For any club that has assigned_member_id != None, an admin user
        SHALL be able to reassign the club to a different member.

        **Validates: Requirements 2.4, 2.7**
        """
        import json as _json
        from handler.assign_club.app import lambda_handler

        # Ensure all emails are distinct
        assume(admin_email.lower() != new_member_email.lower())
        assume(admin_email.lower() != existing_email.lower())
        assume(new_member_email.lower() != existing_email.lower())

        existing_member_id = str(uuid.uuid4())
        new_member_id = str(uuid.uuid4())

        # Set up: club already assigned to existing member
        self._put_club_registry([{
            'club_id': club_id,
            'club_name': f'Club {club_id}',
            'logo_url': None,
            'assigned_member_id': existing_member_id,
            'assigned_contact': existing_email,
            'assigned_at': '2025-01-01T00:00:00Z',
        }])

        # Create members
        self._create_member(existing_member_id, existing_email, club_id=club_id)
        self._create_member(new_member_id, new_member_email)

        # Admin reassigns the club to new_member_email
        event = self._make_event(
            {'club_id': club_id, 'member_email': new_member_email},
            user_email=admin_email,
        )
        auth_patches = self._mock_auth(admin_email, admin_roles)
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200, (
            f"Expected 200 for admin reassigning club '{club_id}', "
            f"got {response['statusCode']}: {response.get('body')}"
        )

        # Verify new member now has the club_id
        new_record = self.members_table.get_item(
            Key={'member_id': new_member_id}
        )['Item']
        assert new_record.get('club_id') == club_id, (
            f"Expected new member to have club_id='{club_id}', "
            f"got '{new_record.get('club_id')}'"
        )

        # Clean up
        self.members_table.delete_item(Key={'member_id': existing_member_id})
        self.members_table.delete_item(Key={'member_id': new_member_id})

    @given(
        club_id=club_id_strategy,
        admin_email=email_strategy,
        new_member_email=email_strategy,
        existing_email=email_strategy,
        admin_roles=admin_roles_strategy,
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property13_admin_reassignment_clears_previous_member_club_id(
        self, club_id, admin_email, new_member_email, existing_email, admin_roles
    ):
        """Feature: presmeet, Property 13: Club assignment uniqueness

        After admin reassignment, the previous member's club_id SHALL be cleared.

        **Validates: Requirements 2.4, 2.7**
        """
        import json as _json
        from handler.assign_club.app import lambda_handler

        # Ensure all emails are distinct
        assume(admin_email.lower() != new_member_email.lower())
        assume(admin_email.lower() != existing_email.lower())
        assume(new_member_email.lower() != existing_email.lower())

        existing_member_id = str(uuid.uuid4())
        new_member_id = str(uuid.uuid4())

        # Set up: club already assigned to existing member
        self._put_club_registry([{
            'club_id': club_id,
            'club_name': f'Club {club_id}',
            'logo_url': None,
            'assigned_member_id': existing_member_id,
            'assigned_contact': existing_email,
            'assigned_at': '2025-01-01T00:00:00Z',
        }])

        # Create members - existing has the club_id assigned
        self._create_member(existing_member_id, existing_email, club_id=club_id)
        self._create_member(new_member_id, new_member_email)

        # Admin reassigns the club
        event = self._make_event(
            {'club_id': club_id, 'member_email': new_member_email},
            user_email=admin_email,
        )
        auth_patches = self._mock_auth(admin_email, admin_roles)
        with auth_patches[0], auth_patches[1], auth_patches[2]:
            response = lambda_handler(event, None)

        assert response['statusCode'] == 200, (
            f"Expected 200 for admin reassignment, got {response['statusCode']}"
        )

        # Verify previous member's club_id is cleared
        prev_record = self.members_table.get_item(
            Key={'member_id': existing_member_id}
        )['Item']
        assert 'club_id' not in prev_record, (
            f"Expected previous member's club_id to be cleared after admin "
            f"reassignment, but got club_id='{prev_record.get('club_id')}'"
        )

        # Clean up
        self.members_table.delete_item(Key={'member_id': existing_member_id})
        self.members_table.delete_item(Key={'member_id': new_member_id})
