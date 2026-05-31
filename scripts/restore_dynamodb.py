"""Restore DynamoDB tables from personal account to nonprofit account."""
import boto3
import sys

SOURCE_PROFILE = None  # default profile (personal account)
DEST_PROFILE = 'nonprofit-deploy'
REGION = 'eu-west-1'

TABLES = ['Members', 'Memberships', 'Orders', 'Payments', 'Events', 'Carts', 'Producten']


def get_session(profile=None):
    if profile:
        return boto3.Session(profile_name=profile, region_name=REGION)
    return boto3.Session(region_name=REGION)


def scan_all(table_resource):
    items = []
    response = table_resource.scan()
    items.extend(response['Items'])
    while 'LastEvaluatedKey' in response:
        response = table_resource.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    return items


def batch_write(table_resource, items):
    with table_resource.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def main():
    source_session = get_session(SOURCE_PROFILE)
    dest_session = get_session(DEST_PROFILE)

    source_ddb = source_session.resource('dynamodb')
    dest_ddb = dest_session.resource('dynamodb')

    for table_name in TABLES:
        print(f"\n--- {table_name} ---")
        
        # Scan from source
        source_table = source_ddb.Table(table_name)
        items = scan_all(source_table)
        print(f"  Source: {len(items)} items")

        # Write to destination
        dest_table = dest_ddb.Table(table_name)
        batch_write(dest_table, items)
        
        # Verify
        dest_count = dest_table.scan(Select='COUNT')['Count']
        print(f"  Destination: {dest_count} items")
        
        if dest_count == len(items):
            print(f"  OK")
        else:
            print(f"  MISMATCH! Expected {len(items)}, got {dest_count}")
            sys.exit(1)

    print("\n=== All tables restored successfully ===")


if __name__ == '__main__':
    main()
