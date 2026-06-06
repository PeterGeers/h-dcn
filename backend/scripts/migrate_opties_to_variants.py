#!/usr/bin/env python3
"""
Migrate legacy `opties` comma-separated string fields to the variant model.

Scans the Producten table for products with an `opties` field and converts them:
1. Parses comma-separated `opties` into variant_schema with axis "opties"
2. Generates variant records (stock=0, allow_oversell=true) for each value
3. Moves original `opties` to `legacy_opties`, removes `opties` field
4. Skips already-migrated products (has `legacy_opties` or variants with parent_id)

Usage:
    python backend/scripts/migrate_opties_to_variants.py --dry-run
    python backend/scripts/migrate_opties_to_variants.py
    python backend/scripts/migrate_opties_to_variants.py --profile nonprofit-deploy

Requirements: 11.1–11.5, 14.1, 14.2
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


REGION = "eu-west-1"
TABLE_NAME = os.environ.get("PRODUCTEN_TABLE_NAME", "Producten")
PARTITION_KEY = "product_id"


def get_table(profile: str | None = None):
    """Create a DynamoDB table resource."""
    import boto3

    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def scan_all_items(table) -> list[dict]:
    """Scan the entire Producten table."""
    items = []
    scan_kwargs: dict[str, Any] = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def parse_opties(opties_value: str) -> list[str]:
    """
    Parse a comma-separated opties string into a list of trimmed values.

    "S, M, L" -> ["S", "M", "L"]
    "Rood,Blauw, Groen" -> ["Rood", "Blauw", "Groen"]

    Empty values after trimming are filtered out.
    """
    if not opties_value or not opties_value.strip():
        return []

    values = [v.strip() for v in opties_value.split(",")]
    # Filter out empty strings that result from trailing commas or double commas
    return [v for v in values if v]


def _sanitize_for_id(value: str) -> str:
    """Sanitize a value for use in a variant product_id."""
    sanitized = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return sanitized.strip("_")


def build_variant_schema(parsed_values: list[str]) -> dict[str, list[str]]:
    """
    Build a variant_schema dict with a single axis "opties".

    Returns: {"opties": ["S", "M", "L"]}
    """
    return {"opties": parsed_values}


def generate_variant_records(
    parent_product_id: str,
    tenant: str,
    parsed_values: list[str],
    timestamp: str,
) -> list[dict[str, Any]]:
    """
    Generate variant records for each parsed opties value.

    Each variant has:
    - stock=0 (admin reviews stock later)
    - allow_oversell=true (safe default during migration)
    """
    variants = []
    for value in parsed_values:
        id_part = _sanitize_for_id(value)
        variant_id = f"var_{parent_product_id}_{id_part}"

        variant_record = {
            "product_id": variant_id,
            "is_parent": False,
            "parent_id": parent_product_id,
            "tenant": tenant,
            "variant_attributes": {"opties": value},
            "stock": 0,
            "sold_count": 0,
            "allow_oversell": True,
            "active": True,
            "created_at": timestamp,
            "updated_at": timestamp,
            "source": "opties_migration",
        }
        variants.append(variant_record)

    return variants


def is_already_migrated(product: dict, all_items: list[dict]) -> tuple[bool, str]:
    """
    Check if a product has already been migrated.

    Returns (is_migrated, reason) tuple.
    Checks:
    1. Product has a `legacy_opties` field
    2. Existing variant records with matching parent_id exist
    """
    product_id = product[PARTITION_KEY]

    # Check 1: legacy_opties field present
    if "legacy_opties" in product:
        return True, "has legacy_opties field"

    # Check 2: existing variant records with this parent_id
    has_variants = any(
        item.get("parent_id") == product_id and item.get("is_parent") is False
        for item in all_items
    )
    if has_variants:
        return True, "has existing variant records"

    return False, ""


def has_opties_field(product: dict) -> bool:
    """Check if a product has a non-empty `opties` field."""
    opties = product.get("opties")
    if opties is None:
        return False
    if isinstance(opties, str) and opties.strip():
        return True
    return False


def create_log_entry(
    product_id: str,
    original_opties: str,
    variant_count: int,
    status: str,
    reason: str = "",
) -> dict[str, Any]:
    """Create a structured log entry for audit purposes."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product_id": product_id,
        "original_opties": original_opties,
        "variant_count": variant_count,
        "status": status,
    }
    if reason:
        entry["reason"] = reason
    return entry


