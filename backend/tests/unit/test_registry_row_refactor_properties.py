"""
Property-Based Tests: Generic Registry Row Refactor

Test file for Hypothesis-based property tests covering the migration script
and related registry row refactor logic.
"""

import os
import sys
import json
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# Ensure AWS env vars are set for moto
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-west-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')

# Add scripts directory to path for migration script import
_scripts_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')
)
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

from migrate_club_to_registry_row import (
    migrate_orders,
    migrate_members,
    migrate_payments,
    validate_table,
    load_registry_from_s3,
    scan_all,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for generating a club_id (simple alphanumeric string)
club_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=10,
).filter(lambda s: s.strip() != '')

# Strategy for generating a registry row label (human-readable name)
label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != '')

# Strategy for optional logo URL
logo_url_strategy = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P')),
        min_size=5,
        max_size=50,
    ).map(lambda s: f"https://logos.example.com/{s}.png"),
)


@st.composite
def registry_entry_strategy(draw):
    """Generate a single registry entry (club in the S3 registry file)."""
    cid = draw(club_id_strategy)
    name = draw(label_strategy)
    logo = draw(logo_url_strategy)
    entry = {
        'club_id': cid,
        'club_name': name,
    }
    if logo:
        entry['logo_url'] = logo
    return entry


@st.composite
def registry_strategy(draw):
    """Generate a registry (list of 1-8 clubs with unique IDs)."""
    entries = draw(st.lists(
        registry_entry_strategy(),
        min_size=1,
        max_size=8,
        unique_by=lambda e: e['club_id'],
    ))
    return entries


@st.composite
def order_record_strategy(draw, registry_ids: list[str], include_already_migrated: bool = True):
    """Generate an Order record — either unmigrated (with club_id) or already migrated."""
    order_id = draw(st.uuids().map(str))
    is_already_migrated = draw(st.booleans()) if include_already_migrated else False

    if is_already_migrated:
        # Already migrated — has registry_row_id, no club_id
        row_id = draw(st.sampled_from(registry_ids)) if registry_ids else draw(club_id_strategy)
        return {
            'order_id': order_id,
            'registry_row_id': row_id,
            'registry_row_label': draw(label_strategy),
            'registry_row_logo_url': draw(logo_url_strategy),
            'status': 'submitted',
        }
    else:
        # Unmigrated — has club_id (might or might not be in registry)
        use_valid_id = draw(st.booleans())
        if use_valid_id and registry_ids:
            cid = draw(st.sampled_from(registry_ids))
        else:
            cid = draw(club_id_strategy)
        return {
            'order_id': order_id,
            'club_id': cid,
            'status': 'submitted',
        }


@st.composite
def member_record_strategy(draw, registry_ids: list[str], include_already_migrated: bool = True):
    """Generate a Member record — either unmigrated or already migrated."""
    member_id = draw(st.uuids().map(str))
    is_already_migrated = draw(st.booleans()) if include_already_migrated else False

    if is_already_migrated:
        row_id = draw(st.sampled_from(registry_ids)) if registry_ids else draw(club_id_strategy)
        return {
            'member_id': member_id,
            'registry_row_id': row_id,
            'email': f"user-{member_id[:8]}@test.nl",
        }
    else:
        use_valid_id = draw(st.booleans())
        if use_valid_id and registry_ids:
            cid = draw(st.sampled_from(registry_ids))
        else:
            cid = draw(club_id_strategy)
        return {
            'member_id': member_id,
            'club_id': cid,
            'email': f"user-{member_id[:8]}@test.nl",
        }


@st.composite
def payment_record_strategy(draw, registry_ids: list[str], include_already_migrated: bool = True):
    """Generate a Payment record — either unmigrated or already migrated."""
    payment_id = draw(st.uuids().map(str))
    is_already_migrated = draw(st.booleans()) if include_already_migrated else False

    if is_already_migrated:
        row_id = draw(st.sampled_from(registry_ids)) if registry_ids else draw(club_id_strategy)
        return {
            'payment_id': payment_id,
            'registry_row_id': row_id,
            'registry_row_label': draw(label_strategy),
            'registry_row_logo_url': draw(logo_url_strategy),
            'amount': draw(st.integers(min_value=1, max_value=9999)),
        }
    else:
        use_valid_id = draw(st.booleans())
        if use_valid_id and registry_ids:
            cid = draw(st.sampled_from(registry_ids))
        else:
            cid = draw(club_id_strategy)
        return {
            'payment_id': payment_id,
            'club_id': cid,
            'amount': draw(st.integers(min_value=1, max_value=9999)),
        }


