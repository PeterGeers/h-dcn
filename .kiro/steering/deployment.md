---
inclusion: manual
---

# H-DCN Dashboard Deployment Guidelines

## Deployment Process

### Frontend Deployment

- Deploy to S3 bucket with CloudFront distribution
- Use PowerShell script `frontend/deploy.ps1`
- Environment variables configured in `.env` files
- Build process creates optimized production bundle

### Backend Deployment

- AWS SAM CLI deployment to eu-west-1 region
- Use `sam deploy --guided` for initial setup
- Configuration in `backend/samconfig.toml`
- Lambda functions deployed individually per handler

## Environment Conf

### Frontend Environment Variables

- AWS Cognito User Pool configuration
- API Gateway endpoints
- Stripe publishable keys
- Regional settings

### Backend Configuration

- Parameter Store for dynamic configuration
- DynamoDB table names and regions
- Cognito User Pool ARNs
- S3 bucket configurations

## Deployment Commands

### Frontend

```powershell
cd frontend
npm run build
./deploy.ps1
```

### Backend

```bash
cd backend
sam build
sam deploy
```

## Pre-deployment Checklist

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] AWS credentials configured
- [ ] Parameter Store updated
- [ ] Database migrations completed (if any)
