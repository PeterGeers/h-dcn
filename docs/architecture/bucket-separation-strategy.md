# Bucket Separation Strategy

## Overview

The H-DCN application uses a **two-bucket architecture** to separate code from data, ensuring safer deployments and better data protection.

## Bucket Architecture

### 🚀 Frontend Bucket: `testportal-h-dcn-frontend`

**Purpose**: Static website hosting for frontend code
**Contents**:

- HTML files (`index.html`)
- CSS files (`static/css/`)
- JavaScript files (`static/js/`)
- Asset manifest (`asset-manifest.json`)
- Build artifacts

**Deployment**: Automated via `deploy-frontend-safe.ps1`
**Lifecycle**: Overwritten with each code deployment

### 📊 Data Bucket: `my-hdcn-bucket`

**Purpose**: Persistent data and user content
**Contents**:

- `parameters.json` - Business configuration data
- `imagesWebsite/` - Logo and UI assets
  - `hdcnFavico.png` - H-DCN logo
  - `info-icon-orange.svg` - UI icons
- `product-images/` - Product photos
  - `G1.jpg`, `G2.jpg`, etc. - Product images

**Deployment**: Manual via dedicated scripts
**Lifecycle**: Persistent, never overwritten by code deployments

## Environment Variables

```bash
# Frontend/Code bucket
REACT_APP_S3_BUCKET=testportal-h-dcn-frontend

# Data/Images bucket
REACT_APP_IMAGES_BUCKET=my-hdcn-bucket
REACT_APP_IMAGES_BASE_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com
REACT_APP_LOGO_BUCKET_URL=https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com
```

## Deployment Scripts

### Frontend Code Deployment

```powershell
# Deploys only code, preserves data
.\scripts\deployment\deploy-frontend-safe.ps1
```

### Data Management

```powershell
# Deploy parameters.json changes
.\scripts\utilities\deploy-parameters.ps1

# Backup current parameters.json
.\scripts\utilities\backup-parameters.ps1

# Fix product image URLs
.\scripts\utilities\fix-product-image-urls.ps1
```

## Benefits

### 🛡️ Data Protection

- User content never deleted during code deployments
- Business data (parameters.json) preserved across deployments
- Accidental `--delete` flags only affect code, not data

### 🚀 Deployment Safety

- Frontend deployments are fast and safe
- Data changes are deliberate and tracked
- Clear separation of concerns

### 📈 Scalability

- Different backup strategies for code vs data
- Different access patterns and permissions
- Independent scaling and optimization

## File Loading Strategy

### Frontend Code

- Loaded from CloudFront CDN
- Fast global distribution
- Cached and optimized

### Parameters & Data

- Loaded directly from S3 data bucket
- Cache-busted with timestamps
- Immediate updates without CDN delays

### Images

- Served from S3 data bucket
- Persistent URLs
- User uploads preserved

## Migration Notes

**Previous Architecture**: Single bucket with mixed content
**Current Architecture**: Separated buckets by content type
**Migration**: Completed December 30, 2025

All product image URLs updated to point to data bucket.
Parameters.json moved to data bucket for persistence.
Frontend deployment no longer affects business data.

## Best Practices

1. **Never use `--delete` on data bucket**
2. **Always backup parameters.json before changes**
3. **Test parameter changes in development first**
4. **Use dedicated scripts for data operations**
5. **Keep frontend deployments separate from data updates**

## Troubleshooting

### Images Not Loading

- Check `REACT_APP_IMAGES_BUCKET` environment variable
- Verify images exist in `my-hdcn-bucket`
- Run `fix-product-image-urls.ps1` to update database URLs

### Parameters Not Loading

- Check `REACT_APP_IMAGES_BASE_URL` environment variable
- Verify `parameters.json` exists in `my-hdcn-bucket`
- Use `backup-parameters.ps1` to download current version

### Deployment Issues

- Use `deploy-frontend-safe.ps1` for code-only deployments
- Use `deploy-parameters.ps1` for data updates
- Never mix code and data deployments
