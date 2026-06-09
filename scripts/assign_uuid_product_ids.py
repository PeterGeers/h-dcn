#!/usr/bin/env python3
"""
Assign UUID v4 product_ids to non-UUID records in the Producten table.

After the initial migration, some records still have non-UUID product_ids
(e.g., "G5", "DB-H", "prod-pm2027-tshirt", "var_G5_default"). This script
converts those to proper UUID v4 values while preserving the old id as
`legacy_id` and generating a `slug`.

Processing order:
1. Parent products first (is_parent=True or is_parent absent)
2. Variants second (is_parent=False), updating parent_id references

For each non-UUID record:
- Generate new UUID v4
- Store old product_id in `legacy_id`
- Generate `slug` from: {old_id}-{name_slugified} (max 60 chars)
- Create NEW record with UUID product_id + all existing attributes
- Delete OLD record
- Update variant parent_id references to point to new parent UUID

Usage:
    python scripts/assign_uuid_product_ids.py --dry-run
    python scripts/assign_uuid_product_ids.py
"""

from __future__ import annotations

import argparse
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import boto3

REGION = "eu-west-1"
DEFAULT_TABLE_NAME = "Producten"
DEFAULT_PROFILE = "nonprofit-deploy"

UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationSummary:
    """Summary of UUID assignment results."""

    total_scanned: int = 0
    non_uuid_count: int = 0
    parents_converted: int = 0
    variants_converted: int = 0
    parent_id_updates: int = 0
    skipped_already_uuid: int = 0
    errors: list[dict] = field(default_factory=list)


