#!/usr/bin/env python3
"""
Product Model Unification Migration Script.

Converts legacy H-DCN products (opties-based, id-keyed) to the unified model
with UUID product_id, variant_schema, and generated Variant_Records.

Responsibilities:
- Scan Producten table for legacy records (has `opties`, no `legacy_opties`, no existing variants)
- For each legacy product: generate UUID, create slug, parse opties → variant_schema, generate variants
- Set is_parent: true, active: true, event_id: null on migrated parent records
- Delete old record keyed by legacy id, create new UUID-keyed record
- Skip already-migrated products (idempotency)
- Log errors per-product and continue processing

Usage:
    python scripts/migrate_products.py --dry-run
    python scripts/migrate_products.py
    python scripts/migrate_products.py --profile nonprofit-deploy --table Producten
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

TABLE_ORDERS = "Orders"
TABLE_CARTS = "Carts"
TABLE_PAYMENTS = "Payments"

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
    products_migrated: int = 0
    variants_created: int = 0
    products_skipped: int = 0
    orders_deleted: int = 0
    carts_deleted: int = 0
    payments_deleted: int = 0
    channel_transformations: int = 0
    cart_channel_removals: int = 0
    errors: list[dict] = field(default_factory=list)


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with optional profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def create_slug(legacy_id: str, name: str) -> str:
    """Create a slug from the old id and product name.

    Example: legacy_id="G5", name="T-shirt" → "G5-t-shirt"
    """
    name_slug = slugify(name) if name else ""
    if name_slug:
        return f"{legacy_id}-{name_slug}"
    return legacy_id


def parse_opties(opties: str | None) -> dict | None:
    """Parse legacy opties string into variant_schema.

    - Comma-separated values → {"Maat": ["S", "M", "L", "XL"]}
    - "One Size" or empty/null → None (signals default variant needed)

    Returns:
        dict with variant_schema if opties has real values, None otherwise.
    """
    if opties is None:
        return None

    trimmed = opties.strip()
    if not trimmed or trimmed.lower() == "one size":
        return None

    values = [v.strip() for v in trimmed.split(",")]
    values = [v for v in values if v]  # filter empty strings

    if not values:
        return None

    return {"Maat": values}


def create_variant_record(
    parent_id: str,
    variant_attributes: dict,
) -> dict:
    """Create a single Variant_Record for a parent product."""
    return {
        "product_id": str(uuid.uuid4()),
        "is_parent": False,
        "parent_id": parent_id,
        "variant_attributes": variant_attributes,
        "stock": 0,
        "allow_oversell": True,
        "active": True,
        "source": "migration",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_variants(parent_id: str, variant_schema: dict | None) -> list[dict]:
    """Generate Variant_Records from variant_schema.

    If variant_schema is None (One Size / empty), creates a single Default_Variant.
    Otherwise creates one variant per value in the schema.
    """
    if variant_schema is None:
        # Default_Variant: no attributes
        return [create_variant_record(parent_id, {})]

    variants = []
    for axis_name, values in variant_schema.items():
        for value in values:
            variant = create_variant_record(parent_id, {axis_name: value})
            variants.append(variant)

    return variants


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


def is_legacy_product(item: dict, all_items: list[dict]) -> bool:
    """Determine if a record is a legacy product needing migration.

    A legacy product:
    - Has an `opties` field
    - Does NOT have a `legacy_opties` field (not already migrated)
    - Does NOT have a `legacy_id` field (not already migrated)
    - Does NOT have existing variant records (records where parent_id == this product's product_id)
    """
    # Must have opties
    if "opties" not in item:
        return False

    # Skip already migrated (has legacy_opties or legacy_id)
    if "legacy_opties" in item:
        return False
    if "legacy_id" in item:
        return False

    # Check for existing variant children
    product_id = item.get("product_id", item.get("id"))
    if product_id:
        for other in all_items:
            if other.get("parent_id") == product_id and other.get("is_parent") is False:
                return False

    return True


def migrate_single_product(
    table, item: dict, dry_run: bool
) -> tuple[int, list[dict]]:
    """Migrate a single legacy product to unified model.

    Returns:
        Tuple of (variants_created_count, variant_records)
    """
    # Get legacy identifiers
    legacy_id = item.get("product_id", item.get("id"))
    name = item.get("naam", item.get("name", ""))
    opties_value = item.get("opties", "")

    # Generate new UUID for the product
    new_product_id = str(uuid.uuid4())

    # Create slug
    slug = create_slug(legacy_id, name)

    # Parse opties into variant_schema
    variant_schema = parse_opties(opties_value)

    # Generate variant records
    variants = generate_variants(new_product_id, variant_schema)

    # Build the new parent product record
    new_record = dict(item)  # copy existing fields

    # Set new fields
    new_record["product_id"] = new_product_id
    new_record["legacy_id"] = legacy_id
    new_record["slug"] = slug
    new_record["is_parent"] = True
    new_record["active"] = True
    new_record["event_id"] = None

    # Copy opties to legacy_opties for audit
    new_record["legacy_opties"] = opties_value

    # Set variant_schema if we have real variants
    if variant_schema:
        new_record["variant_schema"] = variant_schema

    # Remove the opties field
    new_record.pop("opties", None)

    # Remove old 'id' field if present (the new key is product_id)
    new_record.pop("id", None)

    # Add migration metadata
    new_record["migrated_at"] = datetime.now(timezone.utc).isoformat()

    if not dry_run:
        # Write new parent record with UUID key
        table.put_item(Item=new_record)

        # Write variant records
        with table.batch_writer() as batch:
            for variant in variants:
                batch.put_item(Item=variant)

        # Delete old record keyed by legacy id
        table.delete_item(Key={"product_id": legacy_id})

    return len(variants), variants


def delete_all_records(table, table_name: str, key_name: str, dry_run: bool) -> int:
    """Delete all records from a table using scan + batch_writer.

    Args:
        table: boto3 DynamoDB Table resource.
        table_name: Name of the table (for logging).
        key_name: Partition key attribute name.
        dry_run: If True, only count records without deleting.

    Returns:
        Count of deleted (or would-be-deleted) records.
    """
    items = scan_all_items(table)
    count = len(items)

    if count == 0:
        logger.info(f"  {table_name}: 0 records (empty)")
        return 0

    if dry_run:
        logger.info(f"  [DRY RUN] Would delete {count} records from {table_name}")
        return count

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={key_name: item[key_name]})

    logger.info(f"  Deleted {count} records from {table_name}")
    return count


def delete_test_data(
    orders_table,
    carts_table,
    payments_table,
    dry_run: bool = False,
) -> dict:
    """Delete ALL records from Orders, Carts, and Payments tables.

    These tables contain only test data that should be removed during migration.

    Args:
        orders_table: boto3 DynamoDB Table resource for Orders.
        carts_table: boto3 DynamoDB Table resource for Carts.
        payments_table: boto3 DynamoDB Table resource for Payments.
        dry_run: If True, only count records without deleting.

    Returns:
        dict with keys: orders_deleted, carts_deleted, payments_deleted.
    """
    logger.info("Deleting test data from Orders, Carts, Payments...")

    orders_deleted = delete_all_records(orders_table, "Orders", "order_id", dry_run)
    carts_deleted = delete_all_records(carts_table, "Carts", "cart_id", dry_run)
    payments_deleted = delete_all_records(payments_table, "Payments", "payment_id", dry_run)

    return {
        "orders_deleted": orders_deleted,
        "carts_deleted": carts_deleted,
        "payments_deleted": payments_deleted,
    }


# ---------------------------------------------------------------------------
# Channel-to-event_id transformation (Task 1.2)
# ---------------------------------------------------------------------------

TABLE_EVENTS = "Events"


def _build_product_to_event_map(events_table) -> dict:
    """Scan the Events table and build a reverse lookup: product_id → event_id.

    Events store a `product_ids` list containing the IDs of products linked to that event.
    This builds a reverse index so we can quickly find which event owns a given product.

    Returns:
        dict mapping product_id (str) → event_id (str)
    """
    product_to_event: dict[str, str] = {}
    scan_kwargs: dict = {}

    while True:
        response = events_table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for event in items:
            event_id = event.get("event_id")
            product_ids = event.get("product_ids", [])

            if not event_id:
                continue

            if isinstance(product_ids, list):
                for pid in product_ids:
                    if pid:
                        product_to_event[str(pid)] = str(event_id)

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info(f"Built product→event map: {len(product_to_event)} product(s) linked to events")
    return product_to_event


def _resolve_event_id_for_product(product: dict, product_to_event: dict) -> str | None:
    """Determine the event_id for a product based on its channel value.

    Rules:
    - channel == "presmeet" → lookup event_id from product_to_event map
    - channel == "h-dcn" or absent → event_id = None
    - If presmeet product not found in any event → log warning, return None
    """
    channel = product.get("channel", "")

    if not channel or channel == "h-dcn":
        return None

    if channel == "presmeet":
        # Try to find the event that owns this product
        product_id = product.get("product_id", "")
        legacy_id = product.get("id", "")

        event_id = product_to_event.get(product_id)
        if event_id:
            return event_id

        # Fallback: try the legacy 'id' field
        if legacy_id:
            event_id = product_to_event.get(legacy_id)
            if event_id:
                return event_id

        # Product has channel=presmeet but isn't linked to any event
        identifier = product_id or legacy_id or "UNKNOWN"
        logger.warning(
            f"Product '{identifier}' has channel='presmeet' but is not found "
            f"in any event's product_ids list. Setting event_id=null."
        )
        return None

    # Unknown channel value — treat as webshop, set null
    logger.warning(
        f"Product '{product.get('product_id', product.get('id', 'UNKNOWN'))}' "
        f"has unknown channel='{channel}'. Setting event_id=null."
    )
    return None


def transform_channels_to_event_ids(
    table, events_table, dry_run: bool = False, carts_table=None
) -> dict:
    """Replace `channel`/`tenant` fields with `event_id` on all product records.

    Also removes `channel` from all cart records in the Carts table.

    Transformation rules:
    - channel: "presmeet" → event_id set to linked event's event_id
    - channel: "h-dcn" or absent → event_id: null
    - Remove `channel` and `tenant` fields from product records after setting event_id
    - Remove `channel` field from all cart records

    Args:
        table: DynamoDB Table resource for Producten.
        events_table: DynamoDB Table resource for Events.
        dry_run: If True, log changes without writing.
        carts_table: Optional DynamoDB Table resource for Carts (for testing).

    Returns:
        dict with counts: channel_transformations, cart_channel_removals, errors
    """
    # Build the reverse lookup: product_id → event_id
    product_to_event = _build_product_to_event_map(events_table)

    channel_transformations = 0
    errors: list[dict] = []

    # --- Transform channel → event_id on product records ---
    logger.info("  Transforming channel → event_id on product records...")
    scan_kwargs: dict = {}
    total_product_scanned = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        total_product_scanned += len(items)

        for product in items:
            # Only process records that have a `channel` or `tenant` field
            if "channel" not in product and "tenant" not in product:
                continue

            # The table's primary key is 'id' (legacy schema, not 'product_id')
            record_key = product.get("id")
            display_id = product.get("product_id", record_key)
            if not record_key:
                logger.warning(
                    f"Skipping record without 'id' key: {list(product.keys())[:5]}"
                )
                continue

            try:
                event_id = _resolve_event_id_for_product(product, product_to_event)

                if dry_run:
                    logger.info(
                        f"    [DRY-RUN] Would set event_id={event_id}, remove channel/tenant "
                        f"on id={record_key}"
                    )
                else:
                    # Build update expression
                    update_expr_parts = ["SET event_id = :eid"]
                    expr_values = {":eid": event_id}
                    remove_parts = []

                    if "channel" in product:
                        remove_parts.append("channel")
                    if "tenant" in product:
                        remove_parts.append("tenant")

                    update_expr = " ".join(update_expr_parts)
                    if remove_parts:
                        update_expr += " REMOVE " + ", ".join(remove_parts)

                    table.update_item(
                        Key={"id": record_key},
                        UpdateExpression=update_expr,
                        ExpressionAttributeValues=expr_values,
                    )

                channel_transformations += 1

            except Exception as e:
                identifier = display_id or record_key or "UNKNOWN"
                logger.error(f"Error transforming channel on product '{identifier}': {e}")
                errors.append({"product_id": identifier, "error": str(e)})

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info(
        f"    Products transformed: {channel_transformations}, "
        f"scanned: {total_product_scanned}, errors: {len(errors)}"
    )

    # --- Remove `channel` field from all cart records ---
    cart_channel_removals = _remove_channel_from_carts(carts_table, dry_run)

    return {
        "channel_transformations": channel_transformations,
        "cart_channel_removals": cart_channel_removals,
        "errors": errors,
    }


def _remove_channel_from_carts(carts_table=None, dry_run: bool = False) -> int:
    """Remove the `channel` field from all cart records in the Carts table.

    Args:
        carts_table: DynamoDB Table resource for Carts. If None, creates one.
        dry_run: If True, log changes without writing.

    Returns:
        Number of cart records where channel was removed.
    """
    if carts_table is None:
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        carts_table = dynamodb.Table(TABLE_CARTS)

    logger.info("  Removing channel field from cart records...")
    removals = 0
    scan_kwargs: dict = {}

    while True:
        response = carts_table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for cart in items:
            if "channel" not in cart:
                continue

            cart_id = cart.get("cart_id")
            if not cart_id:
                logger.warning(f"Skipping cart without cart_id: {list(cart.keys())[:5]}")
                continue

            if dry_run:
                logger.info(f"    [DRY-RUN] Would remove channel from cart_id={cart_id}")
            else:
                carts_table.update_item(
                    Key={"cart_id": cart_id},
                    UpdateExpression="REMOVE channel",
                )

            removals += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    logger.info(f"    Cart channel removals: {removals}")
    return removals


# ---------------------------------------------------------------------------
# Main migration orchestration
# ---------------------------------------------------------------------------


def migrate_products(
    dry_run: bool = False,
    profile: str | None = DEFAULT_PROFILE,
    table_name: str = DEFAULT_TABLE_NAME,
) -> MigrationSummary:
    """Execute the full product migration.

    Scans the Producten table, identifies legacy products, and converts them
    to the unified model with UUID product_id and variant records.

    Args:
        dry_run: If True, only preview changes without writing to DynamoDB.
        profile: AWS CLI profile name for authentication.
        table_name: Name of the Producten DynamoDB table.

    Returns:
        MigrationSummary with counts of all actions taken.
    """
    summary = MigrationSummary()
    dynamodb = get_dynamodb_resource(profile)
    producten_table = dynamodb.Table(table_name)

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info(f"{'=' * 60}")
    logger.info(f"Product Model Unification Migration [{mode}]")
    logger.info(f"  Table: {table_name} | Region: {REGION}")
    if profile:
        logger.info(f"  Profile: {profile}")
    logger.info(f"{'=' * 60}")

    # --- Step 1: Scan all Producten records ---
    logger.info("Step 1: Scanning Producten table...")
    all_items = scan_all_items(producten_table)
    summary.total_scanned = len(all_items)
    logger.info(f"  Found {summary.total_scanned} total records")

    # --- Step 2: Identify legacy products ---
    logger.info("Step 2: Identifying legacy products...")
    legacy_products = [item for item in all_items if is_legacy_product(item, all_items)]
    skipped = summary.total_scanned - len(legacy_products)
    summary.products_skipped = skipped
    logger.info(f"  Legacy products to migrate: {len(legacy_products)}")
    logger.info(f"  Products skipped: {skipped}")

    # --- Step 3: Migrate each legacy product ---
    logger.info("Step 3: Migrating legacy products...")
    for item in legacy_products:
        product_id = item.get("product_id", item.get("id", "unknown"))
        name = item.get("naam", item.get("name", "unnamed"))
        opties = item.get("opties", "")

        try:
            variants_count, _ = migrate_single_product(producten_table, item, dry_run)
            summary.products_migrated += 1
            summary.variants_created += variants_count
            logger.info(
                f"  {'[DRY]' if dry_run else '[OK]'} {product_id} ({name}) "
                f"→ {variants_count} variant(s) | opties: '{opties}'"
            )
        except Exception as e:
            error_detail = {"product_id": product_id, "error": str(e)}
            summary.errors.append(error_detail)
            logger.error(f"  [ERR] {product_id}: {e}")

    # --- Step 4: Channel → event_id transformation ---
    logger.info("Step 4: Channel → event_id transformation...")
    events_table = dynamodb.Table(TABLE_EVENTS)
    carts_table = dynamodb.Table(TABLE_CARTS)
    channel_result = transform_channels_to_event_ids(
        producten_table, events_table, dry_run=dry_run, carts_table=carts_table
    )
    summary.channel_transformations = channel_result["channel_transformations"]
    summary.cart_channel_removals = channel_result["cart_channel_removals"]
    summary.errors.extend(channel_result["errors"])

    # --- Step 5: Delete test data from Orders, Carts, Payments ---
    logger.info("Step 5: Deleting test data from Orders, Carts, Payments...")
    orders_table = dynamodb.Table(TABLE_ORDERS)
    carts_table = dynamodb.Table(TABLE_CARTS)
    payments_table = dynamodb.Table(TABLE_PAYMENTS)

    deletion_counts = delete_test_data(
        orders_table, carts_table, payments_table, dry_run=dry_run
    )
    summary.orders_deleted = deletion_counts["orders_deleted"]
    summary.carts_deleted = deletion_counts["carts_deleted"]
    summary.payments_deleted = deletion_counts["payments_deleted"]

    # --- Summary ---
    logger.info(f"{'=' * 60}")
    logger.info(f"Migration {'Preview' if dry_run else 'Complete'}")
    logger.info(f"  Total scanned:          {summary.total_scanned}")
    logger.info(f"  Products migrated:      {summary.products_migrated}")
    logger.info(f"  Variants created:       {summary.variants_created}")
    logger.info(f"  Products skipped:       {summary.products_skipped}")
    logger.info(f"  Channel→event_id:       {summary.channel_transformations}")
    logger.info(f"  Cart channel removals:  {summary.cart_channel_removals}")
    logger.info(f"  Orders deleted:         {summary.orders_deleted}")
    logger.info(f"  Carts deleted:          {summary.carts_deleted}")
    logger.info(f"  Payments deleted:       {summary.payments_deleted}")
    logger.info(f"  Errors:                 {len(summary.errors)}")
    if summary.errors:
        for err in summary.errors:
            logger.error(f"    - {err['product_id']}: {err['error']}")
    logger.info(f"{'=' * 60}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate legacy H-DCN products to unified product/variant model"
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

    result = migrate_products(
        dry_run=args.dry_run,
        profile=args.profile,
        table_name=args.table,
    )

    # Exit with error code if there were failures
    if result.errors:
        exit(1)
