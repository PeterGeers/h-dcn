# H-DCN Backend Infrastructure Documentation
** Docker ECR needed as layers are too small to handle needed libraries pandas pyarrow etc.. Moving to GO is complex but probably a cmore complex approach
## Current Stack: webshop-backend

### Existing Resources (as of 2026-01-07)

#### Lambda Functions

- `GenerateMemberParquetFunction` - Container-based function for parquet generation
- `DownloadParquetFunction` - Layer-based function for parquet download
- Various other CRUD functions for members, products, etc.

#### API Gateway

- Main API: `MyApi`
- Existing endpoints managed by SAM Events in function definitions
- **IMPORTANT**: No manual API Gateway resources should be added to avoid conflicts

#### Current Parquet Function Setup

- **Type**: AWS::Lambda::Function (Container)
- **Image**: ECR image `hdcn-parquet-generator:latest`
- **Memory**: 1024MB
- **Timeout**: 300 seconds
- **Dependencies**: pandas, pyarrow, boto3 (installed in container)

### Migration Guidelines

#### Adding New API Endpoints

1. **Use SAM Events** in function definitions instead of manual API Gateway resources
2. **Check existing resources** before adding new ones
3. **Use consistent naming** patterns

#### Container Functions

1. **Build and push** container images before deployment
2. **Use legacy Docker builder** to avoid OCI format issues: `DOCKER_BUILDKIT=0`
3. **Test locally** when possible

#### Deployment Process

1. Check current stack state
2. Build containers if needed
3. Deploy with SAM
4. Verify deployment
5. Test endpoints

### Commands Reference

```bash
# Check stack resources
aws cloudformation describe-stack-resources --stack-name webshop-backend --region eu-west-1

# Build container
cd backend/handler/generate_member_parquet
./build-container.ps1

# Deploy
cd backend
./scripts/deployment/backend-build-and-deploy-fast.ps1

# Test function
aws lambda invoke --function-name webshop-backend-GenerateMemberParquetFunction --region eu-west-1 response.json
```

### Troubleshooting

#### Docker Image Format Issues

- Use `DOCKER_BUILDKIT=0` to force legacy builder
- Ensure base image is `public.ecr.aws/lambda/python:3.11`
- Check image manifest type in ECR

#### API Gateway Conflicts

- Remove manual API Gateway resources from template
- Use SAM Events in function definitions
- Check existing resources before adding new ones

### Future Considerations

- Consider using AWS Data Wrangler base image when available
- Monitor container cold start times
- Implement proper error handling and logging
- Add CloudWatch alarms for monitoring
