#!/usr/bin/env python3
"""
One-time migration: Remove event_id and event_ids from all products in Producten table.

The event_id and event_ids fields are no longer used — the event.product_ids[] array
is now the single source of truth for event-product associations. This script strips
the deprecated fields from existing product records.

Usage:
    # Preview (no changes):
    python scripts/migrate_remove_event_id_from_products.py --dry-run

    # Run migration (default profile: nonprofit-deploy):
    python scripts/migrate_remove_event_id_from_products.py

    # Use a different profile:
    python scripts/migrate_remove_event_id_from_products.py --profile nonprofit-admin
"""

import argparse
import boto3

REGION = 'eu-west-1'
TABLE_NAME = 'Producten'


def main():
    parser = argparse.ArgumentParser(
        description='Remove event_id and event_ids from Producten table'
    )
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile name')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning {TABLE_NAME} for records with event_id or event_ids...")
    print(f"Profile: {args.profile}, Region: {REGION}")
    print("=" * 60)

    # Scan for all items that have event_id OR event_ids attribute
    scan_kwargs = {
        'FilterExpression': 'attribute_exists(event_id) OR attribute_exists(event_ids)',
        'ProjectionExpression': 'product_id, naam, event_id, event_ids',
    }

    total_scanned = 0
    items_matching = 0
    items_modified = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        total_scanned += response.get('ScannedCount', 0)

        for item in items:
            items_matching += 1
            product_id = item['product_id']
            naam = item.get('naam', '(no name)')
            event_id = item.get('event_id', '(none)')
            event_ids = item.get('event_ids', '(none)')

            print(f"  [{items_matching}] {product_id} — {naam}")
            print(f"       event_id: {event_id}")
            print(f"       event_ids: {event_ids}")

            if not args.dry_run:
                # Build REMOVE expression for whichever attributes exist
                remove_attrs = []
                if 'event_id' in item:
                    remove_attrs.append('event_id')
                if 'event_ids' in item:
                    remove_attrs.append('event_ids')

                table.update_item(
                    Key={'product_id': product_id},
                    UpdateExpression=f"REMOVE {', '.join(remove_attrs)}",
                )
                items_modified += 1

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    print("=" * 60)
    print(f"Total records scanned: {total_scanned}")
    print(f"Records matching (have event_id or event_ids): {items_matching}")
    if args.dry_run:
        print(f"[DRY RUN] No changes made. Run without --dry-run to remove the fields.")
    else:
        print(f"Records modified (event_id/event_ids removed): {items_modified}")


if __name__ == '__main__':
    main()
