# Bucket Separation Strategy

> **Verified: June 2026** — reflects current S3 bucket setup as defined in `backend/template.yaml` and `.github/workflows/deploy-frontend.yml`.

## Overview

The H-DCN application uses a **multi-bucket architecture** to separate code from data and isolate concerns by function. This ensures safer deployments and better data protection.

## Bucket Architecture

### 🚀 Frontend Bucket: `h-dcn-frontend-506221081911`

**Purpose**: Static website hosting for the React SPA (production)
**Contents**:

- HTML files (`index.html`)
- CSS files (`static/css/`)
- JavaScript files (`static/js/`)
- Asset manifest (`asset-manifest.json`)
- Build artifacts
- PresMeet logos (`assets/presmeet/logos/`)

**Deployment**: Automated via GitHub Actions (`deploy-frontend.yml`) → `aws s3 sync --delete`
**CDN**: CloudFront distribution (managed via GitHub Actions vars `CLOUDFRONT_DISTRIBUTION_ID`)
**Lifecycle**: Overwritten with each code deployment

**Test environment**: `testportal-h-dcn-frontend` (separate bucket for test stage)

### 📊 Data Bucket: `h-dcn-data-506221081911`

**Purpose**: Persistent data, user content, and business assets
**Contents**:

- `parameters.json` — Business configuration data
- `imagesWebsite/` — Logo and UI assets (e.g., `hdcnFavico.png`)
- `product-images/` — Product photos
- `events/` — Event registry data
- `analytics/` — Analytics output data

**Deployment**: Manual via dedicated scripts or S3FileManager API (`/s3/files`)
**Lifecycle**: Persistent, never overwritten by code deployments

**Test environment**: `h-dcn-data-test-506221081911` (separate bucket for test stage)

### 📋 Reports Bucket: `h-dcn-reports`

**Purpose**: Admin report storage (member exports, analytics reports)
**Used by**: `admin_export_report`, `admin_generate_report` Lambda functions
**Lifecycle**: Reports generated on demand, managed independently

### 📋 Webshop Reports Bucket: `h-dcn-webshop-reports`

**Purpose**: Webshop admin report storage (stock reports, order exports)
**Used by**: Webshop admin Lambda functions
**Lifecycle**: Reports generated on demand, managed independently

### 📧 Email Templates Bucket: `h-dcn-email-templates`

**Purpose**: SES email template storage
**Managed by**: CloudFormation (`EmailTemplatesBucket` resource in SAM template)
**Used by**: Email sender Lambda functions
**Lifecycle**: Versioned, deployed via SAM

## Environment Variables

### Frontend (set in `.env` / CI workflow)

```bash
# Data bucket (images, parameters, events)
REACT_APP_DATA_BUCKET=h-dcn-data-506221081911          # prod
REACT_APP_DATA_BUCKET=h-dcn-data-test-506221081911     # test

# Legacy env vars (set from GitHub vars, point to same data bucket)
REACT_APP_S3_BUCKET=<from vars.REACT_APP_S3_BUCKET>
REACT_APP_IMAGES_BUCKET=<from vars.REACT_APP_IMAGES_BUCKET>
REACT_APP_IMAGES_BASE_URL=<from vars.REACT_APP_IMAGES_BASE_URL>
REACT_APP_LOGO_BUCKET_URL=<from vars.REACT_APP_LOGO_BUCKET_URL>
```

### Backend (set in SAM template → Lambda environment)

```yaml
# Data bucket (passed as SAM parameter, default: h-dcn-data-506221081911)
DataBucket → DATA_BUCKET_NAME, S3_BUCKET, REGISTRY_BUCKET_NAME

# Reports bucket
S3ReportsBucket → REPORTS_BUCKET_NAME (default: h-dcn-reports)
ReportsBucketName → REPORTS_BUCKET_NAME (default: h-dcn-webshop-reports)

# Frontend bucket (hardcoded in some handlers)
FRONTEND_BUCKET_NAME: "h-dcn-frontend-506221081911"

# Email templates (CloudFormation-managed)
EmailTemplatesBucket → EMAIL_TEMPLATES_BUCKET
```

## Deployment

### Frontend Code (GitHub Actions)

```bash
# Production
aws s3 sync frontend/build/ s3://h-dcn-frontend-506221081911/ --delete
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"

# Test
aws s3 sync frontend/build/ s3://testportal-h-dcn-frontend/ --delete
```

### Data Management (manual/scripts)

```powershell
# S3 File Manager API endpoint (CRUD for data bucket files)
# POST /s3/files — upload
# GET /s3/files?bucketName=...&prefix=...&recursive=true — list
# DELETE /s3/files — delete
```

## Benefits

### 🛡️ Data Protection

- User content never deleted during code deployments (`--delete` only affects frontend bucket)
- Business data (parameters.json, product images) preserved across deployments
- Separate test/prod buckets prevent accidental cross-contamination

### 🚀 Deployment Safety

- Frontend deployments are fast, safe, and fully automated
- Data changes are deliberate and tracked via the S3FileManager API
- Clear separation of concerns per bucket

### 📈 Scalability

- Different backup/versioning strategies per bucket
- Different IAM permissions per function (least privilege)
- Independent lifecycle management

## File Loading Strategy

### Frontend Code

- Served via CloudFront CDN (cache invalidation on each deploy)
- Fast global distribution with edge caching

### Parameters & Data

- Loaded directly from S3 data bucket via CloudFront or direct S3 URL
- Cache-busted with timestamps for immediate updates

### Images

- Served from S3 data bucket
- Persistent URLs (e.g., `https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/product-images/...`)
- User uploads preserved across deployments

## Migration History

| Date     | Change                                                                                                             |
| -------- | ------------------------------------------------------------------------------------------------------------------ |
| Dec 2025 | Migrated from single `my-hdcn-bucket` to separated architecture                                                    |
| Dec 2025 | Product image URLs migrated to `h-dcn-data-506221081911` (see `scripts/migrate_image_urls_to_nonprofit_bucket.py`) |
| 2026     | Reports buckets added for admin export functionality                                                               |
| 2026     | Email templates bucket added (CloudFormation managed)                                                              |

## Best Practices

1. **Never use `--delete` on data bucket** — only the frontend bucket uses `--delete` during sync
2. **Use the S3FileManager API** for data bucket operations (provides auth + audit trail)
3. **Always deploy to test stage first** (`gh workflow run deploy-frontend.yml --ref branch -f stage=test`)
4. **Keep frontend deployments separate from data updates**
5. **IAM policies use least privilege** — each Lambda only gets access to the buckets it needs

## Troubleshooting

### Images Not Loading

- Check `REACT_APP_DATA_BUCKET` / `REACT_APP_IMAGES_BASE_URL` environment variables
- Verify images exist in `h-dcn-data-506221081911/product-images/`
- Check CORS configuration on the data bucket

### Parameters Not Loading

- Verify `parameters.json` exists in the data bucket
- Check the S3FileManager API endpoint is working (`GET /s3/files?bucketName=h-dcn-data-506221081911&prefix=parameters`)

### Deployment Issues

- Frontend: Check GitHub Actions workflow `deploy-frontend.yml` — uses `FRONTEND_BUCKET_NAME` var
- Backend: SAM template passes `DataBucket` parameter (default: `h-dcn-data-506221081911`)
- Never mix code and data deployments

## Legacy References

> **Note**: Some utility scripts in `scripts/` still reference the old bucket name `my-hdcn-bucket`. These scripts were written during the migration period (Dec 2025) and point to the old personal-account bucket. The canonical data bucket is `h-dcn-data-506221081911` in the nonprofit account (506221081911).
