# H-DCN Deployment Scripts

Automated deployment scripts with built-in smoke testing to prevent broken deployments.

## 🚀 Quick Start

### Deploy Everything

```powershell
.\scripts\deployment\deploy-full-stack.ps1
```

### Deploy Backend Only

```powershell
.\scripts\deployment\backend-build-and-deploy-fast.ps1
```

### Deploy Frontend Only

```powershell
.\scripts\deployment\frontend-build-and-deploy-fast.ps1
```

### Run Smoke Tests Only

```powershell
node scripts/deployment/smoke-test-production.js
```

## 📋 Deployment Scripts

### `deploy-full-stack.ps1`

Complete deployment pipeline that:

1. Deploys backend (SAM build + deploy)
2. Deploys frontend (build + S3 sync + CloudFront invalidation)
3. Runs smoke tests against deployed environment
4. Commits changes to Git

**Options:**

- `-SkipBackend` - Skip backend deployment
- `-SkipFrontend` - Skip frontend deployment
- `-SkipTests` - Skip smoke tests (not recommended!)
- `-GitMessage "message"` - Custom git commit message

**Examples:**

```powershell
# Full deployment
.\scripts\deployment\deploy-full-stack.ps1

# Frontend only with custom message
.\scripts\deployment\deploy-full-stack.ps1 -SkipBackend -GitMessage "Updated UI styles"

# Backend only, no git commit
.\scripts\deployment\deploy-full-stack.ps1 -SkipFrontend -GitMessage ""
```

### `backend-build-and-deploy-fast.ps1`

Backend deployment with:

- Pre-deployment validation (AuthLayer sync check)
- SAM template validation
- Docker container builds
- SAM build (parallel)
- SAM deploy
- Lambda function updates
- **Post-deployment smoke tests**

### `frontend-build-and-deploy-fast.ps1`

Frontend deployment with:

- Pre-deployment validation (env config, critical files)
- React build
- S3 sync (static assets, HTML, images)
- CloudFront cache invalidation
- **Post-deployment smoke tests**

### `smoke-test-production.js`

Tests the REAL deployed application:

- ✅ Frontend accessible and loads correctly
- ✅ API Gateway reachable
- ✅ CORS headers configured
- ✅ Critical endpoints respond (when auth provided)

**Why smoke tests matter:**

- Unit tests can pass but production still breaks
- Catches environment-specific issues
- Validates API Gateway → Lambda connections
- Detects CORS problems
- Verifies auth configuration

**Deployment will FAIL if smoke tests fail** - preventing broken code from going live.

## 🔧 Configuration

### Current Environment: Development

- **Backend Stack:** `webshop-backend-dev`
- **API Stage:** `/dev`
- **Frontend URL:** https://de1irtdutlxqu.cloudfront.net
- **API URL:** https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/dev

### Changing Environment

Edit `backend/template.yaml`:

```yaml
Parameters:
  Environment:
    Default: "dev" # Change to "test" or "prod"
```

Edit `frontend/.env`:

```
REACT_APP_API_BASE_URL=https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/dev
```

## 🐛 Troubleshooting

### Smoke Tests Fail After Deployment

**502 Bad Gateway:**

- Lambda function not invoked
- Check API Gateway integration
- Verify Lambda exists and is active
- Check CloudWatch logs: `aws logs tail /aws/lambda/[function-name] --follow`

**403 Forbidden:**

- Auth required (expected for protected endpoints)
- Check Cognito configuration
- Verify JWT token format

**CORS Errors:**

- Check API Gateway CORS configuration
- Verify `Access-Control-Allow-Origin` header
- Check preflight OPTIONS requests

### Backend Deployment Issues

**AuthLayer Out of Sync:**

- Script auto-fixes this
- Manually: `Copy-Item backend/shared/auth_utils.py backend/layers/auth-layer/python/shared/auth_utils.py`

**SAM Build Fails:**

- Check Python dependencies
- Verify Docker is running (for container-based functions)
- Check `template.yaml` syntax

### Frontend Deployment Issues

**Build Fails:**

- Check for TypeScript errors
- Run `npm install` to update dependencies
- Check `.env` file exists and is valid

**S3 Sync Fails:**

- Verify AWS credentials
- Check S3 bucket exists: `testportal-h-dcn-frontend`
- Verify IAM permissions

## 📊 Monitoring

### Check Recent Logs

```powershell
python read_latest_logs.py
```

### Check Specific Function Logs

```powershell
aws logs tail /aws/lambda/[function-name] --follow --region eu-west-1
```

### Check API Gateway

```powershell
aws apigateway get-rest-apis --region eu-west-1
```

## 🎯 Best Practices

1. **Always run smoke tests** - Don't use `-SkipTests` unless debugging
2. **Deploy backend before frontend** - API changes should be live first
3. **Check logs after deployment** - Verify no errors in CloudWatch
4. **Test manually after deployment** - Smoke tests don't cover everything
5. **Commit working code** - Don't deploy uncommitted changes
6. **Use feature flags** - For gradual rollouts of new features

## 🔄 CI/CD Integration

These scripts are designed to be CI/CD ready:

```yaml
# Example GitHub Actions workflow
- name: Deploy Backend
  run: ./scripts/deployment/backend-build-and-deploy-fast.ps1

- name: Deploy Frontend
  run: ./scripts/deployment/frontend-build-and-deploy-fast.ps1
# Smoke tests run automatically in each script
# Deployment fails if tests fail
```

## 📝 Migration to Production

When ready for production:

1. Create production stack in `backend/samconfig.toml`:

```toml
[prod.deploy.parameters]
stack_name = "webshop-backend-prod"
```

2. Deploy with production environment:

```powershell
sam deploy --config-env prod --parameter-overrides Environment=prod
```

3. Create production frontend bucket
4. Update DNS to point to production CloudFront
5. Use separate Cognito user pool for production

## 🆘 Support

If deployments consistently fail:

1. Check this README for troubleshooting
2. Review CloudWatch logs
3. Run smoke tests manually to see detailed errors
4. Check AWS Console for resource status
