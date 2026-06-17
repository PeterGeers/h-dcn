#!/usr/bin/env python3
"""
One-time migration: Remove variant_schema from all parent products in Producten table.

The variant_schema field is no longer used — the admin UI and webshop now derive
variant axes directly from variant records. This script strips the dead field
from existing parent product records.

Usage:
    # Preview (no changes):
    python scripts/migrate_remove_variant_schema.py --dry-run

    # Run migration (default profile: nonprofit-deploy):
    python scripts/migrate_remove_variant_schema.py

    # Use a different profile:
    python scripts/migrate_remove_variant_schema.py --profile nonprofit-admin
"""

import argparse
import boto3

REGION = 'eu-west-1'
TABLE_NAME = 'Producten'


def main():
    parser = argparse.ArgumentParser(description='Remove variant_schema from Producten table')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile name')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning {TABLE_NAME} for records with variant_schema...")
    print(f"Profile: {args.profile}, Region: {REGION}")
    print("=" * 60)

    # Scan for all items that have variant_schema attribute
    scan_kwargs = {
        'FilterExpression': 'attribute_exists(variant_schema)',
        'ProjectionExpression': 'product_id, naam, is_parent, variant_schema',
    }

    items_found = 0
    items_updated = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            items_found += 1
            product_id = item['product_id']
            naam = item.get('naam', '(no name)')
            is_parent = item.get('is_parent')
            schema_keys = list(item.get('variant_schema', {}).keys()) if isinstance(item.get('variant_schema'), dict) else str(item.get('variant_schema'))

            print(f"  [{items_found}] {product_id} — {naam} (is_parent={is_parent})")
            print(f"       variant_schema keys: {schema_keys}")

            if not args.dry_run:
                table.update_item(
                    Key={'product_id': product_id},
                    UpdateExpression='REMOVE variant_schema',
                    ConditionExpression='attribute_exists(variant_schema)',
                )
                items_updated += 1

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    print("=" * 60)
    print(f"Records with variant_schema found: {items_found}")
    if args.dry_run:
        print(f"[DRY RUN] No changes made. Run without --dry-run to remove the field.")
    else:
        print(f"Records updated (variant_schema removed): {items_updated}")


if __name__ == '__main__':
    main()
