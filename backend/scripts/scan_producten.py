import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Producten')

response = table.scan()
items = response['Items']

for item in items:
    print(item)