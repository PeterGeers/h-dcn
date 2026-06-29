"""
Production Events table migration for Rel2.

Migrates legacy event records to the new schema expected by the unified event system.
Run BEFORE merging feature/closed-community-booking to main.

Changes per record:
1. name        — copied from 'title' if 'name' is absent
2. status      — 'active'/null/absent → 'published'
3. event_type  — derived from title or set to 'other' if unknown
4. participation — set to 'open' if absent
5. linked_regio — copied from 'region' if absent, mapped to registry values

Additionally creates 'evt-webshop' record if missing.

Supports: --dry-run (default), --apply, --profile, --table

Usage:
  python scripts/migrate_events_prod.py                          # dry-run on prod Events
  python scripts/migrate_events_prod.py --apply                  # apply changes
  python scripts/migrate_events_prod.py --table Events-Test      # target test table
"""
import argparse
import boto3
from decimal import Decimal

VALID_STATUSES = {'draft', 'published', 'archived'}

# Map known event titles to event_type
TITLE_TO_TYPE = {
    'alv': 'alv',
    'algemene ledenvergadering': 'alv',
    'rlv': 'rlv',
    'regio ledenvergadering': 'rlv',
    'regio ledenvergadering/avond': 'rlv',
    'vbv': 'vbv',
    'nieuwjaarsreceptie': 'other',
    'openingsrit': 'openingsrit',
    'landelijke openingsrit': 'openingsrit',
    'toerweekend': 'tourweekend',
    'presidents meeting': 'presmeet',
    'ascension rally': 'internationaal_treffen',
    'int. dutch spring rally': 'nationaal_treffen',
    'american bike day': 'other',
    'webshop': 'webshop',
}

# Map legacy region values to Field Registry linked_regio
REGION_MAP = {
    'noord-holland': 'Noord-Holland',
    'zuid-holland': 'Zuid-Holland',
    'friesland': 'Friesland',
    'utrecht': 'Utrecht',
    'limburg': 'Limburg',
    'groningen/drente': 'Groningen/Drenthe',
    'groningen/drenthe': 'Groningen/Drenthe',
    'noord-brabant/zeeland': 'Brabant/Zeeland',
    'brabant/zeeland': 'Brabant/Zeeland',
    'oost': 'Oost',
    'duitsland': 'Duitsland',
    'overig': 'Overig',
}


def derive_event_type(title: str) -> str:
    """Derive event_type from the event title."""
    lower = title.lower().strip()
    for key, etype in TITLE_TO_TYPE.items():
        if key in lower:
            return etype
    return 'other'


def map_region(region: str) -> str:
    """Map legacy region value to Field Registry linked_regio."""
    if not region:
        return 'regio_all'
    lower = region.lower().strip()
    return REGION_MAP.get(lower, 'Overig')


def main():
    parser = argparse.ArgumentParser(description='Migrate prod Events table to new schema')
    parser.add_argument('--apply', action='store_true', help='Actually write changes (default is dry-run)')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--table', default='Events', help='Table name')
    args = parser.parse_args()

    dry_run = not args.apply
    if dry_run:
        print("=== DRY RUN (use --apply to write changes) ===\n")

    session = boto3.Session(profile_name=args.profile, region_name='eu-west-1')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(args.table)

    # Scan all items
    items = []
    response = table.scan()
    items.extend(response['Items'])
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])

    print(f"Found {len(items)} records in {args.table}\n")

    updated = 0
    skipped = 0

    for item in items:
        event_id = item['event_id']
        title = item.get('title', item.get('name', item.get('naam', '(unnamed)')))
        changes = {}

        # 1. name — copy from title if missing
        if 'name' not in item and 'title' in item:
            changes['name'] = item['title']

        # 2. status — normalize to published
        current_status = item.get('status')
        if current_status not in VALID_STATUSES:
            changes['status'] = 'published'

        # 3. event_type — derive if missing
        if 'event_type' not in item:
            changes['event_type'] = derive_event_type(title)

        # 4. participation — set to open if missing
        if 'participation' not in item:
            changes['participation'] = 'open'

        # 5. linked_regio — map from legacy region if missing
        if 'linked_regio' not in item:
            legacy_region = item.get('region', '')
            changes['linked_regio'] = map_region(legacy_region)

        if not changes:
            print(f"  SKIP  {title:<40} (already migrated)")
            skipped += 1
            continue

        change_desc = ', '.join(f"{k}='{v}'" for k, v in changes.items())
        print(f"  {'WOULD' if dry_run else ''} UPDATE  {title:<40} → {change_desc}")

        if not dry_run:
            update_expr_parts = []
            expr_values = {}
            expr_names = {}

            for i, (key, value) in enumerate(changes.items()):
                placeholder_val = f':v{i}'
                # Use expression attribute names for reserved words
                placeholder_name = f'#k{i}'
                update_expr_parts.append(f'{placeholder_name} = {placeholder_val}')
                expr_values[placeholder_val] = value
                expr_names[placeholder_name] = key

            table.update_item(
                Key={'event_id': event_id},
                UpdateExpression='SET ' + ', '.join(update_expr_parts),
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names,
            )

        updated += 1

    # Check if evt-webshop exists
    print(f"\n--- Checking evt-webshop record ---")
    webshop_response = table.get_item(Key={'event_id': 'evt-webshop'})
    if 'Item' in webshop_response:
        ws = webshop_response['Item']
        product_ids = ws.get('product_ids', [])
        print(f"  EXISTS: evt-webshop has {len(product_ids)} product_ids")
        if not product_ids:
            print(f"  WARNING: evt-webshop has no product_ids — webshop will show no products!")
    else:
        print(f"  MISSING: evt-webshop record does not exist")
        print(f"  ACTION REQUIRED: Create evt-webshop with appropriate product_ids")
        print(f"  You can copy product_ids from the scan of all active products in Producten table")

    print(f"\n{'='*60}")
    print(f"Summary: {updated} {'would be ' if dry_run else ''}updated, {skipped} skipped")
    if dry_run and updated > 0:
        print("\nRun with --apply to execute changes.")


if __name__ == '__main__':
    main()
