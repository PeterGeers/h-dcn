#!/usr/bin/env python3
"""
Migrate PresMeet config records to the unified Parent_Product model.

Scans the Producten table for records matching 'config_presmeet_*' pattern and converts them
to standard Parent_Product records with:
- tenant: "presmeet"
- is_parent: True
- variant_schema: axes derived from enum-type required_attributes
- order_item_fields: entries derived from text/date/integer required_attributes
- purchase_rules: mapped from max_per_club, min_per_club, order_mode "persistent"

The original required_attributes field is preserved as `legacy_required_attributes` (read-only).
Products that cannot be converted are skipped with a logged failure reason.

Usage:
    python backend/scripts/migrate_presmeet_config.py --dry-run
    python backend/scripts/migrate_presmeet_config.py
    python backend/scripts/migrate_presmeet_config.py --profile nonprofit-deploy
    PRODUCTEN_TABLE_NAME=MyTable python backend/scripts/migrate_presmeet_config.py

Requirements: 12.1–12.4, 14.3–14.6
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone

import boto3


REGION = "eu-west-1"
TABLE_NAME = os.environ.get("PRODUCTEN_TABLE_NAME", "Producten")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_table(profile: str | None = None):
    """Create a DynamoDB table resource."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def scan_presmeet_config_records(table) -> list[dict]:
    """Scan Producten table for config_presmeet_* records."""
    items = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            product_id = item.get("product_id", "")
            if product_id.startswith("config_presmeet_"):
                items.append(item)

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def is_already_migrated(item: dict) -> bool:
    """Check if a record has already been migrated.

    A record is considered migrated if it already has is_parent=True
    and any of the new unified model fields set.
    """
    if item.get("is_parent") is True and "legacy_required_attributes" in item:
        return True
    if item.get("is_parent") is True and "variant_schema" in item:
        return True
    if item.get("is_parent") is True and "order_item_fields" in item:
        return True
    if item.get("is_parent") is True and "purchase_rules" in item:
        return True
    return False


def map_required_attributes(
    required_attributes: dict,
) -> tuple[dict, list[dict]]:
    """Map required_attributes to variant_schema axes and order_item_fields.

    The required_attributes format (from seed data) is a flat dict:
    {
        "name": {"type": "string", "required": True, "min_length": 1, ...},
        "gender": {"type": "string", "required": True, "enum": ["male", "female"]},
        "size": {"type": "string", "required": True, "enum": ["S", "M", "L", ...]},
        "persons": {"type": "integer", "required": True, "minimum": 1, "maximum": 50}
    }

    Attributes with an "enum" list become variant_schema axes.
    All other attributes become order_item_fields entries.

    Returns:
        tuple of (variant_schema, order_item_fields)
    """
    variant_schema = {}
    order_item_fields = []

    for attr_name, attr_def in required_attributes.items():
        if not isinstance(attr_def, dict):
            continue

        enum_values = attr_def.get("enum")

        if enum_values and isinstance(enum_values, list) and len(enum_values) > 0:
            # Enum-type → variant_schema axis
            variant_schema[attr_name] = enum_values
        else:
            # Non-enum → order_item_fields entry
            field_def = _build_field_definition(attr_name, attr_def)
            order_item_fields.append(field_def)

    return variant_schema, order_item_fields


def _build_field_definition(attr_name: str, attr_def: dict) -> dict:
    """Build an order_item_fields entry from a required_attributes property.

    Maps legacy types to unified field types:
    - "string" → "text"
    - "integer" → "number"
    - "date" → "date"
    - "number" → "number"
    """
    attr_type = attr_def.get("type", "string")

    type_mapping = {
        "string": "text",
        "integer": "number",
        "date": "date",
        "number": "number",
    }
    field_type = type_mapping.get(attr_type, "text")

    field = {
        "id": attr_name,
        "label": _humanize_label(attr_name),
        "type": field_type,
        "required": bool(attr_def.get("required", False)),
    }

    # Map validation constraints
    validation = {}
    if "min_length" in attr_def:
        validation["min_length"] = int(attr_def["min_length"])
    if "max_length" in attr_def:
        validation["max_length"] = int(attr_def["max_length"])
    if "minimum" in attr_def:
        validation["minimum"] = int(attr_def["minimum"])
    if "maximum" in attr_def:
        validation["maximum"] = int(attr_def["maximum"])

    if validation:
        field["validation"] = validation

    return field


