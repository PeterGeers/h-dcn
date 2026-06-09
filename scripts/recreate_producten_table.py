#!/usr/bin/env python3
"""
Recreate Producten DynamoDB Table with product_id as partition key.

The current Producten table uses `id` as its partition key. After the product
model unification migration, all records have a `product_id` attribute.
This script recreates the table with `product_id` as the partition key.

Steps:
1. Scan all records from current Producten table
2. Verify each record has a product_id attribute (fallback to id if missing)
3. Create temporary table Producten_New with product_id partition key + GSI
4. Copy all records to Producten_New
5. Verify record counts match
6. Delete old Producten table, wait for deletion
7. Create final Producten table (same schema)
8. Copy records from Producten_New to Producten
9. Verify record counts match
10. Delete Producten_New

Usage:
    python scripts/recreate_producten_table.py --dry-run
    python scripts/recreate_producten_table.py
    python scripts/recreate_producten_table.py --profile nonprofit-deploy
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import boto3
from botocore.exceptions import ClientError

REGION = "eu-west-1"
DEFAULT_TABLE_NAME = "Producten"
DEFAULT_PROFILE = "nonprofit-deploy"
TEMP_TABLE_NAME = "Producten_New"

GSI_NAME = "parent-id-index"
GSI_KEY = "parent_id"

POLL_INTERVAL = 5  # seconds between status checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def get_dynamodb_client(profile: str | None = None):
    """Create a DynamoDB client with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.client("dynamodb", region_name=REGION)


def scan_all_items(table) -> list[dict]:
    """Scan entire table with pagination handling."""
    items = []
    scan_kwargs: dict = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def wait_for_table_active(client, table_name: str, timeout: int = 300):
    """Wait for a table to reach ACTIVE status."""
    logger.info(f"  Waiting for table '{table_name}' to become ACTIVE...")
    start = time.time()

    while True:
        if time.time() - start > timeout:
            raise TimeoutError(
                f"Table '{table_name}' did not become ACTIVE within {timeout}s"
            )

        try:
            response = client.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]
            if status == "ACTIVE":
                logger.info(f"  Table '{table_name}' is ACTIVE")
                return
            logger.info(f"  Table status: {status}, waiting...")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"  Table '{table_name}' not found yet, waiting...")
            else:
                raise

        time.sleep(POLL_INTERVAL)


def wait_for_table_deleted(client, table_name: str, timeout: int = 300):
    """Wait for a table to be fully deleted."""
    logger.info(f"  Waiting for table '{table_name}' to be deleted...")
    start = time.time()

    while True:
        if time.time() - start > timeout:
            raise TimeoutError(
                f"Table '{table_name}' was not deleted within {timeout}s"
            )

        try:
            response = client.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]
            logger.info(f"  Table status: {status}, waiting...")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"  Table '{table_name}' has been deleted")
                return
            else:
                raise

        time.sleep(POLL_INTERVAL)


