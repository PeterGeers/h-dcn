#!/usr/bin/env python3
"""
Migrate cart items from legacy `selectedOption` field to `variant_id` references.

This script scans the Carts table for cart items that still use the old
`selectedOption` text string (e.g., "M", "XL") and replaces them with
the `variant_id` of the matching generated variant record.

Prerequisites:
    - migrate_opties_to_variants.py MUST have been run first (variants must exist)
    - The Producten table must contain variant records with parent_id and variant_attributes

Logic:
    For each cart item with a `selectedOption` field:
    1. Look up the parent product's variants (query parent_id-index)
    2. Find the variant where variant_attributes contains {"opties": selectedOption_value}
    3. If matched: replace selectedOption with variant_id and add variant_attributes
    4. If not matched: log the unmatched item for manual resolution

Usage:
    python backend/scripts/migrate_cart_selectedoption.py --dry-run
    python backend/scripts/migrate_cart_selectedoption.py
    python backend/scripts/migrate_cart_selectedoption.py --profile nonprofit-deploy
"""

import argparse
import json
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key


REGION = "eu-west-1"
CARTS_TABLE_NAME = "Carts"
PRODUCTEN_TABLE_NAME = "Producten"


def get_tables(profile: str | None = None):
    """Create DynamoDB table resources."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    carts_table = dynamodb.Table(CARTS_TABLE_NAME)
    producten_table = dynamodb.Table(PRODUCTEN_TABLE_NAME)
    return carts_table, producten_table


def scan_all_carts(carts_table) -> list[dict]:
    """Scan the Carts table for all cart records."""
    items = []
    scan_kwargs = {}

    while True:
        response = carts_table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def get_variants_for_product(producten_table, product_id: str) -> list[dict]:
    """Query all variant records for a given parent product using the GSI."""
    variants = []
    query_kwargs = {
        "IndexName": "parent_id-index",
        "KeyConditionExpression": Key("parent_id").eq(product_id),
    }

    response = producten_table.query(**query_kwargs)
    variants.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = producten_table.query(**query_kwargs)
        variants.extend(response.get("Items", []))

    return variants


def find_matching_variant(variants: list[dict], selected_option: str) -> dict | None:
    """
    Find the variant whose variant_attributes contains {"opties": selected_option}.

    The matching is case-sensitive and expects an exact match after trimming
    whitespace from the selectedOption value.
    """
    selected_option_trimmed = selected_option.strip()

    for variant in variants:
        attrs = variant.get("variant_attributes", {})
        # Match on the "opties" axis (created by migrate_opties_to_variants.py)
        if attrs.get("opties") == selected_option_trimmed:
            return variant

    return None


def cart_has_selected_option_items(cart: dict) -> bool:
    """Check if a cart contains any items with a selectedOption field."""
    items = cart.get("items", [])
    return any("selectedOption" in item for item in items)


def migrate(profile: str | None = None, dry_run: bool = False) -> None:
    """Run the cart selectedOption migration."""
    carts_table, producten_table = get_tables(profile)

    print(f"{'🔍 DRY RUN' if dry_run else '🚀 LIVE RUN'} — Migrating cart selectedOption to variant_id")
    print(f"   Carts table: {CARTS_TABLE_NAME}")
    print(f"   Producten table: {PRODUCTEN_TABLE_NAME}")
    print(f"   Region: {REGION}")
    if profile:
        print(f"   Profile: {profile}")
    print()

    # Scan all carts
    print("📋 Scanning Carts table...")
    all_carts = scan_all_carts(carts_table)
    print(f"   Found {len(all_carts)} total carts")

    # Filter to carts with selectedOption items
    carts_to_migrate = [c for c in all_carts if cart_has_selected_option_items(c)]
    print(f"   Carts with selectedOption items: {len(carts_to_migrate)}")
    print()

    if not carts_to_migrate:
        print("✅ No carts need migration — no selectedOption fields found.")
        return

    # Track statistics
    total_carts_processed = 0
    total_items_migrated = 0
    total_items_unmatched = 0
    unmatched_items = []
    errors = []

    # Cache for variant lookups (product_id -> variants list)
    variants_cache: dict[str, list[dict]] = {}

    for cart in carts_to_migrate:
        cart_id = cart.get("cart_id", "unknown")
        items = cart.get("items", [])
        cart_modified = False

        print(f"  {'[DRY]' if dry_run else '[LIVE]'} Processing cart: {cart_id}")

        updated_items = []
        for item in items:
            selected_option = item.get("selectedOption")

            if selected_option is None:
                # Item doesn't have selectedOption — keep as-is
                updated_items.append(item)
                continue

            product_id = item.get("product_id", "unknown")

            # Get variants for this product (with caching)
            if product_id not in variants_cache:
                variants_cache[product_id] = get_variants_for_product(
                    producten_table, product_id
                )

            variants = variants_cache[product_id]

            # Find matching variant
            matching_variant = find_matching_variant(variants, selected_option)

            if matching_variant:
                # Replace selectedOption with variant_id and variant_attributes
                new_item = {k: v for k, v in item.items() if k != "selectedOption"}
                new_item["variant_id"] = matching_variant["product_id"]
                new_item["variant_attributes"] = matching_variant.get(
                    "variant_attributes", {}
                )
                updated_items.append(new_item)
                cart_modified = True
                total_items_migrated += 1
                print(
                    f"    ✅ Migrated: product={product_id}, "
                    f'selectedOption="{selected_option}" → '
                    f'variant_id="{matching_variant["product_id"]}"'
                )
            else:
                # No match found — log and leave unchanged
                updated_items.append(item)
                total_items_unmatched += 1
                unmatched_entry = {
                    "cart_id": cart_id,
                    "product_id": product_id,
                    "selectedOption": selected_option,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                unmatched_items.append(unmatched_entry)
                print(
                    f'    ⚠️  Unmatched: product={product_id}, '
                    f'selectedOption="{selected_option}" '
                    f"(no variant found with opties={selected_option})"
                )

        # Write updated cart back to DynamoDB
        if cart_modified and not dry_run:
            try:
                now = datetime.now(timezone.utc).isoformat()
                carts_table.update_item(
                    Key={"cart_id": cart_id},
                    UpdateExpression=(
                        "SET #items = :items, updated_at = :updated_at"
                    ),
                    ExpressionAttributeNames={"#items": "items"},
                    ExpressionAttributeValues={
                        ":items": updated_items,
                        ":updated_at": now,
                    },
                )
            except Exception as e:
                errors.append(f"Failed to update cart {cart_id}: {e}")
                print(f"    ❌ Error updating cart: {e}")

        total_carts_processed += 1
        print()

    # Log unmatched items for manual resolution
    if unmatched_items:
        print("=" * 60)
        print("⚠️  UNMATCHED ITEMS (require manual resolution):")
        print("-" * 60)
        for entry in unmatched_items:
            print(
                f"  cart_id: {entry['cart_id']}, "
                f"product_id: {entry['product_id']}, "
                f"selectedOption: \"{entry['selectedOption']}\""
            )
        print()

        # Write unmatched items to JSON file for reference
        output_file = f"backend/scripts/unmatched_cart_items_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        if not dry_run:
            try:
                with open(output_file, "w") as f:
                    json.dump(unmatched_items, f, indent=2)
                print(f"  📄 Unmatched items logged to: {output_file}")
            except Exception as e:
                print(f"  ⚠️  Could not write log file: {e}")
                print(f"  📋 Unmatched items JSON:")
                print(f"     {json.dumps(unmatched_items, indent=2)}")
        else:
            print(f"  → Would write unmatched items to: {output_file}")
        print()

    # Summary
    print("=" * 60)
    print(f"{'🔍 DRY RUN SUMMARY' if dry_run else '🎉 MIGRATION COMPLETE'}")
    print(f"   Total carts processed: {total_carts_processed}")
    print(f"   Items migrated (selectedOption → variant_id): {total_items_migrated}")
    print(f"   Items unmatched (left unchanged): {total_items_unmatched}")
    if errors:
        print(f"   ❌ Errors: {len(errors)}")
        for err in errors:
            print(f"      - {err}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate cart items from selectedOption to variant_id references"
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
