#!/usr/bin/env python3
"""
Clean the Orders table and replace the event-club-index GSI with event-member-index.

This script performs the full infrastructure migration for the generic event booking system:
1. Deletes all records from the Orders table (all existing orders are test data)
2. Deletes the old `event-club-index` GSI (if it exists)
3. Creates the new `event-member-index` GSI (PK: source_id, SK: member_id, Projection: ALL)
4. Waits for the new GSI to become ACTIVE
5. Verifies the GSI works with a test query

Prerequisites:
    - AWS profile `nonprofit-deploy` configured
    - The Orders table must exist in the target account

Usage:
    # Run against test environment
    python backend/scripts/clean_orders_and_replace_gsi.py --stage test

    # Run against production (use with care!)
    python backend/scripts/clean_orders_and_replace_gsi.py --stage prod

    # Check current GSI status only
    python backend/scripts/clean_orders_and_replace_gsi.py --stage test --status
"""

import argparse
import sys
import time

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"

OLD_GSI_NAME = "event-club-index"
NEW_GSI_NAME = "event-member-index"
NEW_GSI_PK = "source_id"
NEW_GSI_SK = "member_id"

STAGE_TABLE_MAP = {
    "test": "Orders-Test",
    "prod": "Orders",
}


def get_table_name(stage: str) -> str:
    """Map stage to DynamoDB table name."""
    if stage not in STAGE_TABLE_MAP:
        print(f"❌ Invalid stage '{stage}'. Must be 'test' or 'prod'.")
        sys.exit(1)
    return STAGE_TABLE_MAP[stage]


def get_session(profile: str = PROFILE) -> boto3.Session:
    """Create a boto3 session with the specified profile."""
    return boto3.Session(profile_name=profile, region_name=REGION)


def confirm_action(message: str) -> bool:
    """Ask the user to confirm a destructive action."""
    response = input(f"\n⚠️  {message}\n   Type 'yes' to confirm: ")
    return response.strip().lower() == "yes"


# --- Delete all records ---


def delete_all_records(session: boto3.Session, table_name: str) -> None:
    """Delete all records from the Orders table using scan + batch delete."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n📋 Scanning table '{table_name}' for existing records...")

    # Count records first
    total_count = 0
    scan_kwargs = {"Select": "COUNT"}
    while True:
        response = table.scan(**scan_kwargs)
        total_count += response["Count"]
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    if total_count == 0:
        print("   ✅ Table is already empty. Nothing to delete.")
        return

    print(f"   Found {total_count} records to delete.")

    if not confirm_action(f"Delete ALL {total_count} records from '{table_name}'?"):
        print("   ⏭️  Skipping record deletion.")
        return

    # Scan and batch delete
    deleted_count = 0
    scan_kwargs = {"ProjectionExpression": "order_id"}

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        if not items:
            break

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"order_id": item["order_id"]})
                deleted_count += 1

        print(f"   Deleted {deleted_count} records so far...")

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"   ✅ Deleted {deleted_count} records from '{table_name}'.")


# --- Delete old GSI ---


def delete_old_gsi(session: boto3.Session, table_name: str) -> None:
    """Delete the old event-club-index GSI if it exists."""
    client = session.client("dynamodb", region_name=REGION)

    print(f"\n🔍 Checking for old GSI '{OLD_GSI_NAME}' on '{table_name}'...")

    try:
        response = client.describe_table(TableName=table_name)
        gsis = response["Table"].get("GlobalSecondaryIndexes", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"   ❌ Table '{table_name}' not found.")
            sys.exit(1)
        raise

    old_gsi = next((g for g in gsis if g["IndexName"] == OLD_GSI_NAME), None)

    if old_gsi is None:
        print(f"   ℹ️  GSI '{OLD_GSI_NAME}' does not exist. Nothing to delete.")
        return

    status = old_gsi.get("IndexStatus", "UNKNOWN")
    print(f"   Found GSI '{OLD_GSI_NAME}' (status: {status}).")

    if not confirm_action(f"Delete GSI '{OLD_GSI_NAME}' from '{table_name}'?"):
        print("   ⏭️  Skipping GSI deletion.")
        return

    try:
        client.update_table(
            TableName=table_name,
            GlobalSecondaryIndexUpdates=[{"Delete": {"IndexName": OLD_GSI_NAME}}],
        )
        print(f"   ✅ GSI '{OLD_GSI_NAME}' deletion initiated.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(f"   ❌ Failed to delete GSI: [{error_code}] {error_message}")
        sys.exit(1)

    # Wait for deletion to complete
    print("   ⏳ Waiting for GSI deletion to complete...")
    _wait_for_gsi_deletion(client, table_name)


def _wait_for_gsi_deletion(client, table_name: str, timeout: int = 300) -> None:
    """Wait until the old GSI is fully removed from the table."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = client.describe_table(TableName=table_name)
            gsis = response["Table"].get("GlobalSecondaryIndexes", [])
            old_gsi = next((g for g in gsis if g["IndexName"] == OLD_GSI_NAME), None)

            if old_gsi is None:
                print("   ✅ GSI deletion complete.")
                return

            status = old_gsi.get("IndexStatus", "UNKNOWN")
            elapsed = int(time.time() - start_time)
            print(f"   [{elapsed}s] GSI status: {status}")
        except ClientError:
            # Table might be in UPDATING state
            pass

        time.sleep(10)

    print(f"   ⚠️  Timeout ({timeout}s) — GSI may still be deleting. Check with --status.")


