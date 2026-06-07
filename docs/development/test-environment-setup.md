# Test Environment Setup Guide

## Overview

This guide sets up `testportal.h-dcn.nl` with HTTPS support for testing authentication changes without affecting production.

> **Note (June 2026):** The backend now has 85 Lambda function handlers (up from ~46 at the time of the original guide). New features including PresMeet and product unification have been added since this guide was last updated.

## Step-by-Step Setup

### 1. Create S3 Bucket and Basic Setup

```powershell
.\setup-test-environment.ps1
```

### 2. Request SSL Certificate

**Important: SSL certificates for CloudFront must be in us-east-1 region!**

```bash
aws acm request-certificate \
  --domain-name testportal.h-dcn.nl \
  --validation-method DNS \
  --region us-east-1
```

**Note the Certificate ARN from the output - you'll need it for CloudFront.**

### 3. Validate SSL Certificate

- Go to AWS Certificate Manager in us-east-1 region
- Find your certificate request
- Add the DNS validation record to your DNS provider
- Wait for validation (usually 5-10 minutes)

### 4. Create CloudFront Distribution

1. Edit `cloudfront-config.json` and replace `REPLACE_WITH_YOUR_CERTIFICATE_ARN` with your actual certificate ARN
2. Create the distribution:

```bash
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

**Note the Distribution ID and Domain Name from the output.**

### 5. Update DNS

Add a CNAME record in your DNS provider:

```
testportal.h-dcn.nl → [CloudFront Domain Name from step 4]
```

Example:

```
testportal.h-dcn.nl → d1234567890123.cloudfront.net
```

### 6. Update Deployment Script

Edit `deploy-test-frontend.ps1` and replace `REPLACE_WITH_YOUR_DISTRIBUTION_ID` with your actual CloudFront Distribution ID.

### 7. Deploy Your Frontend

```powershell
# Build the frontend first
cd frontend
npm run build
cd ..

# Deploy to test environment
.\deploy-test-frontend.ps1
```

## Daily Workflow

### Making Changes

1. Edit your frontend code
2. Test locally: `npm start` (localhost:3000)
3. Build: `npm run build`
4. Deploy: `.\deploy-test-frontend.ps1`
5. Test at: `https://testportal.h-dcn.nl`

### Benefits

- **Fast deploys**: 30 seconds vs 1 hour SAM builds
- **HTTPS support**: Required for passkey authentication
- **Real domain**: Proper WebAuthn RP ID testing
- **Isolated testing**: No impact on production

## Backend Configuration

You'll also need to update your backend to support the test domain:

### SAM Template Updates

Add test environment variables:

```yaml
Environment:
  Variables:
    WEBAUTHN_RP_ID: !If [IsProduction, "portal.h-dcn.nl", "testportal.h-dcn.nl"]
    FRONTEND_URL:
      !If [
        IsProduction,
        "https://portal.h-dcn.nl",
        "https://testportal.h-dcn.nl",
      ]
```

### CORS Updates

Update CORS headers to include test domain:

```python
headers = {
    'Access-Control-Allow-Origin': 'https://testportal.h-dcn.nl',
    # ... other headers
}
```

## Troubleshooting

### Common Issues After Setup

#### PresMeet Configuration

If testing PresMeet features locally, ensure the following environment variables are set:

- `PRESMEET_TABLE_NAME` — points to the PresMeet DynamoDB table
- PresMeet handlers follow the same auth pattern as other handlers

#### Product Variants Setup

The product unification (March 2026) introduced variant-level operations. For local testing:

- The `Producten` table now stores both products and variants in a unified structure
- Use `admin_bulk_create_variants` and `admin_create_variant` handlers for variant operations
- Stock management operates at the variant level via `admin_add_stock`

### Certificate Issues

- Ensure certificate is in us-east-1 region
- Verify DNS validation record is correct
- Wait for validation to complete before creating CloudFront

### DNS Propagation

- DNS changes can take up to 48 hours to propagate globally
- Use `nslookup testportal.h-dcn.nl` to check

### CloudFront Caching

- Changes may take up to 24 hours without cache invalidation
- Use the deployment script to automatically invalidate cache
- For immediate testing, add `?v=timestamp` to URLs

### HTTPS Redirect

- The configuration automatically redirects HTTP to HTTPS
- Test both `http://` and `https://` URLs to verify
