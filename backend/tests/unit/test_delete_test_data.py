"""Unit tests for the delete_test_data function in the migration script."""
import os
import sys

import boto3
import pytest
from moto import mock_aws

# Add project root to path so we can import the migration module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from scripts.migrate_products import delete_test_data, delete_all_records, MigrationSummary


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'


def _create_table(dynamodb, table_name, key_name):
    """Helper to create a DynamoDB table with a given key."""
    return dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': key_name, 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': key_name, 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


@mock_aws
def test_delete_test_data_deletes_all_records(aws_credentials):
    """Verify all records from Orders, Carts, and Payments are deleted."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

    orders_table = _create_table(dynamodb, 'Orders', 'order_id')
    carts_table = _create_table(dynamodb, 'Carts', 'cart_id')
    payments_table = _create_table(dynamodb, 'Payments', 'payment_id')

    # Populate with test data
    for i in range(5):
        orders_table.put_item(Item={'order_id': f'order-{i}', 'status': 'draft'})
    for i in range(3):
        carts_table.put_item(Item={'cart_id': f'cart-{i}', 'items': []})
    for i in range(7):
        payments_table.put_item(Item={'payment_id': f'pay-{i}', 'amount': 100})

    # Execute deletion
    counts = delete_test_data(orders_table, carts_table, payments_table, dry_run=False)

    # Verify counts
    assert counts['orders_deleted'] == 5
    assert counts['carts_deleted'] == 3
    assert counts['payments_deleted'] == 7

    # Verify tables are empty
    assert orders_table.scan(Select='COUNT')['Count'] == 0
    assert carts_table.scan(Select='COUNT')['Count'] == 0
    assert payments_table.scan(Select='COUNT')['Count'] == 0


@mock_aws
def test_delete_test_data_dry_run_does_not_delete(aws_credentials):
    """Verify dry_run mode counts records but doesn't delete them."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

    orders_table = _create_table(dynamodb, 'Orders', 'order_id')
    carts_table = _create_table(dynamodb, 'Carts', 'cart_id')
    payments_table = _create_table(dynamodb, 'Payments', 'payment_id')

    # Populate with test data
    for i in range(4):
        orders_table.put_item(Item={'order_id': f'order-{i}', 'status': 'paid'})
    for i in range(2):
        carts_table.put_item(Item={'cart_id': f'cart-{i}', 'items': []})
    for i in range(6):
        payments_table.put_item(Item={'payment_id': f'pay-{i}', 'amount': 50})

    # Execute with dry_run=True
    counts = delete_test_data(orders_table, carts_table, payments_table, dry_run=True)

    # Verify counts are reported
    assert counts['orders_deleted'] == 4
    assert counts['carts_deleted'] == 2
    assert counts['payments_deleted'] == 6

    # Verify records still exist (not deleted)
    assert orders_table.scan(Select='COUNT')['Count'] == 4
    assert carts_table.scan(Select='COUNT')['Count'] == 2
    assert payments_table.scan(Select='COUNT')['Count'] == 6


@mock_aws
def test_delete_test_data_empty_tables(aws_credentials):
    """Verify it handles empty tables gracefully."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

    orders_table = _create_table(dynamodb, 'Orders', 'order_id')
    carts_table = _create_table(dynamodb, 'Carts', 'cart_id')
    payments_table = _create_table(dynamodb, 'Payments', 'payment_id')

    # Execute on empty tables
    counts = delete_test_data(orders_table, carts_table, payments_table, dry_run=False)

    # All counts should be zero
    assert counts['orders_deleted'] == 0
    assert counts['carts_deleted'] == 0
    assert counts['payments_deleted'] == 0


@mock_aws
def test_migration_summary_includes_deletion_counts(aws_credentials):
    """Verify MigrationSummary correctly stores deletion counts."""
    summary = MigrationSummary()
    summary.orders_deleted = 10
    summary.carts_deleted = 5
    summary.payments_deleted = 8

    assert summary.orders_deleted == 10
    assert summary.carts_deleted == 5
    assert summary.payments_deleted == 8

    # Verify the dataclass repr includes the counts
    summary_str = repr(summary)
    assert "orders_deleted=10" in summary_str
    assert "carts_deleted=5" in summary_str
    assert "payments_deleted=8" in summary_str
