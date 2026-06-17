#!/usr/bin/env python3
"""
Product Field Normalization Migration Script.

Normalizes existing Producten DynamoDB records to match the canonical
productFields registry (frontend/src/config/productFields/fields.ts).

Renames:
  - name → naam  (if 'naam' not already set)
  - price → prijs  (if 'prijs' not already set)
  - image → images  (single string or list → list under 'images')
  - id → artikelcode  (legacy short code like "G5" stored in 'id' field)
  - event_id → event_ids  (string → list of strings)

Removes:
  - nietInWinkel  (replaced by event_ids logic per docs/decisions/webshop-as-event.md)

Logic for event_ids (per webshop-as-event.md):
  - If nietInWinkel is false/absent AND no event_id → event_ids: ["evt-webshop"]
  - If event_id is set → event_ids: [event_id]
  - If nietInWinkel is true AND event_id is set → event_ids: [event_id]
  - If nietInWinkel is true AND no event_id → event_ids: []

Idempotency:
  - Skips records already normalized (has 'artikelcode' or legacy fields absent)
  - Safe to run multiple times

Usage:
    python scripts/migrate_product_fields_to_registry.py --dry-run
    python scripts/migrate_product_fields_to_registry.py
    python scripts/migrate_product_fields_to_registry.py --profile nonprofit-deploy
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
WEBSHOP_EVENT_ID = "evt-webshop"

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
    records_updated: int = 0
    records_skipped: int = 0
    field_renames: dict = field(default_factory=lambda: {
        "name_to_naam": 0,
        "price_to_prijs": 0,
        "image_to_images": 0,
        "id_to_artikelcode": 0,
        "event_id_to_event_ids": 0,
        "nietInWinkel_removed": 0,
    })
    errors: list[dict] = field(default_factory=list)


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def scan_all_items(table) -> list[dict]:
    """Scan all items from a DynamoDB table."""
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def needs_migration(item: dict) -> bool:
    """Determine if a record needs any field normalization.

    A record needs migration if it has any of the legacy field names
    that should be renamed/removed.
    """
    # Has legacy 'name' but no canonical 'naam'
    if "name" in item and "naam" not in item:
        return True
    # Has legacy 'price' but no canonical 'prijs'
    if "price" in item and "prijs" not in item:
        return True
    # Has legacy 'image' field (should be 'images' as a list)
    if "image" in item:
        return True
    # Has legacy 'id' field that should become 'artikelcode'
    # Note: only migrate if product_id exists (otherwise 'id' IS the primary key)
    if "id" in item and "product_id" in item and "artikelcode" not in item:
        return True
    # Has event_id (singular) that should become event_ids (plural list)
    if "event_id" in item and "event_ids" not in item:
        return True
    # Has nietInWinkel flag that should be removed
    if "nietInWinkel" in item:
        return True
    # Has event_ids not set and no event_id — needs webshop default
    if "event_ids" not in item and "event_id" not in item:
        # Only if it has a product_id (is a migrated record)
        if "product_id" in item:
            return True
    return False


def compute_event_ids(item: dict) -> list[str]:
    """Compute the event_ids list from legacy fields.

    Per docs/decisions/webshop-as-event.md:
    - nietInWinkel=false AND no event_id → ["evt-webshop"]
    - event_id set → [event_id]
    - nietInWinkel=true AND event_id set → [event_id]
    - nietInWinkel=true AND no event_id → []
    """
    niet_in_winkel = item.get("nietInWinkel", False)
    event_id = item.get("event_id")

    if event_id:
        # Product is linked to an event
        return [event_id]
    elif niet_in_winkel:
        # Not in shop and no event → draft/hidden
        return []
    else:
        # In the webshop
        return [WEBSHOP_EVENT_ID]


def migrate_single_record(
    table, item: dict, dry_run: bool, summary: MigrationSummary
) -> bool:
    """Migrate a single Producten record to canonical field names.

    Returns True if the record was updated, False if skipped.
    """
    product_id = item.get("product_id")
    if not product_id:
        # Records without product_id use 'id' as the primary key — skip these
        # (they should have been migrated to product_id first by migrate_products.py)
        logger.debug(f"Skipping record without product_id: id={item.get('id')}")
        return False

    # Build the update operations
    set_expressions = []
    remove_expressions = []
    expression_values = {}
    expression_names = {}

    # name → naam
    if "name" in item and "naam" not in item:
        set_expressions.append("#naam = :naam")
        expression_names["#naam"] = "naam"
        expression_values[":naam"] = item["name"]
        remove_expressions.append("#legacy_name")
        expression_names["#legacy_name"] = "name"
        summary.field_renames["name_to_naam"] += 1

    # price → prijs
    if "price" in item and "prijs" not in item:
        set_expressions.append("#prijs = :prijs")
        expression_names["#prijs"] = "prijs"
        expression_values[":prijs"] = item["price"]
        remove_expressions.append("#legacy_price")
        expression_names["#legacy_price"] = "price"
        summary.field_renames["price_to_prijs"] += 1

    # image → images (normalize to list)
    if "image" in item:
        image_val = item["image"]
        if isinstance(image_val, list):
            images_list = image_val
        elif isinstance(image_val, str) and image_val:
            images_list = [image_val]
        else:
            images_list = []

        # Merge with existing 'images' if present
        existing_images = item.get("images", [])
        if isinstance(existing_images, list):
            # Deduplicate while preserving order
            merged = list(existing_images)
            for img in images_list:
                if img not in merged:
                    merged.append(img)
            images_list = merged

        set_expressions.append("#images = :images")
        expression_names["#images"] = "images"
        expression_values[":images"] = images_list
        remove_expressions.append("#legacy_image")
        expression_names["#legacy_image"] = "image"
        summary.field_renames["image_to_images"] += 1

    # id → artikelcode (only if product_id exists, meaning 'id' is the legacy code)
    if "id" in item and "product_id" in item and "artikelcode" not in item:
        legacy_id = item["id"]
        # Only store as artikelcode if it looks like a short code (not a UUID)
        if legacy_id and len(str(legacy_id)) < 36:
            set_expressions.append("#artikelcode = :artikelcode")
            expression_names["#artikelcode"] = "artikelcode"
            expression_values[":artikelcode"] = str(legacy_id)
            summary.field_renames["id_to_artikelcode"] += 1
        # Remove the legacy 'id' field (product_id is now the key)
        remove_expressions.append("#legacy_id")
        expression_names["#legacy_id"] = "id"

    # event_id → event_ids
    if "event_ids" not in item:
        event_ids = compute_event_ids(item)
        set_expressions.append("#event_ids = :event_ids")
        expression_names["#event_ids"] = "event_ids"
        expression_values[":event_ids"] = event_ids
        summary.field_renames["event_id_to_event_ids"] += 1

        # Remove legacy event_id field
        if "event_id" in item:
            remove_expressions.append("#legacy_event_id")
            expression_names["#legacy_event_id"] = "event_id"

    # Remove nietInWinkel
    if "nietInWinkel" in item:
        remove_expressions.append("#nietInWinkel")
        expression_names["#nietInWinkel"] = "nietInWinkel"
        summary.field_renames["nietInWinkel_removed"] += 1

    # Always set updated_at
    set_expressions.append("#updated_at = :updated_at")
    expression_names["#updated_at"] = "updated_at"
    expression_values[":updated_at"] = datetime.now(timezone.utc).isoformat()

    if not set_expressions and not remove_expressions:
        return False

    # Build the update expression
    update_parts = []
    if set_expressions:
        update_parts.append("SET " + ", ".join(set_expressions))
    if remove_expressions:
        update_parts.append("REMOVE " + ", ".join(remove_expressions))
    update_expression = " ".join(update_parts)

    if dry_run:
        logger.info(
            f"[DRY RUN] Would update {product_id}: "
            f"SET={[n for n in expression_names.values() if n not in [expression_names.get(r.replace('#', '')) for r in remove_expressions]]} "
            f"REMOVE={[expression_names[r] for r in remove_expressions if r in expression_names]}"
        )
        return True

    table.update_item(
        Key={"product_id": product_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values if expression_values else None,
    )
    return True


def migrate_product_fields(
    dry_run: bool = True,
    profile: str | None = DEFAULT_PROFILE,
    table_name: str = DEFAULT_TABLE_NAME,
) -> MigrationSummary:
    """Main migration function.

    Scans all Producten records and normalizes field names to match the
    canonical productFields registry.

    Args:
        dry_run: If True, no writes are performed.
        profile: AWS CLI profile name.
        table_name: DynamoDB table name.

    Returns:
        MigrationSummary with counts and any errors.
    """
    summary = MigrationSummary()

    dynamodb = get_dynamodb_resource(profile)
    table = dynamodb.Table(table_name)

    logger.info(f"Scanning table '{table_name}' (dry_run={dry_run})...")
    items = scan_all_items(table)
    summary.total_scanned = len(items)
    logger.info(f"Found {len(items)} total records.")

    for item in items:
        product_id = item.get("product_id", item.get("id", "unknown"))
        try:
            if not needs_migration(item):
                summary.records_skipped += 1
                continue

            updated = migrate_single_record(table, item, dry_run, summary)
            if updated:
                summary.records_updated += 1
            else:
                summary.records_skipped += 1

        except Exception as e:
            logger.error(f"Error migrating record {product_id}: {e}")
            summary.errors.append({"product_id": str(product_id), "error": str(e)})

    return summary


def print_summary(summary: MigrationSummary, dry_run: bool):
    """Print a human-readable summary of the migration."""
    mode = "[DRY RUN]" if dry_run else "[LIVE]"
    print(f"\n{'=' * 60}")
    print(f"  Product Fields Normalization Migration {mode}")
    print(f"{'=' * 60}")
    print(f"  Total scanned:     {summary.total_scanned}")
    print(f"  Records updated:   {summary.records_updated}")
    print(f"  Records skipped:   {summary.records_skipped}")
    print(f"  Errors:            {len(summary.errors)}")
    print(f"\n  Field renames:")
    for rename, count in summary.field_renames.items():
        if count > 0:
            print(f"    {rename}: {count}")
    if summary.errors:
        print(f"\n  Errors:")
        for err in summary.errors:
            print(f"    {err['product_id']}: {err['error']}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize Producten field names to match the canonical registry."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without writing to DynamoDB.",
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

    summary = migrate_product_fields(
        dry_run=args.dry_run,
        profile=args.profile,
        table_name=args.table,
    )
    print_summary(summary, args.dry_run)

    if summary.errors and not args.dry_run:
        exit(1)


if __name__ == "__main__":
    main()
