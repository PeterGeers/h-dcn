"""Check if testadmin email exists in Members-Test."""
import boto3
from boto3.dynamodb.conditions import Attr

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
dynamodb = session.resource('dynamodb')
table = dynamodb.Table('Members-Test')

# Search for testadmin
response = table.scan(FilterExpression=Attr('email').contains('testadmin'))
print(f"Members with 'testadmin' in email: {len(response['Items'])}")
for item in response['Items']:
    print(f"  {item.get('member_id')}: {item.get('email')}")

# Also search for webmaster
response2 = table.scan(FilterExpression=Attr('email').contains('webmaster'))
print(f"\nMembers with 'webmaster' in email: {len(response2['Items'])}")
for item in response2['Items']:
    print(f"  {item.get('member_id')}: {item.get('email')}")