def is_valid_uuid4(value: str) -> bool:
    """Check if a string is a valid UUID v4."""
    return bool(UUID4_PATTERN.match(value.lower()))


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Lowercase, replace non-alphanumeric with hyphens, collapse multiples,
    strip leading/trailing hyphens, truncate to 60 chars.
    """
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text[:60]


def create_slug(old_id: str, name: str | None) -> str:
    """Create a slug from old_id and product name.

    Format: {old_id}-{name_slugified}, max 60 chars total.
    """
    name_part = name or ""
    combined = f"{old_id}-{name_part}" if name_part else old_id
    return slugify(combined)


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


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


def is_parent_record(item: dict) -> bool:
    """Determine if a record is a parent product.

    Parent if is_parent=True or is_parent is absent.
    Variant if is_parent=False.
    """
    is_parent = item.get("is_parent")
    # Absent → parent, True → parent, False → variant
    return is_parent is not False


def convert_record(
    table, item: dict, new_uuid: str, dry_run: bool
) -> None:
    """Replace a non-UUID record with a UUID-keyed copy.

    1. Build new record with UUID product_id, legacy_id, slug
    2. Put new record
    3. Delete old record
    """
    old_id = item["product_id"]
    name = item.get("naam", item.get("name", ""))

    # Build new record (copy all existing attributes)
    new_record = dict(item)
    new_record["product_id"] = new_uuid
    new_record["legacy_id"] = old_id
    new_record["slug"] = create_slug(old_id, name)
    new_record["migrated_at"] = datetime.now(timezone.utc).isoformat()

    if dry_run:
        logger.info(
            f"    [DRY RUN] Would create record with product_id={new_uuid}, "
            f"legacy_id={old_id}, slug={new_record['slug']}"
        )
    else:
        # Write new record
        table.put_item(Item=new_record)
        # Delete old record
        table.delete_item(Key={"product_id": old_id})


def update_variant_parent_id(
    table, variant_item: dict, new_parent_uuid: str, dry_run: bool
) -> None:
    """Update a variant's parent_id to point to the parent's new UUID.

    Uses the variant's current product_id as the key.
    """
    variant_key = variant_item["product_id"]

    if dry_run:
        logger.info(
            f"    [DRY RUN] Would update parent_id on variant {variant_key} "
            f"from {variant_item.get('parent_id')} → {new_parent_uuid}"
        )
    else:
        table.update_item(
            Key={"product_id": variant_key},
            UpdateExpression="SET parent_id = :pid",
            ExpressionAttributeValues={":pid": new_parent_uuid},
        )


def run_migration(
    dry_run: bool = False,
    profile: str | None = DEFAULT_PROFILE,
    table_name: str = DEFAULT_TABLE_NAME,
) -> MigrationSummary:
    """Execute the UUID assignment migration.

    Processing order:
    1. Scan all records, classify as UUID vs non-UUID
    2. Separate non-UUID into parents and variants
    3. Convert parents first, building old_id → new_uuid map
    4. Convert variants, updating parent_id references
    """
    summary = MigrationSummary()
    dynamodb = get_dynamodb_resource(profile)
    table = dynamodb.Table(table_name)

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info(f"{'=' * 60}")
    logger.info(f"Assign UUID v4 Product IDs [{mode}]")
    logger.info(f"  Table: {table_name} | Region: {REGION}")
    if profile:
        logger.info(f"  Profile: {profile}")
    logger.info(f"{'=' * 60}")

    # --- Step 1: Scan all records ---
    logger.info("Step 1: Scanning Producten table...")
    all_items = scan_all_items(table)
    summary.total_scanned = len(all_items)
    logger.info(f"  Found {summary.total_scanned} total records")

    # --- Step 2: Identify non-UUID records ---
    logger.info("Step 2: Identifying non-UUID product_ids...")
    non_uuid_items = []
    uuid_items = []

    for item in all_items:
        pid = item.get("product_id", "")
        if not pid:
            logger.warning(f"  Record without product_id: {item}")
            continue

        if is_valid_uuid4(pid):
            uuid_items.append(item)
            summary.skipped_already_uuid += 1
        else:
            non_uuid_items.append(item)

    summary.non_uuid_count = len(non_uuid_items)
    logger.info(f"  Already UUID: {summary.skipped_already_uuid}")
    logger.info(f"  Non-UUID (to convert): {summary.non_uuid_count}")

    if not non_uuid_items:
        logger.info("  Nothing to convert. All records already have UUID product_ids.")
        return summary

    # --- Step 3: Separate parents and variants ---
    logger.info("Step 3: Separating parents and variants...")
    parents = [item for item in non_uuid_items if is_parent_record(item)]
    variants = [item for item in non_uuid_items if not is_parent_record(item)]
    logger.info(f"  Parents to convert: {len(parents)}")
    logger.info(f"  Variants to convert: {len(variants)}")

    # --- Step 4: Convert parents, build mapping ---
    logger.info("Step 4: Converting parent records...")
    old_to_new_uuid: dict[str, str] = {}  # old_id → new_uuid

    for item in parents:
        old_id = item["product_id"]
        name = item.get("naam", item.get("name", ""))
        new_uuid = str(uuid.uuid4())
        old_to_new_uuid[old_id] = new_uuid

        try:
            convert_record(table, item, new_uuid, dry_run)
            summary.parents_converted += 1
            slug = create_slug(old_id, name)
            logger.info(
                f"  {'[DRY]' if dry_run else '[OK]'} Parent: {old_id} → {new_uuid} "
                f"(slug: {slug})"
            )
        except Exception as e:
            summary.errors.append({"product_id": old_id, "error": str(e)})
            logger.error(f"  [ERR] Parent {old_id}: {e}")

    # --- Step 5: Update variant parent_id references for UUID variants ---
    # Some variants that already have UUID product_ids may reference an old parent_id
    logger.info("Step 5: Updating parent_id references on existing UUID variants...")
    for item in uuid_items:
        parent_id = item.get("parent_id")
        if parent_id and parent_id in old_to_new_uuid:
            new_parent_uuid = old_to_new_uuid[parent_id]
            try:
                update_variant_parent_id(table, item, new_parent_uuid, dry_run)
                summary.parent_id_updates += 1
                logger.info(
                    f"  {'[DRY]' if dry_run else '[OK]'} Updated parent_id on "
                    f"{item['product_id']}: {parent_id} → {new_parent_uuid}"
                )
            except Exception as e:
                summary.errors.append(
                    {"product_id": item["product_id"], "error": str(e)}
                )
                logger.error(f"  [ERR] Updating parent_id on {item['product_id']}: {e}")

    # --- Step 6: Convert variant records ---
    logger.info("Step 6: Converting variant records...")
    for item in variants:
        old_id = item["product_id"]
        name = item.get("naam", item.get("name", ""))
        new_uuid = str(uuid.uuid4())

        # Update parent_id to point to new parent UUID if applicable
        old_parent_id = item.get("parent_id")
        if old_parent_id and old_parent_id in old_to_new_uuid:
            item["parent_id"] = old_to_new_uuid[old_parent_id]

        try:
            convert_record(table, item, new_uuid, dry_run)
            summary.variants_converted += 1
            slug = create_slug(old_id, name)
            parent_info = (
                f", parent_id: {item.get('parent_id', 'N/A')}"
                if old_parent_id
                else ""
            )
            logger.info(
                f"  {'[DRY]' if dry_run else '[OK]'} Variant: {old_id} → {new_uuid} "
                f"(slug: {slug}{parent_info})"
            )
        except Exception as e:
            summary.errors.append({"product_id": old_id, "error": str(e)})
            logger.error(f"  [ERR] Variant {old_id}: {e}")

    # --- Summary ---
    logger.info(f"{'=' * 60}")
    logger.info(f"UUID Assignment {'Preview' if dry_run else 'Complete'}")
    logger.info(f"  Total scanned:           {summary.total_scanned}")
    logger.info(f"  Already UUID (skipped):  {summary.skipped_already_uuid}")
    logger.info(f"  Non-UUID found:          {summary.non_uuid_count}")
    logger.info(f"  Parents converted:       {summary.parents_converted}")
    logger.info(f"  Variants converted:      {summary.variants_converted}")
    logger.info(f"  Parent_id refs updated:  {summary.parent_id_updates}")
    logger.info(f"  Errors:                  {len(summary.errors)}")
    if summary.errors:
        for err in summary.errors:
            logger.error(f"    - {err['product_id']}: {err['error']}")
    logger.info(f"{'=' * 60}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Assign UUID v4 product_ids to non-UUID records in Producten"
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
        help="Preview changes without writing to DynamoDB",
    )
    args = parser.parse_args()

    result = run_migration(
        dry_run=args.dry_run,
        profile=args.profile,
        table_name=args.table,
    )

    # Exit with error code if there were failures
    if result.errors:
        exit(1)
