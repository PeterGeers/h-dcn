"""Seed the member_number counter in the Counters table.

Scans the Members table to find the highest lidnummer, then sets the
counter to that value so the next generated member number is highest + 1.

Usage:
    python scripts/seed_member_number_counter.py --profile nonprofit-deploy
    python scripts/seed_member_number_counter.py --profile nonprofit-deploy --dry-run
"""

import argparse
import boto3
from decimal import Decimal


def get_highest_lidnummer(members_table) -> int:
    """Scan Members table and return the highest numeric lidnummer."""
    highest = 0
    last_evaluated_key = None

    while True:
        scan_kwargs = {
            'ProjectionExpression': 'lidnummer',
        }
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = members_table.scan(**scan_kwargs)

        for item in response.get('Items', []):
            lidnr = item.get('lidnummer')
            if lidnr is not None:
                try:
                    value = int(lidnr) if not isinstance(lidnr, Decimal) else int(lidnr)
                    if value > highest:
                        highest = value
                except (ValueError, TypeError):
                    continue

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    return highest


def main():
    parser = argparse.ArgumentParser(description='Seed member_number counter')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without writing')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource('dynamodb')

    members_table = dynamodb.Table('Members')
    counters_table = dynamodb.Table('Counters')

    print("Scanning Members table for highest lidnummer...")
    highest = get_highest_lidnummer(members_table)
    print(f"Highest lidnummer found: {highest}")

    if args.dry_run:
        print(f"[DRY RUN] Would set counter 'member_number' current_value = {highest}")
        return

    # Set the counter to the highest value (PUT, not ADD)
    counters_table.put_item(
        Item={
            'counter_id': 'member_number',
            'current_value': highest,
        }
    )
    print(f"Set counter 'member_number' to {highest}")
    print(f"Next member activated will receive lidnummer {highest + 1}")


if __name__ == '__main__':
    main()
