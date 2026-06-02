"""
One-time migration: add tenant field to all existing DynamoDB records
that do not yet have a tenant field.

Rules:
- Records with `source` containing "presmeet" → tenant = "presmeet"
- All other records → tenant = "h-dcn"

Run BEFORE v2 deployment.

Usage:
    python scripts/migrate_add_tenant_field.py --profile nonprofit-deploy
    python scripts/migrate_add_tenant_field.py --profile nonprofit-deploy --dry-run
"""

import argparse
import sys

import boto3
from boto3.dynamodb.conditions import Attr

REGION = 'eu-west-1'

TABLES = ['Members', 'Producten', 'Orders', 'Carts', 'Payments']

KEY_MAP = {
    'Members': 'member_id',
    'Producten': 'id',
    'Orders': 'order_id',
    'Carts': 'cart_id',
    'Payments': 'payment_id',
}


def get_key_name(table_name: str) -> str:
    """Return the primary key attribute name for a given table."""
    return KEY_MAP[table_name]


def determine_tenant(item: dict) -> str:
    """Determine tenant value based on the record's source field."""
    source = item.get('source', '')
    if isinstance(source, str) and 'presmeet' in source.lower():
        return 'presmeet'
    return 'h-dcn'


def migrate_table(table_name: str, dynamodb, dry_run: bool = False) -> dict:
    """
    Scan a table for records missing the tenant field and add it.

    Returns a dict with scan/update counts.
    """
    table = dynamodb.Table(table_name)
    key_name = get_key_name(table_name)

    scan_kwargs = {
        'FilterExpression': Attr('tenant').not_exists(),
    }

    scanned = 0
    updated = 0
    tenant_counts = {'presmeet': 0, 'h-dcn': 0}

    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print(f"{'='*60}")

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        scanned += len(items)

        for item in items:
            tenant = determine_tenant(item)
            tenant_counts[tenant] += 1

            if dry_run:
                print(f"  [DRY-RUN] Would set tenant={tenant} on "
                      f"{key_name}={item.get(key_name, 'UNKNOWN')}")
            else:
                if key_name not in item:
                    print(f"  [SKIP] Record missing key '{key_name}': {list(item.keys())[:5]}")
                    continue
                table.update_item(
                    Key={key_name: item[key_name]},
                    UpdateExpression='SET tenant = :t',
                    ExpressionAttributeValues={':t': tenant},
                )
                updated += 1

        # Progress logging per page
        if items:
            print(f"  Processed page: {len(items)} records "
                  f"(total scanned: {scanned})")

        # Check for more pages
        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    # Summary for this table
    print(f"\n  Summary for {table_name}:")
    print(f"    Records scanned (missing tenant): {scanned}")
    if dry_run:
        print(f"    Would update: {scanned}")
    else:
        print(f"    Records updated: {updated}")
    print(f"    Tenant breakdown: presmeet={tenant_counts['presmeet']}, "
          f"h-dcn={tenant_counts['h-dcn']}")

    return {
        'table': table_name,
        'scanned': scanned,
        'updated': updated,
        'tenant_counts': tenant_counts,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Migrate DynamoDB records: add tenant field to records that lack it.'
    )
    parser.add_argument(
        '--profile',
        default='nonprofit-deploy',
        help='AWS CLI profile to use (default: nonprofit-deploy)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Log what would be changed without writing to DynamoDB',
    )
    parser.add_argument(
        '--tables',
        nargs='+',
        choices=TABLES,
        default=TABLES,
        help='Specific tables to migrate (default: all)',
    )
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = session.resource('dynamodb')

    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(f"\n{'#'*60}")
    print(f"  Tenant Field Migration ({mode} MODE)")
    print(f"  Profile: {args.profile}")
    print(f"  Region: {REGION}")
    print(f"  Tables: {', '.join(args.tables)}")
    print(f"{'#'*60}")

    # Confirmation prompt in write mode
    if not args.dry_run:
        print("\n[WARNING] This will WRITE to DynamoDB tables in production.")
        confirm = input("Type 'yes' to continue: ")
        if confirm.strip().lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    results = []
    for table_name in args.tables:
        result = migrate_table(table_name, dynamodb, dry_run=args.dry_run)
        results.append(result)

    # Final summary
    total_scanned = sum(r['scanned'] for r in results)
    total_updated = sum(r['updated'] for r in results)
    total_presmeet = sum(r['tenant_counts']['presmeet'] for r in results)
    total_hdcn = sum(r['tenant_counts']['h-dcn'] for r in results)

    print(f"\n{'#'*60}")
    print(f"  MIGRATION COMPLETE ({mode} MODE)")
    print(f"{'#'*60}")
    print(f"  Total records scanned: {total_scanned}")
    if args.dry_run:
        print(f"  Total records that would be updated: {total_scanned}")
    else:
        print(f"  Total records updated: {total_updated}")
    print(f"  Tenant breakdown: presmeet={total_presmeet}, h-dcn={total_hdcn}")
    print()


if __name__ == '__main__':
    main()
