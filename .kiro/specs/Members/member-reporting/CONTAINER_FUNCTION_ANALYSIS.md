# H-DCN Member Reporting - Docker Container Implementation

## Overview

This document provides comprehensive details about the Docker container implementation for the `GenerateMemberParquetFunction` in the H-DCN member reporting system. The container-based approach was chosen to handle large analytics dependencies (pandas, pyarrow) that exceed Lambda ZIP package size limits.

## ✅ Production Implementation Status

**Current Status**: ✅ **Successfully Deployed and Operational**

- Container function deployed and working in production
- Integrated CI/CD pipeline operational
- Performance metrics meeting requirements
- Automatic file cleanup implemented

---

## Docker Container Architecture

### Docker Container Specifications

**Base Image**: `public.ecr.aws/lambda/python:3.11`

- Official AWS Lambda Python 3.11 runtime
- Optimized for Lambda execution environment
- Includes Lambda Runtime Interface Client (RIC)

**Dependencies Installed**:

```dockerfile
RUN pip install --no-cache-dir pandas==2.0.3 pyarrow==12.0.1 boto3==1.34.0 numpy==1.24.3
```

**Container Structure**:

```
/var/task/
├── app.py                    # Main Lambda handler
├── shared/                   # Authentication utilities
│   ├── __init__.py
│   └── auth_utils.py        # From auth layer
└── [Python dependencies]    # Installed in base image
```

### Build Process

**Build Script**: `backend/handler/generate_member_parquet/build-container.ps1`

**Build Steps**:

1. **Setup Build Context**: Creates temporary directory with all required files
2. **Copy Dependencies**:
   - `app.py` (main function code)
   - `shared/` directory from `backend/layers/auth-layer/python/shared/`
   - `Dockerfile` and `requirements.txt`
3. **Docker Build**: Uses legacy builder for Lambda compatibility
4. **ECR Push**: Pushes to `hdcn-parquet-generator:latest`
5. **Cleanup**: Removes temporary build directory

**ECR Repository**:

- **Name**: `hdcn-parquet-generator`
- **Region**: `eu-west-1`
- **URI**: `344561557829.dkr.ecr.eu-west-1.amazonaws.com/hdcn-parquet-generator:latest`

### Deployment Integration

**CI/CD Pipeline**: Integrated into `scripts/deployment/backend-build-and-deploy-fast.ps1`

**Deployment Flow**:

1. **Template Validation**: `sam validate --template template.yaml --lint`
2. **Docker Build**: Automated container build and push to ECR
3. **SAM Build**: Build all ZIP-based Lambda functions
4. **SAM Deploy**: Deploy CloudFormation stack
5. **Container Update**: Update Lambda function with latest container image

**Function Update Command**:

```powershell
aws lambda update-function-code
  --region eu-west-1
  --function-name webshop-backend-GenerateMemberParquetFunction-I331OsLBHOK9
  --image-uri 344561557829.dkr.ecr.eu-west-1.amazonaws.com/hdcn-parquet-generator:latest
```

### Performance Metrics

**Container Performance**:

- **Cold Start**: ~3.2 seconds (includes pandas/pyarrow initialization)
- **Warm Execution**: <1 second for data processing
- **Memory Usage**: ~231 MB peak (1024 MB allocated)
- **File Generation**: ~793ms for 1228 members
- **Output Size**: ~150KB Parquet file

**Cost Analysis**:

- **Estimated Monthly Cost**: ~€0.08
- **Per Execution**: ~€0.0001 (including cold starts)
- **Storage**: ECR storage costs negligible for single image

### Authentication Integration

**Auth Layer Integration**:

- **Source**: `backend/layers/auth-layer/python/shared/auth_utils.py`
- **Copied During Build**: Ensures container has latest auth utilities
- **JWT Validation**: Supports Members_CRUD_All and System_CRUD_All roles
- **CORS Support**: Proper headers for frontend integration

**Authentication Flow**:

