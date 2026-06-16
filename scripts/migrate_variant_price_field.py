#!/usr/bin/env python3
"""
Variant Price Field Migration Script.

Renames the `price` attribute to `prijs` on existing variant records
in the Producten DynamoDB table, aligning with the Dutch field name convention.

Only targets variant records (is_parent = false) that still have a `price`
attribute. Parent products already use `prijs`.

Behavior:
  - Default mode is dry-run (shows what would change without modifying data)
  - Pass --apply to actually write changes to DynamoDB
  - Logs each record that would be/was modified (product_id, old price value)
  - Prints summary at the end (total scanned, total modified)

Usage:
    # Dry-run (default) -- preview changes
    python scripts/migrate_variant_price_field.py

    # Apply changes
    python scripts/migrate_variant_price_field.py --apply

    # Custom profile / table
    python scripts/migrate_variant_price_field.py --apply --profile nonprofit-deploy --table Producten
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import boto3

REGION = "eu-west-1"
DEFAULT_TABLE_NAME = "Producten"
DEFAULT_PROFILE = "nonprofit-deploy"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationSummary:
    """Summary of migration results."""

    total_scanned: int = 0
    variants_scanned: int = 0
    records_migrated: int = 0
    records_skipped: int = 0
    errors: list[dict] = field(default_factory=list)


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def scan_variant_records(table) -> list[dict]:
    """Scan for variant records (is_parent = false) that have a 'price' attribute."""
    items = []
    # Use FilterExpression to only return variants with a price attribute
    scan_kwargs = {
        "FilterExpression": "is_parent = :false AND attribute_exists(price)",
        "ExpressionAttributeValues": {":false": False},
    }

    response = table.scan(**scan_kwargs)
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
    return items


def get_total_count(table) -> int:
    """Get total item count from table (approximate)."""
    response = table.scan(Select="COUNT")
    count = response.get("Count", 0)
    while "LastEvaluatedKey" in response:
        response = table.scan(
            Select="COUNT", ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        count += response.get("Count", 0)
    return count


def migrate_record(table, item: dict, apply: bool) -> bool:
    """Migrate a single variant record: copy price → prijs, remove price.

    Returns True if the record was (or would be) migrated.
    """
    product_id = item.get("product_id")
    price_value = item.get("price")

    if not product_id:
        return False

    # If prijs already exists, skip to avoid overwriting
    if "prijs" in item:
        logger.info(
            f"  SKIP {product_id}: already has 'prijs' attribute "
            f"(price={price_value}, prijs={item['prijs']})"
        )
        return False

    if apply:
        logger.info(
            f"  MIGRATING {product_id}: price={price_value} -> prijs={price_value}"
        )
        table.update_item(
            Key={"product_id": product_id},
            UpdateExpression="SET #prijs = :prijs, #updated_at = :updated_at REMOVE #price",
            ExpressionAttributeNames={
                "#prijs": "prijs",
                "#price": "price",
                "#updated_at": "updated_at",
            },
            ExpressionAttributeValues={
                ":prijs": price_value,
                ":updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    else:
        logger.info(
            f"  [DRY RUN] Would migrate {product_id}: price={price_value} -> prijs={price_value}"
        )

    return True


def run_migration(
    apply: bool = False,
    profile: str | None = DEFAULT_PROFILE,
    table_name: str = DEFAULT_TABLE_NAME,
) -> MigrationSummary:
    """Main migration function.

    Scans variant records in the Producten table and renames price → prijs.

    Args:
        apply: If True, writes changes to DynamoDB. If False, dry-run only.
        profile: AWS CLI profile name.
        table_name: DynamoDB table name.

    Returns:
        MigrationSummary with counts and any errors.
    """
    summary = MigrationSummary()

    dynamodb = get_dynamodb_resource(profile)
    table = dynamodb.Table(table_name)

    mode = "APPLY" if apply else "DRY RUN"
    logger.info(f"{'=' * 60}")
    logger.info(f"Variant Price Field Migration [{mode}]")
    logger.info(f"Table: {table_name} | Profile: {profile} | Region: {REGION}")
    logger.info(f"{'=' * 60}")

    # Get total count for context
    logger.info("Scanning for variant records with 'price' attribute...")
    summary.total_scanned = get_total_count(table)

    # Scan only variants that have a price attribute
    variants_with_price = scan_variant_records(table)
    summary.variants_scanned = len(variants_with_price)

    logger.info(
        f"Found {summary.variants_scanned} variant records with 'price' attribute "
        f"(out of {summary.total_scanned} total table items)"
    )

    if not variants_with_price:
        logger.info("No records to migrate. All variants already use 'prijs'.")
        return summary

    logger.info("")
    logger.info("Processing records:")

    for item in variants_with_price:
        product_id = item.get("product_id", "unknown")
        try:
            migrated = migrate_record(table, item, apply)
            if migrated:
                summary.records_migrated += 1
            else:
                summary.records_skipped += 1
        except Exception as e:
            logger.error(f"  ERROR {product_id}: {e}")
            summary.errors.append({"product_id": str(product_id), "error": str(e)})

    return summary


def print_summary(summary: MigrationSummary, apply: bool):
    """Print a human-readable summary of the migration."""
    mode = "APPLIED" if apply else "DRY RUN"
    print(f"\n{'=' * 60}")
    print(f"  Variant Price -> Prijs Migration [{mode}]")
    print(f"{'=' * 60}")
    print(f"  Total table items:          {summary.total_scanned}")
    print(f"  Variants with 'price':      {summary.variants_scanned}")
    print(f"  Records migrated:           {summary.records_migrated}")
    print(f"  Records skipped:            {summary.records_skipped}")
    print(f"  Errors:                     {len(summary.errors)}")
    if summary.errors:
        print(f"\n  Error details:")
        for err in summary.errors:
            print(f"    {err['product_id']}: {err['error']}")
    if not apply and summary.records_migrated > 0:
        print(f"\n  NOTE: This was a dry run. Use --apply to execute the migration.")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Rename 'price' to 'prijs' on variant records in the Producten table. "
            "Runs in dry-run mode by default."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually write changes to DynamoDB. Without this flag, only previews changes.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=DEFAULT_PROFILE,
        help=f"AWS CLI profile (default: {DEFAULT_PROFILE}).",
    )
    parser.add_argument(
        "--table",
        type=str,
        default=DEFAULT_TABLE_NAME,
        help=f"DynamoDB table name (default: {DEFAULT_TABLE_NAME}).",
    )
    args = parser.parse_args()

    summary = run_migration(
        apply=args.apply,
        profile=args.profile,
        table_name=args.table,
    )
    print_summary(summary, args.apply)

    if summary.errors:
        exit(1)


if __name__ == "__main__":
    main()