def migrate(profile: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """
    Run the opties-to-variants migration.

    Returns a summary dict with migration statistics.
    """
    table = get_table(profile)

    print(f"{'🔍 DRY RUN' if dry_run else '🚀 LIVE RUN'} — Migrating opties to variant model")
    print(f"   Table: {TABLE_NAME} | Region: {REGION}")
    if profile:
        print(f"   Profile: {profile}")
    print()

    # Scan all records
    print("📋 Scanning Producten table...")
    all_items = scan_all_items(table)
    print(f"   Found {len(all_items)} total records")
    print()

    # Find products with opties field
    products_with_opties = [item for item in all_items if has_opties_field(item)]
    print(f"   Products with opties field: {len(products_with_opties)}")
    print()

    if not products_with_opties:
        print("✅ No products with opties field found — nothing to migrate.")
        return {
            "total_scanned": len(all_items),
            "total_with_opties": 0,
            "successful": 0,
            "skipped": 0,
            "errors": 0,
        }

    # Process each product
    successful = 0
    skipped = 0
    skipped_reasons: list[dict] = []
    errors: list[dict] = []
    log_entries: list[dict] = []

    for product in products_with_opties:
        product_id = product[PARTITION_KEY]
        original_opties = product["opties"]
        tenant = product.get("tenant", "h-dcn")

        # Check if already migrated (idempotency)
        migrated, reason = is_already_migrated(product, all_items)
        if migrated:
            print(f"  ⏭️  Skipping {product_id}: {reason}")
            skipped += 1
            skipped_reasons.append({"product_id": product_id, "reason": reason})
            log_entries.append(
                create_log_entry(product_id, original_opties, 0, "skipped", reason)
            )
            continue

        # Parse opties
        parsed_values = parse_opties(original_opties)
        if not parsed_values:
            print(f"  ⚠️  Skipping {product_id}: opties field is empty after parsing")
            skipped += 1
            skipped_reasons.append({"product_id": product_id, "reason": "empty after parsing"})
            log_entries.append(
                create_log_entry(product_id, original_opties, 0, "skipped", "empty after parsing")
            )
            continue

        # Build variant_schema and generate variants
        variant_schema = build_variant_schema(parsed_values)
        now = datetime.now(timezone.utc).isoformat()
        variants = generate_variant_records(product_id, tenant, parsed_values, now)

        print(f"  {'[DRY]' if dry_run else '[LIVE]'} Migrating: {product_id}")
        print(f"    opties: \"{original_opties}\" → {len(variants)} variants")

        if not dry_run:
            try:
                # Step 1: Write variant records (batch write)
                with table.batch_writer() as batch:
                    for variant in variants:
                        batch.put_item(Item=variant)

                # Step 2: Update parent product:
                #   - SET variant_schema, legacy_opties, updated_at
                #   - REMOVE opties
                table.update_item(
                    Key={PARTITION_KEY: product_id},
                    UpdateExpression=(
                        "SET #variant_schema = :vs, "
                        "#legacy_opties = :lo, "
                        "#updated_at = :ua "
                        "REMOVE #opties"
                    ),
                    ExpressionAttributeNames={
                        "#variant_schema": "variant_schema",
                        "#legacy_opties": "legacy_opties",
                        "#updated_at": "updated_at",
                        "#opties": "opties",
                    },
                    ExpressionAttributeValues={
                        ":vs": variant_schema,
                        ":lo": original_opties,
                        ":ua": now,
                    },
                )

                successful += 1
                print(f"    ✅ Created {len(variants)} variants, moved opties to legacy_opties")
                log_entries.append(
                    create_log_entry(product_id, original_opties, len(variants), "success")
                )

            except Exception as e:
                error_msg = str(e)
                errors.append({"product_id": product_id, "error": error_msg})
                print(f"    ❌ Error: {error_msg}")
                log_entries.append(
                    create_log_entry(product_id, original_opties, 0, "error", error_msg)
                )
        else:
            successful += 1
            print(f"    → Would create variants: {parsed_values}")
            print(f"    → Would set variant_schema: {json.dumps(variant_schema)}")
            print(f"    → Would move opties to legacy_opties")
            log_entries.append(
                create_log_entry(product_id, original_opties, len(variants), "dry_run")
            )

        print()

    # Summary
    summary = {
        "total_scanned": len(all_items),
        "total_with_opties": len(products_with_opties),
        "successful": successful,
        "skipped": skipped,
        "skipped_reasons": skipped_reasons,
        "errors": len(errors),
        "error_details": errors,
    }

    print("=" * 60)
    print(f"{'🔍 DRY RUN SUMMARY' if dry_run else '🎉 MIGRATION COMPLETE'}")
    print(f"   Total records scanned: {summary['total_scanned']}")
    print(f"   Products with opties: {summary['total_with_opties']}")
    print(f"   Successfully migrated: {summary['successful']}")
    print(f"   Skipped: {summary['skipped']}")
    if skipped_reasons:
        for entry in skipped_reasons:
            print(f"      - {entry['product_id']}: {entry['reason']}")
    if errors:
        print(f"   ❌ Errors: {len(errors)}")
        for entry in errors:
            print(f"      - {entry['product_id']}: {entry['error']}")
    print("=" * 60)

    # Output structured audit log
    if log_entries:
        print()
        print("📝 Audit log (JSON):")
        for entry in log_entries:
            print(f"   {json.dumps(entry)}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate legacy opties comma-strings to variant_schema + variant records"
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to DynamoDB",
    )
    args = parser.parse_args()

    result = migrate(profile=args.profile, dry_run=args.dry_run)

    # Exit with error code if there were failures
    if result.get("errors", 0) > 0:
        sys.exit(1)
