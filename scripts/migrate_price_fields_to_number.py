#!/usr/bin/env python3
"""
Price Fields to Number Type Migration Script.

Converts string-typed price fields to DynamoDB Number type (Decimal) in
the Producten and Orders tables. This ensures all historical data is
consistent with the new backend validation rules that enforce numeric types.

Tables and fields:
  - Producten: `prijs` field (stored as string in some records)
  - Orders: `items[].price` and `items[].unit_price` (stored as string in some records)

Behavior:
  - Default mode is dry-run (shows what would change without modifying data)
  - Pass without --dry-run to actually write changes to DynamoDB
  - Handles DynamoDB pagination (LastEvaluatedKey) for tables > 1MB
  - Skips non-parseable strings (logged as errors)
  - Prints summary at the end (scanned, converted, skipped, errors)

Usage:
    # Dry-run (default) -- preview changes
    python scripts/migrate_price_fields_to_number.py --dry-run

    # Apply changes
    python scripts/migrate_price_fields_to_number.py

    # Custom profile
    python scripts/migrate_price_fields_to_number.py --profile nonprofit-deploy
"""

from __future__ import annotations

import argparse
import logging
from decimal import Decimal, InvalidOperation

import boto3

REGION = "eu-west-1"
DEFAULT_PROFILE = "nonprofit-deploy"
PRODUCTEN_TABLE = "Producten"
ORDERS_TABLE = "Orders"

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


def migrate_producten_table(table, dry_run: bool) -> dict:
    """Scan Producten table, find records where prijs is stored as string, convert to Number.

    Returns dict with counts: scanned, converted, skipped, errors.
    """
    counts = {"scanned": 0, "converted": 0, "skipped": 0, "errors": 0}

    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            counts["scanned"] += 1
            product_id = item.get("product_id", "unknown")
            prijs = item.get("prijs")

            # Skip if prijs is absent or already a numeric type
            if prijs is None:
                counts["skipped"] += 1
                continue

            if isinstance(prijs, (int, float, Decimal)):
                counts["skipped"] += 1
                continue

            if not isinstance(prijs, str):
                counts["skipped"] += 1
                continue

            # prijs is a string — attempt conversion
            try:
                decimal_value = Decimal(prijs)
            except (InvalidOperation, ValueError):
                logger.error(
                    f"  ERROR {product_id}: cannot parse prijs='{prijs}' as number"
                )
                counts["errors"] += 1
                continue

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would convert {product_id}: prijs='{prijs}' -> {decimal_value}"
                )
            else:
                logger.info(
                    f"  CONVERTING {product_id}: prijs='{prijs}' -> {decimal_value}"
                )
                table.update_item(
                    Key={"product_id": product_id},
                    UpdateExpression="SET #prijs = :prijs",
                    ExpressionAttributeNames={"#prijs": "prijs"},
                    ExpressionAttributeValues={":prijs": decimal_value},
                )

            counts["converted"] += 1

        # Handle pagination
        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return counts


def migrate_orders_table(table, dry_run: bool) -> dict:
    """Scan Orders table, find records where items[].price or items[].unit_price is string, convert.

    Returns dict with counts: scanned, converted, skipped, errors.
    """
    counts = {"scanned": 0, "converted": 0, "skipped": 0, "errors": 0}

    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for order in items:
            counts["scanned"] += 1
            order_id = order.get("order_id", "unknown")
            order_items = order.get("items")

            if not order_items or not isinstance(order_items, list):
                counts["skipped"] += 1
                continue

            updated_items = []
            order_needs_update = False

            for idx, line_item in enumerate(order_items):
                item_modified = False

                for price_field in ("price", "unit_price"):
                    value = line_item.get(price_field)

                    if value is None:
                        continue

                    if isinstance(value, (int, float, Decimal)):
                        continue

                    if not isinstance(value, str):
                        continue

                    # Value is a string — attempt conversion
                    try:
                        decimal_value = Decimal(value)
                    except (InvalidOperation, ValueError):
                        logger.error(
                            f"  ERROR {order_id} item[{idx}].{price_field}: "
                            f"cannot parse '{value}' as number"
                        )
                        counts["errors"] += 1
                        continue

                    if dry_run:
                        logger.info(
                            f"  [DRY RUN] Would convert {order_id} item[{idx}].{price_field}: "
                            f"'{value}' -> {decimal_value}"
                        )
                    else:
                        logger.info(
                            f"  CONVERTING {order_id} item[{idx}].{price_field}: "
                            f"'{value}' -> {decimal_value}"
                        )

                    line_item[price_field] = decimal_value
                    item_modified = True

                if item_modified:
                    order_needs_update = True

                updated_items.append(line_item)

            if order_needs_update:
                counts["converted"] += 1
                if not dry_run:
                    table.update_item(
                        Key={"order_id": order_id},
                        UpdateExpression="SET #items = :items",
                        ExpressionAttributeNames={"#items": "items"},
                        ExpressionAttributeValues={":items": updated_items},
                    )
            else:
                counts["skipped"] += 1

        # Handle pagination
        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return counts


def print_summary(table_name: str, counts: dict, dry_run: bool):
    """Print a human-readable summary for one table."""
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n  {table_name} [{mode}]:")
    print(f"    Scanned:    {counts['scanned']}")
    print(f"    Converted:  {counts['converted']}")
    print(f"    Skipped:    {counts['skipped']}")
    print(f"    Errors:     {counts['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert string-typed price fields to DynamoDB Number type in "
            "Producten and Orders tables."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log changes without writing to DynamoDB.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=DEFAULT_PROFILE,
        help=f"AWS CLI profile (default: {DEFAULT_PROFILE}).",
    )
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "APPLY"
    logger.info(f"{'=' * 60}")
    logger.info(f"Price Fields to Number Migration [{mode}]")
    logger.info(f"Profile: {args.profile} | Region: {REGION}")
    logger.info(f"{'=' * 60}")

    dynamodb = get_dynamodb_resource(args.profile)

    # Migrate Producten table
    logger.info(f"\nScanning {PRODUCTEN_TABLE} table...")
    producten_table = dynamodb.Table(PRODUCTEN_TABLE)
    producten_counts = migrate_producten_table(producten_table, args.dry_run)

    # Migrate Orders table
    logger.info(f"\nScanning {ORDERS_TABLE} table...")
    orders_table = dynamodb.Table(ORDERS_TABLE)
    orders_counts = migrate_orders_table(orders_table, args.dry_run)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  Price Fields to Number Migration Summary")
    print(f"{'=' * 60}")
    print_summary(PRODUCTEN_TABLE, producten_counts, args.dry_run)
    print_summary(ORDERS_TABLE, orders_counts, args.dry_run)

    total_errors = producten_counts["errors"] + orders_counts["errors"]
    if args.dry_run:
        total_converted = producten_counts["converted"] + orders_counts["converted"]
        if total_converted > 0:
            print(f"\n  NOTE: This was a dry run. Remove --dry-run to execute the migration.")

    print(f"{'=' * 60}\n")

    if total_errors > 0:
        exit(1)


if __name__ == "__main__":
    main()
