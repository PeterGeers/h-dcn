import boto3

ddb = boto3.resource('dynamodb', region_name='eu-west-1')
table = ddb.Table('Members')

response = table.scan(
    FilterExpression='email = :e',
    ExpressionAttributeValues={':e': 'peter@pgeers.nl'}
)

print(f"Records found: {response['Count']}")
for item in response.get('Items', []):
    print(f"  member_id: {item.get('member_id')}")
    print(f"  email: {item.get('email')}")
    print(f"  voornaam: {item.get('voornaam')}")
    print(f"  achternaam: {item.get('achternaam')}")
    print(f"  status: {item.get('status')}")
