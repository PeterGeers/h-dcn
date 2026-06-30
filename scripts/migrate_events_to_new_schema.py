"""
Migration script: Normalize existing event records to new schema.

Maps old field names to new Field Registry names and removes deprecated fields.

Old format:
    title, date, description, status (published/cancelled), max_participants

New format (Field Registry):
    name, event_type, start_date, end_date, registration_open, registration_close,
    linked_regio, status (draft/open/closed/archived)

Usage:
    python scripts/migrate_events_to_new_schema.py --dry-run --profile nonprofit-deploy
    python scripts/migrate_events_to_new_schema.py --profile nonprofit-deploy --stage test
    python scripts/migrate_events_to_new_schema.py --profile nonprofit-deploy --stage prod
"""

import argparse
import boto3
from datetime import datetime, timedelta


# Status mapping: old → new
STATUS_MAP = {
    'published': 'open',
    'cancelled': 'archived',
    'draft': 'draft',
    # New statuses pass through unchanged
    'open': 'open',
    'closed': 'closed',
    'archived': 'archived',
}

# Fields to remove after migration
DEPRECATED_FIELDS = ['title', 'date', 'description', 'max_participants']


def get_table_name(stage: str) -> str:
    """Get table name based on stage."""
    if stage == 'test':
        return 'Events-Test'
    return 'Events'


def build_update_params(item: dict) -> dict | None:
    """
    Build DynamoDB update parameters for a single event record.

    Returns None if the record is already in the new format (has 'name' field).
    """
    event_id = item['event_id']

    # Skip if already migrated (has 'name' field and no 'title' field)
    if 'name' in item and 'title' not in item:
        return None

    # --- Build new field values ---
    updates = {}
    removes = []

    # title → name
    if 'title' in item:
        updates['name'] = item['title']

    # date → start_date + end_date (same day)
    if 'date' in item:
        updates['start_date'] = item['date']
        updates['end_date'] = item['date']

    # status mapping
    old_status = item.get('status', 'draft')
    new_status = STATUS_MAP.get(old_status, old_status)
    if new_status != old_status:
        updates['status'] = new_status

    # Add defaults for missing required fields
    if 'event_type' not in item:
        updates['event_type'] = 'other'

    if 'event_category' not in item:
        updates['event_category'] = 'overig'

    if 'participation' not in item:
        updates['participation'] = 'open'

    if 'linked_regio' not in item:
        updates['linked_regio'] = 'regio_all'

    # registration_open/close defaults based on start_date
    start_date_str = updates.get('start_date') or item.get('start_date')
    if start_date_str and 'registration_open' not in item:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            reg_open = (start_date - timedelta(days=30)).isoformat()[:10]
            reg_close = (start_date - timedelta(days=1)).isoformat()[:10]
            updates['registration_open'] = reg_open
            updates['registration_close'] = reg_close
        except (ValueError, TypeError):
            # If date parsing fails, use reasonable defaults
            updates['registration_open'] = '2024-01-01'
            updates['registration_close'] = '2024-01-01'

    # Mark deprecated fields for removal
    for field in DEPRECATED_FIELDS:
        if field in item:
            removes.append(field)

    if not updates and not removes:
        return None

    # Build update expression
    set_parts = []
    expression_values = {}
    expression_names = {}

    for key, value in updates.items():
        attr_name = f"#{key}"
        attr_value = f":{key}"
        set_parts.append(f"{attr_name} = {attr_value}")
        expression_values[attr_value] = value
        expression_names[attr_name] = key

    remove_parts = []
    for field in removes:
        attr_name = f"#rm_{field}"
        remove_parts.append(attr_name)
        expression_names[attr_name] = field

    update_expression = ''
    if set_parts:
        update_expression += 'SET ' + ', '.join(set_parts)
    if remove_parts:
        update_expression += ' REMOVE ' + ', '.join(remove_parts)

    params = {
        'Key': {'event_id': event_id},
        'UpdateExpression': update_expression.strip(),
        'ExpressionAttributeValues': expression_values,
        'ExpressionAttributeNames': expression_names,
    }

    # Remove empty ExpressionAttributeValues if only REMOVE
    if not expression_values:
        del params['ExpressionAttributeValues']

    return params


def scan_all_events(table) -> list:
    """Scan all events with pagination."""
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    return items


def main():
    parser = argparse.ArgumentParser(
        description='Migrate event records to new Field Registry schema'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show changes without writing to DynamoDB'
    )
    parser.add_argument(
        '--profile', default='nonprofit-deploy',
        help='AWS CLI profile to use (default: nonprofit-deploy)'
    )
    parser.add_argument(
        '--stage', choices=['test', 'prod'], default='test',
        help='Target stage: test or prod (default: test)'
    )
    args = parser.parse_args()

    # Connect to DynamoDB
    session = boto3.Session(profile_name=args.profile, region_name='eu-west-1')
    dynamodb = session.resource('dynamodb')
    table_name = get_table_name(args.stage)
    table = dynamodb.Table(table_name)

    print(f"\n{'='*60}")
    print(f"Event Schema Migration")
    print(f"{'='*60}")
    print(f"  Table:   {table_name}")
    print(f"  Stage:   {args.stage}")
    print(f"  Profile: {args.profile}")
    print(f"  Mode:    {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # Scan all events
    print("Scanning events...")
    items = scan_all_events(table)
    print(f"Found {len(items)} event(s)\n")

    migrated = 0
    skipped = 0
    errors = 0

    for item in items:
        event_id = item['event_id']
        params = build_update_params(item)

        if params is None:
            print(f"  SKIP  {event_id} — already in new format")
            skipped += 1
            continue

        # Show what would change
        old_name = item.get('title', item.get('name', '?'))
        print(f"  MIGRATE  {event_id} ({old_name})")
        print(f"    SET: {list(params.get('ExpressionAttributeValues', {}).keys())}")
        if 'REMOVE' in params.get('UpdateExpression', ''):
            remove_fields = [v for k, v in params['ExpressionAttributeNames'].items() if k.startswith('#rm_')]
            print(f"    REMOVE: {remove_fields}")

        if not args.dry_run:
            try:
                table.update_item(**params)
                print(f"    ✅ Done")
                migrated += 1
            except Exception as e:
                print(f"    ❌ Error: {e}")
                errors += 1
        else:
            migrated += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"  Total:    {len(items)}")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")
    if args.dry_run:
        print(f"\n  ⚠️  DRY RUN — no changes written. Run without --dry-run to apply.")
    print()


if __name__ == '__main__':
    main()
