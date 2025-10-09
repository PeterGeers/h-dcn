import boto3
import csv
import io

def append_csv_to_dynamodb():
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Producten')
    
    # Download CSV from S3
    response = s3.get_object(Bucket='my-hdcn-bucket', Key='results.csv')
    csv_content = response['Body'].read().decode('utf-8')
    
    # Parse CSV and insert records
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    # print(csv_reader)
    
    with table.batch_writer() as batch:
        for row in csv_reader:
            batch.put_item(Item=row)
    
    print("CSV records appended to DynamoDB table")

if __name__ == "__main__":
    append_csv_to_dynamodb()