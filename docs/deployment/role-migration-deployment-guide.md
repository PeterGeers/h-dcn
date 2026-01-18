# Role Migration Deployment Guide

## Overview

This guide covers deployment procedures after the role migration from deprecated `_All` roles to the new permission + region role structure.

## New Role Structure

### Current Roles (Active)

**Permission-Based Roles:**

- `Members_CRUD` - Create, read, update, delete member data
- `Members_Read` - Read-only access to member data
- `Members_Export` - Export member data permissions
- `Products_CRUD` - Create, read, update, delete product data
- `Products_Read` - Read-only access to product data
- `Events_CRUD` - Create, read, update, delete event data
- `Events_Read` - Read-only access to event data
- `Communication_CRUD` - Full communication management
- `Communication_Read` - Read communication data
- `Webshop_Management` - Full webshop control
- `System_User_Management` - System administration
- `System_Logs_Read` - System logs access

**Regional Roles:**

- `Regio_All` - Access to all regions (national level)
- `Regio_Utrecht` - Utrecht region only
- `Regio_Limburg` - Limburg region only
- `Regio_Groningen/Drenthe` - Groningen/Drenthe region only
- `Regio_Zuid-Holland` - Zuid-Holland region only
- `Regio_Brabant/Zeeland` - Brabant/Zeeland region only
- `Regio_Friesland` - Friesland region only
- `Regio_Oost` - Oost region only
- `Regio_Duitsland` - Duitsland region only

**Special Roles:**

- `hdcnLeden` - Basic member access to personal data and webshop
- `verzoek_lid` - New user registration role

### Deprecated Roles (Removed)

❌ **No longer supported:**

- `hdcnAdmins` → Use `System_User_Management`
- `Members_CRUD_All` → Use `Members_CRUD + Regio_All`
- `Members_Read_All` → Use `Members_Read + Regio_All`
- `Products_CRUD_All` → Use `Products_CRUD + Regio_All`
- `Products_Read_All` → Use `Products_Read + Regio_All`
- `Events_CRUD_All` → Use `Events_CRUD + Regio_All`
- `Events_Read_All` → Use `Events_Read + Regio_All`

## Deployment Scripts Updated

### Scripts Modified for New Role Structure

1. **test-s3-list.ps1**

   - Changed: `hdcnAdmins` → `System_User_Management`
   - Purpose: S3 file listing tests

2. **test-s3-api.ps1**

   - Changed: `hdcnAdmins` → `System_User_Management`
   - Purpose: S3 API functionality tests

3. **cleanup-s3-bucket.ps1**

   - Changed: `hdcnAdmins` → `System_User_Management`
   - Purpose: S3 bucket cleanup operations

4. **startUpload/validate-deployment.ps1**
   - Added: Role migration validation checks
   - Purpose: Pre-deployment validation

### New Validation Scripts

1. **scripts/deployment/validate-role-migration.ps1**
   - Comprehensive role migration validation
   - Checks for deprecated role references
   - Validates current role structure usage

## Deployment Procedures

### 1. Pre-Deployment Validation

Run the role migration validation:

```powershell
.\scripts\deployment\validate-role-migration.ps1
```

This script will:

- ✅ Check for deprecated role references
- ✅ Validate current role structure usage
- ✅ Verify deployment tool availability
- ✅ Check configuration files

### 2. Frontend Deployment

**Standard Deployment:**

```powershell
.\startUpload\startUploadS3.ps1
```

**Fast Deployment (Development):**

```powershell
.\scripts\deployment\frontend-build-and-deploy-fast.ps1
```

**Safe Deployment (Production):**

```powershell
.\scripts\deployment\frontend-build-and-deploy-safe.ps1
```

### 3. Backend Deployment

**Full Backend Deployment:**

```powershell
.\scripts\deployment\backend-build-and-deploy-fast.ps1
```

This includes:

- SAM template validation
- Docker container builds (for parquet generation)
- Lambda function deployment
- Container image updates

### 4. Post-Deployment Validation

**Test API Endpoints:**

```powershell
.\test-s3-api.ps1
```

**Test S3 Operations:**

```powershell
.\test-s3-list.ps1
```

## Role-Based Access in Deployment

### System Administration Access

For deployment operations, users need:

- `System_User_Management` role
- AWS CLI access with appropriate permissions

### API Testing Access

For API testing scripts:

- `System_User_Management` role (replaces `hdcnAdmins`)
- Access to test endpoints

### S3 Operations Access

For S3 management:

- `System_User_Management` role
- S3 bucket permissions

## Troubleshooting

### Common Issues After Role Migration

1. **"Access Denied" errors in deployment scripts**

   - **Cause:** User still has old `hdcnAdmins` role
   - **Solution:** Assign `System_User_Management` role

2. **API tests failing with 403 errors**

   - **Cause:** Scripts using deprecated role headers
   - **Solution:** Verify scripts use `System_User_Management`

3. **S3 operations failing**
   - **Cause:** Missing regional permissions
   - **Solution:** Ensure user has appropriate regional role

### Validation Commands

**Check current user roles:**

```powershell
# This would be done through AWS Cognito console or API
# Users should have permission + region role combinations
```

**Validate deployment scripts:**

```powershell
.\scripts\deployment\validate-role-migration.ps1 -Verbose
```

**Test API connectivity:**

```powershell
.\test-s3-api.ps1
```

## Migration Checklist

### Before Deployment

- [ ] Run role migration validation script
- [ ] Verify no deprecated roles in deployment scripts
- [ ] Confirm users have appropriate new roles
- [ ] Test AWS CLI connectivity
- [ ] Validate SAM CLI availability (for backend)

### During Deployment

- [ ] Monitor deployment logs for role-related errors
- [ ] Verify API endpoints respond correctly
- [ ] Test S3 operations work as expected
- [ ] Confirm Docker containers deploy successfully

### After Deployment

- [ ] Run post-deployment validation tests
- [ ] Verify user access with new role structure
- [ ] Test regional filtering works correctly
- [ ] Confirm no deprecated role references remain

## Emergency Rollback

If deployment fails due to role issues:

1. **Check deployment logs** for specific role-related errors
2. **Verify user roles** in AWS Cognito
3. **Run validation script** to identify issues
4. **Fix role assignments** before retrying deployment

## Support

For deployment issues related to role migration:

1. Run `validate-role-migration.ps1` for detailed diagnostics
2. Check AWS Cognito for user role assignments
3. Verify API endpoints are accessible with new roles
4. Review deployment logs for specific error messages

## Security Notes

- New role structure provides better security through principle of least privilege
- Regional roles ensure users only access data for their assigned regions
- System administration is now separate from content management
- All deployment operations require explicit `System_User_Management` role