@st.composite
def migration_scenario_strategy(draw):
    """Generate a complete migration scenario: registry + records for all 3 tables."""
    registry = draw(registry_strategy())
    registry_ids = [e['club_id'] for e in registry]

    orders = draw(st.lists(
        order_record_strategy(registry_ids),
        min_size=1,
        max_size=6,
        unique_by=lambda r: r['order_id'],
    ))
    members = draw(st.lists(
        member_record_strategy(registry_ids),
        min_size=1,
        max_size=6,
        unique_by=lambda r: r['member_id'],
    ))
    payments = draw(st.lists(
        payment_record_strategy(registry_ids),
        min_size=1,
        max_size=6,
        unique_by=lambda r: r['payment_id'],
    ))

    return {
        'registry': registry,
        'registry_ids': registry_ids,
        'orders': orders,
        'members': members,
        'payments': payments,
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _create_tables(dynamodb):
    """Create the DynamoDB tables needed for migration testing."""
    dynamodb.create_table(
        TableName='Orders-Test',
        KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    dynamodb.create_table(
        TableName='Members-Test',
        KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )
    dynamodb.create_table(
        TableName='Payments-Test',
        KeySchema=[{'AttributeName': 'payment_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'payment_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


def _build_registry_lookup(registry_entries: list[dict]) -> dict:
    """Build the registry lookup dict as the migration script expects it."""
    lookup = {}
    for entry in registry_entries:
        cid = entry['club_id']
        lookup[str(cid)] = {
            'club_id': str(cid),
            'club_name': entry.get('club_name', ''),
            'logo_url': entry.get('logo_url'),
        }
    return lookup


def _get_all_items(table) -> list[dict]:
    """Scan all items from a table."""
    items = []
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
    return items


def _normalize_items(items: list[dict]) -> list[dict]:
    """Normalize items for comparison (convert Decimal to int/float)."""
    normalized = []
    for item in items:
        norm = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                norm[key] = int(value) if value == int(value) else float(value)
            else:
                norm[key] = value
        normalized.append(norm)
    return sorted(normalized, key=lambda x: str(sorted(x.items())))


# =============================================================================
# Feature: generic-registry-row-refactor, Property 9: Migration idempotency
# =============================================================================


class TestProperty9MigrationIdempotency:
    """
    Property 9: Migration idempotency — running migration twice produces the
    same result as once; records with registry_row_id are never modified on
    subsequent runs.

    **Validates: Requirements 11.1, 11.3, 11.5**
    """

    @given(scenario=migration_scenario_strategy())
    @settings(max_examples=100, deadline=None)
    def test_migration_idempotency(self, scenario):
        """Running migration twice produces the same result as running once;
        records already containing registry_row_id are never modified."""
        registry_entries = scenario['registry']
        orders = scenario['orders']
        members = scenario['members']
        payments = scenario['payments']
        registry_lookup = _build_registry_lookup(registry_entries)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            orders_table = dynamodb.Table('Orders-Test')
            members_table = dynamodb.Table('Members-Test')
            payments_table = dynamodb.Table('Payments-Test')

            # Seed tables
            for order in orders:
                orders_table.put_item(Item=order)
            for member in members:
                members_table.put_item(Item=member)
            for payment in payments:
                payments_table.put_item(Item=payment)

            # --- First migration run ---
            migrate_orders(orders_table, registry_lookup, dry_run=False)
            migrate_members(members_table, registry_lookup, dry_run=False)
            migrate_payments(payments_table, registry_lookup, dry_run=False)

            # Capture state after first run
            state_after_first_orders = _normalize_items(_get_all_items(orders_table))
            state_after_first_members = _normalize_items(_get_all_items(members_table))
            state_after_first_payments = _normalize_items(_get_all_items(payments_table))

            # --- Second migration run ---
            stats_orders_2 = migrate_orders(orders_table, registry_lookup, dry_run=False)
            stats_members_2 = migrate_members(members_table, registry_lookup, dry_run=False)
            stats_payments_2 = migrate_payments(payments_table, registry_lookup, dry_run=False)

            # Capture state after second run
            state_after_second_orders = _normalize_items(_get_all_items(orders_table))
            state_after_second_members = _normalize_items(_get_all_items(members_table))
            state_after_second_payments = _normalize_items(_get_all_items(payments_table))

            # --- Assertions ---

            # 1. Table states are identical after first and second runs
            assert state_after_first_orders == state_after_second_orders, (
                "Orders table state differs between first and second migration run"
            )
            assert state_after_first_members == state_after_second_members, (
                "Members table state differs between first and second migration run"
            )
            assert state_after_first_payments == state_after_second_payments, (
                "Payments table state differs between first and second migration run"
            )

            # 2. Second run converts zero records (all already migrated or skipped)
            assert stats_orders_2['converted'] == 0, (
                f"Second run converted {stats_orders_2['converted']} orders (expected 0)"
            )
            assert stats_members_2['converted'] == 0, (
                f"Second run converted {stats_members_2['converted']} members (expected 0)"
            )
            assert stats_payments_2['converted'] == 0, (
                f"Second run converted {stats_payments_2['converted']} payments (expected 0)"
            )

            # 3. Second run has no errors
            assert stats_orders_2['errored'] == 0
            assert stats_members_2['errored'] == 0
            assert stats_payments_2['errored'] == 0

            note(
                f"Orders: first run state={len(state_after_first_orders)} items, "
                f"second run converted={stats_orders_2['converted']}"
            )

    @given(scenario=migration_scenario_strategy())
    @settings(max_examples=100, deadline=None)
    def test_already_migrated_records_never_modified(self, scenario):
        """Records that already have registry_row_id are never touched by migration."""
        registry_entries = scenario['registry']
        orders = scenario['orders']
        members = scenario['members']
        payments = scenario['payments']
        registry_lookup = _build_registry_lookup(registry_entries)

        # Identify records that are already migrated (have registry_row_id)
        already_migrated_orders = [o for o in orders if 'registry_row_id' in o]
        already_migrated_members = [m for m in members if 'registry_row_id' in m]
        already_migrated_payments = [p for p in payments if 'registry_row_id' in p]

        # Skip if no already-migrated records to test
        assume(
            len(already_migrated_orders) > 0
            or len(already_migrated_members) > 0
            or len(already_migrated_payments) > 0
        )

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            _create_tables(dynamodb)

            orders_table = dynamodb.Table('Orders-Test')
            members_table = dynamodb.Table('Members-Test')
            payments_table = dynamodb.Table('Payments-Test')

            # Seed tables
            for order in orders:
                orders_table.put_item(Item=order)
            for member in members:
                members_table.put_item(Item=member)
            for payment in payments:
                payments_table.put_item(Item=payment)

            # Capture state of already-migrated records before migration
            pre_migration_orders = {
                o['order_id']: dict(o) for o in already_migrated_orders
            }
            pre_migration_members = {
                m['member_id']: dict(m) for m in already_migrated_members
            }
            pre_migration_payments = {
                p['payment_id']: dict(p) for p in already_migrated_payments
            }

            # Run migration
            migrate_orders(orders_table, registry_lookup, dry_run=False)
            migrate_members(members_table, registry_lookup, dry_run=False)
            migrate_payments(payments_table, registry_lookup, dry_run=False)

            # Check that already-migrated records were not modified
            all_orders_after = {
                item['order_id']: item for item in _get_all_items(orders_table)
            }
            all_members_after = {
                item['member_id']: item for item in _get_all_items(members_table)
            }
            all_payments_after = {
                item['payment_id']: item for item in _get_all_items(payments_table)
            }

            for oid, original in pre_migration_orders.items():
                after = all_orders_after.get(oid)
                assert after is not None, f"Order {oid} disappeared after migration"
                # Compare all fields — they should be identical
                for key, value in original.items():
                    assert key in after, (
                        f"Order {oid}: field '{key}' missing after migration"
                    )
                    after_val = after[key]
                    # Normalize Decimal for comparison
                    if isinstance(after_val, Decimal):
                        after_val = int(after_val) if after_val == int(after_val) else float(after_val)
                    if isinstance(value, Decimal):
                        value = int(value) if value == int(value) else float(value)
                    assert after_val == value, (
                        f"Order {oid}: field '{key}' changed from {value!r} to {after_val!r}"
                    )

            for mid, original in pre_migration_members.items():
                after = all_members_after.get(mid)
                assert after is not None, f"Member {mid} disappeared after migration"
                for key, value in original.items():
                    assert key in after, (
                        f"Member {mid}: field '{key}' missing after migration"
                    )
                    after_val = after[key]
                    if isinstance(after_val, Decimal):
                        after_val = int(after_val) if after_val == int(after_val) else float(after_val)
                    if isinstance(value, Decimal):
                        value = int(value) if value == int(value) else float(value)
                    assert after_val == value, (
                        f"Member {mid}: field '{key}' changed from {value!r} to {after_val!r}"
                    )

            for pid, original in pre_migration_payments.items():
                after = all_payments_after.get(pid)
                assert after is not None, f"Payment {pid} disappeared after migration"
                for key, value in original.items():
                    assert key in after, (
                        f"Payment {pid}: field '{key}' missing after migration"
                    )
                    after_val = after[key]
                    if isinstance(after_val, Decimal):
                        after_val = int(after_val) if after_val == int(after_val) else float(after_val)
                    if isinstance(value, Decimal):
                        value = int(value) if value == int(value) else float(value)
                    assert after_val == value, (
                        f"Payment {pid}: field '{key}' changed from {value!r} to {after_val!r}"
                    )

            note(
                f"Tested {len(pre_migration_orders)} pre-migrated orders, "
                f"{len(pre_migration_members)} members, "
                f"{len(pre_migration_payments)} payments"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 10: Migration validation correctness
# =============================================================================


class TestProperty10MigrationValidationCorrectness:
    """
    Property 10: Migration validation correctness — validate_table() reports pass
    iff every record has registry_row_id and no record has club_id; otherwise
    reports fail with non-compliant record IDs.

    **Validates: Requirements 11.7**
    """

    @given(data=st.data())
    @settings(max_examples=100, deadline=None)
    def test_validate_reports_pass_when_all_compliant(self, data):
        """validate_table passes when all records have registry_row_id and no club_id."""
        # Generate records that are fully compliant (migrated)
        num_records = data.draw(st.integers(min_value=1, max_value=10))
        records = []
        for _ in range(num_records):
            record_id = data.draw(st.uuids().map(str))
            records.append({
                'order_id': record_id,
                'registry_row_id': data.draw(club_id_strategy),
                'registry_row_label': data.draw(label_strategy),
                'status': 'submitted',
            })

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='ValidateTest-Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table = dynamodb.Table('ValidateTest-Orders')

            for record in records:
                table.put_item(Item=record)

            result = validate_table(table, 'order_id', 'Orders')

            assert result['passed'] is True, (
                f"Expected pass but got fail: {result['non_compliant']}"
            )
            assert result['total_checked'] == num_records
            assert result['non_compliant'] == []

    @given(data=st.data())
    @settings(max_examples=100, deadline=None)
    def test_validate_reports_fail_when_missing_registry_row_id(self, data):
        """validate_table fails when any record is missing registry_row_id."""
        # Generate a mix: some compliant, at least one missing registry_row_id
        num_compliant = data.draw(st.integers(min_value=0, max_value=5))
        num_non_compliant = data.draw(st.integers(min_value=1, max_value=5))

        records = []
        non_compliant_ids = []

        for _ in range(num_compliant):
            record_id = data.draw(st.uuids().map(str))
            records.append({
                'order_id': record_id,
                'registry_row_id': data.draw(club_id_strategy),
                'status': 'submitted',
            })

        for _ in range(num_non_compliant):
            record_id = data.draw(st.uuids().map(str))
            # Non-compliant: missing registry_row_id
            has_club_id = data.draw(st.booleans())
            record = {
                'order_id': record_id,
                'status': 'submitted',
            }
            if has_club_id:
                record['club_id'] = data.draw(club_id_strategy)
            records.append(record)
            non_compliant_ids.append(record_id)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='ValidateTest-Orders2',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table = dynamodb.Table('ValidateTest-Orders2')

            for record in records:
                table.put_item(Item=record)

            result = validate_table(table, 'order_id', 'Orders')

            assert result['passed'] is False, (
                f"Expected fail but got pass (non-compliant records: {non_compliant_ids})"
            )
            assert result['total_checked'] == len(records)
            # Every non-compliant record ID should appear in the results
            reported_ids = [entry.split('/')[1].split(' ')[0] for entry in result['non_compliant']]
            for nc_id in non_compliant_ids:
                assert any(nc_id in entry for entry in result['non_compliant']), (
                    f"Non-compliant record {nc_id} not reported. "
                    f"Reported: {result['non_compliant']}"
                )

    @given(data=st.data())
    @settings(max_examples=100, deadline=None)
    def test_validate_reports_fail_when_club_id_still_present(self, data):
        """validate_table fails when any record still has club_id (even if registry_row_id present)."""
        num_records = data.draw(st.integers(min_value=1, max_value=8))
        records = []
        non_compliant_ids = []

        for _ in range(num_records):
            record_id = data.draw(st.uuids().map(str))
            # Has BOTH registry_row_id AND club_id — still non-compliant
            records.append({
                'order_id': record_id,
                'registry_row_id': data.draw(club_id_strategy),
                'club_id': data.draw(club_id_strategy),
                'status': 'submitted',
            })
            non_compliant_ids.append(record_id)

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='ValidateTest-Orders3',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table = dynamodb.Table('ValidateTest-Orders3')

            for record in records:
                table.put_item(Item=record)

            result = validate_table(table, 'order_id', 'Orders')

            assert result['passed'] is False, (
                "Expected fail but got pass — records with club_id should be non-compliant"
            )
            assert result['total_checked'] == num_records
            # All records should be non-compliant
            assert len(result['non_compliant']) == num_records, (
                f"Expected {num_records} non-compliant, got {len(result['non_compliant'])}"
            )
            # Each non-compliant entry should mention "still has club_id"
            for entry in result['non_compliant']:
                assert 'club_id' in entry, (
                    f"Non-compliant entry should mention club_id: {entry}"
                )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 3: get_registry_row_id resolves correctly
# =============================================================================

# Path to the event_access module under test
_event_access_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python', 'shared', 'event_access.py'
    )
)

# Ensure MEMBERS_TABLE_NAME is set for the module
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')


def _load_event_access():
    """Load event_access module by file path using importlib.util (inside mock_aws context)."""
    import importlib.util
    module_name = 'shared.event_access'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _event_access_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Strategies for Property 3
_email_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=3,
    max_size=12,
).map(lambda s: f"{s.lower()}@test.nl")

_registry_row_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() != '')


class TestProperty3GetRegistryRowIdResolvesCorrectly:
    """
    Property 3: get_registry_row_id resolves correctly — for any member with
    email and registry_row_id, calling the function returns that value;
    if field absent, returns None.

    **Validates: Requirements 2.3**
    """

    @given(
        email=_email_strategy,
        registry_row_id=_registry_row_id_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_returns_registry_row_id_when_present(self, email, registry_row_id):
        """For any member with email and registry_row_id, calling get_registry_row_id
        returns that member's registry_row_id value."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table = dynamodb.Table('Members')

            # Insert a member with email and registry_row_id
            member_id = f"member-{hash(email) % 99999:05d}"
            table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'registry_row_id': registry_row_id,
            })

            # Load module inside mock context
            module = _load_event_access()

            result = module.get_registry_row_id(email)
            assert result == registry_row_id, (
                f"Expected '{registry_row_id}' for email '{email}', got '{result}'"
            )

    @given(
        email=_email_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_returns_none_when_registry_row_id_absent(self, email):
        """For any member without registry_row_id field, calling get_registry_row_id
        returns None."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            table = dynamodb.Table('Members')

            # Insert a member WITHOUT registry_row_id
            member_id = f"member-{hash(email) % 99999:05d}"
            table.put_item(Item={
                'member_id': member_id,
                'email': email.lower(),
                'name': 'Test User',
            })

            # Load module inside mock context
            module = _load_event_access()

            result = module.get_registry_row_id(email)
            assert result is None, (
                f"Expected None for email '{email}' (no registry_row_id field), got '{result}'"
            )

    @given(
        email=_email_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_returns_none_when_email_not_found(self, email):
        """For any email not in the Members table, calling get_registry_row_id
        returns None."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='Members',
                KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'member_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )
            # Table is empty — no members at all

            # Load module inside mock context
            module = _load_event_access()

            result = module.get_registry_row_id(email)
            assert result is None, (
                f"Expected None for non-existent email '{email}', got '{result}'"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 4: Delegate assignment validates registry_row_id match
# =============================================================================


def _validate_delegate_registry_row_match(
    order_registry_row_id: str | None,
    target_registry_row_id: str | None,
) -> bool:
    """
    Pure function extracting the delegate registry_row_id validation logic
    from manage_delegates/app.py (_handle_add).

    Returns True if the delegate assignment is accepted, False if rejected.

    Logic (from the handler):
      - If order has a registry_row_id AND target's registry_row_id differs → reject
      - Otherwise → accept
    """
    if order_registry_row_id and target_registry_row_id != order_registry_row_id:
        return False
    return True


# Strategy for generating non-empty registry_row_id values
_delegate_row_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() != '')


class TestProperty4DelegateAssignmentValidatesRegistryRowIdMatch:
    """
    Property 4: Delegate assignment validates registry_row_id match — accepted
    iff order.registry_row_id == member.registry_row_id; rejected otherwise.

    **Validates: Requirements 2.5**
    """

    @given(
        registry_row_id=_delegate_row_id_strategy,
    )
    @settings(max_examples=100)
    def test_accepted_when_registry_row_ids_match(self, registry_row_id):
        """Delegate assignment is accepted when order.registry_row_id == member.registry_row_id."""
        result = _validate_delegate_registry_row_match(
            order_registry_row_id=registry_row_id,
            target_registry_row_id=registry_row_id,
        )
        assert result is True, (
            f"Expected accepted for matching registry_row_id='{registry_row_id}', got rejected"
        )

    @given(
        order_row_id=_delegate_row_id_strategy,
        target_row_id=_delegate_row_id_strategy,
    )
    @settings(max_examples=100)
    def test_rejected_when_registry_row_ids_differ(self, order_row_id, target_row_id):
        """Delegate assignment is rejected when order.registry_row_id != member.registry_row_id."""
        assume(order_row_id != target_row_id)

        result = _validate_delegate_registry_row_match(
            order_registry_row_id=order_row_id,
            target_registry_row_id=target_row_id,
        )
        assert result is False, (
            f"Expected rejected for order_row_id='{order_row_id}' != "
            f"target_row_id='{target_row_id}', got accepted"
        )

    @given(
        target_row_id=st.one_of(st.none(), _delegate_row_id_strategy),
    )
    @settings(max_examples=100)
    def test_accepted_when_order_has_no_registry_row_id(self, target_row_id):
        """When order has no registry_row_id (None/empty), delegate assignment is always accepted
        (validation only applies to row-scoped orders)."""
        # order_registry_row_id is None → no row-scope check applies
        result = _validate_delegate_registry_row_match(
            order_registry_row_id=None,
            target_registry_row_id=target_row_id,
        )
        assert result is True, (
            f"Expected accepted when order has no registry_row_id, got rejected "
            f"(target_row_id={target_row_id!r})"
        )

    @given(
        order_row_id=_delegate_row_id_strategy,
    )
    @settings(max_examples=100)
    def test_rejected_when_target_has_no_registry_row_id(self, order_row_id):
        """When order has a registry_row_id but target member has None, assignment is rejected."""
        result = _validate_delegate_registry_row_match(
            order_registry_row_id=order_row_id,
            target_registry_row_id=None,
        )
        assert result is False, (
            f"Expected rejected when order has registry_row_id='{order_row_id}' "
            f"but target has None, got accepted"
        )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 1: Order creation resolves registry row data from S3
# =============================================================================

# Path to the get_order handler
_get_order_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'get_order', 'app.py')
)

# Ensure env vars for get_order handler
os.environ.setdefault('ORDERS_TABLE_NAME', 'Orders')
os.environ.setdefault('EVENTS_TABLE_NAME', 'Events')
os.environ.setdefault('REGISTRY_BUCKET_NAME', 'h-dcn-data-test')


def _load_get_order_handler():
    """Load get_order handler module by file path using importlib.util."""
    import importlib.util
    module_name = 'get_order_app'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _get_order_handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Strategies for Property 1
_row_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=15,
).filter(lambda s: s.strip() != '')

_row_label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != '')

_row_logo_url_strategy = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=3,
        max_size=20,
    ).map(lambda s: f"https://logos.example.com/{s}.png"),
)

_s3_path_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=3,
    max_size=15,
).map(lambda s: f"registries/{s}.json")


@st.composite
def registry_rows_with_target_strategy(draw):
    """Generate S3 registry data containing a target row and possibly other rows."""
    target_row_id = draw(_row_id_strategy)
    target_label = draw(_row_label_strategy)
    target_logo_url = draw(_row_logo_url_strategy)

    # Build the target row
    target_row = {'row_id': target_row_id, 'label': target_label}
    if target_logo_url is not None:
        target_row['logo_url'] = target_logo_url

    # Generate additional rows (0-5 others)
    other_rows = draw(st.lists(
        st.fixed_dictionaries({
            'row_id': _row_id_strategy,
            'label': _row_label_strategy,
        }),
        min_size=0,
        max_size=5,
    ).filter(lambda rows: all(r['row_id'] != target_row_id for r in rows)))

    # Combine: insert target at random position
    all_rows = other_rows + [target_row]

    s3_path = draw(_s3_path_strategy)

    return {
        'target_row_id': target_row_id,
        'target_label': target_label,
        'target_logo_url': target_logo_url,
        's3_path': s3_path,
        'registry_data': {'rows': all_rows},
    }


class TestProperty1OrderCreationResolvesRegistryRowDataFromS3:
    """
    Property 1: Order creation resolves registry row data from S3 — for any
    member with registry_row_id, creating a row-scoped order resolves
    label/logo from S3 and stores all three fields.

    **Validates: Requirements 1.1**
    """

    @given(scenario=registry_rows_with_target_strategy())
    @settings(max_examples=100, deadline=None)
    def test_resolve_registry_row_data_returns_correct_label_and_logo(self, scenario):
        """_resolve_registry_row_data resolves correct label and logo_url from S3
        for any valid row_id present in the registry."""
        target_row_id = scenario['target_row_id']
        target_label = scenario['target_label']
        target_logo_url = scenario['target_logo_url']
        s3_path = scenario['s3_path']
        registry_data = scenario['registry_data']

        event_record = {
            'event_id': 'evt-001',
            'registry_config': {
                's3_path': s3_path,
                'row_label': 'club',
            },
        }

        with mock_aws():
            # Set up S3 with the registry file
            s3_client = boto3.client('s3', region_name='eu-west-1')
            bucket_name = 'h-dcn-data-test'
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            )
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_path,
                Body=json.dumps(registry_data).encode('utf-8'),
            )

            # Load handler inside mock context
            handler = _load_get_order_handler()

            # Call _resolve_registry_row_data
            label, logo_url = handler._resolve_registry_row_data(event_record, target_row_id)

            # Assert label matches
            assert label == target_label, (
                f"Expected label '{target_label}' for row_id '{target_row_id}', got '{label}'"
            )
            # Assert logo_url matches
            assert logo_url == target_logo_url, (
                f"Expected logo_url '{target_logo_url}' for row_id '{target_row_id}', got '{logo_url}'"
            )

    @given(scenario=registry_rows_with_target_strategy())
    @settings(max_examples=100, deadline=None)
    def test_create_draft_order_stores_all_three_registry_fields(self, scenario):
        """_create_draft_order with is_row_scope=True stores registry_row_id,
        registry_row_label, and registry_row_logo_url on the order."""
        target_row_id = scenario['target_row_id']
        target_label = scenario['target_label']
        target_logo_url = scenario['target_logo_url']

        with mock_aws():
            # Create Orders table for _create_draft_order to write to
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            dynamodb.create_table(
                TableName='Orders',
                KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST',
            )

            # Load handler inside mock context
            handler = _load_get_order_handler()

            # Create a row-scoped draft order
            order = handler._create_draft_order(
                source_id='evt-001',
                member_id='member-123',
                registry_row_id=target_row_id,
                registry_row_label=target_label,
                registry_row_logo_url=target_logo_url,
                is_row_scope=True,
            )

            # Assert all three registry fields are present
            assert order['registry_row_id'] == target_row_id, (
                f"Order missing correct registry_row_id: expected '{target_row_id}', "
                f"got '{order.get('registry_row_id')}'"
            )
            assert order['registry_row_label'] == target_label, (
                f"Order missing correct registry_row_label: expected '{target_label}', "
                f"got '{order.get('registry_row_label')}'"
            )
            assert order['registry_row_logo_url'] == target_logo_url, (
                f"Order missing correct registry_row_logo_url: expected '{target_logo_url}', "
                f"got '{order.get('registry_row_logo_url')}'"
            )
            # Also verify delegates field is set
            assert 'delegates' in order, "Row-scoped order must have delegates field"
            assert order['delegates']['primary_member_id'] == 'member-123'

    @given(
        row_id=_row_id_strategy,
        s3_path=_s3_path_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_returns_none_for_missing_row_id(self, row_id, s3_path):
        """_resolve_registry_row_data returns (None, None) when row_id is not
        in the S3 registry data."""
        # Registry with no matching row_id
        registry_data = {'rows': [
            {'row_id': f"other-{row_id}-x", 'label': 'Other Row'},
        ]}

        event_record = {
            'event_id': 'evt-002',
            'registry_config': {
                's3_path': s3_path,
                'row_label': 'team',
            },
        }

        with mock_aws():
            s3_client = boto3.client('s3', region_name='eu-west-1')
            bucket_name = 'h-dcn-data-test'
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            )
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_path,
                Body=json.dumps(registry_data).encode('utf-8'),
            )

            handler = _load_get_order_handler()

            label, logo_url = handler._resolve_registry_row_data(event_record, row_id)

            assert label is None, (
                f"Expected None label for missing row_id '{row_id}', got '{label}'"
            )
            assert logo_url is None, (
                f"Expected None logo_url for missing row_id '{row_id}', got '{logo_url}'"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 2: Scope derivation from registry_config
# =============================================================================


# Strategy for generating event records with varying registry_config presence
@st.composite
def event_record_with_registry_config_strategy(draw):
    """Generate an event record that HAS a non-empty registry_config."""
    s3_path = draw(_s3_path_strategy)
    row_label = draw(st.sampled_from(['club', 'team', 'school', 'family', 'group']))
    return {
        'event_id': draw(st.uuids().map(str)),
        'title': draw(label_strategy),
        'registry_config': {
            's3_path': s3_path,
            'row_label': row_label,
        },
    }


@st.composite
def event_record_without_registry_config_strategy(draw):
    """Generate an event record that has NO registry_config or an empty one."""
    event_id = draw(st.uuids().map(str))
    title = draw(label_strategy)
    variant = draw(st.sampled_from(['absent', 'none_value', 'empty_dict', 'empty_string']))

    record = {
        'event_id': event_id,
        'title': title,
    }

    if variant == 'none_value':
        record['registry_config'] = None
    elif variant == 'empty_dict':
        record['registry_config'] = {}
    elif variant == 'empty_string':
        record['registry_config'] = ''
    # 'absent' → key not present at all

    return record


class TestProperty2ScopeDerivationFromRegistryConfig:
    """
    Property 2: Scope derivation from registry_config — returns 'registry_row'
    if registry_config is present and non-empty, else 'member'.

    **Validates: Requirements 1.4**
    """

    @given(event_record=event_record_with_registry_config_strategy())
    @settings(max_examples=100, deadline=None)
    def test_returns_registry_row_when_registry_config_present(self, event_record):
        """_resolve_order_scope returns 'registry_row' for any event with
        a non-empty registry_config."""
        with mock_aws():
            handler = _load_get_order_handler()
            result = handler._resolve_order_scope(event_record)
            assert result == 'registry_row', (
                f"Expected 'registry_row' for event with registry_config="
                f"{event_record.get('registry_config')!r}, got '{result}'"
            )

    @given(event_record=event_record_without_registry_config_strategy())
    @settings(max_examples=100, deadline=None)
    def test_returns_member_when_registry_config_absent_or_empty(self, event_record):
        """_resolve_order_scope returns 'member' for any event without
        registry_config or with an empty/falsy registry_config."""
        with mock_aws():
            handler = _load_get_order_handler()
            result = handler._resolve_order_scope(event_record)
            assert result == 'member', (
                f"Expected 'member' for event with registry_config="
                f"{event_record.get('registry_config')!r}, got '{result}'"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 6: Purchase rules resolution
# =============================================================================

# Load validate_purchase_rules from shared layer via importlib
import importlib.util

_event_validation_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python', 'shared', 'event_validation.py'
    )
)

_event_constraints_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python', 'shared', 'event_constraints.py'
    )
)

# Ensure shared layer path is on sys.path for the imports within event_validation
_shared_layer_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _shared_layer_path not in sys.path:
    sys.path.insert(0, _shared_layer_path)

from shared.event_validation import validate_purchase_rules
from shared.event_constraints import validate_event_constraints


# --- Strategies for Property 6 ---

_product_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=3,
    max_size=15,
).filter(lambda s: s.strip() != '')

_product_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=25,
).filter(lambda s: s.strip() != '')


@st.composite
def purchase_rules_strategy(draw):
    """Generate purchase_rules configs: some with max_per_order, some with max_per_club, some absent."""
    variant = draw(st.sampled_from(['max_per_order', 'max_per_club', 'both', 'absent']))
    rules = {}

    if variant == 'max_per_order':
        rules['max_per_order'] = draw(st.integers(min_value=1, max_value=100))
    elif variant == 'max_per_club':
        # Old field name — should be accepted as fallback
        rules['max_per_club'] = draw(st.integers(min_value=1, max_value=100))
    elif variant == 'both':
        # Both present — max_per_order is authoritative per Req 5.8
        rules['max_per_order'] = draw(st.integers(min_value=1, max_value=100))
        rules['max_per_club'] = draw(st.integers(min_value=1, max_value=100))
    # 'absent' → empty rules (unlimited)

    return rules


@st.composite
def items_for_product_strategy(draw, product_id: str, max_quantity: int = 200):
    """Generate a list of items for a single product with varying quantities."""
    num_items = draw(st.integers(min_value=1, max_value=5))
    items = []
    for _ in range(num_items):
        quantity = draw(st.integers(min_value=1, max_value=max_quantity))
        items.append({
            'product_id': product_id,
            'quantity': quantity,
        })
    return items


class TestProperty6PurchaseRulesResolution:
    """
    Property 6: Purchase rules resolution — effective max_per_order read from
    purchase_rules.max_per_order (absent = unlimited); counting_rule only
    'count_distinct_rows' after migration.

    **Validates: Requirements 5.5**
    """

    @given(
        product_id=_product_id_strategy,
        product_name=_product_name_strategy,
        purchase_rules=purchase_rules_strategy(),
        total_quantity=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=100, deadline=None)
    def test_max_per_order_enforced_correctly(self, product_id, product_name, purchase_rules, total_quantity):
        """
        max_per_order is enforced when present; max_per_club accepted as fallback;
        when absent (empty purchase_rules), no error is returned (unlimited).
        """
        # Build items with the given total quantity
        items = [{'product_id': product_id, 'quantity': total_quantity}]
        products = {
            product_id: {
                'product_id': product_id,
                'name': product_name,
                'purchase_rules': purchase_rules,
            }
        }

        errors = validate_purchase_rules(items, products)

        # Determine effective max_per_order
        effective_max = purchase_rules.get('max_per_order')
        if effective_max is None:
            effective_max = purchase_rules.get('max_per_club')

        if effective_max is None:
            # No limit → no errors expected
            max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]
            assert max_errors == [], (
                f"Expected no max_per_order errors when limit is absent, got: {max_errors}"
            )
        elif total_quantity > effective_max:
            # Should produce an error
            max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]
            assert len(max_errors) >= 1, (
                f"Expected max_per_order error: quantity={total_quantity} > max={effective_max}, "
                f"rules={purchase_rules}, but got no error"
            )
        else:
            # Within limit → no max_per_order error
            max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]
            assert max_errors == [], (
                f"Expected no max_per_order errors: quantity={total_quantity} <= max={effective_max}, "
                f"rules={purchase_rules}, but got: {max_errors}"
            )

    @given(
        product_id=_product_id_strategy,
        product_name=_product_name_strategy,
        max_per_order_val=st.integers(min_value=1, max_value=50),
        max_per_club_val=st.integers(min_value=1, max_value=50),
        total_quantity=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100, deadline=None)
    def test_max_per_order_authoritative_over_max_per_club(
        self, product_id, product_name, max_per_order_val, max_per_club_val, total_quantity
    ):
        """
        When both max_per_order and max_per_club are present,
        max_per_order is authoritative and max_per_club is ignored (Req 5.8).
        """
        purchase_rules = {
            'max_per_order': max_per_order_val,
            'max_per_club': max_per_club_val,
        }
        items = [{'product_id': product_id, 'quantity': total_quantity}]
        products = {
            product_id: {
                'product_id': product_id,
                'name': product_name,
                'purchase_rules': purchase_rules,
            }
        }

        errors = validate_purchase_rules(items, products)
        max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]

        # The effective limit is max_per_order (not max_per_club)
        if total_quantity > max_per_order_val:
            assert len(max_errors) >= 1, (
                f"Expected error: quantity={total_quantity} > max_per_order={max_per_order_val}"
            )
        else:
            assert max_errors == [], (
                f"Expected no error: quantity={total_quantity} <= max_per_order={max_per_order_val}, "
                f"but got: {max_errors}"
            )

    @given(
        product_id=_product_id_strategy,
        product_name=_product_name_strategy,
        total_quantity=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=100, deadline=None)
    def test_absent_purchase_rules_means_unlimited(self, product_id, product_name, total_quantity):
        """
        When purchase_rules is absent or empty, no max_per_order error is produced
        regardless of quantity (unlimited).
        """
        # Test with empty purchase_rules
        items = [{'product_id': product_id, 'quantity': total_quantity}]
        products = {
            product_id: {
                'product_id': product_id,
                'name': product_name,
                'purchase_rules': {},
            }
        }

        errors = validate_purchase_rules(items, products)
        max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]
        assert max_errors == [], (
            f"Expected no max_per_order errors with empty purchase_rules, "
            f"quantity={total_quantity}, got: {max_errors}"
        )

        # Also test with None purchase_rules
        products[product_id]['purchase_rules'] = None
        errors = validate_purchase_rules(items, products)
        max_errors = [e for e in errors if 'max_per_order' in e.get('message', '')]
        assert max_errors == [], (
            f"Expected no max_per_order errors with None purchase_rules, "
            f"quantity={total_quantity}, got: {max_errors}"
        )

    @given(
        counting_rule=st.sampled_from(['count_distinct_rows', 'count_distinct_clubs']),
        max_value=st.integers(min_value=2, max_value=10),
        num_existing_rows=st.integers(min_value=0, max_value=8),
    )
    @settings(max_examples=100, deadline=None)
    def test_counting_rule_count_distinct_rows_equivalent(
        self, counting_rule, max_value, num_existing_rows
    ):
        """
        After migration, counting_rule 'count_distinct_rows' is the standard value.
        'count_distinct_clubs' is accepted as functionally equivalent (Req 5.7).
        Both count the distinct registry_row_ids among submitted/locked orders.
        """
        constraint = {
            'key': 'max_rows',
            'label': 'Maximum registraties',
            'max': max_value,
            'counting_rule': counting_rule,
        }

        # Build existing orders from distinct registry rows
        existing_orders = []
        for i in range(num_existing_rows):
            existing_orders.append({
                'order_id': f'order-{i}',
                'registry_row_id': f'row-{i}',
                'status': 'submitted',
                'items': [{'product_id': 'prod-1', 'quantity': 1}],
            })

        # New order items (always adds 1 distinct row)
        new_items = [{'product_id': 'prod-1', 'quantity': 1}]
        current_row_id = 'row-new'

        errors = validate_event_constraints(
            new_items, [constraint], existing_orders, current_row_id
        )

        # Expected: current_count = num_existing_rows (distinct rows in existing orders)
        # Adding this order adds 1 more distinct row → total = num_existing_rows + 1
        total_after = num_existing_rows + 1

        if total_after > max_value:
            assert len(errors) == 1, (
                f"Expected 1 error: {counting_rule} count {total_after} > max {max_value}, "
                f"but got {len(errors)} errors"
            )
            assert errors[0]['constraint_key'] == 'max_rows'
        else:
            assert errors == [], (
                f"Expected no errors: {counting_rule} count {total_after} <= max {max_value}, "
                f"but got: {errors}"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 5: PDF filename sanitization
# =============================================================================

import re


def _sanitize_for_filename(value: str | None) -> str:
    """
    Python equivalent of frontend sanitizeForFilename():
    - Lowercase
    - Non-alphanumeric characters → hyphens
    - Consecutive hyphens collapsed
    - Leading/trailing hyphens removed
    - Empty/absent → "unknown"
    """
    if not value or value.strip() == '':
        return 'unknown'
    result = value.lower()
    result = re.sub(r'[^a-z0-9]+', '-', result)
    result = re.sub(r'-{2,}', '-', result)
    result = result.strip('-')
    return result if result else 'unknown'


def _build_filename(registry_row_label: str | None, event_name: str) -> str:
    """
    Python equivalent of frontend buildFilename():
    Format: booking-{sanitized_label}-{sanitized_name}.pdf
    """
    sanitized_label = _sanitize_for_filename(registry_row_label)
    sanitized_name = _sanitize_for_filename(event_name)
    return f"booking-{sanitized_label}-{sanitized_name}.pdf"


# Strategies for Property 5
_filename_label_strategy = st.one_of(
    st.none(),
    st.just(''),
    st.text(min_size=1, max_size=40),
)

_filename_event_name_strategy = st.text(min_size=1, max_size=40)


class TestProperty5PdfFilenameSanitization:
    """
    Property 5: PDF filename sanitization — filename matches
    `booking-{sanitized_label}-{sanitized_name}.pdf`; absent label → "unknown".

    **Validates: Requirements 3.5**
    """

    @given(
        label=_filename_label_strategy,
        event_name=_filename_event_name_strategy,
    )
    @settings(max_examples=100)
    def test_filename_matches_expected_pattern(self, label, event_name):
        """Generated filename always matches booking-{sanitized}-{sanitized}.pdf pattern."""
        filename = _build_filename(label, event_name)

        # Must start with "booking-" and end with ".pdf"
        assert filename.startswith('booking-'), (
            f"Filename '{filename}' doesn't start with 'booking-'"
        )
        assert filename.endswith('.pdf'), (
            f"Filename '{filename}' doesn't end with '.pdf'"
        )

        # The middle part (between "booking-" and ".pdf") should only contain
        # lowercase alphanumeric characters and hyphens
        middle = filename[len('booking-'):-len('.pdf')]
        assert re.match(r'^[a-z0-9]+(-[a-z0-9]+)*-[a-z0-9]+(-[a-z0-9]+)*$', middle) or \
               re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', middle), (
            f"Middle part '{middle}' contains invalid characters or consecutive hyphens"
        )

        # No consecutive hyphens in the middle
        assert '--' not in middle, (
            f"Filename '{filename}' contains consecutive hyphens in middle: '{middle}'"
        )

        # No leading or trailing hyphens in the middle
        assert not middle.startswith('-'), (
            f"Middle part '{middle}' starts with a hyphen"
        )
        assert not middle.endswith('-'), (
            f"Middle part '{middle}' ends with a hyphen"
        )

    @given(
        label=st.one_of(st.none(), st.just(''), st.just('   ')),
        event_name=_filename_event_name_strategy,
    )
    @settings(max_examples=100)
    def test_absent_label_falls_back_to_unknown(self, label, event_name):
        """When registry_row_label is absent/empty/whitespace, 'unknown' is used."""
        filename = _build_filename(label, event_name)

        # The label part should be "unknown"
        assert filename.startswith('booking-unknown-'), (
            f"Expected 'booking-unknown-...' for absent label={label!r}, got '{filename}'"
        )

    @given(
        label=st.from_regex(r'[a-zA-Z0-9]+', fullmatch=True).filter(lambda s: 1 <= len(s) <= 20),
        event_name=st.from_regex(r'[a-zA-Z0-9]+', fullmatch=True).filter(lambda s: 1 <= len(s) <= 20),
    )
    @settings(max_examples=100)
    def test_sanitization_lowercases_alphanumeric(self, label, event_name):
        """Sanitization lowercases all characters; pure ASCII alphanumeric input stays as-is (lowered)."""
        filename = _build_filename(label, event_name)

        expected_label = label.lower()
        expected_name = event_name.lower()
        expected = f"booking-{expected_label}-{expected_name}.pdf"
        assert filename == expected, (
            f"For alphanumeric input label={label!r}, event_name={event_name!r}, "
            f"expected '{expected}', got '{filename}'"
        )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 7: PDF header labeling format
# =============================================================================

# Path to the generate_preparation_pdf handler
_pdf_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_preparation_pdf', 'app.py')
)


def _load_pdf_handler():
    """Load generate_preparation_pdf handler module by file path using importlib.util."""
    import importlib.util
    module_name = 'generate_preparation_pdf_app'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _pdf_handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Strategies for Property 7
_row_label_prefix_strategy = st.one_of(
    st.just(''),
    st.just('club'),
    st.just('team'),
    st.just('school'),
    st.just('family'),
    st.text(
        alphabet=st.characters(whitelist_categories=('L',)),
        min_size=1,
        max_size=15,
    ),
)

_row_name_for_pdf_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != '')

_logo_url_for_pdf_strategy = st.one_of(
    st.none(),
    st.just(''),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=3,
        max_size=20,
    ).map(lambda s: f"https://logos.example.com/{s}.png"),
)


class TestProperty7PdfHeaderLabelingFormat:
    """
    Property 7: PDF header labeling format — displays "{row_label_prefix}: {label}"
    with the row logo (if available) rendered as a 50×50 image preceding the label.
    When row_label is absent or empty, the fallback "row" SHALL be used as prefix.
    When logo_url is absent, no image is rendered.

    **Validates: Requirements 6.2, 6.3, 6.4**
    """

    @given(
        row_label_prefix=_row_label_prefix_strategy,
        row_name=_row_name_for_pdf_strategy,
        logo_url=_logo_url_for_pdf_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_header_contains_correct_label_format(self, row_label_prefix, row_name, logo_url):
        """The HTML output header contains '{row_label_prefix}: {label}' format."""
        with mock_aws():
            # Set up S3 bucket (handler imports s3 at module level)
            s3_client = boto3.client('s3', region_name='eu-west-1')
            bucket_name = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-test')
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            )

            handler = _load_pdf_handler()

            # Build order with a registry_row_id
            row_id = 'test-row-1'
            order = {
                'order_id': 'order-1',
                'registry_row_id': row_id,
                'items': [],
                'total_amount': 0,
                'payment_status': 'unpaid',
            }

            # Build registry_rows lookup
            registry_row_entry = {'label': row_name}
            if logo_url:
                registry_row_entry['logo_url'] = logo_url
            registry_rows = {row_id: registry_row_entry}

            # Determine expected prefix (handler uses the passed value; caller resolves fallback)
            effective_prefix = row_label_prefix if row_label_prefix else 'row'

            html = handler._build_by_order_page(
                order=order,
                registry_rows=registry_rows,
                products_map={},
                page_num=1,
                total_pages=1,
                event_name='Test Event',
                generation_date='2025-01-01',
                row_label_prefix=effective_prefix,
            )

            # Assert header format
            expected_header = f"{effective_prefix}: {row_name}"
            assert expected_header in html, (
                f"Expected header text '{expected_header}' not found in HTML output.\n"
                f"row_label_prefix={row_label_prefix!r}, row_name={row_name!r}"
            )

    @given(
        row_name=_row_name_for_pdf_strategy,
        logo_url=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=3,
            max_size=20,
        ).map(lambda s: f"https://logos.example.com/{s}.png"),
    )
    @settings(max_examples=100, deadline=None)
    def test_logo_rendered_when_present(self, row_name, logo_url):
        """When logo_url is present, an <img> tag with class 'row-logo' is rendered."""
        with mock_aws():
            s3_client = boto3.client('s3', region_name='eu-west-1')
            bucket_name = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-test')
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            )

            handler = _load_pdf_handler()

            row_id = 'test-row-2'
            order = {
                'order_id': 'order-2',
                'registry_row_id': row_id,
                'items': [],
                'total_amount': 0,
                'payment_status': 'unpaid',
            }
            registry_rows = {row_id: {'label': row_name, 'logo_url': logo_url}}

            html = handler._build_by_order_page(
                order=order,
                registry_rows=registry_rows,
                products_map={},
                page_num=1,
                total_pages=1,
                event_name='Test Event',
                generation_date='2025-01-01',
                row_label_prefix='club',
            )

            # Assert img tag is present with the logo URL and correct class
            assert 'class="row-logo"' in html, (
                f"Expected 'class=\"row-logo\"' in HTML when logo_url={logo_url!r}"
            )
            assert f'src="{logo_url}"' in html, (
                f"Expected 'src=\"{logo_url}\"' in HTML when logo_url={logo_url!r}"
            )

    @given(
        row_name=_row_name_for_pdf_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_no_image_when_logo_absent(self, row_name):
        """When logo_url is absent/None, no <img> tag is rendered."""
        with mock_aws():
            s3_client = boto3.client('s3', region_name='eu-west-1')
            bucket_name = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-test')
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'},
            )

            handler = _load_pdf_handler()

            row_id = 'test-row-3'
            order = {
                'order_id': 'order-3',
                'registry_row_id': row_id,
                'items': [],
                'total_amount': 0,
                'payment_status': 'unpaid',
            }
            # No logo_url in registry entry
            registry_rows = {row_id: {'label': row_name}}

            html = handler._build_by_order_page(
                order=order,
                registry_rows=registry_rows,
                products_map={},
                page_num=1,
                total_pages=1,
                event_name='Test Event',
                generation_date='2025-01-01',
                row_label_prefix='team',
            )

            # Assert no <img> tag is present
            assert '<img' not in html, (
                f"Expected no <img> tag when logo_url is absent, but found one in HTML.\n"
                f"row_name={row_name!r}"
            )


# =============================================================================
# Feature: generic-registry-row-refactor, Property 8: Delegate email template context resolution
# =============================================================================

# Path to the send_delegate_invitation handler
_delegate_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'send_delegate_invitation', 'app.py')
)


def _load_delegate_handler():
    """Load send_delegate_invitation handler module by file path using importlib.util."""
    import importlib.util
    module_name = 'send_delegate_invitation_app'
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _delegate_handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Strategies for Property 8
_row_label_type_strategy = st.one_of(
    st.just(''),
    st.just('club'),
    st.just('team'),
    st.just('school'),
    st.just('family'),
    st.text(
        alphabet=st.characters(whitelist_categories=('L',)),
        min_size=1,
        max_size=15,
    ),
)

_row_name_value_strategy = st.one_of(
    st.just(''),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip() != ''),
)

_registry_row_id_for_email_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=1,
    max_size=15,
).filter(lambda s: s.strip() != '')


class TestProperty8DelegateEmailTemplateContextResolution:
    """
    Property 8: Delegate email template context resolution — ROW_LABEL and
    ROW_NAME resolved from order; fallback to "group" and registry_row_id.

    **Validates: Requirements 7.1, 7.2, 7.4**
    """

    @given(
        row_label=st.text(
            alphabet=st.characters(whitelist_categories=('L',)),
            min_size=1,
            max_size=15,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_row_label_from_registry_config(self, row_label):
        """_resolve_row_label returns event.registry_config.row_label when present."""
        with mock_aws():
            handler = _load_delegate_handler()

            event = {
                'event_id': 'evt-1',
                'registry_config': {'row_label': row_label, 's3_path': 'test.json'},
            }

            result = handler._resolve_row_label(event)
            assert result == row_label, (
                f"Expected '{row_label}', got '{result}'"
            )

    @given(
        variant=st.sampled_from(['absent', 'none_value', 'empty_string', 'empty_config']),
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_row_label_fallback_to_group(self, variant):
        """_resolve_row_label falls back to 'group' when row_label is absent/empty."""
        with mock_aws():
            handler = _load_delegate_handler()

            if variant == 'absent':
                event = {'event_id': 'evt-1'}
            elif variant == 'none_value':
                event = {'event_id': 'evt-1', 'registry_config': None}
            elif variant == 'empty_string':
                event = {'event_id': 'evt-1', 'registry_config': {'row_label': ''}}
            else:  # empty_config
                event = {'event_id': 'evt-1', 'registry_config': {}}

            result = handler._resolve_row_label(event)
            assert result == 'group', (
                f"Expected 'group' for variant={variant!r}, got '{result}'"
            )

    @given(
        row_label_on_order=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=30,
        ).filter(lambda s: s.strip() != ''),
        registry_row_id=_registry_row_id_for_email_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_row_name_from_order_label(self, row_label_on_order, registry_row_id):
        """_resolve_row_name returns order.registry_row_label when present."""
        with mock_aws():
            handler = _load_delegate_handler()

            order = {
                'order_id': 'order-1',
                'registry_row_id': registry_row_id,
                'registry_row_label': row_label_on_order,
            }
            event = {'event_id': 'evt-1', 'registry_config': {'row_label': 'club'}}

            result = handler._resolve_row_name(order, event)
            assert result == row_label_on_order, (
                f"Expected '{row_label_on_order}', got '{result}'"
            )

    @given(
        registry_row_id=_registry_row_id_for_email_strategy,
        claim_label=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=20,
        ).filter(lambda s: s.strip() != ''),
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_row_name_fallback_to_registry_claims(self, registry_row_id, claim_label):
        """_resolve_row_name falls back to event.registry_claims[row_id].label
        when order.registry_row_label is absent."""
        with mock_aws():
            handler = _load_delegate_handler()

            order = {
                'order_id': 'order-1',
                'registry_row_id': registry_row_id,
                # registry_row_label is absent
            }
            event = {
                'event_id': 'evt-1',
                'registry_config': {'row_label': 'team'},
                'registry_claims': {
                    registry_row_id: {'label': claim_label},
                },
            }

            result = handler._resolve_row_name(order, event)
            assert result == claim_label, (
                f"Expected '{claim_label}' from registry_claims, got '{result}'"
            )

    @given(
        registry_row_id=_registry_row_id_for_email_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_resolve_row_name_final_fallback_to_registry_row_id(self, registry_row_id):
        """_resolve_row_name falls back to registry_row_id when both
        order.registry_row_label and event.registry_claims are absent."""
        with mock_aws():
            handler = _load_delegate_handler()

            order = {
                'order_id': 'order-1',
                'registry_row_id': registry_row_id,
                # No registry_row_label
            }
            event = {
                'event_id': 'evt-1',
                'registry_config': {'row_label': 'school'},
                # No registry_claims
            }

            result = handler._resolve_row_name(order, event)
            assert result == registry_row_id, (
                f"Expected '{registry_row_id}' as final fallback, got '{result}'"
            )
