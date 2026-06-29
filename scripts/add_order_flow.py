"""Add order_flow field to evt-webshop and Toerweekend 2026 in Events-Test."""
import argparse
import boto3

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--profile', default='nonprofit-deploy')
    parser.add_argument('--table', default='Events-Test')
    args = parser.parse_args()

    dry_run = not args.apply
    if dry_run:
        print("=== DRY RUN (use --apply to write) ===\n")

    session = boto3.Session(profile_name=args.profile, region_name='eu-west-1')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(args.table)

    updates = [
        {'event_id': 'evt-webshop', 'order_flow': 'catalog', 'name': 'Webshop'},
        {'event_id': 'e7864b54-5de5-4d77-a', 'order_flow': 'attendee', 'name': 'Toerweekend 2026'},
    ]

    # Find Toerweekend by scanning (event_id might be different)
    response = table.scan()
    items = response['Items']
    toerweekend = next((i for i in items if 'Toerweekend' in i.get('name', '')), None)

    if toerweekend:
        updates[1]['event_id'] = toerweekend['event_id']
    else:
        print("WARNING: Toerweekend 2026 not found in table!")
        updates = [updates[0]]

    for update in updates:
        eid = update['event_id']
        flow = update['order_flow']
        name = update['name']
        print(f"  {'WOULD SET' if dry_run else 'SET'} order_flow='{flow}' on {name} ({eid})")

        if not dry_run:
            table.update_item(
                Key={'event_id': eid},
                UpdateExpression='SET order_flow = :flow',
                ExpressionAttributeValues={':flow': flow},
            )

    print(f"\nDone. {'Use --apply to write.' if dry_run else ''}")

if __name__ == '__main__':
    main()
