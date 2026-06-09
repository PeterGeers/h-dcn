#!/usr/bin/env python3
"""
Create the `event-club-index` GSI on the Orders DynamoDB table.

This GSI enables efficient queries for:
- Finding an order by club_id + event_id (used by presmeet_get_order)
- Listing all orders for a given event (used by submit validation and reports)

GSI Definition:
    Name:       event-club-index
    Partition:  event_id (S)
    Sort:       club_id (S)
    Projection: ALL
    Billing:    PAY_PER_REQUEST (inherits from table)

Prerequisites:
    - The Orders table must exist in the target AWS account
    - The AWS profile must have dynamodb:UpdateTable and dynamodb:DescribeTable permissions

Usage:
    # Preview what would be created (no changes)
    python backend/scripts/create_event_club_gsi.py --dry-run

    # Create the GSI using the nonprofit-deploy profile
    python backend/scripts/create_event_club_gsi.py

    # Use a different profile
    python backend/scripts/create_event_club_gsi.py --profile nonprofit-admin

    # Check GSI status
    python backend/scripts/create_event_club_gsi.py --status
"""

import argparse
import sys
import time

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
TABLE_NAME = "Orders"
GSI_NAME = "event-club-index"
GSI_PK = "event_id"
GSI_SK = "club_id"


def get_dynamodb_client(profile: str | None = None):
    """Create a DynamoDB client with the specified profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    return session.client("dynamodb", region_name=REGION)


def get_existing_gsis(client) -> list[dict]:
    """Get the list of existing GSIs on the Orders table."""
    try:
        response = client.describe_table(TableName=TABLE_NAME)
        return response["Table"].get("GlobalSecondaryIndexes", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"❌ Table '{TABLE_NAME}' not found in region {REGION}.")
            sys.exit(1)
        raise


def gsi_exists(client) -> dict | None:
    """Check if the event-club-index GSI already exists. Returns GSI info or None."""
    gsis = get_existing_gsis(client)
    for gsi in gsis:
        if gsi["IndexName"] == GSI_NAME:
            return gsi
    return None


def print_gsi_status(client) -> None:
    """Print the current status of the GSI."""
    gsi = gsi_exists(client)
    if gsi is None:
        print(f"ℹ️  GSI '{GSI_NAME}' does not exist on table '{TABLE_NAME}'.")
        return

    status = gsi.get("IndexStatus", "UNKNOWN")
    item_count = gsi.get("ItemCount", 0)
    size_bytes = gsi.get("IndexSizeBytes", 0)

    print(f"📊 GSI '{GSI_NAME}' on table '{TABLE_NAME}':")
    print(f"   Status:     {status}")
    print(f"   Items:      {item_count}")
    print(f"   Size:       {size_bytes} bytes")
    print(f"   Key Schema:")
    for key in gsi.get("KeySchema", []):
        print(f"     - {key['AttributeName']} ({key['KeyType']})")
    print(f"   Projection: {gsi.get('Projection', {}).get('ProjectionType', 'N/A')}")


def create_gsi(client, dry_run: bool = False) -> None:
    """Create the event-club-index GSI on the Orders table."""
    # Check if GSI already exists
    existing = gsi_exists(client)
    if existing:
        status = existing.get("IndexStatus", "UNKNOWN")
        print(f"✅ GSI '{GSI_NAME}' already exists (status: {status}). Nothing to do.")
        return

    gsi_definition = {
        "Create": {
            "IndexName": GSI_NAME,
            "KeySchema": [
                {"AttributeName": GSI_PK, "KeyType": "HASH"},
                {"AttributeName": GSI_SK, "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    }

    attribute_definitions = [
        {"AttributeName": GSI_PK, "AttributeType": "S"},
        {"AttributeName": GSI_SK, "AttributeType": "S"},
    ]

    print(f"{'🔍 DRY RUN' if dry_run else '🚀 CREATING GSI'}")
    print(f"   Table:      {TABLE_NAME}")
    print(f"   GSI Name:   {GSI_NAME}")
    print(f"   PK:         {GSI_PK} (String)")
    print(f"   SK:         {GSI_SK} (String)")
    print(f"   Projection: ALL")
    print(f"   Region:     {REGION}")
    print()

    if dry_run:
        print("🔍 Dry run complete — no changes made.")
        print("   Run without --dry-run to create the GSI.")
        return

    try:
        client.update_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=attribute_definitions,
            GlobalSecondaryIndexUpdates=[gsi_definition],
        )
        print(f"✅ GSI '{GSI_NAME}' creation initiated.")
        print("   The GSI will take a few minutes to become ACTIVE.")
        print("   Use --status to check progress.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(f"❌ Failed to create GSI: [{error_code}] {error_message}")
        sys.exit(1)


def wait_for_gsi(client, timeout: int = 300) -> None:
    """Wait for the GSI to become ACTIVE."""
    print(f"⏳ Waiting for GSI '{GSI_NAME}' to become ACTIVE (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        gsi = gsi_exists(client)
        if gsi is None:
            print("❌ GSI not found — creation may have failed.")
            sys.exit(1)

        status = gsi.get("IndexStatus", "UNKNOWN")
        elapsed = int(time.time() - start_time)
        print(f"   [{elapsed}s] Status: {status}")

        if status == "ACTIVE":
            print(f"✅ GSI '{GSI_NAME}' is now ACTIVE and queryable.")
            return

        time.sleep(10)

    print(f"⚠️  Timeout reached ({timeout}s). GSI may still be creating.")
    print("   Use --status to check later.")


def main():
    parser = argparse.ArgumentParser(
        description=(
            f"Create the '{GSI_NAME}' GSI on the {TABLE_NAME} DynamoDB table. "
            "This index enables efficient queries by event_id + club_id."
        )
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check the current status of the GSI",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the GSI to become ACTIVE after creation",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for --wait (default: 300)",
    )
    args = parser.parse_args()

    print(f"🔧 Event-Club GSI Management — Table: {TABLE_NAME}, Region: {REGION}")
    if args.profile:
        print(f"   Profile: {args.profile}")
    print()

    client = get_dynamodb_client(args.profile)

    if args.status:
        print_gsi_status(client)
        return

    create_gsi(client, dry_run=args.dry_run)

    if args.wait and not args.dry_run:
        print()
        wait_for_gsi(client, timeout=args.timeout)


if __name__ == "__main__":
    main()
