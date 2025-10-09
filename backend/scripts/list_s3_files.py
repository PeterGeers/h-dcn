import boto3

s3 = boto3.client('s3')
index = 0  # Change this to select different bucket (0, 1, 2, etc.)

# List all buckets
print("Available buckets:")
buckets_response = s3.list_buckets()
for i, bucket_info in enumerate(buckets_response['Buckets']):
    print(f"  [{i}] {bucket_info['Name']}")
print()

# List files in selected bucket
bucket_name = buckets_response['Buckets'][index]['Name']
response = s3.list_objects_v2(Bucket=bucket_name)

if 'Contents' in response:
    print("Files in bucket:")
    for obj in response['Contents']:
        print(f"  {obj['Key']}")
else:
    print("Bucket is empty")