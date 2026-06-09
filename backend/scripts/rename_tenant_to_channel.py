#!/usr/bin/env python3
"""
Rename `tenant` field to `channel` across DynamoDB tables.

Part of the PresMeet v3 channel rename migration (Requirement 16).
For each record in the target tables:
  - If the record already has a `channel` field → skip (idempotent)
  - If the record has a `tenant` field → copy value to `channel`, remove `tenant`
  - If the record has neither → set `channel` to "h-dcn" (default)

Tables migrated:
    - Orders      (PK: order_id)
    - Producten   (PK: product_id)
    - Carts       (PK: cart_id)
    - StockMovements (PK: movement_id)

Prerequisites:
    - The AWS profile must have dynamodb:Scan and dynamodb:UpdateItem permissions
    - Tables must exist in the target account (eu-west-1)

Usage:
    # Preview changes (no modifications)
    python backend/scripts/rename_tenant_to_channel.py --dry-run

    # Migrate all tables
    python backend/scripts/rename_tenant_to_channel.py

    # Migrate a single table (useful for testing)
    python backend/scripts/rename_tenant_to_channel.py --table Orders

    # Use a different profile
    python backend/scripts/rename_tenant_to_channel.py --profile nonprofit-admin

Deployment:
    Run AFTER code deploy (handlers already expect `channel`) and BEFORE
    routing traffic, so records are migrated before they are read.
"""

import argparse
import sys
import time

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
DEFAULT_CHANNEL = "h-dcn"

# Table name → primary key attribute name
# NOTE: This is a fallback. The script now auto-detects keys via describe_table().
TABLES = {
    "Orders": "order_id",
    "Producten": "product_id",
    "Carts": "cart_id",
    "StockMovements": "movement_id",
}


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with the specified profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def get_table_key_schema(table) -> list[dict]:
    """
    Get the key schema from DynamoDB table metadata.

    Returns list of key attributes, e.g.:
        [{"name": "product_id", "type": "HASH"}, {"name": "variant_id", "type": "RANGE"}]
    """
    key_schema = table.key_schema or []
    return [
        {"name": ks["AttributeName"], "type": ks["KeyType"]}
        for ks in key_schema
    ]


def build_key_from_record(record: dict, key_schema: list[dict]) -> dict | None:
    """
    Build the DynamoDB Key dict from a scanned record using the table's key schema.

    Returns None if any key attribute is missing from the record.
    """
    key = {}
    for ks in key_schema:
        attr_name = ks["name"]
        if attr_name not in record:
            return None
        key[attr_name] = record[attr_name]
    return key


def scan_all_items(table) -> list[dict]:
    """Scan all items from a DynamoDB table, handling pagination."""
    items = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def classify_record(record: dict) -> str:
    """
    Classify a record for migration action.

    Returns:
        "skip"    — already has `channel` field (no action needed)
        "rename"  — has `tenant` but no `channel` (copy tenant → channel, remove tenant)
        "default" — has neither field (set channel to default)
    """
    if "channel" in record:
        return "skip"
    elif "tenant" in record:
        return "rename"
    else:
        return "default"


def migrate_table(
    dynamodb,
    table_name: str,
    pk_field: str,
    dry_run: bool = False,
) -> dict:
    """
    Migrate a single table: rename `tenant` → `channel`.

    Uses describe_table() to auto-detect the full key schema (including sort key
    if present), so UpdateItem uses the correct Key.

    Returns a summary dict with counts.
    """
    print(f"\n{'─' * 60}")
    print(f"📋 Table: {table_name}")
    print(f"{'─' * 60}")

    try:
        table = dynamodb.Table(table_name)
        # Verify table exists by loading metadata (also populates key_schema)
        table.load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"  ⚠️  Table '{table_name}' not found — skipping.")
            return {"total": 0, "skipped": 0, "renamed": 0, "defaulted": 0, "errors": 0}
        raise

    # Auto-detect key schema from table metadata
    key_schema = get_table_key_schema(table)
    key_names = [ks["name"] for ks in key_schema]
    print(f"  Key schema: {key_names} (auto-detected)")

    print(f"  Scanning all records...")
    items = scan_all_items(table)
    total = len(items)
    print(f"  Found {total} records.")

    skipped = 0
    renamed = 0
    defaulted = 0
    errors = 0

    for i, record in enumerate(items, 1):
        # Build the full key from the record using auto-detected schema
        key = build_key_from_record(record, key_schema)
        if key is None:
            missing = [ks["name"] for ks in key_schema if ks["name"] not in record]
            print(f"  ❌ Record at index {i} missing key attribute(s) {missing} — skipping.")
            errors += 1
            continue

        # Human-readable key for logging
        key_display = ", ".join(f"{k}={v}" for k, v in key.items())

        action = classify_record(record)

        if action == "skip":
            skipped += 1
            continue

        if action == "rename":
            channel_value = record["tenant"]
            if dry_run:
                print(f"  [DRY RUN] {key_display}: tenant='{channel_value}' → channel='{channel_value}' (remove tenant)")
                renamed += 1
            else:
                try:
                    table.update_item(
                        Key=key,
                        UpdateExpression="SET #channel = :val REMOVE #tenant",
                        ExpressionAttributeNames={
                            "#channel": "channel",
                            "#tenant": "tenant",
                        },
                        ExpressionAttributeValues={
                            ":val": channel_value,
                        },
                        ConditionExpression="attribute_not_exists(#channel)",
                    )
                    renamed += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                        # Another process already migrated this record — idempotent
                        skipped += 1
                    else:
                        print(f"  ❌ Error updating {key_display}: {e.response['Error']['Message']}")
                        errors += 1

        elif action == "default":
            if dry_run:
                print(f"  [DRY RUN] {key_display}: no tenant → channel='{DEFAULT_CHANNEL}' (default)")
                defaulted += 1
            else:
                try:
                    table.update_item(
                        Key=key,
                        UpdateExpression="SET #channel = :val",
                        ExpressionAttributeNames={
                            "#channel": "channel",
                        },
                        ExpressionAttributeValues={
                            ":val": DEFAULT_CHANNEL,
                        },
                        ConditionExpression="attribute_not_exists(#channel)",
                    )
                    defaulted += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                        skipped += 1
                    else:
                        print(f"  ❌ Error updating {key_display}: {e.response['Error']['Message']}")
                        errors += 1

        # Progress reporting every 50 records
        if i % 50 == 0:
            print(f"  Progress: {i} of {total} records processed...")

    return {
        "total": total,
        "skipped": skipped,
        "renamed": renamed,
        "defaulted": defaulted,
        "errors": errors,
    }


