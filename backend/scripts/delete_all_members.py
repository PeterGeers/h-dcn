import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table('Members')

def delete_all_members():
    scan = table.scan()
    
    with table.batch_writer() as batch:
        for item in scan['Items']:
            batch.delete_item(Key={'member_id': item['member_id']})
    
    print(f"Deleted {len(scan['Items'])} records from Members table")

if __name__ == "__main__":
    delete_all_members()