"""
Populate evt-webshop product_ids in the Events table.

Scans Producten table for active parent products (is_parent != false, active != false)
and sets their product_ids on the evt-webshop event record.

Supports: --dry-run (default), --apply, --profile

Usage:
  python scripts/populate_webshop_product_ids.py                  # dry-run
  python scripts/populate_webshop_product_ids.py --apply          # apply changes
"""
import argparse
import boto3


def main():
    parser = argparse.ArgumentParser(description='Populate evt-webshop product_ids')
    parser.add_argument('--apply', action='store_true', help='Actually write changes (default is dry-run)')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--events-table', default='Events', help='Events table name')
    parser.add_argument('--products-table', default='Producten', help='Producten table name')
    args = parser.parse_args()

    dry_run = not args.apply
    if dry_run:
        print("=== DRY RUN (use --apply to write changes) ===\n")

    session = boto3.Session(profile_name=args.profile, region_name='eu-west-1')
    dynamodb = session.resource('dynamodb')
    products_table = dynamodb.Table(args.products_table)
    events_table = dynamodb.Table(args.events_table)

    # Scan all products
    items = []
    response = products_table.scan()
    items.extend(response['Items'])
    while 'LastEvaluatedKey' in response:
        response = products_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])

    print(f"Found {len(items)} total products in {args.products_table}\n")

    # Filter: active parent products only
    # A parent product: is_parent is True OR (no parent_id field = top-level product)
    # Active: active is not explicitly False
    parent_product_ids = []
    for item in items:
        product_id = item['product_id']
        name = item.get('naam', item.get('name', '(unnamed)'))
        active = item.get('active')
        parent_id = item.get('parent_id')
        is_parent = item.get('is_parent')

        # Skip variants (have a parent_id)
        if parent_id:
            continue

        # Skip explicitly deactivated products
        if active is False:
            continue

        parent_product_ids.append(product_id)
        print(f"  INCLUDE  {name:<40} ({product_id})")

    print(f"\n{len(parent_product_ids)} active parent products found.\n")

    # Get current evt-webshop record
    ws_response = events_table.get_item(Key={'event_id': 'evt-webshop'})
    if 'Item' in ws_response:
        current_ids = ws_response['Item'].get('product_ids', [])
        print(f"Current evt-webshop product_ids: {len(current_ids)} items")
    else:
        print("evt-webshop record not found — will need to create it")
        print("ERROR: Cannot proceed without evt-webshop record. Run migrate_events_prod.py first.")
        return

    if set(parent_product_ids) == set(current_ids):
        print("\nNo changes needed — product_ids already match.")
        return

    print(f"\n{'WOULD SET' if dry_run else 'SETTING'} evt-webshop.product_ids to {len(parent_product_ids)} items")

    if not dry_run:
        events_table.update_item(
            Key={'event_id': 'evt-webshop'},
            UpdateExpression='SET product_ids = :pids',
            ExpressionAttributeValues={':pids': parent_product_ids},
        )
        print("Done — evt-webshop updated.")

    print(f"\n{'='*60}")
    if dry_run:
        print(f"Run with --apply to set {len(parent_product_ids)} product_ids on evt-webshop.")


if __name__ == '__main__':
    main()