def _humanize_label(attr_name: str) -> str:
    """Convert snake_case attribute name to a human-readable label."""
    return attr_name.replace("_", " ").capitalize()


def build_purchase_rules(item: dict) -> dict:
    """Build purchase_rules from max_per_club and min_per_club fields.

    PresMeet products use persistent order mode by default.
    """
    rules = {}

    max_per_club = item.get("max_per_club")
    if max_per_club is not None:
        rules["max_per_club"] = int(max_per_club)

    min_per_club = item.get("min_per_club")
    if min_per_club is not None:
        rules["min_per_club"] = int(min_per_club)

    # PresMeet products use persistent order mode
    rules["order_mode"] = "persistent"

    return rules


def convert_record(item: dict) -> tuple[dict | None, str | None]:
    """Convert a config_presmeet_* record to unified Parent_Product fields.

    Returns:
        tuple of (update_fields, error_message)
        - update_fields: dict of fields to set on the record, or None if fails
        - error_message: description of why conversion failed, or None on success
    """
    product_id = item.get("product_id", "")
    required_attributes = item.get("required_attributes")

    if required_attributes is None:
        return None, f"No required_attributes field on {product_id}"

    if not isinstance(required_attributes, dict):
        return None, f"required_attributes is not a dict on {product_id}"

    # Map required_attributes to new fields
    variant_schema, order_item_fields = map_required_attributes(
        required_attributes
    )

    # Validate variant_schema feasibility (max 100 combinations)
    if variant_schema:
        total_combos = 1
        for values in variant_schema.values():
            total_combos *= len(values)
        if total_combos > 100:
            return None, (
                f"variant_schema on {product_id} would produce "
                f"{total_combos} combinations (max 100)"
            )

    # Build purchase_rules
    purchase_rules = build_purchase_rules(item)

    # Build update fields
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "is_parent": True,
        "parent_id": None,
        "tenant": "presmeet",
        "active": True,
        "migrated_at": now,
        # Preserve original required_attributes as read-only legacy field
        "legacy_required_attributes": required_attributes,
    }

    # Only set variant_schema if there are enum axes
    if variant_schema:
        update_fields["variant_schema"] = variant_schema

    # Only set order_item_fields if there are non-enum fields
    if order_item_fields:
        update_fields["order_item_fields"] = order_item_fields

    # Always set purchase_rules (at minimum has order_mode)
    update_fields["purchase_rules"] = purchase_rules

    # Derive a human-friendly name from product_type if available
    product_type = item.get("product_type", "")
    if product_type:
        update_fields["name"] = _humanize_label(product_type)

    # Preserve unit_price as price
    unit_price = item.get("unit_price")
    if unit_price is not None:
        update_fields["price"] = unit_price

    return update_fields, None


def apply_update(table, item: dict, update_fields: dict) -> None:
    """Apply the update to the DynamoDB record."""
    product_id = item.get("product_id", "")

    set_parts = []
    remove_parts = []
    expr_names = {}
    expr_values = {}

    for key, value in update_fields.items():
        safe_key = f"#k_{key}"
        expr_names[safe_key] = key

        if value is None:
            remove_parts.append(safe_key)
        else:
            val_key = f":v_{key}"
            expr_values[val_key] = value
            set_parts.append(f"{safe_key} = {val_key}")

    update_expr = ""
    if set_parts:
        update_expr += "SET " + ", ".join(set_parts)
    if remove_parts:
        update_expr += " REMOVE " + ", ".join(remove_parts)

    update_kwargs = {
        "Key": {"product_id": product_id},
        "UpdateExpression": update_expr.strip(),
        "ExpressionAttributeNames": expr_names,
    }
    if expr_values:
        update_kwargs["ExpressionAttributeValues"] = expr_values

    table.update_item(**update_kwargs)


