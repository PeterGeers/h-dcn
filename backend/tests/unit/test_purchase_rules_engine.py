"""
Unit tests for shared.purchase_rules_engine module.

Tests the purchase rule enforcement functions:
- enforce_max_per_order
- enforce_max_per_member
- enforce_max_per_club
- enforce_requires_membership
- validate_purchase_rules (orchestrator)
"""

import pytest
import boto3
import sys
import os
from moto import mock_aws

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))

from shared.purchase_rules_engine import (
    enforce_max_per_order,
    enforce_max_per_member,
    enforce_max_per_club,
    enforce_requires_membership,
    validate_purchase_rules,
)


@pytest.fixture
def aws_env():
    """Set up mocked AWS credentials."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'


@pytest.fixture
def orders_table(aws_env):
    """Create a mocked Orders DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        yield table


@pytest.fixture
def memberships_table(aws_env):
    """Create a mocked Memberships DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Memberships',
            KeySchema=[{'AttributeName': 'membership_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'membership_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        yield table


@pytest.fixture
def orders_and_memberships(aws_env):
    """Create both Orders and Memberships tables in the same mock context."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        orders = dynamodb.create_table(
            TableName='Orders',
            KeySchema=[{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'order_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        memberships = dynamodb.create_table(
            TableName='Memberships',
            KeySchema=[{'AttributeName': 'membership_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'membership_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        yield orders, memberships


class TestEnforceMaxPerOrder:
    """Tests for enforce_max_per_order."""

    def test_allows_quantity_within_limit(self):
        result = enforce_max_per_order(3, 5)
        assert result is None

    def test_allows_quantity_at_limit(self):
        result = enforce_max_per_order(5, 5)
        assert result is None

    def test_rejects_quantity_exceeding_limit(self):
        result = enforce_max_per_order(6, 5)
        assert result is not None
        assert result["error"] == "purchase_rule_violation"
        assert result["details"]["rule"] == "max_per_order"
        assert result["details"]["limit"] == 5
        assert result["details"]["requested"] == 6
        assert result["details"]["remaining_allowed"] == 5

    def test_single_item_allowed(self):
        result = enforce_max_per_order(1, 1)
        assert result is None

    def test_single_item_exceeded(self):
        result = enforce_max_per_order(2, 1)
        assert result is not None
        assert result["details"]["rule"] == "max_per_order"


class TestEnforceMaxPerMember:
    """Tests for enforce_max_per_member."""

    def test_allows_first_purchase_within_limit(self, orders_table):
        result = enforce_max_per_member(
            "member_1", "prod_1", 2, 5, orders_table
        )
        assert result is None

    def test_rejects_when_existing_orders_plus_new_exceeds_limit(self, orders_table):
        # Create existing paid order
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'member_id': 'member_1',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 3}],
        })

        result = enforce_max_per_member(
            "member_1", "prod_1", 3, 5, orders_table
        )
        assert result is not None
        assert result["details"]["rule"] == "max_per_member"
        assert result["details"]["current_total"] == 3
        assert result["details"]["requested"] == 3
        assert result["details"]["remaining_allowed"] == 2

    def test_counts_only_paid_and_pending_orders(self, orders_table):
        # Paid order counts
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'member_id': 'member_1',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 2}],
        })
        # Pending order counts
        orders_table.put_item(Item={
            'order_id': 'order_2',
            'member_id': 'member_1',
            'status': 'pending',
            'items': [{'product_id': 'prod_1', 'quantity': 1}],
        })
        # Cancelled order does NOT count
        orders_table.put_item(Item={
            'order_id': 'order_3',
            'member_id': 'member_1',
            'status': 'cancelled',
            'items': [{'product_id': 'prod_1', 'quantity': 10}],
        })

        # Total from paid+pending = 3, requesting 2, limit 5 → allowed
        result = enforce_max_per_member(
            "member_1", "prod_1", 2, 5, orders_table
        )
        assert result is None

    def test_different_product_not_counted(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'member_id': 'member_1',
            'status': 'paid',
            'items': [{'product_id': 'prod_other', 'quantity': 10}],
        })

        result = enforce_max_per_member(
            "member_1", "prod_1", 5, 5, orders_table
        )
        assert result is None

    def test_different_member_not_counted(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'member_id': 'member_other',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 10}],
        })

        result = enforce_max_per_member(
            "member_1", "prod_1", 5, 5, orders_table
        )
        assert result is None


class TestEnforceMaxPerClub:
    """Tests for enforce_max_per_club."""

    def test_allows_first_purchase_within_limit(self, orders_table):
        result = enforce_max_per_club(
            "club_NL001", "prod_1", 5, 20, orders_table
        )
        assert result is None

    def test_rejects_when_club_total_exceeds_limit(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'club_id': 'club_NL001',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 18}],
        })

        result = enforce_max_per_club(
            "club_NL001", "prod_1", 5, 20, orders_table
        )
        assert result is not None
        assert result["details"]["rule"] == "max_per_club"
        assert result["details"]["current_total"] == 18
        assert result["details"]["requested"] == 5
        assert result["details"]["remaining_allowed"] == 2

    def test_counts_only_paid_and_pending_orders(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'club_id': 'club_NL001',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 10}],
        })
        orders_table.put_item(Item={
            'order_id': 'order_2',
            'club_id': 'club_NL001',
            'status': 'pending',
            'items': [{'product_id': 'prod_1', 'quantity': 5}],
        })
        # Draft order should NOT count
        orders_table.put_item(Item={
            'order_id': 'order_3',
            'club_id': 'club_NL001',
            'status': 'draft',
            'items': [{'product_id': 'prod_1', 'quantity': 100}],
        })

        # paid(10) + pending(5) = 15, requesting 5, limit 20 → allowed
        result = enforce_max_per_club(
            "club_NL001", "prod_1", 5, 20, orders_table
        )
        assert result is None


