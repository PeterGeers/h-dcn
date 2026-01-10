#!/usr/bin/env python3
"""
Test script to verify parquet generation functionality
"""
import boto3
import json
from datetime import datetime

def test_parquet_generation():
    """Test the parquet generation function"""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    
    # Function name
    function_name = 'webshop-backend-GenerateMemberParquetFunction-I331OsLBHOK9'
    
    # Create a test event that simulates direct invocation (bypassing API Gateway auth)
    test_event = {
        'source': 'test',  # This will bypass the API Gateway authentication
        'options': {}
    }
    
    try:
        print("🧪 Testing parquet generation function...")
        
        # Invoke the function
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(test_event)
        )
        
        # Read the response
        result = json.loads(response['Payload'].read())
        
        print(f"✅ Function executed successfully!")
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing function: {e}")
        return None

def check_s3_files():
    """Check what parquet files exist in S3"""
    
    s3_client = boto3.client('s3')
    bucket = 'my-hdcn-bucket'
    prefix = 'analytics/parquet/members/'
    
    try:
        print(f"\n📁 Checking S3 bucket: {bucket}/{prefix}")
        
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' in response:
            print(f"Found {len(response['Contents'])} parquet files:")
            for obj in response['Contents']:
                print(f"  📄 {obj['Key']} ({obj['Size']} bytes, {obj['LastModified']})")
                
                # Get metadata
                head_response = s3_client.head_object(Bucket=bucket, Key=obj['Key'])
                if 'Metadata' in head_response:
                    print(f"     Metadata: {head_response['Metadata']}")
        else:
            print("No parquet files found")
            
    except Exception as e:
        print(f"❌ Error checking S3: {e}")

if __name__ == "__main__":
    print("🔍 H-DCN Parquet Generation Test")
    print("=" * 40)
    
    # Check existing files
    check_s3_files()
    
    # Test function (this will likely fail due to auth, but that's expected)
    print("\n" + "=" * 40)
    test_parquet_generation()