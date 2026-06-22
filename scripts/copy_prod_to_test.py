"""
Copy production DynamoDB table data to -Test tables.

Scans each production table and batch-writes all items to the corresponding -Test table.
Overwrites existing data in -Test tables.

Usage:
  python scripts/copy_prod_to_test.py --dry-run --profile nonprofit-deploy
  python scripts/copy_prod_to_test.py --profile nonprofit-deploy
"""

import argparse
import boto3
import sys
import time

REGION = "eu-west-1"

TABLES = [
    "Members",
    "Producten",
    "Orders",
    "Events",
    "Payments",
    "Memberships",
    "Carts",
    "Counters",
    "StockMovements",
]


def scan_all_items(table):
    """Scan all items from a DynamoDB table with pagination."""
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def batch_write_items(table, items):
    """Write items in batches of 25 (DynamoDB limit)."""
    written = 0
    for i in range(0, len(items), 25):
        batch = items[i:i + 25]
        with table.batch_writer() as writer:
            for item in batch:
                writer.put_item(Item=item)
        written += len(batch)
        # Small delay to avoid throttling
        if written % 100 == 0 and written > 0:
            time.sleep(0.5)
    return written


def copy_table(dynamodb, source_name, target_name, dry_run):
    """Copy all items from source table to target table."""
    source = dynamodb.Table(source_name)
    target = dynamodb.Table(target_name)

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Copying {source_name} → {target_name}")

    # Scan source
    items = scan_all_items(source)
    print(f"  Scanned: {len(items)} items from {source_name}")

    if len(items) == 0:
        print(f"  Skipping (empty table)")
        return 0

    if dry_run:
        print(f"  Would write {len(items)} items to {target_name}")
        return len(items)

    # Write to target
    written = batch_write_items(target, items)
    print(f"  Written: {written} items to {target_name}")
    return written


def main():
    parser = argparse.ArgumentParser(
        description="Copy production DynamoDB data to -Test tables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be copied without writing",
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS profile to use (default: nonprofit-deploy)",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        help="Specific tables to copy (default: all)",
    )
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = session.resource("dynamodb")

    tables_to_copy = args.tables if args.tables else TABLES
    mode = "[DRY-RUN]" if args.dry_run else "[LIVE]"

    print(f"\n{mode} Copying production data to -Test tables")
    print(f"  Profile: {args.profile}")
    print(f"  Region: {REGION}")
    print(f"  Tables: {', '.join(tables_to_copy)}")

    total_items = 0
    for table_name in tables_to_copy:
        target_name = f"{table_name}-Test"
        try:
            copied = copy_table(dynamodb, table_name, target_name, args.dry_run)
            total_items += copied
        except Exception as e:
            print(f"  ERROR copying {table_name}: {e}")
            if not args.dry_run:
                print("  Stopping on error.")
                sys.exit(1)

    print(f"\n{mode} Done! Total items {'would be ' if args.dry_run else ''}copied: {total_items}")


if __name__ == "__main__":
    main()