class TestEnforceRequiresMembership:
    """Tests for enforce_requires_membership."""

    def test_allows_member_with_active_membership(self, memberships_table):
        memberships_table.put_item(Item={
            'membership_id': 'ms_1',
            'member_id': 'member_1',
            'status': 'active',
        })

        result = enforce_requires_membership("member_1", memberships_table)
        assert result is None

    def test_rejects_member_without_active_membership(self, memberships_table):
        # No membership records at all
        result = enforce_requires_membership("member_1", memberships_table)
        assert result is not None
        assert result["details"]["rule"] == "requires_membership"

    def test_rejects_member_with_only_expired_membership(self, memberships_table):
        memberships_table.put_item(Item={
            'membership_id': 'ms_1',
            'member_id': 'member_1',
            'status': 'expired',
        })

        result = enforce_requires_membership("member_1", memberships_table)
        assert result is not None
        assert result["details"]["rule"] == "requires_membership"


class TestValidatePurchaseRules:
    """Tests for the validate_purchase_rules orchestrator."""

    def test_returns_none_when_rules_is_none(self):
        result = validate_purchase_rules(None, {"quantity": 10, "product_id": "p1", "member_id": "m1"})
        assert result is None

    def test_returns_none_when_rules_is_empty_dict(self):
        result = validate_purchase_rules({}, {"quantity": 10, "product_id": "p1", "member_id": "m1"})
        assert result is None

    def test_max_per_order_violation_through_orchestrator(self):
        rules = {"max_per_order": 3}
        context = {"quantity": 5, "product_id": "prod_1", "member_id": "m1"}

        result = validate_purchase_rules(rules, context)
        assert result is not None
        assert result["details"]["rule"] == "max_per_order"
        assert result["details"]["product_id"] == "prod_1"

    def test_max_per_member_violation_through_orchestrator(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'member_id': 'member_1',
            'status': 'paid',
            'items': [{'product_id': 'prod_1', 'quantity': 4}],
        })

        rules = {"max_per_member": 5}
        context = {
            "quantity": 2,
            "product_id": "prod_1",
            "member_id": "member_1",
            "orders_table": orders_table,
        }

        result = validate_purchase_rules(rules, context)
        assert result is not None
        assert result["details"]["rule"] == "max_per_member"

    def test_max_per_club_violation_through_orchestrator(self, orders_table):
        orders_table.put_item(Item={
            'order_id': 'order_1',
            'club_id': 'club_1',
            'status': 'pending',
            'items': [{'product_id': 'prod_1', 'quantity': 18}],
        })

        rules = {"max_per_club": 20}
        context = {
            "quantity": 5,
            "product_id": "prod_1",
            "member_id": "m1",
            "club_id": "club_1",
            "orders_table": orders_table,
        }

        result = validate_purchase_rules(rules, context)
        assert result is not None
        assert result["details"]["rule"] == "max_per_club"

    def test_requires_membership_violation_through_orchestrator(self, orders_and_memberships):
        orders_table, memberships_table = orders_and_memberships

        rules = {"requires_membership": True}
        context = {
            "quantity": 1,
            "product_id": "prod_1",
            "member_id": "member_no_membership",
            "orders_table": orders_table,
            "memberships_table": memberships_table,
        }

        result = validate_purchase_rules(rules, context)
        assert result is not None
        assert result["details"]["rule"] == "requires_membership"

    def test_all_rules_pass(self, orders_and_memberships):
        orders_table, memberships_table = orders_and_memberships

        memberships_table.put_item(Item={
            'membership_id': 'ms_1',
            'member_id': 'member_1',
            'status': 'active',
        })

        rules = {
            "max_per_order": 10,
            "max_per_member": 20,
            "max_per_club": 50,
            "requires_membership": True,
        }
        context = {
            "quantity": 3,
            "product_id": "prod_1",
            "member_id": "member_1",
            "club_id": "club_1",
            "orders_table": orders_table,
            "memberships_table": memberships_table,
        }

        result = validate_purchase_rules(rules, context)
        assert result is None

    def test_skips_absent_rules(self, orders_and_memberships):
        """When a rule key is absent, that constraint is not enforced."""
        orders_table, memberships_table = orders_and_memberships

        # Only max_per_order is set, others absent → no member/club/membership check
        rules = {"max_per_order": 10}
        context = {
            "quantity": 5,
            "product_id": "prod_1",
            "member_id": "member_1",
            "orders_table": orders_table,
            "memberships_table": memberships_table,
        }

        result = validate_purchase_rules(rules, context)
        assert result is None

    def test_skips_max_per_club_when_no_club_id(self, orders_table):
        """max_per_club is skipped when club_id is not in context."""
        rules = {"max_per_club": 1}
        context = {
            "quantity": 100,
            "product_id": "prod_1",
            "member_id": "m1",
            "orders_table": orders_table,
            # No club_id
        }

        result = validate_purchase_rules(rules, context)
        assert result is None
