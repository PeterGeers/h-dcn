# H-DCN Member Parquet Generation - Docker Container

This Lambda function generates Parquet files from DynamoDB member data using a Docker container approach to handle pandas and pyarrow dependencies.

## Why Docker Container?

- **Size Limit Solution**: AWS Lambda layers have a 250MB limit, but pandas+pyarrow is ~365MB
- **Container Images**: Support up to 10GB, perfect for data science workloads
- **Cost Impact**: Only +€0.08/month for ECR storage (negligible for once-weekly usage)

## Prerequisites

1. **Docker installed** on your development machine
2. **AWS CLI configured** with appropriate permissions
3. **ECR permissions** to create repositories and push images

## Deployment Steps

### 1. Build and Push Container Image

```powershell
# Navigate to the function directory
cd backend/handler/generate_member_parquet

# Build and push using PowerShell script
.\build-and-push.ps1

# Or specify region/account explicitly
.\build-and-push.ps1 -Region "eu-west-1" -AccountId "123456789012"
```

### 2. Deploy SAM Template

The SAM template has been updated to use container images:

```yaml
GenerateMemberParquetFunction:
  Type: AWS::Serverless::Function
  Properties:
    PackageType: Image
    ImageUri: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/hdcn-parquet-generator:latest"
```

Deploy using your existing deployment script:

```powershell
# From backend directory
.\scripts\deployment\backend-build-and-deploy-fast.ps1
```

### 3. Verify Deployment

Test the function using the verification script:

```powershell
# Test locally (will show pandas not available - expected)
python test_pandas_docker_container.py

# Test deployed function via API
curl -X POST https://your-api-gateway-url/analytics/generate-parquet \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json"
```

## Container Contents

The Docker container includes:

- **Base**: `public.ecr.aws/lambda/python:3.11`
- **Dependencies**: pandas==2.0.3, pyarrow==12.0.1, boto3
- **Auth Layer**: Shared authentication utilities
- **Function Code**: Parquet generation logic

## File Structure

```
backend/handler/generate_member_parquet/
├── app.py                    # Main Lambda function
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container definition
├── build-and-push.ps1       # Windows deployment script
├── build-and-push.sh        # Linux deployment script
└── README.md               # This file
```

## Cost Analysis

**Monthly Cost (once-weekly usage):**

- Lambda execution: €2.00/month (unchanged)
- ECR storage: €0.08/month (new)
- **Total**: €2.08/month (+€0.08 increase)

## Troubleshooting

### Build Issues

1. **Docker not running**: Start Docker Desktop
2. **AWS CLI not configured**: Run `aws configure`
3. **Permission denied**: Ensure ECR permissions in IAM

### Deployment Issues

1. **Image not found**: Verify ECR repository exists and image was pushed
2. **Function timeout**: Increase timeout in SAM template if needed
3. **Memory issues**: Increase memory allocation for large datasets

### Runtime Issues

1. **Import errors**: Verify container was built with correct requirements.txt
2. **Auth failures**: Ensure auth layer is properly copied in Dockerfile
3. **S3 permissions**: Verify DynamoDBRole has S3 analytics/\* access

## Verification

After deployment, the function should:

1. ✅ Import pandas and pyarrow successfully
2. ✅ Load member data from DynamoDB
3. ✅ Generate Parquet files with raw data
4. ✅ Upload to S3 analytics/parquet/members/ folder
5. ✅ Return success response with file metadata

## Next Steps

Once deployed and verified:

1. Update plan of approach to mark container tasks as complete
2. Test POST `/analytics/generate-parquet` with authentication
3. Verify parquet files are created in S3
4. Test with full member dataset (1500+ records)
5. Proceed to frontend parquet integration (Phase 2)
