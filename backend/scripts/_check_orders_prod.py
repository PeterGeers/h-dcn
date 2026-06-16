"""Quick check of production Orders table state."""
import boto3

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
client = session.client('dynamodb', region_name='eu-west-1')
dynamodb = session.resource('dynamodb', region_name='eu-west-1')

# Describe table for GSI info
response = client.describe_table(TableName='Orders')
table_info = response['Table']
item_count = table_info.get("ItemCount", 0)
table_status = table_info.get("TableStatus")
print(f"Table: Orders")
print(f"Item Count (approximate): {item_count}")
print(f"Table Status: {table_status}")
print()

# GSIs
gsis = table_info.get('GlobalSecondaryIndexes', [])
if gsis:
    print(f"GSIs ({len(gsis)}):")
    for gsi in gsis:
        index_name = gsi["IndexName"]
        index_status = gsi.get("IndexStatus", "?")
        projection = gsi.get("Projection", {}).get("ProjectionType", "?")
        gsi_items = gsi.get("ItemCount", 0)
        print(f"  - {index_name} (Status: {index_status})")
        for key in gsi.get('KeySchema', []):
            print(f"    {key['KeyType']}: {key['AttributeName']}")
        print(f"    Projection: {projection}")
        print(f"    Items: {gsi_items}")
else:
    print("No GSIs on this table.")

print()

# Exact scan count
table = dynamodb.Table('Orders')
total = 0
scan_kwargs = {'Select': 'COUNT'}
while True:
    resp = table.scan(**scan_kwargs)
    total += resp['Count']
    if 'LastEvaluatedKey' not in resp:
        break
    scan_kwargs['ExclusiveStartKey'] = resp['LastEvaluatedKey']
print(f"Exact record count: {total}")

# If there are records, show a sample
if total > 0 and total <= 20:
    print("\nSample records:")
    resp = table.scan(Limit=5)
    for item in resp.get('Items', []):
        order_id = item.get('order_id', '?')
        source = item.get('source_id', item.get('source', '?'))
        status = item.get('status', '?')
        member = item.get('member_id', '?')
        print(f"  - order_id={order_id}, source={source}, status={status}, member={member}")
elif total > 0:
    print(f"\nShowing first 5 records (of {total}):")
    resp = table.scan(Limit=5)
    for item in resp.get('Items', []):
        order_id = item.get('order_id', '?')
        source = item.get('source_id', item.get('source', '?'))
        status = item.get('status', '?')
        member = item.get('member_id', '?')
        print(f"  - order_id={order_id}, source={source}, status={status}, member={member}")
