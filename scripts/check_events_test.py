"""Check Events-Test for legacy records (missing new schema fields)."""
import boto3

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
dynamodb = session.resource('dynamodb')
table = dynamodb.Table('Events-Test')

items = []
response = table.scan()
items.extend(response['Items'])
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

print(f"Total records in Events-Test: {len(items)}\n")

new_schema_fields = ['name', 'event_type', 'participation']

print("=== Records WITH new schema (name + event_type + participation) ===\n")
new_records = [i for i in items if all(f in i for f in new_schema_fields)]
for item in new_records:
    print(f"  {item.get('event_id')[:20]:<22} name={item.get('name','?'):<30} type={item.get('event_type'):<18} status={item.get('status','?'):<12} part={item.get('participation','?')}")

print(f"\n=== Records MISSING new schema fields (legacy?) ===\n")
old_records = [i for i in items if not all(f in i for f in new_schema_fields)]
for item in old_records:
    print(f"  {item.get('event_id')[:20]:<22} title={item.get('title','?'):<30} has_name={'name' in item:<6} has_type={'event_type' in item:<6} has_part={'participation' in item}")
    # Show what fields they DO have
    print(f"    fields: {sorted(item.keys())}")
    print()
