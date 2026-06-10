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

### Frontend Changes

1. Edit your frontend code
2. Test locally: `npm start` (localhost:3000)
3. Build: `npm run build`
4. Deploy: `.\deploy-test-frontend.ps1`
5. Test at: `https://testportal.h-dcn.nl`

### Backend Test Workflow

1. Make backend changes
2. Run tests locally: `.\run-tests.ps1`
3. Deploy test stack:
   ```bash
   sam deploy \
     --stack-name h-dcn-test \
     --region eu-west-1 \
     --profile nonprofit-deploy \
     --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
     --resolve-s3 \
     --no-confirm-changeset \
     --no-fail-on-empty-changeset \
     --parameter-overrides \
       Stage=test \
       Table=Producten-Test \
       MembersTable=Members-Test \
       PaymentsTable=Payments-Test \
       EventsTable=Events-Test \
       MembershipsTable=Memberships-Test \
       CartsTable=Carts-Test \
       OrdersTable=Orders-Test \
       CountersTable=Counters-Test \
       StockMovementsTableName=StockMovements-Test
   ```
4. Seed test data (if needed): `python scripts/seed-test-data.py`
5. Verify at: `https://testportal.h-dcn.nl`

### Benefits

- **Fast deploys**: 30 seconds vs 1 hour SAM builds
- **HTTPS support**: Required for passkey authentication
- **Real domain**: Proper WebAuthn RP ID testing
- **Isolated testing**: No impact on production

## Backend Configuration

The backend uses a **Stage-parameterized** approach. The same SAM template (`backend/template.yaml`) supports both production and test via a `Stage` parameter and `Mappings` section — no template forking or `!If [IsProduction, ...]` conditions needed.

### Stage Parameter and Mappings

The SAM template defines:

- A `Stage` parameter with allowed values `prod` and `test` (default: `prod`)
- A `StageConfig` mapping that resolves stage-dependent values:

```yaml
Mappings:
  StageConfig:
    prod:
      CorsOrigin: "https://portal.h-dcn.nl"
      OrganizationWebsite: "https://portal.h-dcn.nl"
    test:
      CorsOrigin: "https://testportal.h-dcn.nl"
      OrganizationWebsite: "https://testportal.h-dcn.nl"
```

The CORS origin and organization website are resolved at deploy time based on the `Stage` parameter.

### CORS Configuration

CORS is handled via the `CORS_ALLOWED_ORIGIN` environment variable, set per-stage in the SAM template globals:

```yaml
Globals:
  Function:
    Environment:
      Variables:
        CORS_ALLOWED_ORIGIN: !FindInMap [StageConfig, !Ref Stage, CorsOrigin]
```

The `cors_headers()` function in `shared/auth_utils.py` reads this environment variable:

```python
import os

def cors_headers():
    allowed_origin = os.environ.get('CORS_ALLOWED_ORIGIN', '*')
    return {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE,PATCH",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,...",
        "Access-Control-Allow-Credentials": "false"
    }
```

When `CORS_ALLOWED_ORIGIN` is not set (e.g., local development), it falls back to `*`.

### Test Stack Deployment

Deploy the test stack as a separate CloudFormation stack (`h-dcn-test`) pointing to isolated `-Test` DynamoDB tables:

```bash
sam deploy \
  --stack-name h-dcn-test \
  --region eu-west-1 \
  --profile nonprofit-deploy \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    Stage=test \
    Table=Producten-Test \
    MembersTable=Members-Test \
    PaymentsTable=Payments-Test \
    EventsTable=Events-Test \
    MembershipsTable=Memberships-Test \
    CartsTable=Carts-Test \
    OrdersTable=Orders-Test \
    CountersTable=Counters-Test \
    StockMovementsTableName=StockMovements-Test
```

This creates its own API Gateway (the `ApiUrl` output gives you the invoke URL to configure as `REACT_APP_API_BASE_URL` for the test frontend). It shares the existing Cognito pool (`eu-west-1_fcUkvwjH5`) — test users are isolated by prefix.

### Test Data Seeding

Seed the `-Test` tables with representative data using the seed script:

```bash
# Seed all test tables with deterministic data
python scripts/seed-test-data.py

# Clear all test tables first, then seed fresh data
python scripts/seed-test-data.py --clear
```

The script uses the `nonprofit-deploy` AWS profile and:

- Creates test users in the shared Cognito pool (skip if they already exist)
- Populates each `-Test` DynamoDB table with ≥5 items of synthetic data
- Uses deterministic `SEED-{table}-{index}` partition keys (idempotent on re-run)
- Handles missing tables gracefully (prints error, skips, continues)

### Test User Accounts

Five dedicated test users are provisioned in the shared Cognito pool. They only have data in the `-Test` DynamoDB tables — no production data impact.

| Username         | Email                           | Role / Purpose   | Password    |
| ---------------- | ------------------------------- | ---------------- | ----------- |
| `test-admin`     | webmaster+testadmin@h-dcn.nl    | Full admin       | `Test1234!` |
| `test-lid`       | peter+testlid@pgeers.nl         | Regular member   | `Test1234!` |
| `test-treasurer` | peter+testtreasurer@jabaki.nl   | Treasurer        | `Test1234!` |
| `test-presmeet`  | pjageers+testpresmeet@gmail.com | PresMeet contact | `Test1234!` |
| `test-readonly`  | pjageers+testreadonly@gmail.com | Read-only        | `Test1234!` |

### Local Test Runner

Run all tests (backend + frontend) with a single command from the project root:

```powershell
# Run both backend and frontend tests
.\run-tests.ps1

# Run with coverage reporting
.\run-tests.ps1 -Coverage
```

The script:

- Runs `pytest tests/ --tb=short` from `backend/`
- Runs `npm test -- --watchAll=false` from `frontend/`
- Always executes both suites (no short-circuit on first failure)
- Prints a summary table with suite name, result, and exit code
- Exits 0 only if both suites pass
- With `-Coverage`: adds `--cov=handler --cov-report=term-missing` to backend, `--coverage` to frontend

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
