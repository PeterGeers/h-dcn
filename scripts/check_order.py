import boto3
from boto3.dynamodb.conditions import Attr

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
dynamodb = session.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Orders-Test')
resp = table.scan(FilterExpression=Attr('source_id').eq('542609d8-891e-4f9e-ab97-0c8b3a8c0293'))
items = resp.get('Items', [])
print(f"Found {len(items)} orders")
for item in items:
    print(f"order_id: {item.get('order_id')}")
    print(f"member_id: {item.get('member_id')}")
    print(f"registry_row_id: {item.get('registry_row_id')}")
    print(f"registry_row_label: {item.get('registry_row_label')}")
    print(f"registry_row_logo_url: {item.get('registry_row_logo_url')}")
    print(f"delegates: {item.get('delegates')}")
    print(f"status: {item.get('status')}")
    print()
