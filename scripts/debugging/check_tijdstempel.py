import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

response = table.scan(Limit=5)
items = response['Items']

print('Sample tijdstempel values:')
for item in items:
    lidnummer = item.get('lidnummer')
    tijdstempel = item.get('tijdstempel')
    print(f"  Member {lidnummer}: tijdstempel = {tijdstempel} (type: {type(tijdstempel).__name__})")
