"""
Cleanup script: Delete draft orders (abandoned carts) from the Orders table.

Usage:
    python scripts/migrate_cleanup_draft_orders.py --dry-run
    python scripts/migrate_cleanup_draft_orders.py

Options:
    --dry-run       Show what would be deleted without actually deleting
    --profile       AWS profile (default: nonprofit-deploy)
    --days          Only delete drafts older than N days (default: 0 = all drafts)
"""

import argparse
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime, timezone, timedelta


def main():
    parser = argparse.ArgumentParser(description='Delete draft orders from DynamoDB')
    parser.add_argument('--dry-run', action='store_true', help='Preview without deleting')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--days', type=int, default=0, help='Only delete drafts older than N days (0 = all)')
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name='eu-west-1')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table('Orders')

    print(f"Scanning Orders table for draft orders...")
    print(f"Profile: {args.profile}")
    print(f"Dry run: {args.dry_run}")
    if args.days > 0:
        print(f"Only drafts older than {args.days} days")
    print()

    # Scan for all draft orders
    filter_expr = Attr('status').eq('draft')
    response = table.scan(FilterExpression=filter_expr)
    drafts = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        drafts.extend(response.get('Items', []))

    print(f"Found {len(drafts)} draft orders total.")

    # Filter by age if --days specified
    if args.days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        cutoff_iso = cutoff.isoformat()
        drafts = [d for d in drafts if d.get('created_at', '') < cutoff_iso]
        print(f"After age filter (>{args.days} days): {len(drafts)} drafts to delete.")

    if not drafts:
        print("Nothing to delete.")
        return

    print()
    print("Orders to delete:")
    print("-" * 80)
    for draft in drafts:
        order_id = draft.get('order_id', '?')
        created = draft.get('created_at', '?')
        email = draft.get('user_email', '?')
        items_count = len(draft.get('items', []))
        print(f"  {order_id[:20]}  created={created[:10]}  user={email}  items={items_count}")
    print("-" * 80)
    print(f"Total: {len(drafts)} orders")
    print()

    if args.dry_run:
        print("DRY RUN — no changes made. Remove --dry-run to delete.")
        return

    # Confirm
    confirm = input(f"Delete {len(drafts)} draft orders? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return

    # Delete
    deleted = 0
    failed = 0
    for draft in drafts:
        order_id = draft['order_id']
        try:
            table.delete_item(Key={'order_id': order_id})
            deleted += 1
        except Exception as e:
            print(f"  FAILED to delete {order_id}: {e}")
            failed += 1

    print(f"\nDone. Deleted: {deleted}, Failed: {failed}")


if __name__ == '__main__':
    main()
