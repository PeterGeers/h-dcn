#!/usr/bin/env python3
"""
One-time migration: Create Default_Variant records for products that have none.

Background:
    The variant architecture requires every product to have at least one variant
    record (stock is tracked at variant level only). Products created via the
    admin_create_product handler automatically get a Default_Variant. However,
    older products that were created before this handler existed have zero
    variant records — causing inconsistent cart behavior and stock tracking.

    This script scans the Producten table for parent products (is_parent != false)
    that have NO variant records at all, and creates a Default_Variant for each.

Usage:
    # Preview (no changes):
    python scripts/migrate_create_default_variants.py --dry-run

    # Run migration (default profile: nonprofit-deploy):
    python scripts/migrate_create_default_variants.py

    # Use a different profile:
    python scripts/migrate_create_default_variants.py --profile nonprofit-admin

Related:
    - backend/layers/auth-layer/python/shared/variant_helpers.py (create_default_variant)
    - backend/handler/admin_create_product/app.py (auto-creates default variant for new products)
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

REGION = 'eu-west-1'
TABLE_NAME_PROD = 'Producten'
TABLE_NAME_TEST = 'Producten-Test'


def create_default_variant_record(parent_product_id: str, parent_price=None) -> dict:
    """
    Build a Default_Variant record matching the structure from variant_helpers.py.

    Fields:
        product_id: var_{parent_id}_default
        parent_id: reference to parent
        name: "Default Variant"
        is_parent: False
        variant_attributes: {} (empty — signals it's the default)
        prijs: inherited from parent (or None)
        stock: 0
        sold_count: 0
        allow_oversell: False
        active: True
    """
    now = datetime.now(timezone.utc).isoformat()

    record = {
        'product_id': f'var_{parent_product_id}_default',
        'parent_id': parent_product_id,
        'name': 'Default Variant',
        'is_parent': False,
        'variant_attributes': {},
        'stock': 0,
        'sold_count': 0,
        'allow_oversell': False,
        'active': True,
        'created_at': now,
        'updated_at': now,
    }

    # Inherit price from parent if available
    if parent_price is not None:
        try:
            record['prijs'] = Decimal(str(parent_price))
        except (ValueError, TypeError):
            pass  # Skip price if it can't be converted

    return record


def get_all_parent_products(table) -> list:
    """Scan for all products that are parents or legacy (is_parent != false)."""
    scan_kwargs = {
        'ProjectionExpression': 'product_id, naam, is_parent, prijs, active',
    }

    products = []
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            # Include products where is_parent is True or absent (legacy)
            # Exclude variant records (is_parent === False)
            if item.get('is_parent') is not False:
                products.append(item)

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return products


def get_products_with_variants(table) -> set:
    """
    Find all parent_ids that already have at least one variant record.
    Returns a set of parent product_ids.
    """
    scan_kwargs = {
        'FilterExpression': Attr('is_parent').eq(False),
        'ProjectionExpression': 'parent_id',
    }

    parent_ids_with_variants = set()
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            parent_id = item.get('parent_id')
            if parent_id:
                parent_ids_with_variants.add(parent_id)

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return parent_ids_with_variants


def main():
    parser = argparse.ArgumentParser(
        description='Create Default_Variant records for products without any variants'
    )
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile name')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--stage', choices=['test', 'prod'], default='test',
                        help='Target stage: test (Producten-Test) or prod (Producten). Default: test')
    args = parser.parse_args()

    table_name = TABLE_NAME_TEST if args.stage == 'test' else TABLE_NAME_PROD

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(table_name)

    prefix = '[DRY RUN] ' if args.dry_run else ''
    print(f"{prefix}Migration: Create Default_Variant for products without variants")
    print(f"Profile: {args.profile}, Region: {REGION}, Table: {table_name}, Stage: {args.stage}")
    print("=" * 70)

    # Step 1: Get all parent/legacy products
    print("\n📦 Scanning for parent products...")
    parent_products = get_all_parent_products(table)
    print(f"   Found {len(parent_products)} parent/legacy products")

    # Step 2: Find which parents already have variants
    print("\n🔍 Scanning for existing variant records...")
    parents_with_variants = get_products_with_variants(table)
    print(f"   Found {len(parents_with_variants)} products that already have variants")

    # Step 3: Identify products needing a Default_Variant
    products_needing_variant = [
        p for p in parent_products
        if p['product_id'] not in parents_with_variants
    ]
    print(f"\n⚠️  Products WITHOUT any variant: {len(products_needing_variant)}")
    print("=" * 70)

    if not products_needing_variant:
        print("\n✅ All products already have at least one variant. Nothing to do.")
        return

    # Step 4: Create Default_Variant for each
    created_count = 0
    skipped_count = 0

    for i, product in enumerate(products_needing_variant, 1):
        product_id = product['product_id']
        naam = product.get('naam', '(no name)')
        prijs = product.get('prijs')
        active = product.get('active')

        # Skip inactive products (explicitly deactivated)
        if active is False:
            print(f"  [{i}] SKIP (inactive) {product_id} — {naam}")
            skipped_count += 1
            continue

        variant_record = create_default_variant_record(product_id, prijs)
        variant_id = variant_record['product_id']

        print(f"  [{i}] CREATE {variant_id}")
        print(f"       Parent: {product_id} — {naam} (prijs={prijs})")

        if not args.dry_run:
            # Use condition to avoid overwriting if it somehow already exists
            try:
                table.put_item(
                    Item=variant_record,
                    ConditionExpression='attribute_not_exists(product_id)',
                )
                created_count += 1
            except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                print(f"       ⚠️  Already exists — skipped")
                skipped_count += 1
        else:
            created_count += 1

    print("\n" + "=" * 70)
    print(f"Products without variants: {len(products_needing_variant)}")
    print(f"Skipped (inactive): {skipped_count}")
    if args.dry_run:
        print(f"[DRY RUN] Would create {created_count} Default_Variant records.")
        print(f"Run without --dry-run to apply changes.")
    else:
        print(f"✅ Created {created_count} Default_Variant records.")


if __name__ == '__main__':
    main()
