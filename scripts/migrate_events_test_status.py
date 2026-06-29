"""
Normalize status field in Events-Test table.

Rules:
- status absent/empty/None → 'published'
- status 'active' → 'published'
- status already 'published'/'draft'/'archived' → no change

Supports --dry-run (default) and --apply flags.
"""
import argparse
import boto3

VALID_STATUSES = {'draft', 'published', 'archived'}

def main():
    parser = argparse.ArgumentParser(description='Normalize Events-Test status field')
    parser.add_argument('--apply', action='store_true', help='Actually write changes (default is dry-run)')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--table', default='Events-Test', help='Table name')
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
        name = item.get('name', item.get('title', '?'))
        current_status = item.get('status', None)

        if current_status in VALID_STATUSES:
            print(f"  SKIP  {name:<40} status='{current_status}' (already valid)")
            skipped += 1
            continue

        new_status = 'published'
        print(f"  {'WOULD UPDATE' if dry_run else 'UPDATE'}  {name:<40} status='{current_status}' → '{new_status}'")

        if not dry_run:
            table.update_item(
                Key={'event_id': event_id},
                UpdateExpression='SET #s = :new_status',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':new_status': new_status},
            )
        updated += 1

    print(f"\nSummary: {updated} {'would be ' if dry_run else ''}updated, {skipped} skipped")
    if dry_run and updated > 0:
        print("\nRun with --apply to execute changes.")


if __name__ == '__main__':
    main()
