"""Check if member exists for the logged-in user."""
import boto3
import json
from boto3.dynamodb.conditions import Attr

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
ddb = session.resource('dynamodb')
table = ddb.Table('Members')

# Scan for any members to see the table structure
resp = table.scan(Limit=3, ProjectionExpression='member_id, email, #n', ExpressionAttributeNames={'#n': 'name'})
print(f"Members table sample (Count: {resp['Count']}):")
for item in resp['Items']:
    print(f"  {item.get('member_id')}: {item.get('email', 'NO EMAIL')} - {item.get('name', '')}")

# Check peter's email specifically
print("\nSearching for peter@pgeers.nl...")
resp2 = table.scan(FilterExpression=Attr('email').eq('peter@pgeers.nl'))
print(f"  Found: {resp2['Count']}")
if resp2['Items']:
    print(f"  {json.dumps(resp2['Items'][0], default=str, indent=2)}")