# --- Create new GSI ---


def create_new_gsi(session: boto3.Session, table_name: str) -> None:
    """Create the new event-member-index GSI."""
    client = session.client("dynamodb", region_name=REGION)

    print(f"\n🚀 Creating new GSI '{NEW_GSI_NAME}' on '{table_name}'...")
    print(f"   PK: {NEW_GSI_PK} (String)")
    print(f"   SK: {NEW_GSI_SK} (String)")
    print(f"   Projection: ALL")

    # Check if it already exists
    try:
        response = client.describe_table(TableName=table_name)
        gsis = response["Table"].get("GlobalSecondaryIndexes", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"   ❌ Table '{table_name}' not found.")
            sys.exit(1)
        raise

    existing = next((g for g in gsis if g["IndexName"] == NEW_GSI_NAME), None)
    if existing:
        status = existing.get("IndexStatus", "UNKNOWN")
        print(f"   ✅ GSI '{NEW_GSI_NAME}' already exists (status: {status}). Skipping creation.")
        return

    try:
        client.update_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": NEW_GSI_PK, "AttributeType": "S"},
                {"AttributeName": NEW_GSI_SK, "AttributeType": "S"},
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    "Create": {
                        "IndexName": NEW_GSI_NAME,
                        "KeySchema": [
                            {"AttributeName": NEW_GSI_PK, "KeyType": "HASH"},
                            {"AttributeName": NEW_GSI_SK, "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                }
            ],
        )
        print(f"   ✅ GSI '{NEW_GSI_NAME}' creation initiated.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(f"   ❌ Failed to create GSI: [{error_code}] {error_message}")
        sys.exit(1)


# --- Wait for GSI to become ACTIVE ---


def wait_for_gsi_active(session: boto3.Session, table_name: str, timeout: int = 600) -> None:
    """Wait for the new GSI to become ACTIVE."""
    client = session.client("dynamodb", region_name=REGION)

    print(f"\n⏳ Waiting for GSI '{NEW_GSI_NAME}' to become ACTIVE (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = client.describe_table(TableName=table_name)
            gsis = response["Table"].get("GlobalSecondaryIndexes", [])
            new_gsi = next((g for g in gsis if g["IndexName"] == NEW_GSI_NAME), None)

            if new_gsi is None:
                print("   ❌ GSI not found — creation may have failed.")
                sys.exit(1)

            status = new_gsi.get("IndexStatus", "UNKNOWN")
            elapsed = int(time.time() - start_time)
            print(f"   [{elapsed}s] Status: {status}")

            if status == "ACTIVE":
                print(f"   ✅ GSI '{NEW_GSI_NAME}' is now ACTIVE and ready for queries.")
                return
        except ClientError:
            pass

        time.sleep(10)

    print(f"   ⚠️  Timeout ({timeout}s). GSI may still be creating. Use --status to check.")


# --- Verify GSI with a test query ---


def verify_gsi(session: boto3.Session, table_name: str) -> None:
    """Verify the GSI works by performing a test query."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n🧪 Verifying GSI '{NEW_GSI_NAME}' with a test query...")

    try:
        from boto3.dynamodb.conditions import Key

        response = table.query(
            IndexName=NEW_GSI_NAME,
            KeyConditionExpression=Key(NEW_GSI_PK).eq("__test_verification__"),
            Limit=1,
        )
        print(f"   ✅ Query successful. Returned {response['Count']} items (expected 0 for test key).")
        print(f"   GSI is operational and ready for use.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(f"   ❌ Query failed: [{error_code}] {error_message}")
        sys.exit(1)


# --- Status check ---


def print_status(session: boto3.Session, table_name: str) -> None:
    """Print the current status of GSIs on the table."""
    client = session.client("dynamodb", region_name=REGION)

    print(f"\n📊 GSI Status for table '{table_name}':")

    try:
        response = client.describe_table(TableName=table_name)
        gsis = response["Table"].get("GlobalSecondaryIndexes", [])
        item_count = response["Table"].get("ItemCount", 0)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"   ❌ Table '{table_name}' not found in region {REGION}.")
            return
        raise

    print(f"   Table item count: {item_count}")
    print()

    if not gsis:
        print("   No GSIs found on this table.")
        return

    for gsi in gsis:
        print(f"   📌 {gsi['IndexName']}")
        print(f"      Status:     {gsi.get('IndexStatus', 'UNKNOWN')}")
        print(f"      Items:      {gsi.get('ItemCount', 0)}")
        print(f"      Size:       {gsi.get('IndexSizeBytes', 0)} bytes")
        print(f"      Key Schema:")
        for key in gsi.get("KeySchema", []):
            print(f"        - {key['AttributeName']} ({key['KeyType']})")
        print(f"      Projection: {gsi.get('Projection', {}).get('ProjectionType', 'N/A')}")
        print()


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Clean the Orders table and replace event-club-index GSI with event-member-index. "
            "Part of the generic event booking system migration."
        )
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["test", "prod"],
        help="Target stage: 'test' → Orders-Test, 'prod' → Orders",
    )
    parser.add_argument(
        "--profile",
        default=PROFILE,
        help=f"AWS CLI profile to use (default: {PROFILE})",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Only show current GSI status, don't make any changes",
    )
    parser.add_argument(
        "--skip-delete-records",
        action="store_true",
        help="Skip the record deletion step",
    )
    parser.add_argument(
        "--skip-delete-gsi",
        action="store_true",
        help="Skip the old GSI deletion step",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for waiting on GSI operations (default: 600)",
    )
    args = parser.parse_args()

    table_name = get_table_name(args.stage)
    session = get_session(args.profile)

    print("=" * 60)
    print("🔧 Orders Table Cleanup & GSI Replacement")
    print("=" * 60)
    print(f"   Stage:   {args.stage}")
    print(f"   Table:   {table_name}")
    print(f"   Profile: {args.profile}")
    print(f"   Region:  {REGION}")
    print("=" * 60)

    if args.status:
        print_status(session, table_name)
        return

    # Step 1: Delete all records
    if not args.skip_delete_records:
        delete_all_records(session, table_name)
    else:
        print("\n⏭️  Skipping record deletion (--skip-delete-records).")

    # Step 2: Delete old GSI
    if not args.skip_delete_gsi:
        delete_old_gsi(session, table_name)
    else:
        print("\n⏭️  Skipping old GSI deletion (--skip-delete-gsi).")

    # Step 3: Create new GSI
    create_new_gsi(session, table_name)

    # Step 4: Wait for GSI to become ACTIVE
    wait_for_gsi_active(session, table_name, timeout=args.timeout)

    # Step 5: Verify GSI with a test query
    verify_gsi(session, table_name)

    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print(f"   Table '{table_name}' is clean and has the new '{NEW_GSI_NAME}' GSI.")
    print("=" * 60)


if __name__ == "__main__":
    main()
