#!/usr/bin/env python3
"""
Migrate existing Producten records to the unified product/variant model.

Scans the Producten table for existing product records (source: presmeet_config)
and converts them to the unified format:
- Sets is_parent: true, parent_id: null on each config record
- Creates a Default_Variant record for each product with:
  - product_id: var_{original_id}_default
  - parent_id: original_id
  - variant_attributes: {}
  - stock: 0
  - sold_count: 0
  - allow_oversell: false

Usage:
    python backend/scripts/migrate_products_to_unified.py --dry-run
    python backend/scripts/migrate_products_to_unified.py
    python backend/scripts/migrate_products_to_unified.py --profile nonprofit-deploy
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal

import boto3


REGION = "eu-west-1"
TABLE_NAME = "Producten"


TABLE_KEY = "id"  # Producten table partition key is 'id'


def get_table(profile: str | None = None):
    """Create a DynamoDB table resource."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


def scan_existing_products(table) -> list[dict]:
    """Scan for existing product/config records that need migration."""
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


def needs_migration(item: dict) -> bool:
    """Check if a record needs migration to unified format.

    Migrates records that:
    - Have source 'presmeet_config' (config records) OR are h-dcn products
    - Do NOT already have is_parent set (not yet migrated)
    - Are NOT variant records (no parent_id set, or parent_id is null)
    """
    # Skip records that are already migrated
    if "is_parent" in item:
        return False

    # Skip records that are already variant records
    if item.get("parent_id"):
        return False

    # Migrate presmeet_config records
    if item.get("source") == "presmeet_config":
        return True

    # Migrate h-dcn product records (have naam field, tenant=h-dcn)
    if item.get("tenant") == "h-dcn" and item.get("naam"):
        return True

    return False


def create_unified_product_update(item: dict) -> dict:
    """Create the update fields to convert a record to unified format."""
    tenant = item.get("tenant", "presmeet" if item.get("source") == "presmeet_config" else "h-dcn")
    return {
        "is_parent": True,
        "parent_id": None,
        "tenant": tenant,
        "migrated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_default_variant(parent_item: dict) -> dict:
    """Create a Default_Variant record for a parent product."""
    parent_id = parent_item["id"]  # Table key is 'id'
    variant_id = f"var_{parent_id}_default"
    tenant = parent_item.get("tenant", "presmeet" if parent_item.get("source") == "presmeet_config" else "h-dcn")

    # Get price from appropriate field
    price = parent_item.get("unit_price") or parent_item.get("prijs")
    if price and isinstance(price, str):
        price = Decimal(price)
    elif price is None:
        price = Decimal("0.00")

    return {
        "id": variant_id,
        "product_id": variant_id,
        "parent_id": parent_id,
        "is_parent": False,
        "tenant": tenant,
        "variant_attributes": {},
        "stock": 0,
        "sold_count": 0,
        "allow_oversell": False,
        "price": price,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "migration",
    }


def migrate(profile: str | None = None, dry_run: bool = False) -> None:
    """Run the migration."""
    table = get_table(profile)

    print(f"{'🔍 DRY RUN' if dry_run else '🚀 LIVE RUN'} — Migrating Producten to unified model")
    print(f"   Table: {TABLE_NAME} | Region: {REGION}")
    if profile:
        print(f"   Profile: {profile}")
    print()

    # Scan all records
    print("📋 Scanning Producten table...")
    all_items = scan_existing_products(table)
    print(f"   Found {len(all_items)} total records")
    print()

    # Filter to records needing migration
    to_migrate = [item for item in all_items if needs_migration(item)]
    already_migrated = [item for item in all_items if item.get("is_parent") is True]
    variant_records = [item for item in all_items if item.get("parent_id")]

    print(f"   Records needing migration: {len(to_migrate)}")
    print(f"   Already migrated (is_parent=true): {len(already_migrated)}")
    print(f"   Existing variant records: {len(variant_records)}")
    print()

    if not to_migrate:
        print("✅ Nothing to migrate — all records are already in unified format.")
        return

    # Process each record
    migrated_count = 0
    variants_created = 0
    errors = []

    for item in to_migrate:
        product_id = item["id"]  # Table key is 'id'
        product_type = item.get("product_type", item.get("groep", "unknown"))
        tenant = item.get("tenant", "presmeet" if item.get("source") == "presmeet_config" else "h-dcn")

        print(f"  {'[DRY]' if dry_run else '[LIVE]'} Migrating: {product_id} (type={product_type}, tenant={tenant})")

        # Check if Default_Variant already exists
        variant_id = f"var_{product_id}_default"
        existing_variant = None
        if not dry_run:
            try:
                resp = table.get_item(Key={"id": variant_id})
                existing_variant = resp.get("Item")
            except Exception:
                pass

        # Update the parent record
        update_fields = create_unified_product_update(item)

        if not dry_run:
            try:
                remove_parts = []
                set_parts = []
                expr_names = {}
                expr_values = {}

                for key, value in update_fields.items():
                    if value is None:
                        remove_parts.append(f"#k_{key}")
                        expr_names[f"#k_{key}"] = key
                    else:
                        safe_key = f"#k_{key}"
                        val_key = f":v_{key}"
                        expr_names[safe_key] = key
                        expr_values[val_key] = value
                        set_parts.append(f"{safe_key} = {val_key}")

                update_expr = ""
                if set_parts:
                    update_expr += "SET " + ", ".join(set_parts)
                if remove_parts:
                    update_expr += " REMOVE " + ", ".join(remove_parts)

                update_kwargs = {
                    "Key": {"id": product_id},
                    "UpdateExpression": update_expr.strip(),
                    "ExpressionAttributeNames": expr_names,
                }
                if expr_values:
                    update_kwargs["ExpressionAttributeValues"] = expr_values

                table.update_item(**update_kwargs)
                migrated_count += 1
                print(f"    ✅ Updated parent record (is_parent=true, tenant={tenant})")
            except Exception as e:
                errors.append(f"Failed to update {product_id}: {e}")
                print(f"    ❌ Error updating parent: {e}")
                continue
        else:
            migrated_count += 1
            print(f"    → Would update: is_parent=true, tenant={tenant}")

        # Create Default_Variant
        if existing_variant:
            print(f"    ℹ️  Default_Variant already exists: {variant_id}")
        else:
            variant_record = create_default_variant(item)

            if not dry_run:
                try:
                    table.put_item(Item=variant_record)
                    variants_created += 1
                    print(f"    ✅ Created Default_Variant: {variant_id}")
                except Exception as e:
                    errors.append(f"Failed to create variant {variant_id}: {e}")
                    print(f"    ❌ Error creating variant: {e}")
            else:
                variants_created += 1
                print(f"    → Would create Default_Variant: {variant_id}")
                price = item.get("unit_price") or item.get("prijs", "0.00")
                print(f"      stock=0, sold_count=0, allow_oversell=false, price=€{price}")

        print()

    # Summary
    print("=" * 60)
    print(f"{'🔍 DRY RUN SUMMARY' if dry_run else '🎉 MIGRATION COMPLETE'}")
    print(f"   Parent records {'would be ' if dry_run else ''}updated: {migrated_count}")
    print(f"   Default_Variants {'would be ' if dry_run else ''}created: {variants_created}")
    if errors:
        print(f"   ❌ Errors: {len(errors)}")
        for err in errors:
            print(f"      - {err}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate Producten records to unified product/variant model"
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