def migrate(profile: str | None = None, dry_run: bool = False) -> None:
    """Run the PresMeet config migration."""
    table = get_table(profile)

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"{'🔍' if dry_run else '🚀'} [{mode}] Migrating PresMeet config records")
    print(f"   Table: {TABLE_NAME} | Region: {REGION}")
    if profile:
        print(f"   Profile: {profile}")
    print()

    # Scan for config_presmeet_* records
    logger.info("Scanning Producten table for config_presmeet_* records...")
    config_records = scan_presmeet_config_records(table)
    print(f"📋 Found {len(config_records)} config_presmeet_* records")
    print()

    if not config_records:
        print("✅ No config_presmeet_* records found. Nothing to migrate.")
        return

    # Process each record
    migrated = 0
    skipped_already = 0
    skipped_error = 0
    failures: list[dict] = []

    for item in config_records:
        product_id = item.get("product_id", "")
        product_type = item.get("product_type", "unknown")

        # Check if already migrated
        if is_already_migrated(item):
            skipped_already += 1
            logger.info(f"  ⏭️  Skipping (already migrated): {product_id}")
            continue

        # Attempt conversion
        update_fields, error = convert_record(item)

        if error:
            skipped_error += 1
            failures.append({"product_id": product_id, "reason": error})
            logger.error(f"  ❌ Skipping {product_id}: {error}")
            continue

        # Apply the update
        if dry_run:
            print(f"  [DRY] Would migrate: {product_id} (type={product_type})")
            _print_conversion_summary(update_fields)
            migrated += 1
        else:
            try:
                apply_update(table, item, update_fields)
                migrated += 1
                logger.info(
                    f"  ✅ Migrated: {product_id} (type={product_type})"
                )
                _print_conversion_summary(update_fields)
            except Exception as e:
                skipped_error += 1
                failures.append({"product_id": product_id, "reason": str(e)})
                logger.error(f"  ❌ Failed to update {product_id}: {e}")

    # Summary report
    print()
    print("=" * 60)
    print(f"{'🔍 DRY RUN SUMMARY' if dry_run else '🎉 MIGRATION COMPLETE'}")
    print("=" * 60)
    print(f"   Total records scanned:      {len(config_records)}")
    print(f"   Successfully migrated:      {migrated}")
    print(f"   Skipped (already migrated): {skipped_already}")
    print(f"   Skipped (errors):           {skipped_error}")

    if failures:
        print()
        print("   ❌ Failure details:")
        for f in failures:
            print(f"      - {f['product_id']}: {f['reason']}")

    print("=" * 60)

    # Log structured summary for audit
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "total_scanned": len(config_records),
        "migrated": migrated,
        "skipped_already_migrated": skipped_already,
        "skipped_errors": skipped_error,
        "failures": failures,
    }
    logger.info(f"Migration summary: {json.dumps(summary, default=str)}")


def _print_conversion_summary(update_fields: dict) -> None:
    """Print a brief summary of what the conversion produced."""
    vs = update_fields.get("variant_schema")
    oif = update_fields.get("order_item_fields")
    pr = update_fields.get("purchase_rules")

    parts = []
    if vs:
        axes_desc = ", ".join(f"{k}({len(v)} vals)" for k, v in vs.items())
        parts.append(f"variant_schema: [{axes_desc}]")
    if oif:
        field_ids = [f["id"] for f in oif]
        parts.append(f"order_item_fields: {field_ids}")
    if pr:
        parts.append(f"purchase_rules: {pr}")

    for part in parts:
        print(f"        {part}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Migrate PresMeet config_presmeet_* records to unified "
            "Parent_Product model"
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
        help="Preview changes without writing to DynamoDB",
    )
    args = parser.parse_args()

    migrate(profile=args.profile, dry_run=args.dry_run)
