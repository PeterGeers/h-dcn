"""Migrate 'tijdstempel' field to 'ingangsdatum' in the Members table.

Some records have the membership start date stored as 'tijdstempel' (legacy name).
The canonical field name is 'ingangsdatum'. This script copies the value and removes
the old field.

Logic per record:
- Has 'tijdstempel' but NOT 'ingangsdatum' → copy tijdstempel to ingangsdatum, remove tijdstempel
- Has both 'tijdstempel' AND 'ingangsdatum' → remove tijdstempel (ingangsdatum takes precedence)
- Has only 'ingangsdatum' → skip (already correct)
- Has neither → skip

Usage:
    python scripts/migrate_tijdstempel_to_ingangsdatum.py --profile nonprofit-deploy --dry-run
    python scripts/migrate_tijdstempel_to_ingangsdatum.py --profile nonprofit-deploy
"""

import argparse
import boto3


def main():
    parser = argparse.ArgumentParser(description='Migrate tijdstempel → ingangsdatum')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without writing')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table('Members')

    print("Scanning Members table for records with 'tijdstempel' field...")

    migrated = 0
    cleaned = 0
    skipped = 0
    last_evaluated_key = None

    while True:
        scan_kwargs = {
            'FilterExpression': 'attribute_exists(tijdstempel)',
            'ProjectionExpression': 'member_id, tijdstempel, ingangsdatum',
        }
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = table.scan(**scan_kwargs)

        for item in response.get('Items', []):
            member_id = item['member_id']
            tijdstempel = item.get('tijdstempel')
            ingangsdatum = item.get('ingangsdatum')

            if not tijdstempel:
                skipped += 1
                continue

            if ingangsdatum:
                # Both exist — remove tijdstempel (ingangsdatum is canonical)
                if args.dry_run:
                    print(f"  [CLEAN] {member_id}: remove tijdstempel (ingangsdatum already '{ingangsdatum}')")
                else:
                    table.update_item(
                        Key={'member_id': member_id},
                        UpdateExpression='REMOVE tijdstempel',
                    )
                cleaned += 1
            else:
                # Only tijdstempel exists — copy to ingangsdatum, then remove
                if args.dry_run:
                    print(f"  [MIGRATE] {member_id}: tijdstempel '{tijdstempel}' → ingangsdatum")
                else:
                    table.update_item(
                        Key={'member_id': member_id},
                        UpdateExpression='SET ingangsdatum = :val REMOVE tijdstempel',
                        ExpressionAttributeValues={':val': tijdstempel},
                    )
                migrated += 1

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Results:")
    print(f"  Migrated (tijdstempel → ingangsdatum): {migrated}")
    print(f"  Cleaned (removed duplicate tijdstempel): {cleaned}")
    print(f"  Skipped: {skipped}")
    print(f"  Total processed: {migrated + cleaned + skipped}")


if __name__ == '__main__':
    main()