def create_table_with_product_id_key(client, table_name: str):
    """Create a DynamoDB table with product_id as partition key and parent-id-index GSI."""
    logger.info(f"  Creating table '{table_name}' with product_id partition key...")

    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "product_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"},
            {"AttributeName": "parent_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI_NAME,
                "KeySchema": [
                    {"AttributeName": GSI_KEY, "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    wait_for_table_active(client, table_name)


def copy_records(source_items: list[dict], target_table, table_name: str):
    """Copy records to a target table using batch_writer."""
    logger.info(f"  Copying {len(source_items)} records to '{table_name}'...")

    with target_table.batch_writer() as batch:
        for item in source_items:
            batch.put_item(Item=item)

    logger.info(f"  Copied {len(source_items)} records to '{table_name}'")


def verify_record_count(table, expected_count: int, table_name: str) -> bool:
    """Verify the record count in a table matches the expected count."""
    items = scan_all_items(table)
    actual_count = len(items)

    if actual_count == expected_count:
        logger.info(
            f"  ✓ Record count verified: {actual_count} records in '{table_name}'"
        )
        return True
    else:
        logger.error(
            f"  ✗ Record count MISMATCH in '{table_name}': "
            f"expected {expected_count}, got {actual_count}"
        )
        return False


def disable_deletion_protection(client, table_name: str):
    """Disable deletion protection on a table if enabled."""
    try:
        response = client.describe_table(TableName=table_name)
        if response["Table"].get("DeletionProtectionEnabled", False):
            logger.info(f"  Disabling deletion protection on '{table_name}'...")
            client.update_table(
                TableName=table_name,
                DeletionProtectionEnabled=False,
            )
            # Wait a moment for the update to take effect
            time.sleep(2)
            logger.info(f"  Deletion protection disabled on '{table_name}'")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise


def delete_table(client, table_name: str):
    """Delete a DynamoDB table and wait for deletion to complete."""
    logger.info(f"  Deleting table '{table_name}'...")
    disable_deletion_protection(client, table_name)
    client.delete_table(TableName=table_name)
    wait_for_table_deleted(client, table_name)


def recreate_producten_table(
    dry_run: bool = False,
    profile: str | None = DEFAULT_PROFILE,
    table_name: str = DEFAULT_TABLE_NAME,
):
    """Execute the full table recreation process."""
    dynamodb = get_dynamodb_resource(profile)
    client = get_dynamodb_client(profile)

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info(f"{'=' * 60}")
    logger.info(f"Recreate Producten Table [{mode}]")
    logger.info(f"  Table: {table_name} | Region: {REGION}")
    logger.info(f"  New partition key: product_id (String)")
    logger.info(f"  GSI: {GSI_NAME} on {GSI_KEY}")
    if profile:
        logger.info(f"  Profile: {profile}")
    logger.info(f"{'=' * 60}")

    # --- Step 1: Scan all records ---
    logger.info("Step 1: Scanning all records from current Producten table...")
    current_table = dynamodb.Table(table_name)
    all_items = scan_all_items(current_table)
    total_count = len(all_items)
    logger.info(f"  Found {total_count} records")

    if total_count == 0:
        logger.error("  No records found! Aborting to prevent data loss.")
        sys.exit(1)

    # --- Step 2: Verify product_id attribute ---
    logger.info("Step 2: Verifying each record has a product_id attribute...")
    missing_product_id = 0
    fallback_used = 0

    for item in all_items:
        if "product_id" not in item:
            missing_product_id += 1
            # Use id as fallback
            if "id" in item:
                item["product_id"] = item["id"]
                fallback_used += 1
                logger.warning(
                    f"  Record missing product_id, using id='{item['id']}' as fallback"
                )
            else:
                logger.error(
                    f"  Record has neither product_id nor id! Keys: {list(item.keys())}"
                )
                sys.exit(1)

    if missing_product_id == 0:
        logger.info(f"  ✓ All {total_count} records have product_id attribute")
    else:
        logger.info(
            f"  {missing_product_id} records missing product_id "
            f"({fallback_used} used id as fallback)"
        )

    # Check for duplicate product_ids
    product_ids = [item["product_id"] for item in all_items]
    duplicates = set(
        pid for pid in product_ids if product_ids.count(pid) > 1
    )
    if duplicates:
        logger.error(f"  ✗ Found duplicate product_ids: {duplicates}")
        sys.exit(1)
    else:
        logger.info(f"  ✓ All {total_count} product_ids are unique")

    if dry_run:
        logger.info(f"{'=' * 60}")
        logger.info("DRY RUN complete. No changes made.")
        logger.info(f"  Records to migrate: {total_count}")
        logger.info(f"  Records with product_id: {total_count - missing_product_id}")
        logger.info(f"  Records using id fallback: {fallback_used}")
        logger.info(f"{'=' * 60}")
        return

    # --- Step 3: Create temporary table Producten_New ---
    logger.info(f"Step 3: Creating temporary table '{TEMP_TABLE_NAME}'...")
    create_table_with_product_id_key(client, TEMP_TABLE_NAME)

    # --- Step 4: Copy all records to Producten_New ---
    logger.info(f"Step 4: Copying records to '{TEMP_TABLE_NAME}'...")
    temp_table = dynamodb.Table(TEMP_TABLE_NAME)
    copy_records(all_items, temp_table, TEMP_TABLE_NAME)

    # --- Step 5: Verify record count in new table ---
    logger.info("Step 5: Verifying record count in temporary table...")
    if not verify_record_count(temp_table, total_count, TEMP_TABLE_NAME):
        logger.error("  Aborting! Record count mismatch in temporary table.")
        sys.exit(1)

    # --- Step 6: Delete old Producten table ---
    logger.info(f"Step 6: Deleting old '{table_name}' table...")
    delete_table(client, table_name)

    # --- Step 7: Create final Producten table with new schema ---
    logger.info(f"Step 7: Creating final '{table_name}' table with product_id key...")
    create_table_with_product_id_key(client, table_name)

    # --- Step 8: Copy records from Producten_New to Producten ---
    logger.info(f"Step 8: Copying records from '{TEMP_TABLE_NAME}' to '{table_name}'...")
    final_table = dynamodb.Table(table_name)
    # Re-scan from temp table to ensure fresh data
    temp_items = scan_all_items(temp_table)
    copy_records(temp_items, final_table, table_name)

    # --- Step 9: Verify record count in final table ---
    logger.info("Step 9: Verifying record count in final table...")
    if not verify_record_count(final_table, total_count, table_name):
        logger.error(
            f"  ✗ Record count mismatch! "
            f"Temporary table '{TEMP_TABLE_NAME}' still exists with backup data."
        )
        sys.exit(1)

    # --- Step 10: Delete temporary table ---
    logger.info(f"Step 10: Deleting temporary table '{TEMP_TABLE_NAME}'...")
    delete_table(client, TEMP_TABLE_NAME)

    # --- Done ---
    logger.info(f"{'=' * 60}")
    logger.info("Migration Complete!")
    logger.info(f"  Table '{table_name}' recreated with:")
    logger.info(f"    Partition key: product_id (String)")
    logger.info(f"    GSI: {GSI_NAME} on {GSI_KEY} (String)")
    logger.info(f"    BillingMode: PAY_PER_REQUEST")
    logger.info(f"    Records: {total_count}")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recreate Producten table with product_id as partition key"
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help=f"AWS CLI profile to use (default: {DEFAULT_PROFILE})",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE_NAME,
        help=f"Producten table name (default: {DEFAULT_TABLE_NAME})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only scan and verify records without creating/deleting tables",
    )
    args = parser.parse_args()

    recreate_producten_table(
        dry_run=args.dry_run,
        profile=args.profile,
        table_name=args.table,
    )