def print_summary(results: dict[str, dict]) -> None:
    """Print a summary table of all migration results."""
    print(f"\n{'═' * 60}")
    print("📊 MIGRATION SUMMARY")
    print(f"{'═' * 60}")
    print(f"  {'Table':<18} {'Total':>6} {'Skipped':>8} {'Renamed':>8} {'Defaulted':>10} {'Errors':>7}")
    print(f"  {'─' * 57}")

    totals = {"total": 0, "skipped": 0, "renamed": 0, "defaulted": 0, "errors": 0}
    for table_name, counts in results.items():
        print(
            f"  {table_name:<18} {counts['total']:>6} {counts['skipped']:>8} "
            f"{counts['renamed']:>8} {counts['defaulted']:>10} {counts['errors']:>7}"
        )
        for key in totals:
            totals[key] += counts[key]

    print(f"  {'─' * 57}")
    print(
        f"  {'TOTAL':<18} {totals['total']:>6} {totals['skipped']:>8} "
        f"{totals['renamed']:>8} {totals['defaulted']:>10} {totals['errors']:>7}"
    )

    if totals["errors"] > 0:
        print(f"\n  ⚠️  {totals['errors']} errors occurred. Review output above.")
    else:
        print(f"\n  ✅ Migration completed successfully.")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Rename the `tenant` field to `channel` across DynamoDB tables. "
            "Records already having `channel` are skipped (idempotent). "
            "Records with no `tenant` field get channel='h-dcn' as default."
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
        help="Preview what would be changed without making modifications",
    )
    parser.add_argument(
        "--table",
        choices=list(TABLES.keys()),
        help="Process only a single table (useful for testing)",
    )
    args = parser.parse_args()

    mode = "🔍 DRY RUN" if args.dry_run else "🚀 LIVE MIGRATION"
    print(f"{'═' * 60}")
    print(f"  {mode} — Rename tenant → channel")
    print(f"  Region:  {REGION}")
    print(f"  Profile: {args.profile}")
    print(f"  Default: Records without tenant get channel='{DEFAULT_CHANNEL}'")
    if args.table:
        print(f"  Table:   {args.table} only")
    else:
        print(f"  Tables:  {', '.join(TABLES.keys())}")
    print(f"{'═' * 60}")

    if not args.dry_run:
        print("\n  ⚠️  This will modify production data. Press Ctrl+C to abort.\n")

    dynamodb = get_dynamodb_resource(args.profile)

    # Determine which tables to process
    tables_to_process = {args.table: TABLES[args.table]} if args.table else TABLES

    results = {}
    start_time = time.time()

    for table_name, pk_field in tables_to_process.items():
        results[table_name] = migrate_table(
            dynamodb=dynamodb,
            table_name=table_name,
            pk_field=pk_field,
            dry_run=args.dry_run,
        )

    elapsed = time.time() - start_time
    print_summary(results)
    print(f"\n  ⏱️  Elapsed: {elapsed:.1f}s")

    if args.dry_run:
        print("\n  🔍 Dry run complete — no changes were made.")
        print("  Run without --dry-run to apply the migration.")

    # Exit with non-zero if there were errors
    total_errors = sum(r["errors"] for r in results.values())
    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
