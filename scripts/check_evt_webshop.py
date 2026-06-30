"""Check evt-webshop record in Events-Test for product_ids."""
import boto3
import json
from decimal import Decimal

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
dynamodb = session.resource('dynamodb')
table = dynamodb.Table('Events-Test')

response = table.get_item(Key={'event_id': 'evt-webshop'})
item = response.get('Item', {})

print("evt-webshop record:")
for key in sorted(item.keys()):
    val = item[key]
    if isinstance(val, list) and len(val) > 5:
        print(f"  {key}: [{len(val)} items] {val[:5]}...")
    elif isinstance(val, Decimal):
        print(f"  {key}: {float(val)}")
    else:
        print(f"  {key}: {val}")