1. Extract JWT token from Authorization header
2. Decode and validate token structure
3. Extract user email and roles from token payload
4. Validate required permissions (Members_CRUD_All or System_CRUD_All)
5. Log successful authentication for audit trail

### File Management Features

**Automatic Cleanup**:

- **Strategy**: Create new file first, then delete old files after success
- **Implementation**: `cleanup_old_parquet_files(exclude_key)` function
- **Safety**: Only deletes after successful upload of new file
- **Result**: Always exactly one current Parquet file in S3

**S3 Integration**:

- **Bucket**: `my-hdcn-bucket`
- **Prefix**: `analytics/parquet/members/`
- **Naming**: `members_YYYYMMDD_HHMMSS.parquet`
- **Metadata**: Includes generation timestamp, record count, version info

### Container Advantages Over ZIP

**Why Container Was Chosen**:

1. **Large Dependencies**: pandas + pyarrow exceed ZIP size limits efficiently
2. **Consistent Environment**: Same runtime across all environments
3. **Dependency Management**: All analytics libraries bundled and tested
4. **Performance**: Optimized container layers for faster cold starts
5. **Flexibility**: Can add more analytics libraries without ZIP constraints

**Container vs ZIP Comparison**:

| Aspect            | ZIP Package           | Container Image       |
| ----------------- | --------------------- | --------------------- |
| **Size Limit**    | 50MB (250MB unzipped) | 10GB                  |
| **Dependencies**  | Limited by size       | Full flexibility      |
| **Cold Start**    | ~1-2s                 | ~3-4s                 |
| **Build Process** | SAM handles           | Custom Docker build   |
| **Deployment**    | Direct upload         | ECR + function update |
| **Cost**          | Slightly lower        | Slightly higher       |

### Troubleshooting Guide

**Common Issues**:

1. **Build Context Errors**: Ensure shared directory is copied correctly
2. **ECR Authentication**: Verify AWS credentials and region settings
3. **Function Update Delays**: Allow 30-60 seconds for container updates
4. **Memory Issues**: Monitor CloudWatch for memory usage patterns

**Monitoring**:

- **CloudWatch Logs**: `/aws/lambda/webshop-backend-GenerateMemberParquetFunction-*`
- **Metrics**: Duration, Memory Usage, Error Rate
- **X-Ray Tracing**: Enabled for performance analysis

**Rollback Process**:
If issues occur, rollback by updating function with previous image:

```powershell
aws lambda update-function-code --function-name <name> --image-uri <previous-sha>
```

### Future Enhancements

**Potential Improvements**:

1. **Multi-stage Build**: Reduce final image size
2. **Caching Layers**: Optimize build times with dependency caching
3. **Health Checks**: Add container health monitoring
4. **Versioning**: Implement semantic versioning for container images
5. **Regional Deployment**: Support multiple AWS regions

---

## Historical Context - SAM Template Issues (Resolved)

During initial implementation, we encountered SAM template configuration issues when mixing ZIP and container-based Lambda functions. The key learning was:

### Issue: Global Runtime Conflict

SAM's `Globals` section applied `Runtime`, `Handler`, and `Layers` to ALL functions, but container functions (`PackageType: Image`) cannot have these properties.

### Solution Implemented

Removed conflicting properties from `Globals` section and added them individually to ZIP-based functions:

```yaml
# Current working configuration
GenerateMemberParquetFunction:
  Type: AWS::Serverless::Function
  Properties:
    PackageType: Image
    ImageUri: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/hdcn-parquet-generator:latest"
    Timeout: 300
    MemorySize: 1024
    # No Runtime, Handler, or Layers - these are forbidden for container functions
```

This approach provides clean separation between ZIP and container functions while following AWS SAM best practices.

## References

- [AWS SAM Function Resource](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-function.html)
- [AWS SAM Globals Section](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-specification-template-anatomy-globals.html)
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Docker Best Practices for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html#images-create-from-base)
